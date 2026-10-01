$ErrorActionPreference='Stop'
$ex='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$pkg='C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch'
$dest=Join-Path $ex 'query_t5_reliability_semantics_review_20260929_2054'
$post=Join-Path $ex 'pipeline_post_robustness_audit_20260929_1448'
$target=Join-Path $dest 'REVIEW.json'
if(Test-Path -LiteralPath $target){throw 'Immutable report already exists'}
function Bind-Small([string]$path){
 $item=Get-Item -LiteralPath $path
 if($item.PSIsContainer -or $item.Length -gt 2MB){throw "Expected small source or JSON: $path"}
 [ordered]@{path=$item.FullName;bytes=$item.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
}
$paths=@(
 "$pkg\lgm_game_pytorch\formal_retrieval.py",
 "$pkg\experiments\transactions_query_analysis.py",
 "$pkg\experiments\run_transactions_query_analysis.py",
 "$post\a1\query\transactions_query_analysis_config.json",
 "$post\a1\query\transactions_t5_selective_calibration.json",
 "$post\ROOT_POST_ROBUSTNESS_ADOPTION.json",
 "$post\README.md"
)
$bindings=@($paths|ForEach-Object {Bind-Small $_})
$json=Get-Content -Raw -LiteralPath "$post\a1\query\transactions_t5_selective_calibration.json"|ConvertFrom-Json
$config=Get-Content -Raw -LiteralPath "$post\a1\query\transactions_query_analysis_config.json"|ConvertFrom-Json
$row=$json.native_rows[0]
$review=[ordered]@{
 schema='t5-reliability-static-semantics-review.v1'
 reviewed_at=[DateTimeOffset]::Now.ToString('o')
 conclusion='No semantic blocker identified for the stated unconnected-marker/count-table design, conditional on retaining the documented limits. This is not artifact approval or new scientific acceptance.'
 static_semantics_only=$true
 scientific_numeric_recomputed_here=$false
 scientific_or_rendering_execution_here=$false
 rendered_artifacts_reviewed_here=$false
 source_and_small_file_bindings=$bindings
 inherited_root_adoption_sha256='f55b05559de3ca536170de4ea0be79988dd7c5cf0c822be5f3572eb31a57af0a'
 source_references=[ordered]@{
  normalized_model_descriptors='formal_retrieval.py:1045-1075'
  stable_gallery_ranking_top1_correctness_and_margin='formal_retrieval.py:1624-1669'
  retained_array_correctness_and_margin_validation='transactions_query_analysis.py:116-218'
  visual_full_alignment='transactions_query_analysis.py:221-234; run_transactions_query_analysis.py:286-316'
  fixed_bins='transactions_query_analysis.py:39'
  score_bin_and_ece_definition='transactions_query_analysis.py:501-557'
  full_population_per_variant_call='run_transactions_query_analysis.py:447-477,633-674'
 }
 score_contract=[ordered]@{
  margin='retained highest-minus-second-highest cosine gallery score; not positive-minus-negative or class probability'
  formula='clip(margin / 2.0, 0.0, 1.0)'
  input_precision='retained float32 margin converted by T5 to float64'
  rejection='nonfinite/empty/non-vector and margin < -2e-6'
  mathematical_margin_range=@(0,2)
  actual_clipping_occurrence_evaluated_here=$false
  clipping='Tolerated small negative margins map to0; values above2 map to1. Actual occurrence was not examined here.'
  calibrated_posterior=$false
  fitted_calibration_parameter=$false
 }
 bin_contract=[ordered]@{
  count=15
  implementation='minimum((score*15).astype(int64),14) for nonnegative float64 score'
  mathematical_intervals='[j/15,(j+1)/15) for j=0..13; [14/15,1] for final bin'
  internal_boundary='Higher bin for an exact internal boundary under the original float operation; score1 stays in final bin'
  no_rebinning_from_displayed_edges=$true
  population='Full official query set per task/seed/variant; the15 bins partition that row N'
  visual_full='Same path-aligned query set but independent variant score-bin memberships'
  empty=[ordered]@{count=0;accuracy=$null;mean_score=$null;weighted_gap=0;draw_reliability_marker=$false}
 }
 ece_contract=[ordered]@{
  occupied_x='stored mean_fixed_normalized_margin_confidence'
  occupied_y='stored accuracy = mean Boolean top1 correctness'
  weighted_gap='(bin_count / row_query_count) * abs(bin_accuracy - bin_mean_score)'
  ECE='Sum of all15 stored-definition contributions; not an unweighted mean of bins'
  unit='fraction'
  current_figure_policy='Copy saved ECE; display4 decimals only; do not re-sum or reconstruct from rounded markers'
 }
 geometry_contract=[ordered]@{
  markers='Unconnected at stored mean score and stored accuracy; bin midpoint is not an ECE-compatible scatter x coordinate'
  count_table='All15 original bins for both variants, including zero populations; null accuracy never becomes0'
  diagonal='Numerical equality reference between empirical accuracy and fixed normalized margin score, not proof of calibrated probabilities'
  scope='Separate task/direction/height/seed/variant, no pooling or CI/SD/p-value inference'
  producer_design_provenance='Producer collaboration message, not a hash-bound executed artifact inspected by this review'
 }
 copied_schema_sample=[ordered]@{
  schema=$json.schema_version;status=$json.status;unit=$json.unit
  native_row_key=[ordered]@{dataset=$row.dataset;task=$row.task;seed=$row.seed;variant=$row.variant}
  registered_calibration=$config.calibration
  occupied_bin=$row.calibration.reliability_bins[0]
  empty_bin=$row.calibration.reliability_bins[3]
  last_bin=$row.calibration.reliability_bins[14]
  row_query_count=$row.risk_coverage.queries
  stored_ECE=$row.calibration.ECE
  note='Copied necessary schema examples only; none of these values were independently recomputed in this review.'
 }
 caption_requirements=@('Fixed normalized cosine-margin score, not calibrated posterior or fitted probability','15 equal-width bins; final right endpoint included; empty reliability bins omitted as markers but population0 retained','Marker x is occupied-bin mean score, not bin center','Diagonal is numerical equality only','Saved ECE in fractions with declared display rounding','Visual/Full bin memberships differ; seeds and tasks remain separate','No resampling, uncertainty or significance claim','Existing upstream provenance limitations remain')
 limits=@('No scientific module imports or source execution','No NPZ, checkpoint, cache or image bytes read or hashed','No calibration/ECE/margin/bin recomputation or old test suite','No figure renderer, PowerPoint/Visio application or visual review','No native/GPU/process/resource/recovery/state/intent/release/lock operation','No HANDOFF or automation modification','Full retrieval rankings, model outputs and current checkpoint/cache/image byte verification remain outside this review')
 review_markdown=(Bind-Small "$dest\REVIEW.md")
 sealing_source=(Bind-Small $PSCommandPath)
}
[IO.File]::WriteAllText($target,($review|ConvertTo-Json -Depth 15),[Text.UTF8Encoding]::new($false))
Bind-Small $target | ConvertTo-Json
