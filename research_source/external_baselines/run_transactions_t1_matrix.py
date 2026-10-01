#!/usr/bin/env python3
"""Audit, fit, or officially evaluate the seven Transactions T1 baselines."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from external_baselines.fetch_and_verify_sources import IntegrityError, sha256_file
from external_baselines.mccg_adapter import (
    assert_fit_environment_has_no_test_roots as assert_mccg_no_test_roots,
    validate_completed_fit as validate_mccg_fit,
)
from external_baselines.official_descriptor_evaluation import (
    ALL_FITS_GATE_SCHEMA,
    TEST_INVENTORY_GATE_SCHEMA,
    scan_sues200_official_test,
    scan_university1652_official_test,
    validate_completed_evaluation,
    validate_sues200_test_inventory,
    validate_university1652_test_inventory,
)
from external_baselines.qdfl_adapter import (
    CONFIG_SPECS,
    assert_fit_environment_has_no_test_roots as assert_qdfl_no_test_roots,
    atomic_write_json,
    canonical_object_sha256,
    load_weight_registry,
    training_class_inventory,
    training_content_inventory,
    validate_completed_fit as validate_qdfl_fit,
    validate_resource_adaptation,
    verify_patched_source,
    verify_weight,
)


MATRIX_SCHEMA = "lgm-game.transactions-t1-matrix.v1"
PROFILE_SCHEMA = "lgm-game.transactions-t1-resource-profile.v1"
LEDGER_SCHEMA = "lgm-game.transactions-t1-ledger.v1"
ENVIRONMENT_LOCK_SCHEMA = "lgm-game.transactions-environment-lock.v1"

QDFL_SOURCE_DIR = "qdfl-627296d5-adapter-v4"
QDFL_PATCH_MANIFEST = f"{QDFL_SOURCE_DIR}.patch_manifest.json"
MCCG_SOURCE_DIR = "mccg-e1c51b01-adapter-v2"
MCCG_PATCH_MANIFEST = f"{MCCG_SOURCE_DIR}.patch_manifest.json"

WEIGHT_FILES = {
    "dinov2_vitb14": "dinov2_vitb14_pretrain.pth",
    "fsra_vit_base": "jx_vit_base_p16_224-80ecf9dd.pth",
    "swin_v2_b_imagenet1k_v1": "swin_v2_b-781e5279.pth",
    "convnext_base_22k_1k_224": "convnext_base_22k_1k_224.pth",
    "mccg_convnext_tiny_22k_1k_224": "convnext_tiny_22k_1k_224.pth",
}
QDFL_WEIGHT_ARGUMENTS = {
    "dinov2_vitb14": "--dinov2-weight",
    "fsra_vit_base": "--fsra-weight",
    "swin_v2_b_imagenet1k_v1": "--swinv2-weight",
    "convnext_base_22k_1k_224": "--convnext-weight",
}
QDFL_EVALUATION_WEIGHT_ARGUMENTS = {
    "dinov2_vitb14": "--dinov2-weight",
    "fsra_vit_base": "--fsra-weight",
    "swin_v2_b_imagenet1k_v1": "--swinv2-weight",
    "convnext_base_22k_1k_224": "--convnext-weight",
}
EVALUATION_BATCH_SIZE = {
    "qdfl_dinov2_b14": 8,
    "fsra_vit": 8,
    "sdpl_swinv2_b": 8,
    "ccr_convnext_b": 4,
    "mccg_convnext_tiny": 8,
}
EXPECTED_EVALUATION_TASKS = (
    "university1652_drone_to_satellite",
    "university1652_satellite_to_drone",
    "sues200_uav_150m_to_satellite",
    "sues200_satellite_to_uav_150m",
    "sues200_uav_200m_to_satellite",
    "sues200_satellite_to_uav_200m",
    "sues200_uav_250m_to_satellite",
    "sues200_satellite_to_uav_250m",
    "sues200_uav_300m_to_satellite",
    "sues200_satellite_to_uav_300m",
)
EXPECTED_RUNS = (
    ("qdfl_dinov2_b14/seed_1", "qdfl", "QDFL", "qdfl_dinov2_b14", 1, 160, "dinov2_vitb14"),
    ("qdfl_dinov2_b14/seed_2", "qdfl", "QDFL", "qdfl_dinov2_b14", 2, 160, "dinov2_vitb14"),
    ("qdfl_dinov2_b14/seed_3", "qdfl", "QDFL", "qdfl_dinov2_b14", 3, 160, "dinov2_vitb14"),
    ("fsra_vit/seed_1", "qdfl", "FSRA", "fsra_vit", 1, 120, "fsra_vit_base"),
    ("sdpl_swinv2_b/seed_1", "qdfl", "SDPL", "sdpl_swinv2_b", 1, 160, "swin_v2_b_imagenet1k_v1"),
    ("ccr_convnext_b/seed_1", "qdfl", "CCR", "ccr_convnext_b", 1, 200, "convnext_base_22k_1k_224"),
    (
        "mccg_convnext_tiny/seed_1",
        "mccg",
        "MCCG",
        "mccg_convnext_tiny",
        1,
        200,
        "mccg_convnext_tiny_22k_1k_224",
    ),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise IntegrityError(f"Required JSON file is absent: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise IntegrityError(f"JSON root must be a mapping: {path}")
    return payload


def validate_payload_hash(payload: dict[str, Any], label: str) -> str:
    body = dict(payload)
    declared = body.pop("payload_sha256", None)
    actual = canonical_object_sha256(body)
    if declared != actual:
        raise IntegrityError(
            f"{label} payload hash mismatch: expected {declared!r}, got {actual}"
        )
    return actual


def validate_matrix(path: Path) -> dict[str, Any]:
    matrix = load_json(path)
    if matrix.get("schema_version") != MATRIX_SCHEMA:
        raise IntegrityError("Transactions T1 matrix schema mismatch.")
    if matrix.get("registered_run_count") != len(EXPECTED_RUNS):
        raise IntegrityError("Transactions T1 registered-run count mismatch.")
    dataset = matrix.get("dataset", {})
    expected_dataset = {
        "name": "University-1652",
        "split": "train",
        "views": ["satellite", "street", "drone"],
        "excluded_auxiliary_views": ["google"],
        "class_count": 701,
        "file_count": 41214,
        "total_bytes": 2670030871,
        "content_sha256": (
            "61852ee531d095ae4fd7507c12555fe9cac130df84a1308cacf00b2ca97bf3a6"
        ),
    }
    if dataset != expected_dataset:
        raise IntegrityError("Transactions T1 dataset registration changed.")
    expected_evaluation = {
        "datasets": ["University-1652", "SUES-200"],
        "registered_fits": 7,
        "tasks_per_fit": 10,
        "total_task_evaluations": 70,
        "university1652": {
            "split": "test",
            "directions": [
                {
                    "task": "university1652_drone_to_satellite",
                    "query_role": "query_drone",
                    "query_images": 37855,
                    "gallery_role": "gallery_satellite",
                    "gallery_images": 951,
                },
                {
                    "task": "university1652_satellite_to_drone",
                    "query_role": "query_satellite",
                    "query_images": 701,
                    "gallery_role": "gallery_drone",
                    "gallery_images": 51355,
                },
            ],
            "task_evaluations_per_fit": 2,
            "task_evaluations_total": 14,
            "excluded_direction": "street_to_satellite",
            "exclusion_reason": (
                "The pinned public QDFL-framework and MCCG test entry points "
                "used for T1 implement only Drone-to-Satellite and "
                "Satellite-to-Drone."
            ),
        },
        "zero_shot_sues200": {
            "split": "official fixed 120-train/80-test identity protocol",
            "split_manifest_sha256": (
                "c1386d5c746aca48bbb2793ed1ee19d6cd7330a7f5f1b27a5ec43727317ec226"
            ),
            "target_domain_fitting": False,
            "target_domain_model_selection": False,
            "query_identity_count": 80,
            "gallery_identity_count": 200,
            "altitudes_m": [150, 200, 250, 300],
            "directions": [
                {
                    "task": "sues200_uav_150m_to_satellite",
                    "query_role": "drone_150_all:test_ids",
                    "query_images": 4000,
                    "gallery_role": "satellite_all",
                    "gallery_images": 200,
                },
                {
                    "task": "sues200_satellite_to_uav_150m",
                    "query_role": "satellite_all:test_ids",
                    "query_images": 80,
                    "gallery_role": "drone_150_all",
                    "gallery_images": 10000,
                },
                {
                    "task": "sues200_uav_200m_to_satellite",
                    "query_role": "drone_200_all:test_ids",
                    "query_images": 4000,
                    "gallery_role": "satellite_all",
                    "gallery_images": 200,
                },
                {
                    "task": "sues200_satellite_to_uav_200m",
                    "query_role": "satellite_all:test_ids",
                    "query_images": 80,
                    "gallery_role": "drone_200_all",
                    "gallery_images": 10000,
                },
                {
                    "task": "sues200_uav_250m_to_satellite",
                    "query_role": "drone_250_all:test_ids",
                    "query_images": 4000,
                    "gallery_role": "satellite_all",
                    "gallery_images": 200,
                },
                {
                    "task": "sues200_satellite_to_uav_250m",
                    "query_role": "satellite_all:test_ids",
                    "query_images": 80,
                    "gallery_role": "drone_250_all",
                    "gallery_images": 10000,
                },
                {
                    "task": "sues200_uav_300m_to_satellite",
                    "query_role": "drone_300_all:test_ids",
                    "query_images": 4000,
                    "gallery_role": "satellite_all",
                    "gallery_images": 200,
                },
                {
                    "task": "sues200_satellite_to_uav_300m",
                    "query_role": "satellite_all:test_ids",
                    "query_images": 80,
                    "gallery_role": "drone_300_all",
                    "gallery_images": 10000,
                },
            ],
            "task_evaluations_per_fit": 8,
            "task_evaluations_total": 56,
        },
        "all_queries_and_full_gallery": True,
        "horizontal_flip_augmentation": True,
        "test_content_freeze": (
            "one full path-size-content inventory of both datasets after all "
            "seven completed-fit audits and before the first official evaluation"
        ),
        "registered_test_inventory": {
            "university1652": {
                "images": 90862,
                "bytes": 5704769123,
                "membership_sha256": (
                    "19c26d413c79b77785ca05c02962ed30135c9e2c43a712a3db52c8dda59ff6b7"
                ),
            },
            "sues200": {
                "images": 40200,
                "bytes": 5693433493,
                "membership_sha256": (
                    "dc6742e45599231b53f16730771cb5eab45d5b0ef6aed8d1663324207a15f706"
                ),
            },
            "combined": {
                "images": 131062,
                "bytes": 11398202616,
            },
        },
        "ranking": {
            "qdfl_framework": (
                "float32 squared L2, matching the public QDFL-framework evaluator"
            ),
            "mccg": (
                "float32 inner product, matching the public MCCG evaluator"
            ),
        },
        "metrics": [
            "R@1",
            "R@5",
            "R@10",
            "R@20",
            "official trapezoidal mAP",
            "MRR",
        ],
    }
    if matrix.get("official_evaluation") != expected_evaluation:
        raise IntegrityError(
            "Transactions T1 official-evaluation registration changed."
        )
    rows = matrix.get("runs")
    if not isinstance(rows, list) or len(rows) != len(EXPECTED_RUNS):
        raise IntegrityError("Transactions T1 run rows are absent or duplicated.")
    observed: list[tuple[Any, ...]] = []
    for ordinal, row in enumerate(rows, start=1):
        if row.get("ordinal") != ordinal:
            raise IntegrityError("Transactions T1 ordinals are not contiguous.")
        observed.append(
            (
                row.get("run_id"),
                row.get("framework"),
                row.get("method"),
                row.get("config_id"),
                row.get("seed"),
                row.get("epochs"),
                row.get("initialization_id"),
            )
        )
        if row.get("resource_profile_key") != row.get("config_id"):
            raise IntegrityError("Transactions T1 resource-profile key mismatch.")
    if tuple(observed) != EXPECTED_RUNS:
        raise IntegrityError("Transactions T1 registered matrix changed.")
    return matrix


def validate_environment_lock(path: Path, root: Path) -> dict[str, Any]:
    lock = load_json(path)
    if lock.get("schema_version") != ENVIRONMENT_LOCK_SCHEMA:
        raise IntegrityError("Transactions environment-lock schema mismatch.")
    validate_payload_hash(lock, "Transactions environment lock")
    artifact_paths = {
        "qdfl_adapter": root / "qdfl_adapter.py",
        "mccg_adapter": root / "mccg_adapter.py",
        "source_patching": root / "source_patching.py",
        "source_registry": root / "transactions_baseline_registry.json",
        "weight_registry": root / "transactions_weight_registry.json",
    }
    declared = lock.get("registered_artifacts", {})
    for key, path_value in artifact_paths.items():
        row = declared.get(key, {})
        if (
            Path(str(row.get("path", ""))).resolve() != path_value.resolve()
            or row.get("bytes") != path_value.stat().st_size
            or row.get("sha256") != sha256_file(path_value)
        ):
            raise IntegrityError(
                f"Environment lock no longer matches registered artifact {key}."
            )
    for environment in lock.get("environments", {}).values():
        if environment.get("pip_check", {}).get("status") != "passed":
            raise IntegrityError("A registered T1 environment failed pip check.")
    return lock


def validate_profile(path: Path, matrix: dict[str, Any]) -> dict[str, Any]:
    profile = load_json(path)
    if profile.get("schema_version") != PROFILE_SCHEMA:
        raise IntegrityError("Transactions T1 resource-profile schema mismatch.")
    if profile.get("status") != "frozen":
        raise IntegrityError(
            "Transactions T1 resource profile is not frozen; GPU fitting is prohibited."
        )
    validate_payload_hash(profile, "Transactions T1 resource profile")
    configs = profile.get("configs")
    expected_keys = {row["resource_profile_key"] for row in matrix["runs"]}
    if not isinstance(configs, dict) or set(configs) != expected_keys:
        raise IntegrityError("Transactions T1 resource-profile coverage mismatch.")
    for config_id, row in configs.items():
        if config_id == "mccg_convnext_tiny":
            if (
                row.get("batch_size") != 8
                or row.get("workers") != 0
                or row.get("resource_adapted") is not False
            ):
                raise IntegrityError("MCCG frozen resource profile changed.")
        else:
            spec = CONFIG_SPECS[config_id]
            micro_batch = int(row.get("micro_batch_size", 0))
            accumulation = validate_resource_adaptation(spec, micro_batch)
            if row.get("nominal_batch_size") != spec.nominal_batch_size:
                raise IntegrityError(f"{config_id} nominal batch changed.")
            if row.get("accumulate_grad_batches") != accumulation:
                raise IntegrityError(f"{config_id} accumulation factor mismatch.")
            if int(row.get("workers", -1)) < 0:
                raise IntegrityError(f"{config_id} worker count is invalid.")
        manifest_path = Path(str(row.get("feasibility_manifest_path", "")))
        if not manifest_path.is_file():
            raise IntegrityError(f"{config_id} feasibility manifest is absent.")
        if sha256_file(manifest_path) != row.get("feasibility_manifest_sha256"):
            raise IntegrityError(f"{config_id} feasibility-manifest hash mismatch.")
        feasibility = load_json(manifest_path)
        if (
            feasibility.get("status") != "completed"
            or feasibility.get("config_id") != config_id
            or feasibility.get("official_test_access") is not False
            or feasibility.get("manuscript_result") is not False
        ):
            raise IntegrityError(f"{config_id} feasibility manifest is not admissible.")
    return profile


def verify_static_inputs(args: argparse.Namespace) -> dict[str, Any]:
    delivery = args.delivery_root.resolve(strict=True)
    root = delivery / "external_baselines"
    matrix_path = root / "transactions_t1_matrix.json"
    matrix = validate_matrix(matrix_path)
    environment_path = root / "transactions_environment_lock.json"
    environment_lock = validate_environment_lock(environment_path, root)
    protocol_path = delivery / "TRANSACTIONS_EXTENSION_PROTOCOL.md"
    if not protocol_path.is_file():
        raise IntegrityError("Transactions extension protocol is absent.")

    qdfl_python = args.qdfl_python.resolve(strict=True)
    mccg_python = args.mccg_python.resolve(strict=True)
    registered_environments = environment_lock["environments"]
    expected_interpreters = {
        "qdfl_framework": qdfl_python,
        "mccg": mccg_python,
    }
    for key, interpreter in expected_interpreters.items():
        recorded = Path(
            registered_environments[key]["interpreter_path"]
        ).resolve(strict=True)
        if recorded != interpreter:
            raise IntegrityError(f"{key} interpreter differs from the environment lock.")
    if Path(sys.executable).resolve(strict=True) != qdfl_python:
        raise IntegrityError(
            "The T1 matrix runner must itself use the locked QDFL-framework interpreter."
        )

    assert_qdfl_no_test_roots()
    assert_mccg_no_test_roots()
    train_root = args.train_root.resolve(strict=True)
    classes = training_class_inventory(train_root)
    content = training_content_inventory(train_root)
    classes["content_inventory"] = content

    patched_root = args.external_work_root.resolve(strict=True) / "patched_sources"
    source_rows = {}
    for source_id, directory_name, manifest_name in (
        ("qdfl", QDFL_SOURCE_DIR, QDFL_PATCH_MANIFEST),
        ("mccg", MCCG_SOURCE_DIR, MCCG_PATCH_MANIFEST),
    ):
        source_root = patched_root / directory_name
        manifest_path = patched_root / manifest_name
        manifest = verify_patched_source(
            source_root,
            manifest_path,
            expected_source_id=source_id,
        )
        source_rows[source_id] = {
            "source_root": str(source_root.resolve()),
            "source_tree_sha256": manifest["patched_tree_sha256"],
            "source_file_count": manifest["patched_file_count"],
            "patch_manifest_path": str(manifest_path.resolve()),
            "patch_manifest_sha256": sha256_file(manifest_path),
            "patch_plan_sha256": manifest["patch_plan_sha256"],
        }

    weight_registry_path = root / "transactions_weight_registry.json"
    weight_registry, weight_registry_sha = load_weight_registry(weight_registry_path)
    weights_root = args.external_work_root.resolve(strict=True) / "weights"
    weight_rows = {}
    for weight_id, filename in WEIGHT_FILES.items():
        registered = weight_registry[weight_id]
        weight_rows[weight_id] = verify_weight(
            weights_root / filename,
            str(registered["sha256"]),
            int(registered["bytes"]),
            weight_id,
        )

    evaluation_code = {}
    for name in (
        "official_descriptor_evaluation.py",
        "qdfl_official_evaluation.py",
        "mccg_official_evaluation.py",
    ):
        path = root / name
        if not path.is_file():
            raise IntegrityError(f"T1 official-evaluation code is absent: {path}")
        evaluation_code[name] = {
            "path": str(path.resolve()),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }

    return {
        "schema_version": "lgm-game.transactions-t1-static-audit.v1",
        "status": "static_inputs_verified",
        "registered_run_count": len(matrix["runs"]),
        "matrix_path": str(matrix_path.resolve()),
        "matrix_sha256": sha256_file(matrix_path),
        "protocol_path": str(protocol_path.resolve()),
        "protocol_sha256": sha256_file(protocol_path),
        "runner_path": str(Path(__file__).resolve()),
        "runner_sha256": sha256_file(Path(__file__)),
        "environment_lock_path": str(environment_path.resolve()),
        "environment_lock_sha256": sha256_file(environment_path),
        "environment_lock_payload_sha256": environment_lock["payload_sha256"],
        "weight_registry_path": str(weight_registry_path.resolve()),
        "weight_registry_sha256": weight_registry_sha,
        "dataset": classes,
        "sources": source_rows,
        "weights": weight_rows,
        "official_evaluation_code": evaluation_code,
        "interpreters": {
            "qdfl_framework": str(qdfl_python),
            "mccg": str(mccg_python),
        },
    }


def validate_existing_fit(row: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    manifest_path = output_dir / "fit_manifest.json"
    config_path = output_dir / "run_config.json"
    if not manifest_path.is_file() or not config_path.is_file():
        raise IntegrityError(f"Completed T1 artifacts are absent for {row['run_id']}.")
    run_config_sha = sha256_file(config_path)
    if row["framework"] == "qdfl":
        return validate_qdfl_fit(
            manifest_path=manifest_path,
            output_dir=output_dir,
            spec=CONFIG_SPECS[row["config_id"]],
            seed=int(row["seed"]),
            run_config_sha=run_config_sha,
        )
    return validate_mccg_fit(
        manifest_path,
        output_dir,
        run_config_sha,
        int(row["seed"]),
    )


def fit_checkpoint_path(row: dict[str, Any], fit_dir: Path) -> Path:
    if row["framework"] == "qdfl":
        return fit_dir / "checkpoints" / "last.ckpt"
    return fit_dir / "net_last.pth"


def build_or_validate_all_fits_gate(
    *,
    gate_path: Path,
    audit: dict[str, Any],
    matrix: dict[str, Any],
    runs_root: Path,
) -> dict[str, Any]:
    rows = []
    for row in matrix["runs"]:
        fit_dir = runs_root / "fits" / Path(row["run_id"])
        manifest = validate_existing_fit(row, fit_dir)
        fit_manifest_path = fit_dir / "fit_manifest.json"
        run_config_path = fit_dir / "run_config.json"
        checkpoint_path = fit_checkpoint_path(row, fit_dir)
        rows.append(
            {
                "ordinal": row["ordinal"],
                "run_id": row["run_id"],
                "framework": row["framework"],
                "method": row["method"],
                "config_id": row["config_id"],
                "seed": row["seed"],
                "fit_manifest_path": str(fit_manifest_path.resolve()),
                "fit_manifest_sha256": sha256_file(fit_manifest_path),
                "run_config_path": str(run_config_path.resolve()),
                "run_config_sha256": sha256_file(run_config_path),
                "checkpoint_path": str(checkpoint_path.resolve()),
                "checkpoint_sha256": manifest["checkpoint_sha256"],
            }
        )
    stable = {
        "schema_version": ALL_FITS_GATE_SCHEMA,
        "status": "all_seven_fits_validated",
        "registered_run_count": len(rows),
        "matrix_path": audit["matrix_path"],
        "matrix_sha256": audit["matrix_sha256"],
        "protocol_path": audit["protocol_path"],
        "protocol_sha256": audit["protocol_sha256"],
        "runner_path": audit["runner_path"],
        "runner_sha256": audit["runner_sha256"],
        "official_evaluation_code": audit["official_evaluation_code"],
        "runs": rows,
    }
    if gate_path.exists():
        gate = load_json(gate_path)
        validate_payload_hash(gate, "Transactions T1 all-fits gate")
        observed = dict(gate)
        observed.pop("payload_sha256", None)
        observed.pop("created_utc", None)
        if observed != stable:
            raise IntegrityError(
                "Existing T1 all-fits gate differs from current completed fits/code."
            )
        return gate
    payload = {**stable, "created_utc": utc_now()}
    gate = {
        **payload,
        "payload_sha256": canonical_object_sha256(payload),
    }
    atomic_write_json(gate_path, gate)
    return gate


def build_or_validate_test_inventory_gate(
    *,
    gate_path: Path,
    test_root: Path,
    sues_root: Path,
    sues_manifest: Path,
    all_fits_gate_path: Path,
) -> dict[str, Any]:
    # This is the first operation in the T1 runner that reads official-test
    # files.  Its caller has already validated all seven final-epoch fits and
    # written the immutable all-fits gate.
    _, university_inventory = scan_university1652_official_test(
        test_root,
        hash_contents=True,
    )
    validate_university1652_test_inventory(university_inventory)
    _, sues_inventory, _ = scan_sues200_official_test(
        sues_root,
        sues_manifest,
        hash_contents=True,
    )
    validate_sues200_test_inventory(sues_inventory)
    inventory = {
        "university1652": university_inventory,
        "sues200": sues_inventory,
    }
    stable = {
        "schema_version": TEST_INVENTORY_GATE_SCHEMA,
        "status": "content_frozen_after_all_fits_gate",
        "test_root": str(test_root.resolve()),
        "sues_root": str(sues_root.resolve()),
        "sues_manifest_path": str(sues_manifest.resolve()),
        "sues_manifest_sha256": sha256_file(sues_manifest),
        "all_fits_gate_path": str(all_fits_gate_path.resolve()),
        "all_fits_gate_sha256": sha256_file(all_fits_gate_path),
        "inventory": inventory,
    }
    if gate_path.exists():
        gate = load_json(gate_path)
        validate_payload_hash(gate, "Transactions T1 official-test inventory gate")
        observed = dict(gate)
        observed.pop("payload_sha256", None)
        observed.pop("created_utc", None)
        if observed != stable:
            raise IntegrityError(
                "Official-test content changed after the T1 post-fit freeze."
            )
        return gate
    payload = {**stable, "created_utc": utc_now()}
    gate = {
        **payload,
        "payload_sha256": canonical_object_sha256(payload),
    }
    atomic_write_json(gate_path, gate)
    return gate


def build_evaluation_command(
    args: argparse.Namespace,
    row: dict[str, Any],
    fit_dir: Path,
    output_dir: Path,
    all_fits_gate: Path,
    test_inventory_gate: Path,
) -> list[str]:
    root = args.delivery_root.resolve() / "external_baselines"
    patched = args.external_work_root.resolve() / "patched_sources"
    weights = args.external_work_root.resolve() / "weights"
    shared = [
        "--seed",
        str(row["seed"]),
        "--fit-dir",
        str(fit_dir.resolve()),
        "--all-fits-gate",
        str(all_fits_gate.resolve()),
        "--test-inventory-gate",
        str(test_inventory_gate.resolve()),
        "--test-root",
        str(args.test_root.resolve()),
        "--sues-root",
        str(args.sues_root.resolve()),
        "--sues-manifest",
        str(args.sues_manifest.resolve()),
        "--output-dir",
        str(output_dir.resolve()),
        "--device-index",
        str(args.device_index),
        "--batch-size",
        str(EVALUATION_BATCH_SIZE[row["config_id"]]),
        "--ranking-chunk-size",
        "128",
    ]
    if row["framework"] == "qdfl":
        command = [
            str(args.qdfl_python.resolve()),
            "-B",
            str((root / "qdfl_official_evaluation.py").resolve()),
            "--config-id",
            row["config_id"],
            "--source-root",
            str((patched / QDFL_SOURCE_DIR).resolve()),
            "--patch-manifest",
            str((patched / QDFL_PATCH_MANIFEST).resolve()),
            *shared,
            "--workers",
            "4",
        ]
        for weight_id, argument in QDFL_EVALUATION_WEIGHT_ARGUMENTS.items():
            command.extend(
                [
                    argument,
                    str((weights / WEIGHT_FILES[weight_id]).resolve()),
                ]
            )
        return command
    return [
        str(args.mccg_python.resolve()),
        "-B",
        str((root / "mccg_official_evaluation.py").resolve()),
        "--source-root",
        str((patched / MCCG_SOURCE_DIR).resolve()),
        "--patch-manifest",
        str((patched / MCCG_PATCH_MANIFEST).resolve()),
        *shared,
        "--workers",
        "0",
        "--convnext-weight",
        str(
            (
                weights
                / WEIGHT_FILES["mccg_convnext_tiny_22k_1k_224"]
            ).resolve()
        ),
    ]


def validate_existing_evaluation(
    row: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    manifest = validate_completed_evaluation(output_dir)
    expected = {
        "status": "completed",
        "method": row["method"],
        "config_id": row["config_id"],
        "seed": row["seed"],
        "task_names": list(EXPECTED_EVALUATION_TASKS),
    }
    for field, value in expected.items():
        if manifest.get(field) != value:
            raise IntegrityError(
                f"{row['run_id']} official evaluation {field} mismatch."
            )
    return manifest


def build_fit_command(
    args: argparse.Namespace,
    row: dict[str, Any],
    profile: dict[str, Any],
    output_dir: Path,
) -> list[str]:
    root = args.delivery_root.resolve() / "external_baselines"
    patched = args.external_work_root.resolve() / "patched_sources"
    weights = args.external_work_root.resolve() / "weights"
    device = str(args.device_index)
    if row["framework"] == "qdfl":
        resource = profile["configs"][row["resource_profile_key"]]
        weight_id = row["initialization_id"]
        return [
            str(args.qdfl_python.resolve()),
            "-B",
            str((root / "run_qdfl_fit.py").resolve()),
            "--config-id",
            row["config_id"],
            "--seed",
            str(row["seed"]),
            "--source-root",
            str((patched / QDFL_SOURCE_DIR).resolve()),
            "--patch-manifest",
            str((patched / QDFL_PATCH_MANIFEST).resolve()),
            "--train-root",
            str(args.train_root.resolve()),
            "--output-dir",
            str(output_dir.resolve()),
            "--micro-batch-size",
            str(resource["micro_batch_size"]),
            "--workers",
            str(resource["workers"]),
            "--device-index",
            device,
            "--resume",
            "auto",
            QDFL_WEIGHT_ARGUMENTS[weight_id],
            str((weights / WEIGHT_FILES[weight_id]).resolve()),
        ]
    return [
        str(args.mccg_python.resolve()),
        "-B",
        str((root / "run_mccg_fit.py").resolve()),
        "--seed",
        str(row["seed"]),
        "--source-root",
        str((patched / MCCG_SOURCE_DIR).resolve()),
        "--patch-manifest",
        str((patched / MCCG_PATCH_MANIFEST).resolve()),
        "--train-root",
        str(args.train_root.resolve()),
        "--output-dir",
        str(output_dir.resolve()),
        "--convnext-weight",
        str(
            (
                weights
                / WEIGHT_FILES["mccg_convnext_tiny_22k_1k_224"]
            ).resolve()
        ),
        "--device-index",
        device,
    ]


def assert_no_other_python_gpu_process() -> None:
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-compute-apps=pid,process_name",
            "--format=csv,noheader,nounits",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise IntegrityError(f"nvidia-smi process audit failed: {completed.stderr}")
    conflicts = []
    for line in completed.stdout.splitlines():
        fields = [field.strip() for field in line.split(",", 1)]
        if len(fields) == 2 and "python" in fields[1].lower():
            try:
                pid = int(fields[0])
            except ValueError:
                continue
            if pid != os.getpid():
                conflicts.append({"pid": pid, "process_name": fields[1]})
    if conflicts:
        raise IntegrityError(
            f"Another Python GPU process is active; serialized T1 fitting required: {conflicts}"
        )


def initialize_or_verify_ledger(
    path: Path,
    audit: dict[str, Any],
    profile_path: Path,
    profile: dict[str, Any],
    matrix: dict[str, Any],
) -> dict[str, Any]:
    frozen = {
        "static_audit": audit,
        "resource_profile_path": str(profile_path.resolve()),
        "resource_profile_sha256": sha256_file(profile_path),
        "resource_profile_payload_sha256": profile["payload_sha256"],
    }
    if path.exists():
        ledger = load_json(path)
        if ledger.get("schema_version") != LEDGER_SCHEMA:
            raise IntegrityError("Transactions T1 ledger schema mismatch.")
        if ledger.get("frozen_inputs") != frozen:
            raise IntegrityError("Transactions T1 frozen ledger inputs changed.")
        return ledger
    ledger = {
        "schema_version": LEDGER_SCHEMA,
        "created_utc": utc_now(),
        "updated_utc": utc_now(),
        "status": "registered",
        "registered_run_count": len(matrix["runs"]),
        "frozen_inputs": frozen,
        "runs": {
            row["run_id"]: {
                "ordinal": row["ordinal"],
                "method": row["method"],
                "config_id": row["config_id"],
                "seed": row["seed"],
                "status": "pending",
                "events": [],
            }
            for row in matrix["runs"]
        },
        "invocations": [],
    }
    atomic_write_json(path, ledger)
    return ledger


def record_event(
    ledger_path: Path,
    ledger: dict[str, Any],
    run_id: str,
    event: dict[str, Any],
) -> None:
    row = ledger["runs"][run_id]
    row["events"].append(event)
    row.update({key: value for key, value in event.items() if key != "command"})
    ledger["updated_utc"] = utc_now()
    atomic_write_json(ledger_path, ledger)


def run_training(args: argparse.Namespace) -> dict[str, Any]:
    audit = verify_static_inputs(args)
    root = args.delivery_root.resolve() / "external_baselines"
    matrix = validate_matrix(root / "transactions_t1_matrix.json")
    profile_path = args.resource_profile.resolve()
    profile = validate_profile(profile_path, matrix)
    runs_root = root / "runs" / "transactions_t1"
    ledger_path = runs_root / "transactions_t1_ledger.json"
    ledger = initialize_or_verify_ledger(
        ledger_path,
        audit,
        profile_path,
        profile,
        matrix,
    )
    invocation = {
        "started_utc": utc_now(),
        "stage": "train",
        "status": "running",
    }
    ledger["invocations"].append(invocation)
    ledger["status"] = "training"
    atomic_write_json(ledger_path, ledger)

    try:
        for row in matrix["runs"]:
            run_id = row["run_id"]
            output_dir = runs_root / "fits" / Path(run_id)
            ledger_row = ledger["runs"][run_id]
            if ledger_row["status"] == "completed":
                manifest = validate_existing_fit(row, output_dir)
                record_event(
                    ledger_path,
                    ledger,
                    run_id,
                    {
                        "status": "completed",
                        "event_type": "skipped_already_complete",
                        "updated_utc": utc_now(),
                        "fit_manifest_sha256": sha256_file(
                            output_dir / "fit_manifest.json"
                        ),
                        "checkpoint_sha256": manifest["checkpoint_sha256"],
                    },
                )
                continue
            if ledger_row["status"] in {"failed", "running"}:
                raise IntegrityError(
                    f"{run_id} has status {ledger_row['status']!r}; diagnose and "
                    "preserve the attempt before an explicitly authorized continuation."
                )
            if (output_dir / "fit_manifest.json").exists():
                manifest = validate_existing_fit(row, output_dir)
                record_event(
                    ledger_path,
                    ledger,
                    run_id,
                    {
                        "status": "completed",
                        "recovered_from_complete_artifacts": True,
                        "updated_utc": utc_now(),
                        "fit_manifest_sha256": sha256_file(
                            output_dir / "fit_manifest.json"
                        ),
                        "checkpoint_sha256": manifest["checkpoint_sha256"],
                    },
                )
                continue

            assert_no_other_python_gpu_process()
            command = build_fit_command(args, row, profile, output_dir)
            attempt = 1 + sum(
                event.get("status") == "running"
                for event in ledger_row.get("events", [])
            )
            log_dir = runs_root / "process_logs" / row["config_id"] / f"seed_{row['seed']}"
            log_dir.mkdir(parents=True, exist_ok=True)
            stdout_path = log_dir / f"attempt_{attempt}_stdout.log"
            stderr_path = log_dir / f"attempt_{attempt}_stderr.log"
            if stdout_path.exists() or stderr_path.exists():
                raise IntegrityError(f"Refusing to overwrite T1 process logs for {run_id}.")
            started = time.perf_counter()
            record_event(
                ledger_path,
                ledger,
                run_id,
                {
                    "status": "running",
                    "attempt": attempt,
                    "started_utc": utc_now(),
                    "command": command,
                    "stdout_path": str(stdout_path.resolve()),
                    "stderr_path": str(stderr_path.resolve()),
                },
            )
            environment = dict(os.environ)
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            with stdout_path.open("x", encoding="utf-8", newline="\n") as stdout, (
                stderr_path.open("x", encoding="utf-8", newline="\n")
            ) as stderr:
                completed = subprocess.run(
                    command,
                    cwd=root,
                    env=environment,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout,
                    stderr=stderr,
                    check=False,
                )
            elapsed = time.perf_counter() - started
            if completed.returncode != 0:
                record_event(
                    ledger_path,
                    ledger,
                    run_id,
                    {
                        "status": "failed",
                        "attempt": attempt,
                        "finished_utc": utc_now(),
                        "elapsed_seconds": elapsed,
                        "return_code": completed.returncode,
                        "stdout_sha256": sha256_file(stdout_path),
                        "stderr_sha256": sha256_file(stderr_path),
                    },
                )
                raise IntegrityError(
                    f"Transactions T1 fit failed for {run_id}; "
                    f"return code {completed.returncode}. No retry was attempted."
                )
            manifest = validate_existing_fit(row, output_dir)
            record_event(
                ledger_path,
                ledger,
                run_id,
                {
                    "status": "completed",
                    "attempt": attempt,
                    "finished_utc": utc_now(),
                    "elapsed_seconds": elapsed,
                    "return_code": completed.returncode,
                    "stdout_sha256": sha256_file(stdout_path),
                    "stderr_sha256": sha256_file(stderr_path),
                    "fit_manifest_sha256": sha256_file(
                        output_dir / "fit_manifest.json"
                    ),
                    "checkpoint_sha256": manifest["checkpoint_sha256"],
                },
            )

        incomplete = [
            run_id
            for run_id, row in ledger["runs"].items()
            if row["status"] != "completed"
        ]
        if incomplete:
            raise IntegrityError(f"Transactions T1 fits remain incomplete: {incomplete}")
        invocation["status"] = "completed"
        invocation["finished_utc"] = utc_now()
        ledger["status"] = "all_fits_complete_official_evaluation_not_started"
        ledger["updated_utc"] = utc_now()
        atomic_write_json(ledger_path, ledger)
        return ledger
    except BaseException as error:
        invocation["status"] = "failed_or_interrupted"
        invocation["finished_utc"] = utc_now()
        invocation["error_type"] = type(error).__name__
        invocation["error"] = str(error)
        ledger["status"] = "failed_or_interrupted"
        ledger["updated_utc"] = utc_now()
        atomic_write_json(ledger_path, ledger)
        raise


def run_evaluation(args: argparse.Namespace) -> dict[str, Any]:
    if (
        args.test_root is None
        or args.sues_root is None
        or args.sues_manifest is None
    ):
        raise IntegrityError(
            "--test-root, --sues-root, and --sues-manifest are required "
            "for official evaluation."
        )
    audit = verify_static_inputs(args)
    root = args.delivery_root.resolve() / "external_baselines"
    matrix = validate_matrix(root / "transactions_t1_matrix.json")
    profile_path = args.resource_profile.resolve()
    profile = validate_profile(profile_path, matrix)
    runs_root = root / "runs" / "transactions_t1"
    ledger_path = runs_root / "transactions_t1_ledger.json"
    ledger = initialize_or_verify_ledger(
        ledger_path,
        audit,
        profile_path,
        profile,
        matrix,
    )
    incomplete_fits = [
        row["run_id"]
        for row in matrix["runs"]
        if ledger["runs"][row["run_id"]].get("status") != "completed"
    ]
    if incomplete_fits:
        raise IntegrityError(
            "Official test access is prohibited until all seven T1 fits "
            f"are completed: {incomplete_fits}"
        )
    for row in matrix["runs"]:
        fit_dir = runs_root / "fits" / Path(row["run_id"])
        validate_existing_fit(row, fit_dir)

    gate_path = runs_root / "transactions_t1_all_fits_gate.json"
    build_or_validate_all_fits_gate(
        gate_path=gate_path,
        audit=audit,
        matrix=matrix,
        runs_root=runs_root,
    )
    test_inventory_gate_path = (
        runs_root / "transactions_t1_official_test_inventory_gate.json"
    )
    build_or_validate_test_inventory_gate(
        gate_path=test_inventory_gate_path,
        test_root=args.test_root,
        sues_root=args.sues_root,
        sues_manifest=args.sues_manifest,
        all_fits_gate_path=gate_path,
    )
    invocation = {
        "started_utc": utc_now(),
        "stage": "official_evaluation",
        "status": "running",
        "all_fits_gate_path": str(gate_path.resolve()),
        "all_fits_gate_sha256": sha256_file(gate_path),
        "test_inventory_gate_path": str(
            test_inventory_gate_path.resolve()
        ),
        "test_inventory_gate_sha256": sha256_file(
            test_inventory_gate_path
        ),
    }
    ledger["invocations"].append(invocation)
    ledger["status"] = "official_evaluation_running"
    ledger["updated_utc"] = utc_now()
    atomic_write_json(ledger_path, ledger)

    try:
        for row in matrix["runs"]:
            run_id = row["run_id"]
            fit_dir = runs_root / "fits" / Path(run_id)
            output_dir = runs_root / "evaluations" / Path(run_id)
            manifest_path = output_dir / "evaluation_manifest.json"
            if manifest_path.is_file():
                manifest = validate_existing_evaluation(row, output_dir)
                record_event(
                    ledger_path,
                    ledger,
                    run_id,
                    {
                        "event_type": "official_evaluation_skipped_complete",
                        "evaluation_status": "completed",
                        "updated_utc": utc_now(),
                        "evaluation_manifest_sha256": sha256_file(
                            manifest_path
                        ),
                        "evaluation_config_sha256": manifest[
                            "evaluation_config_sha256"
                        ],
                    },
                )
                continue
            if output_dir.exists() and any(output_dir.iterdir()):
                raise IntegrityError(
                    f"{run_id} has incomplete official-evaluation artifacts; "
                    "archive the failed attempt before retrying."
                )

            assert_no_other_python_gpu_process()
            command = build_evaluation_command(
                args,
                row,
                fit_dir,
                output_dir,
                gate_path,
                test_inventory_gate_path,
            )
            prior_attempts = sum(
                event.get("event_type") == "official_evaluation_running"
                for event in ledger["runs"][run_id].get("events", [])
            )
            attempt = prior_attempts + 1
            log_dir = (
                runs_root
                / "process_logs"
                / row["config_id"]
                / f"seed_{row['seed']}"
            )
            log_dir.mkdir(parents=True, exist_ok=True)
            stdout_path = (
                log_dir / f"evaluation_attempt_{attempt}_stdout.log"
            )
            stderr_path = (
                log_dir / f"evaluation_attempt_{attempt}_stderr.log"
            )
            if stdout_path.exists() or stderr_path.exists():
                raise IntegrityError(
                    f"Refusing to overwrite T1 evaluation logs for {run_id}."
                )
            record_event(
                ledger_path,
                ledger,
                run_id,
                {
                    "event_type": "official_evaluation_running",
                    "evaluation_status": "running",
                    "evaluation_attempt": attempt,
                    "evaluation_started_utc": utc_now(),
                    "evaluation_command": command,
                    "evaluation_stdout_path": str(stdout_path.resolve()),
                    "evaluation_stderr_path": str(stderr_path.resolve()),
                },
            )
            environment = dict(os.environ)
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            environment["PYTHONHASHSEED"] = str(row["seed"])
            environment["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
            started = time.perf_counter()
            with stdout_path.open("x", encoding="utf-8", newline="\n") as stdout, (
                stderr_path.open("x", encoding="utf-8", newline="\n")
            ) as stderr:
                completed = subprocess.run(
                    command,
                    cwd=root,
                    env=environment,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout,
                    stderr=stderr,
                    check=False,
                )
            elapsed = time.perf_counter() - started
            if completed.returncode != 0:
                record_event(
                    ledger_path,
                    ledger,
                    run_id,
                    {
                        "event_type": "official_evaluation_failed",
                        "evaluation_status": "failed",
                        "evaluation_attempt": attempt,
                        "evaluation_finished_utc": utc_now(),
                        "evaluation_elapsed_seconds": elapsed,
                        "evaluation_return_code": completed.returncode,
                        "evaluation_stdout_sha256": sha256_file(stdout_path),
                        "evaluation_stderr_sha256": sha256_file(stderr_path),
                    },
                )
                raise IntegrityError(
                    f"Transactions T1 official evaluation failed for {run_id}; "
                    f"return code {completed.returncode}. No retry was attempted."
                )
            manifest = validate_existing_evaluation(row, output_dir)
            record_event(
                ledger_path,
                ledger,
                run_id,
                {
                    "event_type": "official_evaluation_completed",
                    "evaluation_status": "completed",
                    "evaluation_attempt": attempt,
                    "evaluation_finished_utc": utc_now(),
                    "evaluation_elapsed_seconds": elapsed,
                    "evaluation_return_code": completed.returncode,
                    "evaluation_stdout_sha256": sha256_file(stdout_path),
                    "evaluation_stderr_sha256": sha256_file(stderr_path),
                    "evaluation_manifest_sha256": sha256_file(
                        output_dir / "evaluation_manifest.json"
                    ),
                    "evaluation_config_sha256": manifest[
                        "evaluation_config_sha256"
                    ],
                },
            )

        incomplete = [
            run_id
            for run_id, row in ledger["runs"].items()
            if row.get("evaluation_status") != "completed"
        ]
        if incomplete:
            raise IntegrityError(
                f"Transactions T1 official evaluations remain incomplete: {incomplete}"
            )
        invocation["status"] = "completed"
        invocation["finished_utc"] = utc_now()
        ledger["status"] = "all_fits_and_official_evaluations_complete"
        ledger["updated_utc"] = utc_now()
        atomic_write_json(ledger_path, ledger)
        return ledger
    except BaseException as error:
        invocation["status"] = "failed_or_interrupted"
        invocation["finished_utc"] = utc_now()
        invocation["error_type"] = type(error).__name__
        invocation["error"] = str(error)
        ledger["status"] = "official_evaluation_failed_or_interrupted"
        ledger["updated_utc"] = utc_now()
        atomic_write_json(ledger_path, ledger)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delivery-root", type=Path, required=True)
    parser.add_argument("--train-root", type=Path, required=True)
    parser.add_argument("--external-work-root", type=Path, required=True)
    parser.add_argument("--qdfl-python", type=Path, required=True)
    parser.add_argument("--mccg-python", type=Path, required=True)
    parser.add_argument("--device-index", type=int, default=0)
    parser.add_argument(
        "--stage",
        choices=("audit", "train", "evaluate", "all"),
        default="audit",
    )
    parser.add_argument("--resource-profile", type=Path)
    parser.add_argument(
        "--test-root",
        type=Path,
        help=(
            "University-1652/test; read only after all seven completed-fit "
            "audits pass."
        ),
    )
    parser.add_argument(
        "--sues-root",
        type=Path,
        help="SUES-200 root; read only after all seven T1 fits complete.",
    )
    parser.add_argument(
        "--sues-manifest",
        type=Path,
        help="Frozen SUES-200 official 120/80 identity manifest.",
    )
    args = parser.parse_args()
    if args.device_index < 0:
        raise SystemExit("ERROR: --device-index must be non-negative.")
    if args.resource_profile is None:
        args.resource_profile = (
            args.delivery_root
            / "external_baselines"
            / "transactions_t1_resource_profile.json"
        )
    try:
        if args.stage == "audit":
            payload = verify_static_inputs(args)
        elif args.stage == "train":
            payload = run_training(args)
        elif args.stage == "evaluate":
            payload = run_evaluation(args)
        else:
            run_training(args)
            payload = run_evaluation(args)
    except (IntegrityError, OSError, ValueError, RuntimeError) as error:
        raise SystemExit(f"ERROR: {error}") from error
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
