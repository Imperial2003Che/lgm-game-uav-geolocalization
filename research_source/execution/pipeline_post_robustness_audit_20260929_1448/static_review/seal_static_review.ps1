$ErrorActionPreference='Stop'
$Audit='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\pipeline_post_robustness_audit_20260929_1448'
$Package='C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch'
$Out=Split-Path -Parent $PSCommandPath
$bindings=[Collections.Generic.List[object]]::new()
function Bind([string]$Label,[string]$Path,[string]$Expected){
  $item=Get-Item -LiteralPath $Path
  if($item.Length -gt 1000000){throw 'Static scope: unexpectedly large file'}
  if($item.Extension -notin @('.py','.json','.md','.ps1')){throw 'Static scope: unexpected file type'}
  $hash=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
  if($Expected -and $hash -cne $Expected){throw ('Binding changed: '+$Label)}
  $b=[ordered]@{label=$Label;path=$item.FullName;bytes=$item.Length;sha256=$hash}
  $bindings.Add($b)
  return $b
}
$candidate=Bind 'audit_source' (Join-Path $Audit 'review_post.py') 'bb510281e547182ddc675d8ab34d7905625bb3ed4d7f540416b0cad5a7c36521'
$null=Bind 'original_primitive' (Join-Path $Package 'experiments\transactions_query_analysis.py') '4cf500c09aef5f81c192e0975b024aea1da7c90bfba2c3a70b99632574608221'
$null=Bind 'captured_primitive' (Join-Path $Audit 'a1\source\transactions_query_analysis.py') '4cf500c09aef5f81c192e0975b024aea1da7c90bfba2c3a70b99632574608221'
$null=Bind 'original_runner' (Join-Path $Package 'experiments\run_transactions_query_analysis.py') '0592c3c1859d38b3cea542d6a5afd8e27bc2b5836dcc83103f4f239db363f561'
$null=Bind 'captured_runner' (Join-Path $Audit 'a1\source\run_transactions_query_analysis.py') '0592c3c1859d38b3cea542d6a5afd8e27bc2b5836dcc83103f4f239db363f561'
$null=Bind 'protocol' (Join-Path $Audit 'a1\source\TRANSACTIONS_EXTENSION_PROTOCOL.md') '76b0b29ce7a09710dd8e4495f1fbed36eef2fddce148ad463d83fb115e8a2f4b'
$priorReport=Bind 'independent_execution_report' (Join-Path $Audit 'REVIEW.json') 'e350ca764a7b6a053afbab3062eee6412306685ffeb2c5b9185578896ff451bc'
$prior=Get-Content -LiteralPath $priorReport.path -Raw|ConvertFrom-Json
if($prior.query.source_authority.exact_input_path_sha_size_bindings -ne 66 -or @($prior.query.source_authority.not_directly_found).Count -ne 0 -or $prior.query.source_authority.all_12_run_identifiers_adopted -ne $true){throw 'Current report does not meet explicit authority acceptance condition'}
$text=@'
# Post-robustness source review

No blocking mismatch was found between the fixed bounded auditor and the original T4/T5 numerical contracts. The entire audit source and original primitive module were read; the original runner's evidence construction, pair alignment, strata, native rows, registered settings and Holm-family construction were checked. This is a static review; the candidate, prior suites and NPZ calculations were not executed again.

- Both variants are aligned to the Visual query order before the runner produces native and paired T5 rows. Stable descending margin sorting therefore preserves the same tie order in Python's stable sort and the producer's NumPy stable argsort. Coverage uses ceil(c*N), clamped to [1,N]. AURC is the mean risk over every nonempty prefix, not an integral interpolated through only the ten displayed points.
- ECE uses the prescribed unfitted confidence clip(margin/2,0,1). Fifteen equal-width bins use floor(confidence*15), capped at bin14; confidence1 stays in the last bin. Empty bins are retained, and each contribution is count/N times the absolute accuracy-confidence gap. This remains a fixed-margin diagnostic, not calibrated posterior probability.
- The paired test compares selected-AND-correct binary utility over the common complete query set. It does not treat two different selected subsets as paired conditional accuracies. Conditional selective R@1, selected overlap and full-query success rates remain separate quantities.
- The integer binomial-tail calculation equals the original two-sided exact McNemar definition (twice the lower tail, capped at1; no discordance gives p1). The auditor compares logarithms to the producer's lgamma/logsumexp result with an explicit tolerance and retains underflow-safe serialized probabilities. Holm sorts raw log probabilities, applies the remaining-family multiplier, clips at1 and takes a cumulative maximum. It uses the same strict p<0.05 decision as the frozen producer. The T4 eligible family and 132-comparison T5 family remain separate.
- T4 margin cuts use linear quantiles at (N-1)*p and bisect_left, consistent with searchsorted(side=left): values equal to a cut go into the lower interval. Tied cuts may create empty or uneven groups, so these are quantile strata, not guaranteed equal-size bins. Membership is anchored to Visual's margin and shared by Full. Small strata retain descriptive values while withholding inference below100 queries.
- The 132 Visual-margin rows have stored-query membership and values independently recomputed by the separate artifact audit. The remaining330 entropy/semantic rows have only declared-summary/CSV/threshold and saved-discordance arithmetic checked. Their cache-derived membership and means are not independently reproduced. None of the bootstrap confidence intervals are resampled or independently accepted by this bounded review.

