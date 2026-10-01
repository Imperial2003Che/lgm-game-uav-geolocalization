"""Freeze the six-fit control using only paths, standard-library AST and metadata."""
from __future__ import annotations
import argparse
import ast
from collections import defaultdict
import dataclasses
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import random
import struct
import sys
import types
import zipfile

import matched_runtime as r
from build_matched_source import derive


def pure_formal(path):
    names={'EvidenceRecord','RetrievalTask','TrainingProtocol','canonical_json_bytes','canonical_sha256',
           'stable_identity_holdout','_group_by_label','_assert_task','build_training_protocol',
           'build_official_evaluation_tasks','IdentityBalancedBatchSampler'}
    tree=ast.parse(Path(path).read_text(encoding='utf-8-sig'))
    nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
    module=types.ModuleType('_matched_pure_'+Path(path).stem);sys.modules[module.__name__]=module
    module.__dict__.update(dataclass=dataclasses.dataclass,hashlib=hashlib,json=json,random=random,
                          math=math,defaultdict=defaultdict,BatchSampler=object,Path=Path)
    future=ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future,*nodes],type_ignores=[])),str(path),'exec'),module.__dict__)
    return module


def cached_paths():
    """Read only the Unicode path member of NPZ with the documented .npy header."""
    with zipfile.ZipFile(r.EVIDENCE) as archive:
        candidates=[n for n in archive.namelist() if n in ('relative_paths.npy','paths.npy','image_paths.npy')]
        if len(candidates)!=1:raise RuntimeError('Ambiguous or absent evidence path member: '+repr(candidates))
        with archive.open(candidates[0]) as stream:
            if stream.read(6)!=b'\x93NUMPY':raise RuntimeError('Unexpected NPY magic')
            version=stream.read(2);fmt='<H' if version==b'\x01\x00' else '<I'
            if version not in (b'\x01\x00',b'\x02\x00',b'\x03\x00'):raise RuntimeError('Unsupported NPY version')
            count=struct.unpack(fmt,stream.read(struct.calcsize(fmt)))[0]
            header=ast.literal_eval(stream.read(count).decode('utf-8' if version==b'\x03\x00' else 'latin1').strip())
            dtype=header['descr'];shape=header['shape']
            if header['fortran_order'] or len(shape)!=1 or not (dtype.startswith('<U') or dtype.startswith('|S')):raise RuntimeError('Unexpected path-array schema')
            width=int(dtype[2:])*(4 if dtype[1]=='U' else 1)
            paths=set()
            for _ in range(shape[0]):
                block=stream.read(width)
                if len(block)!=width:raise RuntimeError('Truncated evidence path array')
                text=block.decode('utf-32-le' if dtype[1]=='U' else 'utf-8').rstrip('\x00').replace('\\','/')
                paths.add(text.casefold())
            if len(paths)!=shape[0]:raise RuntimeError('Duplicate normalized evidence paths')
            return paths,{'member':candidates[0],'shape':list(shape),'dtype':dtype,'values_read':'only immutable image path strings; no probability arrays'}


def discover():
    core=pure_formal(r.DERIVED)
    records=[];inventory=[]
    paths,evidence_header=cached_paths()
    roles=[('train/drone','train_drone','train','drone'),('train/satellite','train_satellite','train','satellite'),
           ('train/street','train_street','train','street'),('test/query_drone','query_drone','test','drone'),
           ('test/gallery_satellite','gallery_satellite','test','satellite'),('test/query_satellite','query_satellite','test','satellite'),
           ('test/gallery_drone','gallery_drone','test','drone'),('test/query_street','query_street','test','street')]
    counts={}
    for folder,role,partition,view in roles:
        root=r.DATA/folder
        if not root.is_dir():raise RuntimeError('Missing official role directory: '+str(root))
        count=0
        for identity in sorted(root.iterdir()):
            if not identity.is_dir():continue
            for image in sorted(identity.iterdir()):
                if not image.is_file() or image.suffix.lower() not in {'.jpg','.jpeg','.png','.bmp','.tif','.tiff'}:continue
                relative=image.relative_to(r.DATA).as_posix()
                if relative.casefold() not in paths:raise RuntimeError('Required image absent from fixed CLIP evidence: '+relative)
                stat=image.stat()
                records.append(core.EvidenceRecord(len(records),relative,image.resolve(),identity.name,partition,view,role,''))
                inventory.append({'path':relative,'label':identity.name,'role':role,'bytes':stat.st_size,'mtime_ns':stat.st_mtime_ns})
                count+=1
        counts[role]=count
    if {k:v for k,v in counts.items() if k!='query_street'}!={'train_drone':37854,'train_satellite':701,'train_street':2659,'query_drone':37855,'gallery_satellite':951,'query_satellite':701,'gallery_drone':51355} or counts['query_street']<=0:
        raise RuntimeError('Reviewed University file counts changed: '+repr(counts))
    return core,records,inventory,counts,evidence_header


