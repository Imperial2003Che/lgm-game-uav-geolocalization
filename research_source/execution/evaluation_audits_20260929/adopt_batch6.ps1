param([Parameter(Mandatory=$true)][string]$SnapshotPath, [Parameter(Mandatory=$true)][string]$SnapshotSHA256)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$ex = 'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$auditRoot = Join-Path $ex 'evaluation_audits_20260929'
$batch = Join-Path $auditRoot 'batch6_20260929_024917_529481'
$output = Join-Path $auditRoot 'ROOT_BATCH6_ADOPTION_20260929.json'
if (Test-Path -LiteralPath $output) { throw 'Adoption already exists; no overwrite.' }
$checked = [System.Collections.Generic.List[object]]::new()
function Assert-File([string]$Path, [string]$Expected, [long]$Bytes = -1) {
    if ([IO.Path]::GetExtension($Path) -in '.pt','.pth','.ckpt') { throw 'Checkpoint byte reads forbidden.' }
    $before = Get-Item -LiteralPath $Path
    $hash = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    $after = Get-Item -LiteralPath $Path
    if ($hash -cne $Expected -or ($Bytes -ge 0 -and $before.Length -ne $Bytes)) { throw "Binding mismatch: $Path" }
    if ($before.Length -ne $after.Length -or $before.LastWriteTimeUtc.Ticks -ne $after.LastWriteTimeUtc.Ticks) { throw "Changed during read: $Path" }
    $checked.Add([ordered]@{path=$Path;bytes=$before.Length;sha256=$hash})
}
$reportPath = Join-Path $batch 'BATCH6_EVALUATION_REVIEW.json'
Assert-File $reportPath 'f2d578c904e14c99b4d5b4a00ace980d3ecca99c5ba43d2ebe6c7b228e98acf1'
Assert-File (Join-Path $auditRoot 'review_batch6.py') '80bbbaf3f3f1c36ae9b6dfcf149bc2bb3ff64aede5c4e1bcb5275e37658d41f0'
Assert-File (Join-Path $batch 'DELIVERY.json') 'c38a71b619427ea7df0ad7a43cf8ecab6b4d8fa842f0d6dc33105d248892eb97'
$report = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json -DateKind String
Assert-File (Join-Path $ex 'evaluation_audits_20260928/ROOT_BATCH10_ADOPTION_20260928.json') '155610032a4e1951527206ee47c4366fbb202a7c175006209913cee86902173e'
Assert-File (Join-Path $auditRoot 'REVIEW_BATCH6_SOURCE_DIFF.patch') '1ff1a09dbeb9238f1cfd0d9655d89bc1d00700fdf5d51324e0a921a01ab624b1'
if ($report.previous_eval_adoption.sha256 -cne '155610032a4e1951527206ee47c4366fbb202a7c175006209913cee86902173e' -or $report.accepted_total_evaluation_run_count_with_this_batch -ne 18 -or $report.accepted_total_retrieval_task_count_with_this_batch -ne 54) { throw 'Previous and cumulative evaluation count binding mismatch.' }
$delivery = Get-Content -LiteralPath (Join-Path $batch 'DELIVERY.json') -Raw | ConvertFrom-Json -DateKind String
if (-not $report.passed_with_stated_inheritance_limits -or $report.accepted_evaluation_run_count -ne 6 -or $report.accepted_retrieval_task_count -ne 18 -or $report.fresh_evaluation_artifact_count -ne 42) { throw 'Incorrect bounded result.' }
if ($report.fresh_checkpoint_byte_hashes -ne 0 -or $report.checkpoint_loaded -or $report.scientific_entrypoints_executed -or $report.live_files_modified -or @($report.scientific_modules).Count -ne 0) { throw 'Audit exceeded read-only scope.' }
if ($report.scope.out_of_batch_admitted -ne 0 -or $report.all_42_evaluations_accepted -or $report.paper_means_or_conclusions_created -or $report.evaluation_rerun_or_rank_recomputation) { throw 'Unjustified scope claim.' }
if (@($report.raw_evidence_bindings).Count -ne 133 -or @($report.inherited_training_acceptance_graph).Count -ne 13) { throw 'Evidence count differs.' }
foreach ($binding in $report.raw_evidence_bindings) { Assert-File $binding.snapshot $binding.sha256 $binding.bytes }
foreach ($file in $delivery.files) { Assert-File $file.path $file.sha256 $file.bytes }
$expectedTasks = @('university1652_drone_to_satellite','university1652_satellite_to_drone','university1652_street_to_satellite')
$rootRuns = @()
$targets = @(foreach ($variant in 'visual_style','full') { foreach ($seed in 1,2,3) { @{variant=$variant;seed=$seed} } })
if (@($report.runs).Count -ne 6) { throw 'Unexpected report run count.' }
foreach ($target in $targets) {
    $seed = $target.seed
    $id = "formal_main/university1652/$($target.variant)/seed_$seed/resnet18/dim_512"
    $run = @($report.runs | Where-Object identifier -eq $id)
    if ($run.Count -ne 1) { throw "Missing/duplicate run: $id" }
    $run = $run[0]
    if (-not $run.passed_with_stated_inheritance_limits -or @($run.original_evaluation_completion_issues_with_scoped_inherited_checkpoint_SHA).Count -ne 0) { throw 'Evaluation validator issue.' }
    if (@($run.fresh_evaluation_artifact_verification).Count -ne 7) { throw 'Wrong artifact count.' }
    foreach ($artifact in $run.fresh_evaluation_artifact_verification) {
        Assert-File $artifact.path $artifact.sha256 $artifact.bytes
        Assert-File $artifact.snapshot $artifact.sha256 $artifact.bytes
    }
    $manifestPath = Join-Path $run.evaluation_dir 'evaluation_manifest.json'
    $manifestBinding = @($report.raw_evidence_bindings | Where-Object path -eq $manifestPath)
    if ($manifestBinding.Count -ne 1) { throw 'Missing evaluation manifest binding.' }
    Assert-File $manifestPath $manifestBinding[0].sha256 $manifestBinding[0].bytes
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json -DateKind String
    if ($manifest.checkpoint.training_run_config_sha256 -cne $run.run_config_sha256 -or $manifest.checkpoint.sha256 -cne $run.inherited_checkpoint_SHA.inherited_sha256) { throw 'Training/evaluation binding mismatch.' }
    $event = $run.parent_Popen_event
    if ($event.status -ne 'completed' -or $event.exit_code -ne 0 -or $event.output_dir -ne $run.evaluation_dir) { throw 'Parent completion event mismatch.' }
    $expectedCommand = @(
        'C:\项目\.venvs\lgm-baselines\Scripts\python.exe',
        (Join-Path $ex 'primary_path_repair_20260918\run_formal_worker.py'),
        '--path-compat-sha256','11de17bd611431e4471eec1b8ac072a2159fbd02e4eb2cb041b4f3b0f00012a1',
        'evaluate','--dataset','university1652','--data-root','C:\项目\IMTMN\datasets\University-1652',
        '--evidence','C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\evidence_cache\university1652_clip_image_evidence.npz',
        '--output-dir',$run.evaluation_dir,'--device','cuda','--workers','8','--seed',"$seed",'--data-hash-mode','content',
        '--amp','--eval-batch-size','128','--eval-chunk-size','128','--checkpoint',$run.inherited_checkpoint_SHA.path
    )
    if (($event.command -join "`0") -cne ($expectedCommand -join "`0")) { throw 'Parent command differs from frozen evaluation command.' }
    if (@($run.tasks).Count -ne 3 -or (($run.tasks.task -join '|') -cne ($expectedTasks -join '|'))) { throw 'Task membership differs.' }
    foreach ($task in $run.tasks) {
        if (-not $task.official_membership_and_array_alignment_passed -or -not $task.CSV_JSON_agree -or -not $task.stored_array_aggregates_agree -or $task.full_ranking_or_AP_from_all_positive_ranks_recomputed) { throw 'Task evidence mismatch.' }
    }
    $rootRuns += [ordered]@{identifier=$id;evaluation_dir=$run.evaluation_dir;parent_Popen_event=$event;tasks=$run.tasks;inherited_checkpoint_sha256=$run.inherited_checkpoint_SHA.inherited_sha256;checkpoint_current_bytes_rehashed=$false}
}
Assert-File $SnapshotPath $SnapshotSHA256
$snapshot = Get-Content -LiteralPath $snapshotPath -Raw | ConvertFrom-Json -DateKind String
$allProcesses = @(Get-CimInstance Win32_Process)
$identities = @()
if($snapshot.schema -ne 'host-interruption-preservation.v2' -or -not $snapshot.old_science_and_controllers_absent){throw 'Expected sealed host-interruption snapshot'}
$boot=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().Ticks
if($boot -ne [DateTimeOffset]::Parse($snapshot.last_boot_utc).UtcTicks){throw 'Boot changed after capture'}
$oldLaunchers = @($allProcesses | Where-Object ProcessId -in 12564,7896,28100,18364,16816,31052 | Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine)
if($oldLaunchers.Count){throw 'Prior evaluation PID number now exists; inspect identity before adoption'}
$oldOwners = @($allProcesses | Where-Object ProcessId -in $snapshot.old_ids | Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine)
if($oldOwners.Count){throw 'Captured interrupted PID number now exists; inspect identity before adoption'}
if(-not $report.initial_inventory_not_used -or @($report.specific_training_report_authorities).Count -ne 6){throw 'Missing specific training authority'}
foreach($authority in $report.specific_training_report_authorities){
 Assert-File $authority.report_path $authority.report_sha256
 if($authority.PSObject.Properties.Name -contains 'historical_root_adoption'){
  Assert-File $authority.historical_root_adoption.path $authority.historical_root_adoption.sha256
  if(-not $authority.historical_root_adoption.exact_report_edge_verified){throw 'Missing exact historical authority edge'}
 }
}
$result = [ordered]@{
    schema='root-bounded-evaluation-adoption-v1';adopted_with_stated_inheritance_limits=$true;time_utc=[DateTimeOffset]::UtcNow.ToString('o');
    independent_report=@{path=$reportPath;sha256='f2d578c904e14c99b4d5b4a00ace980d3ecca99c5ba43d2ebe6c7b228e98acf1'};
    root_script=@{path=$PSCommandPath;sha256=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()};
    root_reviewed_inherited_source_and_complete_batch_diff=$true;
    inherited_training_count=42;accepted_evaluation_run_count=6;accepted_retrieval_task_count=18;fresh_evaluation_artifact_count=42;
    inherited_previous_eval_adoption=$report.previous_eval_adoption;accepted_total_evaluation_runs=18;accepted_total_retrieval_tasks=54;
    snapshot_bindings_checked=133;root_checked_file_bindings=$checked.ToArray();runs=$rootRuns;
    host_interruption_snapshot=@{path=$snapshotPath;sha256=$SnapshotSHA256};
    root_current_identities=$identities;root_old_launcher_numbers_observed=$oldLaunchers;root_old_owner_numbers_observed=$oldOwners;current_host_boot_utc_ticks=$boot;current_live_owner_proof='none: host interrupted, recovery not yet launched';specific_training_report_authorities=$report.specific_training_report_authorities;
    independent_interpreter_exit_code_proof=$false;exit_evidence_basis=$report.exit_evidence_basis;
    fresh_checkpoint_byte_hashes=0;scientific_imports=$false;scientific_entrypoints_executed=$false;live_scientific_files_changed=$false;
    limitations=$report.limitations;all_evaluations_accepted=$false;paper_statistics_updated=$false
}
$json = $result | ConvertTo-Json -Depth 20
[IO.File]::WriteAllText($output,$json+[Environment]::NewLine,[Text.UTF8Encoding]::new($false))
[ordered]@{path=$output;sha256=(Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash.ToLowerInvariant();adopted=$true;file_checks=$checked.Count;identities=$identities.Count;new_runs=6;new_tasks=18;total_runs=18;total_tasks=54} | ConvertTo-Json
