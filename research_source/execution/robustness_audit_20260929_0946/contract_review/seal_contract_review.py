"""Seal a read-only source-contract review; standard library only.

No project modules, scientific libraries, weights, images, or cache files opened.
All output writes are exclusive creations inside this review directory.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

HERE = Path(__file__).resolve().parent
PKG = Path(r"C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch")


def canonical(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def save(name, content):
    target = HERE / name
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as out:
        out.write(content)
    return {"path": str(target), "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest()}


def save_json(name, value):
    return save(name, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


specs = [
    ("orchestrator", PKG / "experiments/run_frozen_robustness_matrix.py", "7d4be61b772f41853d7407c703af3ec11cbeca762947b53100f78a13266ff574"),
    ("evaluator", PKG / "experiments/run_image_level_robustness.py", "4f33b8aa96fb7d046f570bc65cce36bdb3c47b1875395b11b1565f2dd71c167a"),
    ("completion_validator", PKG / "experiments/formal_robustness_common.py", "58bc704cb8c00ceac356c338978e5b3a2324f8743b3a0bff1009b90c9327d01e"),
    ("formal_training_runner", PKG / "experiments/run_frozen_formal_matrix.py", "f251e5088b306ddec4769fab06799008d06194bc459282f2432ac3238f4ba59f"),
    ("formal_retrieval", PKG / "lgm_game_pytorch/formal_retrieval.py", "081f327f8f83d79ab078adc61e76070c140f13e0ac9a0d8f423bfad15df59862"),
    ("clip_probability_helper", PKG / "lgm_game_pytorch/generate_clip_image_evidence.py", "cd4002aafef9979bf601c6e80882ab6492bd6fbc774335381960d32c3e64100d"),
    ("protocol", PKG.parent / "FORMAL_EXPERIMENT_PROTOCOL.md", "29c0502b07f09d45c6fd7d4a5b582fdd9a443acc9e8b818cd9941c18a0ee34f9"),
    ("sues_split", PKG / "manifests/sues200_official_train_ids.yaml", "c1386d5c746aca48bbb2793ed1ee19d6cd7330a7f5f1b27a5ec43727317ec226"),
    ("installed_processor_default", Path(r"C:\项目\.venvs\lgm-baselines\Lib\site-packages\transformers\models\auto\image_processing_auto.py"), None),
    ("ledger_snapshot", PKG / "runs/frozen_robustness_matrix_ledger.json", None),
    ("university_visual_configuration", PKG / "runs/formal_robustness/university1652/visual/seed_1/run_config.json", None),
    ("university_full_configuration", PKG / "runs/formal_robustness/university1652/full/seed_1/run_config.json", None),
    ("university_full_clean_clip_diagnostic", PKG / "runs/formal_robustness/university1652/full/seed_1/clip_clean_reproduction_audit.json", None),
]
bindings = []
payloads = {}
for label, source, expected in specs:
    if source.suffix.lower() not in {".py", ".json", ".md", ".yaml"}:
        raise RuntimeError("unexpected source suffix")
    if source.stat().st_size > 2_000_000:
        raise RuntimeError("not a small source/configuration")
    raw = source.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if expected is not None and actual != expected:
        raise RuntimeError(f"Frozen source mismatch: {label}")
    snap = save(f"sources/{label}{source.suffix}", raw)
    bindings.append({"label": label, "source_path": str(source),
                     "bytes": len(raw), "sha256": actual,
                     "expected_sha256": expected,
                     "frozen_expected_match": expected is not None,
                     "snapshot": snap})
    if source.suffix.lower() == ".json":
        payloads[label] = json.loads(raw)

ledger = payloads["ledger_snapshot"]
assert ledger["config_sha256"] == canonical(ledger["immutable_config"]) == "f1016dadeefb98d142d49ea6b46780a0abbaa4cf74727a7c7c237138c0616514"
configs = {}
for label in ("university_visual_configuration", "university_full_configuration"):
    data = payloads[label]
    assert canonical(data["immutable_config"]) == data["run_config_sha256"]
    configs[label] = data["run_config_sha256"]
diag = payloads["university_full_clean_clip_diagnostic"]
assert diag["payload_sha256"] == canonical({k: v for k, v in diag.items() if k != "payload_sha256"})
warning_path = PKG / "runs/frozen_robustness_orchestrator_logs/university1652__full__seed_1.stderr.log"
with warning_path.open("r", encoding="utf-8") as log:
    first_line = log.readline()
assert "Using a slow image processor" in first_line
warning = save_json("OBSERVED_WARNING.json", {
    "observed_utc": datetime.now(timezone.utc).isoformat(),
    "source_path": str(warning_path), "only_first_line_read": True,
    "full_log_hash_or_closure_claim": False, "line": first_line.rstrip("\r\n")})

source_manifest = save_json("SOURCE_BINDINGS.json", {
    "schema": "lgm-game.independent-robustness-source-contract-bindings.v1",
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "bindings": bindings,
    "ledger_immutable_sha256": ledger["config_sha256"],
    "run_configuration_canonical_sha256": configs,
    "optional_diagnostic_payload_sha256": diag["payload_sha256"],
    "scientific_libraries_imported": [], "checkpoint_cache_image_bytes_read": False,
    "frozen_source_or_live_state_modified": False,
})
md_bytes = (HERE / "CONTRACT_REVIEW.md").read_bytes()
script_bytes = Path(__file__).read_bytes()
report = save_json("CONTRACT_REVIEW.json", {
    "schema": "lgm-game.independent-robustness-source-contract-review.v1",
    "reviewer": "/root/sep29_recovery_review",
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "status": "static_contract_review_completed_with_explicit_validation_gaps",
    "completion_gate": "formal_robustness_common.validate_completed_robustness",
    "run_scope": {"datasets": ["university1652", "sues200"], "variants": ["visual", "full"], "seeds": [1], "run_count": 4,
                  "corrupted_conditions_per_run": 30, "clean_reference_per_run": 1,
                  "summary_rows_per_run": {"university1652": 540, "sues200": 1440}},
    "source_bindings": source_manifest,
    "review_markdown": {"path": str(HERE / "CONTRACT_REVIEW.md"), "bytes": len(md_bytes), "sha256": hashlib.sha256(md_bytes).hexdigest()},
    "sealing_script": {"path": str(Path(__file__).resolve()), "bytes": len(script_bytes), "sha256": hashlib.sha256(script_bytes).hexdigest()},
    "critical_interpretations": [
        "Visual intentionally skips online CLIP and clean reproduction audit; visual encoder ignores supplied content/style tensors.",
        "Full corrupted queries recompute CLIP; clean queries and all galleries use cached probabilities.",
        "Full clean reproduction audit reports errors but neither caller nor completion gate imposes a numerical tolerance.",
        "Slow-processor warning is consistent with frozen no-use_fast call and installed default branch; no backend change or failure inferred.",
        "Aggregate drop is clean minus corrupted; per-query saved delta is corrupted minus clean; relative drop null if clean zero.",
        "Seed-1 descriptive results only; not a three-seed SD, pooled score, or significance test."
    ],
    "original_gate_gaps": [
        "Metric/degradation task values of non-dict type are skipped; scalar range/formula/unit and CSV/summary agreement are not checked.",
        "Per-query gate does not check full array shape/dtype, official membership/labels, rank/index bounds or cross-array arithmetic; margin arrays are not required.",
        "Listed artifact hashes do not establish an exhaustive inventory; clean condition hash/clean coverage and summary semantics are not independently checked.",
        "Checkpoint hashing is conditional on existence in the standalone common gate; accepted-training binding is additionally required.",
        "Only evaluator expected SHA is explicitly compared by the common gate; other frozen source/runtime/cache/image bindings need external verification.",
        "Persisted evidence lacks full rankings, all positive ranks, embeddings and corrupted pixels; no independent full AP/embedding reconstruction follows."
    ],
    "optional_full_clip_diagnostic": {
        "sample_count": diag["samples"], "content": diag["content"], "style": diag["style"],
        "precision": diag["clip_provenance"]["precision"], "revision": diag["clip_provenance"]["revision"],
        "bitwise_equivalence_claim": False, "threshold_pass_claim": False,
        "recomputed_here": False, "cause_of_difference_identified": False,
        "recorded_ledger_status": ledger["status"],
        "recorded_full_run_status": ledger["runs"]["university1652/full/seed_1"]["status"],
        "full_robustness_completion_claim": False,
        "warning_snapshot": warning},
    "artifact_acceptance_performed": False,
    "scientific_execution_performed": False,
    "original_validator_executed": False,
    "tests_or_new_control_simulations_run": False,
    "scientific_modules_imported": [],
    "checkpoint_cache_image_bytes_read": False,
    "live_state_or_frozen_source_mutation": False,
    "new_scientific_results": False,
})
print(json.dumps({"report": report, "source_bindings": source_manifest,
                  "snapshotted_small_sources_and_configs": len(bindings)}, ensure_ascii=False))
