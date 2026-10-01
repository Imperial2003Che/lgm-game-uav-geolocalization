"""Prepare or execute fixed CAMP author-checkpoint/full-gallery re-evaluation.

Prepare is filesystem/metadata only. Evaluate requires an explicit release record,
completed preceding queues and their process exit before any scientific import.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter
from contextlib import contextmanager
import csv
import ctypes
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import traceback

HERE=Path(__file__).resolve().parent
EXECUTION=HERE.parent
ROOT=Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724')
SOURCE=HERE.parents[1]/'literature/official_repos/snapshots/Mabel0403__CAMP__b04a9c856711'
CHECKPOINT=EXECUTION/'latest_author_checkpoints/CAMP_University_author_checkpoint.pth'
CHECKPOINT_SHA='6bc5b21310c9698588567a52f54c423e9e8f9c7a4473e85e5e462fea1898869b'
CORE=ROOT/'lgm_game_pytorch/lgm_game_pytorch/formal_retrieval.py'
CORE_SHA='081f327f8f83d79ab078adc61e76070c140f13e0ac9a0d8f423bfad15df59862'
SPLIT=ROOT/'lgm_game_pytorch/manifests/sues200_official_train_ids.yaml'
SPLIT_SHA='c1386d5c746aca48bbb2793ed1ee19d6cd7330a7f5f1b27a5ec43727317ec226'
SCHEMA='camp-author-checkpoint-re-evaluation.v1'
HEIGHTS=('150','200','250','300')
EXTENSION_IDS=['real_model_visualizations','heldout_height_training','heldout_and_seen_height_evaluation','t1_v3_native_resource_profile_then_7fits_70eval']
PRIMARY_STAGE_IDS=['formal_aggregate','formal_figures','cross_dataset_transfer','robustness','robustness_aggregate','query_analysis','formal_efficiency_component']
THREAD_ENVIRONMENT={name:'1' for name in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS')}
sys.dont_write_bytecode=True

def utc():return datetime.now(timezone.utc).isoformat()
def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def canonical(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def artifact(path):return {'path':str(Path(path).resolve()),'bytes':Path(path).stat().st_size,'sha256':sha(path)}
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+f'.tmp.{os.getpid()}')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    os.replace(temp,path)
def seal(value):return {**value,'payload_sha256':canonical(value)}
def verify_seal(value):
    body=dict(value);digest=body.pop('payload_sha256',None)
    if canonical(body)!=digest:raise RuntimeError('Prepared manifest payload hash differs')
def local_output(path):
    path=Path(path).resolve()
    if not path.is_relative_to(HERE):raise RuntimeError('All new outputs must stay inside camp_preparation')
    return path

def verify_sources():
    pins=load(HERE/'source_pins.json')
    for relative,item in pins['official_source_files'].items():
        path=SOURCE/relative
        if not path.is_file() or path.stat().st_size!=item['bytes'] or sha(path)!=item['sha256']:
            raise RuntimeError('Fixed official CAMP source changed: '+str(path))
    if sha(CORE)!=CORE_SHA or sha(SPLIT)!=SPLIT_SHA:
        raise RuntimeError('Frozen metric source or official SUES split changed')
    if CHECKPOINT.stat().st_size!=365745130 or sha(CHECKPOINT)!=CHECKPOINT_SHA:
        raise RuntimeError('Author checkpoint bytes differ from the fixed published download')
    meta=load(HERE/'strict_meta_compatibility.json')
    if meta.get('status')!='strict_meta_compatibility_passed_not_evaluated' or meta.get('checkpoint_sha256')!=CHECKPOINT_SHA or meta.get('adapter_sha256')!=sha(HERE/'camp_model.py'):
        raise RuntimeError('Strict metadata compatibility proof is absent or stale')
    if meta['proof'].get('tensor_count')!=394 or meta['proof'].get('missing_keys') or meta['proof'].get('unexpected_keys') or meta['proof'].get('shape_or_dtype_mismatches'):
        raise RuntimeError('Author checkpoint schema proof differs')
    return {'source_pin_file':artifact(HERE/'source_pins.json'),'official_source_tree_sha256':canonical(pins['official_source_files']),
            'metric_source':artifact(CORE),'sues_split':artifact(SPLIT),'checkpoint':artifact(CHECKPOINT),
            'download_provenance':artifact(EXECUTION/'latest_author_checkpoints/CAMP_University_download.json'),
            'explicit_author_schema_meta_proof':artifact(HERE/'strict_meta_compatibility.json'),
            'adapter_sources':{p.name:artifact(p) for p in [Path(__file__),HERE/'camp_model.py']}}

def runtime_snapshot(python):
    code='import sys,json,importlib.metadata as m; print(json.dumps({"executable":sys.executable,"python":sys.version,"prefix":sys.prefix,"distributions":sorted((d.metadata.get("Name",""),d.version) for d in m.distributions()),"scientific_modules_imported":[n for n in ("torch","numpy","PIL","cv2","timm","albumentations") if n in sys.modules]}))'
    result=subprocess.run([str(python),'-I','-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE,stdin=subprocess.DEVNULL,
                          text=True,encoding='utf-8',errors='strict',timeout=60,creationflags=subprocess.CREATE_NO_WINDOW,check=True)
    snapshot=json.loads(result.stdout)
    if snapshot['scientific_modules_imported']:raise RuntimeError('Metadata probe imported scientific modules')
    versions={k.lower().replace('_','-'):v for k,v in snapshot['distributions']}
    needed={'torch','torchvision','numpy','pillow','timm','albumentations'}
    missing=needed-set(versions)
    if missing or not ({'opencv-python','opencv-python-headless'}&set(versions)):
        raise RuntimeError('Independent CAMP runtime lacks evaluation dependencies: '+str(sorted(missing)))
    if len({'opencv-python','opencv-python-headless'}&set(versions))!=1:
        raise RuntimeError('Require exactly one OpenCV wheel to avoid shared-module ambiguity')
    snapshot['interpreter_sha256']=sha(python)
    snapshot['environment_type']='locally adapted evaluation environment; official repository provides no dependency lock'
    return snapshot

def identity_images(folder,dataset,root):
    folder=Path(folder)
    if not folder.is_dir():raise RuntimeError('Missing official image folder: '+str(folder))
    rows=[]
    for identity in sorted(folder.iterdir()):
        if not identity.is_dir():continue
        if not re.fullmatch(r'\d{4}',identity.name):raise RuntimeError('Unexpected identity directory: '+str(identity))
        for image in sorted(identity.rglob('*')):
            if image.is_file() and image.suffix.lower() in {'.jpg','.jpeg','.png','.bmp','.tif','.tiff'}:
                if image.parent!=identity:raise RuntimeError('Unexpected nested image path: '+str(image))
                info=image.stat()
                rows.append({'key':dataset+'/'+image.relative_to(root).as_posix(),'label':identity.name,'bytes':info.st_size,'mtime_ns':info.st_mtime_ns})
    return rows

def sues_train_ids():
    ids=re.findall(r'^\s*-\s*[\"\']?(\d{4})[\"\']?\s*$',SPLIT.read_text(encoding='utf-8'),re.M)
    if len(ids)!=120 or len(set(ids))!=120:raise RuntimeError('SUES official train split is not 120 distinct identities')
    return set(ids)

def discover_tasks(university_root,sues_root):
    university_root=Path(university_root).resolve();sues_root=Path(sues_root).resolve()
    u={name:identity_images(university_root/'test'/name,'university1652',university_root)
       for name in ('query_drone','gallery_satellite','query_satellite','gallery_drone')}
    counts={'query_drone':37855,'gallery_satellite':951,'query_satellite':701,'gallery_drone':51355}
    for name,n in counts.items():
        if len(u[name])!=n:raise RuntimeError(f'University {name} expected {n}, got {len(u[name])}')
    query_ids={r['label'] for r in u['query_drone']}
    gallery_ids={r['label'] for r in u['gallery_satellite']}
    if len(query_ids)!=701 or len(gallery_ids)!=951 or not query_ids<gallery_ids:
        raise RuntimeError('University query/full-gallery identity counts differ')
    if {r['label'] for r in u['query_satellite']}!=query_ids or {r['label'] for r in u['gallery_drone']}!=gallery_ids:
        raise RuntimeError('University two directions use inconsistent identity memberships')
    raw=[('university1652_drone_to_satellite','in_domain_author_checkpoint',u['query_drone'],u['gallery_satellite']),
         ('university1652_satellite_to_drone','in_domain_author_checkpoint',u['query_satellite'],u['gallery_drone'])]
    all_ids={f'{i:04d}' for i in range(1,201)};test_ids=all_ids-sues_train_ids()
    sat=identity_images(sues_root/'satellite-view','sues200',sues_root)
    if len(sat)!=200 or {r['label'] for r in sat}!=all_ids:raise RuntimeError('Incomplete SUES full satellite gallery')
    for height in HEIGHTS:
        drone=[]
        for identity in sorted(all_ids):
            folder=sues_root/'drone_view_512'/identity/height
            files=sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in {'.jpg','.jpeg','.png','.bmp','.tif','.tiff'})
            if len(files)!=50:raise RuntimeError(f'SUES {identity}/{height}: expected all 50 frames')
            for image in files:
                info=image.stat()
                drone.append({'key':'sues200/'+image.relative_to(sues_root).as_posix(),'label':identity,'bytes':info.st_size,'mtime_ns':info.st_mtime_ns})
        qd=[r for r in drone if r['label'] in test_ids];qs=[r for r in sat if r['label'] in test_ids]
        if (len(qd),len(qs),len(drone))!=(4000,80,10000):raise RuntimeError('SUES official query/gallery counts differ')
        raw.extend([(f'sues200_uav_{height}m_to_satellite','university1652_to_sues200_transfer',qd,sat),
                    (f'sues200_satellite_to_uav_{height}m','university1652_to_sues200_transfer',qs,drone)])
    unique={}
    for _,_,query,gallery in raw:
        for row in (*query,*gallery):
            if row['key'] in unique and unique[row['key']]!=row:raise RuntimeError('Conflicting file metadata')
            unique[row['key']]=row
    inventory=[unique[key] for key in sorted(unique)];indices={r['key']:i for i,r in enumerate(inventory)}
    tasks=[]
    for name,kind,query,gallery in raw:
        qids={r['label'] for r in query};gids={r['label'] for r in gallery}
        if not qids<gids:raise RuntimeError('Full gallery must retain distractor identities')
        tasks.append({'name':name,'task_type':kind,'query_indices':[indices[r['key']] for r in query],
                      'gallery_indices':[indices[r['key']] for r in gallery],'query_count':len(query),'gallery_count':len(gallery),
                      'query_identity_count':len(qids),'gallery_identity_count':len(gids),'distractor_identity_count':len(gids-qids),
                      'membership_sha256':canonical({'query':[(r['key'],r['label']) for r in query],'gallery':[(r['key'],r['label']) for r in gallery]})})
    return inventory,tasks

def record_path(row,roots):
    dataset,relative=row['key'].split('/',1)
    root=Path(roots[dataset]).resolve();path=(root/relative).resolve()
    if not path.is_relative_to(root):raise RuntimeError('Inventory path escapes dataset root')
    return path

def verify_inventory(inventory,roots):
    for row in inventory:
        path=record_path(row,roots);info=path.stat()
        if info.st_size!=row['bytes'] or info.st_mtime_ns!=row['mtime_ns']:
            raise RuntimeError('Prepared image path/size/time changed: '+str(path))

def prepare(args):
    sources=verify_sources();runtime=runtime_snapshot(args.python)
    semantic=load(HERE/'cpu_semantic_validation.json')
    if semantic.get('status')!='passed' or semantic.get('code_sha256')!=sha(Path(__file__)) or semantic.get('camp_model_sha256')!=sha(HERE/'camp_model.py'):
        raise RuntimeError('Run current CPU semantic checks before preparation')
    if Path(semantic.get('python','')).resolve()!=args.python.resolve() or semantic.get('validation_transform',{}).get('status')!='passed' or semantic.get('pos_scale_real_official_forward_fixture',{}).get('status')!='passed':
        raise RuntimeError('Independent CAMP runtime needs both transform and official-forward CPU fixtures')
    inventory,tasks=discover_tasks(args.university_root,args.sues_root)
    directory=HERE/'preparations'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    directory.mkdir(parents=True)
    save(directory/'inventory.json',inventory);save(directory/'tasks.json',tasks)
    manifest=seal({'schema':SCHEMA,'status':'prepared_not_evaluated','created_utc':utc(),'result_type':'author-checkpoint re-evaluation',
                   'source_training_dataset':'University-1652; author-provided checkpoint; training/selection details not inferred from filename',
                   'sources':sources,'runtime':runtime,'python':str(args.python.resolve()),
                   'semantic_cpu_validation':artifact(HERE/'cpu_semantic_validation.json'),
                   'roots':{'university1652':str(args.university_root.resolve()),'sues200':str(args.sues_root.resolve())},
                   'inventory':artifact(directory/'inventory.json'),'tasks':artifact(directory/'tasks.json'),'unique_images':len(inventory),'task_count':len(tasks),
                   'settings':{'image_size':384,'descriptor_dim':1024,'descriptor':'official model(img)[-2], backbone GAP + LayerNorm',
                               'normalization':'official F.normalize(dim=-1) under CUDA autocast, stored FP32','amp':True,'flip_tta':False,
                               'batch_size':args.batch_size,'workers':0,'ranking_chunk_size':args.chunk_size,'device':'cuda:0',
                               'thread_environment':THREAD_ENVIRONMENT,'torch_cpu_threads':1,'opencv_cpu_threads':1,
                               'gallery_protocol':'all original gallery identities retained; no label=-1 or junk removal',
                               'checkpoint_schema':'394 tensors matched strictly after explicit unused-pos_scale auxiliary adaptation; current original architecture has 395',
                               'absent_auxiliary_constant':'pos_scale=0.6 is the current official default, not an inferred author learned value; does not affect selected GAP descriptor',
                               'ranking':'frozen formal_retrieval.rank_task: FP32 cosine, stable descending ties, original trapezoid AP'},
                   'image_evidence':'Prepare pins full membership, file sizes and mtimes; evaluate hashes the exact raw bytes decoded for every descriptor and preserves them in image_content_sha256.jsonl.',
                   'selection_rule':'One fixed author checkpoint; no local training, target-test selection, data sampling, tuning or calibration'})
    save(directory/'manifest.json',manifest)
    save(directory/'release_template.json',{'schema':'camp-author-checkpoint-release.v1','allow_cuda':False,
             'prepared_manifest_sha256':sha(directory/'manifest.json'),'preceding_extension_plan_sha256':sha(EXECUTION/'extension_plan.json'),
             'release_note':'Set allow_cuda true only through an explicit later manual/serial queue release after all current extensions have completed and exited.'})
    print(json.dumps({'status':manifest['status'],'manifest':str(directory/'manifest.json'),'tasks':10,'unique_images':len(inventory),
                      'counts':[{k:t[k] for k in ('name','query_count','gallery_count','distractor_identity_count')} for t in tasks]},ensure_ascii=True,indent=2))

def alive(pid,started=None):
    if not pid:return False
    kernel=ctypes.windll.kernel32;kernel.OpenProcess.restype=ctypes.c_void_p
    handle=kernel.OpenProcess(0x1000,False,int(pid))
    if not handle:
        if kernel.GetLastError()==5:raise RuntimeError('Cannot verify process exit: access denied')
        return False
    try:
        code=ctypes.c_ulong()
        if not kernel.GetExitCodeProcess(ctypes.c_void_p(handle),ctypes.byref(code)):raise RuntimeError('Cannot query preceding process exit')
        if code.value!=259:return False
        if started:
            class FT(ctypes.Structure):_fields_=[('low',ctypes.c_uint32),('high',ctypes.c_uint32)]
            a,b,c,d=FT(),FT(),FT(),FT()
            if not kernel.GetProcessTimes(ctypes.c_void_p(handle),ctypes.byref(a),ctypes.byref(b),ctypes.byref(c),ctypes.byref(d)):raise RuntimeError('Cannot verify process identity')
            stamp=((a.high<<32)|a.low)/10000000-11644473600
            if abs(stamp-datetime.fromisoformat(started).timestamp())>15:return False
        return True
    finally:kernel.CloseHandle(ctypes.c_void_p(handle))

def require_process_exit(record,pid_key,started_key,label):
    pid=record.get(pid_key);started=record.get(started_key)
    if type(pid) is not int or pid<1 or not isinstance(started,str) or datetime.fromisoformat(started).tzinfo is None:
        raise RuntimeError('Missing verifiable process identity: '+label)
    if alive(pid,started):raise RuntimeError('Preceding process still running: '+label)

def release_gate(prepared,release_file):
    if release_file is None:raise RuntimeError('Explicit later release file required; current running queues are not modified')
    release=load(release_file)
    if release.get('schema')!='camp-author-checkpoint-release.v1' or release.get('allow_cuda') is not True or release.get('prepared_manifest_sha256')!=sha(prepared):
        raise RuntimeError('Release does not authorize this exact prepared manifest')
    if release.get('preceding_extension_plan_sha256')!=sha(EXECUTION/'extension_plan.json'):raise RuntimeError('Release refers to another extension plan')
    primary=load(EXECUTION/'status.json');pipeline=load(EXECUTION/'pipeline_status.json');extension=load(EXECUTION/'extension_status.json')
    if primary.get('status')!='completed':raise RuntimeError('Primary matrix has not completed')
    require_process_exit(primary,'controller_pid','started_utc','primary controller')
    for status,required,ids in [(pipeline,'ready_for_extension_preparation',PRIMARY_STAGE_IDS),(extension,'registered_extensions_finished_review_pending',EXTENSION_IDS)]:
        if status.get('status')!=required or [x.get('id') for x in status.get('jobs',[])]!=ids:
            raise RuntimeError('Preceding queue is not complete')
        if any(j.get('status')!='completed' or j.get('exit_code')!=0 for j in status['jobs']):raise RuntimeError('Incomplete preceding jobs')
        require_process_exit(status,'supervisor_pid','supervisor_started_utc','preceding supervisor')
        for job in status['jobs']:
            require_process_exit(job,'pid','started_utc','preceding child '+job['id'])
    if extension.get('plan_sha256')!=release['preceding_extension_plan_sha256']:raise RuntimeError('Completed extension state/plan mismatch')
    result=subprocess.run(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader,nounits'],
                          capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    if any('python' in line.lower() for line in result.stdout.splitlines()):raise RuntimeError('Another Python GPU process remains active')
    return {'released_utc':utc(),'release':artifact(release_file),'primary_status':artifact(EXECUTION/'status.json'),
            'pipeline_status':artifact(EXECUTION/'pipeline_status.json'),'extension_status':artifact(EXECUTION/'extension_status.json'),
            'extension_plan':artifact(EXECUTION/'extension_plan.json')}

def official_rank_function():
    """Compile only the unchanged pure NumPy ranking/AP functions from pinned core."""
    import numpy as np
    if sha(CORE)!=CORE_SHA:raise RuntimeError('Frozen rank source changed')
    tree=ast.parse(CORE.read_text(encoding='utf-8'))
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'official_trapezoid_ap','rank_task'}]
    if len(nodes)!=2:raise RuntimeError('Frozen metric function inventory changed')
    nodes.insert(0,ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0))
    namespace={'np':np,'math':math}
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(CORE),'exec'),namespace)
    return namespace['rank_task'],namespace['official_trapezoid_ap']

@dataclass(frozen=True)
class Record:
    relative_path:str
    label:str
@dataclass(frozen=True)
class Task:
    name:str
    query:tuple
    gallery:tuple

def rank_with_query_evidence(task,encoded,chunk_size):
    """Use frozen primary metrics and retain all positive ranks for independent AP audit."""
    import numpy as np
    rank,trapezoid=official_rank_function()
    metrics,arrays=rank(task,encoded,chunk_size)
    gallery=np.stack([encoded[r.relative_path.casefold()] for r in task.gallery]).astype(np.float32,copy=False)
    labels=np.asarray([r.label for r in task.gallery]);offsets=[0];flat=[];first=[];precision_aps=[]
    for start in range(0,len(task.query),chunk_size):
        query=task.query[start:start+chunk_size]
        query_features=np.stack([encoded[r.relative_path.casefold()] for r in query]).astype(np.float32,copy=False)
        ordering=np.argsort(-(query_features@gallery.T),axis=1,kind='stable')
        for local,row in enumerate(query):
            positions=np.flatnonzero(labels[ordering[local]]==row.label)
            if not len(positions):raise RuntimeError('Query has no positive in the full gallery')
            i=start+local
            if abs(trapezoid(positions)-float(arrays['per_query_official_trapezoid_AP'][i]))>2e-7:
                raise RuntimeError('Saved AP disagrees with independently retained positive ranks')
            if abs(1/(int(positions[0])+1)-float(arrays['reciprocal_rank'][i]))>1e-7:
                raise RuntimeError('First rank differs from frozen metric output')
            ranks=positions.astype(np.int64)+1
            flat.extend(ranks.tolist());offsets.append(len(flat));first.append(int(ranks[0]))
            precision_aps.append(float(np.mean(np.arange(1,len(ranks)+1,dtype=np.float64)/ranks)))
    first=np.asarray(first,dtype=np.int64)
    arrays.update(positive_ranks_1based=np.asarray(flat,dtype=np.int64),positive_rank_offsets=np.asarray(offsets,dtype=np.int64),
                  first_positive_rank_1based=first,per_query_R1=first<=1,per_query_R5=first<=5,per_query_R10=first<=10,
                  per_query_rank_precision_AP=np.asarray(precision_aps,dtype=np.float32),
                  gallery_paths=np.asarray([r.relative_path for r in task.gallery]),gallery_labels=labels)
    metrics['rank_precision_mAP']=float(np.mean(arrays['per_query_rank_precision_AP']))
    metrics['AP_primary']='official trapezoidal AP; rank-precision AP is separately named'
    return metrics,arrays

def validate_query_arrays(path,task,metrics):
    """Recompute per-query recall/rank and both AP definitions from saved ranks."""
    import numpy as np
    _,trapezoid=official_rank_function()
    with np.load(path,allow_pickle=False) as z:
        query_paths=np.asarray([r.relative_path for r in task.query]);query_labels=np.asarray([r.label for r in task.query])
        gallery_paths=np.asarray([r.relative_path for r in task.gallery]);gallery_labels=np.asarray([r.label for r in task.gallery])
        for key,expected in [('query_paths',query_paths),('query_labels',query_labels),('gallery_paths',gallery_paths),('gallery_labels',gallery_labels)]:
            if not np.array_equal(z[key],expected):raise RuntimeError('Saved query/gallery order or labels differ: '+key)
        offsets=z['positive_rank_offsets'];ranks=z['positive_ranks_1based'];n=len(task.query);g=len(task.gallery)
        if offsets.shape!=(n+1,) or offsets[0]!=0 or offsets[-1]!=len(ranks) or (np.diff(offsets)<=0).any():raise RuntimeError('Malformed saved positive-rank offsets')
        counts=Counter(gallery_labels.tolist());first=[];aps=[];standard=[]
        for i,label in enumerate(query_labels):
            positive=ranks[offsets[i]:offsets[i+1]]
            if len(positive)!=counts[label] or positive.min()<1 or positive.max()>g or (np.diff(positive)<=0).any():raise RuntimeError('Saved positive ranks are incomplete/invalid')
            first.append(int(positive[0]));aps.append(trapezoid(positive-1));standard.append(float(np.mean(np.arange(1,len(positive)+1)/positive)))
        first=np.asarray(first);aps=np.asarray(aps);standard=np.asarray(standard)
        expected_arrays={'first_positive_rank_1based':first,'per_query_R1':first<=1,'per_query_R5':first<=5,'per_query_R10':first<=10,
                         'per_query_official_trapezoid_AP':aps,'per_query_rank_precision_AP':standard,'reciprocal_rank':1/first,'correct':first==1}
        for key,expected in expected_arrays.items():
            if not np.allclose(z[key],expected,rtol=0,atol=2e-7):raise RuntimeError('Saved per-query value differs from saved positive ranks: '+key)
        index=z['top1_gallery_indices']
        if index.shape!=(n,) or (index<0).any() or (index>=g).any():raise RuntimeError('Invalid saved top-1 gallery indices')
        if not np.array_equal(z['top1_gallery_paths'],gallery_paths[index]) or not np.array_equal(z['top1_gallery_labels'],gallery_labels[index]):raise RuntimeError('Saved top-1 identity/path differs')
        if not np.array_equal(gallery_labels[index]==query_labels,first==1):raise RuntimeError('Saved top-1 correctness differs')
        expected_metrics={f'r_at_{k}':float(np.mean(first<=k)) for k in [1,5,10,20]}
        expected_metrics.update(official_trapezoid_mAP=float(np.asarray(aps,np.float32).mean()),
                                rank_precision_mAP=float(np.asarray(standard,np.float32).mean()),MRR=float(np.asarray(1/first,np.float32).mean()))
        for key,expected in expected_metrics.items():
            if abs(float(metrics[key])-expected)>2e-7:raise RuntimeError('Summary metric differs from saved per-query ranks: '+key)
    return {'query_count':n,'gallery_count':g,'all_positive_ranks_retained':True,'per_query_metrics_recomputed':True,'AP_definitions':['official_trapezoidal','rank_precision']}

def make_validation_transform():
    import albumentations as A
    import cv2
    from albumentations.pytorch import ToTensorV2
    return A.Compose([A.Resize(384,384,interpolation=cv2.INTER_LINEAR_EXACT,p=1.0),
                      A.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225]),ToTensorV2()])

def encode(manifest,inventory,directory,log):
    import cv2
    import numpy as np
    import torch
    import torch.nn.functional as F
    from camp_model import load_author_model,no_network
    torch.set_num_threads(1);cv2.setNumThreads(1)
    model,loading=load_author_model(CHECKPOINT,SOURCE)
    save(directory/'checkpoint_strict_load.json',loading)
    device=torch.device('cuda:0');model=model.to(device).eval()
    transform=make_validation_transform()
    features=np.lib.format.open_memmap(directory/'descriptors.npy',mode='w+',dtype=np.float32,shape=(len(inventory),1024))
    batch_size=manifest['settings']['batch_size']
    torch.backends.cudnn.benchmark=True;torch.backends.cudnn.deterministic=False
    with (directory/'image_content_sha256.jsonl').open('x',encoding='utf-8') as evidence,no_network(),torch.no_grad():
        for start in range(0,len(inventory),batch_size):
            rows=inventory[start:start+batch_size];images=[]
            for row in rows:
                path=record_path(row,manifest['roots']);before=path.stat();raw=path.read_bytes();after=path.stat()
                if before.st_size!=row['bytes'] or before.st_mtime_ns!=row['mtime_ns'] or (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
                    raise RuntimeError('Image changed between preparation and decoding: '+str(path))
                image=cv2.imdecode(np.frombuffer(raw,dtype=np.uint8),cv2.IMREAD_COLOR)
                if image is None:raise RuntimeError('OpenCV cannot decode '+str(path))
                image=cv2.cvtColor(image,cv2.COLOR_BGR2RGB)
                images.append(transform(image=image)['image'])
                evidence.write(json.dumps({'key':row['key'],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},ensure_ascii=False)+'\n')
            batch=torch.stack(images).to(device)
            with torch.autocast('cuda',dtype=torch.float16):
                descriptor=model(batch)[-2]
                descriptor=F.normalize(descriptor,dim=-1)
            values=descriptor.to(torch.float32).cpu().numpy()
            if values.shape!=(len(rows),1024) or not np.isfinite(values).all() or np.max(np.abs(np.linalg.norm(values,axis=1)-1))>2e-3:
                raise RuntimeError('Invalid normalized CAMP descriptor')
            features[start:start+len(rows)]=values
            if start==0 or (start//batch_size)%100==0:log(f'Encoded {start+len(rows)}/{len(inventory)} images')
            del batch,descriptor,values
        evidence.flush();os.fsync(evidence.fileno())
    features.flush();del features,model
    torch.cuda.empty_cache()
    save(directory/'runtime_actual.json',{'python':sys.executable,'torch':torch.__version__,'cuda':torch.version.cuda,
                                         'cudnn':torch.backends.cudnn.version(),'device':torch.cuda.get_device_name(device),
                                         'amp':True,'flip_tta':False,'cudnn_benchmark':True,'cudnn_deterministic':False,
                                         'thread_environment':{name:os.environ.get(name) for name in THREAD_ENVIRONMENT},
                                         'torch_cpu_threads':torch.get_num_threads(),'opencv_cpu_threads':cv2.getNumThreads()})

def evaluate(args):
    # Set before importing NumPy/OpenCV/torch so their pools inherit the policy.
    os.environ.update(THREAD_ENVIRONMENT)
    prepared=local_output(args.prepared);manifest=load(prepared);verify_seal(manifest)
    if manifest.get('schema')!=SCHEMA or manifest.get('status')!='prepared_not_evaluated':raise RuntimeError('Unexpected prepared record')
    if Path(sys.executable).resolve()!=Path(manifest['python']).resolve():raise RuntimeError('Use the prepared independent CAMP interpreter')
    directory=HERE/'results'/manifest['payload_sha256'][:16]/('attempt_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    directory.mkdir(parents=True)
    state={'schema':SCHEMA,'status':'checking_prerequisites','result_type':'author-checkpoint re-evaluation','started_utc':utc(),
           'prepared_manifest':artifact(prepared),'attempt_directory':str(directory),'pid':os.getpid()}
    save(directory/'status.json',state)
    log_stream=(directory/'run.log').open('x',encoding='utf-8')
    def log(message):
        line=utc()+' '+message
        log_stream.write(line+'\n');log_stream.flush();print(line,flush=True)
    try:
        gate=release_gate(prepared,args.release_file);save(directory/'release_gate.json',gate)
        if verify_sources()!=manifest['sources']:raise RuntimeError('Prepared scientific sources/checkpoint changed')
        if runtime_snapshot(sys.executable)!=manifest['runtime']:raise RuntimeError('Prepared independent environment changed')
        if artifact(Path(manifest['semantic_cpu_validation']['path']))!=manifest['semantic_cpu_validation']:
            raise RuntimeError('Prepared semantic validation report changed')
        for name in ('inventory','tasks'):
            p=Path(manifest[name]['path'])
            if artifact(p)!=manifest[name]:raise RuntimeError('Prepared input manifest changed: '+name)
        inventory=load(manifest['inventory']['path']);tasks=load(manifest['tasks']['path'])
        current_inventory,current_tasks=discover_tasks(manifest['roots']['university1652'],manifest['roots']['sues200'])
        if current_inventory!=inventory or current_tasks!=tasks:raise RuntimeError('Full dataset membership/metadata changed')
        del current_inventory,current_tasks
        # All preceding checks are standard-library/metadata only. Scientific
        # imports and checkpoint/model loading begin only after the release gate.
        state.update(status='encoding',release_verified=True);save(directory/'status.json',state)
        import numpy as np
        encode(manifest,inventory,directory,log)
        features=np.load(directory/'descriptors.npy',mmap_mode='r',allow_pickle=False)
        encoded={row['key'].casefold():features[i] for i,row in enumerate(inventory)}
        metrics={};records=[Record(row['key'],row['label']) for row in inventory]
        arrays_dir=directory/'per_query_arrays';arrays_dir.mkdir()
        for item in tasks:
            task=Task(item['name'],tuple(records[i] for i in item['query_indices']),tuple(records[i] for i in item['gallery_indices']))
            score,arrays=rank_with_query_evidence(task,encoded,manifest['settings']['ranking_chunk_size'])
            score.update(result_type='author-checkpoint re-evaluation',task_type=item['task_type'],source_training_dataset='University-1652',
                         gallery_protocol='all identities; no junk removal',checkpoint_sha256=CHECKPOINT_SHA)
            array_path=arrays_dir/(task.name+'_per_query.npz')
            np.savez_compressed(array_path,**arrays)
            proof=validate_query_arrays(array_path,task,score)
            save(arrays_dir/(task.name+'_validation.json'),proof)
            metrics[task.name]=score;save(directory/'metrics.partial.json',metrics)
            log(f'{task.name}: R@1={score["r_at_1"]:.8f}, AP={score["official_trapezoid_mAP"]:.8f}; {score["queries"]}/{score["gallery"]} full query/gallery')
        if len(metrics)!=10:raise RuntimeError('Expected exactly ten complete evaluation tasks')
        save(directory/'metrics.json',metrics)
        rows=[{'task':name,**value} for name,value in metrics.items()]
        with (directory/'metrics.csv').open('x',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        verify_inventory(inventory,manifest['roots'])
        if verify_sources()!=manifest['sources']:raise RuntimeError('Sources/checkpoint changed during evaluation')
        log('All ten author-checkpoint tasks completed; manuscript integration remains a separate review.')
        log_stream.close()
        hashes={p.relative_to(directory).as_posix():artifact(p) for p in directory.rglob('*') if p.is_file() and p.name not in {'status.json','completion.json'}}
        completion=seal({**state,'status':'completed','completed_utc':utc(),'task_count':10,'prepared_payload_sha256':manifest['payload_sha256'],
                         'artifacts':hashes,'scientific_label':'Author-provided University checkpoint, locally re-evaluated with full distractor galleries; SUES tasks are cross-dataset transfer, not SUES-trained results.'})
        save(directory/'completion.json',completion);save(directory/'status.json',{'status':'completed','completion':artifact(directory/'completion.json')})
    except BaseException as exc:
        state.update(status='failed_or_blocked',failed_utc=utc(),error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
        save(directory/'status.json',state);save(directory/'failure.json',state)
        if not log_stream.closed:log(str(exc))
        raise
    finally:
        if not log_stream.closed:log_stream.close()

def parse_args(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage',choices=['prepare','evaluate'],default='prepare')
    p.add_argument('--python',type=Path,default=Path(r'C:\项目\.venvs\lgm-camp\Scripts\python.exe'))
    p.add_argument('--university-root',type=Path,default=Path(r'C:\项目\IMTMN\datasets\University-1652'))
    p.add_argument('--sues-root',type=Path,default=Path(r'C:\项目\IMTMN\datasets\SUES-200'))
    p.add_argument('--batch-size',type=int,default=16);p.add_argument('--chunk-size',type=int,default=64)
    p.add_argument('--prepared',type=Path);p.add_argument('--release-file',type=Path)
    args=p.parse_args(argv)
    if args.batch_size<1 or args.chunk_size<1:p.error('Resource settings must be positive')
    if args.stage=='evaluate' and args.prepared is None:p.error('--prepared is required for evaluation')
    return args

@contextmanager
def evaluation_lock():
    import msvcrt
    # Runtime-only shared mutex with independently prepared latest baselines;
    # it closes the race between two successful GPU-idle checks.
    with (EXECUTION/'latest_baseline_gpu.lock').open('a+b') as lock:
        lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        try:yield
        finally:
            lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)

if __name__=='__main__':
    args=parse_args()
    if args.stage=='prepare':prepare(args)
    else:
        with evaluation_lock():evaluate(args)
