param([Parameter(Mandatory=$true)][string]$ReportPath,[Parameter(Mandatory=$true)][string]$ReportSHA,[Parameter(Mandatory=$true)][string]$MetadataSHA,[Parameter(Mandatory=$true)][string]$ReviewSourceSHA,[Parameter(Mandatory=$true)][string]$ContractReportSHA,[Parameter(Mandatory=$true)][string]$ObservationPath,[Parameter(Mandatory=$true)][string]$ObservationSHA,[Parameter(Mandatory=$true)][string]$DeliverySHA,[Parameter(Mandatory=$true)][string]$DiffSHA)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$e=Split-Path -Parent $PSScriptRoot
$checked=[Collections.Generic.Dictionary[string,object]]::new([StringComparer]::OrdinalIgnoreCase)
function Verify([string]$p,[string]$h,[long]$bytes=-1){
 if([IO.Path]::GetExtension($p) -in @('.pt','.pth','.ckpt')){throw 'Checkpoint byte read prohibited'}
 $full=[IO.Path]::GetFullPath($p)
 if($checked.ContainsKey($full)){$a=$checked[$full]}else{$i=Get-Item -LiteralPath $full;$a=[ordered]@{path=$full;sha256=(Get-FileHash -LiteralPath $full).Hash.ToLower();bytes=$i.Length};$checked.Add($full,$a)}
 if($a.sha256 -cne $h -or ($bytes -ge 0 -and $a.bytes -ne $bytes)){throw "Binding mismatch: $full"};$a
}
function B($b){$n=-1;if($b.PSObject.Properties.Name -contains 'bytes'){$n=[long]$b.bytes};Verify $b.path $b.sha256 $n}
function J([string]$p){Get-Content -LiteralPath $p -Raw|ConvertFrom-Json -DateKind String}
$rb=Verify $ReportPath $ReportSHA
$attempt=Split-Path -Parent $ReportPath
$mb=Verify (Join-Path $attempt 'METADATA.json') $MetadataSHA
$sb=Verify (Join-Path $PSScriptRoot 'review_full1.py') $ReviewSourceSHA
$r=J $rb.path;$m=J $mb.path
if(-not $r.passed_with_stated_limits -or $r.accepted_runs -ne 1 -or $r.accepted_corrupted_conditions -ne 30 -or $r.accepted_corrupted_tasks -ne 90 -or $r.accepted_clean_tasks -ne 3 -or $r.summary_rows -ne 540){throw 'Unexpected accepted scope'}
if($r.checkpoint_bytes_read -ne 0 -or $r.cache_or_image_bytes_read -ne 0 -or $r.scientific_entrypoints_executed -or $r.live_files_modified -or @($r.scientific_modules).Count -ne 0 -or @($r.original_completion_issues).Count -ne 0){throw 'Unexpected execution or completion issues'}
$null=B $r.source;$null=B $m.source;$null=B $m.report
foreach($b in $m.files){if(-not ([IO.Path]::GetFullPath($b.path)).StartsWith($attempt+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Metadata member outside captured attempt'};$null=B $b}
$ledgerPath='C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\runs\frozen_robustness_matrix_ledger.json'
foreach($b in $r.raw_evidence_bindings){$null=Verify $b.snapshot $b.sha256 $b.bytes;if([IO.Path]::GetFullPath($b.path) -ine $ledgerPath){$null=B $b}}
foreach($b in $r.artifact_bindings){$null=B $b}
$null=B $r.directory_membership
if($r.directory_membership.count -ne 93441 -or $r.directory_membership.image_bytes_read){throw 'Directory-only membership scope mismatch'}
$manifest=J $r.manifest_binding.path
$config=J (Join-Path (Split-Path -Parent $r.manifest_binding.path) 'run_config.json')
if($manifest.status -ne 'completed' -or $manifest.dataset -ne 'university1652' -or $manifest.variant -ne 'full' -or $manifest.completed_corruption_conditions -ne 30 -or $manifest.run_config_sha256 -cne 'c7bfc6c41ccadf0f52cf79609a76ef921bf456c5d06334b78ece284a5b4c9ce1' -or $manifest.checkpoint.checkpoint_sha256 -cne $r.inherited_authority.checkpoint_sha256 -or $null -eq $manifest.clip_clean_reproduction_audit){throw 'Manifest/config scope mismatch'}
if($config.run_config_sha256 -cne $manifest.run_config_sha256 -or $config.immutable_config.checkpoint.checkpoint_sha256 -cne $manifest.checkpoint.checkpoint_sha256){throw 'Config/checkpoint declaration mismatch'}
$ids=@($r.tasks|ForEach-Object {"$($_.condition)/$($_.severity)/$($_.task)"})
if($ids.Count -ne 93 -or @($ids|Select-Object -Unique).Count -ne 93 -or @($r.original_functions|Where-Object body_changed).Count -ne 0){throw 'Task/AST coverage mismatch'}
$inherited=@($r.original_hash_queries|Where-Object mode -eq 'exact_inherited_checkpoint_SHA_no_read')
if($inherited.Count -ne 1 -or $inherited[0].sha256 -cne $manifest.checkpoint.checkpoint_sha256){throw 'Exact inherited checkpoint request mismatch'}
if(@($r.original_functions).Count -ne 52 -or @($r.original_hash_queries).Count -ne 406 -or $r.unique_artifact_count -ne 220 -or @($r.raw_evidence_bindings).Count -ne 247 -or $r.checks.csv_tables -ne 62){throw 'Full fixed source/artifact/hash-query counts differ'}
if(-not $r.full_clip_diagnostic.canonical_verified -or -not $r.full_clip_diagnostic.sample_path_selection_checked_without_image_bytes -or $r.full_clip_diagnostic.tolerance_gate_exists -or $r.full_clip_diagnostic.numerical_error_recomputed){throw 'Full CLIP limited diagnostic scope mismatch'}
$training=J $r.specific_training_source_bindings.report.path
$trainingRoot=J $r.specific_training_source_bindings.root.path
if(-not $training.passed -or $training.run_identifier -cne $r.inherited_authority.source_training_identifier -or $training.epochs_completed -ne 80 -or $trainingRoot.audit_sha256 -cne $r.specific_training_source_bindings.report.sha256 -or $training.artifacts_sha256_verified.'best.pt'.sha256 -cne $manifest.checkpoint.checkpoint_sha256){throw 'Full exact historical training adoption edge mismatch'}
$liveLedger=J $ledgerPath
$finished=$liveLedger.runs.'university1652/full/seed_1'
$sealed=$r.original_parent_record.run_record
if(($finished|ConvertTo-Json -Depth 12 -Compress) -cne ($sealed|ConvertTo-Json -Depth 12 -Compress)){throw 'Completed original ledger record changed'}
if($finished.status -ne 'completed_and_verified' -or @($finished.attempts).Count -ne 1 -or $finished.attempts[0].returncode -ne 0){throw 'Original parent return record mismatch'}
$transition=Verify (Join-Path $PSScriptRoot 'ROOT_FULL_TRANSITION.json') '70967e6f477d24419439c6251601300d7d77056b9682d7c6a963654b53e470f8'
$t=J $transition.path
$null=B $t.source;$null=B $t.old_identity_snapshot;$null=B $t.new_identity_snapshot;$null=B $t.ledger_snapshot
foreach($b in $t.closed_log_bindings){$null=B $b}
if(($t.completed_record|ConvertTo-Json -Depth 12 -Compress) -cne ($sealed|ConvertTo-Json -Depth 12 -Compress)){throw 'Root transition differs from independent completed record'}
$db=Verify (Join-Path $PSScriptRoot 'DELIVERY.json') $DeliverySHA
$delivery=J $db.path
if(-not $delivery.passed_with_stated_limits -or -not $delivery.root_adoption_not_claimed -or $delivery.new_artifacts -ne 220 -or $delivery.scientific_execution_performed){throw 'Independent delivery scope mismatch'}
foreach($b in $delivery.files){$null=B $b}
$diff=Verify (Join-Path $PSScriptRoot 'FULL_FROM_VISUAL_SOURCE_DIFF.patch') $DiffSHA
$previous=Verify (Join-Path $e 'robustness_audit_20260929_0946\ROOT_VISUAL1_ADOPTION.json') '81ec5d80b7370ae5dc79c3f12e0633b88ade73be3422ec155ea11def68713cc6'
$prev=J $previous.path
if(-not $prev.accepted_with_stated_limits -or $prev.accepted_robustness_runs -ne 1 -or $prev.accepted_corrupted_tasks -ne 90){throw 'Previous adopted scope mismatch'}
$cb=Verify (Join-Path $PSScriptRoot 'contract_review\FULL_CONTRACT_REVIEW.json') $ContractReportSHA
$c=J $cb.path
$null=B $c.review_markdown;$null=B $c.sealing_source
foreach($b in $c.source_and_small_file_bindings){$null=B $b.snapshot;if($b.label -ne 'ledger_snapshot'){$null=B $b.source}}
if($c.source_or_live_state_modified -or @($c.scientific_modules_imported).Count -ne 0 -or $c.original_validator_or_science_executed -or $c.new_test_suite_run -or -not $c.manifest_embedded_diagnostic_equals_standalone){throw 'Full contract scope mismatch'}
if(($manifest.clip_clean_reproduction_audit|ConvertTo-Json -Depth 15 -Compress) -cne ($c.diagnostic|ConvertTo-Json -Depth 15 -Compress)){throw 'Full diagnostic declaration mismatch'}
if($c.diagnostic.payload_sha256 -cne 'd8788767a0bd22ef51e0b2a81218b762c5ede896e1668991caa9626b833db10c' -or $c.diagnostic.samples -ne 64 -or $c.diagnostic.clip_provenance.precision -cne 'fp16'){throw 'Full diagnostic scope mismatch'}
if($r.inherited_authority.source_training_identifier -cne 'formal_main/university1652/full/seed_1/resnet18/dim_512' -or $manifest.checkpoint.checkpoint_sha256 -cne '581fc1b40e0dc343f3906c8e180bc843a58d37ba97e8fb5833f2c49ac39a9c99'){throw 'Specific Full authority mismatch'}
$ob=Verify $ObservationPath $ObservationSHA;$obs=J $ob.path
foreach($b in $obs.raw_snapshots){$null=B $b.snapshot};foreach($b in $obs.pins){$null=B $b};$null=B $obs.first_identity;$null=B $obs.source;$null=B $obs.contract_helper;$null=B $obs.contract_report
$live=@($obs.live_roles|ForEach-Object{$_.owner;$_.launcher})+@($obs.stage_pair)+@($obs.robustness.worker_pair)
$all=@(Get-CimInstance Win32_Process)
foreach($p in $live){$n=@($all|Where-Object ProcessId -eq $p.pid);if($n.Count -ne 1 -or $n[0].CreationDate.ToUniversalTime().Ticks -ne [long]$p.creation_utc_ticks -or $n[0].ParentProcessId -ne $p.parent -or $n[0].CommandLine -cne $p.command){throw 'Natural phase change: obtain fresh observation without recovery'}}
if($live.Count -ne 12 -or $null -ne $obs.primary.exit_code){throw 'Live identity/primary exit scope mismatch'}
$old=@($all|Where-Object {$_.ProcessId -in @(40820,43872)}|ForEach-Object{[ordered]@{pid=$_.ProcessId;parent=$_.ParentProcessId;creation_utc_ticks=$_.CreationDate.ToUniversalTime().Ticks;command=$_.CommandLine}})
$result=[ordered]@{schema='lgm.root.robustness-full1-adoption.v1';time=(Get-Date).ToString('o');accepted_with_stated_limits=$true;source=[ordered]@{path=$PSCommandPath;sha256=(Get-FileHash -LiteralPath $PSCommandPath).Hash.ToLower()};independent_review=$rb;metadata=$mb;review_source=$sb;contract_review=$cb;transition=$transition;previous_robustness_adoption=$previous;newly_accepted_runs=1;newly_accepted_corrupted_conditions=30;newly_accepted_corrupted_tasks=90;newly_accepted_clean_tasks=3;accepted_robustness_runs=2;accepted_corrupted_conditions=60;accepted_corrupted_tasks=180;accepted_clean_tasks=6;pipeline_whole_jobs_adopted=3;retained_training_fits=42;retained_official_runs=42;retained_official_tasks=231;retained_transfer_runs=12;retained_transfer_tasks=66;robustness_pipeline_complete=$false;actual_unique_file_checks=$checked.Count;raw_snapshot_count=@($r.raw_evidence_bindings).Count;unique_artifact_count=$r.unique_artifact_count;bindings=@($checked.Values);current_observation=$ob;current_identity_count=$live.Count;current_identities=$live;old_pid_current_presence=$old;inherited_authority=$r.inherited_authority;limits=@($r.limits)+@($c.interpretation_limits);full_clean_diagnostic=$c.diagnostic;validator_compatibility=$r.compatibility;float32_mean_check_limit=$r.independent_mean_check;exit_limit='Original subprocess.run returncode0 plus current old PID absence/identity observation, not independent launcher/interpreter dual-handle exit codes. Primary own exit code remains unknown.';review_method='Root read original completion helpers and producer ranking/degradation/summary code, complete independent audit source and source contract; checked captured/source/production bindings, scope, exact completed ledger record and actual process identities.';checkpoint_bytes_rehashed=0;scientific_execution=$false;live_state_modified=$false}
$out=Join-Path $PSScriptRoot 'ROOT_FULL1_ADOPTION.json';$data=[Text.UTF8Encoding]::new($false).GetBytes(($result|ConvertTo-Json -Depth 35));$f=[IO.File]::Open($out,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read);try{$f.Write($data,0,$data.Length)}finally{$f.Dispose()}
[pscustomobject]@{path=$out;sha256=(Get-FileHash -LiteralPath $out).Hash.ToLower();checks=$checked.Count;identities=$live.Count;corrupted_tasks=90;clean_tasks=3}|ConvertTo-Json
