"""Reuse the original mock suite against the addendum recovery, in a new report."""
from pathlib import Path
from derive_addendum import once

HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parent
source = (EXECUTION / 'memory_recovery_20260914_1544/review_startup_script.ps1').read_text(encoding='utf-8-sig')
source = once(source, "'restart_after_memory_incident_1544.ps1'", "'restart_after_memory_incident_1544_path_compat_v1.ps1'")
source = once(source, "latest=@('latest_baseline_status.json','supervise_latest_baselines.py'", "latest=@('latest_baseline_status.json','supervise_latest_baselines_path_compat_v1.py'")
source = once(source, "independent=@('independent_comparison_status.json','supervise_independent_comparisons.py'", "independent=@('independent_comparison_status.json','supervise_independent_comparisons_path_compat_v1.py'")
source = once(source, "$reviewPath=Join-Path $suiteIncident", "$reviewPath=Join-Path (Join-Path $suiteRoot 'path_alias_queue_20260915')")
source = once(source, "        $kinds=@($script:actions|Where-Object kind -ne 'sleep'|ForEach-Object kind)",
    "        if ($Stage -in @('latest','independent') -and $starts[0].arguments -notlike '*path_compat_v1.py*--addendum-sha256 0c4217fefb33d6550bda2300bc201f1c869da0b8d5ff02d45ae7af45b7ef6d70*') {$ok=$false}\n        $kinds=@($script:actions|Where-Object kind -ne 'sleep'|ForEach-Object kind)")
extra = """
Run-Case 'addendum_manifest_changed' latest @{badHash='EXECUTION_ADDENDUM.json'} $false
Run-Case 'addendum_registration_changed' independent @{badHash='REGISTRATION.json'} $false
Run-Case 'compatibility_common_source_changed' latest @{badHash='compatibility.py'} $false
Run-Case 'compatibility_parent_source_changed' independent @{badHash='supervise_independent_comparisons_path_compat_v1.py'} $false
Run-Case 'new_latest_parent_wrong_command' independent @{predecessor='wrong_command'} $false
Run-Case 'latest_validate_only_mock' latest @{} $true -Validation
Run-Case 'independent_validate_only_mock' independent @{} $true -Validation
"""
source = once(source, "$out=[ordered]@{schema=", extra + "\n$out=[ordered]@{schema=")
source = once(source, "'independent-startup-script-mock-review.v1'", "'root-path-compat-startup-script-mock-review.v1'")
target = HERE / 'review_recovery.ps1'
with target.open('x', encoding='utf-8-sig', newline='\r\n') as stream:
    stream.write(source)
print(str(target))
