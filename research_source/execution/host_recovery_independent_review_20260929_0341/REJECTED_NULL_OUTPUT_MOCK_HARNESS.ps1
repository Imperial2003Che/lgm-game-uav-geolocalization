$ErrorActionPreference='Stop'
$ex='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$candidate=Join-Path $ex 'restart_after_host_interruption_20260929_v1.ps1'
$expectedSha='59deea56a6df6ee59282aa50d2612246a0b3e2cb8b9335120af8907f778fdd64'
function Sha($p) {(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLower()}
function Bind($p) {[ordered]@{path=$p;bytes=(Get-Item -LiteralPath $p).Length;sha256=(Sha $p)}}
if((Sha $candidate)-ne $expectedSha){throw 'Candidate changed'}
$tokens=$null;$errors=$null;$ast=[System.Management.Automation.Language.Parser]::ParseFile($candidate,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Candidate parse failed'}
$extractNames=@('Exact-Time','Assert-HostInterruption')
$definitions=@()
foreach($name in $extractNames){
 $n=@($ast.FindAll({param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst]},$false)|Where-Object Name -eq $name)
 if($n.Count-ne 1){throw ('Expected one function '+$name)}
 $definitions+=$n[0].Extent.Text
}
# Execute only these two exact function definitions; the candidate top-level is never run.
. ([scriptblock]::Create(($definitions -join "`n")))
$baseCap=Get-Content -LiteralPath (Join-Path $ex 'host_interruption_20260929_0341\CAPTURE.json') -Raw
$baseIdentity=Get-Content -LiteralPath (Join-Path $ex 'host_interruption_20260929_0341\previous_identity\OWNER_SNAPSHOT_20260928_144022952.json') -Raw
function Reset-Case {
 $script:capture=$baseCap|ConvertFrom-Json -DateKind String
 $script:oldIdentity=$baseIdentity|ConvertFrom-Json -DateKind String
 $script:oldProcessRows=@();foreach($r in $script:oldIdentity.states){$script:oldProcessRows+=@($r.owner,$r.launcher)}
 $script:oldIds=@(16412,16636,30324,10876,29432,18296,21636,32572,26072,2820)
 $script:mockOs=@([pscustomobject]@{LastBootUpTime=[DateTimeOffset]::Parse($script:capture.last_boot_utc)})
 $script:mockRows=@{}
}
function Get-CimInstance([string]$ClassName,[string]$Filter) {
 if($ClassName-eq 'Win32_OperatingSystem'){return $script:mockOs}
 if($ClassName-eq 'Win32_Process' -and $Filter-match '^ProcessId=(\d+)$'){
  return $script:mockRows[[int]$Matches[1]]
 }
 throw ('Forbidden mocked CIM request '+$ClassName+'/'+$Filter)
}
function Process($id,$when,$command='python test') {[pscustomobject]@{ProcessId=$id;CreationDate=[DateTimeOffset]::Parse($when);CommandLine=$command}}
$results=@()
function Check($name,$reject,[scriptblock]$setup,[scriptblock]$after={param($r)}){
 Reset-Case
 & $setup
 $caught=$null;$result=$null
 try{$result=Assert-HostInterruption}catch{$caught=$_.Exception.Message}
 $actualRejected=$null-ne $caught
 if($actualRejected-ne $reject){throw ('Case '+$name+' expected reject='+$reject+' got '+$caught)}
 if(-not $reject){& $after $result}
 $script:results+=[ordered]@{name=$name;expected_rejected=$reject;actual_rejected=$actualRejected;message=$caught;passed=$true}
}
Check 'sealed incident clean; ten actual historical identities' $false {} {param($r) if($r.observations.Count-ne 10-or $r.old_exit_codes-ne 'unknown_not_observed'-or $r.interrupted_evaluation.prior_creation_and_interpreter-ne 'not_observed'){throw 'Guard fabricated identity/exit'} }
Check 'changed actual boot rejected' $true {$script:mockOs[0].LastBootUpTime=$script:mockOs[0].LastBootUpTime.AddSeconds(1)}
Check 'missing OS boot rejected' $true {$script:mockOs=@()}
Check 'ambiguous OS boot rejected' $true {$script:mockOs=@($script:mockOs[0],$script:mockOs[0])}
Check 'capture observation before boot rejected' $true {$script:capture.time='2026-09-28T20:00:00Z'}
Check 'historical owner snapshot after boot rejected' $true {$script:oldIdentity.time='2026-09-28T22:00:00Z'}
Check 'parent recorded interrupted evaluation start after boot rejected' $true {$script:capture.active.started_utc='2026-09-28T22:00:00Z'}
Check 'historical 100ns tick discrepancy rejected' $true {$script:oldProcessRows[0].creation_utc_ticks=[long]$script:oldProcessRows[0].creation_utc_ticks+1}
Check 'historical identity PID outside exact set rejected' $true {$script:oldProcessRows[0].pid=12345}
Check 'same old controller creation still present rejected' $true {$p=$script:oldProcessRows[0];$script:mockRows[$p.pid]=Process $p.pid $p.creation $p.command}
Check 'old controller numeric PID reused after boot is not old exit proof' $false {$p=$script:oldProcessRows[0];$script:mockRows[$p.pid]=Process $p.pid '2026-09-29T02:00:00Z'} {param($r) if($r.observations[0].current_pid_observation.identity-ne 'different_creation_after_boot'){throw 'Reuse identity not distinguished'} }
Check 'old controller numeric PID reused before boot rejected' $true {$p=$script:oldProcessRows[0];$script:mockRows[$p.pid]=Process $p.pid '2026-09-28T20:00:00Z'}
Check 'old controller reuse missing full command rejected' $true {$p=$script:oldProcessRows[0];$script:mockRows[$p.pid]=Process $p.pid '2026-09-29T02:00:00Z' ''}
Check 'ambiguous old controller observation rejected' $true {$p=$script:oldProcessRows[0];$r=Process $p.pid '2026-09-29T02:00:00Z';$script:mockRows[$p.pid]=@($r,$r)}
Check 'interrupted evaluator unknown prior creation; postboot PID recorded separately' $false {$script:mockRows[22496]=Process 22496 '2026-09-29T02:00:00Z'} {param($r) if($r.interrupted_evaluation.exit_code-ne 'unknown'-or $r.interrupted_evaluation.current_pid_observation.identity-ne 'post_boot_pid_observation_not_old_exit_proof'){throw 'Science reuse fabricated exit'} }
Check 'interrupted evaluator PID observation before boot rejected' $true {$script:mockRows[22496]=Process 22496 '2026-09-28T20:00:00Z'}
Check 'interrupted evaluator PID missing full command rejected' $true {$script:mockRows[22496]=Process 22496 '2026-09-29T02:00:00Z' ''}
Check 'ambiguous interrupted evaluator PID observation rejected' $true {$r=Process 22496 '2026-09-29T02:00:00Z';$script:mockRows[22496]=@($r,$r)}
if((Sha $candidate)-ne $expectedSha){throw 'Candidate changed while tested'}
$report=[ordered]@{schema='independent-sep29-host-guard-controls.v1';time=(Get-Date).ToString('o');passed=$true;candidate=(Bind $candidate);script=(Bind $PSCommandPath);checks=$results;count=$results.Count;extracted_function_names=$extractNames;execution_scope='PowerShell AST extraction of two exact functions only; all CIM mocked; candidate top-level, recovery, ValidateOnly, science, state move and launch never executed';limitations='Controls verify the new host identity/time branch. Static source and evidence review is recorded separately.'}
$out=Join-Path $PSScriptRoot ('GUARD_CONTROLS_'+$expectedSha.Substring(0,12)+'_'+(Get-Date -Format 'HHmmssfff')+'.json')
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($report|ConvertTo-Json -Depth 10));$fs=[IO.File]::Open($out,[IO.FileMode]::CreateNew);try{$fs.Write($bytes,0,$bytes.Length)}finally{$fs.Dispose()}
Bind $out|ConvertTo-Json
