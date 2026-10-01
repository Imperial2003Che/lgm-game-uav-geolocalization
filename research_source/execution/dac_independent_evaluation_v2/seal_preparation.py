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
    patches.extend(difflib.unified_diff((old/before).read_text('utf-8').splitlines(keepends=True),(HERE/after).read_text('utf-8').splitlines(keepends=True),fromfile='camp_independent_evaluation_v3/'+before,tofile='dac_independent_evaluation_v2/'+after))
(HERE/'SOURCE_DERIVATION.patch').write_text(''.join(patches),encoding='utf-8')
validation=json.loads((HERE/'STDLIB_VALIDATION.json').read_text('utf-8'))
if validation['pass_count']!=validation['check_count']:raise RuntimeError('Validation failed')
focused=json.loads((HERE/'V2_FOCUSED_VALIDATION.json').read_text('utf-8'))
if focused['pass_count']!=focused['check_count']:raise RuntimeError('Focused validation failed')
review_path=HERE.parent/'dac_evaluation_review_1923/ROOT_V2_RECHECK.json'
review=json.loads(review_path.read_text('utf-8'))
if review['status']!='passed' or review['count']!=26 or not all(row['passed'] is True for row in review['checks']):raise RuntimeError('Independent review is not passed')
for path,digest in review['source_files'].items():
    if sha(path)!=digest:raise RuntimeError('Reviewed adapter source changed: '+path)
old_manifest=HERE.parent/'dac_independent_evaluation_v1/PREPARATION_MANIFEST.json'
if sha(old_manifest)!='5a65d21c005771a98f9b28716cba775cc15f45b436246544926b14be5a799049':raise RuntimeError('Sealed v1 manifest changed')
for row in json.loads(old_manifest.read_text('utf-8'))['files']:
    path=old_manifest.parent/row['path']
    if sha(path)!=row['sha256'] or path.stat().st_size!=row['bytes']:raise RuntimeError('Sealed v1 payload changed')
files=[]
for path in sorted(HERE.iterdir()):
    if path.is_file():files.append({'path':path.name,'bytes':path.stat().st_size,'sha256':sha(path)})
manifest={'schema':'dac-independent-evaluation-preparation.v2','created_utc':datetime.now(timezone.utc).isoformat(),'status':'prepared_source_only_not_registered','files':files,'stdlib_pass_count':validation['pass_count'],'stdlib_check_count':validation['check_count'],'focused_pass_count':focused['pass_count'],'focused_check_count':focused['check_count'],'independent_review':{'path':str(review_path),'bytes':review_path.stat().st_size,'sha256':sha(review_path),'passed':26,'total':26},'prior_v1_manifest_sha256':sha(old_manifest),'task_count':30,'seeds':[1,2,3],'model_state_count':402,'source_pin_count':112,'scientific_imports':[],'model_loaded':False,'gpu_executed':False,'future_checkpoint_sha256':None,'prepared_contract_created':False,'active_release_created':False,'queue_registered':False,'runtime_status_created':False,'training_executor_binding':'Late-bound at prepare using external exact execution_spec and PREPARATION_MANIFEST SHA values; actual completion API required at bind.'}
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'manifest':str(manifest_path),'sha256':sha(manifest_path),'file_count':len(files)}))
