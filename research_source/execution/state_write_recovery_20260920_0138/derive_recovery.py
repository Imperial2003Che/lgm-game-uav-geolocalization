"""Prepare single-use recovery controls; does not launch or retire state."""
from pathlib import Path
import hashlib,json,shutil,datetime
E=Path(__file__).resolve().parent.parent
I=E/'state_write_recovery_20260920_0138'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
files=[]
for name in ['status.json','pipeline_status.json','extension_status.json','latest_baseline_status.json','independent_comparison_status.json','supervise_pipeline.py','supervise_extensions.py','supervise_latest_baselines.py','supervise_independent_comparisons.py']:
    src=E/name;dst=I/'controllers'/name
    with dst.open('xb') as f:f.write(src.read_bytes())
    if sha(src)!=sha(dst):raise RuntimeError(name)
    files.append(dict(source=str(src),backup=str(dst),sha256=sha(dst),bytes=dst.stat().st_size))
for folder,stages in [('path_registry_recovery_20260918_1239',['primary','pipeline']),('extension_recovery_20260920_0119',['extensions','latest','independent'])]:
    out=I/'prior_launches'/folder;out.mkdir(parents=True)
    for stage in stages:
        for suffix in ['_launch.json','_launch_intent.json','.stdout.log','.stderr.log']:
            src=E/folder/(stage+suffix);dst=out/src.name
            with dst.open('xb') as f:f.write(src.read_bytes())
            if sha(src)!=sha(dst):raise RuntimeError(str(src))
            files.append(dict(source=str(src),backup=str(dst),sha256=sha(dst),bytes=dst.stat().st_size))
preservation=I/'PRESERVED_INCIDENT.json'
with preservation.open('x',encoding='utf-8') as f:
    json.dump(dict(schema='state-write-recovery-preservation.v1',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='preserved_not_launched',files=files),f,indent=2,ensure_ascii=False)
