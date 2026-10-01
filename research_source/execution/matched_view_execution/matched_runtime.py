"""Shared stdlib provenance, original audit extraction and serial admission."""
from __future__ import annotations
import ast
from contextlib import contextmanager
import ctypes
import dataclasses
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types

HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parent
PARENT = Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724')
PYTHON = Path(r'C:\项目\.venvs\lgm-baselines\Scripts\python.exe')
DATA = Path(r'C:\项目\IMTMN\datasets\University-1652')
FORMAL = PARENT/'lgm_game_pytorch/lgm_game_pytorch/formal_retrieval.py'
RUNNER = PARENT/'lgm_game_pytorch/experiments/run_frozen_formal_matrix.py'
DERIVED = HERE/'formal_retrieval_two_view.py'
REVIEWED_PLAN = EXECUTION/'MATCHED_VIEW_COMPARISON_PLAN.json'
EVIDENCE = PARENT/'lgm_game_pytorch/evidence_cache/university1652_clip_image_evidence.npz'
FORMAL_SHA = '081f327f8f83d79ab078adc61e76070c140f13e0ac9a0d8f423bfad15df59862'
RUNNER_SHA = 'f251e5088b306ddec4769fab06799008d06194bc459282f2432ac3238f4ba59f'
EVIDENCE_SHA = '8a2333d58dbb0ca56c5d5829159a32f294e11e686bb6b91d05098d4b170c2bc3'
ID_SHA = '7b2528d2920f7062f337b884825dd2de1de967810cac67ec516b10e5f995057e'
FAMILY = 'university_two_view_matched_v1'
TASKS = {'university1652_drone_to_satellite':(37855,951), 'university1652_satellite_to_drone':(701,51355)}
THREAD_KEYS = ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS')
sys.dont_write_bytecode = True


def utc(): return datetime.now(timezone.utc).isoformat()
def thread_environment(): return {name:os.environ.get(name) for name in THREAD_KEYS}
def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()
def canonical(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),default=str,allow_nan=False).encode()).hexdigest()
def artifact(path):
    path=Path(path).resolve(); return {'path':str(path),'bytes':path.stat().st_size,'sha256':sha(path)}
def save(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+f'.tmp.{os.getpid()}')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    os.replace(temp,path)
def seal(value): return {**value,'payload_sha256':canonical(value)}
def verify_seal(value):
    body=dict(value); expected=body.pop('payload_sha256',None)
    if canonical(body)!=expected: raise RuntimeError('Invalid sealed payload')
def inside(path):
    path=Path(path).resolve()
    if not path.is_relative_to(HERE): raise RuntimeError('Independent output escaped matched_view_execution')
    return path


def original_api():
    """Compile only selected original stdlib definitions; never import a model."""
    if sha(RUNNER)!=RUNNER_SHA: raise RuntimeError('Frozen runner changed')
    names={'DatasetSpec','RunSpec','load_json','canonical_sha256','sha256_file',
           'training_completion_issues','checkpoint_artifact_hash_issues',
           'evaluation_completion_issues','train_command','evaluation_command','base_environment'}
    tree=ast.parse(RUNNER.read_text(encoding='utf-8-sig'))
    nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
    audit=next(n for n in nodes if n.name=='evaluation_completion_issues')
    candidates=[n for n in ast.walk(audit) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='expected_tasks' for t in n.targets)]
    if len(candidates)!=1 or not isinstance(candidates[0].value,ast.IfExp) or candidates[0].value.body.value!=3:
        raise RuntimeError('Original evaluation task-count check changed')
    candidates[0].value.body.value=2  # Declared control scope: original three-task audit -> two tasks.
    module=types.ModuleType('_matched_original_audits');sys.modules[module.__name__]=module
    module.__dict__.update(Path=Path,hashlib=hashlib,json=json,os=os,sys=sys,dataclass=dataclasses.dataclass,FROZEN_EPOCHS=80)
    future=ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future,*nodes],type_ignores=[])),str(RUNNER),'exec'),module.__dict__)
    return module


def specifications():
    api=original_api()
    return [api.RunSpec(FAMILY,'university1652',variant,seed,'resnet18',512,
                       HERE/'runs'/variant/f'seed_{seed}',HERE/'evaluations'/variant/f'seed_{seed}')
            for variant in ('visual','full') for seed in (1,2,3)]


def dataset_spec(): return original_api().DatasetSpec('university1652',DATA,EVIDENCE,EVIDENCE_SHA)


