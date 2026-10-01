$ErrorActionPreference='Stop'
$e=Split-Path -Parent $PSScriptRoot
$pkg='C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch'
$dest=Join-Path $PSScriptRoot ('capture_'+(Get-Date -Format yyyyMMdd_HHmmssfff))
[IO.Directory]::CreateDirectory($dest)|Out-Null
$bindings=[Collections.Generic.List[object]]::new()
function Bind([string]$p){$i=Get-Item -LiteralPath $p;[ordered]@{path=$i.FullName;sha256=(Get-FileHash -LiteralPath $p).Hash.ToLowerInvariant();bytes=$i.Length}}
function Seal([string]$name,[byte[]]$b){$p=Join-Path $dest $name;$s=[IO.File]::Open($p,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read);try{$s.Write($b,0,$b.Length)}finally{$s.Dispose()};Bind $p}
function CopySmall([string]$p){if(-not(Test-Path -LiteralPath $p -PathType Leaf)){throw "Missing required capture $p"};$before=Bind $p;if($before.bytes -gt 6000000){throw 'Small file scope exceeded'};$b=[IO.File]::ReadAllBytes($p);$snap=Seal (('{0:d3}_' -f $bindings.Count)+[IO.Path]::GetFileName($p)) $b;$after=Bind $p;if($before.sha256 -ne $after.sha256 -or $snap.sha256 -ne $before.sha256){throw 'Source changed during incident capture'};$bindings.Add([ordered]@{source=$before;snapshot=$snap})}
$stateNames=@('status.json','pipeline_status.json','extension_status.json','latest_baseline_status.json','independent_comparison_status.json')
foreach($name in $stateNames){CopySmall (Join-Path $e $name)}
foreach($name in @('supervise_pipeline.py','supervise_extensions.py','run_controller_with_state_retry_v2.py')){if(Test-Path -LiteralPath (Join-Path $e $name)){CopySmall (Join-Path $e $name)}}
foreach($name in @('pipeline','extensions','latest','independent')){foreach($suffix in @('stdout.log','stderr.log','launch.json','launch_intent.json','retired.json')){$p=Join-Path $e ('host_recovery_20260929_0341\'+$name+'.'+$suffix);if(Test-Path -LiteralPath $p){CopySmall $p}}}
foreach($name in @('robustness','robustness_aggregate','query_analysis','formal_efficiency_component')){foreach($suffix in @('stdout.log','stderr.log')){CopySmall (Join-Path $e ('stage_logs\'+$name+'.'+$suffix))}}
foreach($name in @('run_frozen_robustness_matrix.py','aggregate_formal_robustness.py','run_transactions_query_analysis.py','run_transactions_formal_efficiency.py')){CopySmall (Join-Path $pkg ('experiments\'+$name))}
CopySmall (Join-Path $pkg 'runs\frozen_robustness_matrix_ledger.json')
foreach($suffix in @('stdout.log','stderr.log')){CopySmall (Join-Path $pkg ('runs\frozen_robustness_orchestrator_logs\sues200__full__seed_1.'+$suffix))}
foreach($name in @('extension_status.json','latest_baseline_status.json','independent_comparison_status.json')){$state=Get-Content -LiteralPath (Join-Path $e $name) -Raw|ConvertFrom-Json -DateKind String;CopySmall $state.plan_path}
CopySmall (Join-Path $e 'state_io_retry_20260920_v2\io_retry_pipeline_14420.jsonl')
CopySmall (Join-Path $e 'robustness_observation_20260929_0647\snapshot_20260929_140746513\OBSERVATION.json')
$ids=@(33924,31992,14420,29784,30388,7584,33520,12896,7484,21652,24120,40780,37764,14260,43500,40968,23920)
$all=@(Get-CimInstance Win32_Process)
$observedAt=[DateTimeOffset]::Now.ToString('o')
$matches=@($all|Where-Object {$_.ProcessId -in $ids -or ($_.Name -eq 'python.exe' -and $_.CommandLine -match 'LGM|lgm')}|ForEach-Object{[ordered]@{pid=$_.ProcessId;parent=$_.ParentProcessId;creation=([DateTimeOffset]$_.CreationDate).ToString('o');creation_utc_ticks=([DateTimeOffset]$_.CreationDate).UtcTicks;command=$_.CommandLine}})
$gpuRaw=(& nvidia-smi --query-compute-apps=pid,process_name --format=csv,noheader 2>&1|Out-String)
$gpuExit=$LASTEXITCODE
$gpu=Seal 'gpu_compute_query.txt' ([Text.UTF8Encoding]::new($false).GetBytes($gpuRaw))
$boot=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime
$report=[ordered]@{schema='root-efficiency-incident-capture.v1';time=[DateTimeOffset]::Now.ToString('o');cim_observed_at=$observedAt;host_boot_utc=([DateTimeOffset]$boot).ToUniversalTime().ToString('o');source=(Bind $PSCommandPath);bindings=$bindings.ToArray();file_count=$bindings.Count;searched_prior_pids=$ids;current_matches=$matches;gpu_query=$gpu;gpu_query_exit_code=$gpuExit;limits=@('New T6 parent-recorded exit1; all previous own controller exit codes remain unknown absent original handles','Do not infer CUDA computation or graphics-only activity from process names or insufficient-permissions entries','No scientific source/state/plan changed; no recovery or ValidateOnly; no applications closed','Other newly completed artifacts require separate audits; capture itself is not scientific acceptance')}
$r=Seal 'CAPTURE.json' ([Text.UTF8Encoding]::new($false).GetBytes(($report|ConvertTo-Json -Depth 20)))
[ordered]@{report=$r;files=$bindings.Count;time=$report.time;host_boot_utc=$report.host_boot_utc;current_matches=$matches;gpu_query_exit_code=$gpuExit}|ConvertTo-Json -Depth 6
