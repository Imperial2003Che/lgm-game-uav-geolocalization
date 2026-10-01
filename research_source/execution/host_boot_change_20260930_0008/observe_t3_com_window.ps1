param([ValidateSet('ROOT_BEFORE_T3_COM.json','ROOT_AFTER_T3_COM.json')][string]$ObservationName)
$ErrorActionPreference='Stop'
$ex='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
function D($p){$f=Get-Item -LiteralPath $p; [ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Save($name,$obj){$p=Join-Path $PSScriptRoot $name;$b=[Text.UTF8Encoding]::new($false).GetBytes(($obj|ConvertTo-Json -Depth 50)+"`n");$s=[IO.File]::Open($p,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read);try{$s.Write($b,0,$b.Length)}finally{$s.Dispose()};D $p}
$oldpath=Join-Path $ex 'query_t5_paired_root_observation_20260929_2157\ROOT_STOPPED_OBSERVATION.json'
$old=Get-Content -LiteralPath $oldpath -Raw|ConvertFrom-Json -DateKind String
$contractpath=Join-Path $ex 't6_recovery_preparation_20260929_1548\RECOVERY_CONTRACT.json'
$contract=Get-Content -LiteralPath $contractpath -Raw|ConvertFrom-Json -DateKind String
$launchpath=Join-Path $ex 'host_recovery_20260929_0341\pipeline_launch.json'
$launch=Get-Content -LiteralPath $launchpath -Raw|ConvertFrom-Json -DateKind String
$records=@(foreach($x in $old.files){$now=D $x.path;if($now.bytes -ne $x.bytes -or $now.sha256 -ne $x.sha256){throw "Changed state/log $($x.path)"};$now})
if($records.Count -ne 16){throw 'Expected 16 closed state/log files'}
function Snap {
 $all=@(Get-CimInstance Win32_Process);$boot=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime()
 $matches=@($all|Where-Object{ $_.ProcessId -ne $PID -and ($_.Name -eq 'VISIO.EXE' -or $_.ProcessId -in @(33924,31992,14420,29784,30388,7584,33520,12896,7484,21652,24120,40780,37764,14260,43500,40968,23920) -or ($_.Name -match '^(python|pythonw|pwsh|powershell)\.exe$' -and $_.CommandLine -match '(run_controller_with_state_retry_v2|supervise_pipeline|supervise_extensions|supervise_latest_baselines|supervise_independent_comparison|run_formal|formal_reproduction|pipeline_supervisor|extension_supervisor|latest_baseline_supervisor|independent_comparison_supervisor|pipeline_recovery_candidate|start_pipeline_recovery_candidate|restart_after_host_interruption|run_frozen|run_image_level_robustness|run_transactions_formal_efficiency|formal_efficiency_component|train_retrieval|train_camp|train_dac|run_baseline|run_independent|resume_formal)'))})
 $rows=@(foreach($m in $matches){$p=@($all|Where-Object ProcessId -eq $m.ParentProcessId);[ordered]@{pid=[int]$m.ProcessId;parent_pid=[int]$m.ParentProcessId;name=$m.Name;command_line=$m.CommandLine;creation_utc=$m.CreationDate.ToUniversalTime().ToString('o');creation_utc_ticks=$m.CreationDate.ToUniversalTime().Ticks.ToString();parent_current_observation=@($p|ForEach-Object{[ordered]@{pid=[int]$_.ProcessId;name=$_.Name;command_line=$_.CommandLine;creation_utc_ticks=$_.CreationDate.ToUniversalTime().Ticks.ToString()}});parent_note='Current parent-number observation only; numeric parent reuse is not historical parent identity proof.'}})
 [ordered]@{observed_utc=[DateTime]::UtcNow.ToString('o');boot_utc=$boot.ToString('o');boot_utc_ticks=$boot.Ticks.ToString();matches=$rows}
}
$first=Snap;Start-Sleep -Milliseconds 400;$second=Snap
$carrierpath=Join-Path $ex 'latest_baseline_gpu.lock';$carrier=D $carrierpath;$carrier.creation_utc_ticks=(Get-Item -LiteralPath $carrierpath).CreationTimeUtc.Ticks.ToString();$carrier.byte_values=@([IO.File]::ReadAllBytes($carrierpath))
if($carrier.bytes -ne 1 -or $carrier.byte_values[0] -ne 48 -or $carrier.creation_utc_ticks -ne '639262940518466959'){throw 'Carrier changed'}
$unused= -not(Test-Path -LiteralPath (Join-Path $ex 't6_recovery_preparation_20260929_1548\runtime_attempt'))
$r=[ordered]@{schema='post-stopped-host-boot-change-observation.v1';utc=[DateTime]::UtcNow.ToString('o');source=(D $PSCommandPath);prior_reference=(D $oldpath);contract=(D $contractpath);old_pipeline_launch=(D $launchpath);old_pipeline_launch_record=$launch;contract_boot_utc=$contract.host_boot_utc;contract_boot_utc_ticks=$contract.host_boot_utc_ticks;contract_boot_matches_current=($first.boot_utc_ticks -eq $contract.host_boot_utc_ticks -and $second.boot_utc_ticks -eq $contract.host_boot_utc_ticks);files=$records;first=$first;second=$second;observer_pid=[int]$PID;carrier=$carrier;runtime_attempt_absent=$unused;t6_output_absent=(-not(Test-Path -LiteralPath 'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\analysis\transactions_t6_formal'));scope='Read-only new boot and PID-reuse observation. No release, native probe, COM, lock acquisition, recovery, state mutation or scientific execution. The already-stopped science evidence is byte-identical; no new scientific failure or exit code is inferred. Old boot-bound recovery contract cannot authorize execution on this boot.'}
Save $ObservationName $r | ConvertTo-Json -Depth 5
