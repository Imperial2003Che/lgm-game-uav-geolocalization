$ErrorActionPreference='Stop'
$executionRoot='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$runRoot='C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\runs\formal_main\university1652\visual_style\seed_2'
$incidentRoot=Join-Path $executionRoot 'memory_recovery_20260914_1424'
if (Test-Path -LiteralPath $incidentRoot) {throw 'Incident directory exists; preserve it.'}
$pythonProcesses=@(Get-CimInstance Win32_Process -Filter "Name='python.exe'")
if ($pythonProcesses.Count) {throw 'Python processes remain; inspect before archival.'}
New-Item -ItemType Directory -Path $incidentRoot|Out-Null
New-Item -ItemType Directory -Path (Join-Path $incidentRoot 'run')|Out-Null
New-Item -ItemType Directory -Path (Join-Path $incidentRoot 'controllers')|Out-Null
$snapshot=[ordered]@{time=(Get-Date).ToString('o');python_processes=$pythonProcesses;memory=(Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory|Select-Object AvailableMBytes,CommittedBytes,CommitLimit);pagefile=@(Get-CimInstance Win32_PageFileUsage|Select-Object Name,AllocatedBaseSize,CurrentUsage,PeakUsage);largest_private_memory=@(Get-CimInstance Win32_PerfFormattedData_PerfProc_Process|Sort-Object PrivateBytes -Descending|Select-Object -First 16 Name,IDProcess,PrivateBytes,WorkingSet);reason='Repeated DataLoader shared mapping Windows1455 after completed epoch18; all original and queued Python processes exited.'}
$snapshot|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $incidentRoot 'system_before_recovery.json') -Encoding utf8
$pairs=@()
foreach($n in @('run_config.json','run_manifest.json','history.json','run.log','last.pt','best.pt','process_stdout.log','process_stderr.log')) {$pairs+=@{source=(Join-Path $runRoot $n);target=(Join-Path (Join-Path $incidentRoot 'run') $n)}}
$ledger='C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\runs\frozen_formal_matrix_ledger.json'
$pairs+=@{source=$ledger;target=(Join-Path $incidentRoot 'frozen_formal_matrix_ledger.json')}
foreach($n in @('status.json','pipeline_status.json','extension_status.json','latest_baseline_status.json','independent_comparison_status.json','extension_plan.json','latest_baseline_plan.json','independent_comparison_plan.json','continue_formal_matrix.py','supervise_pipeline.py','supervise_extensions.py','supervise_latest_baselines.py','supervise_independent_comparisons.py','independent_comparison_launch.json','independent_comparisons.stdout.log','independent_comparisons.stderr.log')) {$pairs+=@{source=(Join-Path $executionRoot $n);target=(Join-Path (Join-Path $incidentRoot 'controllers') $n)}}
foreach($n in @('primary','pipeline','extensions','latest')) {foreach($suffix in @('stdout.log','stderr.log')) {$file=$n+'.'+$suffix;$pairs+=@{source=(Join-Path (Join-Path $executionRoot 'memory_recovery_20260914_1300') $file);target=(Join-Path (Join-Path $incidentRoot 'controllers') $file)}}}
$records=@()
foreach($pair in $pairs) {
 Copy-Item -LiteralPath $pair.source -Destination $pair.target
 $digest=(Get-FileHash -LiteralPath $pair.source -Algorithm SHA256).Hash.ToLower()
 if ((Get-FileHash -LiteralPath $pair.target -Algorithm SHA256).Hash.ToLower() -ne $digest) {throw ('Backup mismatch: '+$pair.source)}
 $records += [ordered]@{source=$pair.source;backup=$pair.target;bytes=(Get-Item -LiteralPath $pair.source).Length;sha256=$digest}
}
$records|ConvertTo-Json -Depth 6|Set-Content -LiteralPath (Join-Path $incidentRoot 'backup_manifest.json') -Encoding utf8
Write-Output ('Preserved '+$records.Count+' files with matching SHA; no active state changed.')
