$ErrorActionPreference='Stop'
$suiteRoot='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$suiteIncident=Join-Path $suiteRoot 'host_recovery_20260927_2145'
$targetScript=Join-Path $suiteRoot 'restart_after_host_interruption_20260927_v1.ps1'
$sourceText=[IO.File]::ReadAllText($targetScript)
$sourceHash=(Get-FileHash -LiteralPath $targetScript).Hash.ToLower()
$tokens=$null;$parseErrors=$null
$ast=[Management.Automation.Language.Parser]::ParseInput($sourceText,[ref]$tokens,[ref]$parseErrors)
if ($parseErrors.Count) { throw ($parseErrors|Out-String) }
$replacements=@()
foreach ($fn in @('Sha','Save-NewJson')) {
    $node=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$true)|Where-Object Name -eq $fn)
    if ($node.Count -ne 1) { throw ('Expected one '+$fn) }
    $replacement=if ($fn -eq 'Sha') {
        'function Sha([string]$Path) { if(-not $Path){return $sourceHash}; if($script:options.badHash -and $Path.EndsWith($script:options.badHash)){return ("f"*64)}; if($Path -eq $script:oldStatePath){$script:stateHashes++;if($script:options.lateStateDrift -and $script:stateHashes -ge 2){return ("e"*64)}}; if($script:options.lateCheckpointDrift -and $Path -eq "C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\runs\formal_sensitivity\university1652\backbone_resnet50\seed_1\last.pt"){$script:checkpointHashes++;if($script:checkpointHashes -ge 2){return ("e"*64)}}; if(-not $script:hashCache.ContainsKey($Path)){$script:hashCache[$Path]=(Microsoft.PowerShell.Utility\Get-FileHash -LiteralPath $Path).Hash.ToLower()};return $script:hashCache[$Path] }'
    } else {
        'function Save-NewJson([string]$Path,$Value) { $script:actions.Add([ordered]@{kind="save";path=$Path;value=$Value}) }'
    }
    $replacements+=@{start=$node[0].Extent.StartOffset;length=$node[0].Extent.EndOffset-$node[0].Extent.StartOffset;text=$replacement}
}
foreach ($node in @($ast.FindAll({param($n) $n -is [Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -eq '$env:PYTHONIOENCODING'},$true))) {
    $replacements+=@{start=$node.Extent.StartOffset;length=$node.Extent.EndOffset-$node.Extent.StartOffset;text='# Environment mutation omitted by control harness.'}
}
$mockText=$sourceText
foreach ($r in ($replacements|Sort-Object start -Descending)) { $mockText=$mockText.Remove($r.start,$r.length).Insert($r.start,$r.text) }
$mockBlock=[scriptblock]::Create($mockText)
$script:hashCache=@{}
$script:results=[Collections.Generic.List[object]]::new()
$script:defs=@{
    primary=@('status.json','controller_pid','running')
    pipeline=@('pipeline_status.json','supervisor_pid','waiting_for_primary')
    extensions=@('extension_status.json','supervisor_pid','waiting_for_pipeline')
    latest=@('latest_baseline_status.json','supervisor_pid','waiting_for_registered_extensions')
    independent=@('independent_comparison_status.json','supervisor_pid','waiting_for_latest_baselines')
}
$script:ioPin=[regex]::Match($sourceText,"\`$ioManifestSha = '([0-9a-f]{64})'").Groups[1].Value
if (-not $script:ioPin) { throw 'Missing actual script I/O pin' }
function Fixture-Command([string]$Role) {
    $items=@('C:\Users\17703\AppData\Local\Programs\Python\Python311\python.exe','-B',(Join-Path $suiteRoot 'run_controller_with_state_retry_v2.py'),'--role',$Role,'--io-manifest-sha256',$script:ioPin)
    if ($Role -eq 'primary') { $items+=@('--stage','all','--workers','8','--path-compat-sha256','11de17bd611431e4471eec1b8ac072a2159fbd02e4eb2cb041b4f3b0f00012a1') }
    if ($Role -eq 'extensions') { $items+=@('--manifest-sha256','b985182c80577fa1a98a7511ce5de2a6a360f908ab063d6f6a0e5a2395be3640') }
    if ($Role -eq 'independent') { $items+=@('--plan',(Join-Path $suiteRoot 'independent_comparison_plan_v2.json')) }
    if ($Role -in @('latest','independent')) { $items+=@('--addendum-sha256','0c4217fefb33d6550bda2300bc201f1c869da0b8d5ff02d45ae7af45b7ef6d70') }
    return ($items | ForEach-Object {'"'+$_+'"'}) -join ' '
}
function Get-Content {
    param([string]$LiteralPath,[switch]$Raw)
    $content=Microsoft.PowerShell.Management\Get-Content -LiteralPath $LiteralPath -Raw
    if ($LiteralPath.EndsWith('CHECKPOINT_RECOVERY_PROOF.json')) {
        $o=$content|ConvertFrom-Json
        switch ($script:options.proof) {
            'not_passed' {$o.passed=$false}
            'string_passed' {$o.passed='true'}
            'wrong_epoch' {$o.completed_epochs=24}
            'wrong_resume' {$o.resume_start_epoch=24}
            'wrong_target' {$o.run_id='formal_main/university1652/visual_style/seed_2/resnet18/dim_512'}
            'no_reports' {$o.reports=@()}
            'duplicate_reports' {$o.reports=@($o.reports[0],$o.reports[0])}
            'wrong_checkpoint_sha' {$o.reports[0].sha256='f'*64}
            'cuda_initialized' {$o.cuda_initialized=$true}
            'wrong_ledger' {$o.ledger.sha256='f'*64}
        }
        return $o|ConvertTo-Json -Depth 100
    }
    if ($LiteralPath.EndsWith('ROOT_BATCH_36_ADOPTION_20260922.json')) {
        $o=$content|ConvertFrom-Json
        switch ($script:options.adoption) {
            'not_adopted' {$o.adopted=$false}
            'wrong_count' {$o.completed_fit_count=37}
            'includes_incomplete' {$o.completed_fit_ids[0]='formal_sensitivity/university1652/full/seed_1/resnet50/dim_512'}
        }
        return $o|ConvertTo-Json -Depth 100
    }
    if ($LiteralPath.EndsWith('host_interruption_20260927_2145\CAPTURE.json') -or $LiteralPath.EndsWith('host_interruption_20260927_2145/CAPTURE.json')) {
        $o=$content|ConvertFrom-Json
        switch ($script:options.capture) {
            'fabricated_exit' {$o.active|Add-Member -Force exit_code 0}
            'wrong_history' {$o.history_count=24}
            'wrong_boot' {$o.last_boot_utc='2026-09-20T20:41:38.5Z'}
            'active_owners' {$o.old_science_and_controllers_absent=$false}
            'missing_file' {$o.files=@($o.files|Select-Object -Skip 1)}
        }
        return $o|ConvertTo-Json -Depth 100
    }
    if ($LiteralPath.EndsWith('previous_identity\LIVE_SNAPSHOT_20260922_152741.json')) {
        $o=$content|ConvertFrom-Json
        switch ($script:options.identity) {
            'missing_pair' {$o.states[0].launcher=@()}
            'wrong_role' {$o.states[0].owner[0].CommandLine=$o.states[0].owner[0].CommandLine.Replace('"--role" "primary"','"--role" "latest"')}
            'creation_after_boot' {$o.states[0].owner[0].creation='2026-09-28T00:00:00Z'}
            'wrong_science_command' {($o.actual_python_processes|Where-Object ProcessId -eq 27308).CommandLine+=' --extra value'}
            'wrong_science_parent' {($o.actual_python_processes|Where-Object ProcessId -eq 12096).ParentProcessId=1234}
        }
        return $o|ConvertTo-Json -Depth 100
    }
    if ($script:predecessor -and $LiteralPath -eq (Join-Path $suiteRoot $script:defs[$script:predecessor][0])) {
        $o=$content|ConvertFrom-Json
        $o.status=$script:defs[$script:predecessor][2]
        $o.($script:defs[$script:predecessor][1])=98000
        $startField=if ($script:predecessor -eq 'primary') {'started_utc'} else {'supervisor_started_utc'}
        $o.$startField=$script:predecessorTime.ToString('o')
        $o|Add-Member -Force state_io_compatibility ([pscustomobject]@{role=$script:predecessor;sha256=$script:ioPin})
        if ($script:options.badPredecessorStatus) {$o.status='failed'}
        if ($script:options.badStateRole) {$o.state_io_compatibility.role='independent'}
        return $o|ConvertTo-Json -Depth 100
    }
    if ($LiteralPath -eq $script:oldStatePath) {
        $o=$content|ConvertFrom-Json
        if ($script:options.wrongOldStatus) {$o.status='failed'}
        if ($script:caseStage -ne 'primary') {
            if ($script:options.jobStarted) {$o.jobs[0]|Add-Member -Force started_utc '2026-09-20T04:00:00+08:00'}
            if ($script:options.jobExit) {$o.jobs[0]|Add-Member -Force exit_code 0}
            if ($script:options.zeroPid) {$o.jobs[0]|Add-Member -Force pid 0}
            if ($script:options.nonPending) {$o.jobs[0].status='running'}
            if ($script:options.emptyJobs) {$o.jobs=@()}
            if ($script:options.duplicateJobs) {$o.jobs[1]=$o.jobs[0]}
        }
        return $o|ConvertTo-Json -Depth 100
    }
    return $content
}
function Get-CimInstance {
    param([string]$ClassName,[string]$Filter)
    if ($ClassName -eq 'Win32_OperatingSystem') {
        $script:bootCalls++
        $boot=[DateTimeOffset]::Parse('2026-09-27T20:41:38.5Z')
        if ($script:options.boot -eq 'missing') {return}
        if ($script:options.boot -eq 'changed' -or ($script:options.boot -eq 'late_change' -and $script:bootCalls -ge 2)) {$boot=$boot.AddSeconds(1)}
        return [pscustomobject]@{LastBootUpTime=$boot}
    }
    if ($ClassName -eq 'Win32_Process' -and $Filter -eq 'ProcessId=27308' -and $script:options.oldIdentity) {
        $old=($script:identityFixture.actual_python_processes|Where-Object ProcessId -eq 27308)
        $created=[DateTimeOffset]$old.creation
        $command=$old.CommandLine
        switch ($script:options.oldIdentity) {
            'same_creation_other_command' {$command='python.exe unrelated.py'}
            'new_creation_same_command' {$created=[DateTimeOffset]::Parse('2026-09-27T20:42:00Z')}
            'new_creation_other_command' {$created=[DateTimeOffset]::Parse('2026-09-27T20:42:00Z');$command='python.exe unrelated.py'}
            'new_creation_no_command' {$created=[DateTimeOffset]::Parse('2026-09-27T20:42:00Z');$command=$null}
            'pre_boot_creation' {$created=[DateTimeOffset]::Parse('2026-09-27T20:40:00Z')}
        }
        return [pscustomobject]@{Name='python.exe';ProcessId=27308;CreationDate=$created;CommandLine=$command}
    }
    if ($ClassName -eq 'Win32_PerfFormattedData_PerfOS_Memory') {
        $script:memoryCalls++
        $m=[pscustomobject]@{CommitLimit=[long](64GB);CommittedBytes=[long](30GB)}
        switch ($script:options.memory) {
            'low' {$m.CommittedBytes=[long](40GB)}
            'missing_limit' {$m.PSObject.Properties.Remove('CommitLimit')}
            'missing_commit' {$m.PSObject.Properties.Remove('CommittedBytes')}
            'bool' {$m.CommittedBytes=$false}
            'float' {$m.CommittedBytes=123.5}
            'negative' {$m.CommittedBytes=-1}
            'zero' {$m.CommittedBytes=0}
            'over_limit' {$m.CommittedBytes=[long](65GB)}
            'final_low' {if ($script:memoryCalls -ge 4) {$m.CommittedBytes=[long](40GB)}}
        }
        return $m
    }
    if ($Filter -eq "Name='python.exe'") {
        $script:pythonCalls++
        if ($script:options.python -eq 'always' -or ($script:options.python -eq 'late' -and $script:pythonCalls -ge 2)) { return [pscustomobject]@{Name='python.exe';ProcessId=90000;CommandLine='python.exe unrelated.py'} }
        if ($script:options.duplicateController) { return [pscustomobject]@{Name='python.exe';ProcessId=90001;CommandLine=(Fixture-Command $script:caseStage)} }
        return
    }
    if ($script:options.oldTrainingLive -and $Filter -eq 'ProcessId=7176') { return [pscustomobject]@{Name='python.exe';ProcessId=7176;CreationDate=[DateTimeOffset]::Parse('2026-09-20T01:18:39.10705+08:00')} }
    if ($script:options.observerLive -and $Filter -eq 'ProcessId=23016') { return [pscustomobject]@{Name='python.exe';ProcessId=23016;CreationDate=[DateTimeOffset]::Parse('2026-09-20T02:17:59.08255+08:00')} }
    if ($script:predecessor -and $Filter -eq 'ProcessId=98000') {
        $script:predecessorCalls++
        if ($script:options.owner -eq 'missing') { return }
        $command=Fixture-Command $script:predecessor
        $creation=$script:predecessorTime.AddMilliseconds(-200)
        switch ($script:options.owner) {
            'wrong_role' {$command=$command.Replace(('"--role" "'+$script:predecessor+'"'),'"--role" "independent"')}
            'role_suffix' {$command=$command.Replace(('"--role" "'+$script:predecessor+'"'),('"--role" "'+$script:predecessor+'_evil"'))}
            'extra_args' {$command+=' "--other" "extra"'}
            'wrong_source' {$command=$command.Replace('run_controller_with_state_retry_v2.py','continue_formal_matrix_path_compat_v1.py')}
            'reused' {$creation=$script:predecessorTime.AddMinutes(1)}
            'old_creation' {$creation=$script:predecessorTime.AddMinutes(-2)}
            'late_change' {if ($script:predecessorCalls -ge 2) {$creation=$creation.AddMilliseconds(-1)}}
        }
        return [pscustomobject]@{Name='python.exe';ProcessId=98000;CreationDate=$creation;CommandLine=$command}
    }
    if ($script:options.oldOwnerLive -and $Filter -eq ('ProcessId='+$script:oldOwner)) { return [pscustomobject]@{Name='python.exe';ProcessId=$script:oldOwner;CreationDate=[DateTimeOffset]::Parse('2026-09-20T01:10:00+08:00')} }
    return
}
function Test-Path {
    param([string]$LiteralPath)
    if ($script:options.existingIntent -and $LiteralPath.EndsWith('_launch_intent.json')) {return $true}
    if ($script:options.existingRetired -and [IO.Path]::GetFileName($LiteralPath).StartsWith('retired_')) {return $true}
    if ($script:options.existingStdout -and $LiteralPath.EndsWith('.stdout.log')) {return $true}
    return Microsoft.PowerShell.Management\Test-Path -LiteralPath $LiteralPath
}
function Start-Sleep {param([int]$Seconds) $script:actions.Add([ordered]@{kind='sleep';seconds=$Seconds})}
function Move-Item {param([string]$LiteralPath,[string]$Destination) $script:actions.Add([ordered]@{kind='move';source=$LiteralPath;target=$Destination})}
function Start-Process {
    param([string]$FilePath,[string]$ArgumentList,[string]$WorkingDirectory,[string]$WindowStyle,[string]$RedirectStandardOutput,[string]$RedirectStandardError,[switch]$PassThru)
    $script:actions.Add([ordered]@{kind='start';file=$FilePath;arguments=$ArgumentList;window=$WindowStyle;directory=$WorkingDirectory})
    return [pscustomobject]@{Id=90002;StartTime=(Get-Date)}
}
foreach ($fn in @('Start-Sleep','Start-Process','Move-Item','Get-CimInstance','Get-Content','Test-Path')) {if ((Get-Command $fn).CommandType -ne 'Function') {throw ('Missing mock '+$fn)}}
function Run-Case([string]$Name,[string]$Stage,[hashtable]$Options,[bool]$ExpectedPass,[switch]$Validation) {
    $script:caseStage=$Stage;$script:options=$Options
    $script:actions=[Collections.Generic.List[object]]::new()
    $script:memoryCalls=0;$script:pythonCalls=0;$script:predecessorCalls=0;$script:stateHashes=0;$script:checkpointHashes=0;$script:bootCalls=0
    $script:predecessor=@{pipeline='primary';extensions='pipeline';latest='extensions';independent='latest'}[$Stage]
    $script:predecessorTime=[DateTimeOffset]::Now.AddSeconds(-10)
    $script:oldStatePath=Join-Path $suiteRoot $script:defs[$Stage][0]
    $old=Microsoft.PowerShell.Management\Get-Content -LiteralPath $script:oldStatePath -Raw|ConvertFrom-Json
    $script:oldOwner=$old.($script:defs[$Stage][1])
    $success=$false;$errorText=$null
    try {& $mockBlock -Stage $Stage -ValidateOnly:$Validation | Out-Null;$success=$true} catch {$errorText=$_.Exception.Message}
    $moves=@($script:actions|Where-Object kind -eq 'move');$starts=@($script:actions|Where-Object kind -eq 'start')
    $passed=($success -eq $ExpectedPass)
    if (-not $ExpectedPass -or $Validation) {$passed=$passed -and $moves.Count -eq 0 -and $starts.Count -eq 0}
    if ($ExpectedPass -and -not $Validation) {
        $passed=$passed -and $moves.Count -eq 1 -and $starts.Count -eq 1 -and $starts[0].window -eq 'Hidden'
        $passed=$passed -and $starts[0].arguments.Contains(('"--role" "'+$Stage+'"'))
        $passed=$passed -and $moves[0].target.StartsWith($suiteIncident+'\')
        if ($Stage -eq 'primary') {$passed=$passed -and $script:memoryCalls -eq 4 -and @($script:actions|Where-Object kind -eq 'sleep').Count -eq 2 -and $starts[0].arguments.Contains('"--workers" "8"')}
    }
    $script:results.Add([ordered]@{name=$Name;stage=$Stage;passed=$passed;expected_pass=$ExpectedPass;actual_pass=$success;error=$errorText;memory_samples=$script:memoryCalls;mutations_mocked=$true})
}
$script:identityFixture=Microsoft.PowerShell.Management\Get-Content -LiteralPath (Join-Path $suiteRoot 'host_interruption_20260927_2145\previous_identity\LIVE_SNAPSHOT_20260922_152741.json') -Raw|ConvertFrom-Json
# Only the new host-interruption and changed 75-epoch interfaces are exercised.
# The Sep22 57 checks remain their separate existing report, not recounted here.
foreach ($stage in @('primary','pipeline','extensions','latest','independent')) { Run-Case ($stage+'_stale_state_valid_mock_launch') $stage @{} $true }
foreach ($boot in @('missing','changed','late_change')) {Run-Case ('host_boot_'+$boot) primary @{boot=$boot} $false}
foreach ($identity in @('missing_pair','wrong_role','creation_after_boot','wrong_science_command','wrong_science_parent')) {Run-Case ('snapshot_'+$identity) primary @{identity=$identity} $false}
foreach ($kind in @('same_creation','same_creation_other_command','new_creation_no_command','pre_boot_creation')) {Run-Case ('old_identity_'+$kind) pipeline @{oldIdentity=$kind} $false}
foreach ($kind in @('new_creation_same_command','new_creation_other_command')) {Run-Case ('pid_reuse_'+$kind) pipeline @{oldIdentity=$kind} $true}
foreach ($proof in @('wrong_epoch','wrong_resume')) {Run-Case ('reject_old_24_proof_'+$proof) primary @{proof=$proof} $false}
foreach ($capture in @('fabricated_exit','wrong_history','wrong_boot')) {Run-Case ('capture_'+$capture) primary @{capture=$capture} $false}
Run-Case 'reject_fabricated_failed_state' primary @{wrongOldStatus=$true} $false
Run-Case 'primary_live_checkpoint_must_still_match' primary @{lateCheckpointDrift=$true} $false
Run-Case 'successor_does_not_recheck_advancing_live_checkpoint' pipeline @{lateCheckpointDrift=$true} $true
$failed=@($script:results|Where-Object {-not $_.passed})
$report=[ordered]@{schema='host-recovery-new-controls-review.v1';created=(Get-Date).ToString('o');source=$targetScript;source_sha256=$sourceHash;actual_source_and_artifact_reads=$true;scope='27 new host and 75-epoch interface cases; no recount of Sep22 controls';scientific_imports=$false;process_launches_and_state_moves='All mocked; no science or controller launched';checks=@($script:results);passed=($failed.Count -eq 0);passed_count=@($script:results|Where-Object passed).Count;failed_count=$failed.Count}
$reportPath=Join-Path $suiteIncident ('CONTROL_REVIEW_'+$sourceHash.Substring(0,12)+'_'+(Get-Date -Format HHmmssfff)+'.json')
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($report|ConvertTo-Json -Depth 12))
$stream=[IO.File]::Open($reportPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
try {$stream.Write($bytes,0,$bytes.Length)} finally {$stream.Dispose()}
[pscustomobject]@{report=$reportPath;passed=$report.passed;passed_count=$report.passed_count;failed=$failed}|ConvertTo-Json -Depth 5
if ($failed.Count) {exit 1}
