$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$e=Split-Path -Parent $PSScriptRoot
function Bound([string]$p,[string]$expected=''){$i=Get-Item -LiteralPath $p;$h=(Get-FileHash -LiteralPath $p).Hash.ToLower();if($expected -and $h -cne $expected){throw 'Binding changed'};[ordered]@{path=$p;sha256=$h;bytes=$i.Length}}
function J([string]$p){Get-Content -LiteralPath $p -Raw|ConvertFrom-Json -DateKind String}
$old=Bound (Join-Path $e 'robustness_observation_20260929_0647\snapshot_20260929_130251128\OBSERVATION.json') 'a1fccfc9fcfed4168e9ca4b0f8ef749c50098b766a6eaef55898b106a45b9dd6'
$new=Bound (Join-Path $e 'robustness_observation_20260929_0647\snapshot_20260929_135047460\OBSERVATION.json') 'e5c4d484bdb7e703b373863b60fb02cdd3f372bf307559f0d00df96a5bc9d950'
$prev=J $old.path;$current=J $new.path
$ledgerBind=Bound (Join-Path (Split-Path -Parent $new.path) 'frozen_robustness_matrix_ledger.json') '222ef32f96e6327d6efe0a33f1125d7d27f50d5db379a52995bf88273dc35060'
$ledger=J $ledgerBind.path;$record=$ledger.runs.'sues200/visual/seed_1'
if($record.status -ne 'completed_and_verified' -or $record.attempts.Count -ne 1 -or $record.attempts[0].returncode -ne 0 -or $prev.robustness.id -ne 'sues200/visual/seed_1' -or $current.robustness.id -ne 'sues200/full/seed_1'){throw 'Unexpected transition scope'}
if(($prev.robustness.command|ConvertTo-Json -Compress) -cne ($record.attempts[0].command|ConvertTo-Json -Compress)){throw 'Old command mismatch'}
$logs=@(foreach($b in @($record.attempts[0].stdout,$record.attempts[0].stderr)){$actual=Bound $b.path $b.sha256;if($actual.bytes -ne $b.bytes){throw 'Closed log size mismatch'};$actual})
$all=@(Get-CimInstance Win32_Process)
$oldPresence=@($all|Where-Object ProcessId -in @(24428,40060)|ForEach-Object{[ordered]@{pid=$_.ProcessId;parent=$_.ParentProcessId;creation_utc_ticks=$_.CreationDate.ToUniversalTime().Ticks;command=$_.CommandLine}})
foreach($p in $current.robustness.worker_pair){$n=@($all|Where-Object ProcessId -eq $p.pid);if($n.Count -ne 1 -or $n[0].CreationDate.ToUniversalTime().Ticks -ne [long]$p.creation_utc_ticks -or $n[0].ParentProcessId -ne $p.parent -or $n[0].CommandLine -cne $p.command){throw 'Current worker naturally changed; reread actual state'}}
$r=[ordered]@{schema='lgm.readonly.worker-transition.v1';time=(Get-Date).ToString('o');source=(Bound $PSCommandPath);old_identity_snapshot=$old;new_identity_snapshot=$new;ledger_snapshot=$ledgerBind;old_pair=$prev.robustness.worker_pair;old_pid_current_presence=$oldPresence;completed_record=$record;closed_log_bindings=$logs;current_worker_pair=$current.robustness.worker_pair;limits=@('Original stage subprocess.run returncode0 plus old PID presence/absence observation; not independent dual-handle interpreter exit evidence.','This transition alone does not accept scientific robustness results.','No checkpoint/cache/image bytes or scientific modules read; no live state modified.')}
$out=Join-Path $PSScriptRoot 'ROOT_SUES_VISUAL_TRANSITION.json';$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($r|ConvertTo-Json -Depth 25));$f=[IO.File]::Open($out,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read);try{$f.Write($bytes,0,$bytes.Length)}finally{$f.Dispose()}
Bound $out|ConvertTo-Json
