param([Parameter(Mandatory=$true)][ValidateSet('primary','pipeline','extensions','latest','independent')][string]$Stage,[switch]$ValidateOnly)
$ErrorActionPreference = 'Stop'
$executionRoot = 'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$incidentRoot = Join-Path $executionRoot 'memory_recovery_20260914_1544'
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
function Check-Predecessor($Previous, $Definition) {
    if ($Previous.status -ne $Definition[3]) { throw ('Predecessor is not running/waiting: '+$Previous.status) }
    $owner = Get-CimInstance Win32_Process -Filter ('ProcessId='+$Previous.($Definition[2]))
    if (-not $owner -or $owner.Name -ne 'python.exe' -or $owner.CommandLine -notlike ('*'+(Join-Path $executionRoot $Definition[1])+'*')) { throw 'Predecessor process identity mismatch.' }
    $recordedStart = if ($Previous.supervisor_started_utc) { Exact-Time $Previous.supervisor_started_utc } else { Exact-Time $Previous.started_utc }
    $actualStart = [DateTimeOffset]$owner.CreationDate
    if ($actualStart -gt $recordedStart -or ($recordedStart-$actualStart).TotalSeconds -gt 60) { throw 'Predecessor PID creation time mismatch.' }
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

$definitions = @{
    primary=@('status.json','continue_formal_matrix.py','controller_pid','running','failed')
    pipeline=@('pipeline_status.json','supervise_pipeline.py','supervisor_pid','waiting_for_primary','primary_interrupted')
    extensions=@('extension_status.json','supervise_extensions.py','supervisor_pid','waiting_for_pipeline','preceding_pipeline_interrupted')
    latest=@('latest_baseline_status.json','supervise_latest_baselines_path_compat_v1.py','supervisor_pid','waiting_for_registered_extensions','preceding_controller_missing')
    independent=@('independent_comparison_status.json','supervise_independent_comparisons_path_compat_v1.py','supervisor_pid','waiting_for_latest_baselines',$null)
}
$proofPath = Join-Path $incidentRoot 'checkpoint_verification.json'
if ((Sha $proofPath) -ne '51e555495e325fb6465f81af580919196998baee7a535f3c5ad9380cf5fa8a5b') { throw 'The reviewed checkpoint verification record changed.' }
$verified = Get-Content -LiteralPath $proofPath -Raw | ConvertFrom-Json
if ($verified.status -ne 'verified_complete_epoch_35' -or $verified.cuda_initialized -isnot [bool] -or $verified.cuda_initialized -ne $false -or $verified.executable -ne $pythonPath -or @($verified.reports).Count -ne 2) { throw 'The current complete checkpoint has not been verified.' }
$checkpointNames = @()
foreach ($proof in $verified.reports) {
    $checkpointName = [IO.Path]::GetFileName($proof.file)
    if ($checkpointName -notin @('last.pt','best.pt') -or $checkpointName -in $checkpointNames -or [IO.Path]::GetFullPath($proof.file) -ne (Join-Path (Join-Path $incidentRoot 'run') $checkpointName)) { throw 'The proof must identify two unique archived last/best checkpoints.' }
    if ($proof.epoch_zero_based -ne 34 -or $proof.completed_epochs -ne 35 -or $proof.config_sha256 -ne 'ce71dbaf10c8ae8a1e3aa04b03d35eac275261c52a07d6082dea5d71c3a4a7f5' -or $proof.sha256 -ne 'a7890410279510f75b7c7f11f79a577245116d294bef680758a4b2beb9f237a5') { throw 'Checkpoint proof does not match this verified incident.' }
    $checkpointNames += $checkpointName
}
$pins = @{
    'continue_formal_matrix.py'='4bac7204d1a152b726ed0fb4ebb806a9ef9f5a81b1c2d53f03ba44b0b124d4da'
    'extension_plan.json'='13ef69f90ef105db4e55a463532fd6ed38f573b3dbe8cd345fd64176318e46be'
    'latest_baseline_plan.json'='80acc8d9eeb2f4fa15b6ff242c0a64acc180edf2386268aa277d55ffe58c6b1e'
    'independent_comparison_plan_v2.json'='a5318f7a60497cc7c9ccb74b7cd82ef7f71fcb072c36a90fb192ea27acc6ca49'
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
    foreach ($proof in $verified.reports) {
        $liveCheckpoint = Join-Path $runRoot ([IO.Path]::GetFileName($proof.file))
        if ((Sha $liveCheckpoint) -ne $proof.sha256) { throw 'Live checkpoint changed since verification.' }
    }
    foreach ($name in @('history.json','run_config.json','run_manifest.json')) {
        if ((Sha (Join-Path $runRoot $name)) -ne (Sha (Join-Path (Join-Path $incidentRoot 'run') $name))) { throw 'Live run state changed since preservation.' }
    }
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
    Check-Predecessor $previous $definition
}
$current = $definitions[$Stage]
$statePath = Join-Path $executionRoot $current[0]
$archivePath = $null
if ($Stage -eq 'independent') {
    if (Test-Path -LiteralPath $statePath) { throw 'Independent v2 already has a state; do not recreate it.' }
    $receipt = Get-Content -LiteralPath (Join-Path $executionRoot 'independent_comparison_registration_v2.json') -Raw | ConvertFrom-Json
    if ($receipt.status -ne 'registered_not_launched') { throw 'Independent v2 registration is not ready.' }
} else {
    $old = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    if ($old.status -ne $current[4]) { throw ('Unexpected old state: '+$old.status) }
    $oldOwner = Get-CimInstance Win32_Process -Filter ('ProcessId='+$old.($current[2]))
    if ($oldOwner) {
        $oldEnded = if ($old.stopped_utc) { Exact-Time $old.stopped_utc } else { Exact-Time $old.finished_utc }
        if (([DateTimeOffset]$oldOwner.CreationDate) -le $oldEnded) { throw 'Old controller may still be alive.' }
    }
    if ($Stage -ne 'primary') {
        $expectedJobCount = @{pipeline=7;extensions=4;latest=2}[$Stage]
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
$arguments = '-B "'+(Join-Path $executionRoot $current[1])+'"'
if ($Stage -eq 'primary') { $arguments += ' --stage all --workers 8' }
if ($Stage -eq 'independent') { $arguments += ' --plan "'+(Join-Path $executionRoot 'independent_comparison_plan_v2.json')+'"' }
if ($Stage -in @('latest','independent')) { $arguments += ' --addendum-sha256 '+$addendumSha }
$stdout = Join-Path $incidentRoot ($Stage+'.stdout.log')
$stderr = Join-Path $incidentRoot ($Stage+'.stderr.log')
if ($Stage -eq 'primary') {
    if (@(Get-CimInstance Win32_Process -Filter "Name='python.exe'").Count) { throw 'A Python process appeared before launch.' }
    $memoryFinal = Read-MemorySample
    if ($memoryFinal.headroom_bytes -lt ([long]26*1GB)) { throw 'Commit headroom dropped below admission threshold before launch.' }
    $memorySamples += $memoryFinal
} else {
    $previousFinal = Get-Content -LiteralPath (Join-Path $executionRoot $definition[0]) -Raw | ConvertFrom-Json
    Check-Predecessor $previousFinal $definition
    if ($previousFinal.($definition[2]) -ne $previous.($definition[2])) { throw 'Predecessor owner changed during preflight.' }
}
if ($archivePath -and (Sha $statePath) -ne (Sha $preserved)) { throw 'Old state changed during preflight.' }
if ($ValidateOnly) {
    Write-Output ('Preflight passed for '+$Stage+'; no state moved and no process started.')
    return
}
Save-NewJson $intentPath ([ordered]@{stage=$Stage;time=(Get-Date).ToString('o');python=$pythonPath;arguments=$arguments;archive=$archivePath;stdout=$stdout;stderr=$stderr;memory_samples=$memorySamples;script_sha256=(Sha $PSCommandPath);status='launch_intent_not_completion'})
if ($archivePath) { Move-Item -LiteralPath $statePath -Destination $archivePath }
$env:PYTHONIOENCODING = 'utf-8'
$started = Start-Process -FilePath $pythonPath -ArgumentList $arguments -WorkingDirectory $executionRoot -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
Save-NewJson $launchPath ([ordered]@{stage=$Stage;time=(Get-Date).ToString('o');launcher_pid=$started.Id;python=$pythonPath;arguments=$arguments;stdout=$stdout;stderr=$stderr;retired_state=$archivePath;status='launched_requires_actual_owner_verification'})
Write-Output ('Launched '+$Stage+' launcher '+$started.Id+'; verify actual state and creation time before the next stage.')
