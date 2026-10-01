$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$e=Split-Path -Parent $PSScriptRoot
$b=Join-Path $e 'external_efficiency_preparation\newer_native_ranking_v1'
$dest=Join-Path $PSScriptRoot 'ROOT_SOURCE_ADOPTION.json'
if(Test-Path -LiteralPath $dest){throw 'Adoption already exists'}
$checks=[System.Collections.Generic.List[object]]::new()
function ReadJ($p){Get-Content -LiteralPath $p -Raw|ConvertFrom-Json -DateKind String}
function Bind($p,$expected,$size=-1){
 if([IO.Path]::GetExtension($p) -in '.pt','.pth','.ckpt'){throw 'No checkpoint reads'}
 $before=Get-Item -LiteralPath $p
 $sha=(Get-FileHash -LiteralPath $p).Hash.ToLowerInvariant()
 $after=Get-Item -LiteralPath $p
 if($sha -cne $expected -or ($size -ge 0 -and $before.Length -ne $size) -or $before.Length -ne $after.Length -or $before.LastWriteTimeUtc.Ticks -ne $after.LastWriteTimeUtc.Ticks){throw ('Binding mismatch '+$p)}
 $checks.Add([ordered]@{path=$p;bytes=$after.Length;sha256=$sha})
}
function Assert($ok,$why){if(-not $ok){throw $why}}
$manifestPath=Join-Path $b 'SOURCE_MANIFEST.json'
$reviewPath=Join-Path $PSScriptRoot 'INDEPENDENT_SOURCE_REVIEW.json'
Bind $manifestPath '6cd6aa011d4c996160adfdf81ad42c9c27692727c4b141bb9b64f6ff56740922'
Bind (Join-Path $b 'PREPARATION_REPORT.json') 'd1a8d33213137aeb4e854380bba3d5b7ec3d76447cbabfc6961637513471bb83'
Bind $reviewPath '5522e087cfeb44bc3d1cfaad90d4a3eb74d226520952084834d7c8803fe491fa'
$manifest=ReadJ $manifestPath
$prep=ReadJ (Join-Path $b 'PREPARATION_REPORT.json')
$review=ReadJ $reviewPath
foreach($item in $manifest.files){Bind $item.path $item.sha256 $item.bytes}
foreach($prop in $prep.existing_manifests.PSObject.Properties){$item=$prop.Value;Bind $item.path $item.sha256 $item.bytes}
foreach($item in $review.inspected_sources){Bind $item.path $item.sha256 $item.bytes}
Bind $review.reviewer_script.path $review.reviewer_script.sha256 $review.reviewer_script.bytes
Bind $review.author_changed_interface_control_report.path $review.author_changed_interface_control_report.sha256 $review.author_changed_interface_control_report.bytes
$control=ReadJ $review.author_changed_interface_control_report.path
Assert ($manifest.status -ceq 'source_preparation_only_not_registered_not_released' -and $review.status -ceq 'passed_for_source_preparation_only') 'Wrong source-only status'
Assert ($manifest.runtime_source_sha256 -ceq 'd0dca4cf031b312c770c12dc653f5a47577c94e191b1f3ce5c7cb9514195372e' -and $manifest.runtime_source_sha256 -ceq $review.source.sha256 -and $review.source.sha256 -ceq $prep.source.sha256 -and $prep.source.sha256 -ceq $control.source.sha256) 'Final source disagreement'
Assert ($control.status -ceq 'passed' -and $control.test_count -eq 5 -and @($review.independent_controls).Count -eq 5 -and @($review.blocking_issues).Count -eq 0) 'Bounded review failure'
Assert (@($review.independent_controls|Where-Object {-not $_.passed}).Count -eq 0) 'Independent control failure'
Assert (-not $manifest.public_measurement_entry_enabled -and -not $review.public_measurement_entry_enabled -and -not $review.scientific_execution -and -not $review.scientific_acceptance -and -not $review.full_t6_complete -and -not $review.manuscript_result -and -not $review.original_B1_executor_verified -and -not $review.fresh_gallery_verified -and @($review.scientific_imports).Count -eq 0) 'Source preparation overclaimed'
Assert (-not $prep.scientific_execution -and -not $prep.scientific_process_launches -and -not $prep.live_or_frozen_files_changed -and -not $prep.queue_registration_changed) 'Preparation exceeded scope'
$result=[ordered]@{
 schema='root-native-ranking-source-only-adoption.v1';time_utc=[DateTimeOffset]::UtcNow.ToString('o');status='adopted_source_preparation_only_public_entry_disabled'
 root_script=@{path=$PSCommandPath;sha256=(Get-FileHash -LiteralPath $PSCommandPath).Hash.ToLowerInvariant()}
 source_manifest=@{path=$manifestPath;sha256='6cd6aa011d4c996160adfdf81ad42c9c27692727c4b141bb9b64f6ff56740922'}
 independent_review=@{path=$reviewPath;sha256='5522e087cfeb44bc3d1cfaad90d4a3eb74d226520952084834d7c8803fe491fa'}
 source=$review.source;root_read_new_source_and_final_guards=$true;root_read_independent_script_and_findings=$true;verified_file_bindings=$checks.ToArray()
 controls_scope='Author initial candidate10 passed after fixture correction; final5 affected-interface checks and independent5 distinct controls. Not25 distinct tests; old suites not repeated.'
 prepared_interface='Unreleased internal complete-gallery stable ranking/raw-image-to-ranking primitive with completed same-seed descriptor and query-content bindings, original one-query all-positive ranking/AP validation and exclusive persistence.'
 public_entry_enabled=$false;source_preparation_only=$true;queue_registration_changed=$false;release_created=$false;scientific_runtime_executed=$false;scientific_results_accepted=0;full_T6_complete=$false;manuscript_result=$false
 pending=@('Independent original B1 executor and immutable evidence gate','Six fresh workers','Fresh full-gallery encoding/parity and full-dataset online accuracy','Predecessor/resource/release/shared lock admission','Real separate Windows launcher/worker exits and closed-stream parent aggregation','Actual scientific forward/GPU/parity/timing execution')
 limitations='No original independent B1 provenance, real NumPy/FP32/GPU parity, fresh gallery, scientific timing, or end-to-end experiment completion established. Public gate must not be bypassed via internal primitive. Final source-only adoption supersedes pending-review wording in the earlier sealed preparation report without changing it.'
}
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($result|ConvertTo-Json -Depth 14))
$stream=[IO.File]::Open($dest,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
[ordered]@{path=$dest;sha256=(Get-FileHash -LiteralPath $dest).Hash.ToLowerInvariant();checks=$checks.Count;source_only=$true}|ConvertTo-Json
