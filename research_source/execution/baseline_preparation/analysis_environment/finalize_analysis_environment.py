"""Publish the completed analysis-environment CPU evidence, never use CUDA."""
from pathlib import Path
import hashlib,json,subprocess,sys,os
P=Path(__file__).resolve().parent
PYTHON=Path(r'C:\项目\.venvs\lgm-paper-analysis\Scripts\python.exe')
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ledger=load(P/'preparation_ledger.json');assert ledger['status']=='installed_awaiting_cpu_fixture'
 command=[str(PYTHON),'-B',str(P/'check_analysis_cpu.py')]
 r=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',env={**os.environ,'PYTHONIOENCODING':'utf-8','PYTHONDONTWRITEBYTECODE':'1','CUDA_VISIBLE_DEVICES':'','MPLBACKEND':'Agg'})
 (P/'cpu_fixture.stdout.log').write_text(r.stdout,encoding='utf-8');(P/'cpu_fixture.stderr.log').write_text(r.stderr,encoding='utf-8')
 if r.returncode:raise RuntimeError('CPU fixture failed; inspect cpu_fixture.stderr.log')
 fixture=load(P/'cpu_fixture_validation.json');assert fixture['status']=='passed' and fixture['cuda_initialized'] is False and fixture['torch_imported'] is False
 fp=load(P/'analysis_environment_packages.json')
 manifest={'status':'ready','analysis_python':str(PYTHON),'base_training_environment':ledger['source'],'original_training_environment_unchanged':ledger['source_environment_unchanged'],
  'python_version':fp['python'],'packages':dict(fp['packages']),'copied_file_count':ledger['copied_file_count'],'copied_total_bytes':ledger['copied_total_bytes'],
  'gpu_executed':False,'cpu_fixture_validation':fixture,'source_sha256':{str(p):sha(p) for p in sorted(P.iterdir()) if p.is_file() and p.name!='analysis_environment_ready.json'}}
 (P/'analysis_environment_ready.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 print(json.dumps({'status':'ready','analysis_python':str(PYTHON),'ready_manifest':str(P/'analysis_environment_ready.json'),'ready_manifest_sha256':sha(P/'analysis_environment_ready.json'),'packages_count':len(fp['packages'])},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
