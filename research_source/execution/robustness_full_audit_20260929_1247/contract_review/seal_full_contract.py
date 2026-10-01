"""Small-file Full-specific contract binding only; no scientific imports."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
EX = HERE.parents[1]
PKG = Path(r"C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch")
FULL = PKG / "runs/formal_robustness/university1652/full/seed_1"
PREV = EX / "robustness_audit_20260929_0946/contract_review"
bindings = []


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canon(value):
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))


def desc(path, raw):
    return {"path": str(path), "bytes": len(raw), "sha256": sha(raw)}


def save(name, raw):
    target = HERE / name
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write(raw)
    return desc(target, raw)


def read(label, path, expected=None):
    path = Path(path)
    assert path.suffix.lower() in {".json", ".py", ".md", ".log"}
    assert path.stat().st_size < 2_000_000
    raw = path.read_bytes()
    if expected is not None:
        assert sha(raw) == expected, label
    snapshot = save(f"raw/{label}{path.suffix}", raw)
    bindings.append({"label": label, "source": desc(path, raw), "snapshot": snapshot})
    return json.loads(raw) if path.suffix.lower() == ".json" else raw


previous = read("previous_contract", PREV / "CONTRACT_REVIEW.json", "ebb07c9957ad985c1e9a3702ab76803db6d2918557d7076da0ac8c4277691dc7")
previous_bindings = read("previous_bindings", PREV / "SOURCE_BINDINGS.json", "36ad5a7f84d4035932cba1b468f81a86b5639fbfd6c833ae1100465d79246a81")
prior = {row["label"]: row for row in previous_bindings["bindings"]}
evaluator = read("evaluator", PKG / "experiments/run_image_level_robustness.py", prior["evaluator"]["sha256"])
validator = read("validator", PKG / "experiments/formal_robustness_common.py", prior["completion_validator"]["sha256"])
orchestrator = read("orchestrator", PKG / "experiments/run_frozen_robustness_matrix.py", prior["orchestrator"]["sha256"])
manifest = read("full_manifest", FULL / "robustness_manifest.json", "ea0cf3add63b66efa57120416937c5c894471b98859eafb2df37010299d155a5")
config = read("full_config", FULL / "run_config.json", prior["university_full_configuration"]["sha256"])
diagnostic = read("clip_clean_diagnostic", FULL / "clip_clean_reproduction_audit.json", prior["university_full_clean_clip_diagnostic"]["sha256"])
immutable = config["immutable_config"]
assert config["run_config_sha256"] == canon(immutable) == manifest["run_config_sha256"] == "c7bfc6c41ccadf0f52cf79609a76ef921bf456c5d06334b78ece284a5b4c9ce1"
assert manifest["payload_sha256"] == canon({k: v for k, v in manifest.items() if k != "payload_sha256"})
assert diagnostic["payload_sha256"] == canon({k: v for k, v in diagnostic.items() if k != "payload_sha256"})
assert manifest["checkpoint"] == immutable["checkpoint"]
assert manifest["schema_version"] == immutable["schema_version"] == diagnostic["schema_version"] == "lgm-game.image-level-robustness.v1"
assert (manifest["dataset"], manifest["variant"], manifest["status"]) == ("university1652", "full", "completed")
assert diagnostic == manifest["clip_clean_reproduction_audit"]
for filename in ("run_config.json", "clip_clean_reproduction_audit.json"):
    raw = (FULL / filename).read_bytes()
    assert manifest["artifacts"][filename] == {"sha256": sha(raw), "bytes": len(raw)}
cache_descriptor = immutable["evidence_caches"][0]
assert len(immutable["evidence_caches"]) == 1
metadata = read("small_cache_metadata_only", cache_descriptor["meta_path"], cache_descriptor["meta_sha256"])
provenance = diagnostic["clip_provenance"]
assert metadata["schema_version"] == "lgm-game.clip-image-evidence.v1"
assert metadata["cache_sha256"] == cache_descriptor["sha256"]
assert provenance["precision"] == metadata["run_configuration"]["precision"] == "fp16"
assert provenance["model_name"] == metadata["model"]["name"] == "openai/clip-vit-base-patch32"
assert provenance["revision"] == provenance["loaded_revision"] == metadata["model"]["revision_resolved"] == metadata["model"]["revision_requested"] == "3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268"
for key in ("model_config_sha256", "combined_candidates_sha256"):
    assert provenance[key] == metadata["hashes"][key]
assert provenance["probability_semantics"] == metadata["probability_semantics"]
assert provenance["transformers_version"] == immutable["environment"]["packages"]["transformers"] == metadata["software"]["transformers"] == "4.57.6"
assert provenance["local_files_only"] is True
assert diagnostic["samples"] == immutable["encoding"]["clip_clean_audit_samples"] == 64
assert diagnostic["selection_seed"] == immutable["corruption_seed"] == 20260727
assert immutable["encoding"] == {"eval_batch_size": 128, "image_workers": 8, "amp": True, "clip_precision": "match-cache", "clip_local_files_only": True, "clip_clean_audit_samples": 64}
assert manifest["clean_query_coverage"]["query_content_style_evidence_mode"] == manifest["clean_gallery_coverage"]["query_content_style_evidence_mode"] == "clean_cache"

ledger = read("ledger_snapshot", PKG / "runs/frozen_robustness_matrix_ledger.json")
assert ledger["config_sha256"] == canon(ledger["immutable_config"]) == "f1016dadeefb98d142d49ea6b46780a0abbaa4cf74727a7c7c237138c0616514"
entry = ledger["runs"]["university1652/full/seed_1"]
assert entry["status"] == "completed_and_verified" and len(entry["attempts"]) == 1
attempt = entry["attempts"][0]
assert attempt["returncode"] == 0 and attempt["completed_utc"] == "2026-09-29T11:18:40.324610+00:00"
registered = next(row for row in ledger["immutable_config"]["registered_runs"] if row["identifier"] == "university1652/full/seed_1")
assert attempt["command"] == registered["command"]
assert entry["robustness_manifest_sha256"] == "ea0cf3add63b66efa57120416937c5c894471b98859eafb2df37010299d155a5"
old_observation = read("historical_full_identity", EX / "robustness_observation_20260929_0647/snapshot_20260929_114610672/OBSERVATION.json", "46026c45b710dbdb48c5c3754f73f3a7555844254d48b9bf8b502dc083872a87")
old = old_observation["robustness"]
assert old["attempt_started_utc"] == attempt["started_utc"] and old["command"] == attempt["command"]
pair = old["worker_pair"]
assert [(r["pid"], r["parent"], r["creation_utc_ticks"]) for r in pair] == [(40820, 40780, 639262647697707190), (43872, 40820, 639262647698144490)]
assert pair[0]["command"] == subprocess.list2cmdline(attempt["command"])
assert pair[1]["command"].split('" ', 1)[1] == subprocess.list2cmdline(attempt["command"][1:])
for kind in ("stdout", "stderr"):
    log = read(f"closed_{kind}", attempt[kind]["path"], attempt[kind]["sha256"])
    assert len(log) == attempt[kind]["bytes"]
current = read("current_old_numeric_pids", HERE / "CURRENT_OLD_PID_OBSERVATION.json", "b54ac43d37f5fb5cd9d06f88d26ca93b2263d6712b2ba61b33851dea1529d23e")
identity_presence = []
for prior_row in pair:
    candidates = [r for r in current["processes"] if r["pid"] == prior_row["pid"]]
    same = [r for r in candidates if int(r["creation_utc_ticks"]) == prior_row["creation_utc_ticks"] and r["command_line"] == prior_row["command"] and r["parent_pid"] == prior_row["parent"]]
    identity_presence.append({"old_identity": prior_row, "numeric_pid_current_rows": candidates, "same_old_identity_present": bool(same)})
report = {
    "schema": "lgm-game.independent-full-robustness-contract-supplement.v1",
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "reviewer": "/root/sep29_recovery_review",
    "status": "small_file_full_contract_consistency_passed_with_inherited_limitations",
    "source_and_small_file_bindings": bindings,
    "manifest_payload_sha256": manifest["payload_sha256"],
    "run_config_sha256": manifest["run_config_sha256"],
    "config_and_diagnostic_match_previous_sealed_bytes": True,
    "manifest_embedded_diagnostic_equals_standalone": True,
    "cache_metadata_consistency_only_no_cache_npz_read": True,
    "diagnostic": diagnostic,
    "parent_completed_attempt": attempt,
    "old_identity_current_presence": identity_presence,
    "cim_observation": current,
    "parent_returncode_not_independent_dual_handle_exit_proof": True,
    "fixed_scope_not_artifact_acceptance": {"corrupted_conditions": 30, "corrupted_tasks": 90, "clean_tasks": 3, "training_seeds": [1]},
    "interpretation_limits": ["No numerical CLIP error threshold exists in producer or original completion validator", "Not bitwise cache/online parity; not full-dataset CLIP parity; diagnostic difference cause and ranking effect unknown", "Clean cached versus corrupted online evidence introduces an evidence-path difference alongside pixel corruption", "No model execution, pixel/embedding reconstruction, fresh ranking/AP reconstruction, or renewed checkpoint/cache/image content hashes", "Complete artifact-tree/per-query audit and root adoption are separate", "No three-seed robustness SD or significance conclusion"],
    "source_or_live_state_modified": False, "scientific_modules_imported": [],
    "original_validator_or_science_executed": False, "new_test_suite_run": False,
    "review_markdown": desc(HERE / "FULL_CONTRACT_REVIEW.md", (HERE / "FULL_CONTRACT_REVIEW.md").read_bytes()),
    "sealing_source": desc(Path(__file__).resolve(), Path(__file__).read_bytes()),
}
saved = save("FULL_CONTRACT_REVIEW.json", (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
print(json.dumps(saved, ensure_ascii=True))
