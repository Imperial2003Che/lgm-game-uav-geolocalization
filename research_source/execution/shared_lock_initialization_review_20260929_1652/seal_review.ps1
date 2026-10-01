$ErrorActionPreference='Stop'
$ex='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$out=Join-Path $ex 'shared_lock_initialization_review_20260929_1652'
$package=Join-Path $ex 'shared_lock_initialization_20260929_1652'
$script=Join-Path $package 'initialize_shared_lock.ps1'
$rejected=Join-Path $package 'INITIALIZE_REJECTED_BEFORE_REGEX_FIX.ps1'
function Binding([string]$Path) {
    $item=Get-Item -LiteralPath $Path
    [ordered]@{path=$item.FullName;bytes=$item.Length;sha256=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()}
}
function NewBytes([string]$Path,[byte[]]$Bytes){
    $stream=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try{$stream.Write($Bytes,0,$Bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
}
$current=Binding $script
$old=Binding $rejected
if($current.sha256 -cne '37d64d971f6f5ded22afc6d31c09d979c2ce1e6806e3b2999a7c0fc83ea54be7'){throw 'Final initializer source changed'}
if($old.sha256 -cne '15619d376530cf8dc7ba5376456aba538d23cdd835210063c0fce1b2ca08943d'){throw 'Rejected draft not preserved'}
$before=[IO.File]::ReadAllText($rejected)
$after=[IO.File]::ReadAllText($script)
$oldLine=($before -split "`r?`n")[37]
$newLine=($after -split "`r?`n")[37]
if($before.Replace($oldLine,$newLine) -cne $after){throw 'Change not restricted to reviewed process regex line'}
if(-not $newLine.Contains('supervise_independent_comparisons?') -or -not $newLine.Contains('(?:_[A-Za-z0-9_]+)?') -or -not $newLine.Contains('run_frozen_formal_matrix')){throw 'Registered command coverage correction absent'}
$diff="--- $rejected`n+++ $script`n@@ -38 +38 @@`n-$oldLine`n+$newLine`n"
$diffPath=Join-Path $out 'INITIALIZATION_REGEX_CORRECTION.patch'
NewBytes $diffPath ([Text.UTF8Encoding]::new($false).GetBytes($diff))
$protocolFiles=@(
    (Join-Path $ex 'external_efficiency_preparation\external_t1_driver_v2\driver.py'),
    (Join-Path $ex 't6_recovery_preparation_20260929_1548\pipeline_recovery_candidate.py'),
    (Join-Path $ex 't6_recovery_preparation_20260929_1548\ROOT_SOURCE_ADOPTION.json'),
    (Join-Path $ex 't6_recovery_preparation_20260929_1548\RECOVERY_CONTRACT.json')
)
$bindings=@($protocolFiles|ForEach-Object {Binding $_})
if($bindings[0].sha256 -cne '98ce4defa8870e3a8a2435e78f8fbe8fabca8b34eb3304d7feef18cbc6920453' -or
   $bindings[1].sha256 -cne 'b95ee9ff8c90b9323b89eb3a9228c36e40576b16830eb07dbd78e38cef1f833e' -or
   $bindings[2].sha256 -cne 'fd093b974627d6ddd6700ffb40c071e2c28deceeb39713fbc8e4cede3dee3fe3' -or
   $bindings[3].sha256 -cne '01bf6d97793d0fbcda9936a85b7955b83e336d0c932531eec9f8f33b179b08a3'){throw 'Protocol/source/root binding mismatch'}
$report=[ordered]@{
    schema='shared-lock-initialization-static-review.v1';
    created_utc=[DateTimeOffset]::UtcNow.ToString('o');
    reviewer='sep29_recovery_review';
    approved_for_exact_initialization=$true;
    status='approved_only_for_reviewed_single_byte_carrier_creation';
    script=$current;
    target='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\latest_baseline_gpu.lock';
    expected_bytes=1;expected_ascii_byte=48;
    source_and_small_file_bindings=$bindings;
    rejected_draft=$old;
    complete_correction_diff=(Binding $diffPath);
    review_markdown=(Binding (Join-Path $out 'STATIC_REVIEW.md'));
    sealing_source=(Binding $PSCommandPath);
    corrected_issue='Initial command regex missed registered v2/path_compat controllers and plural independent comparisons; final source permits the controlled suffixes and includes frozen formal matrix.';
    verified_static_properties=@(
        'Exact absolute target and immediate non-reparse directory parent; no recursive move/delete or external destination.',
        'Independent exact script/target approval and frozen recovery root/contract/protocol hashes required before action.',
        'Two stopped-state/boot/process observations precede target creation; any old PID occupancy is conservatively refused, without asserting historical identity.',
        'FileMode.CreateNew, FileShare.None, one ASCII zero, durable flush, exact byte/length readback; no byte-range lock acquisition.',
        'Compatible with original persistent Windows first-byte lock and candidate existing-file ByteLock.',
        'Existing lock or result refuses replay/overwrite; any partial failure preserves target for review.',
        'Five states checked again after carrier creation; result evidence exclusively created.',
        'No GPU gate exemption, release creation, native import, pipeline/successor launch, or scientific source/state modification.'
    );
    initializer_executed_by_reviewer=$false;
    independent_test_execution=$false;
    gpu_admission_approved=$false;
    recovery_launch_approved=$false;
    scientific_completion=$false;
    interpretation_limits=@(
        'Static source review only; actual creation and readback require a separate execution record.',
        'This carrier is not an owned byte-range lock and does not establish resource exclusivity.',
        'Process observation and CreateNew are not atomic exclusion against later process starts; future guardian gates remain mandatory.',
        'Failure after creation can leave an empty/partial carrier or missing result record; preserve and inspect, never delete or replay.',
        'Existing GPU foreign rows are not changed or exempted; native/resource/process/source/release gates remain required for any future launch.'
    )
}
$destination=Join-Path $out 'STATIC_REVIEW.json'
NewBytes $destination ([Text.UTF8Encoding]::new($false).GetBytes(($report|ConvertTo-Json -Depth 12)))
Binding $destination | ConvertTo-Json -Depth 3
