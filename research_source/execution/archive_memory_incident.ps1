$ErrorActionPreference = 'Stop'
$executionRoot = 'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$runRoot = 'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\runs\formal_main\university1652\visual_style\seed_1'
$incidentRoot = Join-Path $executionRoot 'memory_recovery_20260914_1300'
if (Test-Path -LiteralPath $incidentRoot) { throw 'Incident directory already exists; inspect before retry.' }
$pythonProcesses = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'")
if ($pythonProcesses.Count -ne 0) { throw 'Python processes remain; inspect before recovery.' }
New-Item -ItemType Directory -Path $incidentRoot | Out-Null
New-Item -ItemType Directory -Path (Join-Path $incidentRoot 'run') | Out-Null
New-Item -ItemType Directory -Path (Join-Path $incidentRoot 'controllers') | Out-Null
$snapshot = [ordered]@{ time=(Get-Date -Format o); python_processes=$pythonProcesses; os=(Get-CimInstance Win32_OperatingSystem | Select-Object FreePhysicalMemory,TotalVisibleMemorySize,FreeVirtualMemory,TotalVirtualMemorySize); pagefile=@(Get-CimInstance Win32_PageFileUsage | Select-Object Name,AllocatedBaseSize,CurrentUsage,PeakUsage) }
$snapshot | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $incidentRoot 'system_before_recovery.json') -Encoding UTF8
$records = @()
foreach ($name in @('run_config.json','run_manifest.json','history.json','run.log','last.pt','best.pt','process_stdout.log','process_stderr.log')) {
  $source = Join-Path $runRoot $name
  $target = Join-Path (Join-Path $incidentRoot 'run') $name
  Copy-Item -LiteralPath $source -Destination $target
  $sourceHash=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLower()
  if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLower() -ne $sourceHash) { throw "Backup mismatch: $name" }
  $records += [ordered]@{source=$source;backup=$target;bytes=(Get-Item -LiteralPath $source).Length;sha256=$sourceHash}
}
$ledger='C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\runs\frozen_formal_matrix_ledger.json'
Copy-Item -LiteralPath $ledger -Destination (Join-Path $incidentRoot 'frozen_formal_matrix_ledger.json')
foreach ($name in @('status.json','pipeline_status.json','extension_status.json','latest_baseline_status.json','extension_plan.json','latest_baseline_plan.json','continue_formal_matrix.py','supervise_pipeline.py','supervise_extensions.py','supervise_latest_baselines.py','controller.original_environment.stderr.log','controller.original_environment.stdout.log','pipeline.original_environment.stderr.log','pipeline.original_environment.stdout.log','extensions.stderr.log','extensions.stdout.log','latest_baselines.stderr.log','latest_baselines.stdout.log')) {
  $source=Join-Path $executionRoot $name
  $target=Join-Path (Join-Path $incidentRoot 'controllers') $name
  Copy-Item -LiteralPath $source -Destination $target
  $sourceHash=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLower()
  if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLower() -ne $sourceHash) { throw "Backup mismatch: $name" }
  $records += [ordered]@{source=$source;backup=$target;bytes=(Get-Item -LiteralPath $source).Length;sha256=$sourceHash}
}
$records | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $incidentRoot 'backup_manifest.json') -Encoding UTF8
Write-Output "Preserved $($records.Count) files; no controller states altered."
