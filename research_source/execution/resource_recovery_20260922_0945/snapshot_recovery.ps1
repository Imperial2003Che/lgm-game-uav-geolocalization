$ErrorActionPreference = 'Stop'
$executionRoot = Split-Path $PSScriptRoot -Parent
$sampled = Get-Date
$pythonRows = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Select-Object ProcessId,ParentProcessId,@{n='creation';e={$_.CreationDate.ToString('o')}},CommandLine)
$definitions = @{
    primary=@('status.json','controller_pid')
    pipeline=@('pipeline_status.json','supervisor_pid')
    extensions=@('extension_status.json','supervisor_pid')
    latest=@('latest_baseline_status.json','supervisor_pid')
    independent=@('independent_comparison_status.json','supervisor_pid')
}
$states = @(foreach($role in @('primary','pipeline','extensions','latest','independent')) {
    $definition=$definitions[$role]
    $s=Get-Content -LiteralPath (Join-Path $executionRoot $definition[0]) -Raw | ConvertFrom-Json
    $launch=Get-Content -LiteralPath (Join-Path $PSScriptRoot ($role+'_launch.json')) -Raw | ConvertFrom-Json
    $owner=@($pythonRows | Where-Object ProcessId -eq $s.($definition[1]))
    $launcher=@($pythonRows | Where-Object ProcessId -eq $launch.launcher_pid)
    $expected='"C:\Users\17703\AppData\Local\Programs\Python\Python311\python.exe" '+$launch.arguments
    $stderr=Join-Path $PSScriptRoot ($role+'.stderr.log')
    [pscustomobject]@{role=$role;status=$s.status;heartbeat_utc=$s.heartbeat_utc;owner=$owner;launcher=$launcher;launch_record=$launch;owner_exact_command_match=($owner.Count -eq 1 -and $owner[0].CommandLine -ceq $expected);owner_parent_matches_launcher=($owner.Count -eq 1 -and $launcher.Count -eq 1 -and $owner[0].ParentProcessId -eq $launcher[0].ProcessId);state_io=$s.state_io_compatibility;job_states=@($s.jobs | ForEach-Object status);stderr_bytes=(Get-Item -LiteralPath $stderr).Length;error=$s.error}
})
$primary=Get-Content -LiteralPath (Join-Path $executionRoot 'status.json') -Raw | ConvertFrom-Json
$active=$primary.active
$scienceLauncher=@($pythonRows | Where-Object ProcessId -eq $active.pid)
$scienceChildren=@($pythonRows | Where-Object ParentProcessId -eq $active.pid)
$history=@(Get-Content -LiteralPath (Join-Path $active.output_dir 'history.json') -Raw | ConvertFrom-Json)
$m=Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
$pins=@(foreach($n in @('extension_plan.json','latest_baseline_plan.json','independent_comparison_plan_v2.json','state_io_retry_20260920_v2\SOURCE_MANIFEST.json')) {
    $p=Join-Path $executionRoot $n
    [pscustomobject]@{path=$p;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLower()}
})
$result=[ordered]@{schema='resource-recovery-live-observation.v1';time=$sampled.ToString('o');states=$states;active=$active;active_progress=$primary.active_progress;science_launcher=$scienceLauncher;science_children=$scienceChildren;history_count=$history.Count;history_last=$history[-1];run_log_tail=@(Get-Content -LiteralPath (Join-Path $active.output_dir 'run.log') -Tail 4);actual_python_processes=$pythonRows;commit_headroom_GiB=($m.CommitLimit-$m.CommittedBytes)/1GB;pins=$pins;note='Fresh live observation, not scientific completion. Preserve PID, exact CIM creation timestamp and command for later identity comparison.'}
$path=Join-Path $PSScriptRoot ('LIVE_SNAPSHOT_'+$sampled.ToString('yyyyMMdd_HHmmss')+'.json')
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($result | ConvertTo-Json -Depth 15))
$stream=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
try {$stream.Write($bytes,0,$bytes.Length)} finally {$stream.Dispose()}
[pscustomobject]@{snapshot=$path;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower();time=$result.time;history=$history.Count;commit_headroom_GiB=$result.commit_headroom_GiB;states=@($states | Select-Object role,status,owner_exact_command_match,owner_parent_matches_launcher,stderr_bytes);science_launcher=$scienceLauncher;science_children=$scienceChildren;log_tail=$result.run_log_tail} | ConvertTo-Json -Depth 6
