$ErrorActionPreference='Stop'
$suiteRoot='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$suiteIncident=Join-Path $suiteRoot 'state_write_recovery_20260920_0138'
$targetScript=Join-Path $suiteRoot 'restart_after_state_write_incident_20260920_v1.ps1'
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
        'function Sha([string]$Path) { if(-not $Path){return $sourceHash}; if($script:options.badHash -and $Path.EndsWith($script:options.badHash)){return ("f"*64)}; if($Path -eq $script:oldStatePath){$script:stateHashes++;if($script:options.lateStateDrift -and $script:stateHashes -ge 2){return ("e"*64)}}; if($script:options.lateCheckpointDrift -and $Path.EndsWith("last.pt")){$script:checkpointHashes++;if($script:checkpointHashes -ge 2){return ("e"*64)}}; if(-not $script:hashCache.ContainsKey($Path)){$script:hashCache[$Path]=(Microsoft.PowerShell.Utility\Get-FileHash -LiteralPath $Path).Hash.ToLower()};return $script:hashCache[$Path] }'
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
    $items=@('C:\Users\17703\AppData\Local\Programs\Python\Python311\python.exe','-B',(Join-Path $suiteRoot 'run_controller_with_state_retry.py'),'--role',$Role,'--io-manifest-sha256',$script:ioPin)
    if ($Role -eq 'primary') { $items+=@('--stage','all','--workers','8','--path-compat-sha256','11de17bd611431e4471eec1b8ac072a2159fbd02e4eb2cb041b4f3b0f00012a1') }
    if ($Role -eq 'extensions') { $items+=@('--manifest-sha256','b985182c80577fa1a98a7511ce5de2a6a360f908ab063d6f6a0e5a2395be3640') }
    if ($Role -eq 'independent') { $items+=@('--plan',(Join-Path $suiteRoot 'independent_comparison_plan_v2.json')) }
    if ($Role -in @('latest','independent')) { $items+=@('--addendum-sha256','0c4217fefb33d6550bda2300bc201f1c869da0b8d5ff02d45ae7af45b7ef6d70') }
    return ($items | ForEach-Object {'"'+$_+'"'}) -join ' '
}
function Get-Content {
    param([string]$LiteralPath,[switch]$Raw)
    $content=Microsoft.PowerShell.Management\Get-Content -LiteralPath $LiteralPath -Raw
    if ($LiteralPath.EndsWith('COMPLETED_FIT_REVIEW_20260920.json')) {
        $o=$content|ConvertFrom-Json
        switch ($script:options.proof) {
            'not_passed' {$o.passed=$false}
            'string_passed' {$o.passed='true'}
            'wrong_epoch' {$o.epochs_completed=79}
            'issues' {$o.original_training_completion_issues=@('incomplete')}
            'wrong_target' {$o.run_identifier='formal_main/university1652/visual_style/seed_3/resnet18/dim_512'}
            'no_artifacts' {$o.artifacts_sha256_verified=[pscustomobject]@{}}
            'missing_best' {$o.artifacts_sha256_verified.PSObject.Properties.Remove('best.pt')}
        }
        return $o|ConvertTo-Json -Depth 100
    }
    if ($LiteralPath.EndsWith('OBSERVED_EXIT.json')) {
        $o=$content|ConvertFrom-Json
        switch ($script:options.exit) {
            'nonzero' {$o.actual_exits.'29512'.exit_code=1}
            'missing' {$o.actual_exits.PSObject.Properties.Remove('7176')}
            'string_bool' {$o.both_exited_zero='true'}
            'missing_file' {$o.run_files_after_exit.PSObject.Properties.Remove('process_stdout.log')}
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
        if ($script:options.wrongOldStatus) {$o.status='running'}
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
            'wrong_source' {$command=$command.Replace('run_controller_with_state_retry.py','continue_formal_matrix_path_compat_v1.py')}
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
    $script:memoryCalls=0;$script:pythonCalls=0;$script:predecessorCalls=0;$script:stateHashes=0;$script:checkpointHashes=0
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
foreach ($stage in @('primary','pipeline','extensions','latest','independent')) {
    Run-Case ($stage+'_valid_launch') $stage @{} $true
    Run-Case ($stage+'_validate_only') $stage @{} $true -Validation
    Run-Case ($stage+'_intent_present') $stage @{existingIntent=$true} $false
    Run-Case ($stage+'_old_owner_live') $stage @{oldOwnerLive=$true} $false
    Run-Case ($stage+'_state_hash_changed') $stage @{lateStateDrift=$true} $false
}
foreach ($memory in @('low','missing_limit','missing_commit','bool','float','negative','zero','over_limit','final_low')) {Run-Case ('memory_'+$memory) primary @{memory=$memory} $false}
foreach ($proof in @('not_passed','string_passed','wrong_epoch','issues','wrong_target','no_artifacts','missing_best')) {Run-Case ('proof_'+$proof) primary @{proof=$proof} $false}
foreach ($exit in @('nonzero','missing','string_bool','missing_file')) {Run-Case ('exit_'+$exit) primary @{exit=$exit} $false}
foreach ($owner in @('missing','wrong_role','role_suffix','extra_args','wrong_source','reused','old_creation','late_change')) {Run-Case ('owner_'+$owner) pipeline @{owner=$owner} $false}
foreach ($flag in @('jobStarted','jobExit','zeroPid','nonPending','emptyJobs','duplicateJobs','duplicateController','badStateRole','badPredecessorStatus','existingRetired','existingStdout','wrongOldStatus')) {Run-Case ('independent_'+$flag) independent @{$flag=$true} $false}
foreach ($hash in @('CAPTURE.json','OBSERVED_EXIT.json','COMPLETED_FIT_REVIEW_20260920.json','last.pt','best.pt','run_manifest.json','independent_comparison_registration_v2.json','resilient_state.py','extension_plan.json')) {Run-Case ('hash_'+$hash) primary @{badHash=$hash} $false}
Run-Case 'late_checkpoint_change' primary @{lateCheckpointDrift=$true} $false
Run-Case 'old_training_live' primary @{oldTrainingLive=$true} $false
Run-Case 'observer_live' primary @{observerLive=$true} $false
Run-Case 'python_present' primary @{python='always'} $false
Run-Case 'python_appears_late' primary @{python='late'} $false
$failed=@($script:results|Where-Object {-not $_.passed})
$report=[ordered]@{schema='state-write-recovery-control-review.v1';created=(Get-Date).ToString('o');source=$targetScript;source_sha256=$sourceHash;actual_source_and_artifact_reads=$true;scientific_imports=$false;process_launches_and_state_moves='All mocked; no science or controller launched';checks=@($script:results);passed=($failed.Count -eq 0);passed_count=@($script:results|Where-Object passed).Count;failed_count=$failed.Count}
$reportPath=Join-Path $suiteIncident ('CONTROL_REVIEW_'+$sourceHash.Substring(0,12)+'_'+(Get-Date -Format HHmmssfff)+'.json')
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($report|ConvertTo-Json -Depth 12))
$stream=[IO.File]::Open($reportPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
try {$stream.Write($bytes,0,$bytes.Length)} finally {$stream.Dispose()}
[pscustomobject]@{report=$reportPath;passed=$report.passed;passed_count=$report.passed_count;failed=$failed}|ConvertTo-Json -Depth 5
if ($failed.Count) {exit 1}
