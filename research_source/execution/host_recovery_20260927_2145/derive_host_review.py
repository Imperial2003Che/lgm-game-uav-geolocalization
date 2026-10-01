"""Prepare bounded, mocked host/75-epoch controls, not a launcher execution."""
from pathlib import Path

root = Path(r"C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution")
out = root / "host_recovery_20260927_2145"
text = (root / "resource_recovery_20260922_0945" / "review_recovery.ps1").read_text(encoding="utf-8-sig")
text = text.replace("resource_recovery_20260922_0945", "host_recovery_20260927_2145")
text = text.replace("restart_after_resource_incident_20260922_v1.ps1", "restart_after_host_interruption_20260927_v1.ps1")
text = text.replace("resource_incident_20260922_0945", "host_interruption_20260927_2145")
text = text.replace("$o.completed_epochs=35", "$o.completed_epochs=24")
text = text.replace("$o.resume_start_epoch=23", "$o.resume_start_epoch=24")
text = text.replace("if ($script:options.wrongOldStatus) {$o.status='running'}", "if ($script:options.wrongOldStatus) {$o.status='failed'}")
text = text.replace("'wrong_exit' {$o.active.exit_code=0}", "'fabricated_exit' {$o.active|Add-Member -Force exit_code 0}\n            'wrong_history' {$o.history_count=24}\n            'wrong_boot' {$o.last_boot_utc='2026-09-20T20:41:38.5Z'}")
anchor = "    if ($script:predecessor -and $LiteralPath -eq (Join-Path $suiteRoot $script:defs[$script:predecessor][0])) {"
insert = r'''    if ($LiteralPath.EndsWith('previous_identity\LIVE_SNAPSHOT_20260922_152741.json')) {
        $o=$content|ConvertFrom-Json
        switch ($script:options.identity) {
            'missing_pair' {$o.states[0].launcher=@()}
            'wrong_role' {$o.states[0].owner[0].CommandLine=$o.states[0].owner[0].CommandLine.Replace('"--role" "primary"','"--role" "latest"')}
            'creation_after_boot' {$o.states[0].owner[0].creation='2026-09-28T00:00:00Z'}
            'wrong_science_command' {($o.actual_python_processes|Where-Object ProcessId -eq 27308).CommandLine+=' --extra value'}
            'wrong_science_parent' {($o.actual_python_processes|Where-Object ProcessId -eq 12096).ParentProcessId=1234}
        }
        return $o|ConvertTo-Json -Depth 100
    }
'''
assert anchor in text
text = text.replace(anchor, insert + anchor)
anchor = "    if ($ClassName -eq 'Win32_PerfFormattedData_PerfOS_Memory') {"
insert = r'''    if ($ClassName -eq 'Win32_OperatingSystem') {
        $script:bootCalls++
        $boot=[DateTimeOffset]::Parse('2026-09-27T20:41:38.5Z')
        if ($script:options.boot -eq 'missing') {return}
        if ($script:options.boot -eq 'changed' -or ($script:options.boot -eq 'late_change' -and $script:bootCalls -ge 2)) {$boot=$boot.AddSeconds(1)}
        return [pscustomobject]@{LastBootUpTime=$boot}
    }
    if ($ClassName -eq 'Win32_Process' -and $Filter -eq 'ProcessId=27308' -and $script:options.oldIdentity) {
        $old=($script:identityFixture.actual_python_processes|Where-Object ProcessId -eq 27308)
        $created=[DateTimeOffset]$old.creation
        $command=$old.CommandLine
        switch ($script:options.oldIdentity) {
            'same_creation_other_command' {$command='python.exe unrelated.py'}
            'new_creation_same_command' {$created=[DateTimeOffset]::Parse('2026-09-27T20:42:00Z')}
            'new_creation_other_command' {$created=[DateTimeOffset]::Parse('2026-09-27T20:42:00Z');$command='python.exe unrelated.py'}
            'new_creation_no_command' {$created=[DateTimeOffset]::Parse('2026-09-27T20:42:00Z');$command=$null}
            'pre_boot_creation' {$created=[DateTimeOffset]::Parse('2026-09-27T20:40:00Z')}
        }
        return [pscustomobject]@{Name='python.exe';ProcessId=27308;CreationDate=$created;CommandLine=$command}
    }
'''
assert anchor in text
text = text.replace(anchor, insert + anchor)
text = text.replace("$script:checkpointHashes=0", "$script:checkpointHashes=0;$script:bootCalls=0")
start = text.index("foreach ($stage in @('primary','pipeline','extensions','latest','independent')) {")
end = text.index("$failed=@($script:results", start)
text = text[:start] + r'''$script:identityFixture=Microsoft.PowerShell.Management\Get-Content -LiteralPath (Join-Path $suiteRoot 'host_interruption_20260927_2145\previous_identity\LIVE_SNAPSHOT_20260922_152741.json') -Raw|ConvertFrom-Json
# Only the new host-interruption and changed 75-epoch interfaces are exercised.
# The Sep22 57 checks remain their separate existing report, not recounted here.
foreach ($stage in @('primary','pipeline','extensions','latest','independent')) { Run-Case ($stage+'_stale_state_valid_mock_launch') $stage @{} $true }
foreach ($boot in @('missing','changed','late_change')) {Run-Case ('host_boot_'+$boot) primary @{boot=$boot} $false}
foreach ($identity in @('missing_pair','wrong_role','creation_after_boot','wrong_science_command','wrong_science_parent')) {Run-Case ('snapshot_'+$identity) primary @{identity=$identity} $false}
foreach ($kind in @('same_creation','same_creation_other_command','new_creation_no_command','pre_boot_creation')) {Run-Case ('old_identity_'+$kind) pipeline @{oldIdentity=$kind} $false}
foreach ($kind in @('new_creation_same_command','new_creation_other_command')) {Run-Case ('pid_reuse_'+$kind) pipeline @{oldIdentity=$kind} $true}
foreach ($proof in @('wrong_epoch','wrong_resume')) {Run-Case ('reject_old_24_proof_'+$proof) primary @{proof=$proof} $false}
foreach ($capture in @('fabricated_exit','wrong_history','wrong_boot')) {Run-Case ('capture_'+$capture) primary @{capture=$capture} $false}
Run-Case 'reject_fabricated_failed_state' primary @{wrongOldStatus=$true} $false
Run-Case 'primary_live_checkpoint_must_still_match' primary @{lateCheckpointDrift=$true} $false
Run-Case 'successor_does_not_recheck_advancing_live_checkpoint' pipeline @{lateCheckpointDrift=$true} $true
''' + text[end:]
text = text.replace("resource-recovery-control-review.v1", "host-recovery-new-controls-review.v1")
text = text.replace("actual_source_and_artifact_reads=$true;scientific_imports", "actual_source_and_artifact_reads=$true;scope='27 new host and 75-epoch interface cases; no recount of Sep22 controls';scientific_imports")
with (out / 'review_host_controls.ps1').open('x', encoding='utf-8', newline='\n') as f:
    f.write(text)
print('Prepared mock-only review_host_controls.ps1; not executed.')
