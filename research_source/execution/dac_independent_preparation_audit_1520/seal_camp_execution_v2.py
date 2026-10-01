"""Seal the checked v2 execution binding, without a release or supervisor."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
EXEC=HERE.parent
NEW=EXEC/'camp_training_execution_v2'
OLD=EXEC/'camp_training_execution'

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    if (NEW/'PREPARATION_MANIFEST.json').exists():raise RuntimeError('Immutable preparation already sealed')
    checks={}
    old_plan=read(OLD/'execution_plan.json')
    plan=read(NEW/'execution_plan.json')
    validation=read(NEW/'CPU_VALIDATION.json')
    assert validation['status']=='passed' and len(validation['checks'])==30
    assert validation['scientific_libraries_imported'] is False and validation['real_children_started']==0
    checks['all_30_prior_execution_control_fixtures_passed_for_new_binding']=True
    assert validation['preparation']['manifest_sha256']=='12747158ce2647474c6d24688ba3ebb872ac137118fab7aefd1c1e0ecfad40ec'
    checks['validation_binds_exact_repaired_v2_preparation']=True
    expected={'contracts.py':{'camp_training_preparation_v2':'camp_training_preparation',
        '12747158ce2647474c6d24688ba3ebb872ac137118fab7aefd1c1e0ecfad40ec':'61f4eacc883421c08a5accd32c58c51c3a1a2287bcd5b146c1f1f270abd6b8fd'},
        'supervise_training.py':{'camp_training_inputs_v2':'camp_training_inputs'},
        'validate_cpu.py':{'camp_training_inputs_v2':'camp_training_inputs'},'run_stage.py':{}}
    for filename,mapping in expected.items():
        before=ast.parse((OLD/filename).read_text(encoding='utf-8'))
        after=ast.parse((NEW/filename).read_text(encoding='utf-8'))
        for n in ast.walk(after):
            if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value in mapping:n.value=mapping[n.value]
        assert ast.dump(before,include_attributes=False)==ast.dump(after,include_attributes=False),filename
        checks['only_allowed_path_hash_literals_changed_'+filename]=True
        assert sha(NEW/filename)==plan['execution_code_sha256'][filename]
    for path,value in old_plan['environment_records_sha256'].items():assert sha(path)==value
    assert old_plan['environment_records_sha256']==plan['environment_records_sha256']
    checks['all_70_environment_records_unchanged']=len(plan['environment_records_sha256'])
    old_manifest=read(OLD/'PREPARATION_MANIFEST.json')
    for row in old_manifest['files']:assert sha(OLD/row['path'])==row['sha256']
    for row in old_plan['seeds']:assert sha(row['plan_path'])==row['plan_sha256']
    checks['all_v1_execution_payloads_and_seed_plans_unchanged']=True
    for row in plan['seeds']:
        assert row['plan_path'].find('camp_training_inputs_v2')>=0
        assert sha(row['plan_path'])==row['plan_sha256']
        new_seed=read(row['plan_path'])
        old_seed=read(EXEC/'camp_training_inputs'/f"seed_{row['seed']}_plan.json")
        old_seed['created_utc']=new_seed['created_utc']
        old_seed['code_manifest']['adapter']['camp_train_runtime.py']='3cbf41ddef34fba1bb1a57f5eca287129748708abb21941f63ff9a5ac40d9b26'
        assert old_seed==new_seed
        assert not any(Path(row[k]).exists() for k in ('output_directory','profile_directory','training_receipt_directory'))
    checks['three_seed_plans_only_rebind_one_runtime_sha_no_scientific_changes']=True
    checks['all_future_profile_train_receipt_directories_absent']=True
    assert not (NEW/'status.json').exists() and not (NEW/'release.json').exists()
    checks['no_live_status_or_release_created']=True
    rows=[{'path':name,'bytes':(NEW/name).stat().st_size,'sha256':sha(NEW/name)} for name in
        ('contracts.py','CPU_VALIDATION.json','README.md','run_stage.py','supervise_training.py','validate_cpu.py')]
    record={'schema':'camp-independent-training-execution-preparation.v1','status':'prepared_not_registered',
        'sealed_utc':datetime.now(timezone.utc).isoformat(),'preparation_revision':'v2_observer_parent_signature_fix',
        'upstream_preparation_manifest_sha256':plan['preparation_manifest_sha256'],'files':rows,
        'original_execution_manifest_sha256':sha(OLD/'PREPARATION_MANIFEST.json'),
        'execution_plan_sha256':sha(NEW/'execution_plan.json'),
        'actual_resource_profiles':0,'actual_training_runs':0,'active_release_created':False,
        'scientific_modules_imported':False,'gpu_calls':False,'revision_checks':checks,
        'derivation_record':{'path':str(HERE/'CAMP_EXECUTION_V2_DERIVATION.json'),
            'sha256':sha(HERE/'CAMP_EXECUTION_V2_DERIVATION.json')}}
    write(NEW/'PREPARATION_MANIFEST.json',record)
    handoff={'status':'prepared_not_registered','execution_directory':str(NEW),
        'execution_plan_path':str(NEW/'execution_plan.json'),'execution_plan_sha256':sha(NEW/'execution_plan.json'),
        'execution_preparation_manifest_sha256':sha(NEW/'PREPARATION_MANIFEST.json'),
        'training_preparation_manifest_sha256':plan['preparation_manifest_sha256'],
        'seeds':plan['seeds'],'execution_code_sha256':plan['execution_code_sha256'],
        'cpu_checks':30,'additional_binding_checks':len(checks),
        'native_configuration_unchanged':True,'registered':False,'active_release_created':False,
        'old_execution_and_seed_files_unchanged':True,
        'next':'Independent evaluator must bind this execution plan/status and these seed plan SHAs; root registers a new successor. No future checkpoint SHA exists yet.'}
    write(HERE/'CAMP_EXECUTION_V2_HANDOFF.json',handoff)
    print(json.dumps({'execution_plan_sha256':handoff['execution_plan_sha256'],
        'execution_preparation_manifest_sha256':handoff['execution_preparation_manifest_sha256'],
        'additional_binding_checks':len(checks),'registered':False}))

if __name__=='__main__':main()
