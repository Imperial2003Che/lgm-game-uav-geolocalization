$ErrorActionPreference='Stop'
$dir='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\query_t5_reliability_semantics_review_20260929_2054'
$target=Join-Path $dir 'INTERPRETATION_ADDENDUM.json'
if(Test-Path -LiteralPath $target){throw 'Addendum already exists'}
function Bind-Small([string]$path){$f=Get-Item -LiteralPath $path;if($f.Length -gt 2MB){throw 'Not a small file'};[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
$a=[ordered]@{
 schema='t5-reliability-static-semantics-addendum.v1'
 created_at=[DateTimeOffset]::Now.ToString('o')
 base_review=(Bind-Small "$dir\REVIEW.json")
 base_review_expected_sha256='89578f22d25b28934f11fcf9e80f2f02bfa1b452699a4fd94f18733cfe732c38'
 original_scientific_primitive=(Bind-Small 'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\experiments\transactions_query_analysis.py')
 source_lines='512-556: ECE is the population-weighted absolute gap between within-bin accuracy and the fixed normalized margin score.'
 required_interpretation='Lower fixed margin-score ECE implies neither higher retrieval accuracy nor independently established improved probability calibration. Accuracy and score both change; interpret alongside corresponding task-specific retrieval results and retain unfavorable Full results.'
 new_numeric_calculation_or_comparison=$false
 claim_particular_task_direction_verified_here=$false
 scientific_execution=$false
 original_review_files_modified=$false
 markdown=(Bind-Small "$dir\INTERPRETATION_ADDENDUM.md")
 sealing_source=(Bind-Small $PSCommandPath)
}
[IO.File]::WriteAllText($target,($a|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
Bind-Small $target|ConvertTo-Json
