$ErrorActionPreference = 'Stop'
$executionRoot = 'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$candidateRoot = Join-Path $executionRoot 'external_efficiency_preparation\newer_native_b1_contract_v1'
$reviewRoot = $PSScriptRoot
function Read-SmallBinding([string]$path, [string]$expected = '', [long]$expectedBytes = -1) {
    $resolved = (Resolve-Path -LiteralPath $path).Path
    if ([IO.Path]::GetExtension($resolved) -in @('.pt','.pth','.npz','.npy','.jpg','.jpeg','.png')) { throw 'Large scientific artifacts are outside review scope' }
    $before = Get-Item -LiteralPath $resolved
    if ($before.Length -gt 1500000) { throw 'Small-file size limit' }
    $digest = (Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash.ToLowerInvariant()
    $after = Get-Item -LiteralPath $resolved
    if ($before.Length -ne $after.Length -or $before.LastWriteTimeUtc.Ticks -ne $after.LastWriteTimeUtc.Ticks) { throw 'Input changed during review sealing' }
    if ($expected -and $digest -ne $expected) { throw "SHA mismatch: $resolved" }
    if ($expectedBytes -ge 0 -and $after.Length -ne $expectedBytes) { throw "Size mismatch: $resolved" }
    [ordered]@{ path = $resolved; sha256 = $digest; bytes = $after.Length }
}
$manifestPath = Join-Path $candidateRoot 'SOURCE_MANIFEST.json'
$manifestRecord = Read-SmallBinding $manifestPath '35d7290f2f2f3189390bd45eddf2d6c4ac7378e313b14c9507de2536b997c1a4'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.files.Count -ne 10 -or $manifest.public_admission -ne $false -or $manifest.full_t6_complete -ne $false) { throw 'Unexpected final manifest scope' }
$candidateFiles = @($manifest.files | ForEach-Object { Read-SmallBinding $_.path $_.sha256 $_.bytes })
$prep = Get-Content -LiteralPath (Join-Path $candidateRoot 'PREPARATION_REPORT.json') -Raw | ConvertFrom-Json
$related = @($prep.existing_accepted_source_bindings | ForEach-Object { Read-SmallBinding $_.path $_.sha256 $_.bytes })
foreach ($method in @('CAMP','DAC')) {
    $recipe = $prep.source_recipes.$method
    $related += Read-SmallBinding $recipe.manifest.path $recipe.manifest.sha256 $recipe.manifest.bytes
    $related += @($recipe.sources | ForEach-Object { Read-SmallBinding $_.path $_.sha256 $_.bytes })
}
$loaderPath = Join-Path $executionRoot 'external_efficiency_preparation\newer_native_loader_v1\SOURCE_MANIFEST.json'
$loaderManifest = Get-Content -LiteralPath $loaderPath -Raw | ConvertFrom-Json
foreach ($name in @('source_bindings.py','path_aliases.py')) {
    $matching = @($loaderManifest.files | Where-Object { [IO.Path]::GetFileName($_.path) -eq $name })
    if ($matching.Count -ne 1) { throw 'Unique original completion binder source required' }
    $related += Read-SmallBinding $matching[0].path $matching[0].sha256 $matching[0].bytes
}
$prepared = @(
    (Read-SmallBinding (Join-Path $executionRoot 'camp_independent_evaluation_v3\preparations\frozen_three_seed_final_v3\manifest.json') '305c2b9b56fb6bde1781f459467a6718b9f7ed1df9779bcc7d4a209ca2244317'),
    (Read-SmallBinding (Join-Path $executionRoot 'dac_independent_evaluation_v2\preparations\fixed_three_seed\manifest.json') '9923839dbc3c2504588fed791ef0489047d30c585f3efefd40dfc3da07da64ca')
)
$review = [ordered]@{
    schema = 'independent-newer-native-b1-static-review.v1'
    reviewed_at_utc = [DateTimeOffset]::UtcNow.ToString('o')
    reviewer = '/root/sep29_recovery_review'
    verdict = 'no_blocking_defect_for_source_preparation_only'
    scientific_acceptance = $false
    registration_or_execution_admitted = $false
    full_t6_complete = $false
    candidate_manifest = $manifestRecord
    final_source = $prep.source
    candidate_small_file_bindings = $candidateFiles
    related_original_source_bindings = $related
    original_prepared_bindings = $prepared
    review_markdown = Read-SmallBinding (Join-Path $reviewRoot 'REVIEW.md')
    sealing_source = Read-SmallBinding $PSCommandPath
    review_method = @(
        'Complete final b1_contract.py read; original encode_seed bodies and relevant loader/completion contracts inspected statically',
        'New control source, final sealer, documentation, increment and retained author control reports read',
        'Only small-file SHA/size verification performed during sealing; no candidate import or execution and no control rerun'
    )
    findings = @(
        [ordered]@{ id='F1'; status='pass_with_closed_scope'; detail='Original source recipes retain CAMP 395 independent learned pos_scale and DAC 402 complete heads/DSA; binder and alias source pinned' },
        [ordered]@{ id='F2'; status='pass_with_limit'; detail='Original prepared bytes unchanged; batch16-to1 in-memory derivative has its own diff/digest. Copied original seal is not a valid derivative seal' },
        [ordered]@{ id='F3'; status='pass_with_limit'; detail='First-query-per-ten-task deduplicated subset; full ordered gallery indices are metadata, not independently fresh gallery execution' },
        [ordered]@{ id='F4'; status='pass_with_limit'; detail='Candidate ledger consistency does not reread image bytes; descriptor/load/runtime consistency can be caller-synthesized and proves no independent execution' },
        [ordered]@{ id='F5'; status='pass'; detail='Three new public entry points and existing ranking public gate remain unconditional rejection; all candidate science/admission flags false' },
        [ordered]@{ id='F6'; status='documented'; detail='23 author controls run twice after binder pin addition, no new coverage claimed; initial source is explicitly post-edit hash-proven reconstruction. Reviewer reran none' }
    )
    interpretation_limits = @(
        'Static source-preparation review only; no scientific result, timing, parity, full online accuracy, full FLOPs, full T6 or manuscript-readiness claim',
        'CompletedInputs future builder and original B1 encoders were not run; class/path/source identity does not prove separately observed parent or worker execution',
        'Six fresh workers and actual independent Windows launcher/interpreter identity, separate OS-handle exits and closed-stream evidence remain unimplemented',
        'Predecessor/release/resource/shared-lock admission and immutable actual-launch binding remain unimplemented',
        'Fresh complete-gallery encoding, exact membership/order parity, independent B1 parity and actual image-to-ranking timing remain unimplemented',
        'Existing cached descriptors, selected content ledgers, candidate arrays and booleans cannot establish these missing facts',
        'No old suite, source/scientific entry, GPU, PPT, checkpoint/cache/image bytes, recovery or ValidateOnly executed; no frozen source/plan/prepared/release/live state/HANDOFF/automation changed'
    )
}
$outPath = Join-Path $reviewRoot 'INDEPENDENT_STATIC_REVIEW.json'
$raw = $review | ConvertTo-Json -Depth 30
$stream = [IO.File]::Open($outPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
try {
    $bytes = [Text.UTF8Encoding]::new($false).GetBytes($raw + "`n")
    $stream.Write($bytes, 0, $bytes.Length)
} finally { $stream.Dispose() }
Read-SmallBinding $outPath | ConvertTo-Json
