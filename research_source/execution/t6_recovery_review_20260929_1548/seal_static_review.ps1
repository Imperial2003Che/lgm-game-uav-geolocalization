$ErrorActionPreference='Stop'
$ex='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$out=Join-Path $ex 't6_recovery_review_20260929_1548'
$pkg='C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch'
function Binding([string]$Path) {
    $item=Get-Item -LiteralPath $Path
    if($item.Length -gt 3000000){throw 'Not a small-file binding'}
    [ordered]@{path=$item.FullName;bytes=$item.Length;sha256=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()}
}
$files=@(
    "$ex\efficiency_incident_review_20260929_1448\RECOVERY_SPEC.json",
    "$ex\efficiency_incident_review_20260929_1448\INDEPENDENT_INCIDENT_REVIEW.json",
    "$ex\efficiency_incident_20260929_1448\capture_20260929_144939892\CAPTURE.json",
    "$ex\restart_after_host_interruption_20260929_v1.ps1",
    "$ex\supervise_pipeline.py",
    "$ex\run_controller_with_state_retry_v2.py",
    "$ex\state_io_retry_20260920_v2\resilient_state.py",
    "$ex\state_io_retry_20260920_v2\SOURCE_MANIFEST.json",
    "$ex\continue_formal_matrix.py",
    "$ex\supervise_extensions.py",
    "$ex\supervise_latest_baselines.py",
    "$ex\supervise_independent_comparisons.py",
    "$ex\external_efficiency_preparation\external_t1_driver_v2\driver.py",
    "$pkg\experiments\run_transactions_formal_efficiency.py"
)
$bindings=@($files | ForEach-Object {Binding $_})
$expected=@{
    'supervise_pipeline.py'='a778e291dfef86e5285e05aec3259b6bd54d7a75c64839966770902938e58f90';
    'run_transactions_formal_efficiency.py'='063a2c2a7bddfc4fd4b4063683f6147dc8cab24b54deaf4d3095abb7e14f8615';
    'restart_after_host_interruption_20260929_v1.ps1'='59deea56a6df6ee59282aa50d2612246a0b3e2cb8b9335120af8907f778fdd64';
    'RECOVERY_SPEC.json'='66e499c80036c3ef376993eb0decd01e28cd7adfa07cef54efc1001ac5dc0c45'
}
foreach($binding in $bindings){$name=[IO.Path]::GetFileName($binding.path);if($expected.ContainsKey($name) -and $binding.sha256 -ne $expected[$name]){throw "Source changed: $name"}}
$report=[ordered]@{
    schema='independent-t6-recovery-contract-static-review.v1';
    reviewed_utc=[DateTimeOffset]::UtcNow.ToString('o');
    reviewer='sep29_recovery_review';
    status='design_review_completed_candidate_specific_review_pending';
    scientific_execution=$false;candidate_executed=$false;candidate_adopted=$false;
    source_and_small_file_bindings=$bindings;
    review_markdown=(Binding (Join-Path $out 'STATIC_CHECKLIST.md'));
    sealing_source=(Binding $PSCommandPath);
    specific_findings=@(
        'Original stage logs append at supervisor line 97; preserve failed prefix and new attempt byte offsets.',
        'Pipeline has no actual native import or 26GiB gate; old Sep29 resource sampling was primary-only.',
        'Native probe allowed environment changes must reach actual launch parent, including TORCHINDUCTOR_CACHE_DIR.',
        'Keep six whole completed records and frozen seventh command/source; no absent-state restart.',
        'Persistent shared GPU lock and supervisor lock are distinct; release only supervisor probe before inner acquisition.',
        'Unknown liveness, denied access and PID reuse require conservative refusal, never manufactured old-process identity.',
        'Any post-intent partial mutation is an immutable new incident; no replay or automatic state rollback.',
        'Pipeline-only restoration leaves primary and three successor states unchanged; later serial restoration needs actual predecessor completion and exit.'
    );
    interpretation_limits=@(
        'Small-file/source static review only; no fresh GPU/CIM/resource observation in this report.',
        'No tests, native imports, scientific libraries, model/data/checkpoint reads, process launch, locks, live state edits or candidate execution.',
        'Historical original child exit evidence remains original parent return plus observed absence, not independent dual-handle proof.',
        'Current prerequisite failure must not be bypassed; source design does not authorize launch or establish T6 completion.'
    )
}
$dest=Join-Path $out 'STATIC_REVIEW.json'
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($report | ConvertTo-Json -Depth 12))
$stream=[IO.File]::Open($dest,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
Binding $dest | ConvertTo-Json
