param([Parameter(Mandatory=$true)][ValidateSet('primary','pipeline','extensions','latest','independent')][string]$Stage,[switch]$ValidateOnly)
$ErrorActionPreference = 'Stop'
$executionRoot = 'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$incidentRoot = Join-Path $executionRoot 'state_write_recovery_20260920_0138'
$pythonPath = 'C:\项目\.venvs\lgm-baselines\Scripts\python.exe'
$runRoot = 'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\runs\formal_main\university1652\visual_style\seed_2'
function Sha([string]$Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLower() }
function Exact-Time($Value) {
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
    $tokens = @('-B',(Join-Path $executionRoot 'run_controller_with_state_retry.py'),'--role',$Role,'--io-manifest-sha256',$ioManifestSha)
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
if ((Sha $preservationPath) -ne 'b32817173e226422c694bd3b6b20d67e96c01304aa3c584813f88b2ae7760dca') { throw 'Preserved state-write incident manifest changed.' }
$preservation = Get-Content -LiteralPath $preservationPath -Raw | ConvertFrom-Json
foreach ($source in $preservation.files) {
    if ((Sha $source.backup) -ne $source.sha256 -or (Get-Item -LiteralPath $source.backup).Length -ne $source.bytes) { throw ('Preserved state-write incident artifact changed: '+$source.backup) }
}


$extensionManifestPath = Join-Path $executionRoot 'extension_path_repair_20260920/SOURCE_MANIFEST.json'
$extensionManifestSha = 'b985182c80577fa1a98a7511ce5de2a6a360f908ab063d6f6a0e5a2395be3640'
$ioManifestPath = Join-Path $executionRoot 'state_io_retry_20260920/SOURCE_MANIFEST.json'
$ioManifestSha = '3519d4b5ddcc6252fb6e1d2ed164d7eda0f4ef6ec8f8b7baa87c60382dacdc4f'
foreach ($binding in @(@($extensionManifestPath,$extensionManifestSha),@($ioManifestPath,$ioManifestSha))) {
    if ((Sha $binding[0]) -ne $binding[1]) { throw 'Reviewed controller manifest changed.' }
    $manifest = Get-Content -LiteralPath $binding[0] -Raw | ConvertFrom-Json
    foreach ($source in $manifest.files) {
        if ((Sha $source.path) -ne $source.sha256 -or (Get-Item -LiteralPath $source.path).Length -ne $source.bytes) { throw ('Reviewed controller source changed: '+$source.path) }
    }
}

$definitions = @{
    primary=@('status.json','continue_formal_matrix_path_compat_v1.py','controller_pid','running','failed')
    pipeline=@('pipeline_status.json','supervise_pipeline.py','supervisor_pid','waiting_for_primary','primary_interrupted')
    extensions=@('extension_status.json','supervise_extensions_path_compat_v1.py','supervisor_pid','waiting_for_pipeline','preceding_pipeline_interrupted')
    latest=@('latest_baseline_status.json','supervise_latest_baselines_path_compat_v1.py','supervisor_pid','waiting_for_registered_extensions','preceding_controller_missing')
    independent=@('independent_comparison_status.json','supervise_independent_comparisons_path_compat_v1.py','supervisor_pid','waiting_for_latest_baselines','preceding_controller_missing')
}
# This recovery follows a completed 80-epoch run, never the old 35-epoch proof.
$completedProofPath = Join-Path $executionRoot 'status_write_incident_20260920_0138/COMPLETED_FIT_REVIEW_20260920.json'
$completedProofSha = '93890643b3649b7b53951566ed573d494c5f78016954546853bfc416886afb5b'
if ($completedProofSha -notmatch '^[0-9a-f]{64}$' -or (Sha $completedProofPath) -ne $completedProofSha) { throw 'Completed fit proof is not yet bound or has changed.' }
$completedProof = Get-Content -LiteralPath $completedProofPath -Raw | ConvertFrom-Json
if ($completedProof.schema -ne 'detached-fit-completion-review.v1' -or $completedProof.passed -isnot [bool] -or -not $completedProof.passed -or $completedProof.executable -ne $pythonPath -or @($completedProof.original_training_completion_issues).Count -ne 0 -or $completedProof.original_owner_and_observer_absent -ne $true -or $completedProof.epochs_completed -ne 80 -or $completedProof.last_epoch -ne 79 -or $completedProof.completed_fit_count -ne 14 -or $completedProof.formal_evaluation_manifest_count -ne 0 -or $completedProof.ledger_unchanged -ne $true -or @($completedProof.scientific_modules).Count -ne 0) { throw 'Original completed-fit validation is not the accepted 80-epoch audit.' }
if ($completedProof.run_identifier -cne 'formal_main/university1652/visual_style/seed_2/resnet18/dim_512' -or [IO.Path]::GetFullPath($completedProof.run_dir) -ne $runRoot -or $completedProof.source_provenance.manifest_sha256 -ne $primaryManifestSha) { throw 'Completed proof does not identify this exact frozen fit.' }
foreach ($row in @($completedProof.review_script,$completedProof.observer_started,$completedProof.observed_exit,$completedProof.capture)) {
    if ((Sha $row.path) -ne $row.sha256 -or (Get-Item -LiteralPath $row.path).Length -ne $row.bytes) { throw 'Completed proof provenance changed.' }
}
function Assert-CompletedArtifacts {
    $requiredNames=@('run_config.json','history.json','last.pt','best.pt','run.log')
    if (@($completedProof.artifacts_sha256_verified.PSObject.Properties).Count -ne 5) { throw 'Completed proof artifact count changed.' }
    foreach ($name in $requiredNames) {
        $row=$completedProof.artifacts_sha256_verified.$name
        if (-not $row -or [IO.Path]::GetFullPath($row.path) -ne (Join-Path $runRoot $name) -or (Sha $row.path) -ne $row.sha256 -or (Get-Item -LiteralPath $row.path).Length -ne $row.bytes) { throw 'Completed-fit proof artifact changed.' }
    }
    if (@($observed.run_files_after_exit.PSObject.Properties).Count -ne 6) { throw 'Observed run file count changed.' }
    foreach ($name in @('run_manifest.json','run_config.json','history.json','run.log','process_stdout.log','process_stderr.log')) {
        $row=$observed.run_files_after_exit.$name
        if (-not $row -or [IO.Path]::GetFullPath($row.path) -ne (Join-Path $runRoot $name) -or (Sha $row.path) -ne $row.sha256 -or (Get-Item -LiteralPath $row.path).Length -ne $row.bytes) { throw 'Completed run file changed since real process exit.' }
    }
    if ((Sha $completedProof.ledger.path) -ne $completedProof.ledger.sha256) { throw 'Frozen ledger changed before primary recovery.' }
}
$exitPath = Join-Path $executionRoot 'status_write_incident_20260920_0138/OBSERVED_EXIT.json'
if ((Sha $exitPath) -ne '980a441d300228d55c3f1393b71fd16f0d23e1c283be6b02a71c5f0c384027cf') { throw 'Actual detached process exit receipt changed.' }
$observed = Get-Content -LiteralPath $exitPath -Raw | ConvertFrom-Json
if ($observed.both_exited_zero -isnot [bool] -or -not $observed.both_exited_zero -or @($observed.actual_exits.PSObject.Properties).Count -ne 2 -or @($observed.processes).Count -ne 2) { throw 'Both original detached process exits are required.' }
foreach ($requiredPid in @(7176,29512)) {
    $receipt = $observed.actual_exits.([string]$requiredPid)
    if ($null -eq $receipt.exit_code -or $receipt.exit_code -is [bool] -or $receipt.exit_code -ne 0) { throw 'Detached process exit is not actual zero.' }
    $identity = @($observed.processes | Where-Object { $_.ProcessId -eq $requiredPid })
    if ($identity.Count -ne 1) { throw 'Detached process identity is not unique.' }
    $live = Get-CimInstance Win32_Process -Filter ('ProcessId='+$requiredPid)
    if ($live -and ((Exact-Time $live.CreationDate)-(Exact-Time $identity[0].CreationDate)).Duration().TotalMilliseconds -lt 1) { throw 'Original detached process is still alive.' }
}
$observer = Get-CimInstance Win32_Process -Filter 'ProcessId=23016'
if ($observer -and (Exact-Time $observer.CreationDate) -le (Exact-Time $observed.observed_utc)) { throw 'Original detached observer may still be alive.' }
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
    Assert-CompletedArtifacts
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
    $oldOwner = Get-CimInstance Win32_Process -Filter ('ProcessId='+$old.($current[2]))
    if ($oldOwner) {
        $oldEnded = if ($old.stopped_utc) { Exact-Time $old.stopped_utc } else { Exact-Time $old.finished_utc }
        if (([DateTimeOffset]$oldOwner.CreationDate) -le $oldEnded) { throw 'Old controller may still be alive.' }
    }
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
    if ((Sha $statePath) -ne (Sha $preserved)) { throw 'State differs from the preserved failed incident.' }
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
    Assert-CompletedArtifacts
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
if ($ValidateOnly) {
    Write-Output ('Preflight passed for '+$Stage+'; no state moved and no process started.')
    return
}
Save-NewJson $intentPath ([ordered]@{stage=$Stage;time=(Get-Date).ToString('o');python=$pythonPath;arguments=$arguments;archive=$archivePath;stdout=$stdout;stderr=$stderr;memory_samples=$memorySamples;script_sha256=(Sha $PSCommandPath);predecessor=$predecessorIdentity;completed_fit_proof_sha256=$completedProofSha;io_manifest_sha256=$ioManifestSha;status='launch_intent_not_completion'})
if ($archivePath) { Move-Item -LiteralPath $statePath -Destination $archivePath }
$env:PYTHONIOENCODING = 'utf-8'
$started = Start-Process -FilePath $pythonPath -ArgumentList $arguments -WorkingDirectory $executionRoot -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
Save-NewJson $launchPath ([ordered]@{stage=$Stage;time=(Get-Date).ToString('o');launcher_pid=$started.Id;launcher_creation_time=$started.StartTime.ToString('o');python=$pythonPath;arguments=$arguments;stdout=$stdout;stderr=$stderr;retired_state=$archivePath;status='launched_requires_actual_owner_verification'})
Write-Output ('Launched '+$Stage+' launcher '+$started.Id+'; verify actual state and creation time before the next stage.')
