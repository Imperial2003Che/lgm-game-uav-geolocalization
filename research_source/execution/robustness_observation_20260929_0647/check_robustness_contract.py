"""Read only one sealed ledger and seven explicitly allowlisted small files.

This is metadata/source observation, never a checkpoint or scientific validator.
No project modules are imported. Canonical serialization matches the pinned
formal_robustness_common.py implementation read during observer preparation.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(r"C:\项目\LGM-GAME-Partner-Delivery-20260724")
PKG = ROOT / "lgm_game_pytorch"
SOURCES = {
    "orchestrator": (PKG / "experiments/run_frozen_robustness_matrix.py", "7d4be61b772f41853d7407c703af3ec11cbeca762947b53100f78a13266ff574"),
    "evaluator": (PKG / "experiments/run_image_level_robustness.py", "4f33b8aa96fb7d046f570bc65cce36bdb3c47b1875395b11b1565f2dd71c167a"),
    "common_validator": (PKG / "experiments/formal_robustness_common.py", "58bc704cb8c00ceac356c338978e5b3a2324f8743b3a0bff1009b90c9327d01e"),
    "formal_matrix_runner": (PKG / "experiments/run_frozen_formal_matrix.py", "f251e5088b306ddec4769fab06799008d06194bc459282f2432ac3238f4ba59f"),
    "formal_retrieval": (PKG / "lgm_game_pytorch/formal_retrieval.py", "081f327f8f83d79ab078adc61e76070c140f13e0ac9a0d8f423bfad15df59862"),
    "frozen_protocol": (ROOT / "FORMAL_EXPERIMENT_PROTOCOL.md", "29c0502b07f09d45c6fd7d4a5b582fdd9a443acc9e8b818cd9941c18a0ee34f9"),
}
CONFIG_SHA = "f1016dadeefb98d142d49ea6b46780a0abbaa4cf74727a7c7c237138c0616514"
IDS = [f"{d}/{v}/seed_1" for d in ("university1652", "sues200") for v in ("visual", "full")]


def bind(path, expected):
    if path.suffix not in (".py", ".md", ".yaml"):
        raise ValueError("Non-allowlisted file type")
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected:
        raise ValueError(f"Small source/manifest SHA mismatch: {path}")
    return {"path": str(path), "sha256": digest, "bytes": len(data)}


def main():
    snapshot = Path(sys.argv[1])
    if snapshot.name != "frozen_robustness_matrix_ledger.json" or not snapshot.parent.name.startswith("snapshot_"):
        raise ValueError("Only a sealed observer ledger snapshot may be read")
    ledger_bytes = snapshot.read_bytes()
    ledger = json.loads(ledger_bytes)
    cfg = ledger["immutable_config"]
    canonical = json.dumps(cfg, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    if digest != CONFIG_SHA or ledger["config_sha256"] != digest:
        raise ValueError("Immutable config canonical SHA mismatch")
    if ledger["schema_version"] != "lgm-game.formal-robustness-pipeline.v1" or cfg["schema_version"] != ledger["schema_version"]:
        raise ValueError("Robustness schema mismatch")
    if ledger["status"] != "running_sequential_robustness":
        raise ValueError("Robustness phase changed; not a scientific failure conclusion")
    if [r["identifier"] for r in cfg["registered_runs"]] != IDS or sorted(ledger["runs"]) != sorted(IDS):
        raise ValueError("Four-run registered scope mismatch")
    bound = []
    for key, (path, expected) in SOURCES.items():
        if cfg["source_hashes"][key] != expected:
            raise ValueError("Ledger source binding mismatch")
        bound.append({"role": key, **bind(path, expected)})
    manifest = PKG / "manifests/sues200_official_train_ids.yaml"
    manifest_sha = "c1386d5c746aca48bbb2793ed1ee19d6cd7330a7f5f1b27a5ec43727317ec226"
    if cfg["sues_manifest"]["sha256"] != manifest_sha:
        raise ValueError("SUES member manifest binding mismatch")
    bound.append({"role": "sues_manifest", **bind(manifest, manifest_sha)})
    print(json.dumps({"schema": "lgm-robustness-observer-contract.v1", "passed": True,
        "ledger_snapshot": {"path": str(snapshot), "sha256": hashlib.sha256(ledger_bytes).hexdigest(), "bytes": len(ledger_bytes)},
        "canonical_config_sha256": digest, "source_bindings": bound, "registered_ids": IDS,
        "checkpoint_or_cache_read": False, "scientific_imports": False, "scientific_acceptance": False}, ensure_ascii=True))


if __name__ == "__main__":
    main()
