"""Resume the original frozen matrix, retaining source and partial-run provenance."""
from pathlib import Path
import argparse, datetime, hashlib, importlib.metadata, importlib.util, json, os, shutil, subprocess, sys, time
import msvcrt

HERE=Path(__file__).resolve().parent
ORIGINAL=Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724')
SCRIPT=ORIGINAL/'lgm_game_pytorch'/'experiments'/'run_frozen_formal_matrix.py'
EXPECTED_PYTHON=Path(r'C:\项目\.venvs\lgm-baselines\Scripts\python.exe')
EXPECTED_PACKAGES={'numpy':'2.4.4','Pillow':'12.2.0','torch':'2.11.0+cu126','torchvision':'0.26.0+cu126'}

def verify_training_environment():
    if Path(sys.executable).resolve()!=EXPECTED_PYTHON.resolve():
        raise RuntimeError('The original completed fits require the lgm-baselines interpreter, not the Transactions baseline environment')
    actual={name:importlib.metadata.version(name) for name in EXPECTED_PACKAGES}
    if actual!=EXPECTED_PACKAGES:
        raise RuntimeError('Original formal-training package versions differ: '+str(actual))
    if sys.version_info[:3]!=(3,11,9):
        raise RuntimeError('Original formal-training Python version differs')
    # Metadata alone is insufficient when another directory shadows a package.
    import numpy, PIL, torch, torchvision
    imported={'numpy':numpy.__version__,'Pillow':PIL.__version__,'torch':torch.__version__,'torchvision':torchvision.__version__}
    if imported!=EXPECTED_PACKAGES:
        raise RuntimeError('Imported scientific libraries differ from their registered versions')
    origins={name:str(Path(obj.__file__).resolve()) for name,obj in [('numpy',numpy),('Pillow',PIL),('torch',torch),('torchvision',torchvision)]}
    if any(not Path(origin).is_relative_to(EXPECTED_PYTHON.parent.parent.resolve()) for origin in origins.values()):
        raise RuntimeError('A training dependency was imported outside the original environment')
    manifests=[]
    for path in (ORIGINAL/'lgm_game_pytorch/runs/formal_main').glob('*/*/seed_*/run_manifest.json'):
        record=json.loads(path.read_text(encoding='utf-8'))
        if record.get('status')=='completed':
            if record.get('dependencies_and_device',{}).get('packages')!=EXPECTED_PACKAGES:
                raise RuntimeError('A completed fit records a different runtime: '+str(path))
            manifests.append({'path':str(path),'sha256':sha(path)})
    return {'python':sys.version,'executable':sys.executable,'packages':imported,'package_origins':origins,
            'verified_completed_fit_manifests':manifests,'cuda_initialized_by_guard':torch.cuda.is_initialized(),
            'checked_utc':utc()}

def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''): h.update(block)
    return h.hexdigest()
def save(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    temp=p.with_suffix('.tmp');temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(temp,p)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workers',type=int,default=8)
    parser.add_argument('--stage',choices=['main','sensitivity','evaluate','all'],default='all')
    args=parser.parse_args()
    if args.workers<0: raise ValueError('workers must be nonnegative')
    runtime=verify_training_environment()
    HERE.mkdir(parents=True,exist_ok=True)
    lock=(HERE/'matrix.lock').open('a+b');lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
    try: msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    except OSError: raise RuntimeError('A formal-matrix controller already holds the lock')
    ledger=json.loads((ORIGINAL/'lgm_game_pytorch'/'runs'/'frozen_formal_matrix_ledger.json').read_text(encoding='utf-8'))
    assert sha(SCRIPT)==ledger['runner_sha256']
    assert sha(ORIGINAL/'FORMAL_EXPERIMENT_PROTOCOL.md')==ledger['protocol_sha256']
    assert sha(ORIGINAL/'lgm_game_pytorch'/'lgm_game_pytorch'/'formal_retrieval.py')==ledger['formal_script_sha256']
    spec=importlib.util.spec_from_file_location('original_frozen_matrix',SCRIPT)
    legacy=importlib.util.module_from_spec(spec);sys.modules[spec.name]=legacy;spec.loader.exec_module(legacy)
    launch_id=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    status={'launch_id':launch_id,'controller_pid':os.getpid(),'started_utc':utc(),'status':'starting',
            'workers':args.workers,'source_runner':str(SCRIPT),'source_runner_sha256':sha(SCRIPT),
            'scientific_protocol_sha256':ledger['protocol_sha256'],'formal_code_sha256':ledger['formal_script_sha256'],
            'stage':args.stage,'python':sys.executable,'runtime_provenance':runtime,'events':[]}
    save(HERE/'status.json',status)
    original_train_command=legacy.train_command
    original_eval_command=legacy.evaluation_command
    def resource_command(fn):
        def command(*a,**kw):
            result=fn(*a,**kw)
            result[result.index('--workers')+1]=str(args.workers)
            return result
        return command
    legacy.train_command=resource_command(original_train_command)
    legacy.evaluation_command=resource_command(original_eval_command)
    def monitored_run(command,output_dir,environment):
        output_dir=Path(output_dir);output_dir.mkdir(parents=True,exist_ok=True)
        # Snapshot a resumed run before its config/log/checkpoint files are updated.
        if 'train' in command and (output_dir/'last.pt').is_file():
            backup=HERE/'resume_backups'/launch_id/output_dir.relative_to(ORIGINAL)
            backup.mkdir(parents=True,exist_ok=True)
            records={}
            for name in ['run_config.json','run_manifest.json','history.json','run.log','last.pt','best.pt']:
                src=output_dir/name
                if src.is_file():
                    dst=backup/name;shutil.copy2(src,dst);records[name]={'sha256':sha(dst),'bytes':dst.stat().st_size}
            save(backup/'backup_manifest.json',{'source':str(output_dir),'utc':utc(),'artifacts':records})
        started=time.monotonic()
        event={'started_utc':utc(),'command':command,'output_dir':str(output_dir),'status':'running'}
        status['events'].append(event)
        with (output_dir/'process_stdout.log').open('a',encoding='utf-8') as out,(output_dir/'process_stderr.log').open('a',encoding='utf-8') as err:
            p=subprocess.Popen(command,cwd=output_dir,env=environment,stdin=subprocess.DEVNULL,stdout=out,stderr=err,
                               creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            event['pid']=p.pid;status.update(status='running',active=event)
            while p.poll() is None:
                status['heartbeat_utc']=utc();status['active_elapsed_seconds']=round(time.monotonic()-started,1)
                manifest=output_dir/('run_manifest.json' if 'train' in command else 'evaluation_manifest.json')
                if manifest.is_file():
                    try:
                        run=json.loads(manifest.read_text(encoding='utf-8'))
                        status['active_progress']={k:run[k] for k in ['status','last_completed_epoch','history_rows','updated_utc'] if k in run}
                    except (OSError,ValueError): pass
                save(HERE/'status.json',status);time.sleep(20)
        event.update(finished_utc=utc(),exit_code=p.returncode,elapsed_seconds=round(time.monotonic()-started,1),status='completed' if p.returncode==0 else 'failed')
        save(HERE/'status.json',status)
        return p.returncode,time.monotonic()-started
    legacy.run_command=monitored_run
    try:
        sys.argv=[str(SCRIPT),'--stage',args.stage]
        legacy.main()
        status.update(status='completed',finished_utc=utc());status.pop('active',None)
    except BaseException as exc:
        status.update(status='failed',finished_utc=utc(),error=f'{type(exc).__name__}: {exc}')
        raise
    finally: save(HERE/'status.json',status)

if __name__=='__main__': main()
