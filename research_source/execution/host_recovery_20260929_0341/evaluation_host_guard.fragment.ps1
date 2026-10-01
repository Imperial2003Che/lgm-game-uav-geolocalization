# New host interruption during official evaluation, after all 42 training fits were accepted.
# The interrupted evaluator has only a parent-recorded PID, not an independently observed
# creation time/interpreter pair. No old science creation/exit identity is invented.
$captureRoot = Join-Path $executionRoot 'host_interruption_20260929_0341'
$capturePath = Join-Path $captureRoot 'CAPTURE.json'
$captureSha = '__CAPTURE_SHA__'
if ((Sha $capturePath) -ne $captureSha) { throw 'Latest host interruption capture changed.' }
$capture = Get-Content -LiteralPath $capturePath -Raw | ConvertFrom-Json
if ($capture.schema -ne '__CAPTURE_SCHEMA__' -or $capture.old_science_and_controllers_absent -isnot [bool] -or -not $capture.old_science_and_controllers_absent -or @($capture.actual_python_processes).Count -ne 0 -or @($capture.files).Count -ne __CAPTURE_COUNT__ -or $capture.active.status -ne 'running' -or $capture.primary_status -ne 'running' -or $capture.active.pid -ne 22496 -or $null -ne $capture.active.exit_code -or [IO.Path]::GetFullPath($capture.active.output_dir) -ne $evaluationRoot) { throw 'Host interruption capture does not match the stale interrupted official evaluation.' }
foreach ($row in $capture.files) {
    if ((Sha $row.backup) -ne $row.sha256 -or (Get-Item -LiteralPath $row.backup).Length -ne $row.bytes) { throw 'Archived host interruption file changed.' }
}
$identityRows=@($capture.files | Where-Object { [IO.Path]::GetFileName($_.backup) -eq 'OWNER_SNAPSHOT_20260928_144022952.json' })
if ($identityRows.Count -ne 1 -or $identityRows[0].sha256 -ne '2ad871bafc9eb72591635a0376e44188a5cef3ee8c871f283493bd0c6452be51') { throw 'The last observed controller identity snapshot is missing or changed.' }
$oldIdentity = Get-Content -LiteralPath $identityRows[0].backup -Raw | ConvertFrom-Json
$oldRoleIds=@{primary=@(16412,16636);pipeline=@(30324,10876);extensions=@(29432,18296);latest=@(21636,32572);independent=@(26072,2820)}
$oldIds=@(16412,16636,30324,10876,29432,18296,21636,32572,26072,2820)
$oldProcessRows=@()
if (@($oldIdentity.states).Count -ne 5) { throw 'The last identity snapshot must bind five original controllers.' }
foreach ($role in @('primary','pipeline','extensions','latest','independent')) {
    $roleRows=@($oldIdentity.states | Where-Object role -eq $role)
    if ($roleRows.Count -ne 1 -or @($roleRows[0].owner).Count -ne 1 -or @($roleRows[0].launcher).Count -ne 1) { throw 'Old controller and launcher identities are missing or duplicated.' }
    $roleRow=$roleRows[0]
    if ($roleRow.owner.pid -ne $oldRoleIds[$role][0] -or $roleRow.launcher.pid -ne $oldRoleIds[$role][1] -or $roleRow.owner.parent -ne $roleRow.launcher.pid) { throw 'Old controller PID or parentage differs from the preserved incident.' }
    foreach ($processRow in @($roleRow.owner,$roleRow.launcher)) {
        $proxy=[pscustomobject]@{Name='python.exe';CommandLine=$processRow.command}
        if (-not (Match-Controller $proxy $role)) { throw 'Old controller command or exact role differs from registered execution.' }
        $oldProcessRows+=$processRow
    }
    $capturedState=Get-Content -LiteralPath (Join-Path (Join-Path $incidentRoot 'controllers') $definitions[$role][0]) -Raw | ConvertFrom-Json
    if ($capturedState.status -ne $definitions[$role][4] -or $capturedState.($definitions[$role][2]) -ne $oldRoleIds[$role][0]) { throw 'Preserved original state does not identify the observed controller.' }
    if ((Exact-Time $capturedState.heartbeat_utc) -ge (Exact-Time $capture.last_boot_utc)) { throw 'Preserved state is not older than the captured host boot.' }
}
if ($oldProcessRows.Count -ne 10 -or @($oldProcessRows.pid | Select-Object -Unique).Count -ne 10) { throw 'Exactly ten distinct old controller identities are required.' }
$expectedEvaluationCommand=@($pythonPath,(Join-Path $executionRoot 'primary_path_repair_20260918\run_formal_worker.py'),'--path-compat-sha256',$primaryManifestSha,'evaluate','--dataset','sues200','--data-root','C:\项目\IMTMN\datasets\SUES-200','--evidence','C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\evidence_cache\sues200_clip_image_evidence.npz','--output-dir',$evaluationRoot,'--device','cuda','--workers','8','--seed','1','--data-hash-mode','content','--amp','--eval-batch-size','128','--eval-chunk-size','128','--checkpoint',(Join-Path $runRoot 'best.pt'))
if (@($capture.active.command).Count -ne $expectedEvaluationCommand.Count) { throw 'Interrupted evaluation command length differs.' }
for ($index=0;$index -lt $expectedEvaluationCommand.Count;$index++) { if ($capture.active.command[$index] -cne $expectedEvaluationCommand[$index]) { throw 'Interrupted evaluation command differs from the frozen contract.' } }
function Assert-HostInterruption {
    $capturedBoot=Exact-Time $capture.last_boot_utc
    $actualOs=@(Get-CimInstance Win32_OperatingSystem)
    if ($actualOs.Count -ne 1) { throw 'Current OS boot time is unavailable or ambiguous.' }
    $actualBoot=Exact-Time $actualOs[0].LastBootUpTime
    if ($actualBoot.UtcTicks -ne $capturedBoot.UtcTicks) { throw 'Current OS boot differs from the preserved host interruption; a new capture is required.' }
    if ($capturedBoot -ge (Exact-Time $capture.time) -or $capturedBoot -le (Exact-Time $oldIdentity.time) -or $capturedBoot -le (Exact-Time $capture.active.started_utc)) { throw 'Captured host boot does not follow the observed controllers and active evaluation start.' }
    $observations=@()
    foreach ($prior in $oldProcessRows) {
        $priorStart=Exact-Time $prior.creation
        if ($prior.pid -notin $oldIds -or $priorStart -ge $capturedBoot -or -not $prior.command -or $priorStart.UtcTicks -ne [long]$prior.creation_utc_ticks) { throw 'Old process identity is invalid or not older than the host boot.' }
        $now=@(Get-CimInstance Win32_Process -Filter ('ProcessId='+$prior.pid))
        if ($now.Count -gt 1) { throw 'Process identity observation is ambiguous.' }
        $observed=$null
        if ($now.Count -eq 1) {
            $nowStart=Exact-Time $now[0].CreationDate
            if ($nowStart.UtcTicks -eq $priorStart.UtcTicks) { throw 'An interrupted original process identity is still present.' }
            if ($nowStart -lt $actualBoot -or -not $now[0].CommandLine) { throw 'A reused PID has an invalid creation time or unavailable command.' }
            $observed=[ordered]@{pid=$now[0].ProcessId;creation_time=$nowStart.ToString('o');command=$now[0].CommandLine;original_command_matches=($now[0].CommandLine -ceq $prior.command);identity='different_creation_after_boot'}
        }
        $observations+=[ordered]@{old_pid=$prior.pid;old_creation=$priorStart.ToString('o');old_command=$prior.command;original_identity_absent=$true;current_pid_observation=$observed}
    }
    # No recorded creation time exists for 22496. A post-boot reuse is recorded
    # separately and can never be represented as the original evaluator exiting.
    $scienceNow=@(Get-CimInstance Win32_Process -Filter 'ProcessId=22496')
    if ($scienceNow.Count -gt 1) { throw 'Interrupted evaluator PID observation is ambiguous.' }
    $scienceObservation=$null
    if ($scienceNow.Count -eq 1) {
        $scienceStart=Exact-Time $scienceNow[0].CreationDate
        if ($scienceStart -lt $actualBoot -or -not $scienceNow[0].CommandLine) { throw 'Evaluator PID reuse lacks an unambiguous post-boot identity.' }
        $scienceObservation=[ordered]@{pid=$scienceNow[0].ProcessId;creation_time=$scienceStart.ToString('o');command=$scienceNow[0].CommandLine;identity='post_boot_pid_observation_not_old_exit_proof'}
    }
    return [pscustomobject][ordered]@{captured_boot=$capturedBoot.ToString('o');actual_boot=$actualBoot.ToString('o');old_exit_codes='unknown_not_observed';observations=$observations;interrupted_evaluation=[ordered]@{parent_recorded_pid=22496;parent_recorded_started_utc=$capture.active.started_utc;prior_creation_and_interpreter='not_observed';exit_code='unknown';current_pid_observation=$scienceObservation}}
}
$hostIdentityInitial=Assert-HostInterruption

