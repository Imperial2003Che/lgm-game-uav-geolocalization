param([Parameter(Mandatory=$true)][string]$ReportPath,[Parameter(Mandatory=$true)][string]$ReportSHA,[Parameter(Mandatory=$true)][string]$MetadataSHA,[Parameter(Mandatory=$true)][string]$ReviewSourceSHA,[Parameter(Mandatory=$true)][string]$ContractReportSHA,[Parameter(Mandatory=$true)][string]$ObservationPath,[Parameter(Mandatory=$true)][string]$ObservationSHA)
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
$sb=Verify (Join-Path $PSScriptRoot 'review_visual1.py') $ReviewSourceSHA
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
if($manifest.status -ne 'completed' -or $manifest.dataset -ne 'university1652' -or $manifest.variant -ne 'visual' -or $manifest.completed_corruption_conditions -ne 30 -or $manifest.run_config_sha256 -cne '51edb3f929b337ec3c129ad502336a5f5676ef15fbd606d760526b04a2dbfbd0' -or $manifest.checkpoint.checkpoint_sha256 -cne $r.inherited_authority.checkpoint_sha256 -or $null -ne $manifest.clip_clean_reproduction_audit){throw 'Manifest/config scope mismatch'}
if($config.run_config_sha256 -cne $manifest.run_config_sha256 -or $config.immutable_config.checkpoint.checkpoint_sha256 -cne $manifest.checkpoint.checkpoint_sha256){throw 'Config/checkpoint declaration mismatch'}
$ids=@($r.tasks|ForEach-Object {"$($_.condition)/$($_.severity)/$($_.task)"})
if($ids.Count -ne 93 -or @($ids|Select-Object -Unique).Count -ne 93 -or @($r.original_functions|Where-Object body_changed).Count -ne 0){throw 'Task/AST coverage mismatch'}
$inherited=@($r.original_hash_queries|Where-Object mode -eq 'exact_inherited_checkpoint_SHA_no_read')
if($inherited.Count -ne 1 -or $inherited[0].sha256 -cne $manifest.checkpoint.checkpoint_sha256){throw 'Exact inherited checkpoint request mismatch'}
$liveLedger=J $ledgerPath
$finished=$liveLedger.runs.'university1652/visual/seed_1'
$sealed=$r.original_parent_record.run_record
if(($finished|ConvertTo-Json -Depth 12 -Compress) -cne ($sealed|ConvertTo-Json -Depth 12 -Compress)){throw 'Completed original ledger record changed'}
if($finished.status -ne 'completed_and_verified' -or @($finished.attempts).Count -ne 1 -or $finished.attempts[0].returncode -ne 0){throw 'Original parent return record mismatch'}
$transition=Verify (Join-Path $PSScriptRoot 'ROOT_TRANSITION_20260929_094806.json') '4bc09b83cf1372d06cb32aa2adb9b60a2a3f2f4f81d62c6169ebf00ed803ca91'
$db=Verify (Join-Path $PSScriptRoot 'DELIVERY.json') '72b26b8e9cc4d6ec452bfd1185057f3290a8a4ea6082c7d280c75f3240f1cebf'
$delivery=J $db.path
foreach($b in $delivery.bindings){$null=B $b}
$ab=Verify (Join-Path $PSScriptRoot 'addendum\REVIEW_ADDENDUM.json') '47f5363a92f065caa195bd716065ce7f47b25680a8b75f9de5d06610d22dbb08'
$add=J $ab.path
if(-not $add.passed -or $add.base_review_sha256 -cne $rb.sha256 -or $add.base_metadata_sha256 -cne $mb.sha256 -or $add.npz_header_files -ne 93 -or $add.metrics_semantics_files -ne 31 -or $add.csv_order_unique_headers -ne 62 -or $add.checkpoint_or_cache_or_image_bytes_read -or $add.prior_audit_or_scientific_files_modified){throw 'Addendum scope mismatch'}
$null=B $add.source
foreach($b in $add.input_bindings){$null=B $b}
$cb=Verify (Join-Path $PSScriptRoot 'contract_review\CONTRACT_REVIEW.json') $ContractReportSHA
$c=J $cb.path
$null=B $c.source_bindings;$null=B $c.review_markdown;$null=B $c.sealing_script;$null=B $c.optional_full_clip_diagnostic.warning_snapshot
$contractBindings=J $c.source_bindings.path
if(@($contractBindings.bindings).Count -ne 13 -or $c.scientific_execution_performed -or $c.artifact_acceptance_performed -or $c.optional_full_clip_diagnostic.threshold_pass_claim -or $c.optional_full_clip_diagnostic.full_robustness_completion_claim){throw 'Source contract review scope mismatch'}
foreach($b in $contractBindings.bindings){$null=B $b.snapshot;if($b.label -ne 'ledger_snapshot'){$null=Verify $b.source_path $b.sha256 $b.bytes};if($null -ne $b.expected_sha256 -and $b.sha256 -cne $b.expected_sha256){throw 'Frozen source mismatch'}}
$ob=Verify $ObservationPath $ObservationSHA;$obs=J $ob.path
foreach($b in $obs.raw_snapshots){$null=B $b.snapshot};foreach($b in $obs.pins){$null=B $b};$null=B $obs.first_identity;$null=B $obs.source;$null=B $obs.contract_helper;$null=B $obs.contract_report
$live=@($obs.live_roles|ForEach-Object{$_.owner;$_.launcher})+@($obs.stage_pair)+@($obs.robustness.worker_pair)
$all=@(Get-CimInstance Win32_Process)
foreach($p in $live){$n=@($all|Where-Object ProcessId -eq $p.pid);if($n.Count -ne 1 -or $n[0].CreationDate.ToUniversalTime().Ticks -ne [long]$p.creation_utc_ticks -or $n[0].ParentProcessId -ne $p.parent -or $n[0].CommandLine -cne $p.command){throw 'Natural phase change: obtain fresh observation without recovery'}}
if($live.Count -ne 12 -or $null -ne $obs.primary.exit_code){throw 'Live identity/primary exit scope mismatch'}
$old=@($all|Where-Object {$_.ProcessId -in @(27888,41564)}|ForEach-Object{[ordered]@{pid=$_.ProcessId;parent=$_.ParentProcessId;creation_utc_ticks=$_.CreationDate.ToUniversalTime().Ticks;command=$_.CommandLine}})
$result=[ordered]@{schema='lgm.root.robustness-visual1-adoption.v1';time=(Get-Date).ToString('o');accepted_with_stated_limits=$true;source=[ordered]@{path=$PSCommandPath;sha256=(Get-FileHash -LiteralPath $PSCommandPath).Hash.ToLower()};independent_review=$rb;metadata=$mb;review_source=$sb;contract_review=$cb;transition=$transition;accepted_robustness_runs=1;accepted_corrupted_conditions=30;accepted_corrupted_tasks=90;accepted_clean_tasks=3;pipeline_whole_jobs_adopted=3;retained_training_fits=42;retained_official_runs=42;retained_official_tasks=231;retained_transfer_runs=12;retained_transfer_tasks=66;robustness_pipeline_complete=$false;actual_unique_file_checks=$checked.Count;raw_snapshot_count=@($r.raw_evidence_bindings).Count;unique_artifact_count=$r.unique_artifact_count;bindings=@($checked.Values);current_observation=$ob;current_identity_count=$live.Count;current_identities=$live;old_pid_current_presence=$old;inherited_authority=$r.inherited_authority;limits=$r.limits;validator_compatibility=$r.compatibility;float32_mean_check_limit=$r.independent_mean_check;exit_limit='Original subprocess.run returncode0 plus current old PID absence/identity observation, not independent launcher/interpreter dual-handle exit codes. Primary own exit code remains unknown.';review_method='Root read original completion helpers and producer ranking/degradation/summary code, complete independent audit source and source contract; checked captured/source/production bindings, scope, exact completed ledger record and actual process identities.';checkpoint_bytes_rehashed=0;scientific_execution=$false;live_state_modified=$false}
$out=Join-Path $PSScriptRoot 'ROOT_VISUAL1_ADOPTION.json';$data=[Text.UTF8Encoding]::new($false).GetBytes(($result|ConvertTo-Json -Depth 35));$f=[IO.File]::Open($out,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read);try{$f.Write($data,0,$data.Length)}finally{$f.Dispose()}
[pscustomobject]@{path=$out;sha256=(Get-FileHash -LiteralPath $out).Hash.ToLower();checks=$checked.Count;identities=$live.Count;corrupted_tasks=90;clean_tasks=3}|ConvertTo-Json
