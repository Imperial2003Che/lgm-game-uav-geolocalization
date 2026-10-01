$ErrorActionPreference='Stop'
$reviewDir=Split-Path -Parent $MyInvocation.MyCommand.Path
$outRoot='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914'
$producer=Join-Path $outRoot 'formal_main_native_visio_20260929_2258'
$svg=Join-Path $outRoot 'formal_results_native_20260929'
$ppt=Join-Path $outRoot 'formal_main_native_ppt_20260929_1548'
function Bind-Small([string]$path,[string]$expected='') {
 $item=Get-Item -LiteralPath $path
 if($item.Length -gt 2000000){throw 'Refuse non-small review input'}
 $sha=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
 if($expected -and $sha -cne $expected){throw "Binding changed: $path"}
 [ordered]@{path=$item.FullName;bytes=$item.Length;sha256=$sha}
}
$reportPath=Join-Path $reviewDir 'REVIEW.json'
if(Test-Path -LiteralPath $reportPath){throw 'Refuse replacing an existing independent report'}
$bindings=@(
 (Bind-Small (Join-Path $producer 'build_visio_v2.ps1') 'ea62656245b300cdbd5a306519342c352b997891c84e450b9fd9be4d3ac65665')
 (Bind-Small (Join-Path $producer 'build_visio.ps1') 'ff8d55bcf7b3271cf33b5f2d70fd671cb08dff392281410a90053d005ca35372')
 (Bind-Small (Join-Path $producer 'BUILD_V1_TO_V2.patch') '012f8301ab805290b5aa1885a48a17d6d6e1d7d38673a43e1c70890af170a525')
 (Bind-Small (Join-Path $producer 'prepare_inputs_v2.py') '3203c9584af60bdbc8ec69771e11c874f97932ba0347fe4ad77f66a5ee44e302')
 (Bind-Small (Join-Path $producer 'prepare_inputs.py') 'a5cd8f5f13e8da6a1b82f6099bdf2cf1f650f8853a4a50b2e05bbb6a9489719f')
 (Bind-Small (Join-Path $producer 'PREPARE_V1_TO_V2.patch') '1669b9d940e5a133d2ef3ba2acdb1e4ef45f3b1dc4728af7f1a78967d342951f')
 (Bind-Small (Join-Path $producer 'SOURCE_REVISION.json'))
 (Bind-Small (Join-Path $producer 'CONVERSION_SPEC.json') '3acb5843979a6332f56e3182d1db333c79dbd8d343d7262ea81b796f26ff1816')
 (Bind-Small (Join-Path $producer 'INPUT_PROVENANCE.json'))
 (Bind-Small (Join-Path $producer 'BUILD_FAILURE.json') '17dc7fcd4b454517e35c94456c79e3cc00976707f6fa3de79ab30a5aa7a2b161')
 (Bind-Small (Join-Path $producer 'BUILD_REPORT.json'))
 (Bind-Small (Join-Path $producer 'cleanup_owned_orphan.ps1'))
 (Bind-Small (Join-Path $producer 'OWN_ORPHAN_BEFORE.json') '2d3d3e4255131100da5689222cf9cfc2811c85548bedbd7193b9d2c6f8844838')
 (Bind-Small (Join-Path $producer 'OWN_ORPHAN_CLEANUP.json') 'fced4c2c848d4fdcd8250486ec08e925e8360cb8a45b1da0df333a988a6a3864')
 (Bind-Small (Join-Path $producer 'output_v2\notes\university1652_NOTES.txt') '838adfedd2cd6e776a5b39b5fba91a7fc38a73493749bf45fbc4db53a2bd246b')
 (Bind-Small (Join-Path $producer 'output_v2\notes\sues200_NOTES.txt') '0d66a71d7a1b549bd9177652a8ddadc9132dcabf7c6a2200e8a54850f74ac992')
 (Bind-Small (Join-Path $svg 'v2\CAPTIONS.md') '2dd6fef4c13f2348256b68ede5e099e51ae307b65b93b0ead3afcc88cd3697a9')
 (Bind-Small (Join-Path $svg 'PRIMARY_CLAIM_REVIEW.md'))
 (Bind-Small (Join-Path $svg 'PRIMARY_CLAIM_REVIEW.json') '0e29cdb0412b148100788b02276e9a9ef4a7aed4a1f5d892fb088a0ff184cdb6')
 (Bind-Small (Join-Path $svg 'ROOT_NATIVE_SVG_REVIEW.json') 'ac010cc27c27fa94a9fdd3e860af84c330a8e4cc6efa3c66b2e6a8000d6253ca')
 (Bind-Small (Join-Path $svg 'INDEPENDENT_NATIVE_SVG_REVIEW.json') '9dbcc7f38df2057e900f8a13571b00eadb867d2e890e8948f3eea6e1f6501977')
 (Bind-Small (Join-Path $ppt 'ROOT_DELIVERY_ADOPTION.json') '4d01ad9310e8d726e7a0b5e9852142a51f56a079a30e386d814161f8b328787b')
 (Bind-Small (Join-Path $ppt 'README.md'))
 (Bind-Small (Join-Path $ppt 'build\build_native_v2.mjs') '16933b51afc22c0cb2f52b626946927c6cab635a2ad7fe126e0ef27b343959b9')
)
$result=[ordered]@{
 schema='formal-main-native-visio-static-scope-review.v1'
 reviewed_at_utc=[DateTimeOffset]::UtcNow.ToString('o')
 reviewer='independent subagent sep29_recovery_review'
 scope='Complete static review of both preparation versions and both COM builders/diff; accepted figure caption/notes scope; small producer receipts read only.'
 disposition='Normal-path two-figure scope is consistent; v2 is not approved for unrestricted reuse because two unexercised ownership/exit-attribution error paths remain.'
 normal_path_scope_consistent=$true
 unrestricted_builder_reuse_approved=$false
 application_execution_performed_here=$false
 live_process_observation_performed_here=$false
 artifact_package_or_visual_audit_performed_here=$false
 scientific_or_numeric_reexecution_performed_here=$false
 root_adoption=$false
 inheritance=[ordered]@{figures=2;heatmap_cells=66;mAP_intervals=66;svg_primitives=785;text_elements=216;seeds=@(1,2,3);sample_sd_not_ci=$true;task_pooling=$false;negative_full_results_retained=$true;exact_notes_sidecars_preserved=$true;counts_source='Accepted source contracts; not scientifically recalculated in this static review.'}
 reviewed_source_ranges=@(
  [ordered]@{file='prepare_inputs_v2.py';first_line=11;last_line=18;purpose='Pinned accepted source and current limitations'}
  [ordered]@{file='prepare_inputs_v2.py';first_line=20;last_line=39;purpose='Full primitives and original PPT notes/CSV to sidecar and spec'}
  [ordered]@{file='build_visio_v2.ps1';first_line=24;last_line=45;purpose='New invisible instance, HWND mapping, exact creation identity, own-handle quit'}
  [ordered]@{file='build_visio_v2.ps1';first_line=50;last_line=87;purpose='New-document native primitives/Text and page metadata'}
  [ordered]@{file='build_visio_v2.ps1';first_line=90;last_line=117;purpose='Save, read-only re-open, exports, cleanup and producer receipt'}
 )
 residual_findings=@(
  [ordered]@{id='V2_ERRORPATH_OWNERSHIP';line=26;guard_line=30;cleanup_line=112;finding='owned=true precedes rejection of an initial PID; the rejected reference could be Quit by finally.';condition_in_current_receipt='Not entered: initialVisio empty and two created identities succeeded.';future_requirement='Do not Quit a reference whose ownership gate rejected it.'}
  [ordered]@{id='V2_ERRORPATH_STALE_HANDLE';line=24;cleanup_line=112;finding='ownHandle is not reset before second creation; metadata failure before new assignment could use first-instance exited handle.';condition_in_current_receipt='Not entered: both created records include their own handle ticks and corresponding Quit records.';future_requirement='Reset per-instance handle; bind exit attribution to that exact instance.'}
 )
 producer_receipts_only=[ordered]@{
  first_rejected_source_failure='Visio ProcessID wrongly treated as Windows PID; failed before document creation. Root diagnosed official API semantics; not merely CIM timing.'
  initial_visio_count=0
  successful_windows_pids=@(42148,36900)
  visio_internal_ids=@(4293,4309)
  cim_utc_ticks=@('639263163606499000','639263163886803500')
  handle_utc_ticks=@('639263163606499001','639263163886803504')
  producer_reported_held_quit_exit_codes=@(0,0)
  separately_authorized_own_orphan=[ordered]@{pid=18044;parent=2224;reported_forced_exit_code=-1;not_natural_exit0=$true;cleanup_executed_here=$false}
  independent_handle_observation_here=$false
 }
 interpretation_limits=@(
  'No scientific revalidation; existing checkpoint/cache/image SHA inheritance and historical chain gaps remain.'
  'Flat native shapes/Text are not a linked chart, editable SVG hierarchy, or automatic CSV-driven recalculation.'
  'User cells and Data1/2/3 are metadata; their complete VSDX round-trip and all geometry require the separate artifact review.'
  'Only two main-result figures; not all Visio figures or final project/paper delivery.'
  'Source statements and read producer receipts do not constitute independent current process observations.'
  'No GPU gate, recovery, native scientific launcher, live-state, release, intent, lock, user application, or system setting action was performed by this reviewer.'
 )
 primary_api_references=@(
  'https://learn.microsoft.com/en-us/office/vba/api/visio.invisibleapp'
  'https://learn.microsoft.com/en-us/office/vba/api/visio.application.processid'
  'https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindowthreadprocessid'
  'https://learn.microsoft.com/en-us/office/vba/api/visio.application.quit'
  'https://learn.microsoft.com/en-us/office/vba/api/visio.document.saveasex'
  'https://learn.microsoft.com/en-us/office/vba/api/visio.shape.data1'
 )
 source_and_small_file_bindings=$bindings
 review_markdown=(Bind-Small (Join-Path $reviewDir 'REVIEW.md'))
 sealing_source=(Bind-Small $MyInvocation.MyCommand.Path)
}
$stream=[IO.File]::Open($reportPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
try{$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($result|ConvertTo-Json -Depth 20)+"`n");$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
Bind-Small $reportPath | ConvertTo-Json -Depth 4
