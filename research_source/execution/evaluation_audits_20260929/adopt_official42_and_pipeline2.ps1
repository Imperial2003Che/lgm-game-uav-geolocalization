$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$a=$PSScriptRoot
$e=Split-Path -Parent $a
$dest=Join-Path $a 'ROOT_OFFICIAL42_AND_PIPELINE2_ADOPTION_20260929.json'
if(Test-Path -LiteralPath $dest){throw 'Immutable adoption exists'}
$checks=[Collections.Generic.List[object]]::new()
function J([string]$p){Get-Content -LiteralPath $p -Raw|ConvertFrom-Json -DateKind String}
function CheckFile([string]$p,[string]$sha,[long]$size=-1){
 if([IO.Path]::GetExtension($p) -in '.pt','.pth','.ckpt'){throw 'Checkpoint bytes prohibited'}
 $b=Get-Item -LiteralPath $p;$h=(Get-FileHash -LiteralPath $p).Hash.ToLower();$n=Get-Item -LiteralPath $p
 if($h -cne $sha -or ($size -ge 0 -and $b.Length -ne $size) -or $b.Length -ne $n.Length -or $b.LastWriteTimeUtc.Ticks -ne $n.LastWriteTimeUtc.Ticks){throw "Binding mismatch $p"}
 $checks.Add([ordered]@{path=$p;sha256=$h;bytes=$b.Length})
}
function Assert($v,[string]$why){if(-not $v){throw $why}}
function Tokens([string]$s){@([regex]::Matches($s,'"([^"\r\n]*)"|([^"\s]+)')|ForEach-Object{if($_.Groups[1].Success){$_.Groups[1].Value}else{$_.Groups[2].Value}})}
$priorPath=Join-Path $a 'ROOT_SUES_BATCH11_ADOPTION_20260929.json'
$priorSHA='657968ef1cf457bdc0b052c45cd0b2fd4f22dc687dc012d6f8482286e1fb052b'
CheckFile $priorPath $priorSHA
$prior=J $priorPath
Assert ($prior.adopted_with_stated_inheritance_limits -and $prior.accepted_total_evaluation_runs -eq 30 -and $prior.accepted_total_retrieval_tasks -eq 150) 'Prior scope'
$fitPath=Join-Path $e 'completion_audits_20260928\ROOT_FIT_42_ADOPTION_20260928.json'
CheckFile $fitPath 'ca54f91342f77d7d17f18a932c61681ae6f4d7c14f4ffd917c0c1594fc289e87'
$fits=J $fitPath
$priorIds=@(foreach($data in 'university1652','sues200'){foreach($variant in @('content','style','visual','visual_content','visual_style','full')){if($data -eq 'sues200' -and $variant -in 'visual_style','full'){continue};foreach($seed in 1,2,3){"formal_main/$data/$variant/seed_$seed/resnet18/dim_512"}}})
Assert ($priorIds.Count -eq 30) 'Prior explicit ID set'
$batches=@(
 @{dir='university_sensitivity3_20260929_044847_082786';report='UNIVERSITY_SENSITIVITY3_EVALUATION_REVIEW.json';sha='bf687e9a0d5eeef6ef260b034f7aaccec9fbb5dbedc2fb7b639538655616dc0e';delivery='8ff544d57010bcaa4ce8117178713097f7ab751c195c222a53895dc932f21e82';source='review_university_sensitivity3.py';sourceSHA='7e7f0745e155b353825ad0cc8d40c9d174e828aa9e8448da9dd8f4ba93958022';diff='REVIEW_UNIVERSITY_SENSITIVITY3_SOURCE_DIFF.patch';diffSHA='6d3d950771bd087d77f514f696733bce8acfec784f4db49efdd753ec3fee2a5d';dataset='university1652';runs=3;tasks=9;artifacts=21;raw=72;graph=6},
 @{dir='sues_batch9_v2_20260929_045155_947606';report='SUES_BATCH9_EVALUATION_REVIEW.json';sha='3cb6894e754bf9388519b5886491deca61e807472b7dbde9c2e93dd3ff65c074';delivery='586357eccfc2740226443d105b378bc7215d3e349d0be15d872fb4557c2f8102';source='review_sues_batch9_v2.py';sourceSHA='cd71a80c16534fa1eb12865fd7fd593d0eb11734a5f017bed5e6435801bc0365';diff='REVIEW_SUES_BATCH9_V2_SOURCE_DIFF.patch';diffSHA='76a1f47eb10159b5330e787499b9fbe0ce44a3a6a3e99c9fc080601a96f7bddd';dataset='sues200';runs=9;tasks=72;artifacts=108;raw=231;graph=17}
)
$allNew=@();$reports=@();$limits=@($prior.limitations)
foreach($batch in $batches){
 $bd=Join-Path $a $batch.dir;$rp=Join-Path $bd $batch.report
 CheckFile $rp $batch.sha;CheckFile (Join-Path $bd 'DELIVERY.json') $batch.delivery
 CheckFile (Join-Path $a $batch.source) $batch.sourceSHA;CheckFile (Join-Path $a $batch.diff) $batch.diffSHA
 $r=J $rp;$delivery=J (Join-Path $bd 'DELIVERY.json')
 Assert ($r.passed_with_stated_inheritance_limits -and $r.accepted_evaluation_run_count -eq $batch.runs -and $r.accepted_retrieval_task_count -eq $batch.tasks -and $r.fresh_evaluation_artifact_count -eq $batch.artifacts) 'New bounded scope'
 Assert ($r.previous_eval_adoption.sha256 -ceq $priorSHA -and $r.previous_eval_adoption.accepted_runs -eq 30 -and $r.previous_eval_adoption.accepted_tasks -eq 150 -and -not $r.previous_eval_adoption.old_evaluation_artifacts_rehashed) 'Wrong prior'
 Assert ($r.fresh_checkpoint_byte_hashes -eq 0 -and -not $r.checkpoint_loaded -and -not $r.scientific_entrypoints_executed -and -not $r.live_files_modified -and @($r.scientific_modules).Count -eq 0 -and -not $r.evaluation_rerun_or_rank_recomputation) 'Audit scope exceeded'
 Assert ($r.scope.out_of_batch_admitted -eq 0 -and $r.initial_inventory_not_used -and -not $r.all_42_evaluations_accepted) 'Independent scope exceeded'
 Assert ($r.raw_evidence_bindings.Count -eq $batch.raw -and $r.inherited_training_acceptance_graph.Count -eq $batch.graph) 'Binding counts'
 Assert ($delivery.report.path -ceq $rp -and $delivery.report.sha256 -ceq $batch.sha -and $delivery.source.sha256 -ceq $batch.sourceSHA) 'Delivery linkage'
 foreach($item in $r.raw_evidence_bindings){CheckFile $item.snapshot $item.sha256 $item.bytes}
 foreach($item in $delivery.files){CheckFile $item.path $item.sha256 $item.bytes}
 Assert ($r.original_validator_contract.source_function_sha256 -ceq 'a553c2f641453d640833f3d50d1916d4f795a360e6a75d8aaaeb983410198978' -and -not $r.original_validator_contract.function_body_changed -and $r.original_validator_contract.restored_in_finally -and -not $r.original_validator_contract.unconditional_fresh_checkpoint_validator_pass_claimed) 'Validator changed'
 Assert (@($r.original_validator_hash_queries|Where-Object mode -like 'inherited_*').Count -eq $batch.runs -and @($r.original_validator_hash_queries|Where-Object mode -eq 'fresh_non_checkpoint_byte_hash').Count -eq (2*$batch.runs)) 'Hash query scope'
 CheckFile $r.official_membership.path $r.official_membership.sha256
 if($batch.dataset -eq 'university1652'){
  Assert ($r.official_membership.actual_file_count -eq 93441 -and $r.official_membership.actual_file_bytes -eq 5826667007 -and $r.official_membership.canonical_protocol_membership_sha256 -ceq 'c271b8b342a9642a8ee7bd767ace06f9d934cd58a4c83885d51db2e7b94221df') 'University membership'
 }else{
  $protocol=$r.sues_official_protocol
  CheckFile $protocol.manifest_binding.path $protocol.manifest_binding.sha256 $protocol.manifest_binding.bytes
  Assert ($protocol.manifest_binding.sha256 -ceq 'c1386d5c746aca48bbb2793ed1ee19d6cd7330a7f5f1b27a5ec43727317ec226' -and $protocol.train_ids.Count -eq 120 -and $protocol.test_ids.Count -eq 80 -and ($protocol.heights -join '|') -ceq '150|200|250|300' -and $protocol.all200_gallery_ids_retained) 'SUES split'
  Assert ($r.official_membership.actual_file_count -eq 40200 -and $r.official_membership.actual_file_bytes -eq 5693433493 -and $r.official_membership.canonical_protocol_membership_sha256 -ceq '1f543fb48416204dacfb5ac48b3bbf3ce4080ce164e75e7a86be748e3d798772') 'SUES membership'
 }
 foreach($run in $r.runs){
  Assert ($run.identifier -in $fits.completed_fit_ids -and $run.identifier -notin $priorIds -and $run.identifier -notin @($allNew|ForEach-Object{$_.identifier}) -and $run.passed_with_stated_inheritance_limits -and $run.original_evaluation_completion_issues_with_scoped_inherited_checkpoint_SHA.Count -eq 0) 'Run completion'
  $cp=$run.inherited_checkpoint_SHA;$authority=$cp.specific_training_authority
  CheckFile $authority.report_path $authority.report_sha256
  Assert ($cp.inherited_sha256 -ceq $cp.specific_historical_artifact.sha256 -and $cp.inherited_sha256 -ceq $cp.inherited_ledger_record.checkpoint_sha256) 'Training authority'
  foreach($item in $run.fresh_evaluation_artifact_verification){CheckFile $item.path $item.sha256 $item.bytes;CheckFile $item.snapshot $item.sha256 $item.bytes}
  $mp=Join-Path $run.evaluation_dir 'evaluation_manifest.json';$mb=@($r.raw_evidence_bindings|Where-Object path -eq $mp)
  Assert ($mb.Count -eq 1) 'Manifest binding';CheckFile $mp $mb[0].sha256 $mb[0].bytes;$m=J $mp
  Assert ($m.payload_sha256 -ceq $run.evaluation_manifest_payload_sha256 -and $m.checkpoint.training_run_config_sha256 -ceq $run.run_config_sha256 -and $m.checkpoint.sha256 -ceq $cp.inherited_sha256) 'Manifest/config/checkpoint'
  $idparts=$run.identifier -split '/';$data=$idparts[1];$seed=$idparts[3].Substring(5)
  $rootData=if($data -eq 'university1652'){'C:\项目\IMTMN\datasets\University-1652'}else{'C:\项目\IMTMN\datasets\SUES-200'}
  $expected=@('C:\项目\.venvs\lgm-baselines\Scripts\python.exe',(Join-Path $e 'primary_path_repair_20260918\run_formal_worker.py'),'--path-compat-sha256','11de17bd611431e4471eec1b8ac072a2159fbd02e4eb2cb041b4f3b0f00012a1','evaluate','--dataset',$data,'--data-root',$rootData,'--evidence',("C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\evidence_cache\"+$data+'_clip_image_evidence.npz'),'--output-dir',$run.evaluation_dir,'--device','cuda','--workers','8','--seed',$seed,'--data-hash-mode','content','--amp','--eval-batch-size','128','--eval-chunk-size','128','--checkpoint',$cp.path)
  $ev=$run.parent_Popen_event
  Assert ($ev.status -eq 'completed' -and $ev.exit_code -eq 0 -and $ev.output_dir -ceq $run.evaluation_dir -and ($ev.command -join "\0") -ceq ($expected -join "\0")) 'Original frozen command/event'
  $taskNames=if($data -eq 'university1652'){@('university1652_drone_to_satellite','university1652_satellite_to_drone','university1652_street_to_satellite')}else{@(foreach($h in 150,200,250,300){'sues200_uav_'+$h+'m_to_satellite';'sues200_satellite_to_uav_'+$h+'m'})}
  Assert (($run.tasks.task -join '|') -ceq ($taskNames -join '|')) 'Task set'
  foreach($task in $run.tasks){
   Assert ($task.official_membership_and_array_alignment_passed -and $task.CSV_JSON_agree -and $task.stored_array_aggregates_agree -and -not $task.full_ranking_or_AP_from_all_positive_ranks_recomputed) 'Task consistency'
   if($data -eq 'sues200'){if($task.task -like 'sues200_uav*'){Assert ($task.queries -eq 4000 -and $task.gallery -eq 200) 'UAV size'}else{Assert ($task.queries -eq 80 -and $task.gallery -eq 10000) 'Satellite size'}}
  }
  $allNew+= $run
 }
 $reports+=@{path=$rp;sha256=$batch.sha;delivery_sha256=$batch.delivery;source_sha256=$batch.sourceSHA;raw_snapshot_count=$batch.raw;scope=$r.scope}
 $limits+=@($r.limitations)
}
$newExpected=@(foreach($data in 'university1652','sues200'){foreach($setting in 'resnet50/dim_512','resnet18/dim_256','resnet18/dim_1024'){"formal_sensitivity/$data/full/seed_1/$setting"}})+@(foreach($variant in 'visual_style','full'){foreach($seed in 1,2,3){"formal_main/sues200/$variant/seed_$seed/resnet18/dim_512"}})
Assert ($allNew.Count -eq 12 -and @($allNew.identifier|Sort-Object -Unique).Count -eq 12 -and @($newExpected|Where-Object {$_ -notin $allNew.identifier}).Count -eq 0) 'Fixed final12 union'
$acceptedIds=@($priorIds)+@($allNew|ForEach-Object{$_.identifier})
Assert ($acceptedIds.Count -eq 42 -and @($acceptedIds|Sort-Object -Unique).Count -eq 42 -and @($fits.completed_fit_ids|Where-Object {$_ -notin $acceptedIds}).Count -eq 0) 'All42 exact union'
Assert ((@($allNew|ForEach-Object{$_.tasks}).Count) -eq 81) 'New81 tasks'
$pd=Join-Path $e 'pipeline_transition_audit_20260929_0546'
CheckFile (Join-Path $pd 'REVIEW_FINAL.json') '40c23fe5e810ddb39afc4ff20626eb35fd870a2cdc2ae231e4f94373f6ef5811'
CheckFile (Join-Path $pd 'review_transition_final.py') 'b60a552c4d2cb51eb652c7daa068e91ad2732c851f0f2885dd9d44aad6af8ddf'
CheckFile (Join-Path $pd 'METADATA.json') '4c45bc0c75ab16883b8a146186ce85c5fe60dca67ad9db51b2bad7e1fc351433'
$pr=J (Join-Path $pd 'REVIEW_FINAL.json');$pm=J (Join-Path $pd 'METADATA.json')
Assert ($pr.status -eq 'passed_bounded_data_review_with_figure_editability_limitations' -and $pr.bindings.Count -eq 61 -and $pr.aggregate.output_artifacts_verified -eq 16 -and $pr.aggregate.independent_mean_and_sample_sd_checks -eq 792 -and $pr.figures.artifacts_verified -eq 20 -and -not $pr.figures.fully_native_editable_delivery_accepted -and -not $pr.pipeline.whole_pipeline_completed) 'Pipeline bounded result'
foreach($item in $pr.bindings){CheckFile $item.snapshot $item.sha256 $item.bytes;if($item.path -ne (Join-Path $e 'pipeline_status.json')){CheckFile $item.path $item.sha256 $item.bytes}}
foreach($item in $pm.files){CheckFile $item.path $item.sha256 $item.bytes}
$observer=Join-Path $e 'pipeline_observation_20260929_0548\observe_pipeline_phase_v2.ps1'
CheckFile $observer '2962be0d134a5c1b516a33bbf5357ba64e53c54a0b637728bbae1966cd313dae'
CheckFile (Join-Path (Split-Path -Parent $observer) 'INDEPENDENT_STATIC_REVIEW_V2.json') '77a0d7a23efde7a3c1a613c6c0bada775db13895810b941ecec4662f97d93484'
$observed=(&{Set-StrictMode -Off;& $observer})|ConvertFrom-Json -DateKind String
CheckFile $observed.report.path $observed.report.sha256 $observed.report.bytes
$snap=J $observed.report.path
$identities=@($snap.live_roles|ForEach-Object{$_.owner;$_.launcher})+@($snap.stage_pair)+@($snap.transfer.worker_pair)
Assert ($identities.Count -eq 12 -and $snap.primary.status -eq 'completed' -and $null -eq $snap.primary.exit_code) 'Current phase'
$all=@(Get-CimInstance Win32_Process)
$oldRows=@()
foreach($run in $allNew){
 $event=$run.parent_Popen_event;$now=@($all|Where-Object ProcessId -eq $event.pid)
 if($now.Count){
  Assert ($now.Count -eq 1 -and ([DateTimeOffset]$now[0].CreationDate) -gt [DateTimeOffset]::Parse($event.finished_utc) -and ((Tokens $now[0].CommandLine) -join "\0") -cne ($event.command -join "\0")) 'Old numeric PID lacks newer distinct identity proof'
  $oldRows+=@{pid=$event.pid;classification='numeric_PID_reused_after_original_parent_completed';current_parent=$now[0].ParentProcessId;current_creation=([DateTimeOffset]$now[0].CreationDate).ToString('o');current_creation_utc_ticks=([DateTimeOffset]$now[0].CreationDate).UtcTicks;current_command=$now[0].CommandLine;original_parent_finished_utc=$event.finished_utc}
 }else{$oldRows+=@{pid=$event.pid;classification='currently_absent';original_parent_finished_utc=$event.finished_utc}}
}
$result=[ordered]@{
 schema='root-final-official-evaluation-and-pipeline-two-job-adoption.v1';time_utc=[DateTimeOffset]::UtcNow.ToString('o');adopted_with_stated_inheritance_limits=$true;
 root_script=@{path=$PSCommandPath;sha256=(Get-FileHash -LiteralPath $PSCommandPath).Hash.ToLower()};
 independent_evaluation_reports=$reports;root_reviewed_complete_new_diffs_and_critical_source=$true;
 inherited_previous_eval_adoption=@{path=$priorPath;sha256=$priorSHA;runs=30;tasks=150;old_attachments_rehashed=$false};
 training_adoption=@{path=$fitPath;sha256='ca54f91342f77d7d17f18a932c61681ae6f4d7c14f4ffd917c0c1594fc289e87';fits=42};
 new_evaluation_runs=12;new_retrieval_tasks=81;fresh_evaluation_artifacts=129;new_raw_snapshot_bindings=303;accepted_total_evaluation_runs=42;accepted_total_retrieval_tasks=231;dataset_counts=@{university1652=@{runs=21;tasks=63};sues200=@{runs=21;tasks=168}};
 all_frozen_primary_official_evaluation_artifacts_accepted_with_inherited_checkpoint_limits=$true;accepted_run_identifiers=$acceptedIds;new_runs=$allNew;prior_inheritance_limits_retained=$true;
 pipeline_two_job_independent_report=@{path=(Join-Path $pd 'REVIEW_FINAL.json');sha256='40c23fe5e810ddb39afc4ff20626eb35fd870a2cdc2ae231e4f94373f6ef5811'};
 pipeline_two_jobs_adopted_for_bounded_data_consistency=$true;pipeline_stage_count_completed=2;pipeline_stage_count_total=7;pipeline_aggregate=$pr.aggregate;pipeline_figures=$pr.figures;pipeline_limits=$pr.limits;
 current_phase_snapshot=$observed.report;current_identities=$identities;old_launcher_observation=$oldRows;
 primary_exit_code_observed=$false;independent_interpreter_exit_codes_observed=$false;old_process_evidence='Original parent Popen completed exit0 plus later absence or proved newer numeric-PID reuse; no original dual-handle/interpreter exit proof';
 fresh_checkpoint_byte_hashes=0;scientific_imports=$false;scientific_execution=$false;live_scientific_files_changed=$false;paper_or_overleaf_final_updated=$false;
 limitations=$limits;root_file_binding_checks=$checks.ToArray()
}
$b=[Text.UTF8Encoding]::new($false).GetBytes(($result|ConvertTo-Json -Depth 35))
$f=[IO.File]::Open($dest,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
try{$f.Write($b,0,$b.Length)}finally{$f.Dispose()}
[ordered]@{path=$dest;sha256=(Get-FileHash -LiteralPath $dest).Hash.ToLower();file_checks=$checks.Count;new_runs=12;total_runs=42;total_tasks=231;pipeline_jobs=2;fully_editable_figures_accepted=$false;phase_snapshot=$observed.report;old_launcher_observation=$oldRows}|ConvertTo-Json -Depth 8

