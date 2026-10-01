$ErrorActionPreference='Stop'
$d=$PSScriptRoot
$checks=[Collections.Generic.List[object]]::new()
function Bind([string]$p){$i=Get-Item -LiteralPath $p;[ordered]@{path=$i.FullName;sha256=(Get-FileHash -LiteralPath $p).Hash.ToLower();bytes=$i.Length}}
function Check($b){$a=Bind $b.path;if($a.sha256 -ne $b.sha256 -or $a.bytes -ne $b.bytes){throw "Binding mismatch: $($b.path)"};$checks.Add($a)}
$prepPath=Join-Path $d 'PREPARATION_AND_OBSERVATION_REPORT.json'
if((Bind $prepPath).sha256 -ne 'ff7358fc2e81bf6312af698bac0d8eb8b7c5ff6648dc646c27d7ebfa5106646a'){throw 'Preparation report pin'}
$prep=Get-Content -LiteralPath $prepPath -Raw|ConvertFrom-Json -DateKind String
foreach($key in @('base','source','stdlib_helper','builder','full_diff','observation','contract')){Check $prep.$key}
$obs=Get-Content -LiteralPath $prep.observation.path -Raw|ConvertFrom-Json -DateKind String
foreach($b in $obs.raw_snapshots){Check $b.snapshot}
foreach($b in $obs.pins){Check $b}
Check $obs.first_identity;Check $obs.stage_entrypoint
$contract=Get-Content -LiteralPath $prep.contract.path -Raw|ConvertFrom-Json -DateKind String
Check $contract.ledger_snapshot
foreach($b in $contract.source_bindings){Check $b}
if($obs.identity_count -ne 12 -or $obs.primary.exit_code -ne $null -or $obs.robustness.id -ne 'university1652/visual/seed_1'){throw 'Observation scope mismatch'}
$live=@($obs.live_roles|ForEach-Object {$_.owner;$_.launcher})+@($obs.stage_pair)+@($obs.robustness.worker_pair)
$processes=@(Get-CimInstance Win32_Process)
foreach($p in $live){
 $n=@($processes|Where-Object ProcessId -eq $p.pid)
 if($n.Count -ne 1 -or $n[0].CreationDate.ToUniversalTime().Ticks -ne [long]$p.creation_utc_ticks -or $n[0].CommandLine -cne $p.command -or $n[0].ParentProcessId -ne $p.parent){throw 'Identity changed; inspect fresh phase without recovery replay'}
}
$now=(Get-Date).ToString('o')
$report=[ordered]@{status='root_adopted_readonly_robustness_phase_observer';time=$now;source=(Bind $PSCommandPath);preparation=(Bind $prepPath);observation=$prep.observation;file_checks=$checks.Count;bindings=@($checks);actual_identity_count=$live.Count;actual_identities=$live;reviewed='Root read prior complete v2, complete derived diff and isolated standard-library helper, then checked all source/raw bindings and actual current 12 identities';no_scientific_acceptance=$true;limits=@('Agent prepared and executed observer; root source review and actual identity corroboration only','T3 parent Popen return code is not an independently captured interpreter exit code','Primary own original exit code remains unknown','No scientific checkpoint/cache/image bytes or science imports; no recovery/ValidateOnly or live mutations')}
$out=Join-Path $d 'ROOT_OBSERVER_ADOPTION.json';$data=[Text.UTF8Encoding]::new($false).GetBytes(($report|ConvertTo-Json -Depth 20));$f=[IO.File]::Open($out,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write);try{$f.Write($data,0,$data.Length)}finally{$f.Dispose()}
Bind $out|ConvertTo-Json