text=(E/'restart_after_path_registry_incident_20260918_v1.ps1').read_text(encoding='utf-8-sig')
text=text.replace("'path_registry_recovery_20260918_1239'","'state_write_recovery_20260920_0138'")
text=text.replace("$checkpointArchiveRoot = Join-Path $executionRoot 'memory_recovery_20260914_1544'\n",'')
text=text.replace("'4b5bc25f4e82ce156901b6ed6ba00fda894d77cb15128618a3a609588b2b9ff2'",repr(sha(preservation)))
text=text.replace('Preserved Sep18 incident','Preserved state-write incident')
start=text.index('function Check-Predecessor(');end=text.index('function Read-MemorySample',start)
text=text[:start]+'''function Argument-Tokens([string]$Role) {
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
    if (-not $CommandLine -or $CommandLine -notmatch '^(?:\\s*(?:"[^"\\r\\n]*"|[^"\\s]+))+\\s*$') { throw 'Malformed controller command line.' }
    return @([regex]::Matches($CommandLine,'"([^"\\r\\n]*)"|([^"\\s]+)') | ForEach-Object { if ($_.Groups[1].Success) { $_.Groups[1].Value } else { $_.Groups[2].Value } })
}
function Match-Controller($Owner,[string]$Role) {
    if (-not $Owner -or $Owner.Name -ne 'python.exe') { return $false }
    $tokens = @(Command-Tokens $Owner.CommandLine)
    $expected = @(Argument-Tokens $Role)
    $executables = @($pythonPath,'C:\\Users\\17703\\AppData\\Local\\Programs\\Python\\Python311\\python.exe')
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
''' +text[end:]
extra='''
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
'''
text=text.replace('$definitions = @{',extra+'\n$definitions = @{',1)
text=text.replace("extensions=@('extension_status.json','supervise_extensions.py'","extensions=@('extension_status.json','supervise_extensions_path_compat_v1.py'")
text=text.replace("'waiting_for_latest_baselines',$null)","'waiting_for_latest_baselines','preceding_controller_missing')")
start=text.index('$proofPath = Join-Path $checkpointArchiveRoot');end=text.index('$pins = @{',start)
text=text[:start]+'''# This recovery follows a completed 80-epoch run, never the old 35-epoch proof.
$completedProofPath = Join-Path $executionRoot 'status_write_incident_20260920_0138/COMPLETED_FIT_REVIEW_20260920.json'
$completedProofSha = 'PENDING_ROOT_COMPLETED_PROOF_SHA'
if ($completedProofSha -notmatch '^[0-9a-f]{64}$' -or (Sha $completedProofPath) -ne $completedProofSha) { throw 'Completed fit proof is not yet bound or has changed.' }
$completedProof = Get-Content -LiteralPath $completedProofPath -Raw | ConvertFrom-Json
# Exact completed-proof schema checks are inserted after root completes its native validator.
if ($completedProof.recovery_authorized -ne $true) { throw 'Completed-fit validation has not authorized recovery.' }
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
''' +text[end:]
text=text.replace("'independent_comparison_plan_v2.json'='a5318f7a60497cc7c9ccb74b7cd82ef7f71fcb072c36a90fb192ea27acc6ca49'","'independent_comparison_plan_v2.json'='a5318f7a60497cc7c9ccb74b7cd82ef7f71fcb072c36a90fb192ea27acc6ca49'\n    'independent_comparison_registration_v2.json'='d4307a90fdc04861051f3bdcbafb58c1201640a203177016ea517a1783e7054c'")
start=text.index('    foreach ($proof in $verified.reports)',text.index("if ($Stage -eq 'primary') {",text.index('$launchPath =')));end=text.index('    # Engineering admission threshold:',start)
text=text[:start]+'''    foreach ($entry in $observed.run_files_after_exit.PSObject.Properties) {
        $row=$entry.Value
        if ([IO.Path]::GetFullPath($row.path) -ne (Join-Path $runRoot $entry.Name) -or (Sha $row.path) -ne $row.sha256 -or (Get-Item -LiteralPath $row.path).Length -ne $row.bytes) { throw 'Completed run file changed since real process exit.' }
    }
    # Checkpoint/artifact bindings from the full native completion proof are checked here.
    foreach ($row in $completedProof.recovery_artifacts) {
        if ((Sha $row.path) -ne $row.sha256 -or (Get-Item -LiteralPath $row.path).Length -ne $row.bytes) { throw 'Completed-fit proof artifact changed.' }
    }
''' +text[end:]
text=text.replace('    Check-Predecessor $previous $definition','    $predecessorIdentity = Check-Predecessor $previous $definition $predecessor')
start=text.index("if ($Stage -eq 'independent') {",text.index('$archivePath = $null'));end=text.index('    $old = Get-Content',start)
text=text[:start]+'{\n'+text[end:]
text=text.replace('@{pipeline=7;extensions=4;latest=2}[$Stage]','@{pipeline=7;extensions=4;latest=2;independent=3}[$Stage]')
start=text.index("$arguments = '-B");end=text.index('$stdout = ',start)
text=text[:start]+'''$argumentTokens = @(Argument-Tokens $Stage)
$arguments = ($argumentTokens | ForEach-Object { '"'+$_+'"' }) -join ' '
''' +text[end:]
text=text.replace('    Check-Predecessor $previousFinal $definition','    $predecessorIdentityFinal = Check-Predecessor $previousFinal $definition $predecessor\n    if ($predecessorIdentityFinal.creation_time -ne $predecessorIdentity.creation_time -or $predecessorIdentityFinal.command -cne $predecessorIdentity.command) { throw \'Predecessor process identity changed during preflight.\' }')
text=text.replace("script_sha256=(Sha $PSCommandPath);status=", "script_sha256=(Sha $PSCommandPath);predecessor=$predecessorIdentity;completed_fit_proof_sha256=$completedProofSha;io_manifest_sha256=$ioManifestSha;status=")
text=text.replace("launcher_pid=$started.Id;python=", "launcher_pid=$started.Id;launcher_creation_time=$started.StartTime.ToString('o');python=")
text=text.replace("if ($archivePath -and (Sha $statePath)","$conflicting = @(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { Match-Controller $_ $Stage })\nif ($conflicting.Count) { throw 'This stage already has a matching wrapper process.' }\nif ($archivePath -and (Sha $statePath)")
out=E/'restart_after_state_write_incident_20260920_v1.ps1'
with out.open('x',encoding='utf-8-sig',newline='') as f:f.write(text.replace('\n','\r\n'))
print(json.dumps({'script':str(out),'sha256':sha(out),'preserved_sha256':sha(preservation),'status':'prepared_placeholder_not_launched'},ensure_ascii=False))
