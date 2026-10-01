"""Clone the baseline without changing it, then plan a constrained CAMP environment."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, importlib.util, json, os, shutil, subprocess, traceback

HERE = Path(__file__).resolve().parent
SOURCE = Path(r'C:\项目\.venvs\lgm-baselines')
TARGET = Path(r'C:\项目\.venvs\lgm-camp')
HELPER = HERE.parents[1] / 'baseline_preparation/analysis_environment/prepare_analysis_environment.py'
spec = importlib.util.spec_from_file_location('readonly_environment_helpers', HELPER)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
sha, fingerprint, check_versions = helper.sha, helper.fingerprint, helper.check_versions
ENV = {**os.environ, 'PYTHONDONTWRITEBYTECODE':'1', 'PYTHONIOENCODING':'utf-8',
       'CUDA_VISIBLE_DEVICES':'', 'OMP_NUM_THREADS':'1', 'MKL_NUM_THREADS':'1'}
DIRECT = ['albumentations==1.3.1', 'opencv-python-headless==4.13.0.92',
          'scikit-learn==1.6.1', 'joblib==1.4.2', 'threadpoolctl==3.5.0',
          'tensorboard==2.20.0']

def now(): return datetime.now(timezone.utc).isoformat()
def put(name, value):
    (HERE/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
def read(name): return json.loads((HERE/name).read_text(encoding='utf-8'))
def run(command, stem):
    with (HERE/(stem+'.stdout.log')).open('w',encoding='utf-8') as out, (HERE/(stem+'.stderr.log')).open('w',encoding='utf-8') as err:
        result = subprocess.run(command, stdin=subprocess.DEVNULL,stdout=out,stderr=err,env=ENV)
    if result.returncode: raise RuntimeError(f'{stem} failed with {result.returncode}; preserve logs')
def normalize(name): return name.lower().replace('_','-').replace('.','-')

def copy_environment():
    if TARGET.exists(): raise FileExistsError('Never overwrite an existing CAMP environment')
    before = fingerprint(SOURCE); check_versions(before); put('source_before.json',before)
    constraints = '\n'.join(f'{name}=={version}' for name,version in before['packages'])+'\n'
    (HERE/'preserve_existing_constraints.txt').write_text(constraints,encoding='utf-8')
    put('copy_status.json',dict(status='copying',started_utc=now(),source=str(SOURCE),target=str(TARGET)))
    rows=[]
    def copy_checked(src,dst):
        original=sha(src); shutil.copy2(src,dst)
        if sha(dst)!=original: raise RuntimeError('Byte comparison failed for '+str(src))
        rows.append(dict(path=str(Path(src).relative_to(SOURCE)).replace('\\','/'),bytes=Path(src).stat().st_size,sha256=original))
        if len(rows)%250==0: put('copy_status.json',dict(status='copying',files=len(rows),last_path=rows[-1]['path'],heartbeat_utc=now()))
        return dst
    shutil.copytree(SOURCE,TARGET,copy_function=copy_checked,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    put('copied_file_manifest.json',rows)
    cloned=fingerprint(TARGET); check_versions(cloned)
    if cloned['packages']!=before['packages'] or cloned['records']!=before['records']:
        raise RuntimeError('Cloned package metadata mismatch')
    if Path(cloned['prefix']).resolve()!=TARGET.resolve(): raise RuntimeError('Incorrect Python prefix')
    if fingerprint(SOURCE)!=before: raise RuntimeError('Source environment changed')
    put('copy_status.json',dict(status='copied_verified',completed_utc=now(),source=str(SOURCE),target=str(TARGET),files=len(rows),bytes=sum(r['bytes'] for r in rows),manifest_sha256=sha(HERE/'copied_file_manifest.json'),helper_sha256=sha(HELPER),source_unchanged=True))

def plan():
    if (HERE/'dependency_resolution.json').exists(): raise FileExistsError('Preserve prior resolution')
    command=[str(TARGET/'Scripts/python.exe'),'-B','-m','pip','install','--dry-run','--only-binary=:all:',
             '--constraint',str(HERE/'preserve_existing_constraints.txt'),'--report',str(HERE/'dependency_resolution.json'),*DIRECT]
    put('resolve_command.json',dict(command=command,started_utc=now()))
    run(command,'resolve')
    report=read('dependency_resolution.json')
    old={normalize(k):v for k,v in read('source_before.json')['packages']}
    additions=[]
    for entry in report['install']:
        name,version=entry['metadata']['name'],entry['metadata']['version']
        if normalize(name) in old: raise RuntimeError('Resolver would change an existing package: '+name)
        download=entry['download_info']; digest=download['archive_info']['hashes']['sha256']
        additions.append(dict(name=name,version=version,url=download['url'],sha256=digest))
    put('planned_additions.json',dict(status='resolved_not_installed',created_utc=now(),additions=additions))
    print(json.dumps(additions,ensure_ascii=False))

def install():
    if (HERE/'ready_for_cpu_checks.json').exists(): raise FileExistsError('Environment already installed')
    additions=read('planned_additions.json')['additions']
    lines=[f"{row['url']} --hash=sha256:{row['sha256']}" for row in additions]
    requirements=HERE/'hashed_wheel_requirements.txt'
    requirements.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    command=[str(TARGET/'Scripts/python.exe'),'-B','-m','pip','install','--no-deps','--require-hashes',
             '--only-binary=:all:','--report',str(HERE/'pip_install_report.json'),'-r',str(requirements)]
    put('install_command.json',dict(command=command,started_utc=now()))
    run(command,'install')
    before=read('source_before.json'); after=fingerprint(TARGET); check_versions(after)
    old={normalize(k):v for k,v in before['packages']}; new={normalize(k):v for k,v in after['packages']}
    if any(new.get(k)!=v for k,v in old.items()): raise RuntimeError('Existing package version changed')
    if set(new)-set(old)!={normalize(x['name']) for x in additions}: raise RuntimeError('Unexpected package addition')
    for row in before['records']:
        if sha(TARGET/row['path'])!=row['sha256']: raise RuntimeError('Existing RECORD changed')
    source_after=fingerprint(SOURCE)
    if source_after!=before: raise RuntimeError('Active baseline environment changed')
    put('source_after.json',source_after); put('camp_environment_packages.json',after)
    run([str(TARGET/'Scripts/python.exe'),'-B','-m','pip','check'],'pip_check')
    put('ready_for_cpu_checks.json',dict(status='installed_awaiting_cpu_checks',completed_utc=now(),python=str(TARGET/'Scripts/python.exe'),source_unchanged=True,original_packages_unchanged=True,package_count=len(new),new_packages=additions,helper_sha256=sha(HELPER),gpu_initialized=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['copy','plan','install']);a=p.parse_args()
    try: {'copy':copy_environment,'plan':plan,'install':install}[a.stage]()
    except Exception:
        put('failure_'+a.stage+'_'+datetime.now().strftime('%Y%m%dT%H%M%S')+'.json',dict(stage=a.stage,when_utc=now(),traceback=traceback.format_exc()))
        raise
