$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$a=$PSScriptRoot
$e=Split-Path -Parent $a
$b=Join-Path $a 'sues_content_seed1_20260929_031015_318137'
$dest=Join-Path $a 'ROOT_SUES_CONTENT_SEED1_ADOPTION_20260929.json'
if(Test-Path -LiteralPath $dest){throw 'Adoption already exists'}
$checks=[System.Collections.Generic.List[object]]::new()
function ReadJ([string]$p){Get-Content -LiteralPath $p -Raw|ConvertFrom-Json -DateKind String}
function CheckFile([string]$p,[string]$expected,[long]$size=-1){
 if([IO.Path]::GetExtension($p) -in '.pt','.pth','.ckpt'){throw 'No checkpoint byte reads'}
 $before=Get-Item -LiteralPath $p
 $sha=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()
 $after=Get-Item -LiteralPath $p
 if($sha -cne $expected -or ($size -ge 0 -and $size -ne $before.Length) -or $before.Length -ne $after.Length -or $before.LastWriteTimeUtc.Ticks -ne $after.LastWriteTimeUtc.Ticks){throw ('File binding changed: '+$p)}
 $checks.Add([ordered]@{path=$p;bytes=$before.Length;sha256=$sha})
}
function Assert($ok,[string]$reason){if(-not $ok){throw $reason}}
$reportPath=Join-Path $b 'SUES_CONTENT_SEED1_EVALUATION_REVIEW.json'
CheckFile $reportPath 'c505521f37ce38051b47a699630277b29934ceb70b695cebad11898adbae39f2'
CheckFile (Join-Path $a 'review_sues_content_seed1.py') 'a0dbe9e3de6e7075aaa73681ca7b9a7562d6c663c4eb70f106090424b9e9057c'
CheckFile (Join-Path $a 'REVIEW_SUES_CONTENT_SEED1_SOURCE_DIFF.patch') 'fad4d9187caf59c0700034874e1bc66163af25eebaa5ef1f555b317cd0cb6cbb'
CheckFile (Join-Path $a 'ROOT_BATCH6_ADOPTION_20260929.json') 'c0735605a977e5ffcfd877e980a3773e9a747d4d7b4d68b9b682a0276f693fae'
CheckFile (Join-Path $b 'DELIVERY.json') 'e579f1915b87094b86fed1fc39e090c9aa611a17b37b2c82b1d57c78db9cd8a5'
$r=ReadJ $reportPath
$d=ReadJ (Join-Path $b 'DELIVERY.json')
Assert ($r.passed_with_stated_inheritance_limits -and $r.accepted_evaluation_run_count -eq 1 -and $r.accepted_retrieval_task_count -eq 8 -and $r.fresh_evaluation_artifact_count -eq 12) 'Bounded result mismatch'
Assert ($r.previous_eval_adoption.sha256 -ceq 'c0735605a977e5ffcfd877e980a3773e9a747d4d7b4d68b9b682a0276f693fae' -and $r.accepted_total_evaluation_run_count_with_this_batch -eq 19 -and $r.accepted_total_retrieval_task_count_with_this_batch -eq 62) 'Prior/cumulative result mismatch'
Assert ($r.fresh_checkpoint_byte_hashes -eq 0 -and -not $r.checkpoint_loaded -and -not $r.scientific_entrypoints_executed -and -not $r.live_files_modified -and @($r.scientific_modules).Count -eq 0) 'Audit exceeded read-only scope'
Assert ($r.scope.out_of_batch_admitted -eq 0 -and -not $r.all_42_evaluations_accepted -and -not $r.paper_means_or_conclusions_created -and -not $r.evaluation_rerun_or_rank_recomputation) 'Excessive acceptance claim'
Assert (@($r.raw_evidence_bindings).Count -eq 46 -and @($r.inherited_training_acceptance_graph).Count -eq 13) 'Raw/chain count mismatch'
foreach($item in $r.raw_evidence_bindings){CheckFile $item.snapshot $item.sha256 $item.bytes}
foreach($item in $d.files){CheckFile $item.path $item.sha256 $item.bytes}
Assert ($r.original_validator_contract.source_function_sha256 -ceq 'a553c2f641453d640833f3d50d1916d4f795a360e6a75d8aaaeb983410198978' -and -not $r.original_validator_contract.function_body_changed -and $r.original_validator_contract.restored_in_finally -and -not $r.original_validator_contract.unconditional_fresh_checkpoint_validator_pass_claimed) 'Original validator scope changed'
$inheritedQueries=@($r.original_validator_hash_queries|Where-Object mode -eq 'inherited_adopted_ledger_SHA_NOT_fresh_checkpoint_hash')
$freshQueries=@($r.original_validator_hash_queries|Where-Object mode -eq 'fresh_non_checkpoint_byte_hash')
Assert ($inheritedQueries.Count -eq 1 -and $freshQueries.Count -eq 2) 'Unexpected validator hash query count'
Assert ($r.initial_inventory_not_used -and @($r.specific_training_report_authorities).Count -eq 1) 'Wrong training authority'
$authority=$r.specific_training_report_authorities[0]
CheckFile $authority.report_path $authority.report_sha256
Assert ($authority.report_sha256 -ceq 'f88259d145316e76b36f63130800f2a47f91c0cbdf863fd9cabb2381bbca0bb2' -and $authority.exact_report_edge_verified_by_root42_chain) 'Specific adopted training edge missing'
$protocol=$r.sues_official_protocol
CheckFile $protocol.manifest_binding.path $protocol.manifest_binding.sha256 $protocol.manifest_binding.bytes
Assert ($protocol.manifest_binding.sha256 -ceq 'c1386d5c746aca48bbb2793ed1ee19d6cd7330a7f5f1b27a5ec43727317ec226' -and @($protocol.train_ids).Count -eq 120 -and @($protocol.test_ids).Count -eq 80 -and ($protocol.heights -join '|') -ceq '150|200|250|300' -and $protocol.all200_gallery_ids_retained) 'SUES official split/heights mismatch'
Assert ($r.official_membership.actual_file_count -eq 40200 -and $r.official_membership.actual_file_bytes -eq 5693433493 -and $r.official_membership.canonical_protocol_membership_sha256 -ceq '1f543fb48416204dacfb5ac48b3bbf3ce4080ce164e75e7a86be748e3d798772') 'Official membership binding mismatch'
CheckFile $r.official_membership.path $r.official_membership.sha256
Assert (@($r.runs).Count -eq 1) 'Only seed1 permitted'
$run=$r.runs[0]
Assert ($run.identifier -ceq 'formal_main/sues200/content/seed_1/resnet18/dim_512' -and $run.passed_with_stated_inheritance_limits -and @($run.original_evaluation_completion_issues_with_scoped_inherited_checkpoint_SHA).Count -eq 0) 'Run completion check mismatch'
Assert (@($run.fresh_evaluation_artifact_verification).Count -eq 12) 'Wrong artifact count'
foreach($item in $run.fresh_evaluation_artifact_verification){CheckFile $item.path $item.sha256 $item.bytes;CheckFile $item.snapshot $item.sha256 $item.bytes}
$manifestPath=Join-Path $run.evaluation_dir 'evaluation_manifest.json'
$mb=@($r.raw_evidence_bindings|Where-Object path -eq $manifestPath)
Assert ($mb.Count -eq 1) 'Manifest binding missing'
CheckFile $manifestPath $mb[0].sha256 $mb[0].bytes
$manifest=ReadJ $manifestPath
Assert ($manifest.checkpoint.training_run_config_sha256 -ceq $run.run_config_sha256 -and $manifest.checkpoint.sha256 -ceq $run.inherited_checkpoint_SHA.inherited_sha256 -and $manifest.sues_manifest.sha256 -ceq $protocol.manifest_binding.sha256) 'Training/evaluation/split mismatch'
$event=$run.parent_Popen_event
Assert ($event.pid -eq 20376 -and $event.status -eq 'completed' -and $event.exit_code -eq 0 -and $event.output_dir -eq $run.evaluation_dir) 'Original parent completion missing'
$expectedCommand=@('C:\项目\.venvs\lgm-baselines\Scripts\python.exe',(Join-Path $e 'primary_path_repair_20260918\run_formal_worker.py'),'--path-compat-sha256','11de17bd611431e4471eec1b8ac072a2159fbd02e4eb2cb041b4f3b0f00012a1','evaluate','--dataset','sues200','--data-root','C:\项目\IMTMN\datasets\SUES-200','--evidence','C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\evidence_cache\sues200_clip_image_evidence.npz','--output-dir',$run.evaluation_dir,'--device','cuda','--workers','8','--seed','1','--data-hash-mode','content','--amp','--eval-batch-size','128','--eval-chunk-size','128','--checkpoint',$run.inherited_checkpoint_SHA.path)
Assert (($event.command -join "`0") -ceq ($expectedCommand -join "`0")) 'Frozen evaluate command differs'
$expectedTasks=@(foreach($height in 150,200,250,300){'sues200_uav_'+$height+'m_to_satellite';'sues200_satellite_to_uav_'+$height+'m'})
Assert (@($run.tasks).Count -eq 8 -and ($run.tasks.task -join '|') -ceq ($expectedTasks -join '|')) 'Eight-task scope mismatch'
foreach($task in $run.tasks){
 Assert ($task.official_membership_and_array_alignment_passed -and $task.CSV_JSON_agree -and $task.stored_array_aggregates_agree -and -not $task.full_ranking_or_AP_from_all_positive_ranks_recomputed) 'Task consistency failure'
 if($task.task -match '^sues200_uav_'){Assert ($task.queries -eq 4000 -and $task.gallery -eq 200) 'UAV task counts'}else{Assert ($task.queries -eq 80 -and $task.gallery -eq 10000) 'Satellite task counts'}
}
$observer=Join-Path $e 'host_recovery_20260929_0341\observe_new_owners.ps1'
CheckFile $observer '3bfe889e149c2f97d2c2954ab4903135164c604f170aa900c1afb427086e2f97'
$observed=(& $observer -Stages @('primary','pipeline','extensions','latest','independent'))|ConvertFrom-Json -DateKind String
CheckFile $observed.path $observed.sha256
$snap=ReadJ $observed.path
$identityRows=@($snap.states|ForEach-Object{$_.owner;$_.launcher})+@($snap.science)
Assert ($identityRows.Count -eq 12) 'Missing current owner/science identities'
$processes=@(Get-CimInstance Win32_Process -Filter "Name='python.exe'")
foreach($row in $identityRows){$p=@($processes|Where-Object ProcessId -eq $row.pid);Assert ($p.Count -eq 1 -and $p[0].ParentProcessId -eq $row.parent -and $p[0].CommandLine -ceq $row.command -and ([DateTimeOffset]$p[0].CreationDate).UtcTicks -eq [long]$row.creation_utc_ticks) 'Current exact process changed'}
Assert (@(Get-CimInstance Win32_Process -Filter 'ProcessId=20376 OR ProcessId=11112').Count -eq 0) 'Completed numerical PID now present; inspect reuse'
$result=[ordered]@{
 schema='root-bounded-evaluation-adoption-v1';adopted_with_stated_inheritance_limits=$true;time_utc=[DateTimeOffset]::UtcNow.ToString('o')
 independent_report=@{path=$reportPath;sha256='c505521f37ce38051b47a699630277b29934ceb70b695cebad11898adbae39f2'}
 root_script=@{path=$PSCommandPath;sha256=(Get-FileHash -LiteralPath $PSCommandPath).Hash.ToLowerInvariant()}
 root_reviewed_inherited_source_and_complete_batch_diff=$true;inherited_training_count=42;accepted_evaluation_run_count=1;accepted_retrieval_task_count=8;fresh_evaluation_artifact_count=12
 inherited_previous_eval_adoption=$r.previous_eval_adoption;accepted_total_evaluation_runs=19;accepted_total_retrieval_tasks=62
 snapshot_bindings_checked=46;root_checked_file_bindings=$checks.ToArray();runs=@($run);sues_official_protocol=$protocol
 current_owner_snapshot=@{path=$observed.path;sha256=$observed.sha256};root_current_identities=$identityRows
 old_launcher20376_and_interpreter11112_currently_absent=$true;independent_interpreter_exit_code_proof=$false
 root_initial_identity_and_transition_basis='Initial pair and exact commands were observed at04:01:35; original parent Popen exit0 and later CIM absence. No independent exit handles held.'
 specific_training_report_authorities=$r.specific_training_report_authorities;fresh_checkpoint_byte_hashes=0;scientific_imports=$false;scientific_entrypoints_executed=$false;live_scientific_files_changed=$false
 limitations=$r.limitations;all_evaluations_accepted=$false;paper_statistics_updated=$false
}
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($result|ConvertTo-Json -Depth 25))
$stream=[IO.File]::Open($dest,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
[ordered]@{path=$dest;sha256=(Get-FileHash -LiteralPath $dest).Hash.ToLowerInvariant();file_checks=$checks.Count;identities=$identityRows.Count;total_runs=19;total_tasks=62}|ConvertTo-Json
