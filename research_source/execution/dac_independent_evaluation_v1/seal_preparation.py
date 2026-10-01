"""Seal source-only preparation; no prepared evaluation or active release."""
from datetime import datetime,timezone
import difflib
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
manifest_path=HERE/'PREPARATION_MANIFEST.json'
if manifest_path.exists():raise RuntimeError('Preparation already sealed; do not overwrite')
old=HERE.parent/'camp_independent_evaluation_v3'
patches=[]
for before,after in [('protocol.py','protocol.py'),('run_evaluation.py','run_evaluation.py'),('camp_independent_model.py','dac_independent_model.py')]:
    patches.extend(difflib.unified_diff((old/before).read_text('utf-8').splitlines(keepends=True),(HERE/after).read_text('utf-8').splitlines(keepends=True),fromfile='camp_independent_evaluation_v3/'+before,tofile='dac_independent_evaluation_v1/'+after))
(HERE/'SOURCE_DERIVATION.patch').write_text(''.join(patches),encoding='utf-8')
validation=json.loads((HERE/'STDLIB_VALIDATION.json').read_text('utf-8'))
if validation['pass_count']!=validation['check_count']:raise RuntimeError('Validation failed')
files=[]
for path in sorted(HERE.iterdir()):
    if path.is_file():files.append({'path':path.name,'bytes':path.stat().st_size,'sha256':sha(path)})
manifest={'schema':'dac-independent-evaluation-preparation.v1','created_utc':datetime.now(timezone.utc).isoformat(),'status':'prepared_source_only_not_registered','files':files,'stdlib_pass_count':validation['pass_count'],'stdlib_check_count':validation['check_count'],'task_count':30,'seeds':[1,2,3],'model_state_count':402,'source_pin_count':112,'scientific_imports':[],'model_loaded':False,'gpu_executed':False,'future_checkpoint_sha256':None,'prepared_contract_created':False,'active_release_created':False,'queue_registered':False,'runtime_status_created':False,'training_executor_binding':'Late-bound at prepare using external exact execution_spec and PREPARATION_MANIFEST SHA values; actual completion API required at bind.'}
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'manifest':str(manifest_path),'sha256':sha(manifest_path),'file_count':len(files)}))
