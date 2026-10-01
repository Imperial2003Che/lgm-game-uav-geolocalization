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
