"""Preserve the Sep18 failed control launch and derive a separate recovery.

Standard library only. This script never starts science, moves live states,
alters historic evidence, or copies/reloads checkpoint tensors.
"""
import argparse
import datetime
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).absolute().parent.parent
HERE = Path(__file__).absolute().parent
OLD = ROOT / "memory_recovery_20260914_1544"
TARGET = ROOT / "restart_after_path_registry_incident_20260918_v1.ps1"
SOURCE = ROOT / "restart_after_memory_incident_1544_path_compat_v1.ps1"
SOURCE_SHA = "9f9eae81e78291493cea24206fa0f8f7aed5d941428aa735e9e5caf159c4c398"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path, raw):
    with path.open("xb") as f:
        f.write(raw)


def replace_once(text, before, after):
    assert text.count(before) == 1, (before, text.count(before))
    return text.replace(before, after)


def json_new(path, data):
    write_new(path, (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary-manifest-sha256", required=True)
    args = parser.parse_args()
    assert sha(SOURCE) == SOURCE_SHA
    assert not TARGET.exists()
    manifest_path = ROOT / "primary_path_repair_20260918" / "SOURCE_MANIFEST.json"
    assert sha(manifest_path) == args.primary_manifest_sha256
    manifest = json.loads(manifest_path.read_bytes())
    for record in manifest["files"]:
        path = Path(record["path"])
        assert path.stat().st_size == record["bytes"] and sha(path) == record["sha256"]
    primary = json.loads((ROOT / "status.json").read_bytes())
    assert primary["status"] == "failed" and primary["controller_pid"] == 31168
    assert primary["launch_id"] == "20260918_123904" and primary["events"] == []
    assert primary["error"] == "RuntimeError: Frozen 36+6 run registry changed after ledger creation; refusing to continue."
    states = ["status.json", "pipeline_status.json", "extension_status.json", "latest_baseline_status.json"]
    originals = ["continue_formal_matrix.py", "supervise_pipeline.py", "supervise_extensions.py", "supervise_latest_baselines.py", "supervise_independent_comparisons.py"]
    paths = [(ROOT / name, HERE / "controllers" / name) for name in states + originals]
    paths += [(OLD / name, HERE / "previous_attempt" / name) for name in ["primary_launch_intent.json", "primary_launch.json", "primary.stdout.log", "primary.stderr.log", "retired_status.json"]]
    # The exact ledger location comes from the original preserved backup record.
    old_backup = json.loads((OLD / "backup_manifest.json").read_bytes())
    matches = [x for x in old_backup if Path(x["backup"]).name == "frozen_formal_matrix_ledger.json"]
    assert len(matches) == 1
    ledger_path = Path(matches[0]["source"])
    assert sha(ledger_path) == sha(OLD / "frozen_formal_matrix_ledger.json")
    paths.append((ledger_path, HERE / "frozen_formal_matrix_ledger.json"))
    records = []
    for source, target in paths:
        target.parent.mkdir(exist_ok=True)
        raw = source.read_bytes()
        write_new(target, raw)
        assert source.read_bytes() == raw
        records.append({"source": str(source), "backup": str(target), "bytes": len(raw), "sha256": sha(target)})
    preservation = HERE / "PRESERVED_INCIDENT.json"
    json_new(preservation, {
        "schema": "path-registry-incident-preservation.v1",
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "failed_control_launch_preserved_no_science_or_state_moves",
        "primary_launch_id": primary["launch_id"],
        "checkpoint_archive": str(OLD),
        "checkpoint_proof_sha256": sha(OLD / "checkpoint_verification.json"),
        "files": records,
    })
    source = SOURCE.read_text(encoding="utf-8")
    text = replace_once(source,
        "$incidentRoot = Join-Path $executionRoot 'memory_recovery_20260914_1544'",
        "$incidentRoot = Join-Path $executionRoot 'path_registry_recovery_20260918_1239'\n$checkpointArchiveRoot = Join-Path $executionRoot 'memory_recovery_20260914_1544'")
    text = replace_once(text, "$proofPath = Join-Path $incidentRoot 'checkpoint_verification.json'", "$proofPath = Join-Path $checkpointArchiveRoot 'checkpoint_verification.json'")
    assert text.count("(Join-Path $incidentRoot 'run')") == 2
    text = text.replace("(Join-Path $incidentRoot 'run')", "(Join-Path $checkpointArchiveRoot 'run')")
    text = replace_once(text, "primary=@('status.json','continue_formal_matrix.py'", "primary=@('status.json','continue_formal_matrix_path_compat_v1.py'")
    compatibility = f"""# Primary path adapter is explicit execution provenance; frozen science is unchanged.
$primaryManifestPath = Join-Path $executionRoot 'primary_path_repair_20260918/SOURCE_MANIFEST.json'
$primaryManifestSha = '{args.primary_manifest_sha256}'
if ((Sha $primaryManifestPath) -ne $primaryManifestSha) {{ throw 'Primary path compatibility manifest changed.' }}
$primaryManifest = Get-Content -LiteralPath $primaryManifestPath -Raw | ConvertFrom-Json
foreach ($source in $primaryManifest.files) {{
    if ((Sha $source.path) -ne $source.sha256 -or (Get-Item -LiteralPath $source.path).Length -ne $source.bytes) {{ throw ('Primary compatibility source changed: '+$source.path) }}
}}
$preservationPath = Join-Path $incidentRoot 'PRESERVED_INCIDENT.json'
if ((Sha $preservationPath) -ne '{sha(preservation)}') {{ throw 'Preserved Sep18 incident manifest changed.' }}
$preservation = Get-Content -LiteralPath $preservationPath -Raw | ConvertFrom-Json
foreach ($source in $preservation.files) {{
    if ((Sha $source.backup) -ne $source.sha256 -or (Get-Item -LiteralPath $source.backup).Length -ne $source.bytes) {{ throw ('Preserved Sep18 incident artifact changed: '+$source.backup) }}
}}

"""
    text = replace_once(text, "$definitions = @{", compatibility + "$definitions = @{")
    text = replace_once(text, "if ($Stage -eq 'primary') { $arguments += ' --stage all --workers 8' }", "if ($Stage -eq 'primary') { $arguments += ' --stage all --workers 8 --path-compat-sha256 '+$primaryManifestSha }")
    write_new(TARGET, text.encode("utf-8"))
    write_new(HERE / "recovery.patch", "".join(difflib.unified_diff(source.splitlines(True), text.splitlines(True), fromfile=SOURCE.name, tofile=TARGET.name)).encode("utf-8"))
    json_new(HERE / "RECOVERY_DERIVATION.json", {
        "source": str(SOURCE), "source_sha256": SOURCE_SHA,
        "target": str(TARGET), "target_sha256": sha(TARGET),
        "primary_manifest_sha256": args.primary_manifest_sha256,
        "preservation_sha256": sha(preservation),
        "checkpoint_archive": str(OLD),
        "status": "prepared_waiting_for_control_review_and_root_adoption",
        "real_launches": 0, "real_state_moves": 0,
    })
    print(json.dumps({"target": str(TARGET), "sha256": sha(TARGET), "preservation_sha256": sha(preservation)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
