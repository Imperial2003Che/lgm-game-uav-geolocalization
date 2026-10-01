"""Independent small-file binding/diff check. Does not execute producer code."""
from pathlib import Path
from datetime import datetime, timezone
import difflib
import hashlib
import json

R = Path(__file__).resolve().parent
OUT = R.parent.parent
NEW = OUT / "transfer_native_visio_candidate_20260930_0104"
OLD = OUT / "transfer_native_visio_20260930_0006"


def desc(path):
    path = Path(path)
    if path.stat().st_size > 1_000_000:
        raise ValueError(f"Unexpected large file outside this static check: {path}")
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def save_new(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


manifest_path = NEW / "CANDIDATE_SOURCE_MANIFEST.json"
manifest = read_json(manifest_path)
contract = read_json(manifest["inputContract"]["path"])
pins = {}


def collect_pins(value):
    if isinstance(value, dict):
        if {"path", "sha256", "bytes"} <= value.keys():
            key = value["path"]
            if key in pins and pins[key] != value:
                raise ValueError(f"Contradictory pin: {key}")
            pins[key] = value
        for child in value.values():
            collect_pins(child)
    elif isinstance(value, list):
        for child in value:
            collect_pins(child)


collect_pins(manifest)
collect_pins(contract)
results = []
for expected in pins.values():
    actual = desc(expected["path"])
    results.append({"expected": expected, "actual": actual, "passed": actual == expected})

old_path = OLD / "build_visio.ps1"
new_path = NEW / "build_visio_broker_candidate.ps1"
old = old_path.read_text(encoding="utf-8")
new = new_path.read_text(encoding="utf-8")
reconstructed_diff = "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile=str(old_path), tofile=str(new_path)))
stored_diff = (NEW / "PREDECESSOR_TO_CANDIDATE.patch").read_text(encoding="utf-8")
figure_marker = " foreach($f in $spec.figures){\n  $stage="
old_drawing = old[old.index(figure_marker):old.index("\n QuitOwnedApp", old.index(figure_marker))]
new_drawing = new[new.index(figure_marker):new.index("\n QuitOwnedApp", new.index(figure_marker))]
export_marker = " $stage='reopen-export';"
old_export = old[old.index(export_marker):old.index("\n $ok=$true", old.index(export_marker))]
new_export = new[new.index(export_marker):new.index("\n $ok=$true", new.index(export_marker))]
spec = read_json(contract["spec"]["path"])
checks = {
    "all_manifest_and_input_pins_match": all(row["passed"] for row in results),
    "predecessor_expected_exact_sha": desc(old_path)["sha256"] == "21b292f980dbb62e208f492ef731bfce7d0541bdabce709eaa54a19d8a01a5a6",
    "preserved_predecessor_bytes_exact": old_path.read_bytes() == (NEW / "PREDECESSOR_EXECUTED_build_visio.ps1.txt").read_bytes(),
    "complete_diff_reconstructed_exact": stored_diff == reconstructed_diff,
    "entire_drawing_block_exact": old_drawing == new_drawing,
    "drawing_block_hash_matches_contract": hashlib.sha256(new_drawing.encode()).hexdigest() == contract["drawingBlockUTF8SHA256"],
    "entire_reopen_export_block_exact": old_export == new_export,
    "contract_inputs_equal_bound_spec_inputs": contract["upstreamInputs"] == spec["inputs"],
    "contract_notes_equal_bound_spec_notes": contract["notes"] == [figure["notes"] for figure in spec["figures"]],
    "source_only_manifest_flags": manifest["COMExecuted"] is False and manifest["executionAuthorized"] is False and manifest["cleanupAuthorized"] is False,
    "one_shot_runtime_namespace_absent": not (NEW / "runtime_attempt_v1").exists(),
    "runtime_guard_is_first_action": new.startswith("param([switch]$ExecuteApproved)\n$ErrorActionPreference='Stop'\nif(!$ExecuteApproved){throw"),
}
report = {
    "schema": "independent-t3-candidate-static-bindings.v1",
    "utc": datetime.now(timezone.utc).isoformat(),
    "scope": "Small-file byte pins, independent complete-diff reconstruction, unchanged drawing/export block comparison. No producer script/checker, old 800/1247 suite, science, weights, NPZ, COM, CIM or cleanup was executed.",
    "source": desc(new_path),
    "manifest": desc(manifest_path),
    "inputContract": desc(manifest["inputContract"]["path"]),
    "checks": checks,
    "boundFiles": results,
    "passed": all(checks.values()),
    "COMExecuted": False,
    "executionApproved": False,
}
save_new(R / "STATIC_BINDINGS_REVIEW.json", report)
print(json.dumps({"passed": report["passed"], "source": report["source"], "report": desc(R / "STATIC_BINDINGS_REVIEW.json"), "checks": checks}, ensure_ascii=False))
if not report["passed"]:
    raise SystemExit(1)
