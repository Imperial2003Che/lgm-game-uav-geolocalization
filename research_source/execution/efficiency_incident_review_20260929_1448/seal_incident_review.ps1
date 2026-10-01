$ErrorActionPreference = 'Stop'
$executionRoot = 'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$packageRoot = 'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch'
$reviewRoot = $PSScriptRoot
$capturePath = Join-Path $executionRoot 'efficiency_incident_20260929_1448\capture_20260929_144939892\CAPTURE.json'
function Binding([string]$path,[string]$expected='') {
    $item = Get-Item -LiteralPath $path
    if ($item.Length -gt 1500000 -or $item.Extension -in @('.pt','.pth','.npz','.npy','.jpg','.png','.exe')) { throw 'Outside small-file static review scope' }
    $hash=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    $after=Get-Item -LiteralPath $path
    if ($item.Length -ne $after.Length -or $item.LastWriteTimeUtc.Ticks -ne $after.LastWriteTimeUtc.Ticks) { throw 'Small source changed while sealing' }
    if ($expected -and $hash -ne $expected) { throw "Binding changed: $path" }
    [ordered]@{path=$item.FullName;sha256=$hash;bytes=$after.Length}
}
function Write-New([string]$name,$value) {
    $path=Join-Path $reviewRoot $name
    $raw=($value | ConvertTo-Json -Depth 45)+"`n"
    $stream=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
    try { $bytes=[Text.UTF8Encoding]::new($false).GetBytes($raw); $stream.Write($bytes,0,$bytes.Length) } finally { $stream.Dispose() }
    Binding $path
}
$captureRecord=Binding $capturePath '7cd62f16dcf7f4a1ab9f3578b7c780ecb641ec02bf0fdf55a0a802f8bec2c1e4'
$capture=Get-Content -LiteralPath $capturePath -Raw | ConvertFrom-Json
$names=@('pipeline_status.json','extension_status.json','latest_baseline_status.json','independent_comparison_status.json','status.json','supervise_pipeline.py','supervise_extensions.py','run_controller_with_state_retry_v2.py','formal_efficiency_component.stderr.log','formal_efficiency_component.stdout.log','run_transactions_formal_efficiency.py','TRANSACTIONS_EXTENSION_PROTOCOL.md')
$used=@($capture.bindings | Where-Object { [IO.Path]::GetFileName($_.source.path) -in $names })
$small=@()
foreach($row in $used) {
    $small+=Binding $row.snapshot.path $row.snapshot.sha256
    $small+=Binding $row.source.path $row.source.sha256
}
$pipeline=Get-Content -LiteralPath (Join-Path (Split-Path $capturePath) '001_pipeline_status.json') -Raw | ConvertFrom-Json
if ($pipeline.status -ne 'failed' -or $pipeline.jobs.Count -ne 7 -or $pipeline.jobs[6].id -ne 'formal_efficiency_component' -or $pipeline.jobs[6].exit_code -ne 1) { throw 'Incident does not match requested failed T6' }
foreach($job in $pipeline.jobs[0..5]) { if ($job.status -ne 'completed' -or $job.exit_code -ne 0) { throw 'First six predecessor runtime records incomplete' } }
$related=@(
    (Binding (Join-Path $packageRoot 'experiments\run_transactions_formal_efficiency.py') '063a2c2a7bddfc4fd4b4063683f6147dc8cab24b54deaf4d3095abb7e14f8615'),
    (Binding (Join-Path $packageRoot 'experiments\transactions_efficiency_analysis.py') 'e5704eb5f8681d7a73386c9b787f68e4f6638703c547a8e671e803b319a99853'),
    (Binding (Join-Path (Split-Path $packageRoot) 'TRANSACTIONS_EXTENSION_PROTOCOL.md')),
    (Binding (Join-Path $executionRoot 'external_efficiency_preparation\corrected_driver_v3\contract.py')),
    (Binding (Join-Path $executionRoot 'external_efficiency_preparation\corrected_driver_v3\driver.py')),
    (Binding (Join-Path $executionRoot 'external_efficiency_preparation\corrected_driver_v3\science.py')),
    (Binding (Join-Path $executionRoot 'external_efficiency_preparation\corrected_driver_v3\HANDOFF.md')),
    (Binding (Join-Path $executionRoot 'external_efficiency_preparation\corrected_driver_v3\SOURCE_MANIFEST.json')),
    (Binding (Join-Path $executionRoot 'extension_plan.json') '13ef69f90ef105db4e55a463532fd6ed38f573b3dbe8cd345fd64176318e46be'),
    (Binding (Join-Path $executionRoot 'latest_baseline_plan.json') '80acc8d9eeb2f4fa15b6ff242c0a64acc180edf2386268aa277d55ffe58c6b1e'),
    (Binding (Join-Path $executionRoot 'independent_comparison_plan_v2.json') 'a5318f7a60497cc7c9ccb74b7cd82ef7f71fcb072c36a90fb192ea27acc6ca49'),
    (Binding (Join-Path $executionRoot 'state_io_retry_20260920_v2\SOURCE_MANIFEST.json') 'd8e6209f5ff2c2180d053e6444cb7df6ec0846405fea7ad6dee9b76a8fcb8dfb')
)
$spec=[ordered]@{
    schema='t6-admission-incident-recovery-design.v1'; status='design_only_not_implemented_not_launched'; created_utc=[DateTimeOffset]::UtcNow.ToString('o')
    incident_capture=$captureRecord; live_state_must_remain_unchanged_until_all_gates_pass=$true
    original_t6_command=@($pipeline.jobs[6].command); original_t6_entrypoint_sha256=$pipeline.jobs[6].entrypoint_sha256
    primary_action='Do not restart; require genuinely completed primary, original source evidence and old identity absence'
    role_order=@('pipeline','extensions','latest','independent')
    existing_supervisor_behavior=[ordered]@{retained_failed_state='Rejected before job loop';absent_state='Creates all seven jobs pending and therefore reruns predecessors';skip_rule='Only existing completed jobs are skipped'}
    state_derivation=[ordered]@{
        input='Exact captured failed pipeline state, then recheck live bytes before publication'
        preserve_without_rewriting=@('Seven job IDs/order/commands/entrypoint SHA','All first six completed records including original parent exit0/start/finish/PID evidence','Original scientific source, plans and primary completed state')
        failed_attempt='Immutable original failed state/logs retained; no edit to original failure, exit1 or timestamps'
        new_resumable_state='Incident-specific derived state with status waiting_for_primary, first six jobs completed, only seventh job pending; remove stale owner/active/error/stopped and seventh active PID/start/finish/exit fields only in the new derivative; bind a full derivation diff to captured input'
        new_attempt_fields='Written only by actually launched original supervisor; do not invent successful exits or original interpreter identities'
        child_command='Original frozen T6 command unchanged; use reviewed state-I/O wrapper role pipeline'
        forbidden='Do not simply retire state and launch unseeded supervisor; do not set original T6 completed/exit0; do not substitute corrected_driver_v3'
    }
    admission_before_any_intent_or_state_retirement=@(
        'Bind new incident, original source SHA/size and unchanged seven job definitions; root acceptance/evidence of predecessor outputs remains distinct from parent runtime records',
        'Verify old controller/launcher/science identities absent; use exact creation/ticks/command/parentage when known, preserve unknown interpreter/exit facts',
        'Check no live scientific child, original supervisor lock and shared resource ownership; preserve existing locks and do not delete intents',
        'Require successful fresh original nvidia-smi compute query and zero foreign parsed PIDs; no desktop-name or unknown-process exemptions. Recheck immediately before launch; original runner repeats its guard',
        'Preserve original baseline environment and actual native environment-import requirements, TORCHINDUCTOR_CACHE_DIR and incident-specific resource admission; do not reuse training 26 GiB as a new runtime kill gate or invent free-physical thresholds',
        'Require default T6 output absent as observed, or separately capture/review any newly existing attempt before explicitly authorizing a new output/restart; do not silently delete outputs',
        'New per-role exclusive intent/retired/launch artifacts must be absent and then created once; any partial mutation/failure becomes a new retained incident, never replay'
    )
    dependent_start_boundary='Safest serial schedule: original T6 must genuinely complete with accepted output and original parent exit0; pipeline must write ready_for_extension_preparation and its identities exit. Only then restore extensions, then latest, then independent, each with exact frozen plan/source and own original predecessor guard. Do not force readiness from T6 manifest presence alone.'
    current_action='Keep failed/interrupted states intact and observe GPU admission later; no present recovery/ValidateOnly/known-failing launch'
    corrected_v3_boundary='Five-layer completion and exits are prerequisites, including successful original pipeline T6; not an in-place recovery substitute and its GPU gate also rejects current entries'
    protocol_change_boundary='If frozen GPU admission cannot naturally be met, prepare a separately reviewed explicit environment/admission change; never smuggle a weaker guard into compatibility recovery'
    full_t6_complete=$false; execution_authorized_by_this_spec=$false
}
$specRecord=Write-New 'RECOVERY_SPEC.json' $spec
$observedAt=[DateTimeOffset]::UtcNow.ToString('o')
$wanted=@(14420,29784,30388,7584,33520,12896,7484,21652,23920)
$matches=@(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -in $wanted } | ForEach-Object { [ordered]@{pid=$_.ProcessId;parent_pid=$_.ParentProcessId;creation_utc=$_.CreationDate.ToUniversalTime().ToString('o');creation_utc_ticks=$_.CreationDate.ToUniversalTime().Ticks.ToString();command=$_.CommandLine} })
$outDir=Join-Path $packageRoot 'analysis\transactions_t6_formal'
$report=[ordered]@{
    schema='independent-t6-admission-incident-static-review.v1'; created_utc=[DateTimeOffset]::UtcNow.ToString('o'); reviewer='/root/sep29_recovery_review'
    diagnosis='Original exclusive-GPU admission rejected 21 foreign compute-query entries before explicit device/config/benchmark steps'
    incident_capture=$captureRecord; failed_job=$pipeline.jobs[6]; first_six_runtime_records=@($pipeline.jobs[0..5])
    capture_bound_small_files=$small; related_source_and_plan_bindings=$related
    complete_stderr_binding=Binding (Join-Path $executionRoot 'stage_logs\formal_efficiency_component.stderr.log') '27cde8cc55651bab5bd2c2adbb8efb19002539f328c8bad753c8ac95350fc9ed'
    default_t6_output_observation=[ordered]@{path=$outDir;exists=(Test-Path -LiteralPath $outDir);observed_utc=$observedAt}
    current_old_pid_observation=[ordered]@{time_utc=$observedAt;requested_ids=$wanted;matches=$matches;interpretation='Presence must be compared by identity; absence is not exit-code evidence. Original T6 interpreter identity/creation/exit handle unobserved.'}
    GPU_observation_scope='Independent read-only nvidia-smi tool calls: WDDM/610.74/RTX4060 Laptop, 21 compute query rows with N/A memory; ordinary table at 14:49:54 local showed 19 C+G entries and 8 percent GPU utilization. Root capture independently seals compute query bytes; no process-type harmlessness inference.'
    correction_applicability='corrected_driver_v3 is separately released post-five-layer analysis, not current pipeline replacement; same foreign GPU owner rejection persists'
    recovery_spec=$specRecord; review_markdown=Binding (Join-Path $reviewRoot 'INCIDENT_REVIEW.md'); sealing_source=Binding $PSCommandPath
    limitations=@('Static diagnosis and recovery design only; no recovery source implemented or executed','No model/scientific imports/checkpoint/cache/image read or GPU benchmark performed','No old recovery/ValidateOnly replay; no live state/queue/source/plan/application modified','Parent T6 Popen exit1 preserved; no dual-handle interpreter exit, controller exit0 or original creation time fabricated','Predecessor runtime exit0 records are not independent scientific acceptance','No T6 result exists from admission failure; full T6 remains incomplete')
}
Write-New 'INDEPENDENT_INCIDENT_REVIEW.json' $report | ConvertTo-Json
$specRecord | ConvertTo-Json