$rootAdoptionPath = Join-Path $executionRoot 'completion_audits_20260928/ROOT_FIT_42_ADOPTION_20260928.json'
$rootAdoptionSha = 'ca54f91342f77d7d17f18a932c61681ae6f4d7c14f4ffd917c0c1594fc289e87'
if ((Sha $rootAdoptionPath) -ne $rootAdoptionSha) { throw 'Latest complete 42-fit root adoption changed.' }
$rootAdoption = Get-Content -LiteralPath $rootAdoptionPath -Raw | ConvertFrom-Json
if ($rootAdoption.schema -ne 'root-independent-completion-adoption.v1' -or $rootAdoption.adopted -isnot [bool] -or -not $rootAdoption.adopted -or $rootAdoption.completed_fit_count -ne 42) { throw 'Root adoption does not verify all 42 completed frozen fits.' }
$acceptedIds=@($rootAdoption.completed_fit_ids)
if ($acceptedIds.Count -ne 42 -or @($acceptedIds | Select-Object -Unique).Count -ne 42 -or @($acceptedIds | Where-Object { $_ -like 'formal_main/*' }).Count -ne 36 -or @($acceptedIds | Where-Object { $_ -like 'formal_sensitivity/*' }).Count -ne 6 -or 'formal_main/sues200/content/seed_1/resnet18/dim_512' -cnotin $acceptedIds) { throw 'Root completion adoption scope or interrupted evaluation training source is incorrect.' }
foreach ($row in @($rootAdoption.root_script,$rootAdoption.independent_report)+@($rootAdoption.verified_small_evidence_bindings)) {
    if ([IO.Path]::GetExtension($row.path) -in @('.pt','.pth','.ckpt')) { throw 'The 42-fit provenance check must not reopen previously accepted checkpoints.' }
    if ((Sha $row.path) -ne $row.sha256 -or (Get-Item -LiteralPath $row.path).Length -ne $row.bytes) { throw 'Root completion adoption provenance changed.' }
}
function Assert-RecoveryArtifacts {
    # Compare the sealed partial evaluation and its source metadata before launch.
    # Original --stage all performs its unchanged full training/checkpoint and
    # evaluation completion gates, then reruns incomplete evaluations and
    # continues the remaining registered queue.
    # This wrapper does not substitute inherited hashes into those live gates.
    $activeRows=@($capture.files | Where-Object { [IO.Path]::GetDirectoryName($_.path) -eq $evaluationRoot })
    if ($activeRows.Count -ne __ACTIVE_COUNT__) { throw 'Captured partial-evaluation scope changed.' }
    foreach ($row in $activeRows) {
        if ((Sha $row.path) -ne $row.sha256 -or (Get-Item -LiteralPath $row.path).Length -ne $row.bytes) { throw 'Interrupted evaluation artifact changed after preservation.' }
    }
    $actualNames=@(Get-ChildItem -LiteralPath $evaluationRoot -File | ForEach-Object Name | Sort-Object)
    $capturedNames=@($activeRows | ForEach-Object { [IO.Path]::GetFileName($_.path) } | Sort-Object)
    if (($actualNames -join "`n") -cne ($capturedNames -join "`n")) { throw 'Partial-evaluation file membership changed after preservation.' }
    if (Test-Path -LiteralPath (Join-Path $evaluationRoot 'evaluation_manifest.json')) { throw 'A completed or unexpected evaluation manifest is present; inspect rather than rerun.' }
    foreach ($name in @('run_manifest.json','run_config.json','history.json')) {
        $expectedPath=Join-Path $runRoot $name
        $rows=@($capture.files | Where-Object { $_.path -eq $expectedPath })
        if ($rows.Count -ne 1 -or (Sha $expectedPath) -ne $rows[0].sha256 -or (Get-Item -LiteralPath $expectedPath).Length -ne $rows[0].bytes) { throw 'Interrupted evaluation training metadata changed.' }
    }
    $trainManifest=Get-Content -LiteralPath (Join-Path $runRoot 'run_manifest.json') -Raw | ConvertFrom-Json
    $history=@(Get-Content -LiteralPath (Join-Path $runRoot 'history.json') -Raw | ConvertFrom-Json)
    if ($trainManifest.status -ne 'completed' -or $trainManifest.epochs_completed -ne 80 -or $history.Count -ne 80 -or $history[-1].epoch -ne 79 -or $trainManifest.artifacts.'best.pt'.sha256 -ne 'a6e4cac189b7a1f99bc48a7e26530800e44c473ef9a6b09a2ff33490e955b218') { throw 'Interrupted evaluation must use its original accepted completed training source.' }
    $ledgerPath='C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\runs\frozen_formal_matrix_ledger.json'
    $ledgerRows=@($capture.files | Where-Object { $_.path -eq $ledgerPath })
    if ($ledgerRows.Count -ne 1 -or (Sha $ledgerPath) -ne $ledgerRows[0].sha256 -or (Get-Item -LiteralPath $ledgerPath).Length -ne $ledgerRows[0].bytes) { throw 'Captured latest ledger changed before recovery.' }
}
