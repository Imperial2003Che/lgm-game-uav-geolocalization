$ErrorActionPreference='Stop'
$ex='C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
function ReadJ($p){Get-Content -LiteralPath $p -Raw|ConvertFrom-Json -DateKind String}
function Digest($p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$p;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
$obsPath=Join-Path $ex 'host_boot_change_20260930_0008\OBSERVATION.json'
$obs=ReadJ $obsPath
if((Digest $obsPath).sha256 -ne 'e0d188f5a0b0737acf5d121a4d6255ad228bd51a4385d67945dc4fe68eb4b87e'){throw 'Observation SHA differs from requested record'}
$prior=ReadJ $obs.prior_reference.path
$contract=ReadJ $obs.contract.path
$oldPath=Join-Path $ex 'host_recovery_20260929_0341\ROOT_ACTUAL_LAUNCH_20260929.json'
$old=ReadJ $oldPath
$oldPipeline=@($old.states|Where-Object role -eq 'pipeline')[0]
$earlierPath=Join-Path $ex 'efficiency_incident_20260929_1448\observation_20260929_233721230\OBSERVATION.json'
$earlier=ReadJ $earlierPath
$candidatePath=Join-Path $ex 't6_recovery_preparation_20260929_1548\pipeline_recovery_candidate.py'
$candidateText=Get-Content -LiteralPath $candidatePath -Raw
$observerText=Get-Content -LiteralPath $obs.source.path -Raw
foreach($bound in @($obs.source,$obs.prior_reference,$obs.contract,$obs.old_pipeline_launch)){$now=Digest $bound.path;if($now.sha256 -ne $bound.sha256 -or $now.bytes -ne $bound.bytes){throw ('Observed source mismatch '+$bound.path)}}
$checks=@();foreach($row in $obs.files){$previous=@($prior.files|Where-Object path -eq $row.path);if($previous.Count -ne 1){throw 'Prior file map mismatch'};$now=Digest $row.path;if($now.bytes -ne $row.bytes -or $now.sha256 -ne $row.sha256 -or $row.sha256 -ne $previous[0].sha256 -or $row.bytes -ne $previous[0].bytes){throw ('State/log changed: '+$row.path)};$checks+=([ordered]@{path=$row.path;bytes=$row.bytes;sha256=$row.sha256;matches_prior_and_observation_and_current_bytes=$true})}
if($checks.Count -ne 16){throw 'Expected16 small state/log files'}
$currentA=@($obs.first.matches|Where-Object pid -eq 14420)[0];$currentB=@($obs.second.matches|Where-Object pid -eq 14420)[0]
if($currentA.name -ne 'AppActions.exe' -or $currentB.name -ne 'AppActions.exe' -or $currentA.creation_utc_ticks -ne $currentB.creation_utc_ticks){throw 'Current numeric PID observation mismatch'}
if($oldPipeline.owner.pid -ne 14420 -or $oldPipeline.owner.parent -ne 29784 -or [string]$oldPipeline.owner.creation_utc_ticks -ne '639262477073457420'){throw 'Historical pipeline identity mismatch'}
if($contract.host_boot_utc_ticks -ne '639262263395000000' -or $obs.first.boot_utc_ticks -ne '639263179115000000' -or $obs.second.boot_utc_ticks -ne '639263179115000000' -or $obs.contract_boot_matches_current){throw 'Boot identity mismatch'}
$earlierTicks=([DateTimeOffset]::Parse($earlier.host_boot_utc)).UtcTicks.ToString();if($earlierTicks -ne $obs.first.boot_utc_ticks){throw 'Earlier2337 did not record same boot'}
$guard='require(snapshot[''host_boot_utc_ticks''] == contract[''host_boot_utc_ticks''],'
if(-not $candidateText.Contains($guard) -or -not $candidateText.Contains('Host restarted after captured incident; a new incident review is required')){throw 'Candidate boot guard missing'}
$sources=@($obsPath,$obs.source.path,$obs.prior_reference.path,$obs.contract.path,$obs.old_pipeline_launch.path,$oldPath,$earlierPath,$candidatePath)|Select-Object -Unique
$report=[ordered]@{schema='independent-static-host-boot-review.v1';utc=[DateTime]::UtcNow.ToString('o');passed_with_stated_scope=$true;observation_digest=Digest $obsPath;sources=@($sources|ForEach-Object {Digest $_});state_log_bindings=$checks;state_log_count=$checks.Count;new_boot_utc=$obs.first.boot_utc;new_boot_utc_ticks=$obs.first.boot_utc_ticks;old_contract_boot_utc=$contract.host_boot_utc;old_contract_boot_utc_ticks=$contract.host_boot_utc_ticks;earlier_2337_record=[ordered]@{time=$earlier.time;host_boot_utc=$earlier.host_boot_utc;same_new_boot=$true};historical_pipeline_owner=$oldPipeline.owner;current_numeric_pid_14420=$currentA;second_current_numeric_pid_14420=$currentB;pid_reuse_identity_conclusion='Same PID number, different program/full command/parent/creation ticks; not the historical pipeline owner.';current_parent_limit='svchost.exe command_line is null; current numeric parent observation is not historical lineage proof.';candidate_boot_guard=[ordered]@{source=$candidatePath;condition=$guard;rejection_message='Host restarted after captured incident; a new incident review is required';runtime_attempted=$false};interpretation='Host restarted after science was already stopped. Existing16 state/log bytes unchanged; no new scientific failure, completion, captured exit code or restart authorization is inferred. Existing boot-bound source adoption/release prerequisites cannot authorize launch on the new boot.';selector_limit='Root observer selects explicit17 historical PIDs, VISIO.EXE and listed Python/PowerShell scientific-command regexes. Regex does not explicitly include run_controller_with_state_retry_v2.py, so wrapper detection outside historical PID numbers is not exhaustive. No new CIM query performed by this reviewer.';actions_not_performed=@('No launch/ValidateOnly/recovery/native probe/COM/GPU/scientific execution','No release or new runner preparation','No lock acquisition or live state modification','No old root/contract/source rewriting or old recovery replay','No exit-code inference from process absence','No recursive checking of old root history')}
$dest=Join-Path $PSScriptRoot 'REVIEW.json';if(Test-Path -LiteralPath $dest){throw 'REVIEW already exists'};[IO.File]::WriteAllText($dest,($report|ConvertTo-Json -Depth 14),[Text.UTF8Encoding]::new($false))
[ordered]@{review=Digest $dest;sources=$sources.Count;unchanged_state_logs=$checks.Count;recorded_boot=$report.new_boot_utc;earlier2337_same_boot=$true}|ConvertTo-Json -Depth 4