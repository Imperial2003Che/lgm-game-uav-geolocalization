"""Seal preparation-only source/diffs and new synthetic results; no runtime gates."""
from pathlib import Path
import difflib
import hashlib
import json
import datetime as dt

HERE=Path(__file__).absolute().parent
def sha(data):return hashlib.sha256(data).hexdigest()
def binding(path):
    raw=path.read_bytes();return {'path':str(path),'bytes':len(raw),'sha256':sha(raw)}
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')
def difference(before,after,path=''):
    if isinstance(before,dict) and isinstance(after,dict):
        result=[]
        for key in sorted(before.keys()|after.keys()):
            keypath=path+'/'+key
            if key not in before:result.append({'path':keypath,'operation':'add','after':after[key]})
            elif key not in after:result.append({'path':keypath,'operation':'remove','before':before[key]})
            else:result.extend(difference(before[key],after[key],keypath))
        return result
    if isinstance(before,list) and isinstance(after,list) and len(before)==len(after):
        return [row for index,(a,b) in enumerate(zip(before,after)) for row in difference(a,b,path+'/'+str(index))]
    return [] if before==after else [{'path':path,'operation':'replace','before':before,'after':after}]

def main():
    contract=read(HERE/'RECOVERY_CONTRACT.json')
    for item in contract['live_state_bindings']:
        assert binding(Path(item['path']))==item
    assert not (HERE/'runtime_attempt').exists()
    assert not (HERE.parent/'latest_baseline_gpu.lock').exists()
    original=read(HERE/'captured_pipeline_status.json');seed=read(HERE/'pipeline_seed.json')
    assert original['jobs'][:6]==seed['jobs'][:6]
    semantic={'schema':'t6-seed-semantic-diff.v1','original_exact_bytes':binding(HERE/'captured_pipeline_status.json'),
        'derived_bytes':binding(HERE/'pipeline_seed.json'),'changes':difference(original,seed),
        'first_six_json_objects_equal':True,'limits':'Entire original bytes preserved; derivative serialized text differs.'}
    write(HERE/'PIPELINE_STATE_SEMANTIC_DIFF.json',semantic)
    for old,new,name in [(HERE/'rejected_pre_review_v1/pipeline_recovery_candidate.py',HERE/'pipeline_recovery_candidate.py','PRE_REVIEW_TO_FINAL_SOURCE_DIFF.patch'),
                         (HERE/'rejected_pre_review_v1/prepare_contract_failed_path.py',HERE/'prepare_contract.py','PREPARE_CONTRACT_PATH_CORRECTION.patch')]:
        diff=''.join(difflib.unified_diff(old.read_text(encoding='utf-8').splitlines(True),new.read_text(encoding='utf-8').splitlines(True),fromfile=str(old),tofile=str(new)))
        with (HERE/name).open('x',encoding='utf-8',newline='\n') as stream:stream.write(diff)
    controls=read(HERE/'synthetic_control_a1/REPORT.json')
    assert controls['status']=='passed' and controls['checks']==75
    assert binding(HERE/'pipeline_recovery_candidate.py')==controls['candidate_source']
    files=['pipeline_recovery_candidate.py','start_pipeline_recovery_candidate.ps1','prepare_contract.py',
       'check_preparation.py','seal_preparation.py','RECOVERY_CONTRACT.json','captured_pipeline_status.json',
       'pipeline_seed.json','PIPELINE_STATE_DERIVATION.patch','PIPELINE_STATE_SEMANTIC_DIFF.json',
       'PRE_REVIEW_TO_FINAL_SOURCE_DIFF.patch','PREPARE_CONTRACT_PATH_CORRECTION.patch','README.md','POWERSHELL_SYNTAX.json']
    manifest={'schema':'t6-pipeline-recovery-source-manifest.v1','created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
       'status':'preparation_only_not_released_not_executed','candidate_files':[binding(HERE/name) for name in files],
       'input_contract':binding(HERE/'RECOVERY_CONTRACT.json'),'scientific_sources_modified':False,
       'required_root_adoption_schema':'t6-pipeline-recovery-source-adoption.v1',
       'required_release_schema':'t6-pipeline-recovery-release.v1'}
    write(HERE/'SOURCE_MANIFEST.json',manifest)
    report={'schema':'t6-pipeline-recovery-preparation-report.v1','created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
       'status':'prepared_pending_independent_static_review_and_root_adoption_no_release',
       'scope':'only original pipeline stage7; primary and successors untouched',
       'source_manifest':binding(HERE/'SOURCE_MANIFEST.json'),'input_bindings':len(contract['input_bindings']),
       'new_synthetic_controls':binding(HERE/'synthetic_control_a1/REPORT.json'),'synthetic_checks':75,
       'controls_actual_execution':'check_preparation.py first execution exit0, all external runtime dependencies mocked',
       'state_derivation':binding(HERE/'PIPELINE_STATE_SEMANTIC_DIFF.json'),
       'source_correction_diff':binding(HERE/'PRE_REVIEW_TO_FINAL_SOURCE_DIFF.patch'),
       'rejected_draft':binding(HERE/'rejected_pre_review_v1/pipeline_recovery_candidate.py'),
       'rejected_draft_preservation':'Actual on-disk pre-edit Copy-Item snapshot, SHA observed before fixes; not reconstructed.',
       'preparation_path_rejection':binding(HERE/'rejected_pre_review_v1/PREPARATION_PATH_FAILURE.json'),
       'real_pipeline_launch':False,'real_native_probe':False,'real_gpu_admission':False,
       'live_state_or_intent_or_retirement_mutation':False,'live_lock_creation_or_acquisition':False,
       'root_release_created':False,'T6_scientific_complete':False,
       'final_five_live_state_bindings':contract['live_state_bindings'],
       'explicit_remaining_preconditions':['Independent final source static review and root adoption.',
         'Separately reviewed persistent shared GPU lock initialization; currently absent.',
         'Fresh bounded root release; none generated outside isolated synthetic fixtures.',
         'All real native/source/process/boot/state/GPU/commit/lock/output gates must pass at future execution.'],
       'limits':['Synthetic tests do not establish actual Windows process monitoring, GPU exclusivity, resource admission or successful launch.',
         'Supervisor byte-lock transfer is cooperative, not atomic protection against uncooperative writers.',
         'Polling can miss short-lived descendants; captured handles only certify their own identities.',
         'Guardian kill/host crash releases OS locks; next launch must reject surviving science by actual process scan.',
         'T6 artifacts and actual controller completion must receive separate acceptance before any successor starts.']}
    write(HERE/'PREPARATION_REPORT.json',report)
    delivery={'schema':'t6-recovery-preparation-delivery.v1','created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
       'source_manifest':binding(HERE/'SOURCE_MANIFEST.json'),'preparation_report':binding(HERE/'PREPARATION_REPORT.json'),
       'synthetic_controls':binding(HERE/'synthetic_control_a1/REPORT.json'),
       'interpretation':'Source preparation only; no release/runtime/native/scientific success.'}
    write(HERE/'DELIVERY.json',delivery)
    print(json.dumps(delivery,ensure_ascii=False))

if __name__=='__main__':main()
