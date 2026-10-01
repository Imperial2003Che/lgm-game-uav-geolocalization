$ErrorActionPreference='Stop'
$suiteRoot='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$suiteIncident=Join-Path $suiteRoot 'path_registry_recovery_20260918_1239'
$targetScript=Join-Path $suiteRoot 'restart_after_path_registry_incident_20260918_v1.ps1'
$script:sourceText=[IO.File]::ReadAllText($targetScript)
$sourceHash=(Get-FileHash -LiteralPath $targetScript).Hash.ToLower()
$tokens=$null;$parseErrors=$null
$parsed=[Management.Automation.Language.Parser]::ParseInput($script:sourceText,[ref]$tokens,[ref]$parseErrors)
if ($parseErrors.Count) { throw ($parseErrors|Out-String) }
$replacements=@()
foreach($fn in @('Sha','Save-NewJson')) {
    $node=@($parsed.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$true)|Where-Object Name -eq $fn)
    if($node.Count -ne 1){throw ('Expected one '+$fn+' function')}
    $replacement=if($fn -eq 'Sha'){
        'function Sha([string]$Path) { if(-not $Path){return $sourceHash}; if($script:caseOptions.lateStateDrift -and $Path -eq (Join-Path $suiteRoot $script:definitions[$script:caseStage][0])){$script:stateHashCalls++;if($script:stateHashCalls -ge 2){return ("f"*64)}}; if($script:caseOptions.badHash -and $Path.EndsWith($script:caseOptions.badHash)){return ("f"*64)}; if(-not $script:hashCache.ContainsKey($Path)){$script:hashCache[$Path]=(Microsoft.PowerShell.Utility\Get-FileHash -LiteralPath $Path).Hash.ToLower()}; return $script:hashCache[$Path] }'
    }else{
        'function Save-NewJson([string]$Path,$Value){$script:actions.Add([ordered]@{kind="save";path=$Path;value=$Value})}'
    }
    $replacements+=@{start=$node[0].Extent.StartOffset;length=$node[0].Extent.EndOffset-$node[0].Extent.StartOffset;text=$replacement}
}
$envAssignment=@($parsed.FindAll({param($n) $n -is [Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -eq '$env:PYTHONIOENCODING'},$true))
foreach($node in $envAssignment){$replacements+=@{start=$node.Extent.StartOffset;length=$node.Extent.EndOffset-$node.Extent.StartOffset;text='# Environment assignment omitted by independent test harness.'}}
$mockText=$script:sourceText
foreach($r in ($replacements|Sort-Object start -Descending)){$mockText=$mockText.Remove($r.start,$r.length).Insert($r.start,$r.text)}
$mockBlock=[scriptblock]::Create($mockText)
$script:hashCache=@{}
$script:results=[Collections.Generic.List[object]]::new()
$script:definitions=@{
 primary=@('status.json','continue_formal_matrix_path_compat_v1.py','controller_pid','running','failed')
 pipeline=@('pipeline_status.json','supervise_pipeline.py','supervisor_pid','waiting_for_primary','primary_interrupted')
 extensions=@('extension_status.json','supervise_extensions.py','supervisor_pid','waiting_for_pipeline','preceding_pipeline_interrupted')
 latest=@('latest_baseline_status.json','supervise_latest_baselines_path_compat_v1.py','supervisor_pid','waiting_for_registered_extensions','preceding_controller_missing')
 independent=@('independent_comparison_status.json','supervise_independent_comparisons_path_compat_v1.py','supervisor_pid','waiting_for_latest_baselines',$null)
}
function Get-Content {
    param([string]$LiteralPath,[switch]$Raw)
    $text=Microsoft.PowerShell.Management\Get-Content -LiteralPath $LiteralPath -Raw
    if($LiteralPath.EndsWith('checkpoint_verification.json')){
        $o=$text|ConvertFrom-Json
        switch($script:caseOptions.proof){
            'empty' {$o.reports=@()}
            'duplicate' {$o.reports=@($o.reports[0],$o.reports[0])}
            'wrong_epoch' {$o.reports[0].completed_epochs=34}
            'wrong_config' {$o.reports[0].config_sha256='f'*64}
            'wrong_archive' {$o.reports[0].file=Join-Path (Join-Path $suiteIncident 'run') 'last.pt'}
            'missing_cuda' {$o.PSObject.Properties.Remove('cuda_initialized')}
        }
        return $o|ConvertTo-Json -Depth 100
    }
    if($script:predecessorName -and $LiteralPath -eq (Join-Path $suiteRoot $script:predecessorDefinition[0])){
        $o=$text|ConvertFrom-Json
        $o.status=$script:predecessorDefinition[3]
        if($script:caseOptions.predecessorStatus){$o.status=$script:caseOptions.predecessorStatus}
        return $o|ConvertTo-Json -Depth 100
    }
    if($LiteralPath -eq (Join-Path $suiteRoot $script:definitions[$script:caseStage][0]) -and $script:caseStage -ne 'primary'){
        $o=$text|ConvertFrom-Json
        if($script:caseOptions.jobExit){$o.jobs[0]|Add-Member exit_code 0 -Force}
        if($script:caseOptions.jobFinished){$o.jobs[0]|Add-Member finished_utc '2026-09-14T15:00:00+08:00' -Force}
        if($script:caseOptions.jobStarted){$o.jobs[0]|Add-Member started_utc '2026-09-14T15:00:00+08:00' -Force}
        if($script:caseOptions.zeroPid){$o.jobs[0]|Add-Member pid 0 -Force}
        if($script:caseOptions.duplicateJob){$o.jobs[1]=$o.jobs[0]}
        if($script:caseOptions.emptyJobs){$o.jobs=@()}
        return $o|ConvertTo-Json -Depth 100
    }
    return $text
}
function Get-CimInstance {
    param([string]$ClassName,[string]$Filter)
    if($ClassName -eq 'Win32_PerfFormattedData_PerfOS_Memory'){
        $script:memoryCalls++
        $m=[pscustomobject]@{CommitLimit=[long]65732542464;CommittedBytes=[long]35000000000}
        switch($script:caseOptions.memory){
            'low' {$m.CommittedBytes=[long]42036641792}
            'missing_commit' {$m.PSObject.Properties.Remove('CommittedBytes')}
            'missing_limit' {$m.PSObject.Properties.Remove('CommitLimit')}
            'negative_commit' {$m.CommittedBytes=-1}
            'bool_commit' {$m.CommittedBytes=$false}
            'float_commit' {$m.CommittedBytes=35000000000.5}
            'commit_exceeds_limit' {$m.CommittedBytes=[long]66000000000}
            'final_low' {if($script:memoryCalls -ge 4){$m.CommittedBytes=[long]42036641792}}
        }
        return $m
    }
    if($Filter -eq "Name='python.exe'"){
        $script:pythonCalls++
        if($script:caseOptions.python -eq 'always' -or ($script:caseOptions.python -eq 'late' -and $script:pythonCalls -ge 2)){return [pscustomobject]@{Name='python.exe';ProcessId=777}}
        return
    }
    if($script:predecessorName -and $Filter -eq ('ProcessId='+$script:predecessorPid)){
        $script:predecessorCimCalls++
        if($script:caseOptions.predecessor -eq 'missing' -or ($script:caseOptions.predecessor -eq 'late_missing' -and $script:predecessorCimCalls -ge 2)){return}
        $creation=$script:predecessorTime.AddMilliseconds(-150)
        if($script:caseOptions.predecessor -eq 'reused'){$creation=$script:predecessorTime.AddMinutes(1)}
        $command='"C:\项目\.venvs\lgm-baselines\Scripts\python.exe" "'+(Join-Path $suiteRoot $script:predecessorDefinition[1])+'"'
        if($script:caseOptions.predecessor -eq 'wrong_command'){$command='python unrelated.py'}
        if($script:caseOptions.predecessor -eq 'old_primary'){$command=$command.Replace('continue_formal_matrix_path_compat_v1.py','continue_formal_matrix.py')}
        return [pscustomobject]@{Name='python.exe';ProcessId=$script:predecessorPid;CreationDate=$creation.DateTime;CommandLine=$command}
    }
    return
}
function Test-Path {
    param([string]$LiteralPath)
    if($script:caseOptions.independentStatus -and $LiteralPath.EndsWith('independent_comparison_status.json')){return $true}
    if($script:caseOptions.existingIntent -and $LiteralPath.EndsWith('_launch_intent.json')){return $true}
    return Microsoft.PowerShell.Management\Test-Path -LiteralPath $LiteralPath
}
function Start-Sleep {param([int]$Seconds) $script:actions.Add([ordered]@{kind='sleep';seconds=$Seconds})}
function Move-Item {param([string]$LiteralPath,[string]$Destination) $script:actions.Add([ordered]@{kind='move';source=$LiteralPath;target=$Destination})}
function Start-Process {
    param([string]$FilePath,[string]$ArgumentList,[string]$WorkingDirectory,[string]$WindowStyle,[string]$RedirectStandardOutput,[string]$RedirectStandardError,[switch]$PassThru)
    $script:actions.Add([ordered]@{kind='start';file=$FilePath;arguments=$ArgumentList;directory=$WorkingDirectory;window=$WindowStyle})
    return [pscustomobject]@{Id=990001}
}
foreach($name in @('Start-Process','Move-Item','Start-Sleep','Get-CimInstance','Get-Content','Test-Path')){if((Get-Command $name).CommandType -ne 'Function'){throw ('Mock missing: '+$name)}}
function Run-Case([string]$Name,[string]$Stage,[hashtable]$Options,[bool]$ExpectedPass,[switch]$Validation){
    $script:caseStage=$Stage;$script:caseOptions=$Options
    $script:actions=[Collections.Generic.List[object]]::new();$script:memoryCalls=0;$script:pythonCalls=0;$script:predecessorCimCalls=0;$script:stateHashCalls=0
    $script:predecessorName=@{pipeline='primary';extensions='pipeline';latest='extensions';independent='latest'}[$Stage]
    if($script:predecessorName){
        $script:predecessorDefinition=$script:definitions[$script:predecessorName]
        $o=Microsoft.PowerShell.Management\Get-Content -LiteralPath (Join-Path $suiteRoot $script:predecessorDefinition[0]) -Raw|ConvertFrom-Json
        $script:predecessorPid=$o.($script:predecessorDefinition[2])
        $stamp=if($o.supervisor_started_utc){$o.supervisor_started_utc}else{$o.started_utc}
        $script:predecessorTime=if($stamp -is [DateTime]){[DateTimeOffset]$stamp}else{[DateTimeOffset]::Parse($stamp)}
    }
    $passed=$false;$exception=$null
    try {& $mockBlock -Stage $Stage -ValidateOnly:$Validation | Out-Null;$passed=$true}catch{$exception=$_.Exception.Message}
    $moves=@($script:actions|Where-Object kind -eq 'move');$starts=@($script:actions|Where-Object kind -eq 'start')
    $ok=$passed -eq $ExpectedPass
    if(-not $ExpectedPass -and ($moves.Count -or $starts.Count)){$ok=$false}
    if($Validation -and ($moves.Count -or $starts.Count)){$ok=$false}
    if($ExpectedPass -and -not $Validation){
        if($starts.Count -ne 1 -or $starts[0].window -ne 'Hidden'){$ok=$false}
        if($Stage -eq 'independent'){
            if($moves.Count -ne 0 -or $starts[0].arguments -notlike '*--plan*independent_comparison_plan_v2.json*'){$ok=$false}
        }elseif($moves.Count -ne 1){$ok=$false}
        if ($Stage -in @('latest','independent') -and $starts[0].arguments -notlike '*path_compat_v1.py*--addendum-sha256 0c4217fefb33d6550bda2300bc201f1c869da0b8d5ff02d45ae7af45b7ef6d70*') {$ok=$false}
        if ($Stage -eq 'primary') {
            if ($starts[0].arguments -notlike '*continue_formal_matrix_path_compat_v1.py*--stage all --workers 8 --path-compat-sha256 11de17bd611431e4471eec1b8ac072a2159fbd02e4eb2cb041b4f3b0f00012a1*') {$ok=$false}
            if ($script:memoryCalls -ne 4 -or @($script:actions|Where-Object kind -eq 'sleep').Count -ne 2) {$ok=$false}
        }
        if (@($moves|Where-Object { $_.target -notlike '*path_registry_recovery_20260918_1239*' }).Count) {$ok=$false}
        $kinds=@($script:actions|Where-Object kind -ne 'sleep'|ForEach-Object kind)
        $expectedKinds=if($Stage -eq 'independent'){@('save','start','save')}else{@('save','move','start','save')}
        if(($kinds -join ',') -ne ($expectedKinds -join ',')){$ok=$false}
    }
    $script:results.Add([ordered]@{name=$Name;stage=$Stage;expectedPass=$ExpectedPass;scriptPassed=$passed;checkPassed=$ok;exception=$exception;actions=@($script:actions);memoryCalls=$script:memoryCalls;predecessorCimCalls=$script:predecessorCimCalls})
}
Run-Case 'primary_success_mock' primary @{} $true
Run-Case 'pipeline_success_mock' pipeline @{} $true
Run-Case 'extensions_success_mock' extensions @{} $true
Run-Case 'latest_success_mock' latest @{} $true
Run-Case 'independent_success_v2_no_state_move_mock' independent @{} $true
Run-Case 'primary_validate_only_mock' primary @{} $true -Validation
Run-Case 'memory_low' primary @{memory='low'} $false
Run-Case 'memory_missing_commit' primary @{memory='missing_commit'} $false
Run-Case 'memory_missing_limit' primary @{memory='missing_limit'} $false
Run-Case 'memory_negative_commit' primary @{memory='negative_commit'} $false
Run-Case 'memory_boolean_commit' primary @{memory='bool_commit'} $false
Run-Case 'memory_fractional_commit' primary @{memory='float_commit'} $false
Run-Case 'memory_commit_exceeds_limit' primary @{memory='commit_exceeds_limit'} $false
Run-Case 'memory_drops_at_final_check' primary @{memory='final_low'} $false
Run-Case 'python_already_present' primary @{python='always'} $false
Run-Case 'python_appears_before_launch' primary @{python='late'} $false
Run-Case 'checkpoint_report_empty' primary @{proof='empty'} $false
Run-Case 'checkpoint_report_duplicate' primary @{proof='duplicate'} $false
Run-Case 'checkpoint_report_wrong_epoch' primary @{proof='wrong_epoch'} $false
Run-Case 'checkpoint_report_wrong_config' primary @{proof='wrong_config'} $false
Run-Case 'checkpoint_report_missing_cuda' primary @{proof='missing_cuda'} $false
Run-Case 'predecessor_missing' pipeline @{predecessor='missing'} $false
Run-Case 'predecessor_pid_reused' pipeline @{predecessor='reused'} $false
Run-Case 'predecessor_wrong_command' pipeline @{predecessor='wrong_command'} $false
Run-Case 'predecessor_exits_before_launch' pipeline @{predecessor='late_missing'} $false
Run-Case 'pending_job_has_exit_code_zero' pipeline @{jobExit=$true} $false
Run-Case 'pending_job_has_started_time' pipeline @{jobStarted=$true} $false
Run-Case 'pending_job_has_finished_time' pipeline @{jobFinished=$true} $false
Run-Case 'pending_job_list_missing' pipeline @{emptyJobs=$true} $false
Run-Case 'pending_job_pid_zero_nonnull' pipeline @{zeroPid=$true} $false
Run-Case 'pending_job_duplicate_id' pipeline @{duplicateJob=$true} $false
Run-Case 'independent_status_already_exists' independent @{independentStatus=$true} $false
Run-Case 'launch_intent_already_exists' primary @{existingIntent=$true} $false
Run-Case 'old_state_changes_during_preflight' primary @{lateStateDrift=$true} $false
Run-Case 'frozen_core_hash_drift' primary @{badHash='formal_retrieval.py'} $false
Run-Case 'v2_plan_hash_drift' independent @{badHash='independent_comparison_plan_v2.json'} $false

Run-Case 'addendum_manifest_changed' latest @{badHash='EXECUTION_ADDENDUM.json'} $false
Run-Case 'addendum_registration_changed' independent @{badHash='REGISTRATION.json'} $false
Run-Case 'compatibility_common_source_changed' latest @{badHash='compatibility.py'} $false
Run-Case 'compatibility_parent_source_changed' independent @{badHash='supervise_independent_comparisons_path_compat_v1.py'} $false
Run-Case 'new_latest_parent_wrong_command' independent @{predecessor='wrong_command'} $false
Run-Case 'latest_validate_only_mock' latest @{} $true -Validation
Run-Case 'independent_validate_only_mock' independent @{} $true -Validation

Run-Case 'primary_manifest_changed' primary @{badHash='primary_path_repair_20260918/SOURCE_MANIFEST.json'} $false
Run-Case 'primary_worker_source_changed' primary @{badHash='run_formal_worker.py'} $false
Run-Case 'primary_parent_source_changed' primary @{badHash='continue_formal_matrix_path_compat_v1.py'} $false
Run-Case 'primary_scope_helper_changed' primary @{badHash='project_paths.py'} $false
Run-Case 'sep18_preservation_manifest_changed' primary @{badHash='PRESERVED_INCIDENT.json'} $false
Run-Case 'sep18_preserved_launch_changed' primary @{badHash='previous_attempt\primary_launch_intent.json'} $false
Run-Case 'sep18_preserved_state_changed' primary @{badHash='controllers\status.json'} $false
Run-Case 'checkpoint_must_reference_original_archive' primary @{proof='wrong_archive'} $false
Run-Case 'pipeline_rejects_original_primary_identity' pipeline @{predecessor='old_primary'} $false

$out=[ordered]@{schema='independent-primary-path-recovery-control-mock.v1';time=(Get-Date).ToString('o');target=$targetScript;target_sha256=$sourceHash;parse_errors=@($parseErrors);mocked_function_names=@('Sha','Save-NewJson','Get-CimInstance','Start-Process','Move-Item','Start-Sleep','Get-Content','Test-Path');environment_assignment_omitted=$envAssignment.Count;real_scientific_imports=0;real_process_starts=0;real_state_moves=0;scope='Actual target script except source hashing/output-write routines replaced with memory mocks; all process/move/sleep/system probes mocked. Read-only source hashing and input file reads remain real. No branch here is a live launch.';count=$script:results.Count;passed=@($script:results|Where-Object checkPassed).Count;failed=@($script:results|Where-Object {-not $_.checkPassed}).Count;checks=@($script:results)}
$reviewPath=Join-Path $suiteIncident ('STARTUP_SCRIPT_MOCK_'+$sourceHash.Substring(0,12)+'_'+(Get-Date -Format 'HHmmssfff')+'.json')
[IO.File]::WriteAllText($reviewPath,($out|ConvertTo-Json -Depth 30),[Text.UTF8Encoding]::new($false))
[pscustomobject]@{path=$reviewPath;source_hash=$sourceHash;count=$out.count;passed=$out.passed;failed=$out.failed;failures=@($script:results|Where-Object {-not $_.checkPassed}|Select-Object name,exception,scriptPassed)}|ConvertTo-Json -Depth 5
