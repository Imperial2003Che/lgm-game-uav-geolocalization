$ErrorActionPreference='Stop'
$e=Split-Path -Parent $PSScriptRoot
$dest=Join-Path $PSScriptRoot ('observation_'+(Get-Date -Format yyyyMMdd_HHmmssfff))
[IO.Directory]::CreateDirectory($dest)|Out-Null
function Bind([string]$p){$i=Get-Item -LiteralPath $p;[ordered]@{path=$i.FullName;sha256=(Get-FileHash -LiteralPath $p).Hash.ToLower();bytes=$i.Length}}
function Save([string]$name,[string]$s){$p=Join-Path $dest $name;$b=[Text.UTF8Encoding]::new($false).GetBytes($s);$f=[IO.File]::Open($p,[IO.FileMode]::CreateNew);try{$f.Write($b,0,$b.Length)}finally{$f.Dispose()};Bind $p}
$expected=@{'status.json'='0bd5b1b7b486fb442d7e9f6624839e7b2b2ce1600efd5f6bbbdf00cf22093d8a';'pipeline_status.json'='47fd31336b8e742da91891a87c28a0767989cb45c375aeb000854f50e37acf12';'extension_status.json'='02a21093347100b5a17671f676cf5c9b7c5819a552729733677a1b4b52b2b074';'latest_baseline_status.json'='83fd30e4d1b0efa0a806ceb033f20b6c49553f3c9a649004509929751d91e94a';'independent_comparison_status.json'='a1389f862ec7560e32fb29aeb8dafb93349eaf19a6ae149979c50357760234ee'}
$states=@();foreach($name in $expected.Keys){$p=Join-Path $e $name;$b=Bind $p;$s=Get-Content -LiteralPath $p -Raw;$v=$s|ConvertFrom-Json -DateKind String;$snap=Save $name $s;$after=Bind $p;if($b.sha256 -cne $after.sha256){throw 'State changed during observation'};$states+=@([ordered]@{source=$b;snapshot=$snap;unchanged_since_incident=($b.sha256 -ceq $expected[$name]);status=$v.status;heartbeat_utc=$v.heartbeat_utc})}
$ids=@(33924,31992,14420,29784,30388,7584,33520,12896,7484,21652,24120,40780,37764,14260,43500,40968,23920)
function Processes{
 $all=@(Get-CimInstance Win32_Process)
 [ordered]@{observed_utc=[DateTimeOffset]::UtcNow.ToString('o');records=@($all|Where-Object {$_.ProcessId -in $ids -or ($_.Name -eq 'python.exe' -and $_.CommandLine -match '(supervise_pipeline|supervise_extensions|supervise_latest_baselines|supervise_independent_comparison|run_frozen_robustness_matrix|run_image_level_robustness|run_transactions_formal_efficiency)\.py')}|ForEach-Object{[ordered]@{pid=$_.ProcessId;parent=$_.ParentProcessId;creation_utc_ticks=$_.CreationDate.ToUniversalTime().Ticks.ToString();command=$_.CommandLine}})}
}
$first=Processes
$gpuRaw=(& nvidia-smi --query-compute-apps=pid,process_name --format=csv,noheader 2>&1|Out-String);$gpuExit=$LASTEXITCODE;$gpu=Save 'gpu_compute_query.txt' $gpuRaw
$gpuRows=@($gpuRaw -split "`r?`n" |Where-Object {$_ -match '^\s*\d+\s*,'})
$second=Processes
$report=[ordered]@{schema='stopped-efficiency-incident-readonly-observation.v1';time=[DateTimeOffset]::Now.ToString('o');source=(Bind $PSCommandPath);host_boot_utc=([DateTimeOffset](Get-CimInstance Win32_OperatingSystem).LastBootUpTime).ToUniversalTime().ToString('o');states=$states;first_CIM=$first;second_CIM=$second;gpu_query=$gpu;gpu_query_exit_code=$gpuExit;gpu_process_rows=$gpuRows.Count;original_gpu_exclusive_gate_would_be_satisfied=($gpuExit -eq 0 -and $gpuRows.Count -eq 0);t6_output_exists=(Test-Path -LiteralPath 'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\analysis\transactions_t6_formal');scientific_or_recovery_execution=$false;live_state_modified=$false;limits=@('This is a read-only gate snapshot, not admission for any later launch.','Numeric PID presence, if any, requires exact UTC ticks/full command/parent comparison; absence is not independent exit0 proof.','No application closure, resource modification, source/plan mutation or ValidateOnly/recovery replay.')}
$b=Save 'OBSERVATION.json' ($report|ConvertTo-Json -Depth 15)
[ordered]@{report=$b;time=$report.time;state_changed=@($states|Where-Object {-not $_.unchanged_since_incident}).Count;first_matches=$first.records;second_matches=$second.records;gpu_rows=$gpuRows.Count;original_gpu_gate_satisfied=$report.original_gpu_exclusive_gate_would_be_satisfied;t6_output_exists=$report.t6_output_exists}|ConvertTo-Json -Depth 8
