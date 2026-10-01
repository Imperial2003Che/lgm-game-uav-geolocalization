param([Parameter(Mandatory=$true)][string]$ReportSHA,[Parameter(Mandatory=$true)][string]$MetadataSHA,[Parameter(Mandatory=$true)][string]$DeliverySHA,[Parameter(Mandatory=$true)][string]$ContractSHA,[Parameter(Mandatory=$true)][string]$ObservationPath,[Parameter(Mandatory=$true)][string]$ObservationSHA)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$e=Split-Path -Parent $PSScriptRoot
$checked=[Collections.Generic.Dictionary[string,object]]::new([StringComparer]::OrdinalIgnoreCase)
function V([string]$p,[string]$h,[long]$bytes=-1){
 $p=[IO.Path]::GetFullPath($p)
 if([IO.Path]::GetExtension($p) -in @('.pt','.pth','.ckpt') -or $p -match '[\\/]evidence_cache[\\/].*\.npz$' -or $p.StartsWith('C:\项目\IMTMN\datasets\',[StringComparison]::OrdinalIgnoreCase)){throw 'Scientific data byte read prohibited'}
 if($checked.ContainsKey($p)){$b=$checked[$p]}else{$i=Get-Item -LiteralPath $p;$b=[ordered]@{path=$p;sha256=(Get-FileHash -LiteralPath $p).Hash.ToLower();bytes=$i.Length};$checked.Add($p,$b)}
 if($b.sha256 -cne $h -or ($bytes -ge 0 -and $b.bytes -ne $bytes)){throw "Binding mismatch: $p"};$b
}
function B($b){$n=-1;if($b.PSObject.Properties.Name -contains 'bytes'){$n=[long]$b.bytes};V $b.path $b.sha256 $n}
function J([string]$p){Get-Content -LiteralPath $p -Raw|ConvertFrom-Json -DateKind String}
function Ref($o,[string]$p,[string]$h){
 if($null -eq $o){return $false}
 if($o -is [pscustomobject]){
  $values=@($o.PSObject.Properties.Value)
  $pathMatch=@($values|Where-Object {$_ -is [string] -and $_.EndsWith('.json',[StringComparison]::OrdinalIgnoreCase) -and [IO.Path]::GetFullPath($_) -ieq [IO.Path]::GetFullPath($p)})
  if($h -cin $values -and $pathMatch.Count -gt 0){return $true}
  foreach($v in $values){if(Ref $v $p $h){return $true}}
 }elseif($o -is [array]){foreach($v in $o){if(Ref $v $p $h){return $true}}}
 return $false
}
$attempt=Join-Path $PSScriptRoot 'a1'
$rb=V (Join-Path $attempt 'REVIEW.json') $ReportSHA
$mb=V (Join-Path $attempt 'METADATA.json') $MetadataSHA
$source=V (Join-Path $PSScriptRoot 'review_sues_visual1.py') '30e19aa18bb810604f06c8fb7b6c078d8330355a3e677972b2acc3df37ebdf0c'
$diff=V (Join-Path $PSScriptRoot 'SUES_VISUAL_FROM_FULL_SOURCE_DIFF.patch') 'b78b04ef20efbaaece67bc926b00f8f425c9a20e57dfd165d5d951194db614f7'
$r=J $rb.path;$m=J $mb.path
if(-not $r.passed_with_stated_limits -or $r.accepted_runs -ne 1 -or $r.accepted_corrupted_conditions -ne 30 -or $r.accepted_corrupted_tasks -ne 240 -or $r.accepted_clean_tasks -ne 8 -or $r.summary_rows -ne 1440){throw 'New result scope differs'}
if($r.checkpoint_bytes_read -ne 0 -or $r.cache_or_image_bytes_read -ne 0 -or $r.scientific_entrypoints_executed -or $r.live_files_modified -or @($r.scientific_modules).Count -ne 0 -or @($r.original_completion_issues).Count -ne 0){throw 'Unexpected execution/completion issues'}
$null=B $r.source;$null=B $m.source;$null=B $m.report
foreach($b in $m.files){if(-not ([IO.Path]::GetFullPath($b.path)).StartsWith($attempt+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Metadata member outside captured attempt'};$null=B $b}
$ledgerPath='C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\runs\frozen_robustness_matrix_ledger.json'
foreach($b in $r.raw_evidence_bindings){$null=V $b.snapshot $b.sha256 $b.bytes;if([IO.Path]::GetFullPath($b.path) -ine $ledgerPath){$null=B $b}}
foreach($b in $r.artifact_bindings){$null=B $b}
$null=B $r.directory_membership
if($r.directory_membership.count -ne 40200 -or $r.directory_membership.image_bytes_read){throw 'Directory-only scope mismatch'}
$protocol=$r.sues_official_protocol;$null=B $protocol.manifest
if($protocol.train_ids.Count -ne 120 -or $protocol.test_ids.Count -ne 80 -or ($protocol.heights -join ',') -cne '150,200,250,300' -or $protocol.tasks -ne 8 -or -not $protocol.all_200_gallery_ids_retained){throw 'SUES protocol mismatch'}
$manifest=J $r.manifest_binding.path
$config=J (Join-Path (Split-Path -Parent $r.manifest_binding.path) 'run_config.json')
$checkpointSHA='b9da9c88f13541f05c17848eab9c43a2f332adbd22ee8880b82149ee8cc03a7a'
$identifier='formal_main/sues200/visual/seed_1/resnet18/dim_512'
if($manifest.status -ne 'completed' -or $manifest.dataset -ne 'sues200' -or $manifest.variant -ne 'visual' -or $manifest.completed_corruption_conditions -ne 30 -or $manifest.run_config_sha256 -cne 'd19283877ee9967fc36ca82155564cdc5945a44f7633273e119a661bf684f6d9' -or $manifest.checkpoint.checkpoint_sha256 -cne $checkpointSHA -or $null -ne $manifest.clip_clean_reproduction_audit){throw 'Manifest scope mismatch'}
if($config.run_config_sha256 -cne $manifest.run_config_sha256 -or $config.immutable_config.checkpoint.checkpoint_sha256 -cne $checkpointSHA -or $config.immutable_config.unique_query_images -ne 16080 -or $config.immutable_config.unique_clean_gallery_images -ne 40200){throw 'Config/checkpoint/member declarations differ'}
$ids=@($r.tasks|ForEach-Object {"$($_.condition)/$($_.severity)/$($_.task)"})
if($ids.Count -ne 248 -or @($ids|Select-Object -Unique).Count -ne 248 -or @($r.original_functions|Where-Object body_changed).Count -ne 0 -or @($r.original_functions).Count -ne 52){throw 'Task/AST coverage mismatch'}
foreach($task in $r.tasks){if($task.task -match '^sues200_uav_(150|200|250|300)m_to_satellite$'){if($task.queries -ne 4000 -or $task.gallery -ne 200){throw 'Forward scale'}}elseif($task.task -match '^sues200_satellite_to_uav_(150|200|250|300)m$'){if($task.queries -ne 80 -or $task.gallery -ne 10000){throw 'Reverse scale'}}else{throw 'Unexpected task'}}
$inherited=@($r.original_hash_queries|Where-Object mode -eq 'exact_inherited_checkpoint_SHA_no_read')
if($inherited.Count -ne 1 -or $inherited[0].sha256 -cne $checkpointSHA -or @($r.original_hash_queries).Count -ne 715 -or $r.unique_artifact_count -ne 374 -or @($r.raw_evidence_bindings).Count -ne 409 -or $r.checks.csv_tables -ne 62){throw 'Bounded hash/artifact scope differs'}
if($r.inherited_authority.source_training_identifier -cne $identifier -or $r.inherited_authority.checkpoint_sha256 -cne $checkpointSHA){throw 'Specific training identifier mismatch'}
$trainingBind=B $r.specific_training_source_bindings.report;$trainingBatch=J $trainingBind.path
$training=@($trainingBatch.new_runs|Where-Object run_identifier -CEQ $identifier)
if(-not $trainingBatch.batch_passed -or $training.Count -ne 1 -or $training[0].epochs_completed -ne 80 -or $training[0].last_epoch -ne 79 -or $training[0].optimizer_steps_each_epoch_from_original_config -ne 375 -or @($training[0].original_training_completion_issues).Count -ne 0 -or $training[0].artifacts_sha256_verified.'best.pt'.sha256 -cne $checkpointSHA -or $training[0].artifacts_sha256_verified.'best.pt'.bytes -ne 140607467){throw 'Exact training authority mismatch'}
$chain=@($r.specific_training_source_bindings.root42_ancestry)
if($chain.Count -lt 2 -or [IO.Path]::GetFullPath($chain[0].to_document) -ine $trainingBind.path -or $chain[0].sha256 -cne $trainingBind.sha256 -or $chain[-1].sha256 -cne 'ca54f91342f77d7d17f18a932c61681ae6f4d7c14f4ffd917c0c1594fc289e87' -or $null -ne $chain[-1].from_document){throw 'Training chain endpoints differ'}
for($i=0;$i -lt $chain.Count;$i++){$node=$chain[$i];$null=V $node.to_document $node.sha256;if($i -lt $chain.Count-1){$next=$chain[$i+1];if([IO.Path]::GetFullPath($node.from_document) -ine [IO.Path]::GetFullPath($next.to_document) -or -not (Ref (J $next.to_document) $node.to_document $node.sha256)){throw 'Actual parent path/SHA chain edge absent'}}}
$liveLedger=J $ledgerPath;$finished=$liveLedger.runs.'sues200/visual/seed_1';$sealed=$r.original_parent_record.run_record
if(($finished|ConvertTo-Json -Depth 12 -Compress) -cne ($sealed|ConvertTo-Json -Depth 12 -Compress) -or $finished.status -ne 'completed_and_verified' -or @($finished.attempts).Count -ne 1 -or $finished.attempts[0].returncode -ne 0){throw 'Exact completed parent record changed'}
$tb=V (Join-Path $PSScriptRoot 'ROOT_SUES_VISUAL_TRANSITION.json') '60868db118a368fcd3ca7467afe02e75570309ec2a337f4c56344738f8b4d987';$t=J $tb.path
$null=B $t.source;$null=B $t.old_identity_snapshot;$null=B $t.new_identity_snapshot;$null=B $t.ledger_snapshot;foreach($b in $t.closed_log_bindings){$null=B $b}
if(($t.completed_record|ConvertTo-Json -Depth 12 -Compress) -cne ($sealed|ConvertTo-Json -Depth 12 -Compress)){throw 'Transition record mismatch'}
$db=V (Join-Path $PSScriptRoot 'DELIVERY.json') $DeliverySHA;$d=J $db.path
if(-not $d.passed_with_stated_limits -or -not $d.root_adoption_not_claimed -or $d.new_artifacts -ne 374 -or $d.scientific_execution_performed){throw 'Delivery scope differs'}
foreach($b in $d.files){$null=B $b}
$previous=V (Join-Path $e 'robustness_full_audit_20260929_1247\ROOT_FULL1_ADOPTION.json') 'ea8c3065092db79c67005b6b6aa1b54a5433ba39ae4b143504f09618f98fd1f5';$prev=J $previous.path
if(-not $prev.accepted_with_stated_limits -or $prev.accepted_robustness_runs -ne 2 -or $prev.accepted_corrupted_tasks -ne 180 -or $prev.accepted_clean_tasks -ne 6){throw 'Previous accepted scope differs'}
$cb=V (Join-Path $PSScriptRoot 'contract_review\SUES_VISUAL_CONTRACT_REVIEW.json') $ContractSHA;$c=J $cb.path
foreach($b in $c.bindings){$null=B $b}
if($c.live_state_modified -or @($c.scientific_imports).Count -ne 0 -or $c.checkpoint_cache_image_bytes_read -ne 0 -or $c.scientific_acceptance -or $c.root_adoption){throw 'Contract read-only scope differs'}
if($c.canonical_config_sha256 -cne $manifest.run_config_sha256 -or $c.inherited_checkpoint.sha256 -cne $checkpointSHA -or $c.protocol.unique_queries -ne 16080 -or $c.protocol.unique_clean_gallery_images -ne 40200 -or ($c.parent_completion|ConvertTo-Json -Depth 12 -Compress) -cne ($finished.attempts[0]|ConvertTo-Json -Depth 12 -Compress)){throw 'Independent small contract differs from adopted scope'}
$staticBind=V (Join-Path $PSScriptRoot 'contract_review\SUES_VISUAL_SOURCE_STATIC_REVIEW.json') '16cd978a5156fc1020f9bba9a96508c5504b1eb0c5aa6f4b2be5b0b9f8a77288';$static=J $staticBind.path
$null=B $static.review_markdown;$null=B $static.sealing_source
foreach($b in $static.source_and_small_file_bindings){$null=B $b}
if(@($static.blocking_findings).Count -ne 0 -or $static.audit_candidate_executed_here -or $static.old_suites_rerun -or @($static.scientific_imports).Count -ne 0 -or $static.checkpoint_cache_image_or_query_array_bytes_read -ne 0 -or $static.frozen_sources_or_live_state_modified){throw 'Static source review scope differs'}
$ob=V $ObservationPath $ObservationSHA;$obs=J $ob.path
foreach($b in $obs.raw_snapshots){$null=B $b.snapshot};foreach($b in $obs.pins){$null=B $b};$null=B $obs.first_identity;$null=B $obs.source;$null=B $obs.contract_helper;$null=B $obs.contract_report
$live=@($obs.live_roles|ForEach-Object{$_.owner;$_.launcher})+@($obs.stage_pair)+@($obs.robustness.worker_pair)
$all=@(Get-CimInstance Win32_Process)
foreach($p in $live){$n=@($all|Where-Object ProcessId -eq $p.pid);if($n.Count -ne 1 -or $n[0].CreationDate.ToUniversalTime().Ticks -ne [long]$p.creation_utc_ticks -or $n[0].ParentProcessId -ne $p.parent -or $n[0].CommandLine -cne $p.command){throw 'Natural process transition: refresh observation; do not recover'}}
if($live.Count -ne 12 -or $null -ne $obs.primary.exit_code){throw 'Live identity/primary exit scope differs'}
$old=@($all|Where-Object {$_.ProcessId -in @(24428,40060)}|ForEach-Object{[ordered]@{pid=$_.ProcessId;parent=$_.ParentProcessId;creation_utc_ticks=$_.CreationDate.ToUniversalTime().Ticks;command=$_.CommandLine}})
$result=[ordered]@{schema='lgm.root.robustness-sues-visual1-adoption.v1';time=(Get-Date).ToString('o');accepted_with_stated_limits=$true;source=[ordered]@{path=$PSCommandPath;sha256=(Get-FileHash -LiteralPath $PSCommandPath).Hash.ToLower()};independent_review=$rb;metadata=$mb;review_source=$source;complete_source_diff=$diff;contract_review=$cb;transition=$tb;previous_robustness_adoption=$previous;newly_accepted_runs=1;newly_accepted_corrupted_conditions=30;newly_accepted_corrupted_tasks=240;newly_accepted_clean_tasks=8;accepted_robustness_runs=3;accepted_corrupted_conditions=90;accepted_corrupted_tasks=420;accepted_clean_tasks=14;pipeline_whole_jobs_adopted=3;retained_training_fits=42;retained_official_runs=42;retained_official_tasks=231;retained_transfer_runs=12;retained_transfer_tasks=66;robustness_pipeline_complete=$false;actual_unique_file_checks=$checked.Count;raw_snapshot_count=@($r.raw_evidence_bindings).Count;unique_artifact_count=$r.unique_artifact_count;bindings=@($checked.Values);current_observation=$ob;current_identity_count=$live.Count;current_identities=$live;old_pid_current_presence=$old;inherited_authority=$r.inherited_authority;training_chain=$chain;sues_protocol=$protocol;limits=@($r.limits)+@($c.limits);validator_compatibility=$r.compatibility;float32_mean_check_limit=$r.independent_mean_check;exit_limit='Original parent subprocess.run return0 plus later actual old PID identity observation; no independent launcher/interpreter dual-handle exit proof. Primary own exit code remains unknown.';review_method='Root reviewed complete derived diff, critical source and original validator/protocol, bound all new raw/production artifacts and exact training ancestry, reconciled parent record and current process identities. No old accepted attachment suite or checkpoint hashing repeated.';checkpoint_bytes_rehashed=0;scientific_execution=$false;live_state_modified=$false}
$result['independent_source_static_review']=$staticBind
$result['limits']=@($r.limits)+@($c.limits)+@($static.interpretation_limits)
$out=Join-Path $PSScriptRoot 'ROOT_SUES_VISUAL1_ADOPTION.json';$data=[Text.UTF8Encoding]::new($false).GetBytes(($result|ConvertTo-Json -Depth 35));$f=[IO.File]::Open($out,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read);try{$f.Write($data,0,$data.Length)}finally{$f.Dispose()}
[pscustomobject]@{path=$out;sha256=(Get-FileHash -LiteralPath $out).Hash.ToLower();checks=$checked.Count;identities=$live.Count;corrupted_tasks=240;clean_tasks=8}|ConvertTo-Json
