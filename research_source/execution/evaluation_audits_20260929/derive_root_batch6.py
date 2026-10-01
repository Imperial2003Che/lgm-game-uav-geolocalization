from pathlib import Path
import difflib
ex=Path(__file__).parent.parent
old=ex/'evaluation_audits_20260928/adopt_batch10.ps1'
out=Path(__file__).parent/'adopt_batch6.ps1'
s=old.read_text(encoding='utf-8-sig')
changes={
"$auditRoot = Join-Path $ex 'evaluation_audits_20260928'":"$auditRoot = Join-Path $ex 'evaluation_audits_20260929'",
'batch10_20260928_133806_171727':'batch6_20260929_024917_529481',
'ROOT_BATCH10_ADOPTION_20260928.json':'ROOT_BATCH6_ADOPTION_20260929.json',
'BATCH10_EVALUATION_REVIEW.json':'BATCH6_EVALUATION_REVIEW.json',
'review_batch10.py':'review_batch6.py',
'REVIEW_BATCH10_SOURCE_DIFF.patch':'REVIEW_BATCH6_SOURCE_DIFF.patch',
'7dc08f79d974394c95c53fca990fd55b3832981d72bc0d09a2b64b53206988c8':'f2d578c904e14c99b4d5b4a00ace980d3ecca99c5ba43d2ebe6c7b228e98acf1',
'ef3a63b378d1d7846d87a5faf51a045de98b9b3b7064361c5556603167294c9e':'80bbbaf3f3f1c36ae9b6dfcf149bc2bb3ff64aede5c4e1bcb5275e37658d41f0',
'b9f321f7700adf8fcad1fc766469706ea02c6d82732d6ed6066dd3a4ae96b3e7':'c38a71b619427ea7df0ad7a43cf8ecab6b4d8fa842f0d6dc33105d248892eb97',
'1676ad826b902a0275f931834a33489d699c0690a9d5826be06401b9a62573f3':'155610032a4e1951527206ee47c4366fbb202a7c175006209913cee86902173e',
'1d2263ff8e4feba7f435b5ac3d4d0a9c7f8a7fcc6a937abe5c358a85cc3f0dd8':'1ff1a09dbeb9238f1cfd0d9655d89bc1d00700fdf5d51324e0a921a01ab624b1',
"(Join-Path $auditRoot 'ROOT_CONTENT_SEED12_ADOPTION_20260928.json')":"(Join-Path $ex 'evaluation_audits_20260928/ROOT_BATCH10_ADOPTION_20260928.json')",
'with_this_batch -ne 12':'with_this_batch -ne 18',
'with_this_batch -ne 36':'with_this_batch -ne 54',
'accepted_evaluation_run_count -ne 10':'accepted_evaluation_run_count -ne 6',
'accepted_retrieval_task_count -ne 30':'accepted_retrieval_task_count -ne 18',
'fresh_evaluation_artifact_count -ne 70':'fresh_evaluation_artifact_count -ne 42',
'Count -ne 144':'Count -ne 133',
'@($report.runs).Count -ne 10':'@($report.runs).Count -ne 6',
"$targets = @(@{variant='content';seed=3}) + @(foreach ($variant in 'style','visual','visual_content') { foreach ($seed in 1,2,3) { @{variant=$variant;seed=$seed} } })":"$targets = @(foreach ($variant in 'visual_style','full') { foreach ($seed in 1,2,3) { @{variant=$variant;seed=$seed} } })",
'accepted_evaluation_run_count=10;accepted_retrieval_task_count=30;fresh_evaluation_artifact_count=70':'accepted_evaluation_run_count=6;accepted_retrieval_task_count=18;fresh_evaluation_artifact_count=42',
'accepted_total_evaluation_runs=12;accepted_total_retrieval_tasks=36':'accepted_total_evaluation_runs=18;accepted_total_retrieval_tasks=54',
'snapshot_bindings_checked=144':'snapshot_bindings_checked=133',
'new_runs=10;new_tasks=30;total_runs=12;total_tasks=36':'new_runs=6;new_tasks=18;total_runs=18;total_tasks=54',
}
for a,b in changes.items():
    if a not in s:raise RuntimeError('Missing replacement '+a)
    s=s.replace(a,b)
start=s.index('$identities = @()')
end=s.index('$result = [ordered]@{',start)
s=s[:start]+'''$identities = @()
if($snapshot.schema -ne 'host-interruption-preservation.v2' -or -not $snapshot.old_science_and_controllers_absent){throw 'Expected sealed host-interruption snapshot'}
$boot=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().Ticks
if($boot -ne [DateTimeOffset]::Parse($snapshot.last_boot_utc).UtcTicks){throw 'Boot changed after capture'}
$oldLaunchers = @($allProcesses | Where-Object ProcessId -in 12564,7896,28100,18364,16816,31052 | Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine)
if($oldLaunchers.Count){throw 'Prior evaluation PID number now exists; inspect identity before adoption'}
$oldOwners = @($allProcesses | Where-Object ProcessId -in $snapshot.old_ids | Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine)
if($oldOwners.Count){throw 'Captured interrupted PID number now exists; inspect identity before adoption'}
if(-not $report.initial_inventory_not_used -or @($report.specific_training_report_authorities).Count -ne 6){throw 'Missing specific training authority'}
foreach($authority in $report.specific_training_report_authorities){
 Assert-File $authority.report_path $authority.report_sha256
 if($authority.PSObject.Properties.Name -contains 'historical_root_adoption'){
  Assert-File $authority.historical_root_adoption.path $authority.historical_root_adoption.sha256
  if(-not $authority.historical_root_adoption.exact_report_edge_verified){throw 'Missing exact historical authority edge'}
 }
}
''' +s[end:]
s=s.replace('current_owner_snapshot=@{','host_interruption_snapshot=@{')
s=s.replace('root_current_identities=$identities;root_old_launcher_numbers_observed=$oldLaunchers;',"root_current_identities=$identities;root_old_launcher_numbers_observed=$oldLaunchers;root_old_owner_numbers_observed=$oldOwners;current_host_boot_utc_ticks=$boot;current_live_owner_proof='none: host interrupted, recovery not yet launched';specific_training_report_authorities=$report.specific_training_report_authorities;")
if out.exists():raise RuntimeError('Do not overwrite')
out.write_text(s,encoding='utf-8')
(out.parent/'ROOT_BATCH6_SOURCE_DIFF.patch').write_text(''.join(difflib.unified_diff(old.read_text(encoding='utf-8-sig').splitlines(True),s.splitlines(True),fromfile=str(old),tofile=str(out))),encoding='utf-8')
print(str(out))
