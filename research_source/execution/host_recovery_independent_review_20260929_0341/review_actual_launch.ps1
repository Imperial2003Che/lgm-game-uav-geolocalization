$ErrorActionPreference='Stop'
$ex='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$d=Join-Path $ex 'host_recovery_20260929_0341'
$observedAt=[DateTimeOffset]::Now
function Sha($p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLower()}
function ReadJ($p){Get-Content -LiteralPath $p -Raw|ConvertFrom-Json -DateKind String}
function Bind($p){[ordered]@{path=$p;bytes=(Get-Item -LiteralPath $p).Length;sha256=(Sha $p)}}
function Assert($b,$m){if(-not $b){throw $m}}
function Time($s){if($s-is [DateTime]){return [DateTimeOffset]$s};[DateTimeOffset]::Parse([string]$s)}
function Tokens($cmd){@([regex]::Matches($cmd,'"([^"\r\n]*)"|([^"\s]+)')|ForEach-Object{if($_.Groups[1].Success){$_.Groups[1].Value}else{$_.Groups[2].Value}})}
function SameTokens($a,$b){if($a.Count-ne $b.Count){return $false};for($j=0;$j-lt $a.Count;$j++){if($a[$j]-cne $b[$j]){return $false}};return $true}
$pins=@{
 'ROOT_ADOPTION_20260929.json'='b276efb7973d15d51304bd930bae13ae612c0686c06133e87fab8818f08bdfe4'
 'ACTUAL_PRIMARY_VALIDATE.json'='c51f9673788dbdb86ab15db1425fe4cb4eef435802b2c26459cd32b21b4f2da3'
 'OWNER_SNAPSHOT_20260929_040243134.json'='d62aae3e3c938b63eee99e2bf9bd3403139eac3377b1c0a59230b7f75eb5e731'
}
$bindings=@();foreach($n in $pins.Keys){$p=Join-Path $d $n;Assert ((Sha $p)-eq $pins[$n]) ('Binding changed '+$n);$bindings+=Bind $p}
$snapshot=ReadJ (Join-Path $d 'OWNER_SNAPSHOT_20260929_040243134.json')
$scienceSnapshotPath=Join-Path $PSScriptRoot 'SCIENCE_TRANSITION_20260929_0406.json'
Assert ((Sha $scienceSnapshotPath)-eq 'fb229ee2288e4a53e161b37ce5f69a2766524ef44031a0055119fa129cd63110') 'Science transition observation changed'
$scienceSnapshot=ReadJ $scienceSnapshotPath;$bindings+=Bind $scienceSnapshotPath
Assert ($scienceSnapshot.previous_event.pid-eq 20376-and $scienceSnapshot.previous_event.status-eq 'completed'-and $scienceSnapshot.previous_event.exit_code-eq 0-and $scienceSnapshot.old_pair_absent-ceq $true) 'Parent-recorded transition not confirmed'
$validation=ReadJ (Join-Path $d 'ACTUAL_PRIMARY_VALIDATE.json')
Assert ($validation.passed-ceq $true-and $validation.no_actual_launch-ceq $true-and $validation.source_sha256-eq '59deea56a6df6ee59282aa50d2612246a0b3e2cb8b9335120af8907f778fdd64') 'Actual prior validation record invalid'
$defs=@{primary=@('status.json','controller_pid','running',33924,31992,0);pipeline=@('pipeline_status.json','supervisor_pid','waiting_for_primary',14420,29784,7);extensions=@('extension_status.json','supervisor_pid','waiting_for_pipeline',30388,7584,4);latest=@('latest_baseline_status.json','supervisor_pid','waiting_for_registered_extensions',33520,12896,2);independent=@('independent_comparison_status.json','supervisor_pid','waiting_for_latest_baselines',7484,21652,3)}
$roles=@('primary','pipeline','extensions','latest','independent')
$source=Join-Path $ex 'restart_after_host_interruption_20260929_v1.ps1'
Assert ((Sha $source)-eq '59deea56a6df6ee59282aa50d2612246a0b3e2cb8b9335120af8907f778fdd64') 'Actual recovery source changed';$bindings+=Bind $source
$actualProcess=@(Get-CimInstance Win32_Process -Filter "Name='python.exe'")
$stateReviews=@();$identityChecks=@();$intents=@{};$launches=@{};$liveStates=@{}
foreach($role in $roles){
 $def=$defs[$role];$row=@($snapshot.states|Where-Object role -eq $role)[0]
 $ip=Join-Path $d ($role+'_launch_intent.json');$lp=Join-Path $d ($role+'_launch.json');$rp=Join-Path $d ('retired_'+$def[0])
 foreach($p in @($ip,$lp,$rp)){$bindings+=Bind $p}
 $intent=ReadJ $ip;$launch=ReadJ $lp;$intents[$role]=$intent;$launches[$role]=$launch
 Assert ($intent.stage-eq $role-and $launch.stage-eq $role-and $intent.script_sha256-eq (Sha $source)-and $intent.incident_capture_sha256-eq 'a19eeae091aafdab5791367590e2ac22752d9fc5b57f79c0ddaf090072ee06a0'-and $intent.recovery_mode-eq 'original_official_evaluation_after_42_complete_fits') ('Intent binding differs '+$role)
 Assert ((Time $intent.time)-le (Time $launch.time)-and $launch.launcher_pid-eq $def[4]-and $launch.retired_state-eq $rp-and $intent.archive-eq $rp) ('Launch timing/retired mismatch '+$role)
 Assert ((Sha $rp)-eq (Sha (Join-Path (Join-Path $d 'controllers') $def[0]))) ('Retired bytes differ from preserved state '+$role)
 $livePath=Join-Path $ex $def[0];$live=ReadJ $livePath;$liveStates[$role]=$live
 Assert ($live.($def[1])-eq $def[3]-and $live.status-eq $def[2]-and $live.state_io_compatibility.role-eq $role-and $live.state_io_compatibility.sha256-eq 'd8e6209f5ff2c2180d053e6444cb7df6ec0846405fea7ad6dee9b76a8fcb8dfb') ('Actual role state/owner differs '+$role)
 $heartbeat=Time $live.heartbeat_utc
 Assert (($observedAt-$heartbeat).TotalSeconds-lt 90-and $heartbeat-le [DateTimeOffset]::Now.AddSeconds(2)) ('Stale/future heartbeat '+$role)
 if($role-ne 'primary'){Assert (@($live.jobs).Count-eq $def[5]-and @($live.jobs|Where-Object status -ne 'pending').Count-eq 0) ('Successor science unexpectedly started '+$role)}
 foreach($kind in @('owner','launcher')){
  $expected=$row.$kind;$actual=@($actualProcess|Where-Object ProcessId -eq $expected.pid)
  Assert ($actual.Count-eq 1) ('Missing/duplicate actual '+$role+'/'+$kind)
  $p=$actual[0];$created=Time $p.CreationDate
  Assert ($p.ParentProcessId-eq $expected.parent-and $p.CommandLine-ceq $expected.command-and $created.UtcTicks-eq [long]$expected.creation_utc_ticks-and $created.UtcTicks-eq (Time $expected.creation).UtcTicks) ('Actual exact process differs '+$role+'/'+$kind)
  if($kind-eq 'launcher'){$apiTicks=(Time $launch.launcher_creation_time).UtcTicks;$truncated=$apiTicks-($apiTicks%10);Assert ($truncated-eq $created.UtcTicks) ('Native API/CIM creation precision differs '+$role);Assert (SameTokens (Tokens $p.CommandLine) (@($launch.python)+(Tokens $launch.arguments))) ('Launcher command record differs '+$role)}
  $identityChecks+=[ordered]@{role=$role;kind=$kind;pid=$p.ProcessId;parent=$p.ParentProcessId;creation=$created.ToString('o');creation_utc_ticks=$created.UtcTicks;command=$p.CommandLine;matched_snapshot=$true}
 }
 $err=Get-Item -LiteralPath (Join-Path $d ($role+'.stderr.log'));Assert ($err.Length-eq 0) ('Nonempty controller stderr '+$role)
 $retry=Join-Path (Join-Path $ex 'state_io_retry_20260920_v2') ('io_retry_'+$role+'_'+$def[3]+'.jsonl')
 $retryInfo=if(Test-Path -LiteralPath $retry){[ordered]@{exists=$true;path=$retry;bytes=(Get-Item -LiteralPath $retry).Length;tail=@(Get-Content -LiteralPath $retry -Tail 8)}}else{[ordered]@{exists=$false;path=$retry}}
 $stateReviews+=[ordered]@{role=$role;state=$live.status;owner=$live.($def[1]);heartbeat_utc=$live.heartbeat_utc;pending_jobs=if($role-eq 'primary'){0}else{@($live.jobs|Where-Object status -eq 'pending').Count};stderr_bytes=$err.Length;retry=$retryInfo}
}
for($i=1;$i-lt $roles.Count;$i++){
 $role=$roles[$i];$prior=$roles[$i-1];$pre=$intents[$role].predecessor;$expected=@($snapshot.states|Where-Object role -eq $prior)[0].owner
 Assert ($pre.role-eq $prior-and $pre.pid-eq $expected.pid-and (Time $pre.creation_time).UtcTicks-eq [long]$expected.creation_utc_ticks-and $pre.command-ceq $expected.command-and (Time $launches[$prior].time)-lt (Time $intents[$role].time)) ('Sequential predecessor identity differs '+$role)
}
$samples=@($intents.primary.memory_samples);Assert ($samples.Count-eq 4) 'Require four recorded actual launch memory samples'
foreach($s in $samples){Assert ([long]$s.required_headroom_bytes-eq [long]26*1GB-and [long]$s.headroom_bytes-eq ([long]$s.limit_bytes-[long]$s.commit_bytes)-and [long]$s.headroom_bytes-ge [long]26*1GB) 'Resource sample invalid'}
Assert (((Time $samples[1].time)-(Time $samples[0].time)).TotalSeconds-ge 15-and ((Time $samples[2].time)-(Time $samples[1].time)).TotalSeconds-ge 15-and (Time $samples[3].time)-lt (Time $intents.primary.time)) 'Resource sample ordering invalid'
$probe=Join-Path $ex 'environment_probes\20260929_040047_25ff0f4f36d3473cbceb141742f407ac'
$pl=ReadJ (Join-Path $probe 'launch.json');$pr=ReadJ (Join-Path $probe 'report.json');$isolation=$liveStates.primary.runtime_provenance.isolation
foreach($n in @('launch.json','report.json','stdout.log','stderr.log')){$bindings+=Bind (Join-Path $probe $n)}
Assert ($pl.pid-eq 3060-and $pl.exit_code-eq 0-and $pr.pid-eq 34284-and $pr.schema-eq 'formal-environment-subprocess.v1'-and $pr.source_sha256-eq (Sha (Join-Path $ex 'continue_formal_matrix_path_compat_v1.py'))) 'Native probe source/process mismatch'
Assert ((Time $pl.started_utc)-le (Time $pr.started_utc)-and (Time $pr.started_utc)-le (Time $pr.finished_utc)-and (Time $pr.finished_utc)-le (Time $pl.finished_utc)) 'Native probe time mismatch'
$packages=@{numpy='2.4.4';Pillow='12.2.0';torch='2.11.0+cu126';torchvision='0.26.0+cu126'}
foreach($k in $packages.Keys){Assert ($pr.runtime_provenance.packages.$k-eq $packages[$k]-and $pr.runtime_provenance.package_origins.$k.StartsWith('C:\项目\.venvs\lgm-baselines\Lib\site-packages\')) ('Native import provenance mismatch '+$k)}
Assert ($pr.runtime_provenance.executable-eq 'C:\项目\.venvs\lgm-baselines\Scripts\python.exe'-and $pr.runtime_provenance.cuda_initialized_by_guard-ceq $false-and $pr.import_environment_changes.TORCHINDUCTOR_CACHE_DIR.after-and $isolation.preserved_import_environment_keys-contains 'TORCHINDUCTOR_CACHE_DIR') 'Native probe CUDA/environment mismatch'
Assert ($isolation.probe_report-eq (Join-Path $probe 'report.json')-and $isolation.report_sha256-eq (Sha (Join-Path $probe 'report.json'))-and $isolation.launcher_pid-eq 3060-and $isolation.interpreter_pid-eq 34284-and $isolation.exit_code-eq 0-and @($isolation.controller_scientific_modules).Count-eq 0) 'Parent native probe adoption mismatch'
Assert (@(Get-CimInstance Win32_Process -Filter 'ProcessId=3060 OR ProcessId=34284').Count-eq 0) 'Native probe numeric PID now present; inspect reuse'
$sourcePins=@{'extension_plan.json'='13ef69f90ef105db4e55a463532fd6ed38f573b3dbe8cd345fd64176318e46be';'latest_baseline_plan.json'='80acc8d9eeb2f4fa15b6ff242c0a64acc180edf2386268aa277d55ffe58c6b1e';'independent_comparison_plan_v2.json'='a5318f7a60497cc7c9ccb74b7cd82ef7f71fcb072c36a90fb192ea27acc6ca49';'state_io_retry_20260920_v2\SOURCE_MANIFEST.json'='d8e6209f5ff2c2180d053e6444cb7df6ec0846405fea7ad6dee9b76a8fcb8dfb'}
foreach($n in $sourcePins.Keys){$p=Join-Path $ex $n;Assert ((Sha $p)-eq $sourcePins[$n]) ('Plan/source pin differs '+$n);$bindings+=Bind $p}
$active=$liveStates.primary.active
Assert ($active.pid-eq 33892-and $active.status-eq 'running'-and $active.command[4]-eq 'evaluate') 'Science advanced/changed during audit; capture fresh identity before adoption'
Assert (SameTokens @($active.command) @($scienceSnapshot.active.command)) 'Actual science command differs from independently captured transition'
foreach($expected in $scienceSnapshot.science){
 $rows=@($actualProcess|Where-Object ProcessId -eq $expected.pid);Assert ($rows.Count-eq 1) 'Science PID no longer present; observe transition'
 $p=$rows[0];$created=Time $p.CreationDate
 Assert ($created.UtcTicks-eq [long]$expected.creation_utc_ticks-and $p.ParentProcessId-eq $expected.parent-and $p.CommandLine-ceq $expected.command) 'Actual science identity differs'
 $identityChecks+=[ordered]@{role='science';kind=if($p.ProcessId-eq 33892){'launcher'}else{'interpreter'};pid=$p.ProcessId;parent=$p.ParentProcessId;creation=$created.ToString('o');creation_utc_ticks=$created.UtcTicks;command=$p.CommandLine;matched_snapshot=$true}
}
$scienceLogs=@();foreach($n in @('run.log','process_stdout.log','process_stderr.log')){$p=Join-Path $active.output_dir $n;$f=Get-Item -LiteralPath $p;$scienceLogs+=[ordered]@{path=$p;bytes=$f.Length;last_write_utc=$f.LastWriteTimeUtc.ToString('o');tail=@(Get-Content -LiteralPath $p -Tail 5)}}
$report=[ordered]@{schema='independent-sep29-actual-launch-readonly-review.v1';time=$observedAt.ToString('o');finished=(Get-Date).ToString('o');passed=$true;blocking_findings=@();script=(Bind $PSCommandPath);bindings=$bindings;states=$stateReviews;actual_identity_checks=$identityChecks;actual_identity_count=$identityChecks.Count;launch_memory_samples=$samples;launch_headroom_gib=@($samples|ForEach-Object{[math]::Round([long]$_.headroom_bytes/1GB,4)});native_probe=[ordered]@{launch=(Bind (Join-Path $probe 'launch.json'));report=(Bind (Join-Path $probe 'report.json'));launcher=3060;interpreter=34284;original_parent_popen_exit_code=0;current_both_numeric_pids_absent=$true;independent_dual_handle_exit_evidence=$false;libraries_actually_imported=$packages;TORCHINDUCTOR_CACHE_DIR=$pr.import_environment_changes.TORCHINDUCTOR_CACHE_DIR;verified_completed_main_manifests_count=@($pr.runtime_provenance.verified_completed_fit_manifests).Count;reviewer_scientific_imports=$false};active_evaluation=$active;science_logs=$scienceLogs;no_live_state_or_scientific_mutations=$true;limitations=@('This verifies actual recovery launch and currently live ordered owners/science; it is not scientific completion.','Native probe parent Popen exit0 plus current absence is not independent dual-handle interpreter exit proof.','All recovery entry points including newly used Sep29 must not be replayed or ValidateOnly rerun.','Accepted42 fits and adopted18 University evaluations are inherited; no new checkpoint hash or scientific result is accepted here.','Live status/log observations can change after this read-only snapshot; runtime headroom is never a stop threshold.')}
$out=Join-Path $d 'INDEPENDENT_ACTUAL_LAUNCH_READONLY_REVIEW.json';Assert (-not (Test-Path -LiteralPath $out)) 'Refuse overwrite'
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($report|ConvertTo-Json -Depth 18));$fs=[IO.File]::Open($out,[IO.FileMode]::CreateNew);try{$fs.Write($bytes,0,$bytes.Length)}finally{$fs.Dispose()}
Bind $out|ConvertTo-Json
