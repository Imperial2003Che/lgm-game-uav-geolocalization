$ErrorActionPreference='Stop'
$ex='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$d=Join-Path $ex 'host_recovery_20260929_0341'
function Sha($p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLower()}
function Bind($p){[ordered]@{path=$p;bytes=(Get-Item -LiteralPath $p).Length;sha256=(Sha $p)}}
function ReadJ($p){Get-Content -LiteralPath $p -Raw | ConvertFrom-Json -DateKind String}
$candidate=Join-Path $ex 'restart_after_host_interruption_20260929_v1.ps1'
$parent=Join-Path $ex 'restart_after_host_interruption_20260927_v1.ps1'
if((Sha $candidate)-ne '59deea56a6df6ee59282aa50d2612246a0b3e2cb8b9335120af8907f778fdd64'){throw 'Final source changed'}
if((Sha $parent)-ne 'e4e7fcd529caff3a705273f3ec2c90d2a919c10358b3ac4c9788a6f8afe5c3bc'){throw 'Parent source changed'}
$pins=@{
 'FINAL_PREPARATION_REPORT.json'='a959dad1b8e20456c6afcb92a918dd20e4e9c1218450ac8c55d2c857b61bcdb3'
 'FINAL_SOURCE_DIFF.patch'='f56c8e251ce4a7e99cbadf2a5df54299f96962d1afc3c0444faf94d99e8d045b'
 'COMMENT_CLARIFICATION_DIFF.patch'='84e36222c3dd6a60a513f1451ad8c4609f391322f8ec9a0af50daab62ec0b199'
 'CONTROL_REVIEW_59deea56a6df_035222064.json'='7c7c95c72ffd985353a472d65826ea4637468f658f7a8262cdb253774077f963'
 'PRESERVED_INCIDENT.json'='035c8e4df1f2281097f0fa24c8442c2d9199faa2a87090be0fbcef7819fa9d9a'
}
$bindings=@(Bind $candidate;Bind $parent)
foreach($name in $pins.Keys){$p=Join-Path $d $name;if((Sha $p)-ne $pins[$name]){throw ('Changed report '+$name)};$bindings+=Bind $p}
$pres=ReadJ (Join-Path $d 'PRESERVED_INCIDENT.json')
foreach($row in $pres.files){if((Sha $row.backup)-ne $row.sha256-or (Get-Item -LiteralPath $row.backup).Length-ne $row.bytes){throw 'Recovery preservation changed'};$bindings+=Bind $row.backup}
$rootPath=Join-Path $ex 'completion_audits_20260928\ROOT_FIT_42_ADOPTION_20260928.json';$r=ReadJ $rootPath
if((Sha $rootPath)-ne 'ca54f91342f77d7d17f18a932c61681ae6f4d7c14f4ffd917c0c1594fc289e87'){throw 'ROOT42 changed'}
$bindings+=Bind $rootPath
$provenance=@($r.root_script,$r.independent_report)+@($r.verified_small_evidence_bindings)
foreach($row in $provenance){if([IO.Path]::GetExtension($row.path)-in @('.pt','.pth','.ckpt')){throw 'Checkpoint reopening forbidden'};if((Sha $row.path)-ne $row.sha256-or (Get-Item -LiteralPath $row.path).Length-ne $row.bytes){throw 'ROOT42 provenance drift'};$bindings+=Bind $row.path}
$tok=$null;$err=$null;$newAst=[Management.Automation.Language.Parser]::ParseFile($candidate,[ref]$tok,[ref]$err);if($err.Count){throw 'New parse failed'}
$oldAst=[Management.Automation.Language.Parser]::ParseFile($parent,[ref]$tok,[ref]$err);if($err.Count){throw 'Old parse failed'}
$sameFunctions=@()
foreach($name in @('Sha','Exact-Time','Save-NewJson','Argument-Tokens','Command-Tokens','Match-Controller','Check-Predecessor','Read-MemorySample')){
 $a=@($newAst.FindAll({param($n)$n-is [Management.Automation.Language.FunctionDefinitionAst]},$false)|Where-Object Name -eq $name)
 $b=@($oldAst.FindAll({param($n)$n-is [Management.Automation.Language.FunctionDefinitionAst]},$false)|Where-Object Name -eq $name)
 if($a.Count-ne 1-or $b.Count-ne 1-or $a[0].Extent.Text-cne $b[0].Extent.Text){throw ('Unexpected original control modification '+$name)}
 $sameFunctions+=$name
}
$newText=[IO.File]::ReadAllText($candidate);$oldText=[IO.File]::ReadAllText($parent)
$start='$pins = @{';$end='Save-NewJson $intentPath'
$newTail=$newText.Substring($newText.IndexOf($start),$newText.IndexOf($end)-$newText.IndexOf($start))
$oldTail=$oldText.Substring($oldText.IndexOf($start),$oldText.IndexOf($end)-$oldText.IndexOf($start))
if($newTail-cne $oldTail){throw 'Original source/resource/retirement/anti-replay/predecessor control tail changed'}
$independentControls=Join-Path $PSScriptRoot 'GUARD_CONTROLS_59deea56a6df_035334611.json';$control=ReadJ $independentControls
if((Sha $independentControls)-ne 'c678780d0a92266d62e456d13603075fa51e596e4bbcf7749b914ed737f09308'-or $control.count-ne 18-or -not $control.passed){throw 'Independent controls invalid'}
$bindings+=Bind $independentControls
$incident=Join-Path $PSScriptRoot 'INCIDENT_REVIEW_20260929_035036125.json';if((Sha $incident)-ne 'd5a61ed1ac901c5332e30242477383e0f57856b7984b758fd88c1eaa3162a47d'){throw 'Independent incident review changed'};$bindings+=Bind $incident
$report=[ordered]@{
 schema='independent-sep29-evaluation-recovery-static-review.v1';time=(Get-Date).ToString('o');passed=$true;blocking_findings=@();candidate=(Bind $candidate);parent=(Bind $parent);review_script=(Bind $PSCommandPath);verified_bindings=$bindings
 reviewer_scope='Independent complete Sep27-to-Sep29 source diff, candidate guards/tail, new sealed incident evidence, frozen primary controller and original matrix runner control paths.'
 direct_evidence_review=[ordered]@{capture_files_verified=42;exact_old_controller_identities=10;old_science_identity='Only parent-recorded PID22496 and start; creation/interpreter/exit unknown';root42_small_provenance_binding_count=$provenance.Count;preservation_file_count=@($pres.files).Count;checkpoint_content_rehashed=$false;scientific_imports=$false}
 controls=[ordered]@{unchanged_original_functions=$sameFunctions;unchanged_original_tail='From pins through ValidateOnly branch; covers scientific source hashes, 26GiB four-sample admission, zeroPython twice, exact predecessor identity twice, pending successor jobs, state hash/retirement containment, replay guards and hidden launch';independent_new_host_branch_cases=18;independent_new_host_branch_passed=18;preparer_control_cases_reported=49;preparer_cases_independently_rerun=$false;preparer_harness_inspection='Mocks source hash/save/environment/CIM/start/move/sleep and reads actual small sources; no original wrapper top-level or live ValidateOnly executed by reviewer'}
 decisions=@('Fresh Sep29 incident is pinned to exact42 preserved files and later actual boot; old running/waiting are not completion or fault attribution.','All42 training acceptance replaces obsolete75 partial-training proof. The interrupted action is exact frozen SUES content seed1 official evaluate, not train.','No weight hash substitution or scientific command change is made to live original runner. Original --stage all validates full training and evaluation gates, skips completed runs, and continues incomplete/pending evaluations.','Original native isolated import of numpy/PIL/torch/torchvision and TORCHINDUCTOR_CACHE_DIR preservation remain in the unmodified pinned controller. Runtime guard execution still required.','Original 5-role exact commands, predecessor checks, per-role intent anti-replay, state move confinement and hidden process launch remain.','No blocking issue found in final59deea56 source. Root can perform newly authorized fresh-entry validation and launch only under its real live checks.')
 limitations=@('This is independent static/control review, not an actual launch, GPU forward or scientific result.','Old interrupted process exit codes and exact cessation time/cause remain unknown.','Previously accepted42 checkpoints are inherited in this preparation review; actual original runtime checkpoint validation is unchanged and will execute at launch.','Control review is not a guarantee that host/resource state stays suitable. Root must verify actual new owner/launcher/interpreter PID, creation, complete command and parentage after each stage.')
 reviewer_harness_corrections=@('First harness rejected stale a2bb source pin before function execution when preparer clarified one comment; priorcandidate and rejection retained.','First mock emitted explicitnull for absent CIM result; corrected to empty pipeline and retained rejected harness/report.','Second mock keyed JSON Int64 PID against Int32 lookup; normalized PID keys only, preserving Int64 time ticks, and retained rejected harness/report. Final18cases pass. None were scientific failures or source changes.')
 no_recovery_or_validateonly_or_live_state_mutation=$true
}
$out=Join-Path $PSScriptRoot 'INDEPENDENT_STATIC_REVIEW.json';if(Test-Path -LiteralPath $out){throw 'Refuse replacing review'}
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($report|ConvertTo-Json -Depth 16));$fs=[IO.File]::Open($out,[IO.FileMode]::CreateNew);try{$fs.Write($bytes,0,$bytes.Length)}finally{$fs.Dispose()}
Bind $out|ConvertTo-Json
