"""Create an isolated analysis venv copy; preserve the training venv verbatim."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,shutil,subprocess,sys
P=Path(__file__).resolve().parent
SOURCE=Path(r'C:\项目\.venvs\lgm-baselines')
TARGET=Path(r'C:\项目\.venvs\lgm-paper-analysis')
EXPECTED={'numpy':'2.4.4','pillow':'12.2.0','torch':'2.11.0+cu126','torchvision':'0.26.0+cu126','matplotlib':'3.10.9'}
ADDITIONS=['scikit-learn==1.6.1','joblib==1.4.2','threadpoolctl==3.5.0']
def now():return datetime.now(timezone.utc).isoformat()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 return h.hexdigest()
def put(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def fingerprint(root):
 code="import importlib.metadata as m,json,sys;print(json.dumps({'python':sys.version,'executable':sys.executable,'prefix':sys.prefix,'base_prefix':sys.base_prefix,'packages':sorted([(d.metadata['Name'].lower(),d.version) for d in m.distributions()])}))"
 r=subprocess.run([str(root/'Scripts/python.exe'),'-B','-c',code],capture_output=True,text=True,encoding='utf-8',check=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'})
 obj=json.loads(r.stdout)
 obj['records']=[{'path':str(p.relative_to(root)).replace('\\','/'),'sha256':sha(p)} for p in sorted((root/'Lib/site-packages').glob('*.dist-info/RECORD'))]
 return obj
def check_versions(fp):
 installed=dict(fp['packages'])
 for name,version in EXPECTED.items():assert installed[name]==version,(name,installed[name],version)
def main():
 assert SOURCE.resolve()==Path(r'C:\项目\.venvs\lgm-baselines').resolve()
 assert TARGET.resolve()==Path(r'C:\项目\.venvs\lgm-paper-analysis').resolve()
 if TARGET.exists():raise RuntimeError('Target already exists; refuse to overwrite. Inspect its provenance before continuing.')
 before=fingerprint(SOURCE);check_versions(before);put(P/'source_before.json',before)
 cfg=(SOURCE/'pyvenv.cfg').read_text(encoding='utf-8');(P/'source_pyvenv.cfg').write_text(cfg,encoding='utf-8')
 ledger={'status':'copying','source':str(SOURCE),'target':str(TARGET),'started_utc':now(),'source_before_sha256':sha(P/'source_before.json'),'source_pyvenv_sha256':sha(SOURCE/'pyvenv.cfg'),'commands':[]}
 put(P/'preparation_ledger.json',ledger)
 rows=[]
 def copy_checked(src,dst):
  before_hash=sha(src);shutil.copy2(src,dst);after_hash=sha(dst)
  if before_hash!=after_hash:raise RuntimeError('Copy verification failed: '+str(src))
  rows.append({'relative_path':str(Path(src).relative_to(SOURCE)).replace('\\','/'),'bytes':Path(src).stat().st_size,'sha256':before_hash})
  return dst
 shutil.copytree(SOURCE,TARGET,copy_function=copy_checked,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 put(P/'copied_file_manifest.json',rows)
 ledger.update(status='copied',copied_file_count=len(rows),copied_total_bytes=sum(r['bytes'] for r in rows),copied_manifest_sha256=sha(P/'copied_file_manifest.json'))
 put(P/'preparation_ledger.json',ledger)
 # Keep the original cfg byte-for-byte; the executable uses the current directory
 # for sys.prefix. Its historical command points to the prior original location.
 assert sha(SOURCE/'pyvenv.cfg')==sha(TARGET/'pyvenv.cfg')
 cloned=fingerprint(TARGET);check_versions(cloned)
 assert cloned['packages']==before['packages'] and cloned['records']==before['records']
 assert Path(cloned['prefix']).resolve()==TARGET.resolve()
 python=TARGET/'Scripts/python.exe'
 command=[str(python),'-B','-m','pip','install','--no-deps','--only-binary=:all:','--report',str(P/'pip_install_report.json'),*ADDITIONS]
 ledger['commands'].append(command);put(P/'preparation_ledger.json',ledger)
 with (P/'pip_install.stdout.log').open('w',encoding='utf-8') as out,(P/'pip_install.stderr.log').open('w',encoding='utf-8') as err:
  r=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=out,stderr=err,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8','CUDA_VISIBLE_DEVICES':''})
 if r.returncode:raise RuntimeError('pip install failed; preserve target and inspect logs.')
 after=fingerprint(TARGET);check_versions(after);put(P/'analysis_environment_packages.json',after)
 source_after=fingerprint(SOURCE);put(P/'source_after.json',source_after)
 assert source_after==before,'Original training environment metadata changed.'
 old=dict(before['packages']);new=dict(after['packages'])
 assert all(new[k]==v for k,v in old.items()),'An original package version changed.'
 assert set(new)-set(old)=={'scikit-learn','joblib','threadpoolctl'}
 for row in before['records']:
  assert sha(TARGET/row['path'])==row['sha256'],'An original distribution RECORD changed.'
 check=[str(python),'-B','-m','pip','check'];ledger['commands'].append(check)
 r=subprocess.run(check,capture_output=True,text=True,encoding='utf-8',env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
 (P/'pip_check.stdout.log').write_text(r.stdout,encoding='utf-8');(P/'pip_check.stderr.log').write_text(r.stderr,encoding='utf-8')
 if r.returncode:raise RuntimeError('pip check failed')
 ledger.update(status='installed_awaiting_cpu_fixture',finished_utc=now(),source_environment_unchanged=True,source_after_sha256=sha(P/'source_after.json'),analysis_packages_sha256=sha(P/'analysis_environment_packages.json'),pip_install_report_sha256=sha(P/'pip_install_report.json'),gpu_initialized=False)
 put(P/'preparation_ledger.json',ledger)
 print(json.dumps({'status':ledger['status'],'analysis_python':str(python),'copied_files':len(rows),'copied_bytes':ledger['copied_total_bytes']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
