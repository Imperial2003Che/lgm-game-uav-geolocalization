param([Parameter(Mandatory=$true)][ValidateSet('primary','pipeline','extensions','latest','independent')][string]$Stage,[switch]$ValidateOnly)
$ErrorActionPreference = 'Stop'
$executionRoot = 'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$incidentRoot = Join-Path $executionRoot 'host_recovery_20260929_0341'
$pythonPath = 'C:\项目\.venvs\lgm-baselines\Scripts\python.exe'
$runRoot = 'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\runs\formal_main\sues200\content\seed_1'
$evaluationRoot = 'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\evaluations\formal_main\sues200\content\seed_1'
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
if ((Sha $preservationPath) -ne '035c8e4df1f2281097f0fa24c8442c2d9199faa2a87090be0fbcef7819fa9d9a') { throw 'Preserved host interruption manifest changed.' }
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
# New host interruption during official evaluation, after all 42 training fits were accepted.
# The interrupted evaluator has only a parent-recorded PID, not an independently observed
# creation time/interpreter pair. No old science creation/exit identity is invented.
$captureRoot = Join-Path $executionRoot 'host_interruption_20260929_0341'
$capturePath = Join-Path $captureRoot 'CAPTURE.json'
$captureSha = 'a19eeae091aafdab5791367590e2ac22752d9fc5b57f79c0ddaf090072ee06a0'
if ((Sha $capturePath) -ne $captureSha) { throw 'Latest host interruption capture changed.' }
$capture = Get-Content -LiteralPath $capturePath -Raw | ConvertFrom-Json
if ($capture.schema -ne 'host-interruption-preservation.v2' -or $capture.old_science_and_controllers_absent -isnot [bool] -or -not $capture.old_science_and_controllers_absent -or @($capture.actual_python_processes).Count -ne 0 -or @($capture.files).Count -ne 42 -or $capture.active.status -ne 'running' -or $capture.primary_status -ne 'running' -or $capture.active.pid -ne 22496 -or $null -ne $capture.active.exit_code -or [IO.Path]::GetFullPath($capture.active.output_dir) -ne $evaluationRoot) { throw 'Host interruption capture does not match the stale interrupted official evaluation.' }
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
    # evaluation completion gates, then reruns only the interrupted evaluation.
    # This wrapper does not substitute inherited hashes into those live gates.
    $activeRows=@($capture.files | Where-Object { [IO.Path]::GetDirectoryName($_.path) -eq $evaluationRoot })
    if ($activeRows.Count -ne 3) { throw 'Captured partial-evaluation scope changed.' }
    foreach ($row in $activeRows) {
        if ((Sha $row.path) -ne $row.sha256 -or (Get-Item -LiteralPath $row.path).Length -ne $row.bytes) { throw 'Interrupted evaluation artifact changed after preservation.' }
    }
    $actualNames=@(Get-ChildItem -LiteralPath $evaluationRoot -File | ForEach-Object Name | Sort-Object)
    $capturedNames=@($activeRows | ForEach-Object { [IO.Path]::GetFileName($_.path) } | Sort-Object)
    if (($actualNames -join "`n") -cne ($capturedNames -join "`n")) { throw 'Partial-evaluation file membership changed after preservation.' }
    if (Test-Path -LiteralPath (Join-Path $evaluationRoot 'evaluation_manifest.json')) { throw 'A completed or unexpected evaluation manifest is present; inspect rather than rerun.' }
    foreach ($name in @('run_manifest.json','run_config.json','history.json')) {
        $expectedPath=Join-Path $runRoot $name
        $rows=@($preservation.files | Where-Object { $_.source -eq $expectedPath })
        if ($rows.Count -ne 1 -or (Sha $expectedPath) -ne $rows[0].sha256 -or (Get-Item -LiteralPath $expectedPath).Length -ne $rows[0].bytes) { throw 'Interrupted evaluation training metadata changed.' }
    }
    $trainManifest=Get-Content -LiteralPath (Join-Path $runRoot 'run_manifest.json') -Raw | ConvertFrom-Json
    $history=@(Get-Content -LiteralPath (Join-Path $runRoot 'history.json') -Raw | ConvertFrom-Json)
    if ($trainManifest.status -ne 'completed' -or $trainManifest.epochs_completed -ne 80 -or $history.Count -ne 80 -or $history[-1].epoch -ne 79 -or $trainManifest.artifacts.'best.pt'.sha256 -ne 'a6e4cac189b7a1f99bc48a7e26530800e44c473ef9a6b09a2ff33490e955b218') { throw 'Interrupted evaluation must use its original accepted completed training source.' }
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
Save-NewJson $intentPath ([ordered]@{stage=$Stage;time=(Get-Date).ToString('o');python=$pythonPath;arguments=$arguments;archive=$archivePath;stdout=$stdout;stderr=$stderr;memory_samples=$memorySamples;script_sha256=(Sha $PSCommandPath);predecessor=$predecessorIdentity;recovery_mode='original_official_evaluation_after_42_complete_fits';root_adoption_sha256=$rootAdoptionSha;incident_capture_sha256=$captureSha;host_interruption=$hostIdentityFinal;io_manifest_sha256=$ioManifestSha;status='launch_intent_not_completion'})
if ($archivePath) { Move-Item -LiteralPath $statePath -Destination $archivePath }
$env:PYTHONIOENCODING = 'utf-8'
$started = Start-Process -FilePath $pythonPath -ArgumentList $arguments -WorkingDirectory $executionRoot -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
Save-NewJson $launchPath ([ordered]@{stage=$Stage;time=(Get-Date).ToString('o');launcher_pid=$started.Id;launcher_creation_time=$started.StartTime.ToString('o');python=$pythonPath;arguments=$arguments;stdout=$stdout;stderr=$stderr;retired_state=$archivePath;status='launched_requires_actual_owner_verification'})
Write-Output ('Launched '+$Stage+' launcher '+$started.Id+'; verify actual state and creation time before the next stage.')
