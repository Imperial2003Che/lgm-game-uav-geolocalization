$ErrorActionPreference='Stop'
$executionRoot='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$incidentRoot=Join-Path $executionRoot 'camp_observer_repair_20260914'
$statePath=Join-Path $executionRoot 'independent_comparison_status.json'
function Get-SharedFileHash([string]$Path) {
 $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
 $hasher=[Security.Cryptography.SHA256]::Create()
 try{return [Convert]::ToHexString($hasher.ComputeHash($stream)).ToLower()}finally{$hasher.Dispose();$stream.Dispose()}
}
$s=Get-Content -LiteralPath $statePath -Raw|ConvertFrom-Json
if($s.status -ne 'waiting_for_latest_baselines' -or $s.plan_sha256 -ne 'a36388bb2a9c81b70c95ee77f7a80f57b7d43ff5c0470eee151bb1a60d9ab235'){throw 'Unexpected independent state; inspect.'}
if($s.jobs.Count -ne 3){throw 'Unexpected job count.'}
foreach($j in $s.jobs){if($j.status -ne 'pending' -or $j.pid -or $j.started_utc){throw 'A job started; do not stop or replace this queue.'}}
$owner=Get-CimInstance Win32_Process -Filter ('ProcessId='+$s.supervisor_pid)
if(-not $owner -or $owner.Name -ne 'python.exe' -or $owner.CommandLine -notlike '*supervise_independent_comparisons.py*'){throw 'Owner mismatch.'}
$started=[DateTimeOffset]$s.supervisor_started_utc
if(([DateTimeOffset]$owner.CreationDate) -gt $started -or ($started-[DateTimeOffset]$owner.CreationDate).TotalSeconds -gt 60){throw 'Owner creation mismatch.'}
$launcher=Get-CimInstance Win32_Process -Filter ('ProcessId='+$owner.ParentProcessId)
if(-not $launcher -or $launcher.Name -ne 'python.exe' -or $launcher.CommandLine -notlike '*supervise_independent_comparisons.py*'){throw 'Launcher mismatch.'}
if(Test-Path -LiteralPath $incidentRoot){throw 'Repair directory exists; inspect before retry.'}
New-Item -ItemType Directory -Path $incidentRoot|Out-Null
New-Item -ItemType Directory -Path (Join-Path $incidentRoot 'prior')|Out-Null
$files=@('independent_comparison_plan.json','independent_comparison_status.json','independent_comparison_registration.json','register_independent_comparisons.py','supervise_independent_comparisons.py','matched_view_execution\release.json','camp_training_execution\release.json','camp_independent_evaluation\controller_release.json','camp_training_execution\execution_plan.json','camp_training_preparation\PREPARATION_MANIFEST.json','camp_independent_evaluation\preparations\frozen_three_seed_final_v2\manifest.json','memory_recovery_20260914_1424\independent_launch.json','memory_recovery_20260914_1424\independent.stdout.log','memory_recovery_20260914_1424\independent.stderr.log')
$records=@()
foreach($n in $files){$src=Join-Path $executionRoot $n;$dst=Join-Path (Join-Path $incidentRoot 'prior') $n;New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($dst)) -Force|Out-Null;Copy-Item -LiteralPath $src -Destination $dst;$digest=Get-SharedFileHash $src;if((Get-SharedFileHash $dst) -ne $digest){throw 'Backup mismatch.'};$records+=[ordered]@{source=$src;backup=$dst;sha256=$digest;bytes=(Get-Item -LiteralPath $src).Length}}
$records|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $incidentRoot 'backup_manifest.json') -Encoding utf8
[ordered]@{time=(Get-Date).ToString('o');reason='Confirmed unstarted CAMP AverageMeter observer signature TypeError; retire only the independent waiting queue for a versioned repair.';actual_owner=($owner|Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine);launcher=($launcher|Select-Object ProcessId,CreationDate,CommandLine);all_jobs_unstarted=$true}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $incidentRoot 'pause_intent.json') -Encoding utf8
Stop-Process -Id $owner.ProcessId -ErrorAction Stop
Start-Sleep -Milliseconds 500
$remainingLauncher=Get-CimInstance Win32_Process -Filter ('ProcessId='+$launcher.ProcessId)
if($remainingLauncher -and $remainingLauncher.CreationDate -eq $launcher.CreationDate){Stop-Process -Id $launcher.ProcessId -ErrorAction Stop}
$remainingOwner=Get-CimInstance Win32_Process -Filter ('ProcessId='+$owner.ProcessId)
if($remainingOwner -and $remainingOwner.CreationDate -eq $owner.CreationDate){throw 'Own supervisor did not exit.'}
$final=Get-Content -LiteralPath $statePath -Raw|ConvertFrom-Json
foreach($j in $final.jobs){if($j.status -ne 'pending' -or $j.pid -or $j.started_utc){throw 'Unexpected state changed during pause.'}}
$archivePath=Join-Path $incidentRoot 'retired_independent_comparison_status.json'
$srcFull=[IO.Path]::GetFullPath($statePath);$dstFull=[IO.Path]::GetFullPath($archivePath)
if(-not $srcFull.StartsWith($executionRoot+'\',[StringComparison]::OrdinalIgnoreCase) -or -not $dstFull.StartsWith($incidentRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Retirement path outside verified workspace.'}
Move-Item -LiteralPath $statePath -Destination $archivePath
[ordered]@{status='paused_unstarted_for_versioned_observer_repair';time=(Get-Date).ToString('o');retired_state=$archivePath;retired_state_sha256=(Get-FileHash -LiteralPath $archivePath).Hash.ToLower();main_and_other_successors_untouched=$true;stopped_owner=$owner.ProcessId;stopped_launcher=$launcher.ProcessId}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $incidentRoot 'pause_completed.json') -Encoding utf8
Write-Output 'Only unstarted independent waiting queue stopped; failure evidence and prior registration retained.'
