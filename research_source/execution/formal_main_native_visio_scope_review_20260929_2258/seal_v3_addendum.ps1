$ErrorActionPreference='Stop'
$reviewDir=Split-Path -Parent $MyInvocation.MyCommand.Path
$producer='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\formal_main_native_visio_20260929_2258'
function Bind-Small([string]$path,[string]$expected='') {
 $item=Get-Item -LiteralPath $path
 if($item.Length -gt 2000000){throw 'Refuse non-small static input'}
 $sha=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
 if($expected -and $sha -cne $expected){throw "Source binding changed: $path"}
 [ordered]@{path=$item.FullName;bytes=$item.Length;sha256=$sha}
}
$target=Join-Path $reviewDir 'V3_ADDENDUM.json'
if(Test-Path -LiteralPath $target){throw 'Refuse overwrite'}
$record=[ordered]@{
 schema='formal-main-native-visio-unexecuted-hardening-static-addendum.v1'
 reviewed_at_utc=[DateTimeOffset]::UtcNow.ToString('o')
 reviewer='independent subagent sep29_recovery_review'
 original_review=(Bind-Small (Join-Path $reviewDir 'REVIEW.json') '5f21400c74515f1d0aa0cef0f09d7853f8bab15e80497dda35982d324db939aa')
 disposition='The two specifically reported v2 ownership/stale-handle defects are corrected at source level in v3. Future-only; no execution or comprehensive Windows failure-case validation.'
 full_v3_source_and_diff_read=$true
 actual_application_execution_performed_here=$false
 runtime_or_control_tests_performed_here=$false
 figure_regenerated_here=$false
 v3_produced_delivered_figures=$false
 scientific_execution=$false
 root_adoption=$false
 resolved_source_findings=@(
  [ordered]@{id='V2_ERRORPATH_STALE_HANDLE';v3_lines=@(26,27);resolution='NewOwnedApp clears per-instance app/ownership/ownHandle before creation.'}
  [ordered]@{id='V2_ERRORPATH_OWNERSHIP';v3_lines=@(32,33,34,35,36,37,38,115);resolution='Ownership after HWND/non-initial/CIM/held-ticks gates; rejected or unconfirmed reference gets release without Quit.'}
 )
 limitations=@(
  'Only source-level remediation is reviewed; no real Windows/COM branch or new suite was executed.'
  'Unknown ownership intentionally permits no process termination; separately evidenced handling could remain necessary.'
  'Catch writes failure JSON before finally; finally-only release events are not necessarily persisted in that receipt.'
  'COM reference release is not independent proof of operating-system process exit.'
  'Actual VSDX outputs and producer held exit0 receipts remain v2, not v3.'
  'No blanket launch, process-termination, recovery, native-scientific, system-setting, or user-application authorization is created.'
 )
 source_and_small_file_bindings=@(
  (Bind-Small (Join-Path $producer 'build_visio_v3_unexecuted.ps1') 'e17a9c81680de7b9af5830f021b3481c8edfb414bf7ae7f4d0b03de9a15e728f')
  (Bind-Small (Join-Path $producer 'BUILD_V2_TO_V3_UNEXECUTED.patch') 'bb81fee508eeeeb2a5a90be233b406288df8cb7097afb1d6a9bbbcbf6ecf7cc1')
  (Bind-Small (Join-Path $producer 'UNEXECUTED_HARDENING.json'))
  (Bind-Small (Join-Path $producer 'build_visio_v2.ps1') 'ea62656245b300cdbd5a306519342c352b997891c84e450b9fd9be4d3ac65665')
  (Bind-Small (Join-Path $producer 'BUILD_REPORT.json') 'cd6be22fe4adbb490422014d965b7ebf1ac89d224362cbf1ec931bd575a605ca')
 )
 review_markdown=(Bind-Small (Join-Path $reviewDir 'V3_ADDENDUM.md'))
 sealing_source=(Bind-Small $MyInvocation.MyCommand.Path)
}
$stream=[IO.File]::Open($target,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
try{$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($record|ConvertTo-Json -Depth 20)+"`n");$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
Bind-Small $target | ConvertTo-Json -Depth 4
