"""Preserve current interruption and register reviewed v2; do not launch any queue."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
EXEC=HERE.parent
PYTHON=Path(r'C:\项目\.venvs\lgm-baselines\Scripts\python.exe')
REGISTRAR=EXEC/'register_independent_comparisons_v2.py'
REGISTRAR_SHA='cb8166e8fc6366ba76a5a96c2f0b45f067c5a027429f042e04c9e7bad5ec73f5'
TRAIN_SHA='d7ba4f15a076131b464cb39a04ec869444a8e4711348929c6233e8f083df0dc2'
EVAL_SHA='305c2b9b56fb6bde1781f459467a6718b9f7ed1df9779bcc7d4a209ca2244317'

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    assert sha(REGISTRAR)==REGISTRAR_SHA
    review=read(EXEC/'registration_v2_review/FIXED_REVIEW.json')
    assert review['status']=='passed' and review['reviewed_sha256']==REGISTRAR_SHA and review['check_count']==37
    assert sha(EXEC/'camp_training_execution_v2/execution_plan.json')==TRAIN_SHA
    assert sha(EXEC/'camp_independent_evaluation_v3/preparations/frozen_three_seed_final_v3/manifest.json')==EVAL_SHA
    blockers=[EXEC/'independent_comparison_plan_v2.json',EXEC/'independent_comparison_registration_v2.json',
        HERE/'registration_v2_transaction.json',EXEC/'independent_comparison_status.json',
        EXEC/'camp_training_execution_v2/release.json',EXEC/'camp_independent_evaluation_v3/controller_release.json']
    assert not any(p.exists() for p in blockers),'Existing registration or transaction must be reviewed'
    evidence=HERE/'main_failure_1544'
    evidence.mkdir(exist_ok=False)
    primary=read(EXEC/'status.json')
    assert primary['status']=='failed' and primary['active']['exit_code']==1
    run=Path(primary['active']['output_dir'])
    files=[EXEC/n for n in ('status.json','pipeline_status.json','extension_status.json','latest_baseline_status.json',
        'independent_comparison_plan.json','extension_plan.json','latest_baseline_plan.json','continue_formal_matrix.py')]
    files += [run/n for n in ('history.json','run_config.json','run_manifest.json','run.log','process_stdout.log','process_stderr.log')]
    files += [EXEC/'memory_recovery_20260914_1424'/n for n in ('primary.stderr.log','primary.stdout.log',
        'pipeline.stderr.log','pipeline.stdout.log','extensions.stderr.log','extensions.stdout.log','latest.stderr.log','latest.stdout.log')]
    records=[]
    for index,p in enumerate(files):
        assert p.is_file(),str(p)
        target=evidence/f'{index:02d}_{p.name}'
        before=sha(p);shutil.copy2(p,target);assert sha(target)==before and sha(p)==before
        records.append({'source':str(p),'backup':str(target),'sha256':before,'bytes':p.stat().st_size})
    stderr=(run/'process_stderr.log').read_text(encoding='utf-8',errors='replace')
    assert 'error code: <1455>' in stderr
    checkpoints=[{'path':str(run/n),'bytes':(run/n).stat().st_size,'sha256':sha(run/n)} for n in ('last.pt','best.pt')]
    states={n:read(EXEC/n) for n in ('status.json','pipeline_status.json','extension_status.json','latest_baseline_status.json')}
    state_sha_before={n:sha(EXEC/n) for n in states}
    fixed_before={n:sha(EXEC/n) for n in ('independent_comparison_plan.json','extension_plan.json','latest_baseline_plan.json','continue_formal_matrix.py')}
    write(evidence/'EVIDENCE_MANIFEST.json',{'created_utc':datetime.now(timezone.utc).isoformat(),
        'status':'actual_1455_main_failure_captured_no_training_restart', 'files':records,
        'checkpoints_content_sha_only_not_deserialized':checkpoints,
        'primary_last_completed_epoch':primary['active_progress']['last_completed_epoch'],
        'primary_history_rows':primary['active_progress']['history_rows'],
        'primary_exit_code':primary['active']['exit_code'],'primary_finished_utc':primary['active']['finished_utc'],
        'states':{n:s['status'] for n,s in states.items()},'training_restart':False})
    command=[str(PYTHON),'-B',str(REGISTRAR),'--training-plan-sha',TRAIN_SHA,'--evaluation-prepared-sha',EVAL_SHA]
    for label,args in [('validation',command+['--validate-only']),('registration',command)]:
        started=datetime.now(timezone.utc).isoformat()
        with (HERE/f'{label}_v2.stdout.log').open('xb') as out,(HERE/f'{label}_v2.stderr.log').open('xb') as err:
            result=subprocess.run(args,cwd=EXEC,stdout=out,stderr=err,stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,timeout=180,check=False)
        receipt={'started_utc':started,'finished_utc':datetime.now(timezone.utc).isoformat(),
            'command':args,'exit_code':result.returncode,'registrar_sha256':sha(REGISTRAR),
            'stdout_sha256':sha(HERE/f'{label}_v2.stdout.log'),'stderr_sha256':sha(HERE/f'{label}_v2.stderr.log'),
            'no_scientific_training_launched':True}
        write(HERE/f'{label}_v2_execution_record.json',receipt)
        if result.returncode!=0:raise RuntimeError(f'{label} failed; logs and any transaction preserved; no supervisor launch attempted')
    assert sha(REGISTRAR)==REGISTRAR_SHA
    new_plan=EXEC/'independent_comparison_plan_v2.json'
    plan=read(new_plan);receipt=read(EXEC/'independent_comparison_registration_v2.json')
    transaction=read(HERE/'registration_v2_transaction.json')
    assert receipt['status']=='registered_not_launched' and transaction['status']=='registered_not_launched'
    assert receipt['plan_sha256']==sha(new_plan)
    assert not (EXEC/'independent_comparison_status.json').exists()
    assert plan['jobs'][0]==read(EXEC/'independent_comparison_plan.json')['jobs'][0]
    assert all(sha(EXEC/n)==value for n,value in state_sha_before.items())
    assert all(sha(EXEC/n)==value for n,value in fixed_before.items())
    for row in receipt['new_releases']:assert sha(row['path'])==row['sha256']
    write(HERE/'REGISTRATION_COMPLETED_NOT_LAUNCHED.json',{'created_utc':datetime.now(timezone.utc).isoformat(),
        'status':'registered_not_launched_due_to_failed_predecessor_chain',
        'plan':str(new_plan),'plan_sha256':sha(new_plan),'receipt':str(EXEC/'independent_comparison_registration_v2.json'),
        'receipt_sha256':sha(EXEC/'independent_comparison_registration_v2.json'),
        'transaction_sha256':sha(HERE/'registration_v2_transaction.json'),
        'new_releases':receipt['new_releases'],'unchanged_matched_release_sha256':receipt['unchanged_matched_release_sha256'],
        'old_plan_sha256':sha(EXEC/'independent_comparison_plan.json'),
        'main_and_first_three_successor_state_hashes_unchanged':state_sha_before,
        'frozen_control_and_plan_hashes_unchanged':fixed_before,
        'independent_status_file_exists':False,'new_supervisor_started':False,'new_pid':None,
        'reason_not_launched':'Primary failed at 15:44:50 with Windows1455 after35completeepochs; pipeline/extension/latest supervisors interrupted. Root explicitly deferred training recovery for current full-paper request.',
        'automatic_restart_performed':False,'scientific_imports':[]})
    print(json.dumps({'status':'registered_not_launched','plan_sha256':sha(new_plan),
        'new_releases':receipt['new_releases'],'main_status':'failed','completed_epochs':35}))

if __name__=='__main__':main()
