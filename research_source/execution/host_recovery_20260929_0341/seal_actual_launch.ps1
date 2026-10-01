param([Parameter(Mandatory=$true)][string]$ReviewPath,[Parameter(Mandatory=$true)][string]$ReviewSha256)
$ErrorActionPreference='Stop'
$r=$PSScriptRoot
$e=Split-Path -Parent $r
$dest=Join-Path $r 'ROOT_ACTUAL_LAUNCH_20260929.json'
if(Test-Path -LiteralPath $dest){throw 'Final launch record already exists'}
function Read-Json([string]$p){Get-Content -LiteralPath $p -Raw|ConvertFrom-Json -DateKind String}
function Bind([string]$p,[string]$expected=''){
 $f=Get-Item -LiteralPath $p
 $sha=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()
 if($expected -and $sha -cne $expected){throw ('Binding mismatch: '+$p)}
 [ordered]@{path=$p;size=$f.Length;sha256=$sha}
}
$bindings=@()
$bindings+=Bind $PSCommandPath
$bindings+=Bind (Join-Path $e 'restart_after_host_interruption_20260929_v1.ps1') '59deea56a6df6ee59282aa50d2612246a0b3e2cb8b9335120af8907f778fdd64'
$bindings+=Bind (Join-Path $r 'ROOT_ADOPTION_20260929.json') 'b276efb7973d15d51304bd930bae13ae612c0686c06133e87fab8818f08bdfe4'
$bindings+=Bind (Join-Path $e 'host_interruption_20260929_0341\CAPTURE.json') 'a19eeae091aafdab5791367590e2ac22752d9fc5b57f79c0ddaf090072ee06a0'
$bindings+=Bind (Join-Path $e 'completion_audits_20260928\ROOT_FIT_42_ADOPTION_20260928.json') 'ca54f91342f77d7d17f18a932c61681ae6f4d7c14f4ffd917c0c1594fc289e87'
$bindings+=Bind (Join-Path $e 'evaluation_audits_20260929\ROOT_BATCH6_ADOPTION_20260929.json') 'c0735605a977e5ffcfd877e980a3773e9a747d4d7b4d68b9b682a0276f693fae'
$bindings+=Bind (Join-Path $r 'ACTUAL_PRIMARY_VALIDATE.json') 'c51f9673788dbdb86ab15db1425fe4cb4eef435802b2c26459cd32b21b4f2da3'
$bindings+=Bind (Join-Path $r 'ACTUAL_PRIMARY_ENTRY_RETURN.json') 'c19e49697a1dd8fd732623ebb730f90d00554603b2b744bee3cf83c626476eea'
$bindings+=Bind $ReviewPath $ReviewSha256
$review=Read-Json $ReviewPath
if(-not $review.passed -or $review.schema -ne 'independent-sep29-actual-launch-readonly-review.v1' -or @($review.blocking_findings).Count -or $review.actual_identity_count -ne 12){throw 'Independent actual review not passed'}
$bindings+=Bind $review.script.path $review.script.sha256
foreach($item in $review.bindings){$bindings+=Bind $item.path $item.sha256}
$observer=Join-Path $r 'observe_new_owners.ps1'
$bindings+=Bind $observer '3bfe889e149c2f97d2c2954ab4903135164c604f170aa900c1afb427086e2f97'
$observation=(& $observer -Stages @('primary','pipeline','extensions','latest','independent'))|ConvertFrom-Json -DateKind String
$bindings+=Bind $observation.path $observation.sha256
$snapshot=Read-Json $observation.path
if(@($snapshot.states).Count -ne 5 -or @($snapshot.science).Count -ne 2){throw 'Expected five controllers and scientific pair'}
$defs=@{primary='status.json';pipeline='pipeline_status.json';extensions='extension_status.json';latest='latest_baseline_status.json';independent='independent_comparison_status.json'}
$live=@()
foreach($role in @('primary','pipeline','extensions','latest','independent')){
 $bindings+=Bind (Join-Path $r ($role+'_launch_intent.json'))
 $bindings+=Bind (Join-Path $r ($role+'_launch.json'))
 $bindings+=Bind (Join-Path $r ('retired_'+$defs[$role]))
 $s=Read-Json (Join-Path $e $defs[$role])
 $row=@($snapshot.states|Where-Object role -eq $role)[0]
 $hb=[DateTimeOffset]::Parse([string]$s.heartbeat_utc)
 if(([DateTimeOffset]::UtcNow-$hb).TotalSeconds -gt 90){throw ('Stale heartbeat '+$role)}
 if($role -ne 'primary'){
  $count=@{pipeline=7;extensions=4;latest=2;independent=3}[$role]
  if(@($s.jobs).Count -ne $count -or @($s.jobs|Where-Object status -ne 'pending').Count){throw 'Successor job state changed'}
 }
 $retry=Join-Path $e ('state_io_retry_20260920_v2\io_retry_'+$role+'_'+$row.owner.pid+'.jsonl')
 $err=Get-Item -LiteralPath (Join-Path $r ($role+'.stderr.log'))
 $live+=[ordered]@{role=$role;status=$s.status;heartbeat_utc=$s.heartbeat_utc;owner=$row.owner;launcher=$row.launcher;stderr_bytes=$err.Length;retry_diagnostic_exists=(Test-Path -LiteralPath $retry)}
}
$intent=Read-Json (Join-Path $r 'primary_launch_intent.json')
if(@($intent.memory_samples).Count -ne 4){throw 'Admission sample count'}
foreach($sample in $intent.memory_samples){if([long]$sample.headroom_bytes -lt ([long]26*1GB)){throw 'Admission resource below original gate'}}
$probeDir=Join-Path $e 'environment_probes\20260929_040047_25ff0f4f36d3473cbceb141742f407ac'
foreach($name in @('report.json','launch.json','stdout.log','stderr.log')){$bindings+=Bind (Join-Path $probeDir $name)}
$probe=Read-Json (Join-Path $probeDir 'report.json')
$probeLaunch=Read-Json (Join-Path $probeDir 'launch.json')
if($probeLaunch.exit_code -ne 0 -or $probeLaunch.pid -ne 3060 -or $probe.pid -ne 34284){throw 'Native probe mismatch'}
if(@(Get-CimInstance Win32_Process -Filter 'ProcessId=3060 OR ProcessId=34284').Count){throw 'Probe PID reappeared; inspect identity'}
if($probe.runtime_provenance.packages.torch -ne '2.11.0+cu126' -or $probe.runtime_provenance.packages.torchvision -ne '0.26.0+cu126' -or $probe.runtime_provenance.packages.numpy -ne '2.4.4' -or $probe.runtime_provenance.packages.Pillow -ne '12.2.0'){throw 'Native package mismatch'}
if(-not $probe.import_environment_changes.TORCHINDUCTOR_CACHE_DIR.after){throw 'Native cache environment missing'}
$state=Read-Json (Join-Path $e 'status.json')
$old=Read-Json (Join-Path $r 'retired_status.json')
$firstPath=Join-Path $r 'OWNER_SNAPSHOT_20260929_040135456.json'
$bindings+=Bind $firstPath '92fd3a952f343eae98193589e477a3564a9c650dac0f4cb4810d0c56094d4bbd'
$first=Read-Json $firstPath
if(($first.states[0].active.command|ConvertTo-Json -Compress) -cne ($old.active.command|ConvertTo-Json -Compress)){throw 'Initially restored scientific command changed'}
if($state.active.pid -ne $snapshot.science[0].pid -or ($state.active.command|ConvertTo-Json -Compress) -cne ($snapshot.states[0].active.command|ConvertTo-Json -Compress)){throw 'Science naturally transitioned during observation; take a fresh bounded snapshot'}
$restoredEvent=@($state.events|Where-Object pid -eq 20376)
if($state.active.pid -ne 20376){
 if($restoredEvent.Count -ne 1 -or $restoredEvent[0].status -ne 'completed' -or $restoredEvent[0].exit_code -ne 0){throw 'Restored evaluation has no successful parent-recorded transition'}
 if(@(Get-CimInstance Win32_Process -Filter 'ProcessId=20376 OR ProcessId=11112').Count){throw 'Initial science PID reappeared; inspect identity'}
}
$stderr=Get-Item -LiteralPath (Join-Path $state.active.output_dir 'process_stderr.log')
$log=Get-Content -LiteralPath (Join-Path $state.active.output_dir 'run.log') -Tail 8
$report=[ordered]@{
 schema='root-actual-evaluation-host-recovery-launch.v1';time=(Get-Date).ToString('o');passed=$true;bindings=$bindings
 identities_verified=12;states=$live;science=$snapshot.science;initial_restored_command_same_as_sealed_interrupted_evaluation=$true
 restored_evaluation_parent_event=$restoredEvent;restored_evaluation_independent_double_handle_exit_proof=$false
 admission_samples_GiB=@($intent.memory_samples|ForEach-Object{[double]$_.headroom_bytes/1GB})
 native_probe=[ordered]@{launcher_pid=3060;interpreter_pid=34284;parent_recorded_launcher_exit_code=0;both_now_absent=$true;independent_double_handle_exit_proof=$false;packages=$probe.runtime_provenance.packages;import_environment_changes=$probe.import_environment_changes;cuda_initialized_by_guard=$probe.runtime_provenance.cuda_initialized_by_guard}
 science_log_tail=$log;science_stderr_bytes=$stderr.Length;current_evaluation_manifest_present=(Test-Path -LiteralPath (Join-Path $state.active.output_dir 'evaluation_manifest.json'))
 accepted_training_fits=42;accepted_evaluation_runs=18;accepted_evaluation_tasks=54
 acceptance_scope='Inherited checkpoint SHA with actual new evaluation artifact hashes and per-query consistency; no independent model/full-ranking/AP rerun or unconditional current checkpoint-byte proof.'
 old_interrupted_exit_codes='unknown';all_five_new_entry_roles_used_no_replay=$true
 runtime_memory_not_stop_threshold=$true;scientific_completion_not_inferred_from_launch=$true
}
$json=$report|ConvertTo-Json -Depth 30
$bytes=[Text.UTF8Encoding]::new($false).GetBytes($json)
$stream=[IO.File]::Open($dest,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
Bind $dest|ConvertTo-Json
