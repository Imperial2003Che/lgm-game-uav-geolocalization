$ErrorActionPreference='Stop'
$ex='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$out=Join-Path $ex 't6_recovery_review_20260929_1548'
$package=Join-Path $ex 't6_recovery_preparation_20260929_1548'
function Binding([string]$Path) {
    $item=Get-Item -LiteralPath $Path
    if($item.Length -gt 3000000){throw 'Not a small-file binding'}
    [ordered]@{path=$item.FullName;bytes=$item.Length;sha256=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()}
}
function Verify($Expected) {
    $actual=Binding $Expected.path
    if($actual.path -cne $Expected.path -or $actual.bytes -ne $Expected.bytes -or $actual.sha256 -cne $Expected.sha256){throw "Changed binding: $($Expected.path)"}
    return $actual
}
$manifestPath=Join-Path $package 'SOURCE_MANIFEST.json'
$manifestBinding=Binding $manifestPath
if($manifestBinding.sha256 -cne '8cf084500ae398685ab79d629edb1f9ebffd808e28e605c104d8a93a39c52c41'){throw 'Final manifest mismatch'}
$manifest=Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if(@($manifest.candidate_files).Count -ne 14){throw 'Expected exact fourteen candidate files'}
$candidateBindings=@($manifest.candidate_files | ForEach-Object {Verify $_})
$candidate=$candidateBindings | Where-Object {[IO.Path]::GetFileName($_.path) -eq 'pipeline_recovery_candidate.py'}
if($candidate.sha256 -cne 'b95ee9ff8c90b9323b89eb3a9228c36e40576b16830eb07dbd78e38cef1f833e' -or $candidate.bytes -ne 36404){throw 'Candidate source mismatch'}
$preparationPath=Join-Path $package 'PREPARATION_REPORT.json'
$preparationBinding=Binding $preparationPath
if($preparationBinding.sha256 -cne '9ae3709b19ca2e3f96ad0acd8efeeeaa17c09cbab5201fcf2efd2e8ffb6896d4'){throw 'Preparation report mismatch'}
$preparation=Get-Content -LiteralPath $preparationPath -Raw -Encoding UTF8 | ConvertFrom-Json
$controlBinding=Verify $preparation.new_synthetic_controls
$control=Get-Content -LiteralPath $controlBinding.path -Raw -Encoding UTF8 | ConvertFrom-Json
if($control.status -cne 'passed' -or $control.checks -ne 75 -or $control.candidate_source.sha256 -cne $candidate.sha256){throw 'Author synthetic report binding mismatch'}
$controlSource=Verify $control.control_source
$draftBinding=Verify $preparation.rejected_draft
$failedPreparation=Verify $preparation.preparation_path_rejection
$deliveryBinding=Binding (Join-Path $package 'DELIVERY.json')
if($deliveryBinding.sha256 -cne '44bdc4ec10cd0b73228ba82ba28bf606069dbc43306e262a2ff8ac652acd6097'){throw 'Delivery mismatch'}
$null=Verify $manifestBinding
$report=[ordered]@{
    schema='independent-t6-pipeline-recovery-candidate-static-review.v1';
    created_utc=[DateTimeOffset]::UtcNow.ToString('o');reviewer='sep29_recovery_review';
    status='static_review_no_remaining_definite_blocker_for_source_preparation';
    candidate_source=$candidate;source_manifest=$manifestBinding;
    candidate_file_count=14;verified_candidate_file_bindings=$candidateBindings;
    preparation_report=$preparationBinding;author_delivery=$deliveryBinding;
    synthetic_control_report=$controlBinding;synthetic_control_source=$controlSource;
    synthetic_control_scope='Author-reported 75 passing new synthetic checks; bound here, not rerun or independently executed';
    retained_rejected_source=$draftBinding;retained_preparation_path_failure=$failedPreparation;
    review_markdown=(Binding (Join-Path $out 'CANDIDATE_STATIC_REVIEW.md'));
    prior_original_contract_review=(Binding (Join-Path $out 'STATIC_REVIEW.json'));
    sealing_source=(Binding $PSCommandPath);
    read_scope=@('Whole initial candidate and all final changed blocks','Complete final source correction diff','Preparation source and one-line retained root-path correction','PowerShell entry','Semantic state derivation','Final README, manifest, preparation and synthetic report');
    corrected_findings=@('Monitor immutable-record reentry and final closed-record validation','Original commit-counter validation','Popen retained-handle launcher anchor and full controller command tokens','Final source/seed/release/state/boot rechecks and exact prepared seed bytes','Final admission snapshot retained inside intent','Initial launcher duplicate cleanup on creation-query failure','PowerShell source manifest verification before guardian launch','Six whole job records plus exact original stage7 completion gate');
    actual_execution=$false;scientific_execution=$false;independent_test_execution=$false;
    approval_to_launch=$false;T6_scientific_completion=$false;
    candidate_specific_limitations=@(
        'Source preparation only: actual Windows handle monitoring, GPU/memory admission, locks, native imports and real child execution are untested by this review.',
        'Current shared lock missing, no execution release and original GPU rejection are separately documented prerequisites; no live-state or resource observation was performed here.',
        'Cooperative supervisor-lock transfer and filesystem compare/rename/create are not atomic against arbitrary uncooperative writers.',
        'Polling may miss short-lived descendants; only captured handles prove their own exit statuses; parent return and observed absence are separate evidence.',
        'A hard guardian or host termination can release OS-held locks; future incident recovery must still detect surviving descendants.',
        'A real T6 completion requires separate artifact acceptance; this guardian neither adopts science nor starts primary or successor roles.',
        'No candidate, checker, native environment, GPU query, old suite or scientific source was executed; no weights/cache/image files, live locks/states/intents or existing scientific sources were modified.'
    )
}
$destination=Join-Path $out 'CANDIDATE_STATIC_REVIEW.json'
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($report | ConvertTo-Json -Depth 16))
$stream=[IO.File]::Open($destination,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
Binding $destination | ConvertTo-Json
