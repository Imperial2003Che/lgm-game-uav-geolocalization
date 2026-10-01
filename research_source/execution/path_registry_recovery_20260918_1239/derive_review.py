"""Derive the versioned PowerShell control mock; no live launch is permitted."""
import difflib
from pathlib import Path

HERE = Path(__file__).absolute().parent
ROOT = HERE.parent
SOURCE = ROOT / "path_alias_queue_20260915" / "review_recovery.ps1"
TARGET = HERE / "review_recovery.ps1"
text = source = SOURCE.read_text(encoding="utf-8")


def one(before, after):
    global text
    assert text.count(before) == 1, (before, text.count(before))
    text = text.replace(before, after)


one("$suiteIncident=Join-Path $suiteRoot 'memory_recovery_20260914_1544'", "$suiteIncident=Join-Path $suiteRoot 'path_registry_recovery_20260918_1239'")
one("$targetScript=Join-Path $suiteRoot 'restart_after_memory_incident_1544_path_compat_v1.ps1'", "$targetScript=Join-Path $suiteRoot 'restart_after_path_registry_incident_20260918_v1.ps1'")
one("primary=@('status.json','continue_formal_matrix.py'", "primary=@('status.json','continue_formal_matrix_path_compat_v1.py'")
one("'wrong_config' {$o.reports[0].config_sha256='f'*64}", "'wrong_config' {$o.reports[0].config_sha256='f'*64}\n            'wrong_archive' {$o.reports[0].file=Join-Path (Join-Path $suiteIncident 'run') 'last.pt'}")
one("if($script:caseOptions.predecessor -eq 'wrong_command'){$command='python unrelated.py'}", "if($script:caseOptions.predecessor -eq 'wrong_command'){$command='python unrelated.py'}\n        if($script:caseOptions.predecessor -eq 'old_primary'){$command=$command.Replace('continue_formal_matrix_path_compat_v1.py','continue_formal_matrix.py')}")
one("$kinds=@($script:actions|Where-Object kind -ne 'sleep'|ForEach-Object kind)", """if ($Stage -eq 'primary') {
            if ($starts[0].arguments -notlike '*continue_formal_matrix_path_compat_v1.py*--stage all --workers 8 --path-compat-sha256 11de17bd611431e4471eec1b8ac072a2159fbd02e4eb2cb041b4f3b0f00012a1*') {$ok=$false}
            if ($script:memoryCalls -ne 4 -or @($script:actions|Where-Object kind -eq 'sleep').Count -ne 2) {$ok=$false}
        }
        if (@($moves|Where-Object { $_.target -notlike '*path_registry_recovery_20260918_1239*' }).Count) {$ok=$false}
        $kinds=@($script:actions|Where-Object kind -ne 'sleep'|ForEach-Object kind)""")
one("$out=[ordered]@{schema='root-path-compat-startup-script-mock-review.v1'", """Run-Case 'primary_manifest_changed' primary @{badHash='SOURCE_MANIFEST.json'} $false
Run-Case 'primary_worker_source_changed' primary @{badHash='run_formal_worker.py'} $false
Run-Case 'primary_parent_source_changed' primary @{badHash='continue_formal_matrix_path_compat_v1.py'} $false
Run-Case 'primary_scope_helper_changed' primary @{badHash='project_paths.py'} $false
Run-Case 'sep18_preservation_manifest_changed' primary @{badHash='PRESERVED_INCIDENT.json'} $false
Run-Case 'sep18_preserved_launch_changed' primary @{badHash='previous_attempt\\primary_launch_intent.json'} $false
Run-Case 'sep18_preserved_state_changed' primary @{badHash='controllers\\status.json'} $false
Run-Case 'checkpoint_must_reference_original_archive' primary @{proof='wrong_archive'} $false
Run-Case 'pipeline_rejects_original_primary_identity' pipeline @{predecessor='old_primary'} $false

$out=[ordered]@{schema='independent-primary-path-recovery-control-mock.v1'""")
one("$reviewPath=Join-Path (Join-Path $suiteRoot 'path_alias_queue_20260915')", "$reviewPath=Join-Path $suiteIncident")
with TARGET.open("x", encoding="utf-8", newline="\n") as f:
    f.write(text)
with (HERE / "review.patch").open("x", encoding="utf-8", newline="\n") as f:
    f.write("".join(difflib.unified_diff(source.splitlines(True), text.splitlines(True), fromfile=str(SOURCE), tofile=str(TARGET))))
print(TARGET)
