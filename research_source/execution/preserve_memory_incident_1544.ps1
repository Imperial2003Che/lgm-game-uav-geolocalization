$ErrorActionPreference = 'Stop'
$executionRoot = 'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$incidentRoot = Join-Path $executionRoot 'memory_recovery_20260914_1544'
$runRoot = 'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\runs\formal_main\university1652\visual_style\seed_2'
$pythonProcesses = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'")
if ($pythonProcesses.Count) { throw 'Python processes remain; inspect before preserving stopped training.' }
New-Item -ItemType Directory -Path $incidentRoot -Force | Out-Null
$manifestPath = Join-Path $incidentRoot 'backup_manifest.json'
if (Test-Path -LiteralPath $manifestPath) { throw 'Incident already preserved; do not overwrite.' }
$items = @()
foreach ($name in @('run_config.json','run_manifest.json','history.json','run.log','last.pt','best.pt','process_stdout.log','process_stderr.log')) {
    $items += [pscustomobject]@{Source=(Join-Path $runRoot $name);Target=(Join-Path (Join-Path $incidentRoot 'run') $name)}
}
$items += [pscustomobject]@{Source='C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\runs\frozen_formal_matrix_ledger.json';Target=(Join-Path $incidentRoot 'frozen_formal_matrix_ledger.json')}
foreach ($name in @('status.json','pipeline_status.json','extension_status.json','latest_baseline_status.json','continue_formal_matrix.py','supervise_pipeline.py','supervise_extensions.py','supervise_latest_baselines.py','supervise_independent_comparisons.py','extension_plan.json','latest_baseline_plan.json','independent_comparison_plan_v2.json','independent_comparison_registration_v2.json')) {
    $items += [pscustomobject]@{Source=(Join-Path $executionRoot $name);Target=(Join-Path (Join-Path $incidentRoot 'controllers') $name)}
}
$backup = @()
foreach ($item in $items) {
    if (Test-Path -LiteralPath $item.Target) { throw ('Backup already exists: '+$item.Target) }
    New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($item.Target)) -Force | Out-Null
    $before = (Get-FileHash -LiteralPath $item.Source -Algorithm SHA256).Hash.ToLower()
    Copy-Item -LiteralPath $item.Source -Destination $item.Target
    $after = (Get-FileHash -LiteralPath $item.Target -Algorithm SHA256).Hash.ToLower()
    if ($before -ne $after -or $before -ne (Get-FileHash -LiteralPath $item.Source -Algorithm SHA256).Hash.ToLower()) { throw 'Source/backup changed during preservation.' }
    $backup += [ordered]@{source=$item.Source;backup=$item.Target;bytes=(Get-Item -LiteralPath $item.Target).Length;sha256=$before}
}
$backup | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding utf8
[ordered]@{
    time=(Get-Date).ToString('o')
    python_processes=$pythonProcesses
    memory=(Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory | Select-Object AvailableMBytes,CommittedBytes,CommitLimit)
    pagefile=(Get-CimInstance Win32_PageFileUsage | Select-Object Name,AllocatedBaseSize,CurrentUsage,PeakUsage)
    largest_private_memory=@(Get-Process | Sort-Object PrivateMemorySize64 -Descending | Select-Object -First 15 ProcessName,Id,PrivateMemorySize64,WorkingSet64)
    action='Preservation only; no restart or scientific parameter change.'
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $incidentRoot 'system_before_recovery.json') -Encoding utf8
Write-Output ('Preserved '+$backup.Count+' files with matching SHA256.')
