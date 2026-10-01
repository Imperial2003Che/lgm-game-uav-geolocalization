$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$e=Split-Path -Parent $PSScriptRoot
$bs=[Collections.Generic.Dictionary[string,object]]::new([StringComparer]::OrdinalIgnoreCase)
function B($d){$p=[IO.Path]::GetFullPath($d.path);$h=(Get-FileHash -LiteralPath $p).Hash.ToLower();$n=(Get-Item -LiteralPath $p).Length;if($h -cne $d.sha256){throw 'SHA mismatch'};if(($d.PSObject.Properties.Name -contains 'bytes') -and $n -ne $d.bytes){throw 'size mismatch'};$bs[$p]=[ordered]@{path=$p;sha256=$h;bytes=$n}}
function J($p){Get-Content -LiteralPath $p -Raw|ConvertFrom-Json -DateKind String}
$fullStatic=[pscustomobject]@{path=(Join-Path $e 'robustness_full_audit_20260929_1247\contract_review\FULL_AUDIT_SOURCE_STATIC_REVIEW.json');sha256='dc419dc464a4cd76569d97fb7fc2ce8a99cb8c12da8621ee333abc18bdc5839d'}
$pairStatic=[pscustomobject]@{path=(Join-Path $PSScriptRoot 'INDEPENDENT_SOURCE_STATIC_REVIEW.json');sha256='a5f96110d3a018ad678e2d4b628b81e98ca7b627d7db0c6a1bf6b0607a6eebe9'}
B $fullStatic;B $pairStatic;$f=J $fullStatic.path;$p=J $pairStatic.path
if(@($f.blocking_findings).Count -ne 0 -or @($p.blocking_findings).Count -ne 0 -or $f.candidate_executed_here -or $p.candidate_executed_here -or $f.tests_run_here -or $p.tests_run_here){throw 'Static review scope mismatch'}
foreach($b in $f.bindings){B $b};B $p.source
$fullRoot=[pscustomobject]@{path=(Join-Path $e 'robustness_full_audit_20260929_1247\ROOT_FULL1_ADOPTION.json');sha256='ea8c3065092db79c67005b6b6aa1b54a5433ba39ae4b143504f09618f98fd1f5'}
$pairRoot=[pscustomobject]@{path=(Join-Path $PSScriptRoot 'ROOT_PAIR_STATISTICS_ADOPTION.json');sha256='2eaed53c937a4a260be321c18ff100522c601622374153a511388e5c797b1cee'}
B $fullRoot;B $pairRoot
$exec=[pscustomobject]@{path=(Join-Path $PSScriptRoot 'EXECUTION.json');sha256='1a85f9689ec1d2ff51fdb6790531ac98ea25d45af20f221c8f6a89960b98ffcd'}
B $exec;$run=J $exec.path;if($run.first_execution_exit_code -ne 0 -or $run.first_execution_failed -or -not $run.source_unchanged){throw 'First comparison execution mismatch'}
foreach($b in $run.bindings){B $b}
$deliveryPath=Join-Path $PSScriptRoot 'result_20260929_115922_396070\DELIVERY.json';$delivery=J $deliveryPath;B $delivery.report;B $delivery.source;foreach($b in $delivery.artifacts){B $b}
$r=[ordered]@{schema='lgm.root.later-static-review-adoption.v1';time=(Get-Date).ToString('o');source=[ordered]@{path=$PSCommandPath;sha256=(Get-FileHash -LiteralPath $PSCommandPath).Hash.ToLower()};accepted_as_later_static_addendum=$true;full_static=$fullStatic;pair_static=$pairStatic;prior_full_root=$fullRoot;prior_pair_statistics_root=$pairRoot;comparison_execution_record=$exec;bindings=@($bs.Values);unique_file_checks=$bs.Count;review_method='Root read both complete independent static reports and checked bound source/diff/report and separately recorded comparison execution/delivery artifacts. Earlier Full and statistics adoptions remain byte-for-byte unchanged.';no_new_scientific_run=$true;no_prior_suite_repeated=$true;limits='Static review supplies no second artifact execution. Original bounded inherited-SHA, no model/full-ranking/AP reconstruction, Full evidence-path difference and seed1 limits remain.'}
$out=Join-Path $PSScriptRoot 'ROOT_STATIC_ADDENDUM.json';$raw=[Text.UTF8Encoding]::new($false).GetBytes(($r|ConvertTo-Json -Depth 18));$s=[IO.File]::Open($out,[IO.FileMode]::CreateNew);try{$s.Write($raw,0,$raw.Length)}finally{$s.Dispose()};[ordered]@{path=$out;sha256=(Get-FileHash -LiteralPath $out).Hash.ToLower();checks=$bs.Count}|ConvertTo-Json
