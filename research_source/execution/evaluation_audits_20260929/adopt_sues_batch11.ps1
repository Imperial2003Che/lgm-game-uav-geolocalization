$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$a=$PSScriptRoot
$e=Split-Path -Parent $a
$b=Join-Path $a 'sues_batch11_20260929_034356_906951'
$dest=Join-Path $a 'ROOT_SUES_BATCH11_ADOPTION_20260929.json'
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
$reportPath=Join-Path $b 'SUES_BATCH11_EVALUATION_REVIEW.json'
CheckFile $reportPath '78b187ce0388f5d8d28ebcb7139039059cf897eb574051c38ee50e72a60e6a1a'
CheckFile (Join-Path $a 'review_sues_batch11.py') 'a1e79940cb32c2ed1e97a7cc87cb9199526ece5bd88ca6674ee7a8a506fe3c65'
CheckFile (Join-Path $a 'REVIEW_SUES_BATCH11_SOURCE_DIFF.patch') '73fc764fbbfc2ef34c1824418fe925384af4b754452dddf8751d73b85c28a13b'
CheckFile (Join-Path $a 'ROOT_SUES_CONTENT_SEED1_ADOPTION_20260929.json') '7acf3313c7d3950a3da9f0fe13166b9536dd5615f5b0137eaf09a25cd621e715'
CheckFile (Join-Path $b 'DELIVERY.json') '8929dd7fb3d4910a8812fe462c8301bc6f67c20baa401a19aede6d32f11e6e94'
$r=ReadJ $reportPath
$d=ReadJ (Join-Path $b 'DELIVERY.json')
Assert ($r.passed_with_stated_inheritance_limits -and $r.accepted_evaluation_run_count -eq 11 -and $r.accepted_retrieval_task_count -eq 88 -and $r.fresh_evaluation_artifact_count -eq 132) 'Bounded result mismatch'
Assert ($r.previous_eval_adoption.sha256 -ceq '7acf3313c7d3950a3da9f0fe13166b9536dd5615f5b0137eaf09a25cd621e715' -and $r.accepted_total_evaluation_run_count_with_this_batch -eq 30 -and $r.accepted_total_retrieval_task_count_with_this_batch -eq 150) 'Prior/cumulative result mismatch'
Assert ($r.fresh_checkpoint_byte_hashes -eq 0 -and -not $r.checkpoint_loaded -and -not $r.scientific_entrypoints_executed -and -not $r.live_files_modified -and @($r.scientific_modules).Count -eq 0) 'Audit exceeded read-only scope'
Assert ($r.scope.out_of_batch_admitted -eq 0 -and -not $r.all_42_evaluations_accepted -and -not $r.paper_means_or_conclusions_created -and -not $r.evaluation_rerun_or_rank_recomputation) 'Excessive acceptance claim'
Assert (@($r.raw_evidence_bindings).Count -eq 267 -and @($r.inherited_training_acceptance_graph).Count -eq 14) 'Raw/chain count mismatch'
foreach($item in $r.raw_evidence_bindings){CheckFile $item.snapshot $item.sha256 $item.bytes}
foreach($item in $d.files){CheckFile $item.path $item.sha256 $item.bytes}
Assert ($r.original_validator_contract.source_function_sha256 -ceq 'a553c2f641453d640833f3d50d1916d4f795a360e6a75d8aaaeb983410198978' -and -not $r.original_validator_contract.function_body_changed -and $r.original_validator_contract.restored_in_finally -and -not $r.original_validator_contract.unconditional_fresh_checkpoint_validator_pass_claimed) 'Original validator scope changed'
$inheritedQueries=@($r.original_validator_hash_queries|Where-Object mode -eq 'inherited_adopted_ledger_SHA_NOT_fresh_checkpoint_hash')
$freshQueries=@($r.original_validator_hash_queries|Where-Object mode -eq 'fresh_non_checkpoint_byte_hash')
Assert ($inheritedQueries.Count -eq 11 -and $freshQueries.Count -eq 22) 'Unexpected validator hash query count'
Assert ($r.initial_inventory_not_used -and @($r.specific_training_report_authorities).Count -eq 11) 'Wrong training authority'
$authorityPins=@{
 'BATCH_COMPLETION_1611.json'='f88259d145316e76b36f63130800f2a47f91c0cbdf863fd9cabb2381bbca0bb2'
 'SUES_VISUAL_CONTENT_SEED2_COMPLETION.json'='48987b92b39e9f311fc886b16bc90d007770e693e2fa287908f02dc276220067'
 'BATCH_COMPLETION_0013.json'='d0c73981bd2679d2d569bd37715f332384f9f2e62fa14290aa23ed659fef50e1'
}
foreach($authority in $r.specific_training_report_authorities){
 $name=Split-Path -Leaf $authority.report_path
 Assert ($authorityPins.ContainsKey($name) -and $authority.report_sha256 -ceq $authorityPins[$name] -and $authority.exact_report_edge_verified_by_root42_chain) 'Specific adopted training edge missing'
 CheckFile $authority.report_path $authority.report_sha256
}
$protocol=$r.sues_official_protocol
CheckFile $protocol.manifest_binding.path $protocol.manifest_binding.sha256 $protocol.manifest_binding.bytes
Assert ($protocol.manifest_binding.sha256 -ceq 'c1386d5c746aca48bbb2793ed1ee19d6cd7330a7f5f1b27a5ec43727317ec226' -and @($protocol.train_ids).Count -eq 120 -and @($protocol.test_ids).Count -eq 80 -and ($protocol.heights -join '|') -ceq '150|200|250|300' -and $protocol.all200_gallery_ids_retained) 'SUES official split/heights mismatch'
Assert ($r.official_membership.actual_file_count -eq 40200 -and $r.official_membership.actual_file_bytes -eq 5693433493 -and $r.official_membership.canonical_protocol_membership_sha256 -ceq '1f543fb48416204dacfb5ac48b3bbf3ce4080ce164e75e7a86be748e3d798772') 'Official membership binding mismatch'
CheckFile $r.official_membership.path $r.official_membership.sha256
$targets=@('content/seed_2','content/seed_3','style/seed_1','style/seed_2','style/seed_3','visual/seed_1','visual/seed_2','visual/seed_3','visual_content/seed_1','visual_content/seed_2','visual_content/seed_3')
$oldLaunchers=@(33892,35044,23980,30140,15024,9620,34464,32728,35396,36160,35544)
Assert (@($r.runs).Count -eq 11) 'Exactly eleven new runs permitted'
for($i=0;$i -lt $targets.Count;$i++){
 $run=$r.runs[$i]
 $seed=($targets[$i] -split 'seed_')[1]
 Assert ($run.identifier -ceq ('formal_main/sues200/'+$targets[$i]+'/resnet18/dim_512') -and $run.passed_with_stated_inheritance_limits -and @($run.original_evaluation_completion_issues_with_scoped_inherited_checkpoint_SHA).Count -eq 0) 'Run completion check mismatch'
 $specific=@($r.specific_training_report_authorities|Where-Object run_identifier -eq $run.identifier)
 Assert ($specific.Count -eq 1 -and $specific[0].report_sha256 -ceq $run.inherited_checkpoint_SHA.specific_training_authority.report_sha256) 'Run training authority mismatch'
Assert (@($run.fresh_evaluation_artifact_verification).Count -eq 12) 'Wrong artifact count'
foreach($item in $run.fresh_evaluation_artifact_verification){CheckFile $item.path $item.sha256 $item.bytes;CheckFile $item.snapshot $item.sha256 $item.bytes}
$manifestPath=Join-Path $run.evaluation_dir 'evaluation_manifest.json'
$mb=@($r.raw_evidence_bindings|Where-Object path -eq $manifestPath)
Assert ($mb.Count -eq 1) 'Manifest binding missing'
CheckFile $manifestPath $mb[0].sha256 $mb[0].bytes
$manifest=ReadJ $manifestPath
Assert ($manifest.checkpoint.training_run_config_sha256 -ceq $run.run_config_sha256 -and $manifest.checkpoint.sha256 -ceq $run.inherited_checkpoint_SHA.inherited_sha256 -and $manifest.sues_manifest.sha256 -ceq $protocol.manifest_binding.sha256) 'Training/evaluation/split mismatch'
$event=$run.parent_Popen_event
Assert ($event.pid -eq $oldLaunchers[$i] -and $event.status -eq 'completed' -and $event.exit_code -eq 0 -and $event.output_dir -eq $run.evaluation_dir) 'Original parent completion missing'
$expectedCommand=@('C:\项目\.venvs\lgm-baselines\Scripts\python.exe',(Join-Path $e 'primary_path_repair_20260918\run_formal_worker.py'),'--path-compat-sha256','11de17bd611431e4471eec1b8ac072a2159fbd02e4eb2cb041b4f3b0f00012a1','evaluate','--dataset','sues200','--data-root','C:\项目\IMTMN\datasets\SUES-200','--evidence','C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\evidence_cache\sues200_clip_image_evidence.npz','--output-dir',$run.evaluation_dir,'--device','cuda','--workers','8','--seed',$seed,'--data-hash-mode','content','--amp','--eval-batch-size','128','--eval-chunk-size','128','--checkpoint',$run.inherited_checkpoint_SHA.path)
Assert (($event.command -join "`0") -ceq ($expectedCommand -join "`0")) 'Frozen evaluate command differs'
$expectedTasks=@(foreach($height in 150,200,250,300){'sues200_uav_'+$height+'m_to_satellite';'sues200_satellite_to_uav_'+$height+'m'})
Assert (@($run.tasks).Count -eq 8 -and ($run.tasks.task -join '|') -ceq ($expectedTasks -join '|')) 'Eight-task scope mismatch'
foreach($task in $run.tasks){
 Assert ($task.official_membership_and_array_alignment_passed -and $task.CSV_JSON_agree -and $task.stored_array_aggregates_agree -and -not $task.full_ranking_or_AP_from_all_positive_ranks_recomputed) 'Task consistency failure'
 if($task.task -match '^sues200_uav_'){Assert ($task.queries -eq 4000 -and $task.gallery -eq 200) 'UAV task counts'}else{Assert ($task.queries -eq 80 -and $task.gallery -eq 10000) 'Satellite task counts'}
}
}
$observer=Join-Path $e 'host_recovery_20260929_0341\observe_new_owners.ps1'
CheckFile $observer '3bfe889e149c2f97d2c2954ab4903135164c604f170aa900c1afb427086e2f97'
$observed=(& { Set-StrictMode -Off; & $observer -Stages @('primary','pipeline','extensions','latest','independent') })|ConvertFrom-Json -DateKind String
CheckFile $observed.path $observed.sha256
$snap=ReadJ $observed.path
$identityRows=@($snap.states|ForEach-Object{$_.owner;$_.launcher})+@($snap.science)
Assert ($identityRows.Count -eq 12) 'Missing current owner/science identities'
$processes=@(Get-CimInstance Win32_Process -Filter "Name='python.exe'")
foreach($row in $identityRows){$p=@($processes|Where-Object ProcessId -eq $row.pid);Assert ($p.Count -eq 1 -and $p[0].ParentProcessId -eq $row.parent -and $p[0].CommandLine -ceq $row.command -and ([DateTimeOffset]$p[0].CreationDate).UtcTicks -eq [long]$row.creation_utc_ticks) 'Current exact process changed'}
$oldFilter=($oldLaunchers|ForEach-Object{'ProcessId='+$_}) -join ' OR '
$oldCurrent=@(Get-CimInstance Win32_Process -Filter $oldFilter)
Assert ($oldCurrent.Count -eq 0) 'Completed numerical PID now present; inspect reuse'
$result=[ordered]@{
 schema='root-bounded-evaluation-adoption-v1';adopted_with_stated_inheritance_limits=$true;time_utc=[DateTimeOffset]::UtcNow.ToString('o')
 independent_report=@{path=$reportPath;sha256='78b187ce0388f5d8d28ebcb7139039059cf897eb574051c38ee50e72a60e6a1a'}
 root_script=@{path=$PSCommandPath;sha256=(Get-FileHash -LiteralPath $PSCommandPath).Hash.ToLowerInvariant()}
 root_reviewed_inherited_source_and_complete_batch_diff=$true;inherited_training_count=42;accepted_evaluation_run_count=11;accepted_retrieval_task_count=88;fresh_evaluation_artifact_count=132
 inherited_previous_eval_adoption=$r.previous_eval_adoption;accepted_total_evaluation_runs=30;accepted_total_retrieval_tasks=150
 snapshot_bindings_checked=267;root_checked_file_bindings=$checks.ToArray();runs=@($r.runs);sues_official_protocol=$protocol
 current_owner_snapshot=@{path=$observed.path;sha256=$observed.sha256};root_current_identities=$identityRows
 old_launcher_pid_numbers=$oldLaunchers;old_launcher_pid_numbers_currently_absent=$true;independent_interpreter_exit_code_proof=$false
 root_exit_evidence_basis='Original parent Popen exit0 and later actual CIM absence of eleven launcher PID numbers. No independently held exit handles or interpreter exit codes; no fabricated original creation timestamps.'
 specific_training_report_authorities=$r.specific_training_report_authorities;fresh_checkpoint_byte_hashes=0;scientific_imports=$false;scientific_entrypoints_executed=$false;live_scientific_files_changed=$false
 limitations=$r.limitations;all_evaluations_accepted=$false;paper_statistics_updated=$false
}
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($result|ConvertTo-Json -Depth 25))
$stream=[IO.File]::Open($dest,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
[ordered]@{path=$dest;sha256=(Get-FileHash -LiteralPath $dest).Hash.ToLowerInvariant();file_checks=$checks.Count;identities=$identityRows.Count;total_runs=30;total_tasks=150}|ConvertTo-Json