The current report declares all66 exact input path/SHA/size bindings, no missing items and all12 relevant official run identifiers adopted; this static supplement explicitly checks those report fields. The candidate's official_authority function returns diagnostics rather than rejecting missing edges, so a generic passed_with_stated_limits flag alone must never be treated as complete source acceptance on another dataset snapshot. Root adoption must continue requiring those exact fields.

Aggregate CSV/JSON/table agreement is initially internal consistency only. The separate mandatory annex must reconcile all four adopted robustness inputs, including the newly completed SUES Full run. This static supplement does not assert that annex has completed. The22 original aggregate SVG groups contain editable text but their recorded6/7pt sizes and unchecked final geometry mean they are not final minimum8pt publication figures.

All inherited checkpoint/cache/image byte limits remain. Stored query values are not a model/full-ranking/AP rerun. Query-level paired inference is not a test over three independent training seeds or a universal superiority claim. Stage parent exit0 is not independent dual-handle exit proof. No T6 completion or final paper/Overleaf delivery follows from these two post-robustness jobs.
'@
$md=Join-Path $Out 'POST_SOURCE_STATIC_REVIEW.md'
if(Test-Path -LiteralPath $md){throw 'Do not overwrite static report'}
[IO.File]::WriteAllText($md,$text+"`n",[Text.UTF8Encoding]::new($false))
$markdown=Bind 'review_markdown' $md ''
$sealer=Bind 'sealing_source' $PSCommandPath ''
$report=[ordered]@{
 schema='lgm-game.independent-post-robustness-source-static.v1'
 created_utc=[DateTime]::UtcNow.ToString('o')
 reviewer='/root/sep29_recovery_review'
 verdict='No blocking numerical-contract mismatch found within the explicitly bounded source-audit scope.'
 candidate=$candidate
 source_and_small_file_bindings=@($bindings.ToArray())
 review_markdown=$markdown
 sealing_source=$sealer
 read_scope=@('Complete review_post.py','Complete transactions_query_analysis.py primitives','Runner evidence/alignment/strata/native/config/Holm blocks','Protocol T4/T5/statistics clauses')
 blocking_findings=@()
 actual_report_authority_fields=[ordered]@{exact_input_path_sha_size_bindings=66;not_directly_found=@();all_12_run_identifiers_adopted=$true}
 acceptance_conditions=@('Root must require66 exact input bindings, no missing inputs, and all12 official identifiers adopted; candidate helper reports but does not enforce these fields.','Aggregate four-run source reconciliation annex is mandatory and not asserted complete here.')
 interpretation_limits=@('Static/small-file review only: no candidate execution, NPZ reading, source scientific imports, bootstrap resampling, previous suite repetition or live-state mutation.','T4 non-margin330 rows are aggregate-level only;132 margin rows andT5 stored-query arithmetic belong to the separate artifact execution report.','All bootstrap intervals remain retained producer outputs with only structural checks.','Historical authority and checkpoint/cache/image byte limitations remain inherited; no model/full rankings/all-positive-rank AP reconstruction.','Fixed-margin ECE is descriptive, not calibrated posterior; inference is query-paired, not cross-seed training uncertainty.','Source consistency and original parent exit0 do not establish full pipeline/T6 completion or final publication figures.')
 scientific_or_test_execution=$false
 scientific_acceptance=$false
 live_state_modified=$false
 root_adoption=$false
}
$target=Join-Path $Out 'POST_SOURCE_STATIC_REVIEW.json'
if(Test-Path -LiteralPath $target){throw 'Do not overwrite static report'}
[IO.File]::WriteAllText($target,($report|ConvertTo-Json -Depth 30)+"`n",[Text.UTF8Encoding]::new($false))
Get-FileHash -LiteralPath $target -Algorithm SHA256
