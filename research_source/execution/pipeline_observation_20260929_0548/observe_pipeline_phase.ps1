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
 $t3Path='C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\evaluations\transactions_t3_transfer\transactions_t3_ledger.json'
 $t3=CaptureJson $t3Path 'transactions_t3_ledger.json'
 $all=@(Get-CimInstance Win32_Process)
 $cimTime=(Get-Date).ToString('o')
 $priorPrimary=@($first.states|Where-Object role -eq 'primary')[0]
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
 if($active.Count -ne 1 -or $active[0].id -ne 'cross_dataset_transfer'){throw 'Active pipeline stage changed; inspect new phase'}
 $entryBinding=Bind $active[0].command[1]
 if($entryBinding.sha256 -ne $active[0].entrypoint_sha256){throw 'Stage entrypoint SHA mismatch'}
 $stagePair=Pair (FindPid $active[0].pid) $pipe.supervisor_pid $active[0].command
 $running=@($t3.evaluations.PSObject.Properties|Where-Object {$_.Value.status -eq 'running'})
 if($running.Count -ne 1){throw 'T3 between jobs or changed; retain this partial snapshot and inspect again'}
 $event=@($running[0].Value.events|Where-Object status -eq 'running')[-1]
 $child=@($all|Where-Object {$_.ParentProcessId -eq $stagePair[1].pid -and $_.Name -eq 'python.exe'})
 if($child.Count -ne 1){throw 'T3 worker transition or missing child'}
 $workerPair=Pair $child[0] $stagePair[1].pid $event.command
 $dataloaders=@($all|Where-Object {$_.ParentProcessId -eq $workerPair[1].pid -and $_.Name -eq 'python.exe'}|ForEach-Object{Proc $_})
 $pins=@(
 @('extension_plan.json','13ef69f90ef105db4e55a463532fd6ed38f573b3dbe8cd345fd64176318e46be'),
 @('latest_baseline_plan.json','80acc8d9eeb2f4fa15b6ff242c0a64acc180edf2386268aa277d55ffe58c6b1e'),
 @('independent_comparison_plan_v2.json','a5318f7a60497cc7c9ccb74b7cd82ef7f71fcb072c36a90fb192ea27acc6ca49'),
 @('state_io_retry_20260920_v2\SOURCE_MANIFEST.json','d8e6209f5ff2c2180d053e6444cb7df6ec0846405fea7ad6dee9b76a8fcb8dfb'))
 $pinRows=@();foreach($pin in $pins){$b=Bind (Join-Path $e $pin[0]);if($b.sha256 -ne $pin[1]){throw 'Registered pin mismatch'};$pinRows+=$b}
 $mem=Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
 $report=[ordered]@{
 schema='lgm-post-primary-pipeline-observation.v1';time=(Get-Date).ToString('o');cim_observed_at=$cimTime;source=(Bind $PSCommandPath);first_identity=$firstBinding;raw_snapshots=@($bindings);pins=$pinRows;
 primary=[ordered]@{status=$primary.status;finished_utc=$primary.finished_utc;heartbeat_utc=$primary.heartbeat_utc;controller_pid=$primary.controller_pid;old_owner_and_launcher_absent=$true;exit_code=$null;exit_limit='No original primary process handles or parent-recorded primary exit code captured; completed state and current absence only'};
 live_roles=$rows;stage_entrypoint=$entryBinding;stage_pair=$stagePair;transfer=[ordered]@{id=$running[0].Name;status=$running[0].Value.status;worker_pair=$workerPair;dataloader_children=$dataloaders;ledger_status_counts=@($t3.evaluations.PSObject.Properties|Group-Object {$_.Value.status}|Select-Object Name,Count);counts_are_runtime_status_not_independent_acceptance=$true;stdout=(LogMeta $event.stdout_path);stderr=(LogMeta $event.stderr_path)};
 completed_pipeline_jobs=@($pipe.jobs|Where-Object status -eq 'completed');
 commit_headroom_GiB=($mem.CommitLimit-$mem.CommittedBytes)/1GB;runtime_memory_not_stop_threshold=$true;
 limitations=@('Read-only phase and process observation; no experiment launch or recovery replay','Completed pipeline jobs are parent Popen records, not independent dual-handle exit proofs','No checkpoint reading, scientific imports, or scientific result acceptance in this observation')}
 $out=Seal 'OBSERVATION.json' ($report|ConvertTo-Json -Depth 35)
 [ordered]@{report=(Bind $out);primary=$report.primary;live_roles=@($rows|ForEach-Object{[ordered]@{role=$_.role;status=$_.status;owner=$_.owner.pid;launcher=$_.launcher.pid}});stage_pair=$stagePair;transfer_id=$running[0].Name;worker_pair=$workerPair;commit_headroom_GiB=$report.commit_headroom_GiB}|ConvertTo-Json -Depth 12
}catch{
 $failure=Seal 'REJECTED_OBSERVATION.json' (@{time=(Get-Date).ToString('o');error=$_.ToString();source=(Bind $PSCommandPath);raw_snapshots=@($bindings);not_scientific_failure=$true}|ConvertTo-Json -Depth 15)
 Write-Output $failure;throw
}

