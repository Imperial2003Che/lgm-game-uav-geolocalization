"""Derive a mocked control suite for new Sep29 evaluation/host interfaces only."""
from pathlib import Path

ROOT = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution')
OUT = ROOT / 'host_recovery_20260929_0341'
text = (ROOT / 'host_recovery_20260927_2145' / 'review_host_controls.ps1').read_text(encoding='utf-8-sig')
text = text.replace('host_recovery_20260927_2145', 'host_recovery_20260929_0341').replace('restart_after_host_interruption_20260927_v1.ps1', 'restart_after_host_interruption_20260929_v1.ps1')
text = text.replace('$script:options.lateCheckpointDrift -and $Path -eq "C:\\项目\\LGM-GAME-Partner-Delivery-20260724\\lgm_game_pytorch\\runs\\formal_sensitivity\\university1652\\backbone_resnet50\\seed_1\\last.pt"', '$script:options.lateArtifactDrift -and $Path -eq "C:\\项目\\LGM-GAME-Partner-Delivery-20260724\\lgm_game_pytorch\\evaluations\\formal_main\\sues200\\content\\seed_1\\run.log"')
start = text.index('function Get-Content {')
end = text.index('function Get-CimInstance {', start)
text = text[:start] + r'''function Get-Content {
    param([string]$LiteralPath,[switch]$Raw)
    $content=Microsoft.PowerShell.Management\Get-Content -LiteralPath $LiteralPath -Raw
    if ($LiteralPath.EndsWith('ROOT_FIT_42_ADOPTION_20260928.json')) {
        $o=$content|ConvertFrom-Json
        switch ($script:options.adoption) {
            'not_adopted' {$o.adopted=$false}
            'string_adopted' {$o.adopted='true'}
            'wrong_count' {$o.completed_fit_count=41}
            'duplicate_ids' {$o.completed_fit_ids[1]=$o.completed_fit_ids[0]}
            'wrong_scope' {$o.completed_fit_ids[0]='formal_sensitivity/other/run'}
            'wrong_source' {$o.completed_fit_ids[0]='formal_main/sues200/absent/seed_1/resnet18/dim_512'}
        }
        return $o|ConvertTo-Json -Depth 100
    }
    if ($LiteralPath.EndsWith('host_interruption_20260929_0341\CAPTURE.json')) {
        $o=$content|ConvertFrom-Json
        switch ($script:options.capture) {
            'fabricated_exit' {$o.active|Add-Member -Force exit_code 0}
            'wrong_pid' {$o.active.pid=27308}
            'wrong_boot' {$o.last_boot_utc='2026-09-27T20:41:38.5Z'}
            'active_owners' {$o.old_science_and_controllers_absent=$false}
            'missing_file' {$o.files=@($o.files|Select-Object -Skip 1)}
            'wrong_command' {$o.active.command[4]='train'}
            'extra_command' {$o.active.command+=@('--extra','1')}
            'wrong_output' {$o.active.output_dir='C:\different'}
            'late_evaluation' {$o.active.started_utc='2026-09-29T01:00:00Z'}
        }
        return $o|ConvertTo-Json -Depth 100
    }
    if ($LiteralPath.EndsWith('previous_identity\OWNER_SNAPSHOT_20260928_144022952.json')) {
        $o=$content|ConvertFrom-Json
        switch ($script:options.identity) {
            'missing_pair' {$o.states[0].launcher=@()}
            'wrong_role' {$o.states[0].owner.command=$o.states[0].owner.command.Replace('"--role" "primary"','"--role" "latest"')}
            'creation_after_boot' {$o.states[0].owner.creation='2026-09-29T00:00:00Z'}
            'wrong_parent' {$o.states[0].owner.parent=1234}
            'inexact_ticks' {$o.states[0].owner.creation_utc_ticks=[long]$o.states[0].owner.creation_utc_ticks+1}
        }
        return $o|ConvertTo-Json -Depth 100
    }
    if ($LiteralPath -eq 'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\runs\formal_main\sues200\content\seed_1\run_manifest.json') {
        $o=$content|ConvertFrom-Json
        switch ($script:options.training) {
            'not_completed' {$o.status='running'}
            'old_epoch' {$o.epochs_completed=75}
            'wrong_checkpoint_sha' {$o.artifacts.'best.pt'.sha256='f'*64}
        }
        return $o|ConvertTo-Json -Depth 100
    }
    if ($script:predecessor -and $LiteralPath -eq (Join-Path $suiteRoot $script:defs[$script:predecessor][0])) {
        $o=$content|ConvertFrom-Json
        $o.status=$script:defs[$script:predecessor][2]
        $o.($script:defs[$script:predecessor][1])=98000
        $startField=if ($script:predecessor -eq 'primary') {'started_utc'} else {'supervisor_started_utc'}
        $o.$startField=$script:predecessorTime.ToString('o')
        $o|Add-Member -Force state_io_compatibility ([pscustomobject]@{role=$script:predecessor;sha256=$script:ioPin})
        if ($script:options.badPredecessorStatus) {$o.status='failed'}
        if ($script:options.badStateRole) {$o.state_io_compatibility.role='independent'}
        return $o|ConvertTo-Json -Depth 100
    }
    if ($LiteralPath -eq $script:oldStatePath) {
        $o=$content|ConvertFrom-Json
        if ($script:options.wrongOldStatus) {$o.status='failed'}
        if ($script:caseStage -ne 'primary') {
            if ($script:options.jobStarted) {$o.jobs[0]|Add-Member -Force started_utc '2026-09-29T03:00:00+01:00'}
            if ($script:options.nonPending) {$o.jobs[0].status='running'}
        }
        return $o|ConvertTo-Json -Depth 100
    }
    return $content
}
''' + text[end:]
text = text.replace("'2026-09-27T20:41:38.5Z'", "'2026-09-28T21:05:39.5Z'")
# Retain a genuinely wrong captured boot in the injected negative fixture.
text = text.replace("'wrong_boot' {$o.last_boot_utc='2026-09-28T21:05:39.5Z'}", "'wrong_boot' {$o.last_boot_utc='2026-09-27T20:41:38.5Z'}")
start = text.index("    if ($ClassName -eq 'Win32_Process' -and $Filter -eq 'ProcessId=27308'")
end = text.index("    if ($ClassName -eq 'Win32_PerfFormattedData_PerfOS_Memory')", start)
text = text[:start] + r'''    if ($ClassName -eq 'Win32_Process' -and $Filter -eq 'ProcessId=16412' -and $script:options.oldIdentity) {
        $old=$script:identityFixture.states[0].owner
        $created=[DateTimeOffset]$old.creation
        $command=$old.command
        switch ($script:options.oldIdentity) {
            'same_creation_other_command' {$command='python.exe unrelated.py'}
            'new_creation_same_command' {$created=[DateTimeOffset]::Parse('2026-09-28T21:06:00Z')}
            'new_creation_other_command' {$created=[DateTimeOffset]::Parse('2026-09-28T21:06:00Z');$command='python.exe unrelated.py'}
            'new_creation_no_command' {$created=[DateTimeOffset]::Parse('2026-09-28T21:06:00Z');$command=$null}
            'pre_boot_creation' {$created=[DateTimeOffset]::Parse('2026-09-28T21:04:00Z')}
        }
        return [pscustomobject]@{Name='python.exe';ProcessId=16412;CreationDate=$created;CommandLine=$command}
    }
    if ($ClassName -eq 'Win32_Process' -and $Filter -eq 'ProcessId=22496' -and $script:options.sciencePid) {
        $created=[DateTimeOffset]::Parse('2026-09-28T21:06:00Z');$command='other.exe unrelated'
        switch ($script:options.sciencePid) {
            'pre_boot' {$created=[DateTimeOffset]::Parse('2026-09-28T14:13:54Z')}
            'no_command' {$command=$null}
        }
        return [pscustomobject]@{Name='other.exe';ProcessId=22496;CreationDate=$created;CommandLine=$command}
    }
''' + text[end:]
text = text.replace("    if ($script:options.existingIntent", "    if ($script:options.unexpectedEvalManifest -and $LiteralPath.EndsWith('evaluation_manifest.json')) {return $true}\n    if ($script:options.existingIntent")
start = text.index('$script:identityFixture=')
end = text.index('$failed=@(', start)
text = text[:start] + r'''$script:identityFixture=Microsoft.PowerShell.Management\Get-Content -LiteralPath (Join-Path $suiteRoot 'host_interruption_20260929_0341\previous_identity\OWNER_SNAPSHOT_20260928_144022952.json') -Raw|ConvertFrom-Json
# New Sep29 evaluation, accepted42, ten observed controllers and unobserved evaluator interfaces.
# Existing Sep22/Sep27 unchanged tests are not recounted.
foreach ($stage in @('primary','pipeline','extensions','latest','independent')) { Run-Case ($stage+'_stale_state_valid_mock_launch') $stage @{} $true }
foreach ($boot in @('missing','changed','late_change')) {Run-Case ('host_boot_'+$boot) primary @{boot=$boot} $false}
foreach ($identity in @('missing_pair','wrong_role','creation_after_boot','wrong_parent','inexact_ticks')) {Run-Case ('snapshot_'+$identity) primary @{identity=$identity} $false}
foreach ($kind in @('same_creation','same_creation_other_command','new_creation_no_command','pre_boot_creation')) {Run-Case ('old_controller_'+$kind) pipeline @{oldIdentity=$kind} $false}
foreach ($kind in @('new_creation_same_command','new_creation_other_command')) {Run-Case ('controller_pid_reuse_'+$kind) pipeline @{oldIdentity=$kind} $true}
foreach ($kind in @('pre_boot','no_command')) {Run-Case ('unknown_science_pid_'+$kind) pipeline @{sciencePid=$kind} $false}
Run-Case 'post_boot_science_pid_reuse_no_old_exit_claim' pipeline @{sciencePid='post_boot'} $true
foreach ($kind in @('not_adopted','string_adopted','wrong_count','duplicate_ids','wrong_scope','wrong_source')) {Run-Case ('root42_'+$kind) primary @{adoption=$kind} $false}
foreach ($kind in @('fabricated_exit','wrong_pid','wrong_boot','active_owners','missing_file','wrong_command','extra_command','wrong_output','late_evaluation')) {Run-Case ('capture_'+$kind) primary @{capture=$kind} $false}
foreach ($kind in @('not_completed','old_epoch','wrong_checkpoint_sha')) {Run-Case ('training_source_'+$kind) primary @{training=$kind} $false}
Run-Case 'reject_unexpected_evaluation_manifest' primary @{unexpectedEvalManifest=$true} $false
Run-Case 'primary_partial_evaluation_drift' primary @{lateArtifactDrift=$true} $false
Run-Case 'successor_does_not_recheck_advancing_evaluation' pipeline @{lateArtifactDrift=$true} $true
Run-Case 'primary_memory_low_before_retire' primary @{memory='low'} $false
Run-Case 'primary_memory_final_low_before_retire' primary @{memory='final_low'} $false
Run-Case 'no_reuse_existing_intent' primary @{existingIntent=$true} $false
Run-Case 'no_reuse_retired_state' primary @{existingRetired=$true} $false
Run-Case 'predecessor_role_exact' pipeline @{owner='role_suffix'} $false
Run-Case 'successor_pending_only' pipeline @{nonPending=$true} $false
''' + text[end:]
text = text.replace("schema='host-recovery-new-controls-review.v1'", "schema='evaluation-host-recovery-controls-review.v1'")
text = text.replace("scope='27 new host and 75-epoch interface cases; no recount of Sep22 controls'", "scope='49 bounded Sep29 evaluation/42-fit/host controls; original Sep22/Sep27 unchanged suites are not recounted'")
with (OUT / 'review_evaluation_host_controls.ps1').open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(text)
