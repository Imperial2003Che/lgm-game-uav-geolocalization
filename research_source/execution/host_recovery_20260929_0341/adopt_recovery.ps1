param([Parameter(Mandatory=$true)][string]$ReviewPath,[Parameter(Mandatory=$true)][string]$ReviewSHA256)
$ErrorActionPreference='Stop'
$d=$PSScriptRoot
$e=Split-Path -Parent $d
$out=Join-Path $d 'ROOT_ADOPTION_20260929.json'
if(Test-Path -LiteralPath $out){throw 'Existing adoption must not be overwritten'}
$checked=[Collections.Generic.List[object]]::new()
function Verify([string]$Path,[string]$Expected,[long]$Bytes=-1){
 if([IO.Path]::GetExtension($Path) -in '.pt','.pth','.ckpt'){throw 'No checkpoint reads in control adoption'}
 $i=Get-Item -LiteralPath $Path;$hash=(Get-FileHash -LiteralPath $Path).Hash.ToLower()
 if($hash -cne $Expected -or ($Bytes -ge 0 -and $i.Length -ne $Bytes)){throw ('Binding mismatch: '+$Path)}
 $checked.Add([ordered]@{path=$Path;sha256=$hash;bytes=$i.Length})
}
$source=Join-Path $e 'restart_after_host_interruption_20260929_v1.ps1'
Verify $source '59deea56a6df6ee59282aa50d2612246a0b3e2cb8b9335120af8907f778fdd64'
$prepPath=Join-Path $d 'FINAL_PREPARATION_REPORT.json'
Verify $prepPath 'a959dad1b8e20456c6afcb92a918dd20e4e9c1218450ac8c55d2c857b61bcdb3'
$prep=Get-Content -LiteralPath $prepPath -Raw|ConvertFrom-Json -DateKind String
foreach($row in @($prep.target,$prep.parent_source,$prep.capture,$prep.preservation,$prep.control_review,$prep.control_harness,$prep.final_diff,$prep.comment_diff,$prep.previous_candidate,$prep.previous_preparation_report)+@($prep.source_generators)){Verify $row.path $row.sha256 $row.bytes}
$capture=Get-Content -LiteralPath $prep.capture.path -Raw|ConvertFrom-Json -DateKind String
foreach($row in $capture.files){Verify $row.backup $row.sha256 $row.bytes}
$preserved=Get-Content -LiteralPath $prep.preservation.path -Raw|ConvertFrom-Json -DateKind String
foreach($row in $preserved.files){Verify $row.backup $row.sha256 $row.bytes}
$control=Get-Content -LiteralPath $prep.control_review.path -Raw|ConvertFrom-Json -DateKind String
if($control.source_sha256 -ne $prep.target.sha256 -or -not $control.passed -or $control.passed_count -ne 49 -or $control.failed_count -ne 0){throw 'Final control report not passed'}
Verify $ReviewPath $ReviewSHA256
$review=Get-Content -LiteralPath $ReviewPath -Raw|ConvertFrom-Json -DateKind String
if($review.schema -ne 'independent-sep29-evaluation-recovery-static-review.v1' -or $review.passed -isnot [bool] -or -not $review.passed -or @($review.blocking_findings).Count){throw 'Independent final review not passed'}
Verify $review.review_script.path $review.review_script.sha256 $review.review_script.bytes
foreach($row in $review.verified_bindings){Verify $row.path $row.sha256 $row.bytes}
$rawReview=Get-Content -LiteralPath $ReviewPath -Raw
if(-not $rawReview.Contains($prep.target.sha256)){throw 'Independent review lacks exact final source binding'}
$tokens=$null;$errors=$null
[void][Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Source syntax errors'}
$processes=@(Get-CimInstance Win32_Process -Filter "Name='python.exe'"|Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine)
if($processes.Count){throw 'Python still active before actual admission'}
$boot=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString('o')
if($boot -ne $capture.last_boot_utc){throw 'New boot needs new incident'}
foreach($role in 'primary','pipeline','extensions','latest','independent'){
 if(Test-Path -LiteralPath (Join-Path $d ($role+'_launch_intent.json'))){throw 'An actual launch was already attempted'}
}
$r=[ordered]@{schema='root-evaluation-host-recovery-control-adoption.v1';adopted=$true;time=[DateTimeOffset]::Now.ToString('o');source=$prep.target;parent_source=$prep.parent_source;capture=$prep.capture;preservation=$prep.preservation;final_preparation=@{path=$prepPath;sha256='a959dad1b8e20456c6afcb92a918dd20e4e9c1218450ac8c55d2c857b61bcdb3'};independent_review=@{path=$ReviewPath;sha256=$ReviewSHA256};controls=$prep.control_review;control_case_count=49;checked_bindings=$checked.ToArray();root_read_complete_derivation_and_guards=$true;root_read_original_native_import_and_completion_paths=$true;actual_python_processes=$processes;actual_boot_utc=$boot;old_exit_codes='unknown';no_old_checkpoint_resume_proof_used=$true;training_accepted=42;eval_adoption_total=18;eval_adoption_total_is_bounded_inherited_checkpoint_basis=$true;live_launch_performed=$false;limitations='Control adoption only, not actual launch or experiment completion. Original runner retains full current-byte training/evaluation completion validation; independent artifact audits use explicitly bounded inherited checkpoint SHA. New resource admission must pass at actual start.';root_script=@{path=$PSCommandPath;sha256=(Get-FileHash -LiteralPath $PSCommandPath).Hash.ToLower()}}
[IO.File]::WriteAllText($out,($r|ConvertTo-Json -Depth 15),[Text.UTF8Encoding]::new($false))
[ordered]@{path=$out;sha256=(Get-FileHash -LiteralPath $out).Hash.ToLower();checked=$checked.Count;source=$prep.target.sha256}|ConvertTo-Json
