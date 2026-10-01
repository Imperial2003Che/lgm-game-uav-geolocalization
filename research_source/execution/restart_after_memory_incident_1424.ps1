param([Parameter(Mandatory=$true)][ValidateSet('primary','pipeline','extensions','latest','independent')][string]$Stage)
$ErrorActionPreference='Stop'
$executionRoot='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$incidentRoot=Join-Path $executionRoot 'memory_recovery_20260914_1424'
$pythonPath='C:\项目\.venvs\lgm-baselines\Scripts\python.exe'
function Convert-ExactTimestamp($Value) {
 if($Value -is [DateTime]) {return [DateTimeOffset]$Value}
 return [DateTimeOffset]::Parse([string]$Value)
}
$definitions=@{
 primary=@('status.json','continue_formal_matrix.py','controller_pid','running')
 pipeline=@('pipeline_status.json','supervise_pipeline.py','supervisor_pid','waiting_for_primary')
 extensions=@('extension_status.json','supervise_extensions.py','supervisor_pid','waiting_for_pipeline')
 latest=@('latest_baseline_status.json','supervise_latest_baselines.py','supervisor_pid','waiting_for_registered_extensions')
 independent=@('independent_comparison_status.json','supervise_independent_comparisons.py','supervisor_pid','waiting_for_latest_baselines')
}
$verified=Get-Content -LiteralPath (Join-Path $incidentRoot 'checkpoint_verification.json') -Raw|ConvertFrom-Json
if ($verified.status -ne 'verified_complete_epoch_18' -or $verified.cuda_initialized) {throw 'Checkpoint not verified.'}
$liveCheck=Get-Content -LiteralPath (Join-Path $incidentRoot 'isolated_environment_live_check.json') -Raw|ConvertFrom-Json
if ($liveCheck.status -ne 'passed_live_isolated_environment_probe' -or $liveCheck.scientific_modules_after_legacy_import.Count) {throw 'Live environment isolation not verified.'}
if ((Get-FileHash -LiteralPath (Join-Path $executionRoot 'continue_formal_matrix.py')).Hash.ToLower() -ne $liveCheck.new_controller_sha256) {throw 'Verified wrapper changed.'}
$pins=@{
 'extension_plan.json'='13ef69f90ef105db4e55a463532fd6ed38f573b3dbe8cd345fd64176318e46be'
 'latest_baseline_plan.json'='80acc8d9eeb2f4fa15b6ff242c0a64acc180edf2386268aa277d55ffe58c6b1e'
 'independent_comparison_plan.json'='a36388bb2a9c81b70c95ee77f7a80f57b7d43ff5c0470eee151bb1a60d9ab235'
}
foreach($key in $pins.Keys) {if((Get-FileHash -LiteralPath (Join-Path $executionRoot $key)).Hash.ToLower() -ne $pins[$key]){throw ('Frozen plan changed: '+$key)}}
foreach($key in @('supervise_pipeline.py','supervise_extensions.py','supervise_latest_baselines.py','supervise_independent_comparisons.py')) {
 if((Get-FileHash -LiteralPath (Join-Path $executionRoot $key)).Hash -ne (Get-FileHash -LiteralPath (Join-Path (Join-Path $incidentRoot 'controllers') $key)).Hash){throw ('Frozen successor changed: '+$key)}
}
if($Stage -eq 'primary'){
 if(@(Get-CimInstance Win32_Process -Filter "Name='python.exe'").Count){throw 'Python process remains; inspect before primary start.'}
 foreach($proof in $verified.reports){$original=Join-Path 'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\runs\formal_main\university1652\visual_style\seed_2' ([IO.Path]::GetFileName($proof.file));if((Get-FileHash -LiteralPath $original).Hash.ToLower() -ne $proof.sha256){throw 'Live checkpoint changed since verification.'}}
}else{
 $predecessor=@{pipeline='primary';extensions='pipeline';latest='extensions';independent='latest'}[$Stage]
 $definition=$definitions[$predecessor]
 $previous=Get-Content -LiteralPath (Join-Path $executionRoot $definition[0]) -Raw|ConvertFrom-Json
 if($previous.status -ne $definition[3]){throw ('Predecessor not ready: '+$previous.status)}
 $owner=Get-CimInstance Win32_Process -Filter ('ProcessId='+$previous.($definition[2]))
 if(-not $owner -or $owner.Name -ne 'python.exe' -or $owner.CommandLine -notlike ('*'+$definition[1]+'*')){throw 'Predecessor identity mismatch.'}
 $recordedStart=if($previous.supervisor_started_utc){Convert-ExactTimestamp $previous.supervisor_started_utc}else{Convert-ExactTimestamp $previous.started_utc}
 $actualStart=[DateTimeOffset]$owner.CreationDate
 if($actualStart -gt $recordedStart -or ($recordedStart-$actualStart).TotalSeconds -gt 60){throw 'Predecessor PID creation time mismatch.'}
}
$current=$definitions[$Stage]
$statePath=Join-Path $executionRoot $current[0]
$old=Get-Content -LiteralPath $statePath -Raw|ConvertFrom-Json
$oldOwner=Get-CimInstance Win32_Process -Filter ('ProcessId='+$old.($current[2]))
if($oldOwner){
 $oldEnded=if($old.stopped_utc){Convert-ExactTimestamp $old.stopped_utc}else{Convert-ExactTimestamp $old.finished_utc}
 if(([DateTimeOffset]$oldOwner.CreationDate) -le $oldEnded){throw 'Old controller may still be alive.'}
 $oldOwner|Select-Object ProcessId,CreationDate,Name,CommandLine|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $incidentRoot ($Stage+'_pid_reuse.json')) -Encoding utf8
}
if($Stage -ne 'primary'){
 foreach($job in $old.jobs){if($job.status -ne 'pending' -or $job.pid -or $job.started_utc){throw 'A successor job started; cannot recreate waiting state.'}}
}
$preserved=Join-Path (Join-Path $incidentRoot 'controllers') $current[0]
if((Get-FileHash -LiteralPath $statePath).Hash -ne (Get-FileHash -LiteralPath $preserved).Hash){throw 'State differs from preserved failed incident.'}
$archivePath=Join-Path $incidentRoot ('retired_'+$current[0])
$resolvedSource=[IO.Path]::GetFullPath($statePath);$resolvedTarget=[IO.Path]::GetFullPath($archivePath)
if(-not $resolvedSource.StartsWith($executionRoot+'\',[StringComparison]::OrdinalIgnoreCase) -or -not $resolvedTarget.StartsWith($incidentRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'State archival outside verified workspace.'}
if(Test-Path -LiteralPath $archivePath){throw 'Retired state already exists; inspect before retry.'}
Move-Item -LiteralPath $statePath -Destination $archivePath
$arguments='-B "'+(Join-Path $executionRoot $current[1])+'"'
if($Stage -eq 'primary'){$arguments+=' --stage all --workers 8'}
if($Stage -eq 'independent'){$arguments+=' --plan "'+(Join-Path $executionRoot 'independent_comparison_plan.json')+'"'}
$stdout=Join-Path $incidentRoot ($Stage+'.stdout.log');$stderr=Join-Path $incidentRoot ($Stage+'.stderr.log')
$env:PYTHONIOENCODING='utf-8'
$started=Start-Process -FilePath $pythonPath -ArgumentList $arguments -WorkingDirectory $executionRoot -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
[ordered]@{stage=$Stage;time=(Get-Date).ToString('o');launcher_pid=$started.Id;python=$pythonPath;arguments=$arguments;stdout=$stdout;stderr=$stderr;retired_state=$archivePath;checkpoint_proof='checkpoint_verification.json';isolation_proof='isolated_environment_live_check.json'}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $incidentRoot ($Stage+'_launch.json')) -Encoding utf8
Write-Output ('Launched '+$Stage+' launcher '+$started.Id+'; verify actual state before next stage.')
