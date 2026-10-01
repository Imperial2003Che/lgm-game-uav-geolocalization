#!/usr/bin/env python3
"""CPU prepare -> measured profile -> isolated T1 seven-fit/70-evaluation runner.

Default is prepare (CPU only). --stage all explicitly runs CUDA after preparation.
All commands, logs, artifact hashes and transitions are retained in this directory.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,subprocess,sys
P=Path(__file__).resolve().parent
QPY=Path(r'C:\项目\.venvs\lgm-transactions\Scripts\python.exe')
MPY=Path(r'C:\项目\.venvs\lgm-mccg\Scripts\python.exe')
DELIVERY=P/'compatibility_v3/delivery';WORK=P/'compatibility_v3/work'
PROBE=P/'profile_transactions_resources.py'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 return h.hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--stage',choices=['prepare','measure','all'],default='prepare');ap.add_argument('--plan',type=Path)
 ap.add_argument('--train-root',type=Path,default=Path(r'C:\项目\IMTMN\datasets\University-1652\train'))
 ap.add_argument('--test-root',type=Path);ap.add_argument('--sues-root',type=Path);ap.add_argument('--sues-manifest',type=Path)
 ap.add_argument('--device-index',type=int,default=0);a=ap.parse_args()
 if a.stage=='all' and any(x is None for x in [a.test_root,a.sues_root,a.sues_manifest]):ap.error('--stage all requires --test-root, --sues-root and --sues-manifest; only the original post-fit evaluation stage reads them.')
 for name in ['qdfl_cpu_import_preflight.json','mccg_cpu_import_preflight.json']:
  r=load(P/name)
  if r.get('status')!='passed' or r.get('cuda_initialized') is not False:raise RuntimeError('CPU import preflight must pass: '+name)
 session=P/'extension_runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');session.mkdir(parents=True)
 ledger={'stage':a.stage,'status':'running','wrapper_sha256':sha(__file__),'probe_sha256':sha(PROBE),'registration_path':str(P/'compatibility_v3/registration.json'),
         'registration_sha256':sha(P/'compatibility_v3/registration.json'),'delivery_root':str(DELIVERY),'external_work_root':str(WORK),'commands':[]}
 def command(label,cmd):
  entry={'label':label,'argv':[str(x) for x in cmd],'started_utc':datetime.now(timezone.utc).isoformat(),'stdout_path':str(session/(label+'.stdout.log')),'stderr_path':str(session/(label+'.stderr.log'))}
  ledger['commands'].append(entry);write(session/'ledger.json',ledger)
  with Path(entry['stdout_path']).open('x',encoding='utf-8') as out,Path(entry['stderr_path']).open('x',encoding='utf-8') as err:
   r=subprocess.run(entry['argv'],stdin=subprocess.DEVNULL,stdout=out,stderr=err,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'},check=False)
  entry.update(returncode=r.returncode,completed_utc=datetime.now(timezone.utc).isoformat(),stdout_sha256=sha(entry['stdout_path']),stderr_sha256=sha(entry['stderr_path']))
  write(session/'ledger.json',ledger)
  if r.returncode:raise RuntimeError(label+' failed; see '+str(session/'ledger.json'))
  return load(entry['stdout_path'])
 try:
  if a.plan:
   plan=a.plan.resolve();p=load(plan)
   if Path(p['delivery_root']).resolve()!=DELIVERY.resolve() or Path(p['external_work_root']).resolve()!=WORK.resolve():raise RuntimeError('Plan is not bound to the isolated MCCG v3 registration.')
   if Path(p['train_root']).resolve()!=a.train_root.resolve() or p['device_index']!=a.device_index:raise RuntimeError('Training root/device differ from the prepared resource plan.')
  else:
   r=command('01_cpu_prepare',[QPY,'-B',PROBE,'--stage','prepare','--delivery-root',DELIVERY,'--external-work-root',WORK,'--train-root',a.train_root,
            '--qdfl-python',QPY,'--mccg-python',MPY,'--device-index',a.device_index,'--output-root',P/'v3_resource_measurements'])
   plan=Path(r['plan_path'])
  ledger.update(plan_path=str(plan),plan_sha256=sha(plan));write(session/'ledger.json',ledger)
  if a.stage=='prepare':ledger['status']='prepared_cpu_only'
  else:
   r=command('02_cuda_measure',[QPY,'-B',PROBE,'--stage','measure','--plan',plan])
   profile=Path(r['profile_path']);payload=load(profile)
   if r['status']!='frozen' or payload['status']!='frozen' or len(payload['configs'])!=5:raise RuntimeError('Only a complete, validated, measured five-config profile can enter T1 fitting.')
   ledger.update(resource_profile_path=str(profile),resource_profile_sha256=sha(profile));write(session/'ledger.json',ledger)
   if a.stage=='measure':ledger['status']='profile_frozen'
   else:
    runner=DELIVERY/'external_baselines/run_transactions_t1_matrix.py'
    ledger['t1_runner_sha256']=sha(runner)
    r=command('03_t1_all',[QPY,'-B',runner,'--stage','all','--delivery-root',DELIVERY,'--external-work-root',WORK,'--train-root',a.train_root,
        '--qdfl-python',QPY,'--mccg-python',MPY,'--device-index',a.device_index,'--resource-profile',profile,
        '--test-root',a.test_root,'--sues-root',a.sues_root,'--sues-manifest',a.sues_manifest])
    ledger['status']='t1_all_completed';ledger['t1_result']=r
 except BaseException as e:
  ledger.update(status='stopped',error_type=type(e).__name__,error=str(e));write(session/'ledger.json',ledger);raise
 write(session/'ledger.json',ledger)
 result={'status':ledger['status'],'ledger_path':str(session/'ledger.json'),'plan_path':str(plan)}
 if 'resource_profile_path' in ledger:result['resource_profile_path']=ledger['resource_profile_path']
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
