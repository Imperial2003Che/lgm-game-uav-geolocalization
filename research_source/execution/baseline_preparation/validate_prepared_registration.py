"""CPU-only structural and command validation for the isolated T1 handoff."""
from pathlib import Path
import argparse,ast,hashlib,json,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
import profile_transactions_resources as probe
def sha(p):return probe.sha(p)
def load(p):return probe.load(p)
def main():
 plan_path=Path(load(P/'v3_resource_measurements/latest_prepared_plan.json')['plan_path'])
 plan=load(plan_path);delivery=Path(plan['delivery_root']);work=Path(plan['external_work_root'])
 q,m,t=probe.modules(delivery)
 results={'status':'running','gpu_executed':False,'checks':[]}
 for p in P.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
 results['checks'].append('all preparation Python syntax parsed')
 assert sha(P/'profile_transactions_resources.py')==plan['profiler_sha256']
 assert sha(plan['environment_lock_path'])==plan['environment_lock_sha256']
 assert sha(plan['static_audit_path'])==plan['static_audit_sha256']
 body=dict(plan);claimed=body.pop('payload_sha256');assert q.canonical_object_sha256(body)==claimed
 results['checks'].append('latest v3 plan, profiler, static audit and environment lock hashes verified')
 matrix=t.validate_matrix(delivery/'external_baselines/transactions_t1_matrix.json')
 t.validate_environment_lock(delivery/'external_baselines/transactions_environment_lock.json',delivery/'external_baselines')
 original=probe.DEFAULT_DELIVERY/'external_baselines/run_transactions_t1_matrix.py'
 expected=original.read_text(encoding='utf-8').replace('MCCG_SOURCE_DIR = "mccg-e1c51b01-adapter-v2"','MCCG_SOURCE_DIR = "mccg-e1c51b01-adapter-v3"')
 old='''            QDFL_WEIGHT_ARGUMENTS[weight_id],
            str((weights / WEIGHT_FILES[weight_id]).resolve()),'''
 new='''            *[value for init_id, argument in QDFL_WEIGHT_ARGUMENTS.items()
              for value in (argument, str((weights / WEIGHT_FILES[init_id]).resolve()))],'''
 assert expected.count(old)==1
 assert expected.replace(old,new)==(delivery/'external_baselines/run_transactions_t1_matrix.py').read_text(encoding='utf-8')
 results['checks'].append('derived runner differs only in MCCG v3 binding and four-weight eager-import binding')
 for sid,old_name,new_name in [('qdfl',t.QDFL_SOURCE_DIR,t.QDFL_SOURCE_DIR),('mccg','mccg-e1c51b01-adapter-v2',t.MCCG_SOURCE_DIR)]:
  for root,name in [(probe.DEFAULT_WORK,old_name),(work,new_name)]:
   source=root/'patched_sources'/name;q.verify_patched_source(source,source.with_name(name+'.patch_manifest.json'),expected_source_id=sid)
 m.validate_published_recipe(work/'patched_sources'/t.MCCG_SOURCE_DIR)
 before=(probe.DEFAULT_WORK/'patched_sources/mccg-e1c51b01-adapter-v2/train.py').read_text(encoding='utf-8')
 after=(work/'patched_sources'/t.MCCG_SOURCE_DIR/'train.py').read_text(encoding='utf-8')
 assert before.replace('import random\nimport torch\n','import random\nimport numpy as np\nimport torch\n')==after
 results['checks'].append('original frozen sources intact, isolated sources pass patch manifests, only explicit NumPy import in MCCG')
 config_fixture={'configs':{key:{'micro_batch_size':n,'workers':0} for key,n in probe.NOMINAL.items()}}
 args=argparse.Namespace(delivery_root=delivery,external_work_root=work,train_root=Path(plan['train_root']),device_index=0,qdfl_python=Path(plan['qdfl_python']),mccg_python=Path(plan['mccg_python']))
 commands=[]
 for row in matrix['runs']:
  argv=t.build_fit_command(args,row,config_fixture,P/'command_only_fixture')
  if row['framework']=='qdfl':
   for flag in t.QDFL_WEIGHT_ARGUMENTS.values():assert argv.count(flag)==1
  else:
   assert any(t.MCCG_SOURCE_DIR in value for value in argv)
  commands.append({'run_id':row.get('run_id',row.get('id')),'argv':argv})
 assert len(commands)==7
 results['checks'].append('seven fit commands bind selected source and all required import-time initialization arguments')
 for name in ['qdfl_cpu_import_preflight.json','mccg_cpu_import_preflight.json']:
  r=load(P/name);assert r['status']=='passed' and r['cuda_initialized'] is False and r['gpu_executed'] is False
 results['checks'].append('two isolated locked-interpreter native import checks passed without CUDA initialization')
 results['boundary_self_test']=probe.self_test()
 assert results['boundary_self_test']['cuda_imported'] is False
 results.update(status='passed',plan_path=str(plan_path),plan_sha256=sha(plan_path),validated_fit_command_count=len(commands),
                matrix_sha256=sha(delivery/'external_baselines/transactions_t1_matrix.json'),
                preparation_sources_sha256={str(p):sha(p) for p in P.glob('*.py')})
 probe.write(P/'CPU_VALIDATION.json',results)
 probe.write(P/'cpu_fit_command_validation.json',{'purpose':'command assembly verification only; no profile measurements and no commands executed','commands':commands})
 registration=load(P/'compatibility_v3/registration.json')
 registration.update(status='registered_cpu_validated_awaiting_cuda_measurement',cpu_validation_path=str(P/'CPU_VALIDATION.json'),cpu_validation_sha256=sha(P/'CPU_VALIDATION.json'),producer_path=str(P/'prepare_mccg_v3_registration.py'),producer_sha256=sha(P/'prepare_mccg_v3_registration.py'))
 probe.write(P/'compatibility_v3/registration.json',registration)
 print(json.dumps(results,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
