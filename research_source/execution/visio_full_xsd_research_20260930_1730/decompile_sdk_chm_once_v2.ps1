$ErrorActionPreference='Stop'
$episode='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\visio_full_xsd_research_20260930_1730'
$chm='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\schema_package_research_20260930_1228\sdk_chm_data\VISSDK.CHM'
$attempt=Join-Path $episode 'hh_decompile_attempt_v1'
$dest=Join-Path $attempt 'decompiled_data'
$exe='C:\Windows\hh.exe'
function Write-NewJson([string]$path,$obj){
  $raw=[Text.UTF8Encoding]::new($false).GetBytes(($obj|ConvertTo-Json -Depth 12)+"`n")
  $stream=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
  try{$stream.Write($raw,0,$raw.Length);$stream.Flush($true)}finally{$stream.Dispose()}
}
function File-Binding([string]$path){$item=Get-Item -LiteralPath $path;return [ordered]@{path=$item.FullName;bytes=[int64]$item.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
if(Test-Path -LiteralPath $attempt){throw 'Attempt already exists; no replay permitted'}
if(Test-Path -LiteralPath $dest){throw 'Output already exists'}
$inputBefore=File-Binding $chm
if($inputBefore.bytes -ne 6764354 -or $inputBefore.sha256 -cne '19a74be23751db246fdf047d49a187187074113ad9095febd0cb640dba465a4a'){throw 'CHM bytes differ from adopted extraction'}
$source=File-Binding $PSCommandPath
$system=File-Binding $exe
$command=@($exe,'-decompile',$dest,$chm)
$entry=[ordered]@{schema='official-sdk-chm-system-data-decompile-entry.v1';utc=[DateTime]::UtcNow.ToString('o');source=$source;input=$inputBefore;system_executable=$system;argument_vector=$command;attempt_absent_before=$true;destination_absent_before=$true;timeout_ms=60000;single_use=$true;root_authorization='Task root explicitly allowed one system hh.exe -decompile data extraction; no default viewer/OfficeCOM/installer/downloaded code/HTML execution';scope='Data extraction only; no Visio VSDX application/schema/scientific acceptance'}
[void][IO.Directory]::CreateDirectory($attempt)
Write-NewJson (Join-Path $attempt 'ENTRY.json') $entry
[void][IO.Directory]::CreateDirectory($dest)
$stdout=Join-Path $attempt 'hh.stdout.log'
$stderr=Join-Path $attempt 'hh.stderr.log'
$events=[Collections.Generic.List[object]]::new()
$result=[ordered]@{schema='official-sdk-chm-system-data-decompile-result.v1';started_utc=[DateTime]::UtcNow.ToString('o');source=$source;entry=File-Binding (Join-Path $attempt 'ENTRY.json');argument_vector=$command;events=$events;process_exit_code=$null;process_exit_confirmed=$false;ordinary_system_process_only=$true;scientific_dual_exit_evidence=$false;downloaded_payload_executed=$false;default_help_viewer_requested=$false;Office_COM=$false;schema_validation=$false;application_validation=$false;science=$false;timed_out=$false;error=$null}
$p=$null
try{
  $argumentString='-decompile "'+$dest+'" "'+$chm+'"'
  $p=Start-Process -FilePath $exe -ArgumentList $argumentString -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
  $handle=$p.Handle
  $identity=[ordered]@{pid=$p.Id;held_process_handle_decimal=$handle.ToInt64().ToString();handle_obtained=$true;creation_utc=$p.StartTime.ToUniversalTime().ToString('o');creation_utc_ticks=$p.StartTime.ToUniversalTime().Ticks.ToString();captured_utc=[DateTime]::UtcNow.ToString('o');handle_scope='Same returned System.Diagnostics.Process object; ordinary system extraction child, not scientific launcher/interpreter pair'}
  $events.Add([ordered]@{kind='process_identity';value=$identity})
  Write-NewJson (Join-Path $attempt 'LIVE_PROCESS_IDENTITY.json') $identity
  $ended=$p.WaitForExit(60000)
  $events.Add([ordered]@{kind='wait';utc=[DateTime]::UtcNow.ToString('o');timeout_ms=60000;returned=$ended})
  if(-not $ended){$result.timed_out=$true;throw 'Extraction wait timed out; preserve attempt and process, no kill or replay'}
  # An extra wait on the already-signalled same process closes redirected asynchronous streams.
  $p.WaitForExit()
  $result.process_exit_code=$p.ExitCode
  $result.process_exit_confirmed=$true
  $result.process_exit_utc=$p.ExitTime.ToUniversalTime().ToString('o')
  $result.process_exit_utc_ticks=$p.ExitTime.ToUniversalTime().Ticks.ToString()
  $result.stdout=File-Binding $stdout
  $result.stderr=File-Binding $stderr
  $result.streams_read_after_signalled_process=$true
  $inputAfter=File-Binding $chm
  $result.input_after=$inputAfter
  $result.input_unchanged=($inputAfter.bytes -eq $inputBefore.bytes -and $inputAfter.sha256 -ceq $inputBefore.sha256)
  if(-not $result.input_unchanged){throw 'CHM changed across extraction'}
  $files=@(Get-ChildItem -LiteralPath $dest -File -Recurse)
  $result.extracted_file_count=$files.Count
  $result.extracted_total_bytes=[int64](($files|Measure-Object -Property Length -Sum).Sum)
  $result.member_contents_not_yet_audited=$true
  $result.complete_schema_collection_obtained=$false
  $result.completed_utc=[DateTime]::UtcNow.ToString('o')
}catch{$result.error=$_.Exception.ToString();$result.completed_utc=[DateTime]::UtcNow.ToString('o')}
finally{
  if($p -and $result.process_exit_confirmed){$p.Dispose();$result.returned_process_object_disposed_after_exit=$true}else{$result.returned_process_object_disposed_after_exit=$false}
  Write-NewJson (Join-Path $attempt 'RESULT.json') $result
}
$binding=File-Binding (Join-Path $attempt 'RESULT.json')
$binding|ConvertTo-Json -Depth 4
if($result.error -or $result.process_exit_code -ne 0){exit 1}
