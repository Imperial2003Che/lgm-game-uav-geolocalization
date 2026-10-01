$ErrorActionPreference='Stop'
$auditDir=$PSScriptRoot
$execRoot=Split-Path -Parent $auditDir
$reportPath=Join-Path $auditDir 'SUES_EMBED_DIM_1024_SEED1_COMPLETION.json'
$outPath=Join-Path $auditDir 'ROOT_FIT_42_ADOPTION_20260928.json'
if(Test-Path -LiteralPath $outPath){throw 'Do not overwrite acceptance'}
function RecordFile([string]$path){
  $item=Get-Item -LiteralPath $path
  [pscustomobject]@{path=$path;bytes=$item.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
}
function VerifyRecord($record){
  $path=if($record.snapshot){$record.snapshot}else{$record.path}
  $actual=RecordFile $path
  if($actual.bytes -ne $record.bytes -or $actual.sha256 -ne $record.sha256){throw "Changed binding: $path"}
  $actual
}
$reportRecord=RecordFile $reportPath
if($reportRecord.sha256 -ne '5136b0acd9cc7bcc67d6d49a41fff5476b40d2f647c0b0239a95bed691d84475'){throw 'Wrong independent report'}
$r=Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
if(-not $r.batch_passed -or $r.new_fits_fully_artifact_verified -ne 1 -or $r.accepted_total_with_this_bounded_batch -ne 42 -or -not $r.evaluation_manifest_count_is_observation_only_not_acceptance -or $r.evaluations_accepted_by_this_train_audit -ne 0){throw 'Wrong completion boundary'}
if(@($r.scientific_modules).Count -ne 0 -or @($r.completed_outside_this_bounded_batch_pending_root_review).Count -ne 0){throw 'Unexpected scope'}
$run=$r.new_runs[0]
if($run.run_identifier -ne 'formal_sensitivity/sues200/full/seed_1/resnet18/dim_1024' -or @($run.original_training_completion_issues).Count -ne 0){throw 'Wrong target'}
$bindings=@($r.review_script,$r.derived_from_script,$r.root_owner_reference,$r.accepted_baseline_report)+@($r.accepted_baseline_independent_reports)+@($r.frozen_sources.PSObject.Properties.Value)+@($r.parent_status_raw_snapshot,$r.ledger_raw_snapshot,$run.manifest_raw_snapshot,$run.config_raw_snapshot,$run.history_raw_snapshot)
$checked=@($bindings | ForEach-Object {VerifyRecord $_})
foreach($binding in @($run.manifest_raw_snapshot,$run.config_raw_snapshot,$run.history_raw_snapshot)){
  $actual=RecordFile $binding.source
  if($actual.sha256 -ne $binding.sha256 -or $actual.bytes -ne $binding.bytes){throw 'Closed run source differs from captured bytes'}
  $checked+=$actual
}
$checked+=VerifyRecord $run.artifacts_sha256_verified.'run.log'
$manifest=Get-Content -LiteralPath $run.manifest_raw_snapshot.snapshot -Raw | ConvertFrom-Json
$history=Get-Content -LiteralPath $run.history_raw_snapshot.snapshot -Raw | ConvertFrom-Json
if($manifest.status -ne 'completed' -or $manifest.epochs_completed -ne 80 -or @($history).Count -ne 80){throw 'Incomplete raw run'}
$config=Get-Content -LiteralPath $run.config_raw_snapshot.snapshot -Raw | ConvertFrom-Json
if($config.immutable_config.dataset -ne 'sues200' -or $config.immutable_config.model.backbone -ne 'resnet18' -or $config.immutable_config.model.embed_dim -ne 1024 -or $config.immutable_config.optimization.steps_per_epoch_actual -ne 375){throw 'Unexpected original SUES configuration'}
for($i=0;$i -lt 80;$i++){if($history[$i].epoch -ne $i -or $history[$i].optimizer_steps -ne 375){throw 'Raw epoch/step gap'}}
foreach($entry in $manifest.artifacts.PSObject.Properties){
  $reviewed=$run.artifacts_sha256_verified.PSObject.Properties[$entry.Name].Value
  if($reviewed.sha256 -ne $entry.Value.sha256 -or $reviewed.bytes -ne $entry.Value.bytes){throw 'Artifact declaration mismatch'}
}
$rawParent=Get-Content -LiteralPath $r.parent_status_raw_snapshot.snapshot -Raw | ConvertFrom-Json
$event=@($rawParent.events | Where-Object {$_.pid -eq 19004 -and $_.status -eq 'completed' -and $_.exit_code -eq 0})
if($event.Count -ne 1 -or $event[0].output_dir -ne $run.parent_completed_event.output_dir){throw 'Parent completion mismatch'}
$oldPresent=@(Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -in @(19004,31612)})
if($oldPresent.Count){throw 'Old PID is present; inspect identity'}
$shotPath=Join-Path $execRoot 'host_recovery_20260927_2145\OWNER_SNAPSHOT_20260928_133721457.json'
$shotRecord=RecordFile $shotPath
if($shotRecord.sha256 -ne '9a9e17c9b0c2ae9a6c8c1352f2b1c42bec9c5454337c659f04651226335d926b'){throw 'Snapshot changed'}
$shot=Get-Content -LiteralPath $shotPath -Raw | ConvertFrom-Json
$identities=@($shot.states | ForEach-Object {$_.owner;$_.launcher})+@($shot.science)
$live=@(Get-CimInstance Win32_Process)
foreach($identity in $identities){
  $proc=@($live | Where-Object {$_.ProcessId -eq $identity.pid})
  if($proc.Count -ne 1){throw 'Missing current identity'}
  if([int64]$proc[0].CreationDate.ToUniversalTime().Ticks -ne [int64]$identity.creation_utc_ticks -or $proc[0].CommandLine -cne $identity.command -or $proc[0].ParentProcessId -ne $identity.parent){throw 'Current identity changed'}
}
$transitionPath=Join-Path $execRoot 'host_recovery_20260927_2145\TRANSITION_20260928_133652.json'
$transitionRecord=RecordFile $transitionPath
if($transitionRecord.sha256 -ne '26043523e817f4fff477f06d018f85c8751d522f0c2ce88977fcf25b7fe4bbf7'){throw 'Transition evidence changed'}
$diffRecord=RecordFile (Join-Path $auditDir 'SUES_EMBED_DIM_1024_SEED1_SOURCE_DIFF.patch')
if($diffRecord.sha256 -ne 'dfc9ca366730ebdc58432737e3d92482e5d6b09a20e8c68ca4967b0b9bbe6fe3'){throw 'Reviewed source diff changed'}
$result=[ordered]@{
  schema='root-independent-completion-adoption.v1';adopted_utc=[DateTimeOffset]::UtcNow.ToString('o');adopted=$true
  root_script=(RecordFile $PSCommandPath);independent_report=$reportRecord;reviewed_source_diff=$diffRecord
  verified_small_evidence_bindings=$checked;verified_small_evidence_count=$checked.Count
  root_read_independent_source_and_diff=$true;independent_verified_all_five_new_artifacts=$true
  root_repeated_old_41_checkpoint_hashes=$false;root_repeated_new_checkpoint_hashes=$false
  completed_fit_count=42;completed_fit_ids=$r.accepted_total_fit_ids;formal_evaluation_manifest_count_at_independent_train_audit=$r.formal_evaluation_manifest_count;formal_evaluation_manifests_not_accepted_by_this_train_adoption=$r.formal_evaluation_manifests;accepted_evaluations_by_this_train_adoption=0
  completed_run=$run.run_identifier;parent_completed_event=$run.parent_completed_event
  old_pids_absent_at_root_sample=@(19004,31612)
  independently_held_training_exit_handles=$false;interpreter_exit_code_observed=$false
  exit_evidence_basis='Original parent Popen launcher exit0 and later CIM absence; no independent dual-handle exit proof.'
  owner_snapshot=$shotRecord;transition_evidence=$transitionRecord;fresh_root_identity_count=$identities.Count
  current_science=$shot.science;current_history_count=$shot.history_count;current_history_at_snapshot=$shot.last_history
  running_resource_snapshot_not_a_stop_threshold=$true;runtime_commit_headroom_GiB=$shot.commit_headroom_GiB
  no_live_state_or_source_changes=$true;no_scientific_library_imports=$true;no_recovery_or_validateonly=$true
  resumed_segment_time_not_used_as_complete_training_efficiency=$true
}
$json=$result | ConvertTo-Json -Depth 30
[IO.File]::WriteAllText($outPath,$json+[Environment]::NewLine,[Text.UTF8Encoding]::new($false))
RecordFile $outPath | ConvertTo-Json -Compress
