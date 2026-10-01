$ErrorActionPreference='Stop'
$e='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$dest=Join-Path $e 'host_interruption_20260929_0341'
if(Test-Path -LiteralPath $dest){throw 'New capture directory already exists; do not overwrite.'}
$old=Join-Path $e 'host_recovery_20260927_2145'
$stateNames=@('status.json','pipeline_status.json','extension_status.json','latest_baseline_status.json','independent_comparison_status.json')
$roles=@('primary','pipeline','extensions','latest','independent')
$oldIds=@(16412,16636,30324,10876,29432,18296,21636,32572,26072,2820,22496)
$processes=@(Get-CimInstance Win32_Process)
$python=@($processes|Where-Object Name -eq 'python.exe')
$liveOld=@($processes|Where-Object{$_.ProcessId -in $oldIds})
$liveScience=@($python|Where-Object{$_.CommandLine -match 'run_controller_with_state_retry|continue_formal_matrix|supervise_.*\.py|run_formal_worker|lgm_game_pytorch'})
if($liveOld.Count -or $liveScience.Count){throw 'Old IDs or scientific/controller process remains; capture assumption rejected.'}
$s=Get-Content -LiteralPath (Join-Path $e 'status.json') -Raw|ConvertFrom-Json -DateKind String
$boot=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime()
if($s.active.pid -ne 22496 -or $s.active.command[4] -ne 'evaluate' -or $boot -le [DateTimeOffset]::Parse($s.heartbeat_utc).UtcDateTime){throw 'Latest state/boot does not match this incident.'}
[void](New-Item -ItemType Directory -Path $dest)
$files=[Collections.Generic.List[object]]::new()
function Preserve([string]$path,[string]$relative){
 $target=Join-Path $dest $relative
 [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target))
 $before=Get-Item -LiteralPath $path
 $beforeHash=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower()
 Copy-Item -LiteralPath $path -Destination $target -ErrorAction Stop
 $after=Get-Item -LiteralPath $path
 $copiedHash=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLower()
 $afterHash=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower()
 if($beforeHash -ne $copiedHash -or $afterHash -ne $copiedHash -or $before.Length -ne $after.Length -or $before.LastWriteTimeUtc.Ticks -ne $after.LastWriteTimeUtc.Ticks){throw ('Unstable file: '+$path)}
 $files.Add([ordered]@{path=$path;backup=$target;bytes=$after.Length;sha256=$copiedHash;last_write_utc=$after.LastWriteTimeUtc.ToString('o')})
}
foreach($n in $stateNames){Preserve (Join-Path $e $n) ('states\'+$n)}
for($i=0;$i -lt $roles.Count;$i++){
 $role=$roles[$i]
 foreach($n in @($role+'_launch.json',$role+'_launch_intent.json',$role+'.stdout.log',$role+'.stderr.log','retired_'+$stateNames[$i])){Preserve (Join-Path $old $n) ('previous_launch\'+$n)}
 $diag=Join-Path $e ('state_io_retry_20260920_v2\io_retry_'+$role+'_'+(@(16412,30324,29432,21636,26072)[$i])+'.jsonl')
 if(Test-Path -LiteralPath $diag){Preserve $diag ('retry\'+[IO.Path]::GetFileName($diag))}
}
$activeFiles=@(Get-ChildItem -LiteralPath $s.active.output_dir -Recurse -File)
foreach($f in $activeFiles){Preserve $f.FullName ('active_evaluation\'+[IO.Path]::GetRelativePath($s.active.output_dir,$f.FullName))}
Preserve 'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\runs\frozen_formal_matrix_ledger.json' 'ledger\frozen_formal_matrix_ledger.json'
Preserve (Join-Path $old 'OWNER_SNAPSHOT_20260928_144022952.json') 'previous_identity\OWNER_SNAPSHOT_20260928_144022952.json'
foreach($rel in @('completion_audits_20260928\ROOT_FIT_42_ADOPTION_20260928.json','evaluation_audits_20260928\ROOT_BATCH10_ADOPTION_20260928.json','host_recovery_20260927_2145\ROOT_ACTUAL_LAUNCH_20260927.json','host_recovery_20260927_2145\ROOT_ADOPTION_20260927.json')){Preserve (Join-Path $e $rel) ('adoptions\'+[IO.Path]::GetFileName($rel))}
foreach($n in @('extension_plan.json','latest_baseline_plan.json','independent_comparison_plan_v2.json')){if(Test-Path -LiteralPath (Join-Path $e $n)){Preserve (Join-Path $e $n) ('plans\'+$n)}}
$memory=Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
$summaries=@(foreach($n in $stateNames){$x=Get-Content -LiteralPath (Join-Path $e $n) -Raw|ConvertFrom-Json -DateKind String; [ordered]@{file=$n;status=$x.status;controller_pid=$x.controller_pid;supervisor_pid=$x.supervisor_pid;heartbeat_utc=$x.heartbeat_utc;pending_jobs=@($x.jobs|Where-Object status -eq 'pending').Count}})
$capture=[ordered]@{schema='host-interruption-preservation.v2';time=[DateTimeOffset]::Now.ToString('o');last_boot_utc=$boot.ToString('o');old_science_and_controllers_absent=$true;old_ids=$oldIds;actual_python_processes=@($python|Select-Object ProcessId,ParentProcessId,@{n='creation_utc';e={$_.CreationDate.ToUniversalTime().ToString('o')}},CommandLine);active=$s.active;primary_status=$s.status;primary_heartbeat=$s.heartbeat_utc;states=$summaries;active_evaluation_manifest_exists=(Test-Path -LiteralPath (Join-Path $s.active.output_dir 'evaluation_manifest.json'));active_evaluation_file_count=$activeFiles.Count;commit_headroom_GiB=([double]($memory.CommitLimit-$memory.CommittedBytes)/1GB);training_accepted=42;evaluations_previously_adopted=12;files=@($files.ToArray());note='Later host boot and absent old processes establish interruption; old exit codes and exact stop time/cause unknown. Active evaluation has only logs, no completion manifest. Forty-two fits remain previously accepted; no old checkpoint rehash, no scientific state/source/parameter mutation. Last observed science pair in old identity snapshot belongs to an earlier completed evaluation; current interrupted science interpreter/creation identity was not observed.'}
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($capture|ConvertTo-Json -Depth 20))
[IO.File]::WriteAllBytes((Join-Path $dest 'CAPTURE.json'),$bytes)
[ordered]@{path=(Join-Path $dest 'CAPTURE.json');sha256=(Get-FileHash -LiteralPath (Join-Path $dest 'CAPTURE.json')).Hash.ToLower();files=$files.Count;boot=$capture.last_boot_utc;python=$capture.actual_python_processes;active_files=$activeFiles.Count;headroom=$capture.commit_headroom_GiB}|ConvertTo-Json -Depth 6
