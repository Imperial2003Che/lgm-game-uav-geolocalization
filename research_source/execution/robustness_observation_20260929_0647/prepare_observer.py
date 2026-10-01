"""Create a new observer and its complete diff without editing the prior source."""
import difflib
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "pipeline_observation_20260929_0548/observe_pipeline_phase_v2.ps1"
raw = BASE.read_bytes()
assert hashlib.sha256(raw).hexdigest() == "2962be0d134a5c1b516a33bbf5357ba64e53c54a0b637728bbae1966cd313dae"
old = raw.decode("utf-8")
new = old.replace(
    " $t3Path='C:\\项目\\LGM-GAME-Partner-Delivery-20260724\\lgm_game_pytorch\\evaluations\\transactions_t3_transfer\\transactions_t3_ledger.json'\n $t3=CaptureJson $t3Path 'transactions_t3_ledger.json'",
    r""" $ledgerPath='C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\runs\frozen_robustness_matrix_ledger.json'
 $ledger=CaptureJson $ledgerPath 'frozen_robustness_matrix_ledger.json'
 $helper=Join-Path $PSScriptRoot 'check_robustness_contract.py'
 $helperBinding=Bind $helper
 $contractText=& 'C:\Users\17703\AppData\Local\Programs\Python\Python311\python.exe' -I -B $helper (Join-Path $dest 'frozen_robustness_matrix_ledger.json')
 if($LASTEXITCODE -ne 0){throw 'Read-only stdlib contract helper rejected snapshot'}
 $contract=$contractText|ConvertFrom-Json -DateKind String
 if($contract.passed -ne $true){throw 'Robustness metadata contract failed'}
 $contractPath=Seal 'CONTRACT.json' ($contract|ConvertTo-Json -Depth 20)"""
)
start = new.index(" $running=@($t3.evaluations")
end = new.index(" $pins=@(", start)
new = new[:start] + r""" $expectedStage=@('C:\项目\.venvs\lgm-baselines\Scripts\python.exe','C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\experiments\run_frozen_robustness_matrix.py','--delivery-root','C:\项目\LGM-GAME-Partner-Delivery-20260724','--university-root','C:\项目\IMTMN\datasets\University-1652','--sues-root','C:\项目\IMTMN\datasets\SUES-200','--python','C:\项目\.venvs\lgm-baselines\Scripts\python.exe','--stage','run')
 if(-not(Same @($active[0].command) $expectedStage)){throw 'Original robustness stage command mismatch'}
 if($entryBinding.sha256 -ne $ledger.immutable_config.source_hashes.orchestrator){throw 'Stage/ledger source mismatch'}
 $priorT3=@($pipe.jobs|Where-Object id -eq 'cross_dataset_transfer')
 if($priorT3.Count -ne 1 -or $priorT3[0].status -ne 'completed' -or $priorT3[0].exit_code -ne 0){throw 'T3 parent completion record unavailable'}
 $running=@($ledger.runs.PSObject.Properties|Where-Object {$_.Value.status -eq 'running'})
 if($running.Count -ne 1){throw 'Robustness between jobs or changed; retain partial snapshot and inspect again'}
 $taskId=$running[0].Name;$task=$running[0].Value
 $registry=@($ledger.immutable_config.registered_runs|Where-Object identifier -CEQ $taskId)
 if($registry.Count -ne 1){throw 'Expected unique registered robustness task'}
 $spec=$registry[0]
 if($taskId -cne ($spec.dataset+'/'+$spec.variant+'/seed_'+$spec.seed)){throw 'Robustness identifier mismatch'}
 $attempts=@($task.attempts)
 if($attempts.Count -lt 1){throw 'Running robustness record has no attempt'}
 for($i=0;$i -lt $attempts.Count;$i++){
  $names=@($attempts[$i].PSObject.Properties.Name)
  if($i -eq $attempts.Count-1){
   if('completed_utc' -in $names -or 'returncode' -in $names){throw 'Current robustness attempt already closed; resample'}
  }elseif('completed_utc' -notin $names -or 'returncode' -notin $names){throw 'Prior robustness attempt not closed'}
 }
 $event=$attempts[-1]
 if(-not(Same @($event.command) @($spec.command))){throw 'Attempt differs from original registered command'}
 if($event.evaluator_sha256 -ne $ledger.immutable_config.source_hashes.evaluator){throw 'Attempt evaluator SHA mismatch'}
 if($task.checkpoint_status -ne 'completed_and_verified' -or @($task.checkpoint_issues).Count){throw 'Producer checkpoint readiness is not ready'}
 foreach($arg in @(@('--dataset',[string]$spec.dataset),@('--data-root',[string]$spec.data_root),@('--evidence',[string]$spec.evidence),@('--checkpoint',[string]$spec.checkpoint),@('--output-dir',[string]$spec.output_dir),@('--sues-manifest',[string]$ledger.immutable_config.sues_manifest.path))){
  $indices=@(for($j=0;$j -lt $event.command.Count;$j++){if($event.command[$j] -ceq $arg[0]){$j}})
  if($indices.Count -ne 1 -or $indices[0]+1 -ge $event.command.Count -or $event.command[$indices[0]+1] -cne $arg[1]){throw 'Robustness registered row-to-command mismatch'}
 }
 $child=@($all|Where-Object {$_.ParentProcessId -eq $stagePair[1].pid -and $_.Name -eq 'python.exe'})
 if($child.Count -ne 1){throw 'Robustness worker transition or missing child; inspect fresh observation'}
 $workerPair=Pair $child[0] $stagePair[1].pid $event.command
 if([long]$workerPair[0].creation_utc_ticks -lt ([DateTimeOffset]::Parse($event.started_utc)).UtcTicks -or [long]$workerPair[1].creation_utc_ticks -lt [long]$workerPair[0].creation_utc_ticks){throw 'Worker creation predates ledger attempt or parent'}
 if([long]$stagePair[0].creation_utc_ticks -lt ([DateTimeOffset]::Parse($active[0].started_utc)).UtcTicks -or [long]$stagePair[1].creation_utc_ticks -lt [long]$stagePair[0].creation_utc_ticks){throw 'Stage creation predates parent launch record'}
 $dataloaders=@($all|Where-Object {$_.ParentProcessId -eq $workerPair[1].pid -and $_.Name -eq 'python.exe'}|ForEach-Object{Proc $_})
 $wrapperLogDir=Join-Path (Split-Path -Parent $ledgerPath) 'frozen_robustness_orchestrator_logs'
 $logStem=$taskId.Replace('/','__')
 $scienceStdout=LogMeta (Join-Path $wrapperLogDir ($logStem+'.stdout.log'))
 $scienceStderr=LogMeta (Join-Path $wrapperLogDir ($logStem+'.stderr.log'))
 # A second read must describe the same still-active attempt; natural transition is not a science failure.
 $endPipe=CaptureJson (Join-Path $e 'pipeline_status.json') 'pipeline_status_after.json'
 $endLedger=CaptureJson $ledgerPath 'frozen_robustness_matrix_ledger_after.json'
 $endActive=@($endPipe.jobs|Where-Object status -eq 'running')
 $endRunning=@($endLedger.runs.PSObject.Properties|Where-Object {$_.Value.status -eq 'running'})
 if($endActive.Count -ne 1 -or $endActive[0].id -ne 'robustness' -or $endActive[0].pid -ne $active[0].pid -or -not(Same @($endActive[0].command) @($active[0].command))){throw 'Pipeline changed during observation; resample'}
 if($endRunning.Count -ne 1 -or $endRunning[0].Name -cne $taskId -or $endLedger.config_sha256 -ne $ledger.config_sha256){throw 'Robustness task changed during observation; resample'}
 $endAttempt=@($endRunning[0].Value.attempts)[-1]
 if($endAttempt.started_utc -cne $event.started_utc -or -not(Same @($endAttempt.command) @($event.command)) -or 'completed_utc' -in @($endAttempt.PSObject.Properties.Name) -or 'returncode' -in @($endAttempt.PSObject.Properties.Name)){throw 'Robustness attempt changed or completed during observation; resample'}
 $finalCim=@(Get-CimInstance Win32_Process)
 $expectedLive=@($rows|ForEach-Object{$_.owner;$_.launcher})+@($stagePair)+@($workerPair)
 foreach($observed in $expectedLive){
  $again=@($finalCim|Where-Object ProcessId -eq $observed.pid)
  if($again.Count -ne 1 -or ([DateTimeOffset]$again[0].CreationDate).UtcTicks -ne [long]$observed.creation_utc_ticks -or $again[0].CommandLine -cne $observed.command -or $again[0].ParentProcessId -ne $observed.parent){throw 'Process identity changed during observation; retain and resample'}
 }
 $finalCimTime=(Get-Date).ToString('o')
""" + new[end:]
new = new.replace("$active[0].id -ne 'cross_dataset_transfer'", "$active[0].id -ne 'robustness'")
new = new.replace("schema='lgm-post-primary-pipeline-observation.v1'", "schema='lgm-post-primary-robustness-observation.v1'")
new = new.replace("cim_observed_at=$cimTime;", "cim_observed_at=$cimTime;cim_reconfirmed_at=$finalCimTime;identity_count=$expectedLive.Count;contract_helper=$helperBinding;contract_report=(Bind $contractPath);")
start = new.index("transfer=[ordered]@{")
end = new.index(";\n completed_pipeline_jobs", start)
new = new[:start] + """robustness=[ordered]@{id=$taskId;status=$task.status;attempt_ordinal_derived_from_array_length=$attempts.Count;attempt_started_utc=$event.started_utc;command=$event.command;evaluator_sha256=$event.evaluator_sha256;config_sha256=$ledger.config_sha256;ledger_updated_utc=$ledger.updated_utc;worker_pair=$workerPair;dataloader_children=$dataloaders;ledger_status_counts=@($ledger.runs.PSObject.Properties|Group-Object {$_.Value.status}|Select-Object Name,Count);counts_are_runtime_status_not_independent_acceptance=$true;checkpoint_status_is_producer_record_only=$true;stdout=$scienceStdout;stderr=$scienceStderr};
 t3_parent_completion=[ordered]@{record=$priorT3[0];numeric_pid_current_presence=@($finalCim|Where-Object ProcessId -eq $priorT3[0].pid|ForEach-Object{Proc $_});limit='Original parent Popen exit record only; no independent interpreter exit code or held handles'}""" + new[end:]
new = new.replace("transfer_id=$running[0].Name", "robustness_id=$taskId")
new = new.replace("'Read-only phase and process observation; no experiment launch or recovery replay'", "'Read-only phase and process observation; only an isolated stdlib metadata helper is executed, no science/native worker or recovery launch','Cache/checkpoint SHA and readiness are inherited producer metadata, no bytes read or scientific completion independently accepted','Wrapper logs may be open; size/time/tail are observation only, not a whole-file digest'")
assert "$t3" not in new and "transfer=[ordered]" not in new
out = HERE / "observe_robustness_phase.ps1"
with out.open("x", encoding="utf-8", newline="") as handle:
    handle.write(new)
diff = "".join(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True), fromfile=str(BASE), tofile=str(out)))
with (HERE / "SOURCE_DIFF.patch").open("x", encoding="utf-8", newline="") as handle:
    handle.write(diff)
print(hashlib.sha256(out.read_bytes()).hexdigest())
