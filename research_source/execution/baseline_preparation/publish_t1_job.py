"""Freeze a CPU-validated T1 command for the parent's serial GPU supervisor."""
from pathlib import Path
import json,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
import profile_transactions_resources as probe
def main():
 result=probe.load(P/'CPU_VALIDATION.json');assert result['status']=='passed' and result['gpu_executed'] is False
 plan=Path(probe.load(P/'v3_resource_measurements/latest_prepared_plan.json')['plan_path'])
 assert result['plan_sha256']==probe.sha(plan)
 body=probe.load(plan);assert body['profiler_sha256']==probe.sha(P/'profile_transactions_resources.py')
 paths=list(P.glob('*.py'))+[P/'CPU_VALIDATION.json',P/'qdfl_cpu_import_preflight.json',P/'mccg_cpu_import_preflight.json',P/'compatibility_v3/registration.json',plan,Path(body['static_audit_path'])]
 paths+=list((P/'compatibility_v3/delivery/external_baselines').glob('*.py'))
 paths+=list((P/'compatibility_v3/delivery/external_baselines').glob('*.json'))
 paths+=list((P/'compatibility_v3/work/patched_sources').glob('*.patch_manifest.json'))
 sues_manifest=Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\manifests\sues200_official_train_ids.yaml')
 paths.append(sues_manifest)
 command=[body['qdfl_python'],'-B',str(P/'run_t1_extension.py'),'--stage','all','--plan',str(plan),
          '--train-root',body['train_root'],'--device-index',str(body['device_index']),
          '--test-root',r'C:\项目\IMTMN\datasets\University-1652\test',
          '--sues-root',r'C:\项目\IMTMN\datasets\SUES-200','--sues-manifest',str(sues_manifest)]
 job={'id':'t1_v3_native_resource_profile_then_7fits_70eval','command':command,'cwd':str(P),
      'source_sha256':{str(p.resolve()):probe.sha(p) for p in sorted(set(paths))},
      'status_at_registration':'CPU validated; awaiting serial GPU resource measurement; no measured profile or formal T1 result yet',
      'execution_gate':'Only after earlier GPU jobs finish. All five configurations require measured complete optimizer-step proofs before the seven-fit T1 matrix is unlocked.',
      'scope':'Full original 7-fit / 70-evaluation matrix in isolated compatibility v3; 120/160/200 original epochs unchanged.',
      'resource_adaptation_notice':'A smaller QDFL-framework microbatch changes batch-local mining and is reported as resource-adapted.',
      'cpu_validation_path':str(P/'CPU_VALIDATION.json')}
 probe.write(P/'t1_job.json',job)
 print(json.dumps({'status':'job_frozen_awaiting_gpu','job_path':str(P/'t1_job.json'),'job_sha256':probe.sha(P/'t1_job.json'),'pinned_file_count':len(job['source_sha256'])},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
