"""Create a separate compatibility registration; never edit the original delivery."""
from pathlib import Path
import sys,json,hashlib,shutil,difflib
P=Path(__file__).resolve().parent
ORIGINAL=Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724')
WORK=Path(r'C:\项目\LGM-GAME-External-Baseline-Work')
DEST=P/'compatibility_v3'
sys.dont_write_bytecode=True;sys.path.insert(0,str(ORIGINAL))
from external_baselines.qdfl_adapter import verify_patched_source, canonical_object_sha256
from external_baselines.fetch_and_verify_sources import canonical_tree_hash,sha256_file
from external_baselines.mccg_adapter import validate_published_recipe
from external_baselines.run_transactions_t1_matrix import validate_matrix,validate_environment_lock

def put(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')

def main():
 if DEST.exists():raise SystemExit('Compatibility destination already exists; preserve it and inspect registration.json.')
 delivery=DEST/'delivery';work=DEST/'work';patched=work/'patched_sources'
 shutil.copytree(ORIGINAL/'external_baselines',delivery/'external_baselines',ignore=shutil.ignore_patterns('__pycache__','audits','tests'))
 shutil.copy2(ORIGINAL/'TRANSACTIONS_EXTENSION_PROTOCOL.md',delivery/'TRANSACTIONS_EXTENSION_PROTOCOL.md')
 (delivery/'TRANSACTIONS_EXTENSION_PROTOCOL.md').open('a',encoding='utf-8').write('\n\nCompatibility registration 2026-09-14: MCCG adapter source v3 adds the missing explicit NumPy import required by the already registered deterministic seed. Network, loss, optimizer, sampling, schedule, initialization, seeds, final-epoch selection and seven-fit/70-task matrix are unchanged. This registration is isolated from the original v2 delivery and results.\n')
 manifests={}
 for old,new in [('qdfl-627296d5-adapter-v4','qdfl-627296d5-adapter-v4'),('mccg-e1c51b01-adapter-v2','mccg-e1c51b01-adapter-v3')]:
  source=WORK/'patched_sources'/old;origin_manifest=source.with_name(old+'.patch_manifest.json')
  sid='mccg' if old.startswith('mccg') else 'qdfl'
  manifest=verify_patched_source(source,origin_manifest,expected_source_id=sid)
  destination=patched/new;shutil.copytree(source,destination)
  manifest['destination']=str(destination.resolve());manifest['parent_patch_manifest_path']=str(origin_manifest);manifest['parent_patch_manifest_sha256']=sha256_file(origin_manifest)
  if sid=='mccg':
   f=destination/'train.py';before=f.read_text(encoding='utf-8');oldtext='import random\nimport torch\n';newtext='import random\nimport numpy as np\nimport torch\n'
   assert before.count(oldtext)==1 and 'import numpy as np' not in before
   after=before.replace(oldtext,newtext);beforehash=sha256_file(f);f.write_text(after,encoding='utf-8',newline='\n')
   spec={'relative_path':'train.py','old':oldtext,'new':newtext,'expected_count':1,'rationale':'Explicitly import NumPy for the existing deterministic np.random.seed call; no method or recipe change.'}
   manifest['patches'].append({'relative_path':'train.py','before_sha256':beforehash,'after_sha256':sha256_file(f),'replacement_count':1,'rationale':spec['rationale']})
   manifest['patch_plan_sha256']=canonical_object_sha256({'parent_plan_sha256':manifest['patch_plan_sha256'],'compatibility_patch':spec})
   (DEST/'mccg_v2_to_v3.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='v2/train.py',tofile='v3/train.py')),encoding='utf-8')
   validate_published_recipe(destination)
  tree,count=canonical_tree_hash(destination);manifest.update(patched_tree_sha256=tree,patched_file_count=count)
  path=destination.with_name(new+'.patch_manifest.json');put(path,manifest);verify_patched_source(destination,path,expected_source_id=sid)
  manifests[sid]={'source_root':str(destination),'manifest_path':str(path),'manifest_sha256':sha256_file(path),'source_tree_sha256':tree}
 runner=delivery/'external_baselines/run_transactions_t1_matrix.py';before=runner.read_text(encoding='utf-8');assert before.count('MCCG_SOURCE_DIR = "mccg-e1c51b01-adapter-v2"')==1
 after=before.replace('MCCG_SOURCE_DIR = "mccg-e1c51b01-adapter-v2"','MCCG_SOURCE_DIR = "mccg-e1c51b01-adapter-v3"');runner.write_text(after,encoding='utf-8',newline='\n')
 (DEST/'runner_v3_binding.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='original/run_transactions_t1_matrix.py',tofile='compatibility_v3/run_transactions_t1_matrix.py')),encoding='utf-8')
 # All QDFL backbones import the DINOv2 module, whose path dictionary is eager.
 # Bind all already registered paths even when only FSRA/SDPL/CCR is selected.
 before_binding=after
 old_binding='''            QDFL_WEIGHT_ARGUMENTS[weight_id],
            str((weights / WEIGHT_FILES[weight_id]).resolve()),'''
 new_binding='''            *[value for init_id, argument in QDFL_WEIGHT_ARGUMENTS.items()
              for value in (argument, str((weights / WEIGHT_FILES[init_id]).resolve()))],'''
 assert after.count(old_binding)==1
 after=after.replace(old_binding,new_binding);runner.write_text(after,encoding='utf-8',newline='\n')
 (DEST/'qdfl_import_weight_binding.patch').write_text(''.join(difflib.unified_diff(before_binding.splitlines(True),after.splitlines(True),fromfile='v3_before_binding/run_transactions_t1_matrix.py',tofile='v3/run_transactions_t1_matrix.py')),encoding='utf-8')
 lock_path=delivery/'external_baselines/transactions_environment_lock.json';lock=json.loads(lock_path.read_text(encoding='utf-8'))
 names={'qdfl_adapter':'qdfl_adapter.py','mccg_adapter':'mccg_adapter.py','source_patching':'source_patching.py','source_registry':'transactions_baseline_registry.json','weight_registry':'transactions_weight_registry.json'}
 for key,name in names.items():
  path=delivery/'external_baselines'/name;lock['registered_artifacts'][key]={'path':str(path.resolve()),'bytes':path.stat().st_size,'sha256':sha256_file(path)}
 lock['compatibility_revision']={'parent_lock_path':str(ORIGINAL/'external_baselines/transactions_environment_lock.json'),'parent_lock_sha256':sha256_file(ORIGINAL/'external_baselines/transactions_environment_lock.json'),
   'change':'MCCG v3 explicit NumPy seed import; isolated path rebinding. Package distributions unchanged.',
   'additional_fix':'Bind all registered QDFL initialization paths for eager DINOv2 import; selected configuration and actually loaded weights are unchanged.',
   'runner_path':str(runner),'runner_sha256':sha256_file(runner),'source_manifests':manifests}
 lock.pop('payload_sha256');lock['payload_sha256']=canonical_object_sha256(lock);put(lock_path,lock)
 validate_environment_lock(lock_path,delivery/'external_baselines');validate_matrix(delivery/'external_baselines/transactions_t1_matrix.json')
 report={'status':'cpu_registration_created_weights_link_pending','delivery_root':str(delivery),'external_work_root':str(work),'source_manifests':manifests,'runner_sha256':sha256_file(runner),
  'environment_lock_sha256':sha256_file(lock_path),'matrix_unchanged_sha256':sha256_file(delivery/'external_baselines/transactions_t1_matrix.json'),'original_delivery_untouched':True,
  'weights_link_path':str(work/'weights'),'weights_link_target':str(WORK/'weights'),'gpu_executed':False}
 assert report['matrix_unchanged_sha256']==sha256_file(ORIGINAL/'external_baselines/transactions_t1_matrix.json')
 put(DEST/'registration.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
