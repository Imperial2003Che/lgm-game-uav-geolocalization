param([ValidateSet('primary','pipeline','extensions','latest')][string]$Stage)
$ErrorActionPreference='Stop'
$executionRoot='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$incidentRoot=Join-Path $executionRoot 'memory_recovery_20260914_1300'
$pythonPath='C:\项目\.venvs\lgm-baselines\Scripts\python.exe'
$definitions=@{
 primary=@('status.json','continue_formal_matrix.py','controller_pid','running')
 pipeline=@('pipeline_status.json','supervise_pipeline.py','supervisor_pid','waiting_for_primary')
 extensions=@('extension_status.json','supervise_extensions.py','supervisor_pid','waiting_for_pipeline')
 latest=@('latest_baseline_status.json','supervise_latest_baselines.py','supervisor_pid','waiting_for_registered_extensions')
}
if (-not (Test-Path -LiteralPath (Join-Path $incidentRoot 'checkpoint_verification.json'))) { throw 'Missing checkpoint verification.' }
$verified=Get-Content -LiteralPath (Join-Path $incidentRoot 'checkpoint_verification.json') -Raw | ConvertFrom-Json
if ($verified.status -ne 'verified_complete_epoch_67') { throw 'Checkpoint not verified.' }
if ($Stage -eq 'primary') {
 if (@(Get-CimInstance Win32_Process -Filter "Name='python.exe'").Count -ne 0) { throw 'Python process remains.' }
} else {
 $predecessor=@{pipeline='primary';extensions='pipeline';latest='extensions'}[$Stage]
 $definition=$definitions[$predecessor]
 $previous=Get-Content -LiteralPath (Join-Path $executionRoot $definition[0]) -Raw | ConvertFrom-Json
 if ($previous.status -ne $definition[3]) { throw "Predecessor is not ready: $($previous.status)" }
 if (-not (Get-Process -Id $previous.($definition[2]) -ErrorAction SilentlyContinue)) { throw 'Predecessor process missing.' }
}
$current=$definitions[$Stage]
$statePath=Join-Path $executionRoot $current[0]
$old=Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
$oldPidProcess=Get-CimInstance Win32_Process -Filter ('ProcessId='+$old.($current[2]))
if ($oldPidProcess) {
 $oldEnded=if ($old.stopped_utc) {[DateTimeOffset]::Parse($old.stopped_utc)} else {[DateTimeOffset]::Parse($old.finished_utc)}
 if ($oldPidProcess.CreationDate.ToUniversalTime() -le $oldEnded.UtcDateTime) { throw 'Old controller may still be alive.' }
 $oldPidProcess | Select-Object ProcessId,ParentProcessId,CreationDate,Name,CommandLine | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $incidentRoot ($Stage+'_pid_reuse.json')) -Encoding UTF8
}
if ($Stage -ne 'primary') {
 foreach ($job in $old.jobs) {
  if ($job.status -ne 'pending' -or $job.pid -or $job.started_utc) { throw 'A downstream job has started; cannot reset its state.' }
 }
}
$preserved=Join-Path (Join-Path $incidentRoot 'controllers') $current[0]
if ((Get-FileHash -LiteralPath $statePath).Hash -ne (Get-FileHash -LiteralPath $preserved).Hash) { throw 'Status differs from incident backup.' }
$archivePath=Join-Path $incidentRoot ('retired_'+$current[0])
$resolvedSource=[IO.Path]::GetFullPath($statePath)
$resolvedTarget=[IO.Path]::GetFullPath($archivePath)
if (-not $resolvedSource.StartsWith($executionRoot+'\',[StringComparison]::OrdinalIgnoreCase) -or -not $resolvedTarget.StartsWith($incidentRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Archive path outside verified workspace.' }
Move-Item -LiteralPath $statePath -Destination $archivePath
$arguments='-B "'+(Join-Path $executionRoot $current[1])+'"'
if ($Stage -eq 'primary') { $arguments+=' --stage all --workers 8' }
$stdout=Join-Path $incidentRoot ($Stage+'.stdout.log')
$stderr=Join-Path $incidentRoot ($Stage+'.stderr.log')
$env:PYTHONIOENCODING='utf-8'
$started=Start-Process -FilePath $pythonPath -ArgumentList $arguments -WorkingDirectory $executionRoot -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
[ordered]@{stage=$Stage;time=(Get-Date -Format o);launcher_pid=$started.Id;python=$pythonPath;arguments=$arguments;stdout=$stdout;stderr=$stderr;retired_state=$archivePath} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $incidentRoot ($Stage+'_launch.json')) -Encoding UTF8
Write-Output "Launched $Stage PID $($started.Id). Check new status before next stage."
