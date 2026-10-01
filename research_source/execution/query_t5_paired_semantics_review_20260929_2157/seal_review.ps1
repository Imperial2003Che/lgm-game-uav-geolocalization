$ErrorActionPreference='Stop'
$ex='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$pkg='C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch'
$dest=Join-Path $ex 'query_t5_paired_semantics_review_20260929_2157'
$post=Join-Path $ex 'pipeline_post_robustness_audit_20260929_1448'
$target=Join-Path $dest 'REVIEW.json'
if(Test-Path -LiteralPath $target){throw 'Immutable report already exists'}
function Bind-Small([string]$path){$f=Get-Item -LiteralPath $path;if($f.PSIsContainer -or $f.Length -gt 2MB){throw 'Expected small input'};[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
$paths=@(
 "$pkg\experiments\transactions_query_analysis.py",
 "$pkg\experiments\run_transactions_query_analysis.py",
 "$post\a1\query\transactions_query_analysis_config.json",
 "$post\a1\query\transactions_t5_selective_calibration.json",
 "$post\a1\query\transactions_t5_selective_comparisons.csv",
 "$post\ROOT_POST_ROBUSTNESS_ADOPTION.json",
 "$post\README.md"
)
$bindings=@($paths|ForEach-Object {Bind-Small $_})
$saved=Get-Content -Raw -LiteralPath "$post\a1\query\transactions_t5_selective_calibration.json"|ConvertFrom-Json
$sample=$saved.paired_comparisons[0]
$review=[ordered]@{
 schema='t5-paired-coverage-static-semantics-review.v1'
 reviewed_at=[DateTimeOffset]::Now.ToString('o')
 conclusion='No semantic blocker identified for plotting saved realized coverage against saved selected-and-correct/full-N rates, conditional on the stated denominator, sparse-coverage and interpretation requirements.'
 static_only=$true; numeric_reexecution=$false; rendered_artifact_acceptance=$false; root_adoption=$false
 source_and_small_file_bindings=$bindings
 inherited_root_sha256='f55b05559de3ca536170de4ea0be79988dd7c5cf0c822be5f3572eb31a57af0a'
 read_scope='Relevant alignment, original count, raw-margin selection, utility/rate, McNemar, Holm, caller and serialization blocks; whole source-file bytes bound, not a claim of new full-module audit.'
 source_references=[ordered]@{
  registered_coverage='transactions_query_analysis.py:41'
  query_alignment='transactions_query_analysis.py:221-234; run_transactions_query_analysis.py:286-316'
  selected_count='transactions_query_analysis.py:560-563'
  selection_success_overlap='transactions_query_analysis.py:612-655'
  original_mcnemar='transactions_query_analysis.py:395-424'
  original_holm='transactions_query_analysis.py:659-684'
  registered_caller_and_output_count='run_transactions_query_analysis.py:633-697'
  complete_T5_Holm_family='run_transactions_query_analysis.py:732-757'
 }
 contract=[ordered]@{
  requested_coverages=@(0.50,0.75,0.90,1.00)
  full_N='Path-aligned full official query count for a single dataset/task/seed; both variants use same N'
  display_N_source='Matching native_rows[].risk_coverage.queries with dataset/task/seed/variant and query_membership_sha256 binding; N is not a separate paired-row field'
  k='min(N,max(1,ceil(requested_coverage*N)))'
  selection='Each variant independently selects top k by stable descending raw cosine Top1-minus-Top2 margin; ties preserve common aligned query order'
  plotted_x='100 * saved realized_coverage'
  plotted_y_visual='100 * saved coverage_constrained_success.visual_rate'
  plotted_y_full='100 * saved coverage_constrained_success.full_rate'
  success_denominator='N: complete shared query population'
  selective_R1_denominator='k: queries selected by that particular variant'
  conceptual_identity='success=(k/N)*selective_R1; not recomputed for the new display'
  unselected='Utility false/no success; does not assert the underlying retrieval prediction is wrong'
  overlap='Integer count of shared selected query paths; not common correctness, union/Jaccard or gallery overlap'
  coverage1='k=N and overlap=N; saved success definition becomes ordinary full-task R1'
  shape_meaning='Each model selected prefixes are nested; success cannot decrease as more queries are selected. A rising curve is not improved ranking quality with coverage.'
  presentation='Retain task/direction/height/seed/variant identities and unfavorable Full results; label y selected and correct (% of all queries)'
 }
 sparse_geometry=[ordered]@{
  paired_observations_per_seed=4
  native_ten_point_curve_distinct=$true
  paired_75_percent='Use original saved paired observation, not native70/80 interpolation'
  no_origin_or_unsaved_coverage=$true
  line_segments='Visual guides only if used; no fitted smoothing or interpolated scientific observations'
  no_area_or_AUC_from_four_points=$true
  native_all_prefix_AURC_is_different_metric=$true
  no_CI_SD_pvalue_or_significance_graphics=$true
 }
 existing_inference_limits=[ordered]@{
  original_test='Exact two-sided binomial McNemar on discordance of selected AND correct utility over shared full query population'
  not_test_of='Two selected-subset accuracies with potentially different query memberships'
  no_discordance_p='1 by original source definition'
  original_Holm_family_size=132
  original_Holm_scope='All11 tasks,3seeds,4paired coverages; distinct from T4 family, not a per-figure selected subset'
  original_paired_bootstrap_CI_generated=$false
  previous_audit_bootstrap_resampled=$false
  new_rates_overlap_p_or_CI_recomputed_here=$false
  seed_uncertainty_or_general_superiority_claim=$false
 }
 copied_schema_examples=[ordered]@{
  schema=$saved.schema_version;unit=$saved.unit
  first_paired_record=$sample
  full_coverage_record=$saved.paired_comparisons[3]
  corresponding_native_rows=@($saved.native_rows[0..1] | ForEach-Object {[ordered]@{dataset=$_.dataset;task=$_.task;seed=$_.seed;variant=$_.variant;query_membership_sha256=$_.query_membership_sha256;queries=$_.risk_coverage.queries}})
  note='Copied source-schema examples only, not an independent numeric or membership recheck. Saved p-values included only as schema evidence and not for plotting.'
 }
 limits=@('No science or numeric suite executed','No NPZ/checkpoint/cache/image read or hash','No model, full ranking, all-positive AP, query or membership recomputation','Existing checkpoint/cache/image inheritance and historical metadata-chain gaps remain','No p-value, CI, SD, bootstrap or new inference for this figure','No native/GPU/process/resource/recovery/intent/release/lock/live-state operation','No rendering or presentation application','No HANDOFF or automation mutation')
 review_markdown=(Bind-Small "$dest\REVIEW.md")
 sealing_source=(Bind-Small $PSCommandPath)
}
[IO.File]::WriteAllText($target,($review|ConvertTo-Json -Depth 16),[Text.UTF8Encoding]::new($false))
Bind-Small $target|ConvertTo-Json
