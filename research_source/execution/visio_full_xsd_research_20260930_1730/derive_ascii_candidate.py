from pathlib import Path
import hashlib,json,difflib,datetime
base=Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\visio_full_xsd_research_20260930_1730')
old=base/'decompile_sdk_chm_once_v3.ps1'
raw=old.read_bytes()
assert len(raw)==5536 and hashlib.sha256(raw).hexdigest()=='bede70805473de74ae7c59e9eab96304590dc6227fa4fd252bee3735aabac0cf'
data=raw.decode('utf-8')
source_chm=r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\schema_package_research_20260930_1228\sdk_chm_data\VISSDK.CHM'
ascii_root=r'C:\Users\17703\AppData\Local\Temp\LGM_GAME_CHM_20260930_1745_1730_ascii_v1'
needle="$chm='"+source_chm+"'\n$attempt=Join-Path $episode 'hh_decompile_attempt_v1'\n$dest=Join-Path $attempt 'decompiled_data'"
replacement="$sourceChm='"+source_chm+"'\n$attempt='"+ascii_root+"'\n$chm=Join-Path $attempt 'input\\VISSDK.CHM'\n$dest=Join-Path $attempt 'decompiled_data'\n$identityPython='C:\\Users\\17703\\AppData\\Local\\Programs\\Python\\Python311\\python.exe'\n$samefileCode='import os,sys,json;a,b=sys.argv[1:];sa=os.stat(a);sb=os.stat(b);print(json.dumps({\"samefile\":os.path.samefile(a,b),\"source_dev\":str(sa.st_dev),\"source_ino\":str(sa.st_ino),\"alias_dev\":str(sb.st_dev),\"alias_ino\":str(sb.st_ino),\"source_bytes\":sa.st_size,\"alias_bytes\":sb.st_size}))'"
assert data.count(needle)==1
data=data.replace(needle,replacement,1)
needle="$inputBefore=File-Binding $chm"
replacement="$inputBefore=File-Binding $sourceChm"
assert data.count(needle)==1
data=data.replace(needle,replacement,1)
needle="$command=@($exe,'-decompile',$dest,$chm)"
replacement="""function Check-SameFile{
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
$command=@($exe,'-decompile',$dest,$chm)"""
assert data.count(needle)==1
data=data.replace(needle,replacement,1)
needle="input=$inputBefore;system_executable=$system;"
replacement="input=$aliasBefore;original_input=$inputBefore;os_path_samefile_before=$samefileBefore;system_executable=$system;"
assert data.count(needle)==1
data=data.replace(needle,replacement,1)
needle="root_authorization='Task root explicitly allowed one system hh.exe -decompile data extraction; no default viewer/OfficeCOM/installer/downloaded code/HTML execution'"
replacement="root_authorization='Task root explicitly allowed this separate necessary ASCII hardlink extraction after full new source/delta review; no default viewer/OfficeCOM/installer/downloaded code/HTML execution; prior HH attempt preserved'"
assert data.count(needle)==1
data=data.replace(needle,replacement,1)
needle="[void][IO.Directory]::CreateDirectory($attempt)\nWrite-NewJson (Join-Path $attempt 'ENTRY.json') $entry"
replacement="Write-NewJson (Join-Path $attempt 'ENTRY.json') $entry"
assert data.count(needle)==1
data=data.replace(needle,replacement,1)
needle="$result.input_after=$inputAfter\n  $result.input_unchanged=($inputAfter.bytes -eq $inputBefore.bytes -and $inputAfter.sha256 -ceq $inputBefore.sha256)"
replacement="$result.input_after=$inputAfter\n  $result.original_input_after=File-Binding $sourceChm\n  $result.os_path_samefile_after=Check-SameFile\n  $result.input_unchanged=($inputAfter.bytes -eq $inputBefore.bytes -and $inputAfter.sha256 -ceq $inputBefore.sha256 -and $result.original_input_after.bytes -eq $inputBefore.bytes -and $result.original_input_after.sha256 -ceq $inputBefore.sha256)"
assert data.count(needle)==1
data=data.replace(needle,replacement,1)
new=base/'decompile_sdk_chm_ascii_candidate.ps1'
out=data.encode('utf-8')
with new.open('xb') as f:f.write(out)
patch=''.join(difflib.unified_diff(raw.decode('utf-8').splitlines(True),data.splitlines(True),fromfile=old.name,tofile=new.name))
patch_path=base/'decompile_v3_to_ascii_candidate.patch'
with patch_path.open('xb') as f:f.write(patch.encode('utf-8'))
contract={'schema':'official-sdk-chm-ascii-candidate-source-contract.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':{'path':str(new),'bytes':len(out),'sha256':hashlib.sha256(out).hexdigest()},'parent':{'path':str(old),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},'complete_delta':{'path':str(patch_path),'bytes':len(patch.encode('utf-8')),'sha256':hashlib.sha256(patch.encode('utf-8')).hexdigest()},'ascii_attempt':ascii_root,'original_chm':source_chm,'expected_CHM_bytes':6764354,'expected_CHM_sha256':'19a74be23751db246fdf047d49a187187074113ad9095febd0cb640dba465a4a','samefile_mechanism':'Native PowerShell hardlink only, os.path.samefile via ordinary isolated Python stdlib before and after HH plus exact SHA/size; no fallback copy','runtime_scope':'One new system HH -decompile with ASCII input/output arguments only; hidden/same returned Process held WaitForExit<=60000/same-object actual exit and closed output. Preserve any new attempt including hardlink failure; no cleanup or replay. Does not prove original zero-output cause, scientific dual exits or Office figure acceptance.','not_executed':True,'Temp_directory_not_created_by_derivation':True,'schema_full_collection_obtained':False,'root_review_and_separate_start_decision_required':True}
with (base/'ASCII_CANDIDATE_SOURCE_CONTRACT.json').open('xb') as f:f.write((json.dumps(contract,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
print(json.dumps({'source':contract['source'],'patch':contract['complete_delta'],'contract':str(base/'ASCII_CANDIDATE_SOURCE_CONTRACT.json'),'Temp_attempt_exists_now':Path(ascii_root).exists(),'HH_executed':False},ensure_ascii=False))

