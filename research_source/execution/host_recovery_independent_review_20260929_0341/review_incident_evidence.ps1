$ErrorActionPreference='Stop'
$ex='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$captureRoot=Join-Path $ex 'host_interruption_20260929_0341'
$reviewRoot=$PSScriptRoot
function Sha($p) { (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLower() }
function ReadJ($p) { Get-Content -LiteralPath $p -Raw | ConvertFrom-Json -DateKind String }
function Assert($condition,$message) { if (-not $condition) { throw $message } }
function Bind($p) { $f=Get-Item -LiteralPath $p; [ordered]@{path=$p;bytes=$f.Length;sha256=(Sha $p)} }
$capturePath=Join-Path $captureRoot 'CAPTURE.json'
Assert ((Sha $capturePath) -eq 'a19eeae091aafdab5791367590e2ac22752d9fc5b57f79c0ddaf090072ee06a0') 'Capture SHA mismatch'
$cap=ReadJ $capturePath
Assert ($cap.schema -eq 'host-interruption-preservation.v2' -and $cap.old_science_and_controllers_absent -ceq $true -and @($cap.actual_python_processes).Count -eq 0) 'Unexpected capture schema/processes'
Assert (@($cap.files).Count -eq 42) 'Wrong preservation count'
$checks=@()
foreach($r in $cap.files) {
  Assert ((Sha $r.backup) -eq $r.sha256 -and (Get-Item -LiteralPath $r.backup).Length -eq $r.bytes) ('Archived binding mismatch '+$r.backup)
  $checks+=Bind $r.backup
}
$boot=[DateTimeOffset]::Parse($cap.last_boot_utc)
$currentBoot=[DateTimeOffset](Get-CimInstance Win32_OperatingSystem).LastBootUpTime
Assert ($currentBoot.UtcTicks -eq $boot.UtcTicks) 'Boot changed after capture'
$identityPath=Join-Path $captureRoot 'previous_identity\OWNER_SNAPSHOT_20260928_144022952.json'
$identity=ReadJ $identityPath
Assert ((Sha $identityPath) -eq '2ad871bafc9eb72591635a0376e44188a5cef3ee8c871f283493bd0c6452be51') 'Identity SHA mismatch'
Assert ([DateTimeOffset]::Parse($identity.time) -lt $boot -and $boot -lt [DateTimeOffset]::Parse($cap.time)) 'Boot ordering invalid'
$defs=@{primary=@('status.json',16412,16636,'controller_pid','running',0);pipeline=@('pipeline_status.json',30324,10876,'supervisor_pid','waiting_for_primary',7);extensions=@('extension_status.json',29432,18296,'supervisor_pid','waiting_for_pipeline',4);latest=@('latest_baseline_status.json',21636,32572,'supervisor_pid','waiting_for_registered_extensions',2);independent=@('independent_comparison_status.json',26072,2820,'supervisor_pid','waiting_for_latest_baselines',3)}
$identities=@()
foreach($role in @('primary','pipeline','extensions','latest','independent')) {
 $d=$defs[$role]; $rows=@($identity.states | Where-Object role -eq $role)
 Assert ($rows.Count -eq 1) ('Missing/duplicate old role '+$role)
 $row=$rows[0]
 Assert ($row.owner.pid -eq $d[1] -and $row.launcher.pid -eq $d[2] -and $row.owner.parent -eq $d[2]) ('Old role identity mismatch '+$role)
 $args=@('-B',(Join-Path $ex 'run_controller_with_state_retry_v2.py'),'--role',$role,'--io-manifest-sha256','d8e6209f5ff2c2180d053e6444cb7df6ec0846405fea7ad6dee9b76a8fcb8dfb')
 if($role -eq 'primary') {$args+=@('--stage','all','--workers','8','--path-compat-sha256','11de17bd611431e4471eec1b8ac072a2159fbd02e4eb2cb041b4f3b0f00012a1')}
 if($role -eq 'extensions') {$args+=@('--manifest-sha256','b985182c80577fa1a98a7511ce5de2a6a360f908ab063d6f6a0e5a2395be3640')}
 if($role -eq 'independent') {$args+=@('--plan',(Join-Path $ex 'independent_comparison_plan_v2.json'))}
 if($role -in @('latest','independent')) {$args+=@('--addendum-sha256','0c4217fefb33d6550bda2300bc201f1c869da0b8d5ff02d45ae7af45b7ef6d70')}
 foreach($kind in @('owner','launcher')) {
  $p=$row.$kind; $start=[DateTimeOffset]::Parse($p.creation)
  Assert ($start.UtcTicks -eq [long]$p.creation_utc_ticks -and $start -lt $boot) ('Precise old time mismatch '+$role+'/'+$kind)
  $exe=if($kind -eq 'owner'){'C:\Users\17703\AppData\Local\Programs\Python\Python311\python.exe'}else{'C:\项目\.venvs\lgm-baselines\Scripts\python.exe'}
  $expected=(@($exe)+$args | ForEach-Object {'"'+$_+'"'}) -join ' '
  Assert ($p.command -ceq $expected) ('Complete command mismatch '+$role+'/'+$kind)
  Assert (@(Get-CimInstance Win32_Process -Filter ('ProcessId='+$p.pid)).Count -eq 0) ('Old PID presently reused/present; inspect '+$p.pid)
  $identities+=[ordered]@{role=$role;kind=$kind;pid=$p.pid;parent=$p.parent;creation=$p.creation;creation_utc_ticks=$p.creation_utc_ticks;command=$p.command;absent_now=$true}
 }
 $s=ReadJ (Join-Path (Join-Path $captureRoot 'states') $d[0])
 Assert ($s.($d[3]) -eq $d[1] -and $s.status -eq $d[4] -and [DateTimeOffset]::Parse($s.heartbeat_utc) -lt $boot) ('Archived state identity/time mismatch '+$role)
 if($role -ne 'primary') { Assert (@($s.jobs).Count -eq $d[5] -and @($s.jobs | Where-Object status -ne 'pending').Count -eq 0) ('Successor job state mismatch '+$role) }
}
Assert ($cap.active.pid -eq 22496 -and $cap.active.status -eq 'running' -and $null -eq $cap.active.exit_code -and $cap.active.command[4] -eq 'evaluate' -and [DateTimeOffset]::Parse($cap.active.started_utc) -lt $boot) 'Wrong interrupted evaluation'
Assert (@(Get-CimInstance Win32_Process -Filter 'ProcessId=22496').Count -eq 0) 'Interrupted numeric PID now present; inspect identity'
Assert ($cap.active_evaluation_manifest_exists -ceq $false -and $cap.active_evaluation_file_count -eq 3) 'Unexpected evaluation completeness in capture'
Assert (-not (Test-Path -LiteralPath (Join-Path $cap.active.output_dir 'evaluation_manifest.json'))) 'Evaluation now has manifest; recapture required'
$root42Path=Join-Path $captureRoot 'adoptions\ROOT_FIT_42_ADOPTION_20260928.json';$root42=ReadJ $root42Path
Assert ((Sha $root42Path) -eq 'ca54f91342f77d7d17f18a932c61681ae6f4d7c14f4ffd917c0c1594fc289e87' -and $root42.adopted -ceq $true -and $root42.completed_fit_count -eq 42 -and @($root42.completed_fit_ids).Count -eq 42 -and @($root42.completed_fit_ids|Select-Object -Unique).Count -eq 42) 'ROOT42 adoption invalid'
Assert (@($root42.completed_fit_ids|Where-Object {$_ -like 'formal_main/*'}).Count -eq 36 -and @($root42.completed_fit_ids|Where-Object {$_ -like 'formal_sensitivity/*'}).Count -eq 6) 'Adopted training scope differs'
$py=@(Get-CimInstance Win32_Process -Filter "Name='python.exe'")
$report=[ordered]@{schema='independent-sep29-host-evidence-review.v1';time=(Get-Date).ToString('o');passed=$true;script=(Bind $PSCommandPath);capture=(Bind $capturePath);verified_archived_files=$checks;old_controller_identities=$identities;current_boot_utc=$currentBoot.ToUniversalTime().ToString('o');python_processes=$py;training_acceptance='42 prior accepted fits; no new weight content hash or scientific import';interrupted_evaluation=[ordered]@{pid=22496;pid_absent_now=$true;old_creation_time=$null;old_interpreter_identity=$null;old_exit_codes='unknown';old_snapshot_science_pair='7896/28260 belongs to earlier completed University visual_style seed2 and is not the interrupted pair'};limitations=@('This verifies incident evidence only, not a recovery candidate or launch.','Original frozen runtime validators must remain unchanged; prior42 acceptance is inherited.','No live state or scientific artifact has been changed.')}
$out=Join-Path $reviewRoot ('INCIDENT_REVIEW_'+(Get-Date -Format 'yyyyMMdd_HHmmssfff')+'.json')
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($report|ConvertTo-Json -Depth 12));$fs=[IO.File]::Open($out,[IO.FileMode]::CreateNew);try{$fs.Write($bytes,0,$bytes.Length)}finally{$fs.Dispose()}
Bind $out | ConvertTo-Json
