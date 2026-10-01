$ErrorActionPreference='Stop'
$executionRoot='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$incidentRoot=Join-Path $executionRoot 'memory_recovery_20260914_1424'
$samples=@()
for($i=0;$i -lt 18;$i++){
 $s=Get-Content -LiteralPath (Join-Path $executionRoot 'status.json') -Raw|ConvertFrom-Json
 $memory=Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory|Select-Object AvailableMBytes,CommittedBytes,CommitLimit
 $owners=@(Get-CimInstance Win32_Process -Filter "Name='python.exe'"|Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine)
 $footprints=@(Get-CimInstance Win32_PerfFormattedData_PerfProc_Process|Where-Object {$_.Name -like 'python*'}|Select-Object Name,IDProcess,PrivateBytes,WorkingSet)
 $samples += [ordered]@{local_time=(Get-Date).ToString('o');status=$s.status;active_output_dir=$s.active.output_dir;active_started_utc=$s.active.started_utc;progress=$s.active_progress;memory=$memory;python_processes=$owners;python_memory=$footprints}
 $report=[ordered]@{schema='memory-recovery-observation.v1';sample_count=$samples.Count;samples=$samples;note='System-wide commit, not a controlled process attribution experiment. No science imports or new GPU work.'}
 $report|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $incidentRoot 'memory_recovery_observation.json') -Encoding utf8
 if($s.status -ne 'running'){Write-Output ('Controller state: '+$s.status);break}
 if($s.active_progress.history_rows -ge 19){Write-Output ('New complete epochs: '+$s.active_progress.history_rows);break}
 Start-Sleep -Seconds 10
}
Write-Output ('Saved '+$samples.Count+' lightweight memory observations.')
