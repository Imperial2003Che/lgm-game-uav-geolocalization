$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$e=Split-Path -Parent $PSScriptRoot
function Bound([string]$p,[string]$expected=''){$i=Get-Item -LiteralPath $p;$h=(Get-FileHash -LiteralPath $p).Hash.ToLower();if($expected -and $h -cne $expected){throw 'Binding changed'};[ordered]@{path=$p;sha256=$h;bytes=$i.Length}}
function J([string]$p){Get-Content -LiteralPath $p -Raw|ConvertFrom-Json -DateKind String}
$old=Bound (Join-Path $e 'robustness_observation_20260929_0647\snapshot_20260929_114610672\OBSERVATION.json') '46026c45b710dbdb48c5c3754f73f3a7555844254d48b9bf8b502dc083872a87'
$new=Bound (Join-Path $e 'robustness_observation_20260929_0647\snapshot_20260929_124603856\OBSERVATION.json') '5d0667518c128d8ec26b97ad5de980c30743451c3c6e262d1bf75317c2730aa1'
$prev=J $old.path;$current=J $new.path
$ledgerBind=Bound (Join-Path (Split-Path -Parent $new.path) 'frozen_robustness_matrix_ledger.json') '76b4f64ff91c512225584cf128294fa76a1b96b4003186ca8eee0a74d1736115'
$ledger=J $ledgerBind.path;$record=$ledger.runs.'university1652/full/seed_1'
if($record.status -ne 'completed_and_verified' -or $record.attempts.Count -ne 1 -or $record.attempts[0].returncode -ne 0 -or $prev.robustness.id -ne 'university1652/full/seed_1' -or $current.robustness.id -ne 'sues200/visual/seed_1'){throw 'Unexpected transition scope'}
if(($prev.robustness.command|ConvertTo-Json -Compress) -cne ($record.attempts[0].command|ConvertTo-Json -Compress)){throw 'Old command mismatch'}
$logs=@(foreach($b in @($record.attempts[0].stdout,$record.attempts[0].stderr)){$actual=Bound $b.path $b.sha256;if($actual.bytes -ne $b.bytes){throw 'Closed log size mismatch'};$actual})
$all=@(Get-CimInstance Win32_Process)
$oldPresence=@($all|Where-Object ProcessId -in @(40820,43872)|ForEach-Object{[ordered]@{pid=$_.ProcessId;parent=$_.ParentProcessId;creation_utc_ticks=$_.CreationDate.ToUniversalTime().Ticks;command=$_.CommandLine}})
foreach($p in $current.robustness.worker_pair){$n=@($all|Where-Object ProcessId -eq $p.pid);if($n.Count -ne 1 -or $n[0].CreationDate.ToUniversalTime().Ticks -ne [long]$p.creation_utc_ticks -or $n[0].ParentProcessId -ne $p.parent -or $n[0].CommandLine -cne $p.command){throw 'Current worker naturally changed; reread actual state'}}
$r=[ordered]@{schema='lgm.readonly.worker-transition.v1';time=(Get-Date).ToString('o');source=(Bound $PSCommandPath);old_identity_snapshot=$old;new_identity_snapshot=$new;ledger_snapshot=$ledgerBind;old_pair=$prev.robustness.worker_pair;old_pid_current_presence=$oldPresence;completed_record=$record;closed_log_bindings=$logs;current_worker_pair=$current.robustness.worker_pair;limits=@('Original stage subprocess.run returncode0 plus old PID presence/absence observation; not independent dual-handle interpreter exit evidence.','This transition alone does not accept scientific robustness results.','No checkpoint/cache/image bytes or scientific modules read; no live state modified.')}
$out=Join-Path $PSScriptRoot 'ROOT_FULL_TRANSITION.json';$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($r|ConvertTo-Json -Depth 25));$f=[IO.File]::Open($out,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read);try{$f.Write($bytes,0,$bytes.Length)}finally{$f.Dispose()}
Bound $out|ConvertTo-Json
