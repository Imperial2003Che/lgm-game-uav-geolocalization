$ErrorActionPreference='Stop'
$ex='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$pkg='C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch'
$out=Split-Path -Parent $ex
$outputs=Split-Path -Parent $out
$dest=Join-Path $ex 'remaining_delivery_dependency_review_20260929_1952'
$reportPath=Join-Path $dest 'REVIEW.json'
if(Test-Path -LiteralPath $reportPath){throw 'Immutable review already exists'}
function Bind-Small([string]$path){
    $f=Get-Item -LiteralPath $path
    if($f.PSIsContainer -or $f.Length -gt 2MB){throw "Expected small input: $path"}
    [ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash.ToLowerInvariant();last_write_utc=$f.LastWriteTimeUtc.ToString('o')}
}
$post=Join-Path $ex 'pipeline_post_robustness_audit_20260929_1448'
$paths=@(
 "$ex\HANDOFF.md", "$ex\extension_plan.json", "$ex\extension_status.json", "$ex\supervise_extensions.py",
 "$ex\real_visualization_plan.json", "$ex\make_real_model_visualizations.py",
 "$pkg\experiments\transactions_t2_heldout_matrix.json", "$pkg\experiments\run_transactions_t2_heldout_matrix.py",
 "$ex\heldout_evaluation\run_heldout_evaluation.py",
 "$pkg\experiments\transactions_query_analysis.py",
 "$post\a1\query\transactions_t5_selective_calibration.json", "$post\a1\query\transactions_t4_strata.json",
 "$post\ROOT_POST_ROBUSTNESS_ADOPTION.json", "$post\README.md",
 "$outputs\paper_tgrs_revision_20260909\README_DELIVERY.md", "$outputs\paper_tgrs_revision_20260909\package_final.py",
 "$outputs\paper_label_revision_20260914\FINAL_REVIEW.json"
)
$bindings=@($paths | ForEach-Object { Bind-Small $_ })
$plan=Get-Content -Raw -LiteralPath "$ex\extension_plan.json" | ConvertFrom-Json
$state=Get-Content -Raw -LiteralPath "$ex\extension_status.json" | ConvertFrom-Json
$t5=Get-Content -Raw -LiteralPath "$post\a1\query\transactions_t5_selective_calibration.json" | ConvertFrom-Json
$t4=Get-Content -Raw -LiteralPath "$post\a1\query\transactions_t4_strata.json" | ConvertFrom-Json
$targetPaths=@(
 "$out\real_model_visualizations", "$out\real_model_visualizations\completion.json",
 "$pkg\runs\transactions_t2_heldout", "$pkg\runs\transactions_t2_heldout\transactions_t2_ledger.json",
 "$ex\heldout_evaluation\results", "$ex\heldout_evaluation\results\completion.json"
)
$pathObservations=@($targetPaths | ForEach-Object { [ordered]@{path=$_;exists=(Test-Path -LiteralPath $_)} })
$nativeVisio=@(& rg --files --hidden --no-ignore $outputs -g '*.vsdx' -g '*.vdx' -g '*.vsd')
$rgExit=$LASTEXITCODE
if($rgExit -ne 0 -and $rgExit -ne 1){throw 'Filename-only inventory failed'}
$review=[ordered]@{
 schema='remaining-delivery-dependency-static-review.v1'
 observed_at=[DateTimeOffset]::Now.ToString('o')
 scope='Existing small-file source contracts, accepted small query tables, exact configured path existence and bounded output filename inventory only; no experiments, tests or artifact re-audit.'
 scientific_execution=$false
 t6_status_basis='Latest HANDOFF/root observation, not a new GPU/process/resource measurement by this review.'
 extension=[ordered]@{
   status=$state.status; heartbeat_utc=([DateTimeOffset]$state.heartbeat_utc).ToUniversalTime().ToString('o')
   original_plan_sha256=$state.plan_sha256
   jobs=@($plan.jobs | ForEach-Object { $jobRow=$_; [ordered]@{id=$jobRow.id;command=$jobRow.command;status=(@($state.jobs|Where-Object { $_.id -eq $jobRow.id })[0].status)}})
   predecessor='All seven exact pipeline jobs completed with recorded parent exit0, ready_for_extension_preparation and preceding supervisor no longer alive.'
   source_reference="$ex\supervise_extensions.py:103-111"
 }
 loho=[ordered]@{
   additional_fits=24;epochs=80;heldout_altitudes_m=@(150,200,250,300);variants=@('visual','full');seeds=@(1,2,3)
   all_scope_tasks=192;heldout_tasks=48;seen_height_tasks=144;included_in_primary_42_fits=$false
   actual_completion_accepted_here=$false;absence_interpretation='Configured outputs absent plus pending jobs; not evidence of a failed attempted run.'
   references=@("$pkg\experiments\transactions_t2_heldout_matrix.json:4-24","$pkg\experiments\run_transactions_t2_heldout_matrix.py:573-582","$ex\heldout_evaluation\run_heldout_evaluation.py:369-391")
 }
 real_interpretability=[ordered]@{
   registered_device='cuda';batch_size=16;models=@('visual','visual_content','visual_style','full');seed=1;dataset='university1652'
   source_gate='All42 primary completion plus fresh checkpoint/cache/image bindings; inherited audit reports do not replace this gate.'
   outputs_require_actual_science=@('FP32 descriptors','3D t-SNE coordinates','visual-path target-conditioned Grad-CAM')
   registered_completion_status='computed_pending_visual_review'
   references=@("$ex\make_real_model_visualizations.py:13-24","$ex\make_real_model_visualizations.py:38-79","$ex\make_real_model_visualizations.py:138-171","$ex\make_real_model_visualizations.py:189-227","$ex\make_real_model_visualizations.py:265")
 }
 query_safe_cpu_work=[ordered]@{
   inherited_root_adoption_sha256='f55b05559de3ca536170de4ea0be79988dd7c5cf0c822be5f3572eb31a57af0a'
   native_t5_records=@($t5.native_rows).Count;fixed_bins_per_native_record=15;stored_bin_records=@($t5.native_rows.calibration.reliability_bins).Count
   paired_t5_records=@($t5.paired_comparisons).Count;t4_records=@($t4.rows).Count
   independently_recounted_t4_margin_records=132;t4_other_memberships_and_values_recomputed=$false;bootstrap_resampled=$false
   recommended_one_next_item='Native T5 margin-score reliability/ECE figures from already adopted small JSON records; no new inference, cache, NPZ or resampling.'
   confidence_definition='clip(cosine_top1_minus_top2_margin / 2, 0, 1)'
   caption_limits=@('Fixed score normalization, not fitted calibration or posterior probability','Retain all15 bins and empty-bin nulls; no zero imputation, pooling or refitting','Separate task/direction/height/variant/seed; no invented SD/CI/significance','Existing upstream inherited checkpoint/cache/image and historical metadata-chain limitations remain')
   source_reference="$pkg\experiments\transactions_query_analysis.py:501-557"
 }
 visio=[ordered]@{
   historical_statement_reference="$outputs\paper_tgrs_revision_20260909\README_DELIVERY.md:30"
   historical_statement='The September9 package explicitly says no VSDX was generated; PPT and SVG/PDF were delivered.'
   inventory_root=$outputs;method='rg --files --hidden --no-ignore with suffix globs *.vsdx,*.vdx,*.vsd; filenames only'
   rg_exit_code=$rgExit;matching_file_count=$nativeVisio.Count;matching_paths=$nativeVisio
   limit='No inference about files outside outputs, internal members of archived packages, application availability, or native Visio rendering.'
   completion_claim=$false
 }
 configured_path_observations=$pathObservations
 source_and_small_file_bindings=$bindings
 review_markdown=(Bind-Small "$dest\REVIEW.md")
 sealing_source=(Bind-Small $PSCommandPath)
 unchanged_scope=@('HANDOFF','automation','original science sources','plans','states','queue','intent','release','locks')
 not_performed=@('process/GPU/resource query','native or recovery entry','candidate or ValidateOnly','scientific import','PowerPoint/Visio application','experiment or test','checkpoint/cache/image/NPZ read or hash','old large artifact hash','result redraw or statistical recomputation')
 interpretation_limits=@('This auxiliary review is not root adoption or project delivery','Source readiness and file presence/absence do not establish scientific success','The latest recorded stopped state is not asserted as a fresh runtime observation','Original stage parent exit0 is not independent launcher/interpreter dual-handle evidence','Remaining later comparison and efficiency jobs were not independently re-audited here')
}
[IO.File]::WriteAllText($reportPath,($review|ConvertTo-Json -Depth 15),[Text.UTF8Encoding]::new($false))
Bind-Small $reportPath | ConvertTo-Json
