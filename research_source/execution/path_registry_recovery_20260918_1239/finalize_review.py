"""Read-only recovery derivation and artifact verification; writes new review."""
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).absolute().parent
ROOT = HERE.parent
OLD = ROOT / "memory_recovery_20260914_1544"
source = ROOT / "restart_after_memory_incident_1544_path_compat_v1.ps1"
target = ROOT / "restart_after_path_registry_incident_20260918_v1.ps1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


before = source.read_text(encoding="utf-8")
after = target.read_text(encoding="utf-8")
reconstructed = after.replace(
    "$incidentRoot = Join-Path $executionRoot 'path_registry_recovery_20260918_1239'\n$checkpointArchiveRoot = Join-Path $executionRoot 'memory_recovery_20260914_1544'",
    "$incidentRoot = Join-Path $executionRoot 'memory_recovery_20260914_1544'")
start = reconstructed.index("# Primary path adapter is explicit execution provenance;")
end = reconstructed.index("$definitions = @{", start)
reconstructed = reconstructed[:start] + reconstructed[end:]
reconstructed = reconstructed.replace("primary=@('status.json','continue_formal_matrix_path_compat_v1.py'", "primary=@('status.json','continue_formal_matrix.py'")
reconstructed = reconstructed.replace("$checkpointArchiveRoot 'checkpoint_verification.json'", "$incidentRoot 'checkpoint_verification.json'")
reconstructed = reconstructed.replace("$checkpointArchiveRoot 'run'", "$incidentRoot 'run'")
reconstructed = reconstructed.replace("' --stage all --workers 8 --path-compat-sha256 '+$primaryManifestSha", "' --stage all --workers 8'")
assert reconstructed == before, "Unexplained recovery control changes"
preservation = HERE / "PRESERVED_INCIDENT.json"
records = json.loads(preservation.read_bytes())["files"]
assert len(records) == 15
for record in records:
    backup = Path(record["backup"])
    assert backup.stat().st_size == record["bytes"] and sha(backup) == record["sha256"]
    assert sha(Path(record["source"])) == record["sha256"], record["source"]
assert sha(ROOT / "status.json") == "6c1fde1739ea949fd4978543882dd9073d8113c610d4dc6eb166eb8e5a47cee0"
assert not (ROOT / "independent_comparison_status.json").exists()
assert all(not (HERE / (stage + suffix)).exists() for stage in ["primary", "pipeline", "extensions", "latest", "independent"] for suffix in ["_launch.json", "_launch_intent.json", ".stdout.log", ".stderr.log"])
assert not list(HERE.glob("retired_*.json"))
assert not (HERE / "run").exists()
assert sha(OLD / "checkpoint_verification.json") == "51e555495e325fb6465f81af580919196998baee7a535f3c5ad9380cf5fa8a5b"
mock_path = HERE / "STARTUP_SCRIPT_MOCK_1e98d56dfd96_011138147.json"
mock = json.loads(mock_path.read_bytes())
assert mock["target_sha256"] == sha(target) and mock["count"] == mock["passed"] == 52 and mock["failed"] == 0
report = {
    "schema": "independent-primary-path-recovery-review.v1",
    "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "control_review_passed_pending_root_adoption_and_live_resource_check",
    "source": str(source), "source_sha256": sha(source),
    "target": str(target), "target_sha256": sha(target),
    "primary_manifest_sha256": sha(ROOT / "primary_path_repair_20260918" / "SOURCE_MANIFEST.json"),
    "preservation_sha256": sha(preservation),
    "preserved_file_count": len(records),
    "reconstructed_original_script_exact": True,
    "original_failed_launch_preserved": True,
    "current_primary_failed_sha256": sha(ROOT / "status.json"),
    "checkpoint_archive": str(OLD),
    "checkpoint_proof_sha256": sha(OLD / "checkpoint_verification.json"),
    "mock_report": str(mock_path), "mock_report_sha256": sha(mock_path),
    "mock_checks_passed": 52,
    "initial_mock_failure": "One injected manifest hash did not match the Windows backslash path because the harness used a slash suffix; fixed only the harness suffix. Initial 51/52 report and harness retained.",
    "live_validate_only_executed": False,
    "real_process_starts": 0, "real_state_moves": 0, "scientific_imports": 0,
    "root_adoption_required": True,
    "limitations": ["Control mocks cannot establish scientific path-adapter correctness or successful resumed training.", "Root must finish adapter review and execute actual four-sample >=26 GiB ValidateOnly before a launch.", "Every launch remains one attempt: preserve intent, retired state and logs if it fails."]
}
with (HERE / "CONTROL_REVIEW.json").open("x", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(json.dumps({"report": str(HERE / "CONTROL_REVIEW.json"), "sha256": sha(HERE / "CONTROL_REVIEW.json"), "status": report["status"]}, ensure_ascii=False))
