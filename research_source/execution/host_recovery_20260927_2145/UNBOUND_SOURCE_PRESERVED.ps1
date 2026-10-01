param([Parameter(Mandatory=$true)][ValidateSet('primary','pipeline','extensions','latest','independent')][string]$Stage,[switch]$ValidateOnly)
$ErrorActionPreference = 'Stop'
$executionRoot = 'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$incidentRoot = Join-Path $executionRoot 'host_recovery_20260927_2145'
$pythonPath = 'C:\项目\.venvs\lgm-baselines\Scripts\python.exe'
$runRoot = 'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\runs\formal_sensitivity\university1652\backbone_resnet50\seed_1'
function Sha([string]$Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLower() }
function Exact-Time($Value) {
    if ($Value -is [DateTimeOffset]) { return $Value }
    if ($Value -is [DateTime]) { return [DateTimeOffset]$Value }
    if (-not $Value) { throw 'Missing process timestamp.' }
    return [DateTimeOffset]::Parse([string]$Value)
}
function Save-NewJson([string]$Path, $Value) {
    $bytes = [Text.UTF8Encoding]::new($false).GetBytes(($Value | ConvertTo-Json -Depth 12))
    $stream = [IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
    try { $stream.Write($bytes,0,$bytes.Length) } finally { $stream.Dispose() }
}
function Argument-Tokens([string]$Role) {
    $tokens = @('-B',(Join-Path $executionRoot 'run_controller_with_state_retry_v2.py'),'--role',$Role,'--io-manifest-sha256',$ioManifestSha)
    if ($Role -eq 'primary') { $tokens += @('--stage','all','--workers','8','--path-compat-sha256',$primaryManifestSha) }
    if ($Role -eq 'extensions') { $tokens += @('--manifest-sha256',$extensionManifestSha) }
    if ($Role -eq 'independent') { $tokens += @('--plan',(Join-Path $executionRoot 'independent_comparison_plan_v2.json')) }
    if ($Role -in @('latest','independent')) { $tokens += @('--addendum-sha256',$addendumSha) }
    return $tokens
}
function Command-Tokens([string]$CommandLine) {
    # The frozen arguments contain no embedded quotes or escaped quote syntax.
    # Parse complete tokens, then compare the whole argument vector, never substrings.
    if (-not $CommandLine -or $CommandLine -notmatch '^(?:\s*(?:"[^"\r\n]*"|[^"\s]+))+\s*$') { throw 'Malformed controller command line.' }
    return @([regex]::Matches($CommandLine,'"([^"\r\n]*)"|([^"\s]+)') | ForEach-Object { if ($_.Groups[1].Success) { $_.Groups[1].Value } else { $_.Groups[2].Value } })
}
function Match-Controller($Owner,[string]$Role) {
    if (-not $Owner -or $Owner.Name -ne 'python.exe') { return $false }
    $tokens = @(Command-Tokens $Owner.CommandLine)
    $expected = @(Argument-Tokens $Role)
    $executables = @($pythonPath,'C:\Users\17703\AppData\Local\Programs\Python\Python311\python.exe')
    if ($tokens.Count -ne ($expected.Count+1) -or $tokens[0] -notin $executables) { return $false }
    for ($index=0;$index -lt $expected.Count;$index++) { if ($tokens[$index+1] -cne $expected[$index]) { return $false } }
    return $true
}
function Check-Predecessor($Previous,$Definition,[string]$Role) {
    if ($Previous.status -ne $Definition[3]) { throw ('Predecessor is not running/waiting: '+$Previous.status) }
    if ($Previous.state_io_compatibility.role -ne $Role -or $Previous.state_io_compatibility.sha256 -ne $ioManifestSha) { throw 'Predecessor state lacks exact I/O wrapper provenance.' }
    $ownerId = $Previous.($Definition[2])
    if ($null -eq $ownerId -or $ownerId -is [bool] -or $ownerId -le 0) { throw 'Predecessor owner PID is invalid.' }
    $owner = Get-CimInstance Win32_Process -Filter ('ProcessId='+$ownerId)
    if (-not (Match-Controller $owner $Role)) { throw 'Predecessor process role or complete command mismatch.' }
    $recordedStart = if ($Previous.supervisor_started_utc) { Exact-Time $Previous.supervisor_started_utc } else { Exact-Time $Previous.started_utc }
    $actualStart = Exact-Time $owner.CreationDate
    if ($actualStart -gt $recordedStart -or ($recordedStart-$actualStart).TotalSeconds -gt 60) { throw 'Predecessor PID creation time mismatch.' }
    return [pscustomobject][ordered]@{role=$Role;pid=$owner.ProcessId;creation_time=$actualStart.ToString('o');command=$owner.CommandLine;state_started=$recordedStart.ToString('o')}
}
function Read-MemorySample {
    $memory = Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
    if (-not $memory -or $null -eq $memory.CommitLimit -or $null -eq $memory.CommittedBytes -or $memory.CommitLimit -is [bool] -or $memory.CommittedBytes -is [bool]) { throw 'Memory counters are unavailable or invalid.' }
    [long]$limitBytes = 0
    [long]$commitBytes = 0
    if (-not [long]::TryParse([string]$memory.CommitLimit,[ref]$limitBytes) -or -not [long]::TryParse([string]$memory.CommittedBytes,[ref]$commitBytes) -or $limitBytes -le 0 -or $commitBytes -le 0 -or $commitBytes -gt $limitBytes) { throw 'Memory counters are outside the valid measured range.' }
    return [pscustomobject][ordered]@{time=(Get-Date).ToString('o');commit_bytes=$commitBytes;limit_bytes=$limitBytes;headroom_bytes=($limitBytes-$commitBytes);required_headroom_bytes=([long]26*1GB)}
}

# Registered execution addendum, separate from every unchanged science plan.
$addendumPath = Join-Path $executionRoot 'path_alias_queue_20260915/EXECUTION_ADDENDUM.json'
$addendumSha = '0c4217fefb33d6550bda2300bc201f1c869da0b8d5ff02d45ae7af45b7ef6d70'
$addendumRegistration = Join-Path $executionRoot 'path_alias_queue_20260915/REGISTRATION.json'
if ((Sha $addendumPath) -ne $addendumSha -or (Sha $addendumRegistration) -ne 'a76004bd031c858fc407cf2faffca87b4e76ed17172dda877c1698d308c5f234') { throw 'Registered path compatibility addendum changed.' }
$addendum = Get-Content -LiteralPath $addendumPath -Raw | ConvertFrom-Json
foreach ($source in $addendum.files) {
    if ((Sha $source.path) -ne $source.sha256 -or (Get-Item -LiteralPath $source.path).Length -ne $source.bytes) { throw ('Compatibility source changed: '+$source.path) }
}

# Primary path adapter is explicit execution provenance; frozen science is unchanged.
$primaryManifestPath = Join-Path $executionRoot 'primary_path_repair_20260918/SOURCE_MANIFEST.json'
$primaryManifestSha = '11de17bd611431e4471eec1b8ac072a2159fbd02e4eb2cb041b4f3b0f00012a1'
if ((Sha $primaryManifestPath) -ne $primaryManifestSha) { throw 'Primary path compatibility manifest changed.' }
$primaryManifest = Get-Content -LiteralPath $primaryManifestPath -Raw | ConvertFrom-Json
foreach ($source in $primaryManifest.files) {
    if ((Sha $source.path) -ne $source.sha256 -or (Get-Item -LiteralPath $source.path).Length -ne $source.bytes) { throw ('Primary compatibility source changed: '+$source.path) }
}
$preservationPath = Join-Path $incidentRoot 'PRESERVED_INCIDENT.json'
if ((Sha $preservationPath) -ne 'b6e037d17f1168025db7af97481ce5551b68573185b4cac9c67b1a04b8ede6b7') { throw 'Preserved host interruption manifest changed.' }
$preservation = Get-Content -LiteralPath $preservationPath -Raw | ConvertFrom-Json
foreach ($source in $preservation.files) {
    if ((Sha $source.backup) -ne $source.sha256 -or (Get-Item -LiteralPath $source.backup).Length -ne $source.bytes) { throw ('Preserved host interruption artifact changed: '+$source.backup) }
}


$extensionManifestPath = Join-Path $executionRoot 'extension_path_repair_20260920/SOURCE_MANIFEST.json'
$extensionManifestSha = 'b985182c80577fa1a98a7511ce5de2a6a360f908ab063d6f6a0e5a2395be3640'
$ioManifestPath = Join-Path $executionRoot 'state_io_retry_20260920_v2/SOURCE_MANIFEST.json'
$ioManifestSha = 'd8e6209f5ff2c2180d053e6444cb7df6ec0846405fea7ad6dee9b76a8fcb8dfb'
foreach ($binding in @(@($extensionManifestPath,$extensionManifestSha),@($ioManifestPath,$ioManifestSha))) {
    if ((Sha $binding[0]) -ne $binding[1]) { throw 'Reviewed controller manifest changed.' }
    $manifest = Get-Content -LiteralPath $binding[0] -Raw | ConvertFrom-Json
    foreach ($source in $manifest.files) {
        if ((Sha $source.path) -ne $source.sha256 -or (Get-Item -LiteralPath $source.path).Length -ne $source.bytes) { throw ('Reviewed controller source changed: '+$source.path) }
    }
}

$definitions = @{
    primary=@('status.json','continue_formal_matrix_path_compat_v1.py','controller_pid','running','running')
    pipeline=@('pipeline_status.json','supervise_pipeline.py','supervisor_pid','waiting_for_primary','waiting_for_primary')
    extensions=@('extension_status.json','supervise_extensions_path_compat_v1.py','supervisor_pid','waiting_for_pipeline','waiting_for_pipeline')
    latest=@('latest_baseline_status.json','supervise_latest_baselines_path_compat_v1.py','supervisor_pid','waiting_for_registered_extensions','waiting_for_registered_extensions')
    independent=@('independent_comparison_status.json','supervise_independent_comparisons_path_compat_v1.py','supervisor_pid','waiting_for_latest_baselines','waiting_for_latest_baselines')
}
# This is a later OS boot with stale original running/waiting states, not a recorded child failure.
# No exit code is available for interrupted old processes; only their absence and newer boot are proven.
$captureRoot = Join-Path $executionRoot 'host_interruption_20260927_2145'
$capturePath = Join-Path $captureRoot 'CAPTURE.json'
$captureSha = 'b572bb641a696ae216c52563f3e65e92004bc23576c331f14a0b6b1585bd69e0'
if ((Sha $capturePath) -ne $captureSha) { throw 'Latest host interruption capture changed.' }
$capture = Get-Content -LiteralPath $capturePath -Raw | ConvertFrom-Json
if ($capture.schema -ne 'host-interruption-preservation.v1' -or $capture.old_science_and_controllers_absent -isnot [bool] -or -not $capture.old_science_and_controllers_absent -or @($capture.actual_python_processes).Count -ne 0 -or @($capture.files).Count -ne 35 -or $capture.active.status -ne 'running' -or $capture.primary_status -ne 'running' -or $capture.active.pid -ne 27308 -or $null -ne $capture.active.exit_code -or [IO.Path]::GetFullPath($capture.active.output_dir) -ne $runRoot -or $capture.history_count -ne 75 -or $capture.history_last.epoch -ne 74) { throw 'Host interruption capture does not match the stale original training and latest 75 epochs.' }
foreach ($row in $capture.files) {
    if ((Sha $row.backup) -ne $row.sha256 -or (Get-Item -LiteralPath $row.backup).Length -ne $row.bytes) { throw 'Archived host interruption file changed.' }
}
$identityRows=@($capture.files | Where-Object { [IO.Path]::GetDirectoryName($_.backup) -eq (Join-Path $captureRoot 'previous_identity') })
if ($identityRows.Count -ne 1 -or $identityRows[0].sha256 -ne '6b31ef8fdcf2d0f0991cabd6ceafd9687b8be45acbfe4ce04eceb27b0b61adfe') { throw 'The last observed 12-process identity snapshot is missing or changed.' }
$oldIdentity = Get-Content -LiteralPath $identityRows[0].backup -Raw | ConvertFrom-Json
$oldRoleIds=@{primary=@(31792,8124);pipeline=@(45592,44300);extensions=@(43076,35716);latest=@(45980,2036);independent=@(33528,35608)}
$oldIds=@(31792,8124,45592,44300,43076,35716,45980,2036,33528,35608,27308,12096)
$oldProcessRows=@()
if (@($oldIdentity.states).Count -ne 5) { throw 'The last identity snapshot must bind five original controllers.' }
foreach ($role in @('primary','pipeline','extensions','latest','independent')) {
    $roleRows=@($oldIdentity.states | Where-Object role -eq $role)
    if ($roleRows.Count -ne 1 -or @($roleRows[0].owner).Count -ne 1 -or @($roleRows[0].launcher).Count -ne 1) { throw 'Old controller and launcher identities are missing or duplicated.' }
    $roleRow=$roleRows[0]
    if ($roleRow.owner[0].ProcessId -ne $oldRoleIds[$role][0] -or $roleRow.launcher[0].ProcessId -ne $oldRoleIds[$role][1] -or $roleRow.owner[0].ParentProcessId -ne $roleRow.launcher[0].ProcessId) { throw 'Old controller PID or parentage differs from the preserved incident.' }
    foreach ($processRow in @($roleRow.owner[0],$roleRow.launcher[0])) {
        $proxy=[pscustomobject]@{Name='python.exe';CommandLine=$processRow.CommandLine}
        if (-not (Match-Controller $proxy $role)) { throw 'Old controller command or exact role differs from registered execution.' }
        $oldProcessRows+=$processRow
    }
    $capturedState=Get-Content -LiteralPath (Join-Path (Join-Path $captureRoot 'states') $definitions[$role][0]) -Raw | ConvertFrom-Json
    if ($capturedState.status -ne $definitions[$role][4] -or $capturedState.($definitions[$role][2]) -ne $oldRoleIds[$role][0]) { throw 'Preserved original state does not identify the observed controller.' }
    if ((Exact-Time $capturedState.heartbeat_utc) -ge (Exact-Time $capture.last_boot_utc)) { throw 'Preserved state is not older than the captured host boot.' }
}
foreach ($oldId in @(27308,12096)) {
    $processRows=@($oldIdentity.actual_python_processes | Where-Object ProcessId -eq $oldId)
    if ($processRows.Count -ne 1) { throw 'The original scientific launcher/interpreter identity is missing or duplicated.' }
    $processRow=$processRows[0]
    $expectedCommand=@($capture.active.command)
    if ($oldId -eq 12096) { $expectedCommand[0]='C:\Users\17703\AppData\Local\Programs\Python\Python311\python.exe' }
    $observedCommand=@(Command-Tokens $processRow.CommandLine)
    if ($observedCommand.Count -ne $expectedCommand.Count) { throw 'Interrupted science command has the wrong argument count.' }
    for ($index=0;$index -lt $expectedCommand.Count;$index++) { if ($observedCommand[$index] -cne $expectedCommand[$index]) { throw 'Interrupted science command differs from the captured original command.' } }
    $expectedParent=if ($oldId -eq 27308) {31792} else {27308}
    if ($processRow.ParentProcessId -ne $expectedParent) { throw 'Interrupted scientific process parentage differs.' }
    $oldProcessRows+=$processRow
}
if ($oldProcessRows.Count -ne 12 -or @($oldProcessRows.ProcessId | Select-Object -Unique).Count -ne 12) { throw 'Exactly twelve distinct old process identities are required.' }
function Assert-HostInterruption {
    $capturedBoot=Exact-Time $capture.last_boot_utc
    $actualOs=@(Get-CimInstance Win32_OperatingSystem)
    if ($actualOs.Count -ne 1) { throw 'Current OS boot time is unavailable or ambiguous.' }
    $actualBoot=Exact-Time $actualOs[0].LastBootUpTime
    if ($actualBoot.UtcTicks -ne $capturedBoot.UtcTicks) { throw 'Current OS boot differs from the preserved host interruption; a new capture is required.' }
    if ($capturedBoot -ge (Exact-Time $capture.time) -or $capturedBoot -le (Exact-Time $oldIdentity.time)) { throw 'Captured host boot does not follow the last live process observation.' }
    $observations=@()
    foreach ($prior in $oldProcessRows) {
        $priorStart=Exact-Time $prior.creation
        if ($prior.ProcessId -notin $oldIds -or $priorStart -ge $capturedBoot -or -not $prior.CommandLine) { throw 'Old process identity is invalid or not older than the host boot.' }
        $now=@(Get-CimInstance Win32_Process -Filter ('ProcessId='+$prior.ProcessId))
        if ($now.Count -gt 1) { throw 'Process identity observation is ambiguous.' }
        $observed=$null
        if ($now.Count -eq 1) {
            $nowStart=Exact-Time $now[0].CreationDate
            if ($nowStart.UtcTicks -eq $priorStart.UtcTicks) { throw 'An interrupted original process identity is still present.' }
            if ($nowStart -lt $actualBoot -or -not $now[0].CommandLine) { throw 'A reused PID has an invalid creation time or unavailable command.' }
            $observed=[ordered]@{pid=$now[0].ProcessId;creation_time=$nowStart.ToString('o');command=$now[0].CommandLine;original_command_matches=($now[0].CommandLine -ceq $prior.CommandLine);identity='different_creation_after_boot'}
        }
        $observations+=[ordered]@{old_pid=$prior.ProcessId;old_creation=$priorStart.ToString('o');old_command=$prior.CommandLine;original_identity_absent=$true;current_pid_observation=$observed}
    }
    return [pscustomobject][ordered]@{captured_boot=$capturedBoot.ToString('o');actual_boot=$actualBoot.ToString('o');old_exit_codes='unknown_not_observed';observations=$observations}
}
$hostIdentityInitial=Assert-HostInterruption

$checkpointProofPath = Join-Path $executionRoot 'host_interruption_20260927_2145/CHECKPOINT_RECOVERY_PROOF.json'
$checkpointProofSha = 'UNBOUND_75_EPOCH_PROOF_DO_NOT_LAUNCH'
$rootAdoptionPath = Join-Path $executionRoot 'completion_audits_20260922/ROOT_BATCH_36_ADOPTION_20260922.json'
$rootAdoptionSha = '1c7bdd8e27328118789462a3db2f8283d6803e50c26a2914dd4674010ddf358f'
if ($checkpointProofSha -notmatch '^[0-9a-f]{64}$' -or $rootAdoptionSha -notmatch '^[0-9a-f]{64}$') { throw 'Latest checkpoint verification and root completion adoption are not yet bound; no launch permitted.' }
if ((Sha $checkpointProofPath) -ne $checkpointProofSha -or (Sha $rootAdoptionPath) -ne $rootAdoptionSha) { throw 'Reviewed latest recovery evidence changed.' }
$checkpointProof = Get-Content -LiteralPath $checkpointProofPath -Raw | ConvertFrom-Json
$rootAdoption = Get-Content -LiteralPath $rootAdoptionPath -Raw | ConvertFrom-Json
if ($rootAdoption.schema -ne 'root-independent-completion-adoption.v1' -or $rootAdoption.adopted -isnot [bool] -or -not $rootAdoption.adopted -or $rootAdoption.completed_fit_count -ne 36 -or $rootAdoption.formal_evaluation_count -ne 0 -or $rootAdoption.no_scientific_imports_or_live_changes -ne $true) { throw 'Root adoption does not verify exactly 36 completed main fits; its historical partial checkpoint is not reused.' }
$acceptedIds=@($rootAdoption.completed_fit_ids)
if ($acceptedIds.Count -ne 36 -or @($acceptedIds | Select-Object -Unique).Count -ne 36 -or @($acceptedIds | Where-Object { $_ -notlike 'formal_main/*' }).Count -ne 0) { throw 'Root completion adoption includes missing, duplicate or non-main fits.' }
foreach ($row in @($rootAdoption.root_script,$rootAdoption.independent_report)+@($rootAdoption.verified_small_evidence_bindings)+@($rootAdoption.root_observational_evidence)) {
    if ((Sha $row.path) -ne $row.sha256 -or (Get-Item -LiteralPath $row.path).Length -ne $row.bytes) { throw 'Root adoption provenance changed.' }
}
if ($checkpointProof.schema -ne 'host-interruption-checkpoint-recovery-proof.v1' -or $checkpointProof.passed -isnot [bool] -or -not $checkpointProof.passed -or $checkpointProof.status -ne 'verified_complete_epoch_75' -or $checkpointProof.executable -ne $pythonPath -or $checkpointProof.cuda_initialized -isnot [bool] -or $checkpointProof.cuda_initialized -ne $false -or $checkpointProof.run_id -cne 'formal_sensitivity/university1652/full/seed_1/resnet50/dim_512' -or $checkpointProof.completed_epochs -ne 75 -or $checkpointProof.epoch_zero_based -ne 74 -or $checkpointProof.resume_start_epoch -ne 75 -or $checkpointProof.target_epochs -ne 80) { throw 'Independent checkpoint proof does not verify this exact latest complete 75-epoch run.' }
if ($checkpointProof.capture.sha256 -ne $captureSha -or [IO.Path]::GetFullPath($checkpointProof.capture.path) -ne $capturePath -or $checkpointProof.resume_interface.applicable -isnot [bool] -or -not $checkpointProof.resume_interface.applicable -or $checkpointProof.resume_interface.requested -ne 'last' -or [IO.Path]::GetFullPath($checkpointProof.resume_interface.resolved_path) -ne (Join-Path $runRoot 'last.pt')) { throw 'Checkpoint proof does not bind the latest incident and original resume-last interface.' }
if ((Sha $checkpointProof.script.path) -ne $checkpointProof.script.sha256) { throw 'Independent checkpoint review script changed.' }
$checkpointNames=@()
if (@($checkpointProof.reports).Count -ne 2) { throw 'Exactly two reviewed last/best checkpoint reports are required.' }
foreach ($proof in $checkpointProof.reports) {
    $name=[IO.Path]::GetFileName($proof.file)
    if ($name -notin @('last.pt','best.pt') -or $name -in $checkpointNames) { throw 'Latest checkpoint reports must identify unique last/best files.' }
    $checkpointNames+=$name
    $captured=@($capture.files | Where-Object { $_.path -eq (Join-Path $runRoot $name) })
    if ($captured.Count -ne 1 -or [IO.Path]::GetFullPath($proof.file) -notin @($captured[0].path,$captured[0].backup) -or $proof.sha256 -ne $captured[0].sha256 -or $proof.bytes -ne $captured[0].bytes -or $proof.epoch_zero_based -ne 74 -or $proof.completed_epochs -ne 75 -or $proof.config_sha256 -ne $checkpointProof.run_config_sha256) { throw 'Latest checkpoint report does not match the captured complete epoch and configuration.' }
}
$capturedLedger=@($capture.files | Where-Object { $_.path -eq 'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\runs\frozen_formal_matrix_ledger.json' })
if ($capturedLedger.Count -ne 1 -or $checkpointProof.ledger.sha256 -ne $capturedLedger[0].sha256) { throw 'Independent checkpoint proof does not bind the latest ledger.' }
function Assert-RecoveryArtifacts {
    $requiredNames=@('last.pt','best.pt','history.json','run_config.json','run_manifest.json','run.log','process_stdout.log','process_stderr.log')
    $activeRows=@($capture.files | Where-Object { [IO.Path]::GetDirectoryName($_.backup) -eq (Join-Path $captureRoot 'active_run') })
    if ($activeRows.Count -ne 8) { throw 'Captured current run scope changed.' }
    foreach ($name in $requiredNames) {
        $matches=@($activeRows | Where-Object { [IO.Path]::GetFileName($_.path) -eq $name })
        if ($matches.Count -ne 1) { throw 'A required current-run artifact is missing or duplicated.' }
        $row=$matches[0]
        if ([IO.Path]::GetFullPath($row.path) -ne (Join-Path $runRoot $name) -or (Sha $row.path) -ne $row.sha256 -or (Get-Item -LiteralPath $row.path).Length -ne $row.bytes) { throw 'Latest live run changed after the host interruption was captured.' }
    }
    $ledgerPath='C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\runs\frozen_formal_matrix_ledger.json'
    $ledgerRows=@($capture.files | Where-Object { $_.path -eq $ledgerPath })
    if ($ledgerRows.Count -ne 1 -or (Sha $ledgerPath) -ne $ledgerRows[0].sha256 -or (Get-Item -LiteralPath $ledgerPath).Length -ne $ledgerRows[0].bytes) { throw 'Captured latest ledger changed before recovery.' }
}
$pins = @{
    'continue_formal_matrix.py'='4bac7204d1a152b726ed0fb4ebb806a9ef9f5a81b1c2d53f03ba44b0b124d4da'
    'extension_plan.json'='13ef69f90ef105db4e55a463532fd6ed38f573b3dbe8cd345fd64176318e46be'
    'latest_baseline_plan.json'='80acc8d9eeb2f4fa15b6ff242c0a64acc180edf2386268aa277d55ffe58c6b1e'
    'independent_comparison_plan_v2.json'='a5318f7a60497cc7c9ccb74b7cd82ef7f71fcb072c36a90fb192ea27acc6ca49'
    'independent_comparison_registration_v2.json'='d4307a90fdc04861051f3bdcbafb58c1201640a203177016ea517a1783e7054c'
}
foreach ($key in $pins.Keys) { if ((Sha (Join-Path $executionRoot $key)) -ne $pins[$key]) { throw ('Frozen execution source/plan changed: '+$key) } }
foreach ($key in @('supervise_pipeline.py','supervise_extensions.py','supervise_latest_baselines.py','supervise_independent_comparisons.py')) {
    if ((Sha (Join-Path $executionRoot $key)) -ne (Sha (Join-Path (Join-Path $incidentRoot 'controllers') $key))) { throw ('Frozen successor source changed: '+$key) }
}
$core = 'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\lgm_game_pytorch\formal_retrieval.py'
$runner = 'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\experiments\run_frozen_formal_matrix.py'
if ((Sha $core) -ne '081f327f8f83d79ab078adc61e76070c140f13e0ac9a0d8f423bfad15df59862' -or (Sha $runner) -ne 'f251e5088b306ddec4769fab06799008d06194bc459282f2432ac3238f4ba59f') { throw 'Frozen scientific source changed.' }
if ((Sha 'C:\项目\LGM-GAME-Partner-Delivery-20260724\FORMAL_EXPERIMENT_PROTOCOL.md') -ne '29c0502b07f09d45c6fd7d4a5b582fdd9a443acc9e8b818cd9941c18a0ee34f9') { throw 'Frozen scientific protocol changed.' }
$launchPath = Join-Path $incidentRoot ($Stage+'_launch.json')
$intentPath = Join-Path $incidentRoot ($Stage+'_launch_intent.json')
foreach ($path in @($launchPath,$intentPath,(Join-Path $incidentRoot ($Stage+'.stdout.log')),(Join-Path $incidentRoot ($Stage+'.stderr.log')))) {
    if (Test-Path -LiteralPath $path) { throw ('A launch was already attempted; inspect its evidence: '+$path) }
}
if ($Stage -eq 'primary') {
    if (@(Get-CimInstance Win32_Process -Filter "Name='python.exe'").Count) { throw 'Python process remains; inspect before primary start.' }
    Assert-RecoveryArtifacts
    # Engineering admission threshold: measured prior runtime rise plus buffer.
    # It is not a guarantee against future memory use by other applications.
    $memorySamples = @()
    for ($index=0;$index -lt 3;$index++) {
        $sample = Read-MemorySample
        $headroom = $sample.headroom_bytes
        $memorySamples += $sample
        if ($headroom -lt ([long]26*1GB)) {
            $rejection = Join-Path $incidentRoot ('memory_gate_rejected_'+[Guid]::NewGuid().ToString('N')+'.json')
            Save-NewJson $rejection ([ordered]@{status='not_launched_insufficient_commit_headroom';samples=$memorySamples;action='No application was closed and no experiment state was moved.'})
            throw ('Insufficient commit headroom: '+[math]::Round($headroom/1GB,2)+' GiB; require 26 GiB before restart. See '+$rejection)
        }
        if ($index -lt 2) { Start-Sleep -Seconds 15 }
    }
} else {
    $predecessor = @{pipeline='primary';extensions='pipeline';latest='extensions';independent='latest'}[$Stage]
    $definition = $definitions[$predecessor]
    $previous = Get-Content -LiteralPath (Join-Path $executionRoot $definition[0]) -Raw | ConvertFrom-Json
    $predecessorIdentity = Check-Predecessor $previous $definition $predecessor
}
$current = $definitions[$Stage]
$statePath = Join-Path $executionRoot $current[0]
$archivePath = $null
if ($true) {
    $old = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    if ($old.status -ne $current[4]) { throw ('Unexpected old state: '+$old.status) }
    # Assert-HostInterruption verifies actual prior PID identities; no exit code or stopped time is invented.
    if ($Stage -ne 'primary') {
        $expectedJobCount = @{pipeline=7;extensions=4;latest=2;independent=3}[$Stage]
        $preservedState = Get-Content -LiteralPath (Join-Path (Join-Path $incidentRoot 'controllers') $current[0]) -Raw | ConvertFrom-Json
        if (@($old.jobs).Count -ne $expectedJobCount -or @($preservedState.jobs).Count -ne $expectedJobCount) { throw 'Successor task count differs from its unstarted registered scope.' }
        $seenIds = @()
        for ($index=0;$index -lt $expectedJobCount;$index++) {
            $jobId = $old.jobs[$index].id
            if (-not ($jobId -is [string]) -or -not $jobId -or $jobId -in $seenIds -or $jobId -ne $preservedState.jobs[$index].id) { throw 'Successor task IDs differ from the preserved order.' }
            $seenIds += $jobId
        }
        foreach ($job in $old.jobs) {
            if ($job.status -ne 'pending') { throw 'A successor job is not pending; cannot recreate waiting state.' }
            foreach ($field in @('pid','started_utc','finished_utc','exit_code','elapsed_seconds','active_stage','active_pid','child_pid')) {
                if ($null -ne $job.$field) { throw ('A successor job has execution evidence: '+$field) }
            }
        }
    }
    $preserved = Join-Path (Join-Path $incidentRoot 'controllers') $current[0]
    if ((Sha $statePath) -ne (Sha $preserved)) { throw 'State differs from the preserved stale host-interruption state.' }
    $archivePath = Join-Path $incidentRoot ('retired_'+$current[0])
    if (Test-Path -LiteralPath $archivePath) { throw 'Retired state already exists; inspect before retry.' }
    $resolvedSource = [IO.Path]::GetFullPath($statePath)
    $resolvedTarget = [IO.Path]::GetFullPath($archivePath)
    if (-not $resolvedSource.StartsWith($executionRoot+'\',[StringComparison]::OrdinalIgnoreCase) -or -not $resolvedTarget.StartsWith($incidentRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'State archival outside verified workspace.' }
}
$argumentTokens = @(Argument-Tokens $Stage)
$arguments = ($argumentTokens | ForEach-Object { '"'+$_+'"' }) -join ' '
$stdout = Join-Path $incidentRoot ($Stage+'.stdout.log')
$stderr = Join-Path $incidentRoot ($Stage+'.stderr.log')
if ($Stage -eq 'primary') {
    if (@(Get-CimInstance Win32_Process -Filter "Name='python.exe'").Count) { throw 'A Python process appeared before launch.' }
    Assert-RecoveryArtifacts
    $memoryFinal = Read-MemorySample
    if ($memoryFinal.headroom_bytes -lt ([long]26*1GB)) { throw 'Commit headroom dropped below admission threshold before launch.' }
    $memorySamples += $memoryFinal
} else {
    $previousFinal = Get-Content -LiteralPath (Join-Path $executionRoot $definition[0]) -Raw | ConvertFrom-Json
    $predecessorIdentityFinal = Check-Predecessor $previousFinal $definition $predecessor
    if ($predecessorIdentityFinal.creation_time -ne $predecessorIdentity.creation_time -or $predecessorIdentityFinal.command -cne $predecessorIdentity.command) { throw 'Predecessor process identity changed during preflight.' }
    if ($previousFinal.($definition[2]) -ne $previous.($definition[2])) { throw 'Predecessor owner changed during preflight.' }
}
$conflicting = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { Match-Controller $_ $Stage })
if ($conflicting.Count) { throw 'This stage already has a matching wrapper process.' }
if ($archivePath -and (Sha $statePath) -ne (Sha $preserved)) { throw 'Old state changed during preflight.' }
$hostIdentityFinal = Assert-HostInterruption
if ($ValidateOnly) {
    Write-Output ('Preflight passed for '+$Stage+'; no state moved and no process started.')
    return
}
Save-NewJson $intentPath ([ordered]@{stage=$Stage;time=(Get-Date).ToString('o');python=$pythonPath;arguments=$arguments;archive=$archivePath;stdout=$stdout;stderr=$stderr;memory_samples=$memorySamples;script_sha256=(Sha $PSCommandPath);predecessor=$predecessorIdentity;checkpoint_proof_sha256=$checkpointProofSha;root_adoption_sha256=$rootAdoptionSha;incident_capture_sha256=$captureSha;host_interruption=$hostIdentityFinal;io_manifest_sha256=$ioManifestSha;status='launch_intent_not_completion'})
if ($archivePath) { Move-Item -LiteralPath $statePath -Destination $archivePath }
$env:PYTHONIOENCODING = 'utf-8'
$started = Start-Process -FilePath $pythonPath -ArgumentList $arguments -WorkingDirectory $executionRoot -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
Save-NewJson $launchPath ([ordered]@{stage=$Stage;time=(Get-Date).ToString('o');launcher_pid=$started.Id;launcher_creation_time=$started.StartTime.ToString('o');python=$pythonPath;arguments=$arguments;stdout=$stdout;stderr=$stderr;retired_state=$archivePath;status='launched_requires_actual_owner_verification'})
Write-Output ('Launched '+$Stage+' launcher '+$started.Id+'; verify actual state and creation time before the next stage.')
