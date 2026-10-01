"""Derive an unlaunched host-interruption recovery entry; standard library only."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution")
OUT = ROOT / "host_recovery_20260927_2145"
CAPTURE = ROOT / "host_interruption_20260927_2145" / "CAPTURE.json"
CAPTURE_SHA = "b572bb641a696ae216c52563f3e65e92004bc23576c331f14a0b6b1585bd69e0"
BASE = ROOT / "restart_after_resource_incident_20260922_v1.ps1"
BASE_SHA = "84746e85d393b664823cbcb737afe85ddb59c86fa4c8181751032d6d186226db"
TARGET = ROOT / "restart_after_host_interruption_20260927_v1.ps1"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

assert sha(BASE) == BASE_SHA
assert sha(CAPTURE) == CAPTURE_SHA
capture = json.loads(CAPTURE.read_text(encoding="utf-8-sig"))
assert capture["schema"] == "host-interruption-preservation.v1"
assert capture["history_count"] == 75 and len(capture["files"]) == 35
OUT.mkdir(exist_ok=True)
(OUT / "controllers").mkdir(exist_ok=True)
names = ["status.json", "pipeline_status.json", "extension_status.json", "latest_baseline_status.json", "independent_comparison_status.json", "supervise_pipeline.py", "supervise_extensions.py", "supervise_latest_baselines.py", "supervise_independent_comparisons.py"]
rows = []
for name in names:
    source = ROOT / name
    backup = OUT / "controllers" / name
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if name.endswith(".json"):
        bound = [r for r in capture["files"] if r["path"] == str(source)]
        assert len(bound) == 1 and bound[0]["sha256"] == digest and bound[0]["bytes"] == len(data)
    with backup.open("xb") as stream:
        stream.write(data)
    rows.append(dict(source=str(source), backup=str(backup), sha256=digest, bytes=len(data)))
preservation = dict(schema="host-recovery-control-preservation.v1", created_utc=datetime.now(timezone.utc).isoformat(), capture_sha256=CAPTURE_SHA, files=rows, note="Byte copies only; stored stale running/waiting fields have not been altered. No launch or exit claim.")
preservation_path = OUT / "PRESERVED_INCIDENT.json"
with preservation_path.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(preservation, stream, ensure_ascii=False, indent=2)
    stream.write("\n")

text = BASE.read_text(encoding="utf-8-sig")
text = text.replace("resource_recovery_20260922_0945", "host_recovery_20260927_2145")
text = text.replace("d9b96c3188693501834dc90394f6fd6a4676e45e08ab91e27887c1bafd901277", sha(preservation_path))
text = text.replace("Preserved resource incident", "Preserved host interruption")
for old, new in [("'running','failed'", "'running','running'"), ("'waiting_for_primary','primary_interrupted'", "'waiting_for_primary','waiting_for_primary'"), ("'waiting_for_pipeline','preceding_pipeline_interrupted'", "'waiting_for_pipeline','waiting_for_pipeline'"), ("'waiting_for_registered_extensions','preceding_controller_missing'", "'waiting_for_registered_extensions','waiting_for_registered_extensions'"), ("'waiting_for_latest_baselines','preceding_controller_missing'", "'waiting_for_latest_baselines','waiting_for_latest_baselines'")]:
    assert old in text
    text = text.replace(old, new)
start = text.index("# This is the Sep22 resource incident")
end = text.index("$checkpointProofPath =", start)
text = text[:start] + (OUT / "host_guard.fragment.ps1").read_text(encoding="utf-8-sig") + "\n" + text[end:]
text = text.replace("resource_incident_20260922_0945/CHECKPOINT_RECOVERY_PROOF.json", "host_interruption_20260927_2145/CHECKPOINT_RECOVERY_PROOF.json")
text = text.replace("34d22eb95a2cc2c5da80f342810f1a299d9a028086d2aaed06f9e968f1010f6a", "UNBOUND_75_EPOCH_PROOF_DO_NOT_LAUNCH")
old = " -or $rootAdoption.last_active_status -ne 'failed' -or $rootAdoption.last_active_complete_epochs -ne 24 -or [IO.Path]::GetFullPath($rootAdoption.last_active_run) -ne $runRoot"
assert old in text
text = text.replace(old, "")
text = text.replace("Root adoption does not match 36 completed main fits and this incomplete 24-epoch run.", "Root adoption does not verify exactly 36 completed main fits; its historical partial checkpoint is not reused.")
text = text.replace("resource-incident-checkpoint-recovery-proof.v1", "host-interruption-checkpoint-recovery-proof.v1")
text = text.replace("verified_complete_epoch_24", "verified_complete_epoch_75")
text = text.replace("$checkpointProof.completed_epochs -ne 24", "$checkpointProof.completed_epochs -ne 75")
text = text.replace("$checkpointProof.epoch_zero_based -ne 23", "$checkpointProof.epoch_zero_based -ne 74")
text = text.replace("$checkpointProof.resume_start_epoch -ne 24", "$checkpointProof.resume_start_epoch -ne 75")
text = text.replace("$proof.epoch_zero_based -ne 23", "$proof.epoch_zero_based -ne 74")
text = text.replace("$proof.completed_epochs -ne 24", "$proof.completed_epochs -ne 75")
text = text.replace("this exact latest complete 24-epoch run", "this exact latest complete 75-epoch run")
text = text.replace("after the resource incident was captured", "after the host interruption was captured")
old = """    $oldOwner = Get-CimInstance Win32_Process -Filter ('ProcessId='+$old.($current[2]))
    if ($oldOwner) {
        $oldEnded = if ($old.stopped_utc) { Exact-Time $old.stopped_utc } else { Exact-Time $old.finished_utc }
        if (([DateTimeOffset]$oldOwner.CreationDate) -le $oldEnded) { throw 'Old controller may still be alive.' }
    }
"""
assert old in text
text = text.replace(old, "    # Assert-HostInterruption verifies actual prior PID identities; no exit code or stopped time is invented.\n")
text = text.replace("State differs from the preserved failed incident.", "State differs from the preserved stale host-interruption state.")
text = text.replace("if ($ValidateOnly) {", "$hostIdentityFinal = Assert-HostInterruption\nif ($ValidateOnly) {")
text = text.replace("incident_capture_sha256=$captureSha;io_manifest_sha256", "incident_capture_sha256=$captureSha;host_interruption=$hostIdentityFinal;io_manifest_sha256")
with TARGET.open("x", encoding="utf-8", newline="\n") as stream:
    stream.write(text)
import difflib
diff = ''.join(difflib.unified_diff(BASE.read_text(encoding="utf-8-sig").splitlines(keepends=True), text.splitlines(keepends=True), fromfile=BASE.name, tofile=TARGET.name))
with (OUT / "SOURCE_DIFF.patch").open("x", encoding="utf-8", newline="\n") as stream:
    stream.write(diff)
print(json.dumps(dict(target=str(TARGET), source_sha256=sha(TARGET), preservation_sha256=sha(preservation_path), proof_binding="unbound; hard reject", controllers_copied=len(rows)), ensure_ascii=False))