def runtime_snapshot(python=PYTHON):
    script='import sys,json,importlib.metadata as m; print(json.dumps({"python":sys.version,"executable":sys.executable,"prefix":sys.prefix,"distributions":sorted((d.metadata.get("Name",""),d.version) for d in m.distributions()),"scientific_imports":[n for n in ("torch","numpy","scipy","PIL","cv2") if n in sys.modules]}))'
    result=subprocess.run([str(python),'-I','-c',script],capture_output=True,text=True,encoding='utf-8',check=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
    value=json.loads(result.stdout)
    if value['scientific_imports']: raise RuntimeError('Metadata probe imported scientific libraries')
    versions=dict(value['distributions'])
    for name,expected in {'numpy':'2.4.4','pillow':'12.2.0','torch':'2.11.0+cu126','torchvision':'0.26.0+cu126'}.items():
        lower={n.lower():v for n,v in versions.items()}
        if lower.get(name)!=expected: raise RuntimeError('Original baseline runtime differs: '+name)
    value['interpreter_sha256']=sha(python)
    return value


def validate_prepared(path,check_runtime=False):
    path=inside(path); plan=read(path);verify_seal(plan)
    if plan.get('schema')!='matched-view-execution.v1' or plan.get('status')!='prepared_not_registered': raise RuntimeError('Unexpected preparation')
    for record in plan['pins'].values():
        if artifact(record['path'])!=record: raise RuntimeError('Prepared input/source changed: '+record['path'])
    if check_runtime and runtime_snapshot()!=plan['runtime']: raise RuntimeError('Prepared original environment changed')
    if thread_environment()!=plan['host_thread_environment']:raise RuntimeError('Host thread environment differs from prepared inherited values; no automatic override is allowed')
    if os.environ.get('CUDA_VISIBLE_DEVICES')!=plan['host_cuda_visible_devices']:raise RuntimeError('Host CUDA visibility differs from the inherited preparation')
    return plan


def alive(pid,started=None):
    if not pid:return False
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.OpenProcess.restype=ctypes.c_void_p
    handle=kernel.OpenProcess(0x1000,False,int(pid))
    if not handle:
        error=ctypes.get_last_error()
        if error not in (0,87):raise RuntimeError(f'Cannot verify process identity: Win32 {error}')
        return False
    try:
        code=ctypes.c_ulong()
        if not kernel.GetExitCodeProcess(ctypes.c_void_p(handle),ctypes.byref(code)):raise RuntimeError('Cannot query process exit')
        if code.value!=259:return False
        if started:
            class FT(ctypes.Structure):_fields_=[('low',ctypes.c_uint32),('high',ctypes.c_uint32)]
            a,b,c,d=FT(),FT(),FT(),FT()
            if not kernel.GetProcessTimes(ctypes.c_void_p(handle),ctypes.byref(a),ctypes.byref(b),ctypes.byref(c),ctypes.byref(d)):raise RuntimeError('Cannot query process start')
            actual=((a.high<<32)|a.low)/10000000-11644473600
            if abs(actual-datetime.fromisoformat(started).timestamp())>15:return False
        return True
    finally:kernel.CloseHandle(ctypes.c_void_p(handle))


def recorded_owners(value):
    if isinstance(value,list):
        for row in value:yield from recorded_owners(row)
    elif isinstance(value,dict):
        for name,item in value.items():
            if (name=='pid' or name.endswith('_pid')) and type(item) is int and item>0:
                yield item,value.get('supervisor_started_utc') if name=='supervisor_pid' else value.get('started_utc')
            elif isinstance(item,(dict,list)):yield from recorded_owners(item)


def process_started_utc(pid):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.OpenProcess.restype=ctypes.c_void_p
    handle=kernel.OpenProcess(0x1000,False,int(pid))
    if not handle:raise RuntimeError('Cannot obtain actual process creation time')
    try:
        class FT(ctypes.Structure):_fields_=[('low',ctypes.c_uint32),('high',ctypes.c_uint32)]
        a,b,c,d=FT(),FT(),FT(),FT()
        if not kernel.GetProcessTimes(ctypes.c_void_p(handle),ctypes.byref(a),ctypes.byref(b),ctypes.byref(c),ctypes.byref(d)):raise RuntimeError('Cannot obtain actual process creation time')
        epoch=((a.high<<32)|a.low)/10000000-11644473600
        return datetime.fromtimestamp(epoch,timezone.utc).isoformat()
    finally:kernel.CloseHandle(ctypes.c_void_p(handle))


def write_owner_receipt(lease,lease_path):
    import multiprocessing
    pid=os.getpid();started=process_started_utc(pid)
    suffix=int(datetime.fromisoformat(started).timestamp()*1000000)
    folder=inside(Path(lease['attempt_dir'])/'owners');folder.mkdir(parents=True,exist_ok=True)
    path=folder/f'{pid}_{suffix}.json'
    if path.exists():
        previous=read(path);verify_seal(previous)
        if previous.get('lease_sha256')!=sha(lease_path) or previous.get('pid')!=pid or previous.get('started_utc')!=started:
            raise RuntimeError('Conflicting process ownership receipt')
        return previous
    value=seal({'schema':'matched-view-process-owner.v1','pid':pid,'started_utc':started,
        'multiprocessing_name':multiprocessing.current_process().name,'controller_pid':lease['controller_pid'],
        'controller_started_utc':lease['controller_started_utc'],'lease':str(lease_path),'lease_sha256':sha(lease_path),
        'prepared_sha256':lease['prepared_sha256'],'operation':lease['mode'],'id':lease['id']})
    save(path,value);return value


def write_launched_owner_receipt(lease,lease_path,process):
    """Record a spawned child's identity before it can import the dataset module."""
    pid=process.pid
    if type(pid) is not int or pid<=0:raise RuntimeError('Spawn returned without a child process identity')
    started=process_started_utc(pid)
    suffix=int(datetime.fromisoformat(started).timestamp()*1000000)
    folder=inside(Path(lease['attempt_dir'])/'owners');folder.mkdir(parents=True,exist_ok=True)
    path=folder/f'launch_{pid}_{suffix}.json'
    value=seal({'schema':'matched-view-process-owner.v1','pid':pid,'started_utc':started,
        'multiprocessing_name':process.name,'controller_pid':lease['controller_pid'],
        'controller_started_utc':lease['controller_started_utc'],'lease':str(lease_path),'lease_sha256':sha(lease_path),
        'prepared_sha256':lease['prepared_sha256'],'operation':lease['mode'],'id':lease['id'],
        'recorded_by_pid':os.getpid(),'recorded_by_started_utc':process_started_utc(os.getpid()),
        'source':'parent_launch',
        'observation':'original BaseProcess.start returned; actual Win32 child creation time, before requiring worker imports'})
    if path.exists():
        previous=read(path);verify_seal(previous)
        if previous!=value:raise RuntimeError('Conflicting launcher process ownership receipt')
        return previous
    save(path,value);return value


def install_process_start_observer(lease,lease_path):
    """Observe original multiprocessing launches without changing their arguments."""
    from multiprocessing.process import BaseProcess
    original=BaseProcess.start
    def observed_start(process,*args,**kwargs):
        answer=original(process,*args,**kwargs)
        write_launched_owner_receipt(lease,lease_path,process)
        return answer
    BaseProcess.start=observed_start
    return original


def owner_receipts(root=None):
    root=inside(root or HERE/'attempts')
    result=[];identities={}
    if root.exists():
        for path in sorted(root.rglob('owners/*.json')):
            value=read(path);verify_seal(value)
            if value.get('schema')!='matched-view-process-owner.v1' or not value.get('pid') or not value.get('started_utc'):
                raise RuntimeError('Invalid process ownership receipt')
            if sha(inside(value['lease']))!=value['lease_sha256']:raise RuntimeError('Process ownership lease changed')
            identity=(value['pid'],value['started_utc'])
            binding={key:value[key] for key in ('lease_sha256','prepared_sha256','operation','id','controller_pid','controller_started_utc')}
            if identity in identities and identities[identity]!=binding:raise RuntimeError('Worker and parent-launch receipts disagree on process ownership')
            identities[identity]=binding
            result.append({'receipt':artifact(path),**value})
    return result


def owned_processes_exited(root=None,require_receipt=False):
    records=owner_receipts(root)
    if require_receipt and not records:raise RuntimeError('The child never registered an actual Python process identity')
    for record in records:
        if alive(record['pid'],record['started_utc']):raise RuntimeError('An admitted main/worker process is still alive: '+str(record['pid']))
    return {'checked_utc':utc(),'all_recorded_main_and_worker_processes_exited':True,'owners':records}


def release_gate(prepared,release_path):
    if release_path is None:raise RuntimeError('Later serial release required; this prepared control is not registered')
    release=read(release_path)
    if release.get('schema')!='matched-view-release.v1' or release.get('allow_cuda') is not True or release.get('prepared_sha256')!=sha(prepared):
        raise RuntimeError('Release does not bind this prepared six-fit control')
    plan=validate_prepared(prepared)
    for name,expected in plan['predecessor_plan_sha256'].items():
        if sha(EXECUTION/name)!=expected or release.get('predecessor_plan_sha256',{}).get(name)!=expected:raise RuntimeError('Predecessor plan changed')
    definitions=[('status.json','completed',None),('pipeline_status.json','ready_for_extension_preparation',
        ['formal_aggregate','formal_figures','cross_dataset_transfer','robustness','robustness_aggregate','query_analysis','formal_efficiency_component']),
        ('extension_status.json','registered_extensions_finished_review_pending',
        [j['id'] for j in read(EXECUTION/'extension_plan.json')['jobs']]),
        ('latest_baseline_status.json','latest_baselines_finished_review_pending',
        [j['id'] for j in read(EXECUTION/'latest_baseline_plan.json')['jobs']])]
    proofs={}
    for name,status,ids in definitions:
        state=read(EXECUTION/name)
        if state.get('status')!=status:raise RuntimeError('Predecessor incomplete: '+name)
        if name=='status.json' and state.get('stage')!='all':raise RuntimeError('Primary must complete the all stage')
        if ids is not None:
            if [j.get('id') for j in state.get('jobs',[])]!=ids or any(j.get('status')!='completed' or j.get('exit_code')!=0 for j in state['jobs']):raise RuntimeError('Predecessor jobs incomplete: '+name)
        if name in ('extension_status.json','latest_baseline_status.json'):
            key='extension_plan.json' if name=='extension_status.json' else 'latest_baseline_plan.json'
            if state.get('plan_sha256')!=plan['predecessor_plan_sha256'][key]:raise RuntimeError('Predecessor state belongs to another plan')
        owner_key='controller_pid' if name=='status.json' else 'supervisor_pid'
        time_key='started_utc' if name=='status.json' else 'supervisor_started_utc'
        if not state.get(owner_key) or not state.get(time_key):raise RuntimeError('Missing preceding controller identity')
        for pid,started in recorded_owners(state):
            if not started:raise RuntimeError('Missing preceding child start time')
            if alive(pid,started):raise RuntimeError(f'Predecessor process still alive: {pid}')
        proofs[name]=artifact(EXECUTION/name)
    gpu=subprocess.run(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
    if any('python' in line.lower() for line in gpu.stdout.splitlines()):raise RuntimeError('Another Python GPU process is active')
    return {'checked_utc':utc(),'release':artifact(release_path),'preceding_status':proofs}


@contextmanager
def exclusive_lock():
    import msvcrt
    with (EXECUTION/'latest_baseline_gpu.lock').open('a+b') as stream:
        stream.seek(0,os.SEEK_END)
        if stream.tell()==0:stream.write(b'0');stream.flush()
        stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        try:yield
        finally:stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)


def child_gate():
    """Require a current parent's durable launch lease, including DataLoader workers."""
    lease_name=os.environ.get('MATCHED_VIEW_LEASE')
    if not lease_name:raise RuntimeError('Use the independent wrapper after serial release; direct model launch is disabled')
    lease=read(inside(lease_name));verify_seal(lease)
    if lease.get('schema')!='matched-view-child-lease.v1' or not alive(lease.get('controller_pid'),lease.get('controller_started_utc')):
        raise RuntimeError('Launch owner is absent or changed')
    if Path(sys.executable).resolve()!=PYTHON.resolve():raise RuntimeError('Use the prepared baseline Python')
    if sha(lease['prepared'])!=lease['prepared_sha256'] or sha(DERIVED)!=lease['derived_sha256']:raise RuntimeError('Child source/preparation changed')
    plan=read(lease['prepared']);verify_seal(plan)
    if thread_environment()!=plan['host_thread_environment'] or os.environ.get('CUDA_VISIBLE_DEVICES')!=plan['host_cuda_visible_devices']:
        raise RuntimeError('Spawned child/worker did not inherit the reviewed host environment')
    if os.environ.get('CUBLAS_WORKSPACE_CONFIG')!=':4096:8' or os.environ.get('PYTHONHASHSEED')!=str(lease['seed']):
        raise RuntimeError('Original per-seed runtime environment differs')
    if Path(lease['output_dir']).resolve().is_relative_to(HERE) is False:raise RuntimeError('Invalid child output root')
    write_owner_receipt(lease,inside(lease_name))
    return lease
