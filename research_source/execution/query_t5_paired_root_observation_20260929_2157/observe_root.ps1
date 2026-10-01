$ErrorActionPreference='Stop'
$ex='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$capturePath=Join-Path $ex 'efficiency_incident_20260929_1448\capture_20260929_144939892\CAPTURE.json'
$capture=Get-Content -LiteralPath $capturePath -Raw | ConvertFrom-Json -DateKind String
$chosen=@($capture.bindings | Where-Object { $_.source.path -match '\\(status|pipeline_status|extension_status|latest_baseline_status|independent_comparison_status)\.json$' -or $_.source.path -match '\\host_recovery_20260929_0341\\.*\.(stdout|stderr)\.log$' -or $_.source.path -match '\\formal_efficiency_component\.(stdout|stderr)\.log$' -or $_.source.path -match '\\io_retry_pipeline_14420\.jsonl$' })
$files=@(foreach($binding in $chosen){
  $s=$binding.source; $f=Get-Item -LiteralPath $s.path; $h=(Get-FileHash -LiteralPath $s.path -Algorithm SHA256).Hash.ToLowerInvariant()
  if($f.Length -ne $s.bytes -or $h -ne $s.sha256){throw ('Changed stopped evidence: '+$s.path)}
  $row=[ordered]@{path=$s.path;sha256=$h;bytes=$f.Length}
  if($f.Extension -eq '.json'){$state=Get-Content -LiteralPath $f.FullName -Raw | ConvertFrom-Json -DateKind String;$row.status=$state.status;$row.heartbeat_utc=$state.heartbeat_utc}
  [pscustomobject]$row
})
function Observe-Processes {
  $seen=Get-Date -Format o
  $matches=@(Get-CimInstance Win32_Process | Where-Object {
    $_.ProcessId -ne $PID -and ($_.ProcessId -in @(33924,31992,14420,29784,30388,7584,33520,12896,7484,21652,24120,40780,37764,14260,43500,40968,23920) -or
    ($_.CommandLine -match '(run_formal|formal_reproduction|pipeline_supervisor|extension_supervisor|latest_baseline_supervisor|independent_comparison_supervisor|pipeline_recovery_candidate|start_pipeline_recovery_candidate|restart_after_host_interruption|run_frozen|formal_efficiency_component|train_retrieval|train_camp|train_dac|run_baseline|run_independent|resume_formal)' -and $_.Name -match '^(python|pythonw|pwsh|powershell)\.exe$'))
  } | ForEach-Object {[ordered]@{pid=[int]$_.ProcessId;parent_pid=[int]$_.ParentProcessId;creation_utc=$_.CreationDate.ToUniversalTime().ToString('o');creation_utc_ticks=$_.CreationDate.ToUniversalTime().Ticks.ToString();name=$_.Name;command_line=$_.CommandLine}})
  [ordered]@{observed_at=$seen;matches=$matches}
}
$first=Observe-Processes
Start-Sleep -Milliseconds 400
$second=Observe-Processes
$carrierPath=Join-Path $ex 'latest_baseline_gpu.lock'
$carrier=Get-Item -LiteralPath $carrierPath
$carrierBytes=[System.IO.File]::ReadAllBytes($carrierPath)
if($carrierBytes.Length -ne 1 -or $carrierBytes[0] -ne 48 -or $carrier.CreationTimeUtc.Ticks -ne [long]'639262940518466959'){throw 'Shared carrier changed'}
$report=[ordered]@{schema='root-stopped-transfer-artifact-observation.v1';time=(Get-Date -Format o);source=@{path=$PSCommandPath;sha256=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()};capture=@{path=$capturePath;sha256=(Get-FileHash -LiteralPath $capturePath -Algorithm SHA256).Hash.ToLowerInvariant()};files=$files;first=$first;second=$second;excluded_process_id=[int]$PID;carrier=@{path=$carrierPath;bytes=1;byte_value=48;sha256=(Get-FileHash -LiteralPath $carrierPath -Algorithm SHA256).Hash.ToLowerInvariant();creation_utc_ticks=$carrier.CreationTimeUtc.Ticks.ToString()};boot_utc=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString('o');limits=@('Read-only state/log/carrier/identity observation. No native import, GPU measurement, lock acquisition, release or scientific launch.','Absence does not prove independent interpreter exit code. Any nonempty process result requires exact identity review before recovery.')}
$out=Join-Path $PSScriptRoot 'ROOT_STOPPED_OBSERVATION.json'
$json=$report | ConvertTo-Json -Depth 20
$stream=[System.IO.File]::Open($out,[System.IO.FileMode]::CreateNew,[System.IO.FileAccess]::Write,[System.IO.FileShare]::Read)
try{$b=[System.Text.UTF8Encoding]::new($false).GetBytes($json+"`n");$stream.Write($b,0,$b.Length)}finally{$stream.Dispose()}
[ordered]@{path=$out;sha256=(Get-FileHash -LiteralPath $out -Algorithm SHA256).Hash.ToLowerInvariant();files=$files.Count;first=$first;second=$second;time=$report.time;carrier=$report.carrier} | ConvertTo-Json -Depth 10
