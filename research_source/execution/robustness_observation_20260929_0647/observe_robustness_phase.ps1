$ErrorActionPreference='Stop'
$e=Split-Path -Parent $PSScriptRoot
$r=Join-Path $e 'host_recovery_20260929_0341'
$dest=Join-Path $PSScriptRoot ('snapshot_'+(Get-Date -Format yyyyMMdd_HHmmssfff))
[IO.Directory]::CreateDirectory($dest)|Out-Null
$bindings=[Collections.Generic.List[object]]::new()
function Bind([string]$p){$i=Get-Item -LiteralPath $p;[ordered]@{path=$i.FullName;sha256=(Get-FileHash -LiteralPath $p).Hash.ToLower();bytes=$i.Length}}
function Seal([string]$name,[string]$s){$p=Join-Path $dest $name;$b=[Text.UTF8Encoding]::new($false).GetBytes($s);$f=[IO.File]::Open($p,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read);try{$f.Write($b,0,$b.Length)}finally{$f.Dispose()};$p}
function CaptureJson([string]$path,[string]$name){$s=[IO.File]::ReadAllText($path);$p=Seal $name $s;$bindings.Add([ordered]@{source=$path;snapshot=(Bind $p)});ConvertFrom-Json -InputObject $s -DateKind String}
function Tokens([string]$s){@([regex]::Matches($s,'"([^"\r\n]*)"|([^"\s]+)')|ForEach-Object{if($_.Groups[1].Success){$_.Groups[1].Value}else{$_.Groups[2].Value}})}
function Same($a,$b){if($a.Count -ne $b.Count){return $false};for($i=0;$i -lt $a.Count;$i++){if($a[$i] -cne $b[$i]){return $false}};$true}
function Proc($p){[ordered]@{pid=$p.ProcessId;parent=$p.ParentProcessId;creation=([DateTimeOffset]$p.CreationDate).ToString('o');creation_utc_ticks=([DateTimeOffset]$p.CreationDate).UtcTicks;command=$p.CommandLine}}
function FindPid([int]$n){$a=@($all|Where-Object ProcessId -eq $n);if($a.Count -ne 1){throw "Expected one live PID $n"};$a[0]}
function Pair($launcher,[int]$parent,$command){if($launcher.ParentProcessId -ne $parent -or -not(Same @(Tokens $launcher.CommandLine) @($command))){throw 'Launcher command or parent mismatch'};$children=@($all|Where-Object {$_.ParentProcessId -eq $launcher.ProcessId -and $_.Name -eq 'python.exe'});if($children.Count -ne 1){throw 'Expected one Python interpreter child'};$expected=@($command);$expected[0]='C:\Users\17703\AppData\Local\Programs\Python\Python311\python.exe';if(-not(Same @(Tokens $children[0].CommandLine) $expected)){throw 'Interpreter command mismatch'};@((Proc $launcher),(Proc $children[0]))}
function LogMeta([string]$path){$i=Get-Item -LiteralPath $path;[ordered]@{path=$i.FullName;bytes=$i.Length;last_write_utc=$i.LastWriteTimeUtc.ToString('o');tail=@(Get-Content -LiteralPath $path -Tail 6)}}
try {
 $firstPath=Join-Path $r 'OWNER_SNAPSHOT_20260929_040832626.json'
 $firstBinding=Bind $firstPath
 if($firstBinding.sha256 -ne '8b54506101ec62a4542414e32e21d9ab458bd0ec0ea66158f27276142d0736eb'){throw 'Initial identity snapshot SHA mismatch'}
 $first=Get-Content -LiteralPath $firstPath -Raw|ConvertFrom-Json -DateKind String
 $primary=CaptureJson (Join-Path $e 'status.json') 'primary_status.json'
 if($primary.status -ne 'completed' -or $null -ne $primary.active){throw 'Primary is not completed/inactive'}
 $defs=@(
 @('pipeline','pipeline_status.json','running_post_training'),
 @('extensions','extension_status.json','waiting_for_pipeline'),
 @('latest','latest_baseline_status.json','waiting_for_registered_extensions'),
 @('independent','independent_comparison_status.json','waiting_for_latest_baselines'))
 $states=@{};foreach($d in $defs){$states[$d[0]]=CaptureJson (Join-Path $e $d[1]) $d[1]}
 $ledgerPath='C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\runs\frozen_robustness_matrix_ledger.json'
 $ledger=CaptureJson $ledgerPath 'frozen_robustness_matrix_ledger.json'
 $helper=Join-Path $PSScriptRoot 'check_robustness_contract.py'
 $helperBinding=Bind $helper
 $contractText=& 'C:\Users\17703\AppData\Local\Programs\Python\Python311\python.exe' -I -B $helper (Join-Path $dest 'frozen_robustness_matrix_ledger.json')
 if($LASTEXITCODE -ne 0){throw 'Read-only stdlib contract helper rejected snapshot'}
 $contract=$contractText|ConvertFrom-Json -DateKind String
 if($contract.passed -ne $true){throw 'Robustness metadata contract failed'}
 $contractPath=Seal 'CONTRACT.json' ($contract|ConvertTo-Json -Depth 20)
 $all=@(Get-CimInstance Win32_Process)
 $cimTime=(Get-Date).ToString('o')
 $priorPrimary=@($first.states|Where-Object role -eq 'primary')[0]
 if($primary.controller_pid -ne $priorPrimary.owner.pid){throw 'Primary completed state owner mismatch'}
 $primaryPresence=@($all|Where-Object {$_.ProcessId -in @($priorPrimary.owner.pid,$priorPrimary.launcher.pid)})
 if($primaryPresence.Count){throw 'Old primary PID present; identity/exit needs review'}
 $rows=@()
 foreach($d in $defs){
  $role=$d[0];$state=$states[$role];if($state.status -ne $d[2]){throw "Phase changed for $role : $($state.status); inspect fresh state"}
  $old=@($first.states|Where-Object role -eq $role)[0]
  if($state.supervisor_pid -ne $old.owner.pid){throw 'Owner state PID differs from first identity'}
  $owner=FindPid $old.owner.pid;$launcher=FindPid $old.launcher.pid
  foreach($which in @(@($owner,$old.owner),@($launcher,$old.launcher))){
   if(([DateTimeOffset]$which[0].CreationDate).UtcTicks -ne [long]$which[1].creation_utc_ticks -or $which[0].CommandLine -cne $which[1].command -or $which[0].ParentProcessId -ne $which[1].parent){throw 'Live owner/launcher identity mismatch'}
  }
  if($owner.ParentProcessId -ne $launcher.ProcessId){throw 'Owner parent mismatch'}
  $age=([DateTimeOffset]::Now-[DateTimeOffset]::Parse($state.heartbeat_utc)).TotalSeconds
  if($age -lt -5 -or $age -gt 120){throw "Heartbeat stale for $role"}
  $launch=Get-Content -LiteralPath (Join-Path $r ($role+'_launch.json')) -Raw|ConvertFrom-Json -DateKind String
  $retry=Join-Path $e ("state_io_retry_20260920_v2\io_retry_"+$role+"_"+$owner.ProcessId+".jsonl")
  $rows += [ordered]@{role=$role;status=$state.status;heartbeat_utc=$state.heartbeat_utc;heartbeat_age_seconds=$age;owner=(Proc $owner);launcher=(Proc $launcher);jobs=@($state.jobs|ForEach-Object{[ordered]@{id=$_.id;status=$_.status}});stderr=(LogMeta $launch.stderr);retry=if(Test-Path -LiteralPath $retry){LogMeta $retry}else{@{path=$retry;exists=$false}}}
 }
 $pipe=$states.pipeline
 $active=@($pipe.jobs|Where-Object status -eq 'running')
 if($active.Count -ne 1 -or $active[0].id -ne 'robustness'){throw 'Active pipeline stage changed; inspect new phase'}
 $entryBinding=Bind $active[0].command[1]
 if($entryBinding.sha256 -ne $active[0].entrypoint_sha256){throw 'Stage entrypoint SHA mismatch'}
 $stagePair=Pair (FindPid $active[0].pid) $pipe.supervisor_pid $active[0].command
 $expectedStage=@('C:\项目\.venvs\lgm-baselines\Scripts\python.exe','C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\experiments\run_frozen_robustness_matrix.py','--delivery-root','C:\项目\LGM-GAME-Partner-Delivery-20260724','--university-root','C:\项目\IMTMN\datasets\University-1652','--sues-root','C:\项目\IMTMN\datasets\SUES-200','--python','C:\项目\.venvs\lgm-baselines\Scripts\python.exe','--stage','run')
 if(-not(Same @($active[0].command) $expectedStage)){throw 'Original robustness stage command mismatch'}
 if($entryBinding.sha256 -ne $ledger.immutable_config.source_hashes.orchestrator){throw 'Stage/ledger source mismatch'}
 $priorT3=@($pipe.jobs|Where-Object id -eq 'cross_dataset_transfer')
 if($priorT3.Count -ne 1 -or $priorT3[0].status -ne 'completed' -or $priorT3[0].exit_code -ne 0){throw 'T3 parent completion record unavailable'}
 $running=@($ledger.runs.PSObject.Properties|Where-Object {$_.Value.status -eq 'running'})
 if($running.Count -ne 1){throw 'Robustness between jobs or changed; retain partial snapshot and inspect again'}
 $taskId=$running[0].Name;$task=$running[0].Value
 $registry=@($ledger.immutable_config.registered_runs|Where-Object identifier -CEQ $taskId)
 if($registry.Count -ne 1){throw 'Expected unique registered robustness task'}
 $spec=$registry[0]
 if($taskId -cne ($spec.dataset+'/'+$spec.variant+'/seed_'+$spec.seed)){throw 'Robustness identifier mismatch'}
 $attempts=@($task.attempts)
 if($attempts.Count -lt 1){throw 'Running robustness record has no attempt'}
 for($i=0;$i -lt $attempts.Count;$i++){
  $names=@($attempts[$i].PSObject.Properties.Name)
  if($i -eq $attempts.Count-1){
   if('completed_utc' -in $names -or 'returncode' -in $names){throw 'Current robustness attempt already closed; resample'}
  }elseif('completed_utc' -notin $names -or 'returncode' -notin $names){throw 'Prior robustness attempt not closed'}
 }
 $event=$attempts[-1]
 if(-not(Same @($event.command) @($spec.command))){throw 'Attempt differs from original registered command'}
 if($event.evaluator_sha256 -ne $ledger.immutable_config.source_hashes.evaluator){throw 'Attempt evaluator SHA mismatch'}
 if($task.checkpoint_status -ne 'completed_and_verified' -or @($task.checkpoint_issues).Count){throw 'Producer checkpoint readiness is not ready'}
 foreach($arg in @(@('--dataset',[string]$spec.dataset),@('--data-root',[string]$spec.data_root),@('--evidence',[string]$spec.evidence),@('--checkpoint',[string]$spec.checkpoint),@('--output-dir',[string]$spec.output_dir),@('--sues-manifest',[string]$ledger.immutable_config.sues_manifest.path))){
  $indices=@(for($j=0;$j -lt $event.command.Count;$j++){if($event.command[$j] -ceq $arg[0]){$j}})
  if($indices.Count -ne 1 -or $indices[0]+1 -ge $event.command.Count -or $event.command[$indices[0]+1] -cne $arg[1]){throw 'Robustness registered row-to-command mismatch'}
 }
 $child=@($all|Where-Object {$_.ParentProcessId -eq $stagePair[1].pid -and $_.Name -eq 'python.exe'})
 if($child.Count -ne 1){throw 'Robustness worker transition or missing child; inspect fresh observation'}
 $workerPair=Pair $child[0] $stagePair[1].pid $event.command
 if([long]$workerPair[0].creation_utc_ticks -lt ([DateTimeOffset]::Parse($event.started_utc)).UtcTicks -or [long]$workerPair[1].creation_utc_ticks -lt [long]$workerPair[0].creation_utc_ticks){throw 'Worker creation predates ledger attempt or parent'}
 if([long]$stagePair[0].creation_utc_ticks -lt ([DateTimeOffset]::Parse($active[0].started_utc)).UtcTicks -or [long]$stagePair[1].creation_utc_ticks -lt [long]$stagePair[0].creation_utc_ticks){throw 'Stage creation predates parent launch record'}
 $dataloaders=@($all|Where-Object {$_.ParentProcessId -eq $workerPair[1].pid -and $_.Name -eq 'python.exe'}|ForEach-Object{Proc $_})
 $wrapperLogDir=Join-Path (Split-Path -Parent $ledgerPath) 'frozen_robustness_orchestrator_logs'
 $logStem=$taskId.Replace('/','__')
 $scienceStdout=LogMeta (Join-Path $wrapperLogDir ($logStem+'.stdout.log'))
 $scienceStderr=LogMeta (Join-Path $wrapperLogDir ($logStem+'.stderr.log'))
 # A second read must describe the same still-active attempt; natural transition is not a science failure.
 $endPipe=CaptureJson (Join-Path $e 'pipeline_status.json') 'pipeline_status_after.json'
 $endLedger=CaptureJson $ledgerPath 'frozen_robustness_matrix_ledger_after.json'
 $endActive=@($endPipe.jobs|Where-Object status -eq 'running')
 $endRunning=@($endLedger.runs.PSObject.Properties|Where-Object {$_.Value.status -eq 'running'})
 if($endActive.Count -ne 1 -or $endActive[0].id -ne 'robustness' -or $endActive[0].pid -ne $active[0].pid -or -not(Same @($endActive[0].command) @($active[0].command))){throw 'Pipeline changed during observation; resample'}
 if($endRunning.Count -ne 1 -or $endRunning[0].Name -cne $taskId -or $endLedger.config_sha256 -ne $ledger.config_sha256){throw 'Robustness task changed during observation; resample'}
 $endAttempt=@($endRunning[0].Value.attempts)[-1]
 if($endAttempt.started_utc -cne $event.started_utc -or -not(Same @($endAttempt.command) @($event.command)) -or 'completed_utc' -in @($endAttempt.PSObject.Properties.Name) -or 'returncode' -in @($endAttempt.PSObject.Properties.Name)){throw 'Robustness attempt changed or completed during observation; resample'}
 $finalCim=@(Get-CimInstance Win32_Process)
 $expectedLive=@($rows|ForEach-Object{$_.owner;$_.launcher})+@($stagePair)+@($workerPair)
 foreach($observed in $expectedLive){
  $again=@($finalCim|Where-Object ProcessId -eq $observed.pid)
  if($again.Count -ne 1 -or ([DateTimeOffset]$again[0].CreationDate).UtcTicks -ne [long]$observed.creation_utc_ticks -or $again[0].CommandLine -cne $observed.command -or $again[0].ParentProcessId -ne $observed.parent){throw 'Process identity changed during observation; retain and resample'}
 }
 $finalCimTime=(Get-Date).ToString('o')
 $pins=@(
 @('extension_plan.json','13ef69f90ef105db4e55a463532fd6ed38f573b3dbe8cd345fd64176318e46be'),
 @('latest_baseline_plan.json','80acc8d9eeb2f4fa15b6ff242c0a64acc180edf2386268aa277d55ffe58c6b1e'),
 @('independent_comparison_plan_v2.json','a5318f7a60497cc7c9ccb74b7cd82ef7f71fcb072c36a90fb192ea27acc6ca49'),
 @('state_io_retry_20260920_v2\SOURCE_MANIFEST.json','d8e6209f5ff2c2180d053e6444cb7df6ec0846405fea7ad6dee9b76a8fcb8dfb'))
 $pinRows=@();foreach($pin in $pins){$b=Bind (Join-Path $e $pin[0]);if($b.sha256 -ne $pin[1]){throw 'Registered pin mismatch'};$pinRows+=$b}
 $mem=Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
 $report=[ordered]@{
 schema='lgm-post-primary-robustness-observation.v1';time=(Get-Date).ToString('o');cim_observed_at=$cimTime;cim_reconfirmed_at=$finalCimTime;identity_count=$expectedLive.Count;contract_helper=$helperBinding;contract_report=(Bind $contractPath);source=(Bind $PSCommandPath);first_identity=$firstBinding;raw_snapshots=@($bindings);pins=$pinRows;
 primary=[ordered]@{status=$primary.status;finished_utc=$primary.finished_utc;heartbeat_utc=$primary.heartbeat_utc;controller_pid=$primary.controller_pid;old_owner_and_launcher_absent=$true;exit_code=$null;exit_limit='No original primary process handles or parent-recorded primary exit code captured; completed state and current absence only'};
 live_roles=$rows;stage_entrypoint=$entryBinding;stage_pair=$stagePair;robustness=[ordered]@{id=$taskId;status=$task.status;attempt_ordinal_derived_from_array_length=$attempts.Count;attempt_started_utc=$event.started_utc;command=$event.command;evaluator_sha256=$event.evaluator_sha256;config_sha256=$ledger.config_sha256;ledger_updated_utc=$ledger.updated_utc;worker_pair=$workerPair;dataloader_children=$dataloaders;ledger_status_counts=@($ledger.runs.PSObject.Properties|Group-Object {$_.Value.status}|Select-Object Name,Count);counts_are_runtime_status_not_independent_acceptance=$true;checkpoint_status_is_producer_record_only=$true;stdout=$scienceStdout;stderr=$scienceStderr};
 t3_parent_completion=[ordered]@{record=$priorT3[0];numeric_pid_current_presence=@($finalCim|Where-Object ProcessId -eq $priorT3[0].pid|ForEach-Object{Proc $_});limit='Original parent Popen exit record only; no independent interpreter exit code or held handles'};
 completed_pipeline_jobs=@($pipe.jobs|Where-Object status -eq 'completed');
 commit_headroom_GiB=($mem.CommitLimit-$mem.CommittedBytes)/1GB;runtime_memory_not_stop_threshold=$true;
 limitations=@('Read-only phase and process observation; only an isolated stdlib metadata helper is executed, no science/native worker or recovery launch','Cache/checkpoint SHA and readiness are inherited producer metadata, no bytes read or scientific completion independently accepted','Wrapper logs may be open; size/time/tail are observation only, not a whole-file digest','Completed pipeline jobs are parent Popen records, not independent dual-handle exit proofs','No checkpoint reading, scientific imports, or scientific result acceptance in this observation')}
 $out=Seal 'OBSERVATION.json' ($report|ConvertTo-Json -Depth 35)
 [ordered]@{report=(Bind $out);primary=$report.primary;live_roles=@($rows|ForEach-Object{[ordered]@{role=$_.role;status=$_.status;owner=$_.owner.pid;launcher=$_.launcher.pid}});stage_pair=$stagePair;robustness_id=$taskId;worker_pair=$workerPair;commit_headroom_GiB=$report.commit_headroom_GiB}|ConvertTo-Json -Depth 12
}catch{
 $failure=Seal 'REJECTED_OBSERVATION.json' (@{time=(Get-Date).ToString('o');error=$_.ToString();source=(Bind $PSCommandPath);raw_snapshots=@($bindings);not_scientific_failure=$true}|ConvertTo-Json -Depth 15)
 Write-Output $failure;throw
}