def audit_sampler(core,protocol,seed):
    sampler=core.IdentityBalancedBatchSampler([x.label for x in protocol.train_queries],16,4,0,0,seed)
    counts=[];schedule_hashes=[]
    expected=set(range(37854))
    for epoch in range(80):
        sampler.set_epoch(epoch)
        batches=list(sampler)
        if any(len(batch)!=64 or len({protocol.train_queries[i].label for i in batch})!=16 for batch in batches):raise RuntimeError('Original sampler violated native 16x4 batches')
        if not expected.issubset({index for batch in batches for index in batch}):raise RuntimeError('Original sampler lost training query coverage')
        counts.append(len(batches));schedule_hashes.append(r.canonical(batches))
    if len(set(counts))!=1:raise RuntimeError('Original sampler step counts vary across epochs')
    return {'seed':seed,'epochs':80,'steps_per_epoch':counts[0],'counts':counts,
            'counts_sha256':r.canonical(counts),'batch_schedule_sha256':schedule_hashes,
            'full_query_coverage_all_epochs':True,'native_batch_size':64,'derived_by':'actual unchanged original sampler body with object base; no Torch import'}


def prepare():
    if (r.HERE/'prepared_manifest.json').exists():raise RuntimeError('A prepared manifest already exists; do not overwrite frozen evidence')
    expected_text,diff,changed=derive()
    if r.DERIVED.read_text(encoding='utf-8')!=expected_text:raise RuntimeError('Derivative differs from the narrow reviewed patch')
    cpu=r.read(r.HERE/'CPU_VALIDATION.json')
    if cpu.get('status')!='passed_stdlib_only' or cpu.get('scientific_imports')!=[]:raise RuntimeError('Current standard-library CPU checks are required')
    if cpu['adapter_source_sha256']!={p.name:r.sha(p) for p in sorted(r.HERE.glob('*.py'))}:raise RuntimeError('CPU review predates current adapter sources')
    approved=r.read(r.REVIEWED_PLAN)
    if approved['scope']!={'fits':6,'variants':['visual','full'],'seeds':[1,2,3],'epochs':80,'evaluation_tasks_per_checkpoint':2,'total_checkpoint_task_evaluations':12}:raise RuntimeError('Reviewed scope changed')
    for key in ('formal_source','formal_runner','formal_protocol','extension_protocol','visual_seed1_configuration','evidence_meta'):
        proof=approved['source_proofs'][key]
        if r.sha(proof['path'])!=proof['sha256']:raise RuntimeError('Reviewed immutable source differs: '+key)
    if r.sha(r.EVIDENCE)!=r.EVIDENCE_SHA:raise RuntimeError('Fixed CLIP evidence bytes changed')
    pretrained=approved['inherited_settings']['model']['pretrained_initialization']
    if r.sha(pretrained['cached_file'])!=pretrained['cached_file_sha256']:raise RuntimeError('Original ImageNet initialization changed')
    api=r.original_api();specs=r.specifications()
    for spec in specs:
        if spec.run_dir.exists() or spec.evaluation_dir.exists():raise RuntimeError('Potential duplicate control output already exists: '+str(spec.run_dir))
    for proposed in approved['jobs']:
        if Path(proposed['proposed_run_directory']).exists() or Path(proposed['proposed_evaluation_directory']).exists():raise RuntimeError('A control already occupies the earlier proposed output root')
    core,records,inventory,counts,evidence_header=discover()
    original=pure_formal(r.FORMAL)
    schedules={};protocols={}
    for seed in (1,2,3):
        parent=original.build_training_protocol(records,'university1652',0,seed,[])
        protocol=core.build_training_protocol(records,'university1652',0,seed,[])
        if protocol.train_ids!=parent.train_ids or len(parent.train_queries)!=40513:raise RuntimeError('Two-view change altered the reviewed identity set')
        protocols[str(seed)]=protocol.protocol_summary
        schedules[str(seed)]=audit_sampler(core,protocol,seed)
    if len({s['steps_per_epoch'] for s in schedules.values()})!=1:raise RuntimeError('Step count differs across seeds')
    tasks=core.build_official_evaluation_tasks(records,'university1652',[])
    selected=[t for t in tasks if t.name in r.TASKS]
    if len(selected)!=2:raise RuntimeError('Official directions absent')
    for task in selected:
        if (len(task.query),len(task.gallery))!=r.TASKS[task.name]:raise RuntimeError('Evaluation scale differs')
        if len({x.label for x in task.gallery}-{x.label for x in task.query})!=250:raise RuntimeError('Distractor gallery differs')
    r.save(r.HERE/'path_inventory.json',inventory)
    r.save(r.HERE/'sampler_audit.json',{'kind':'stdlib software/data-path audit, not an experiment result','by_seed':schedules})
    r.save(r.HERE/'protocol_audit.json',{'counts':counts,'matched_protocol_by_seed':protocols,'evidence_path_header':evidence_header,
                                     'all_training_ids_unchanged':True,'evaluation_task_count':2,'distractor_ids_per_direction':250})
    inherited=approved['inherited_settings']
    r.save(r.HERE/'parent_configuration_difference.json',{
        'parent_source_sha256':r.FORMAL_SHA,'derived_source_sha256':r.sha(r.DERIVED),'changed_algorithm_definitions':changed,
        'scientific_change':'Exclude train_street from University training queries and UAV/satellite identity intersection',
        'training_queries_before':40513,'training_queries_after':37854,'training_identities_before_and_after':701,
        'steps_per_epoch_before':652,'steps_per_epoch_after':schedules['1']['steps_per_epoch'],
        'steps_rule':'Unchanged full-coverage sampler and 80 epochs; no forced 652 step count',
        'evaluation_scope':'Only the two unchanged University UAV/satellite tasks; omit Street-to-satellite',
        'retained_settings':inherited,'not_bitwise_equivalent_to_three_view':True,
        'output_location_change':'Approved conceptual plan proposed matched_view_comparison; current explicitly assigned implementation/output root is matched_view_execution',
        'resource_controls':{'workers':8,'training_batch':64,'eval_batch_size':128,'thread_environment':r.THREADS},
        'no_fullbatch_resource_measurement_yet':True})
    sources=[p for p in sorted(r.HERE.iterdir()) if p.suffix in {'.py','.patch'}]
    sources += [r.REVIEWED_PLAN,r.FORMAL,r.RUNNER,r.EVIDENCE,Path(pretrained['cached_file']),
                r.HERE/'path_inventory.json',r.HERE/'sampler_audit.json',r.HERE/'protocol_audit.json',r.HERE/'parent_configuration_difference.json',
                r.HERE/'CPU_VALIDATION.json',r.HERE/'README.md']
    sources += [Path(approved['source_proofs'][key]['path']) for key in ('formal_protocol','extension_protocol','visual_seed1_configuration','evidence_meta')]
    dataset=r.dataset_spec();jobs=[]
    for spec in specs:
        train=api.train_command(r.HERE/'run_matched_child.py',dataset,spec);evaluation=api.evaluation_command(r.HERE/'run_matched_child.py',dataset,spec)
        train[0]=evaluation[0]=str(r.PYTHON)
        jobs.append({'id':spec.identifier,'variant':spec.variant,'seed':spec.seed,'run_dir':str(spec.run_dir),'evaluation_dir':str(spec.evaluation_dir),
                     'train_command':train,'evaluation_command':evaluation,'epochs':80,'tasks':list(r.TASKS)})
    plan=r.seal({'schema':'matched-view-execution.v1','status':'prepared_not_registered','created_utc':r.utc(),
                 'result_type':'independently trained two-view matched control','family':r.FAMILY,'fits':6,'checkpoint_task_evaluations':12,
                 'pins':{str(p.resolve()):r.artifact(p) for p in sources},'runtime':r.runtime_snapshot(),
                 'predecessor_plan_sha256':{name:r.sha(r.EXECUTION/name) for name in ('extension_plan.json','latest_baseline_plan.json')},
                 'jobs':jobs,'training_protocol_by_seed':protocols,'steps_per_epoch':schedules['1']['steps_per_epoch'],
                 'settings':inherited,'thread_environment':r.THREADS,'resource_profile_required':{'variants':['visual','full'],'seed':1,'native_optimizer_updates':2},
                 'evaluation_gate':'All six full 80-epoch fits pass strict completion and checkpoint audits before either official test task is evaluated',
                 'image_evidence':'Prepare pins full path/size/mtime membership. Original train/evaluate computes content inventory hashes of all actually used images.',
                 'actual_scientific_execution':False})
    r.save(r.HERE/'prepared_manifest.json',plan)
    r.save(r.HERE/'release_template.json',{'schema':'matched-view-release.v1','allow_cuda':False,
        'prepared_sha256':r.sha(r.HERE/'prepared_manifest.json'),'predecessor_plan_sha256':plan['predecessor_plan_sha256']})
    job={'id':'matched_two_view_profile_then_6fits_12eval','status':'prepared_not_registered',
         'command':[str(r.PYTHON),'-B',str(r.HERE/'run_matched_view.py'),'--stage','all','--prepared',str(r.HERE/'prepared_manifest.json'),'--release-file',str(r.HERE/'release.json')],
         'cwd':str(r.HERE),'source_sha256':{p:item['sha256'] for p,item in plan['pins'].items()},'prepared_manifest':r.artifact(r.HERE/'prepared_manifest.json')}
    r.save(r.HERE/'queue_job.json',job)
    print(json.dumps({'status':plan['status'],'prepared':r.artifact(r.HERE/'prepared_manifest.json'),
                      'steps_per_epoch':plan['steps_per_epoch'],'fits':6,'task_evaluations':12,'scientific_imports':False},ensure_ascii=True))


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    prepare()
