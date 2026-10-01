$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$d=$PSScriptRoot
$e=Split-Path -Parent $d
$o=Split-Path -Parent $e
$attempt=Join-Path $d 'attempt_20260929_055841_945130'
$checked=[Collections.Generic.Dictionary[string,object]]::new([StringComparer]::OrdinalIgnoreCase)
function Verify([string]$p,[string]$h,[long]$bytes=-1){
 if([IO.Path]::GetExtension($p) -in @('.pt','.pth','.ckpt')){throw 'Checkpoint read prohibited'}
 $full=[IO.Path]::GetFullPath($p)
 if($checked.ContainsKey($full)){$a=$checked[$full]}else{
  $i=Get-Item -LiteralPath $full
  $a=[ordered]@{path=$full;bytes=$i.Length;sha256=(Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToLower()}
  $checked.Add($full,$a)
 }
 if($a.sha256 -cne $h -or ($bytes -ge 0 -and $a.bytes -ne $bytes)){throw "Binding mismatch: $full"}
 $a
}
function B($b){$n=-1;if($b.PSObject.Properties.Name -contains 'bytes'){$n=[long]$b.bytes};Verify $b.path $b.sha256 $n}
function J([string]$p){Get-Content -LiteralPath $p -Raw|ConvertFrom-Json -DateKind String}
$reviewBinding=Verify (Join-Path $attempt 'TRANSFER_REVIEW.json') 'b0627920c9e8ab1da0dbc6d2d48795b3abe68cf3b79f7d7dba7afa9bba3847c7'
$metaBinding=Verify (Join-Path $attempt 'METADATA.json') '5f268f24d14c272ed96c7b259fffe5fbef0082b9c708313f58ecf5ce4846f815'
$sourceBinding=Verify (Join-Path $d 'review_transfer_v3.py') '0c98c9b4fab3a1d36c0a980699f1af0dd3d254f3c973a4b90ed0e507c421b6a7'
$diffBinding=Verify (Join-Path $d 'V1_TO_V3_FULL.patch') '14c36c5b33d2dcb865f7f4466d0308a6f315c4977323509608a886e4d6120792'
$r=J $reviewBinding.path
$m=J $metaBinding.path
if(-not $r.passed_with_stated_limits -or $r.accepted_transfer_runs -ne 12 -or $r.accepted_transfer_tasks -ne 66 -or $r.new_evaluation_artifact_count -ne 138 -or $r.checkpoint_hash_queries -ne 0 -or @($r.scientific_modules).Count -ne 0){throw 'Unexpected review scope'}
$null=B $r.source
$null=B $m.report
foreach($b in $m.files){
 if(-not ([IO.Path]::GetFullPath($b.path)).StartsWith($attempt+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Metadata member outside audit attempt'}
 $null=B $b
}
foreach($b in $r.raw_evidence_bindings){
 $null=Verify $b.snapshot $b.sha256 $b.bytes
 # The original pipeline status continues receiving heartbeats. Only its sealed snapshot is bound here.
 if([IO.Path]::GetFullPath($b.path) -ine (Join-Path $e 'pipeline_status.json')){$null=B $b}
}
$expected=@()
foreach($direction in @('university1652_to_sues200','sues200_to_university1652')){foreach($variant in @('visual','full')){foreach($seed in 1..3){$expected+="$direction/$variant/seed_$seed"}}}
$ids=@($r.runs.evaluation_id)
if(@($ids|Select-Object -Unique).Count -ne 12 -or @(Compare-Object ($expected|Sort-Object) ($ids|Sort-Object)).Count -ne 0){throw 'Fixed transfer identifier set mismatch'}
foreach($run in $r.runs){
 $count=if($run.evaluation_id.StartsWith('university1652_to_sues200/')){8}else{3}
 if(@($run.tasks).Count -ne $count -or $run.subprocess_run_return_code -ne 0 -or -not $run.original_completed_gate_passed_with_stdlib_compatibility){throw 'Run completion scope mismatch'}
 foreach($b in $run.artifacts){$null=B $b}
 $config=J (@($run.artifacts|Where-Object {$_.path.EndsWith('transfer_evaluation_config.json')})[0].path)
 $manifest=J $run.manifest_binding.path
 if($config.checkpoint.sha256 -cne $run.inherited_checkpoint_SHA -or $manifest.checkpoint_sha256 -cne $run.inherited_checkpoint_SHA -or $manifest.selected_training_epoch -ne 79 -or $manifest.status -ne 'completed'){throw 'Inherited checkpoint/manifest binding mismatch'}
}
if(@($r.original_hash_queries).Count -ne 102 -or @($r.source_definitions_extracted_unchanged|Where-Object body_changed).Count -ne 0){throw 'Compatibility evidence mismatch'}
$observerDir=Join-Path $e 'robustness_observation_20260929_0647'
$obsBinding=Verify (Join-Path $observerDir 'snapshot_20260929_070430172\OBSERVATION.json') '201a4a131ffbaabb0d947d1c6000b9381dfdb8747dfdfc1cc5805ad89c601344'
$observerAdoption=Verify (Join-Path $observerDir 'ROOT_OBSERVER_ADOPTION.json') '2567f5c0f56838ad0563e08f427a8144a1f308f58c26a29e312bab07bf0dd766'
$obs=J $obsBinding.path
foreach($b in $obs.raw_snapshots){$null=B $b.snapshot}
foreach($b in $obs.pins){$null=B $b}
$null=B $obs.first_identity
$null=B $obs.stage_entrypoint
$live=@($obs.live_roles|ForEach-Object {$_.owner;$_.launcher})+@($obs.stage_pair)+@($obs.robustness.worker_pair)
$procs=@(Get-CimInstance Win32_Process)
foreach($p in $live){$n=@($procs|Where-Object ProcessId -eq $p.pid);if($n.Count -ne 1 -or $n[0].CreationDate.ToUniversalTime().Ticks -ne [long]$p.creation_utc_ticks -or $n[0].CommandLine -cne $p.command -or $n[0].ParentProcessId -ne $p.parent){throw 'Phase changed; observe fresh without recovery'}}
if($live.Count -ne 12 -or $null -ne $obs.primary.exit_code){throw 'Live/primary evidence scope'}
$oldStage=@($procs|Where-Object {$_.ProcessId -in @(20604,39488)}|ForEach-Object {[ordered]@{pid=$_.ProcessId;parent=$_.ParentProcessId;creation_utc=$_.CreationDate.ToUniversalTime().ToString('o');command=$_.CommandLine}})
$figdir=Join-Path $o 'formal_results_native_20260929'
$figReviewBinding=Verify (Join-Path $figdir 'INDEPENDENT_NATIVE_SVG_REVIEW.json') '9dbcc7f38df2057e900f8a13571b00eadb867d2e890e8948f3eea6e1f6501977'
$fr=J $figReviewBinding.path
foreach($key in @('review_source','build_source','build_report','render_report')){$null=B $fr.$key}
foreach($b in $fr.authority){$null=B $b}
foreach($f in $fr.figures){foreach($key in @('csv_original','csv_copy','svg','preview')){$null=B $f.$key};if($f.raster_count -ne 0 -or -not $f.all_text_editable){throw 'Figure editable scope'}}
if($fr.total_cells -ne 66 -or $fr.total_intervals -ne 66 -or $fr.visual_review.label_overlap_detected -or $fr.visual_review.clipping_detected){throw 'Figure content/visual scope'}
$rootFigureReview=Verify (Join-Path $figdir 'v2\ROOT_NATIVE_SVG_REVIEW.json') 'ac010cc27c27fa94a9fdd3e860af84c330a8e4cc6efa3c66b2e6a8000d6253ca'
$captions=Verify (Join-Path $figdir 'v2\CAPTIONS.md') '2dd6fef4c13f2348256b68ede5e099e51ae307b65b93b0ead3afcc88cd3697a9'
$claimNote=Verify (Join-Path $figdir 'PRIMARY_CLAIM_REVIEW.json') '0e29cdb0412b148100788b02276e9a9ef4a7aed4a1f5d892fb088a0ff184cdb6'
$out=Join-Path $d 'ROOT_TRANSFER12_AND_NATIVE2_ADOPTION.json'
$result=[ordered]@{
 schema='lgm.root.transfer12-native2-adoption.v1';time=(Get-Date).ToString('o');accepted=$true
 source=[ordered]@{path=$PSCommandPath;sha256=(Get-FileHash -LiteralPath $PSCommandPath).Hash.ToLower()}
 independent_transfer_review=$reviewBinding;metadata=$metaBinding;review_source=$sourceBinding;full_candidate_diff=$diffBinding
 accepted_transfer_runs=12;accepted_transfer_tasks=66;new_evaluation_artifact_count=138;raw_snapshot_count=@($r.raw_evidence_bindings).Count
 retained_official_runs=42;retained_official_tasks=231;retained_training_fits=42;pipeline_jobs_adopted=3
 transfer_identifiers=$ids;transfer_limits=$r.limits;validator_compatibility_limit=$r.validator_compatibility_limit
 review_method='Root read full v3 source, candidate diff, frozen original completion helpers and independent contract review; verified sealed metadata, raw snapshots, new source/metric/NPZ/log originals and exact registered scope. No rerun of scientific model, original NumPy runtime, full ranking or checkpoint bytes.'
 current_observation=$obsBinding;observer_root_adoption=$observerAdoption;current_identity_count=$live.Count;current_identities=$live;current_old_t3_pid_number_matches=$oldStage
 exit_limit='T3 original pipeline Popen exit0 and 12 subprocess.run return0. No independent dual process handles. Primary own original exit code remains unknown; completed plus absence only.'
 native_figures=[ordered]@{accepted_count=2;independent=$figReviewBinding;root_review=$rootFigureReview;captions=$captions;scope='v2 native SVG only, 66 cells and 66 intervals, 216 editable texts, no raster. Source CSV and inherited upstream limits retained. No final PPT/Visio or manuscript delivery.'}
 primary_claim_note=$claimNote
 actual_unique_file_checks=$checked.Count;bindings=@($checked.Values);checkpoint_bytes_rehashed=0;scientific_execution=$false;live_state_modified=$false
}
$data=[Text.UTF8Encoding]::new($false).GetBytes(($result|ConvertTo-Json -Depth 32))
$f=[IO.File]::Open($out,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
try{$f.Write($data,0,$data.Length)}finally{$f.Dispose()}
[pscustomobject]@{path=$out;sha256=(Get-FileHash -LiteralPath $out).Hash.ToLower();checks=$checked.Count;identities=$live.Count;transfer_runs=12;transfer_tasks=66;native_figures=2}|ConvertTo-Json

