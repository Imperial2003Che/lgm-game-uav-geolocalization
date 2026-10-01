$ErrorActionPreference='Stop'
$episode='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\visio_full_xsd_research_20260930_1730'
$sourceChm='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\schema_package_research_20260930_1228\sdk_chm_data\VISSDK.CHM'
$attempt='C:\Users\17703\AppData\Local\Temp\LGM_GAME_CHM_20260930_1745_1730_ascii_v1'
$chm=Join-Path $attempt 'input\VISSDK.CHM'
$dest=Join-Path $attempt 'decompiled_data'
$identityPython='C:\Users\17703\AppData\Local\Programs\Python\Python311\python.exe'
$samefileCode='import os,sys,json;a,b=sys.argv[1:];sa=os.stat(a);sb=os.stat(b);print(json.dumps({"samefile":os.path.samefile(a,b),"source_dev":str(sa.st_dev),"source_ino":str(sa.st_ino),"alias_dev":str(sb.st_dev),"alias_ino":str(sb.st_ino),"source_bytes":sa.st_size,"alias_bytes":sb.st_size}))'
$exe='C:\Windows\hh.exe'
function Write-NewJson([string]$path,$obj){
  $raw=[Text.UTF8Encoding]::new($false).GetBytes(($obj|ConvertTo-Json -Depth 12)+"`n")
  $stream=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
  try{$stream.Write($raw,0,$raw.Length);$stream.Flush($true)}finally{$stream.Dispose()}
}
function File-Binding([string]$path){$item=Get-Item -LiteralPath $path;return [ordered]@{path=$item.FullName;bytes=[int64]$item.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
if(Test-Path -LiteralPath $attempt){throw 'Attempt already exists; no replay permitted'}
if(Test-Path -LiteralPath $dest){throw 'Output already exists'}
$inputBefore=File-Binding $sourceChm
if($inputBefore.bytes -ne 6764354 -or $inputBefore.sha256 -cne '19a74be23751db246fdf047d49a187187074113ad9095febd0cb640dba465a4a'){throw 'CHM bytes differ from adopted extraction'}
$source=File-Binding $PSCommandPath
$system=File-Binding $exe
function Check-SameFile{
  $samefileRaw=@(& $identityPython -I -S -B -X utf8 -c $samefileCode $sourceChm $chm)
  $samefileExit=$LASTEXITCODE
  if($samefileExit -ne 0){throw ('samefile metadata process returned '+$samefileExit)}
  $samefile=($samefileRaw -join [Environment]::NewLine)|ConvertFrom-Json
  if(($samefile.samefile -isnot [bool]) -or ($samefile.samefile -ne $true)){throw 'Hardlink is not os.path.samefile'}
  if($samefile.source_bytes -ne 6764354 -or $samefile.alias_bytes -ne 6764354){throw 'samefile size changed'}
  return [ordered]@{ordinary_metadata_exit=[int]$samefileExit;value=$samefile}
}
# This fresh ASCII task directory is single use; a hardlink failure retains it without fallback.
[void][IO.Directory]::CreateDirectory($attempt)
$declaration=[ordered]@{schema='official-sdk-chm-ascii-hardlink-declaration.v1';utc=[DateTime]::UtcNow.ToString('o');source=$source;original_input=$inputBefore;system_executable=$system;ascii_attempt=$attempt;ascii_input=$chm;ascii_output=$dest;single_use=$true;hardlink_only=$true;fallback_copy_permitted=$false;HH_not_yet_started=$true;scope='Separate necessary ASCII-path data extraction after root source review; does not diagnose cause of prior zero-output run'}
Write-NewJson (Join-Path $attempt 'ATTEMPT_DECLARATION.json') $declaration
try{
  [void][IO.Directory]::CreateDirectory((Join-Path $attempt 'input'))
  [void](New-Item -ItemType HardLink -Path $chm -Target $sourceChm -ErrorAction Stop)
  $samefileBefore=Check-SameFile
  $aliasBefore=File-Binding $chm
  if($aliasBefore.bytes -ne $inputBefore.bytes -or $aliasBefore.sha256 -cne $inputBefore.sha256){throw 'Hardlink bytes differ from original'}
}catch{
  Write-NewJson (Join-Path $attempt 'HARDLINK_FAILURE.json') ([ordered]@{schema='official-sdk-chm-ascii-hardlink-failure.v1';utc=[DateTime]::UtcNow.ToString('o');error=$_.Exception.ToString();HH_started=$false;fallback_copy=$false;cleanup=$false;single_use_consumed=$true})
  throw
}
$command=@($exe,'-decompile',$dest,$chm)
$entry=[ordered]@{schema='official-sdk-chm-system-data-decompile-entry.v1';utc=[DateTime]::UtcNow.ToString('o');source=$source;input=$aliasBefore;original_input=$inputBefore;os_path_samefile_before=$samefileBefore;system_executable=$system;argument_vector=$command;attempt_absent_before=$true;destination_absent_before=$true;timeout_ms=60000;single_use=$true;root_authorization='Task root explicitly allowed this separate necessary ASCII hardlink extraction after full new source/delta review; no default viewer/OfficeCOM/installer/downloaded code/HTML execution; prior HH attempt preserved';scope='Data extraction only; no Visio VSDX application/schema/scientific acceptance'}
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
  $result.original_input_after=File-Binding $sourceChm
  $result.os_path_samefile_after=Check-SameFile
  $result.input_unchanged=($inputAfter.bytes -eq $inputBefore.bytes -and $inputAfter.sha256 -ceq $inputBefore.sha256 -and $result.original_input_after.bytes -eq $inputBefore.bytes -and $result.original_input_after.sha256 -ceq $inputBefore.sha256)
  if(-not $result.input_unchanged){throw 'CHM changed across extraction'}
  $files=@(Get-ChildItem -LiteralPath $dest -File -Recurse)
  $result.extracted_file_count=$files.Count
  $result.extracted_total_bytes=[int64](($files|Measure-Object -Property Length -Sum).Sum)
  $result.member_contents_not_yet_audited=$true
  $result.complete_schema_collection_obtained=$false
  $result.completed_utc=[DateTime]::UtcNow.ToString('o')
}catch{$result.error=$_.Exception.ToString();$result.completed_utc=[DateTime]::UtcNow.ToString('o')}
finally{
  if($p -and ($result.process_exit_confirmed -is [bool]) -and ($result.process_exit_confirmed -eq $true)){$p.Dispose();$result.returned_process_object_disposed_after_exit=$true}else{$result.returned_process_object_disposed_after_exit=$false}
  Write-NewJson (Join-Path $attempt 'RESULT.json') $result
}
$binding=File-Binding (Join-Path $attempt 'RESULT.json')
$binding|ConvertTo-Json -Depth 4
if($result.error -or $result.process_exit_code -ne 0){exit 1}
