"""One-time preparation seal only. No experiment plan, release or process launch."""
from pathlib import Path
import dac2_contracts as c

def main():
    destination=c.HERE/'PREPARATION_MANIFEST.json'
    c.require(not destination.exists(),'Control preparation already frozen; preserve it')
    qa=c.read(c.HERE/'CONTROL_VALIDATION.json')
    c.require(qa['status']=='passed' and qa['passed']==qa['total'] and not qa['scientific_imports'] and not qa['new_resource_measurements'],'Control stdlib validation incomplete')
    for name,expected in qa['source_files_sha256'].items():c.require(c.sha(c.HERE/name)==expected,'Control source changed after validation: '+name)
    c.require(set(qa['source_files_sha256'])=={p.name for p in c.HERE.glob('*.py')},'Unchecked source added after validation')
    review_root=c.EXECUTION/'dac_control_review_1822'
    review_path=review_root/'V2_RECHECK.json';review=c.read(review_path)
    c.require(review['passed']==review['total'] and review['passed']>=57 and not review['scientific_import_attempts'] and not review['author_files_changed_during_test'],'Independent control recheck incomplete')
    for name,expected in review['final_source_sha256'].items():c.require(c.sha(c.HERE/name)==expected,'Independent-reviewed source changed: '+name)
    smoke_path=review_root/'REAL_PROCESS_API_SMOKE_1822.json'
    c.require(c.sha(smoke_path)=='b36f0762835cca5934293f9a86388f9be73079e1834d07fe5cceed282a9f5cad','Real Win32 helper proof changed')
    smoke=c.read(smoke_path)
    c.require(smoke['status']=='passed','Real Win32 process helper test did not pass')
    for name,expected in smoke['source_files_sha256'].items():c.require(c.sha(c.HERE/name)==expected,'Real Win32 helper source changed')
    c.require([case['actual_worker_exit_code'] for case in smoke['cases']]==[0,7] and all(case['launcher_exit_code']==case['expected_exit_code'] and case['retained_handle_verified_running_then_actual_exit'] for case in smoke['cases']),'Real expected success/failure lifecycle cases differ')
    c.science_binding()
    anchor=c.read(c.HERE/'TRUSTED_CPU_EXECUTION.json')
    for row in anchor['files']:c.require(c.sha(row['path'])==row['sha256'],'Trusted real CPU evidence changed')
    independent_plan=c.EXECUTION/'independent_comparison_plan_v2.json'
    c.require(c.sha(independent_plan)=='a5318f7a60497cc7c9ccb74b7cd82ef7f71fcb072c36a90fb192ea27acc6ca49','Fifth registered preceding plan changed')
    rows=[]
    for path in sorted(c.HERE.rglob('*')):
        if path.is_file():
            c.require('__pycache__' not in path.parts and path.suffix!='.pyc' and not path.name.endswith('.partial'),'Unexpected generated file in control source')
            rows.append({'path':path.relative_to(c.HERE).as_posix(),'sha256':c.sha(path),'bytes':path.stat().st_size})
    dependencies=[review_path,review_root/'V2_RECHECK.md',review_root/'recheck_v2_stdlib.py',smoke_path,
        review_root/'smoke_windows_process_api_1822.py',review_root/'REAL_WINDOWS_LAUNCHER_IDENTITY.json',independent_plan,
        c.CPU_RESULT,Path(anchor['exit_receipt']['path'])]
    manifest={'schema':'dac-control-preparation.v2','status':'prepared_not_registered','prepared_utc':c.utc(),
        'files':rows,'payload_files':len(rows),'payload_bytes':sum(row['bytes'] for row in rows),
        'science_binding':c.science_binding(),'trusted_cpu_result_sha256':c.CPU_RESULT_SHA,
        'validation':{'stdlib_passed':qa['passed'],'stdlib_total':qa['total'],'independent_passed':review['passed'],'independent_total':review['total'],
            'real_win32_helpers_tested':True,'real_win32_expected_exit_cases':[0,7]},
        'external_evidence':[{'path':str(path),'sha256':c.sha(path),'bytes':path.stat().st_size} for path in dependencies],
        'active_queue_plan_release_status_written':False,'scientific_code_modified':False,
        'new_scientific_imports_executed_by_this_preparation':False,'gpu_resource_profile_executed':False,'training_executed':False,
        'pending':['Three separately frozen University seed plans','Fresh five-stage serial release after all owners exit',
            'Real native batch24 two-actual-AdamW-update DAC resource measurement','Three complete independent training runs and full-gallery final-checkpoint evaluation'],
        'profile_scope':'Resource-only discarded model; original DAC402/all3loss/native24; no current GPU measurements or research scores'}
    c.write(destination,manifest)
    for row in rows:c.require(c.sha(c.HERE/row['path'])==row['sha256'],'Payload changed during seal')
    print({'status':manifest['status'],'files':len(rows),'bytes':manifest['payload_bytes'],'manifest_sha256':c.sha(destination)})
if __name__=='__main__':main()
