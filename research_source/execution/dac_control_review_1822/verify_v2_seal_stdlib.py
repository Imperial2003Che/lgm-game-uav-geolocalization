"""Read-only verification of the final author seal; writes only our separate receipt."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

OUT=Path(__file__).resolve().parent
V2=OUT.parent/'dac_training_control_v2'
V1=OUT.parent/'dac_training_preparation_v1'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def require(value,message):
    if not value:raise AssertionError(message)

review_path=OUT/'V2_RECHECK.json';review=read(review_path)
manifest_path=V2/'PREPARATION_MANIFEST.json';manifest=read(manifest_path)
checks=[]
require(manifest['schema']=='dac-control-preparation.v2' and manifest['status']=='prepared_not_registered','Unexpected final preparation scope')
require(review['passed']==review['total']==58 and not review['scientific_import_attempts'] and not review['author_files_changed_during_test'],'Independent review does not match final 58-check result')
for name,digest in review['final_source_sha256'].items():
    require(sha(V2/name)==digest,'Code changed after independent review: '+name)
    checks.append({'kind':'independently_reviewed_source','path':name,'sha256':digest})
seen=set()
for row in manifest['files']:
    path=(V2/row['path']).resolve()
    require(path.is_relative_to(V2.resolve()) and row['path'] not in seen,'Seal has escaped or duplicate path')
    seen.add(row['path'])
    require(path.stat().st_size==row['bytes'] and sha(path)==row['sha256'],'Sealed payload changed: '+row['path'])
    checks.append({'kind':'sealed_payload','path':row['path'],'sha256':row['sha256']})
required={'dac2_contracts.py','dac2_gates.py','run_dac_stage.py','TRUSTED_CPU_EXECUTION.json','CONTROL_VALIDATION.json','validate_control_stdlib.py','seal_control.py','README.md','HANDOFF.md'}
require(required.issubset(seen),'Required code, QA, documentation or trusted evidence absent from seal')
require(len(manifest['files'])==manifest['payload_files'] and sum(row['bytes'] for row in manifest['files'])==manifest['payload_bytes'],'Payload summary mismatch')
for row in manifest['external_evidence']:
    path=Path(row['path'])
    require(path.stat().st_size==row['bytes'] and sha(path)==row['sha256'],'External evidence changed: '+str(path))
    checks.append({'kind':'external_evidence','path':str(path),'sha256':row['sha256']})
require(manifest['validation']['independent_passed']==manifest['validation']['independent_total']==58,'Seal records outdated independent test count')
require(manifest['validation']['stdlib_passed']==manifest['validation']['stdlib_total'],'Author tests not all passed')
qa=read(V2/'CONTROL_VALIDATION.json')
require(qa['status']=='passed' and qa['passed']==qa['total']==manifest['validation']['stdlib_total'],'Author validation summary mismatches seal')
for name,digest in qa['source_files_sha256'].items():require(sha(V2/name)==digest,'Author tested source differs from sealed source')
require(manifest['validation']['real_win32_helpers_tested'] is True and manifest['validation']['real_win32_expected_exit_cases']==[0,7],'Real Windows evidence omitted')
require(sha(V1/'PREPARATION_MANIFEST.json')=='169a6eb7c351acc7e291b4ceefdecebda2c80ad70b46a20eeed6d42d14e72bc9','Original science manifest changed')
for row in read(V1/'PREPARATION_MANIFEST.json')['files']:
    require(sha(V1/row['path'])==row['sha256'],'Original scientific preparation changed')
for field in ('active_queue_plan_release_status_written','scientific_code_modified','new_scientific_imports_executed_by_this_preparation','gpu_resource_profile_executed','training_executed'):
    require(manifest[field] is False,'Preparation overclaims execution: '+field)
report={'schema':'dac-v2-independent-seal-verification.v1','status':'passed','verified_utc':datetime.now(timezone.utc).isoformat(),
    'manifest_path':str(manifest_path),'manifest_sha256':sha(manifest_path),'manifest_bytes':manifest_path.stat().st_size,
    'independent_review_sha256':sha(review_path),'independent_checks':58,'author_stdlib_checks':qa['total'],
    'payload_files':manifest['payload_files'],'payload_bytes':manifest['payload_bytes'],'external_evidence_count':len(manifest['external_evidence']),
    'verified_entries':checks,'v1_payload_unchanged':True,'actual_scientific_imports':[],'process_or_gpu_launched':False,
    'active_plans_or_status_changed_by_reviewer':False,'review_files_in_seal_left_unchanged':True,
    'execution_scope':'Control preparation reviewed and sealed; no actual GPU resource profile/training or experiment scores produced'}
path=OUT/'V2_SEAL_VERIFICATION.json'
path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':'passed','manifest_sha256':report['manifest_sha256'],'payload_files':manifest['payload_files'],'external_evidence':report['external_evidence_count'],'report':str(path)},ensure_ascii=False))
