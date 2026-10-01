"""Bounded stdlib-only fixtures; never import scientific libraries or run children."""
import ast
import copy
import io
import json
import math
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
from unittest.mock import patch
import zipfile

import matched_runtime as r
import matched_audit as audit
import run_matched_view as wrapper
from build_matched_source import derive
from prepare_matched_view import pure_formal


def denied(function,message):
    try:function()
    except (RuntimeError,ValueError,FileNotFoundError):return
    raise AssertionError(message)


def main():
    checks=[]
    text,diff,changes=derive()
    assert r.DERIVED.read_text(encoding='utf-8')==text and changes==['build_training_protocol','run_evaluate']
    for path in r.HERE.glob('*.py'):ast.parse(path.read_text(encoding='utf-8'))
    checks.append('All sources parse; only build_training_protocol and run_evaluate algorithm definitions differ from frozen original')
    api=r.original_api();specs=r.specifications()
    assert len(specs)==6 and [(s.variant,s.seed) for s in specs]==[(v,s) for v in ('visual','full') for s in (1,2,3)]
    for spec in specs:
        command=wrapper.command_for(spec,'train')
        inherited=api.train_command(r.HERE/'run_matched_child.py',r.dataset_spec(),spec);inherited[0]=str(r.PYTHON)
        assert command==inherited
        for flag,value in {'--epochs':'80','--workers':'8','--identities-per-batch':'16','--instances-per-identity':'4','--steps-per-epoch':'0','--samples-per-class-per-epoch':'0','--val-fraction':'0','--patience':'0','--learning-rate':'0.0003','--backbone':'resnet18','--embed-dim':'512'}.items():
            assert command[command.index(flag)+1]==value
        evaluation=wrapper.command_for(spec,'evaluate')
        assert evaluation[evaluation.index('--checkpoint')+1]==str(spec.run_dir/'best.pt')
        assert evaluation[evaluation.index('--eval-batch-size')+1]=='128'
    checks.append('Exact six variant/seed commands retain original training and evaluation options')
    denied(lambda:r.inside(r.PARENT/'lgm_game_pytorch/runs'),'Output escape accepted')
    denied(lambda:r.release_gate(r.HERE/'never.json',None),'Missing serial release accepted')
    with patch.dict('os.environ',{},clear=True):denied(r.child_gate,'Direct model import without parent lease accepted')
    checks.append('Original output roots and unleased model launch are rejected without scientific imports')
    seal=r.seal({'seed':1});r.verify_seal(seal)
    denied(lambda:r.verify_seal({**seal,'seed':2}),'Tampered preparation accepted')
    checks.append('Sealed payload tampering rejected')
    stamp='2026-09-14T00:00:00+00:00'
    pipeline=['formal_aggregate','formal_figures','cross_dataset_transfer','robustness','robustness_aggregate','query_analysis','formal_efficiency_component']
    extensions=['visuals','heldout_train','heldout_eval','t1']
    latest=['camp','dac']
    fixtures={'release.json':{'schema':'matched-view-release.v1','allow_cuda':True,'prepared_sha256':'pin',
                              'predecessor_plan_sha256':{'extension_plan.json':'pin','latest_baseline_plan.json':'pin'}},
        'extension_plan.json':{'jobs':[{'id':name} for name in extensions]},'latest_baseline_plan.json':{'jobs':[{'id':name} for name in latest]},
        'status.json':{'status':'completed','stage':'all','controller_pid':1,'started_utc':stamp}}
    for filename,status,names in [('pipeline_status.json','ready_for_extension_preparation',pipeline),
        ('extension_status.json','registered_extensions_finished_review_pending',extensions),
        ('latest_baseline_status.json','latest_baselines_finished_review_pending',latest)]:
        fixtures[filename]={'status':status,'supervisor_pid':2,'supervisor_started_utc':stamp,'plan_sha256':'pin',
                            'jobs':[{'id':name,'status':'completed','exit_code':0,'pid':10+i,'started_utc':stamp} for i,name in enumerate(names)]}
    with patch.object(r,'read',side_effect=lambda p:copy.deepcopy(fixtures[Path(p).name])),patch.object(r,'sha',return_value='pin'),\
         patch.object(r,'validate_prepared',return_value={'predecessor_plan_sha256':{'extension_plan.json':'pin','latest_baseline_plan.json':'pin'}}),\
         patch.object(r,'artifact',return_value={'sha256':'pin'}),patch.object(r,'alive',return_value=False),\
         patch.object(r.subprocess,'run',return_value=SimpleNamespace(stdout='')) as gpu:
        r.release_gate(Path('manifest.json'),Path('release.json'));assert gpu.call_count==1
        fixtures['latest_baseline_status.json']['jobs'][0]['status']='pending'
        denied(lambda:r.release_gate(Path('manifest.json'),Path('release.json')),'Unfinished latest baseline accepted')
        fixtures['latest_baseline_status.json']['jobs'][0]['status']='completed'
        fixtures['status.json']['stage']='main'
        denied(lambda:r.release_gate(Path('manifest.json'),Path('release.json')),'Main-only matrix accepted as all stages')
        fixtures['status.json']['stage']='all'
        with patch.object(r,'alive',return_value=True):denied(lambda:r.release_gate(Path('manifest.json'),Path('release.json')),'Live predecessor accepted')
        fixtures['pipeline_status.json']['jobs'][0].pop('started_utc')
        denied(lambda:r.release_gate(Path('manifest.json'),Path('release.json')),'Unidentified preceding child accepted')
        assert gpu.call_count==1
    checks.append('Real serial-gate code rejects unfinished latest baselines, main-only primary, live owners and missing child timestamps; mocked GPU query only')
    core=pure_formal(r.DERIVED)
    sampler=core.IdentityBalancedBatchSampler([str(i//5) for i in range(100)],16,4,0,0,1)
    for epoch in (0,1,79):
        sampler.set_epoch(epoch);batches=list(sampler)
        assert set(range(100)).issubset({index for batch in batches for index in batch})
        assert all(len(batch)==64 and len({str(i//5) for i in batch})==16 for batch in batches)
    checks.append('Actual unchanged sampler body preserves full coverage and native identity batches on a tiny CPU fixture')
    denied(lambda:core.build_training_protocol([],'sues200',0,1,[]),'SUES accepted in this University-only control')
    denied(lambda:core.build_training_protocol([],'university1652',.1,1,[]),'Validation tuning accepted')
    checks.append('Derived protocol rejects other datasets and nonzero validation fraction')
    def npy(dtype,values,fmt):
        header=repr({'descr':dtype,'fortran_order':False,'shape':(len(values),)}).encode('ascii')
        header+=b' '*((16-(10+len(header)+1)%16)%16)+b'\n'
        return b'\x93NUMPY\x01\x00'+struct.pack('<H',len(header))+header+struct.pack('<'+fmt*len(values),*values)
    memory=io.BytesIO()
    with zipfile.ZipFile(memory,'w') as archive:archive.writestr('rr.npy',npy('<f4',[1,.5,.25],'f'))
    memory.seek(0)
    with zipfile.ZipFile(memory) as archive:assert audit.npy_vector(archive,'rr')==[1,.5,.25]
    checks.append('Stdlib NPZ reader recovers original float32 per-query evidence on an in-memory fixture')
    # Complete/absent artifacts must not be treated as completed just because best.pt exists.
    missing=api.training_completion_issues(specs[0],r.dataset_spec(),r.sha(r.DERIVED))
    assert missing==['run_manifest.json is absent']
    checks.append('Absent six-fit results are rejected by unchanged original completion audit')
    parent=r.read(r.REVIEWED_PLAN)
    config=copy.deepcopy(r.read(parent['source_proofs']['visual_seed1_configuration']['path']))
    immutable=config['immutable_config'];immutable['code_sha256']=r.sha(r.DERIVED)
    protocol=copy.deepcopy(parent['path_only_split_audit']['matched_protocol_summary'])
    protocol.update(comparison_family=r.FAMILY,training_query_roles=['train_drone'],positive_gallery_role='train_satellite',
                    parent_training_query_roles=['train_drone','train_street'],removed_street_queries=2659)
    immutable['protocol']=protocol;immutable['image_inventory']['file_count']=38555
    steps=immutable['optimization']['steps_per_epoch_actual'];immutable['optimization']['sampler_step_count_schedule_sha256']=r.canonical([steps]*80)
    config['run_config_sha256']=r.canonical(immutable)
    example={'training_protocol_by_seed':{'1':copy.deepcopy(protocol)},'steps_per_epoch':steps,'settings':parent['inherited_settings']}
    with patch.object(r,'read',side_effect=lambda p:copy.deepcopy(config)):
        audit.audit_config(specs[0],example)
        config['cli']['workers']=4
        denied(lambda:audit.audit_config(specs[0],example),'Changed worker count accepted on resume')
        config['cli']['workers']=8
        immutable['protocol']['training_query_roles'].append('train_street');config['run_config_sha256']=r.canonical(immutable)
        denied(lambda:audit.audit_config(specs[0],example),'Three-view configuration accepted in matched control')
    checks.append('In-memory configuration audit rejects changed workers and added street-training roles')
    prohibited=['torch','numpy','scipy','matplotlib','PIL','torchvision','cv2']
    assert not any(name in sys.modules for name in prohibited)
    report={'status':'passed_stdlib_only','created_utc':r.utc(),'checks':checks,'count':len(checks),
            'scientific_imports':[],'cuda_execution':False,'model_construction':False,'training_or_evaluation_executed':False,
            'derived_source_sha256':r.sha(r.DERIVED),'adapter_source_sha256':{p.name:r.sha(p) for p in sorted(r.HERE.glob('*.py'))},
            'scope':'Source AST and tiny in-memory software fixtures only; full real path/sampler preparation is a separate report.'}
    r.save(r.HERE/'CPU_VALIDATION.json',report)
    print(json.dumps(report,ensure_ascii=True,indent=2))


if __name__=='__main__':main()
