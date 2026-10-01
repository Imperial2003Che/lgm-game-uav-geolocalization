$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$d=$PSScriptRoot
$ex=Split-Path -Parent $d
$result=Join-Path $d 'result_20260929_061052_519928'
$cr=Join-Path $ex 'transfer_audit_20260929_0647\contract_review'
$bindings=[Collections.Generic.Dictionary[string,object]]::new([StringComparer]::OrdinalIgnoreCase)
function Verify([string]$path,[string]$hash,[long]$bytes=-1){
 if([IO.Path]::GetExtension($path) -in @('.pt','.pth','.ckpt')){throw 'Weight access prohibited'}
 $p=[IO.Path]::GetFullPath($path)
 if(-not $bindings.ContainsKey($p)){$i=Get-Item -LiteralPath $p;$bindings.Add($p,[ordered]@{path=$p;sha256=(Get-FileHash -LiteralPath $p).Hash.ToLower();bytes=$i.Length})}
 $b=$bindings[$p]
 if($b.sha256 -cne $hash -or ($bytes -ge 0 -and $b.bytes -ne $bytes)){throw "File binding mismatch: $p"}
 $b
}
function B($b){$size=-1;if($b.PSObject.Properties.Name -contains 'bytes'){$size=[long]$b.bytes};Verify $b.path $b.sha256 $size}
function J([string]$p){Get-Content -LiteralPath $p -Raw|ConvertFrom-Json -DateKind String}
$reportBinding=Verify (Join-Path $result 'REPORT.json') '22d8578b17fa7d71bd2078a630b62b8e8e45c3082a7b86f608580bd0a4478c7c'
$deliveryBinding=Verify (Join-Path $result 'DELIVERY.json') 'd8fd7ab801ffb61f448f4bc12cc68f03d95e7f53a141d6ea0096bc96f4541c22'
$producerBinding=Verify (Join-Path $d 'aggregate_transfer.py') 'd981b45c7ab7f1e4d7e018635771b63d84d307a14cdc2bcc5b4e5ec1f2e99bd3'
$indBinding=Verify (Join-Path $cr 'INDEPENDENT_TRANSFER_AGGREGATION_DECIMAL_REVIEW_V2_20260929.json') '305d5f87dbe5fd7347c4c0e9944b1b020486d43e747a52f02ebbc24ac7bd380b'
$indSource=Verify (Join-Path $cr 'independent_transfer_aggregation_decimal_review_v2.py') '569361a0e98faec3588eae0d7a5d187dc4b8364bb97f54681c7e6d7023f90024'
$r=J $reportBinding.path;$i=J $indBinding.path;$delivery=J $deliveryBinding.path
if(-not $r.passed -or -not $i.passed -or $r.seed_task_rows -ne 66 -or $r.three_seed_groups -ne 22 -or $r.within_task_contrasts -ne 11 -or $r.sample_sd_ddof -ne 1 -or $i.checks.decimal_numeric_comparisons -ne 330 -or $i.numeric_method.sample_sd_denominator -ne 2){throw 'Unexpected aggregation scope'}
foreach($b in $r.input_bindings){$null=B $b}
foreach($b in $r.outputs){$null=B $b}
foreach($b in $i.inputs_read){$null=B $b}
foreach($b in $delivery.artifacts){$null=B $b}
$readme=Verify (Join-Path $d 'README.md') '58bf8762dddface66fd67db0c2b85540a77e849310002611f98e7eb86d2c8a85'
$priorSource=Verify (Join-Path $cr 'independent_transfer_aggregation_decimal_review.py') '073e9d93b0d63d4cede208f807d8e1978c9941ec932600fa84ae048c06bb77a4'
$priorPath=Join-Path $cr 'INDEPENDENT_TRANSFER_AGGREGATION_DECIMAL_REVIEW_20260929.json'
$priorBinding=Verify $priorPath (Get-FileHash -LiteralPath $priorPath).Hash.ToLower()
$rows=@(J (Join-Path $result 'SEED_RESULTS.json'))
$groups=@(J (Join-Path $result 'THREE_SEED_SUMMARY.json'))
$deltas=@(J (Join-Path $result 'FULL_MINUS_VISUAL.json'))
$directionCounts=@($rows|Group-Object source_dataset|Select-Object Name,Count)
$negativeR1=@($deltas|Where-Object {$_.r_at_1_mean_delta -lt 0}).Count
$negativeAP=@($deltas|Where-Object {$_.official_trapezoid_mAP_mean_delta -lt 0}).Count
$positiveAP=@($deltas|Where-Object {$_.official_trapezoid_mAP_mean_delta -gt 0})
if($rows.Count -ne 66 -or $groups.Count -ne 22 -or $deltas.Count -ne 11 -or $negativeR1 -ne 11 -or $negativeAP -ne 10 -or $positiveAP.Count -ne 1 -or $positiveAP[0].task -cne 'university1652_street_to_satellite' -or $positiveAP[0].source_dataset -cne 'sues200'){throw 'Descriptive conclusion mismatch'}
$out=Join-Path $d 'ROOT_AGGREGATION_ADOPTION.json'
$res=[ordered]@{status='root_adopted_descriptive_transfer_statistics';time=(Get-Date).ToString('o');source=[ordered]@{path=$PSCommandPath;sha256=(Get-FileHash -LiteralPath $PSCommandPath).Hash.ToLower()};producer=$producerBinding;report=$reportBinding;delivery=$deliveryBinding;independent=$indBinding;independent_source=$indSource;companion=$readme;retained_rejected_checker=@{source=$priorSource;report=$priorBinding;reason='V1 applied fraction tolerance to x100 units; v2 propagates the same tolerance by100 and sets Decimal50 globally. Producer and outputs unchanged.'};scope=@{accepted_runs=12;seed_task_rows=66;three_seed_groups=22;within_task_contrasts=11;metrics=3};independent_numerics=$i.numeric_method;independent_checks=$i.checks;descriptive_findings=@{full_mean_R1_below_visual_tasks=$negativeR1;full_mean_official_mAP_below_visual_tasks=$negativeAP;positive_mAP_task=$positiveAP[0].task;no_significance_claim=$true;no_task_pooling=$true};root_review='Complete aggregation source, original independent checker and full v2 line diff read; all exact input/output/source/report/companion hashes verified; fixed scope and descriptive sign counts independently checked.';actual_unique_file_checks=$bindings.Count;bindings=@($bindings.Values);limits=$r.limits;scientific_execution=$false;live_state_modified=$false}
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($res|ConvertTo-Json -Depth 25))
$f=[IO.File]::Open($out,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write)
try{$f.Write($bytes,0,$bytes.Length)}finally{$f.Dispose()}
[pscustomobject]@{path=$out;sha256=(Get-FileHash -LiteralPath $out).Hash.ToLower();checks=$bindings.Count;scope=$res.scope}|ConvertTo-Json

