"""Audit and aggregate the frozen 36+6 formal experiment matrix.

This program is deliberately CPU-only.  It accepts evidence only from completed
training and evaluation manifests, verifies the critical file hashes, recomputes
task metrics from the per-query arrays, and then writes task-level tables.

The default mode is fail-closed: all 36 main runs and all 6 sensitivity runs
must be complete and valid.  ``--allow-partial`` is an explicit audit mode.  It
never fills missing cells and withholds Holm-adjusted inference until the full
33-comparison visual-versus-full family is available.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import statistics
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


SCHEMA_VERSION = "lgm-game.formal-aggregate.v1"
EXPECTED_TRAINING_EPOCHS = 80
BOOTSTRAP_SAMPLES = 10_000
MAIN_SEEDS = (1, 2, 3)
VARIANT_ORDER = (
    "visual",
    "content",
    "style",
    "visual_content",
    "visual_style",
    "full",
)
DATASET_ORDER = ("university1652", "sues200")
SUES_ALTITUDES = ("150", "200", "250", "300")

TASKS: dict[str, tuple[str, ...]] = {
    "university1652": (
        "university1652_drone_to_satellite",
        "university1652_satellite_to_drone",
        "university1652_street_to_satellite",
    ),
    "sues200": tuple(
        task
        for altitude in SUES_ALTITUDES
        for task in (
            f"sues200_uav_{altitude}m_to_satellite",
            f"sues200_satellite_to_uav_{altitude}m",
        )
    ),
}

METRICS = (
    "r_at_1",
    "r_at_5",
    "r_at_10",
    "r_at_20",
    "official_trapezoid_mAP",
    "MRR",
    "mean_top1_margin",
)
PERCENT_METRICS = METRICS[:-1]
SUMMARY_METRICS = (
    "r_at_1",
    "r_at_5",
    "r_at_10",
    "r_at_20",
    "official_trapezoid_mAP",
    "MRR",
)
EXPECTED_MAIN_RUNS = 36
EXPECTED_SENSITIVITY_RUNS = 6
EXPECTED_PAIRWISE_TESTS = len(MAIN_SEEDS) * sum(len(value) for value in TASKS.values())


class IntegrityError(RuntimeError):
    """A completed artifact violates the frozen evidence contract."""


class MatrixIncompleteError(RuntimeError):
    """The fail-closed matrix gate found one or more unfinished runs."""


@dataclass(frozen=True)
class RunSpec:
    family: str
    dataset: str
    variant: str
    seed: int
    backbone: str
    embed_dim: int
    setting: str
    run_dir: Path
    evaluation_dir: Path

    @property
    def identifier(self) -> str:
        return (
            f"{self.family}/{self.dataset}/{self.variant}/seed_{self.seed}/"
            f"{self.backbone}/dim_{self.embed_dim}"
        )


@dataclass(frozen=True)
class ArrayDescriptor:
    path: Path
    sha256: str
    query_membership_sha256: str
    queries: int


@dataclass
class ValidRun:
    spec: RunSpec
    metric_rows: list[dict[str, Any]]
    arrays: dict[str, ArrayDescriptor]
    run_config_sha256: str
    checkpoint_sha256: str
    metrics_sha256: str
    protocol_membership_sha256: str
    code_sha256: str
    input_artifacts: list[dict[str, Any]]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            if text and not text.endswith("\n"):
                handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_text(
        path,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str),
    )


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise IntegrityError(f"Cannot read valid JSON from {path}: {error}") from error
    if not isinstance(value, dict):
        raise IntegrityError(f"Expected a JSON object in {path}.")
    return value


def load_json_list(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise IntegrityError(f"Cannot read valid JSON from {path}: {error}") from error
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise IntegrityError(f"Expected a list of JSON objects in {path}.")
    return value


def verify_payload_hash(payload: Mapping[str, Any], path: Path) -> None:
    declared = payload.get("payload_sha256")
    if not isinstance(declared, str):
        raise IntegrityError(f"{path} does not declare payload_sha256.")
    body = dict(payload)
    body.pop("payload_sha256", None)
    actual = canonical_sha256(body)
    if actual != declared:
        raise IntegrityError(
            f"Canonical payload hash mismatch for {path}: {actual} != {declared}."
        )


def slugify(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return value.strip("_") or "task"


def canonical_query_path(value: Any) -> str:
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return str(value).strip().replace("\\", "/").casefold()


def as_text_array(value: np.ndarray) -> np.ndarray:
    return np.asarray(
        [
            item.decode("utf-8") if isinstance(item, bytes) else str(item)
            for item in np.asarray(value).reshape(-1)
        ],
        dtype=str,
    )


def expected_specs(delivery_root: Path) -> list[RunSpec]:
    package_root = delivery_root / "lgm_game_pytorch"
    specs: list[RunSpec] = []
    for dataset in DATASET_ORDER:
        for variant in VARIANT_ORDER:
            for seed in MAIN_SEEDS:
                specs.append(
                    RunSpec(
                        family="formal_main",
                        dataset=dataset,
                        variant=variant,
                        seed=seed,
                        backbone="resnet18",
                        embed_dim=512,
                        setting=variant,
                        run_dir=(
                            package_root
                            / "runs"
                            / "formal_main"
                            / dataset
                            / variant
                            / f"seed_{seed}"
                        ),
                        evaluation_dir=(
                            package_root
                            / "evaluations"
                            / "formal_main"
                            / dataset
                            / variant
                            / f"seed_{seed}"
                        ),
                    )
                )
    sensitivity = (
        ("resnet50", 512, "backbone_resnet50"),
        ("resnet18", 256, "embed_dim_256"),
        ("resnet18", 1024, "embed_dim_1024"),
    )
    for dataset in DATASET_ORDER:
        for backbone, embed_dim, setting in sensitivity:
            specs.append(
                RunSpec(
                    family="formal_sensitivity",
                    dataset=dataset,
                    variant="full",
                    seed=1,
                    backbone=backbone,
                    embed_dim=embed_dim,
                    setting=setting,
                    run_dir=(
                        package_root
                        / "runs"
                        / "formal_sensitivity"
                        / dataset
                        / setting
                        / "seed_1"
                    ),
                    evaluation_dir=(
                        package_root
                        / "evaluations"
                        / "formal_sensitivity"
                        / dataset
                        / setting
                        / "seed_1"
                    ),
                )
            )
    if sum(spec.family == "formal_main" for spec in specs) != EXPECTED_MAIN_RUNS:
        raise AssertionError("Internal main-matrix specification is not 36 runs.")
    if (
        sum(spec.family == "formal_sensitivity" for spec in specs)
        != EXPECTED_SENSITIVITY_RUNS
    ):
        raise AssertionError("Internal sensitivity specification is not 6 runs.")
    return specs


def record_artifact(
    path: Path,
    delivery_root: Path,
    spec: RunSpec | None,
    role: str,
    *,
    actual_sha256: str | None = None,
    verification: str = "computed",
) -> dict[str, Any]:
    if not path.is_file():
        raise IntegrityError(f"Required artifact is missing: {path}")
    actual = actual_sha256 or sha256_file(path)
    try:
        display_path = path.resolve().relative_to(delivery_root.resolve()).as_posix()
    except ValueError:
        display_path = str(path.resolve())
    return {
        "run_identifier": spec.identifier if spec else "",
        "role": role,
        "path": display_path,
        "sha256": actual,
        "bytes": path.stat().st_size,
        "verification": verification,
    }


def require_equal(actual: Any, expected: Any, context: str) -> None:
    if actual != expected:
        raise IntegrityError(f"{context}: expected {expected!r}, found {actual!r}.")


def declared_artifact_hash(
    manifest: Mapping[str, Any], relative_path: str, manifest_path: Path
) -> str:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise IntegrityError(f"{manifest_path} has no artifact hash map.")
    record = artifacts.get(relative_path)
    if not isinstance(record, dict) or not isinstance(record.get("sha256"), str):
        raise IntegrityError(
            f"{manifest_path} has no SHA-256 for artifact {relative_path!r}."
        )
    return str(record["sha256"])


def verify_small_training_artifact(
    run_dir: Path,
    manifest: Mapping[str, Any],
    name: str,
    delivery_root: Path,
    spec: RunSpec,
) -> dict[str, Any]:
    path = run_dir / name
    declared = declared_artifact_hash(manifest, name, run_dir / "run_manifest.json")
    actual = sha256_file(path)
    if actual != declared:
        raise IntegrityError(f"Training artifact hash mismatch for {path}.")
    return record_artifact(
        path,
        delivery_root,
        spec,
        f"training_{name}",
        actual_sha256=actual,
    )


def validate_frozen_run_config(
    spec: RunSpec,
    run_config: Mapping[str, Any],
    run_manifest: Mapping[str, Any],
    formal_script_sha256: str,
) -> str:
    immutable = run_config.get("immutable_config")
    if not isinstance(immutable, dict):
        raise IntegrityError(f"{spec.run_dir / 'run_config.json'} lacks immutable_config.")
    require_equal(
        immutable.get("schema_version"),
        "formal-retrieval-v1",
        f"{spec.identifier} immutable schema",
    )
    declared = run_config.get("run_config_sha256")
    if not isinstance(declared, str) or canonical_sha256(immutable) != declared:
        raise IntegrityError(f"Immutable run-configuration hash mismatch for {spec.identifier}.")
    require_equal(
        run_manifest.get("run_config_sha256"),
        declared,
        f"{spec.identifier} run manifest configuration hash",
    )
    require_equal(immutable.get("dataset"), spec.dataset, f"{spec.identifier} dataset")
    require_equal(immutable.get("seed"), spec.seed, f"{spec.identifier} seed")
    model = immutable.get("model")
    if not isinstance(model, dict):
        raise IntegrityError(f"{spec.identifier} has no model configuration.")
    require_equal(model.get("variant"), spec.variant, f"{spec.identifier} variant")
    require_equal(model.get("backbone"), spec.backbone, f"{spec.identifier} backbone")
    require_equal(
        int(model.get("embed_dim", -1)),
        spec.embed_dim,
        f"{spec.identifier} embedding dimension",
    )
    require_equal(float(model.get("dropout", -1.0)), 0.20, "model dropout")
    require_equal(int(model.get("image_size", -1)), 224, "model image size")
    require_equal(int(model.get("resize_size", -1)), 256, "model resize size")
    pretrained = model.get("pretrained_initialization")
    if not isinstance(pretrained, dict):
        raise IntegrityError(f"{spec.identifier} lacks pretrained-weight provenance.")
    uses_visual = spec.variant in {
        "visual",
        "visual_content",
        "visual_style",
        "full",
    }
    require_equal(
        pretrained.get("enabled"),
        uses_visual,
        f"{spec.identifier} pretrained visual initialization",
    )
    optimization = immutable.get("optimization")
    if not isinstance(optimization, dict):
        raise IntegrityError(f"{spec.identifier} has no optimization configuration.")
    frozen_optimization = {
        "epochs": 80,
        "learning_rate": 0.0003,
        "backbone_lr_multiplier": 0.1,
        "weight_decay": 0.0001,
        "warmup_epochs": 5,
        "gradient_clip_norm": 5.0,
        "identities_per_batch": 16,
        "instances_per_identity": 4,
        "samples_per_class_per_epoch": 0,
        "steps_per_epoch_requested": 0,
        "sampler_schedule_audited_epochs": 80,
        "sampler_step_count_fixed_across_epochs": True,
        "amp": True,
    }
    for key, expected in frozen_optimization.items():
        require_equal(
            optimization.get(key),
            expected,
            f"{spec.identifier} optimization.{key}",
        )
    if int(optimization.get("steps_per_epoch_actual", 0)) <= 0:
        raise IntegrityError(f"{spec.identifier} has no positive fixed step count.")
    protocol = immutable.get("protocol")
    if not isinstance(protocol, dict):
        raise IntegrityError(f"{spec.identifier} has no protocol summary.")
    require_equal(
        float(protocol.get("holdout_fraction", -1.0)),
        0.0,
        f"{spec.identifier} holdout fraction",
    )
    require_equal(
        int(protocol.get("official_test_images_used_by_train_or_validation", -1)),
        0,
        f"{spec.identifier} training/test isolation",
    )
    expected_scale = (
        {
            "official_train_identity_count": 701,
            "fit_identity_count": 701,
            "fit_query_image_count": 40513,
        }
        if spec.dataset == "university1652"
        else {
            "official_train_identity_count": 120,
            "fit_identity_count": 120,
            "fit_query_image_count": 24000,
        }
    )
    for key, expected in expected_scale.items():
        require_equal(
            int(protocol.get(key, -1)),
            expected,
            f"{spec.identifier} protocol.{key}",
        )
    require_equal(
        immutable.get("code_sha256"),
        formal_script_sha256,
        f"{spec.identifier} formal code hash",
    )
    cli = run_config.get("cli")
    if isinstance(cli, dict):
        require_equal(float(cli.get("val_fraction", -1.0)), 0.0, "CLI val_fraction")
        require_equal(int(cli.get("patience", -1)), 0, "CLI patience")
    return declared


def validate_history(
    spec: RunSpec,
    history: Sequence[Mapping[str, Any]],
    run_config: Mapping[str, Any],
) -> None:
    if len(history) != EXPECTED_TRAINING_EPOCHS:
        raise IntegrityError(
            f"{spec.identifier} history has {len(history)} rows, expected 80."
        )
    immutable = run_config["immutable_config"]
    expected_steps = int(immutable["optimization"]["steps_per_epoch_actual"])
    for epoch, row in enumerate(history):
        require_equal(int(row.get("epoch", -1)), epoch, f"{spec.identifier} history epoch")
        require_equal(
            int(row.get("optimizer_steps", -1)),
            expected_steps,
            f"{spec.identifier} optimizer steps at epoch {epoch}",
        )
        if row.get("validation_selection_mAP", "missing") is not None:
            raise IntegrityError(
                f"{spec.identifier} unexpectedly selected on validation at epoch {epoch}."
            )
        validation = row.get("validation")
        if validation not in ({}, None):
            raise IntegrityError(
                f"{spec.identifier} unexpectedly contains validation task metrics."
            )


def task_membership_hash(paths: np.ndarray, labels: np.ndarray) -> str:
    normalized_paths = [canonical_query_path(item) for item in paths]
    if len(normalized_paths) != len(set(normalized_paths)):
        raise IntegrityError("Per-query array contains duplicate canonical query paths.")
    label_text = as_text_array(labels).tolist()
    pairs = sorted(zip(normalized_paths, label_text, strict=True))
    return canonical_sha256(pairs)


def metric_close(actual: float, expected: float, name: str, path: Path) -> None:
    tolerance = 2e-7 if name != "mean_top1_margin" else 2e-6
    if not math.isclose(actual, expected, rel_tol=tolerance, abs_tol=tolerance):
        raise IntegrityError(
            f"{path}: recomputed {name}={actual:.12g}, metrics.json has "
            f"{expected:.12g}."
        )


def validate_per_query_arrays(
    path: Path,
    metrics: Mapping[str, Any],
) -> tuple[str, int]:
    required = {
        "margin",
        "correct",
        "per_query_official_trapezoid_AP",
        "reciprocal_rank",
        "query_paths",
        "query_labels",
        "top1_gallery_indices",
        "top1_gallery_paths",
        "top1_gallery_labels",
    }
    try:
        with np.load(path, allow_pickle=False) as payload:
            missing = required - set(payload.files)
            if missing:
                raise IntegrityError(f"{path} is missing arrays: {sorted(missing)}")
            arrays = {name: np.asarray(payload[name]) for name in required}
    except (OSError, ValueError) as error:
        if isinstance(error, IntegrityError):
            raise
        raise IntegrityError(f"Cannot read per-query arrays from {path}: {error}") from error

    count = int(metrics.get("queries", -1))
    if count <= 0:
        raise IntegrityError(f"{path}: metrics.json has invalid query count {count}.")
    for name, values in arrays.items():
        if values.ndim != 1 or len(values) != count:
            raise IntegrityError(
                f"{path}: {name} shape {values.shape} does not match {count} queries."
            )
    query_paths = as_text_array(arrays["query_paths"])
    query_labels = as_text_array(arrays["query_labels"])
    top1_labels = as_text_array(arrays["top1_gallery_labels"])
    correct = np.asarray(arrays["correct"], dtype=bool)
    if not np.array_equal(correct, query_labels == top1_labels):
        raise IntegrityError(f"{path}: correct flags disagree with top-1/query labels.")
    aps = np.asarray(arrays["per_query_official_trapezoid_AP"], dtype=np.float64)
    reciprocal = np.asarray(arrays["reciprocal_rank"], dtype=np.float64)
    margins = np.asarray(arrays["margin"], dtype=np.float64)
    if not np.all(np.isfinite(aps)) or np.any((aps < 0.0) | (aps > 1.0)):
        raise IntegrityError(f"{path}: per-query official AP values are outside [0, 1].")
    if not np.all(np.isfinite(reciprocal)) or np.any(
        (reciprocal <= 0.0) | (reciprocal > 1.0)
    ):
        raise IntegrityError(f"{path}: reciprocal ranks are outside (0, 1].")
    if not np.all(np.isfinite(margins)):
        raise IntegrityError(f"{path}: top-1 margins contain non-finite values.")
    reciprocal_positions = np.rint(1.0 / reciprocal).astype(np.int64)
    if np.any(reciprocal_positions < 1) or not np.allclose(
        reciprocal,
        1.0 / reciprocal_positions,
        rtol=2e-6,
        atol=2e-7,
    ):
        raise IntegrityError(f"{path}: reciprocal ranks do not encode integer ranks.")
    derived = {
        "r_at_1": float(np.mean(reciprocal_positions <= 1)),
        "r_at_5": float(np.mean(reciprocal_positions <= 5)),
        "r_at_10": float(np.mean(reciprocal_positions <= 10)),
        "r_at_20": float(np.mean(reciprocal_positions <= 20)),
        "official_trapezoid_mAP": float(np.mean(aps, dtype=np.float64)),
        "MRR": float(np.mean(reciprocal, dtype=np.float64)),
        "mean_top1_margin": float(np.mean(margins, dtype=np.float64)),
    }
    if not np.array_equal(correct, reciprocal_positions == 1):
        raise IntegrityError(f"{path}: correct flags disagree with reciprocal rank.")
    for name, actual in derived.items():
        if name not in metrics:
            raise IntegrityError(f"{path}: metrics.json is missing {name}.")
        metric_close(actual, float(metrics[name]), name, path)
    gallery = int(metrics.get("gallery", -1))
    indices = np.asarray(arrays["top1_gallery_indices"], dtype=np.int64)
    if gallery <= 0 or np.any((indices < 0) | (indices >= gallery)):
        raise IntegrityError(f"{path}: top-1 gallery indices are out of range.")
    return task_membership_hash(query_paths, query_labels), count


def metrics_row(
    spec: RunSpec,
    task: str,
    metrics: Mapping[str, Any],
    run_config_sha256: str,
    checkpoint_sha256: str,
    metrics_sha256: str,
    array_sha256: str,
    membership_sha256: str,
    protocol_membership_sha256: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "family": spec.family,
        "dataset": spec.dataset,
        "task": task,
        "variant": spec.variant,
        "seed": spec.seed,
        "backbone": spec.backbone,
        "embed_dim": spec.embed_dim,
        "setting": spec.setting,
        "queries": int(metrics["queries"]),
        "gallery": int(metrics["gallery"]),
        "query_identities": int(metrics["query_identities"]),
        "gallery_identities": int(metrics["gallery_identities"]),
        "protocol": str(metrics.get("protocol", "")),
        "run_config_sha256": run_config_sha256,
        "checkpoint_sha256": checkpoint_sha256,
        "metrics_sha256": metrics_sha256,
        "per_query_arrays_sha256": array_sha256,
        "query_membership_sha256": membership_sha256,
        "protocol_membership_sha256": protocol_membership_sha256,
    }
    for name in METRICS:
        value = float(metrics[name])
        row[f"{name}_pct" if name in PERCENT_METRICS else name] = (
            100.0 * value if name in PERCENT_METRICS else value
        )
    return row


def validate_completed_run(
    spec: RunSpec,
    delivery_root: Path,
    formal_script_sha256: str,
) -> ValidRun:
    run_manifest_path = spec.run_dir / "run_manifest.json"
    run_config_path = spec.run_dir / "run_config.json"
    history_path = spec.run_dir / "history.json"
    best_path = spec.run_dir / "best.pt"
    last_path = spec.run_dir / "last.pt"
    run_manifest = load_json(run_manifest_path)
    verify_payload_hash(run_manifest, run_manifest_path)
    require_equal(
        run_manifest.get("schema_version"),
        "formal-retrieval-v1",
        f"{spec.identifier} run-manifest schema",
    )
    require_equal(run_manifest.get("status"), "completed", f"{spec.identifier} status")
    require_equal(
        int(run_manifest.get("epochs_completed", -1)),
        EXPECTED_TRAINING_EPOCHS,
        f"{spec.identifier} epochs",
    )
    require_equal(
        run_manifest.get("test_protocol_was_evaluated"),
        False,
        f"{spec.identifier} training-time official-test use",
    )
    require_equal(
        int(run_manifest.get("best_epoch", -1)),
        EXPECTED_TRAINING_EPOCHS - 1,
        f"{spec.identifier} selected epoch",
    )
    if run_manifest.get("best_validation_mAP", "missing") is not None:
        raise IntegrityError(f"{spec.identifier} has a validation-selected checkpoint.")
    for path in (run_config_path, history_path, best_path, last_path):
        if not path.is_file():
            raise IntegrityError(f"{spec.identifier} is missing required artifact {path}.")
    run_config = load_json(run_config_path)
    run_config_sha = validate_frozen_run_config(
        spec, run_config, run_manifest, formal_script_sha256
    )
    history = load_json_list(history_path)
    validate_history(spec, history, run_config)

    input_artifacts = [
        record_artifact(run_manifest_path, delivery_root, spec, "training_manifest"),
        verify_small_training_artifact(
            spec.run_dir, run_manifest, "run_config.json", delivery_root, spec
        ),
        verify_small_training_artifact(
            spec.run_dir, run_manifest, "history.json", delivery_root, spec
        ),
    ]
    declared_best = declared_artifact_hash(run_manifest, "best.pt", run_manifest_path)
    checkpoint_sha = sha256_file(best_path)
    if checkpoint_sha != declared_best:
        raise IntegrityError(f"Checkpoint hash mismatch for {best_path}.")
    input_artifacts.append(
        record_artifact(
            best_path,
            delivery_root,
            spec,
            "selected_checkpoint",
            actual_sha256=checkpoint_sha,
        )
    )
    declared_last = declared_artifact_hash(run_manifest, "last.pt", run_manifest_path)
    input_artifacts.append(
        {
            **record_artifact(
                last_path,
                delivery_root,
                spec,
                "last_checkpoint",
                actual_sha256=declared_last,
                verification="declared_manifest_hash_and_file_presence",
            )
        }
    )

    evaluation_manifest_path = spec.evaluation_dir / "evaluation_manifest.json"
    metrics_path = spec.evaluation_dir / "metrics.json"
    metrics_csv_path = spec.evaluation_dir / "metrics.csv"
    for path in (evaluation_manifest_path, metrics_path, metrics_csv_path):
        if not path.is_file():
            raise IntegrityError(f"{spec.identifier} is missing evaluation artifact {path}.")
    evaluation_manifest = load_json(evaluation_manifest_path)
    verify_payload_hash(evaluation_manifest, evaluation_manifest_path)
    require_equal(
        evaluation_manifest.get("schema_version"),
        "formal-retrieval-v1",
        f"{spec.identifier} evaluation-manifest schema",
    )
    require_equal(
        evaluation_manifest.get("status"),
        "completed",
        f"{spec.identifier} evaluation status",
    )
    require_equal(
        evaluation_manifest.get("dataset"),
        spec.dataset,
        f"{spec.identifier} evaluation dataset",
    )
    checkpoint = evaluation_manifest.get("checkpoint")
    if not isinstance(checkpoint, dict):
        raise IntegrityError(f"{spec.identifier} evaluation has no checkpoint record.")
    require_equal(checkpoint.get("sha256"), checkpoint_sha, "evaluation checkpoint SHA")
    require_equal(
        checkpoint.get("training_run_config_sha256"),
        run_config_sha,
        "evaluation training-configuration SHA",
    )
    require_equal(checkpoint.get("variant"), spec.variant, "evaluation variant")
    require_equal(
        int(checkpoint.get("selected_training_epoch", -1)),
        EXPECTED_TRAINING_EPOCHS - 1,
        "evaluation selected epoch",
    )
    controls = evaluation_manifest.get("leakage_controls")
    required_controls = {
        "labels_and_splits_from_cache_used": False,
        "labels_and_splits_derived_from_dataset_paths_and_official_manifest": True,
        "each_image_encoded_independently": True,
        "test_used_during_training_or_model_selection": False,
        "all_official_queries_used": True,
        "all_official_gallery_images_used": True,
    }
    if not isinstance(controls, dict):
        raise IntegrityError(f"{spec.identifier} has no evaluation leakage controls.")
    for key, expected in required_controls.items():
        require_equal(controls.get(key), expected, f"{spec.identifier} control {key}")
    protocol_membership = evaluation_manifest.get("protocol_membership_sha256")
    if not isinstance(protocol_membership, str):
        raise IntegrityError(f"{spec.identifier} lacks protocol-membership hash.")

    metrics_sha = sha256_file(metrics_path)
    declared_metrics = declared_artifact_hash(
        evaluation_manifest, "metrics.json", evaluation_manifest_path
    )
    if metrics_sha != declared_metrics:
        raise IntegrityError(f"Evaluation metrics hash mismatch for {metrics_path}.")
    metrics_csv_sha = sha256_file(metrics_csv_path)
    declared_metrics_csv = declared_artifact_hash(
        evaluation_manifest, "metrics.csv", evaluation_manifest_path
    )
    if metrics_csv_sha != declared_metrics_csv:
        raise IntegrityError(f"Evaluation CSV hash mismatch for {metrics_csv_path}.")
    input_artifacts.extend(
        [
            record_artifact(
                evaluation_manifest_path,
                delivery_root,
                spec,
                "evaluation_manifest",
            ),
            record_artifact(
                metrics_path,
                delivery_root,
                spec,
                "evaluation_metrics",
                actual_sha256=metrics_sha,
            ),
            record_artifact(
                metrics_csv_path,
                delivery_root,
                spec,
                "evaluation_metrics_csv",
                actual_sha256=metrics_csv_sha,
            ),
        ]
    )

    metrics_payload = load_json(metrics_path)
    require_equal(
        metrics_payload.get("schema_version"),
        "formal-retrieval-v1",
        f"{spec.identifier} metrics schema",
    )
    require_equal(metrics_payload.get("unit"), "fraction", "metrics unit")
    require_equal(metrics_payload.get("full_gallery"), True, "full-gallery flag")
    results = metrics_payload.get("results")
    if not isinstance(results, dict):
        raise IntegrityError(f"{metrics_path} has no task result object.")
    expected_tasks = TASKS[spec.dataset]
    if set(results) != set(expected_tasks):
        raise IntegrityError(
            f"{metrics_path} task set differs from the exact official task set. "
            f"Expected {list(expected_tasks)}, found {sorted(results)}.  Aggregate or "
            "duplicate overall/subset rows are not accepted."
        )
    task_scale = evaluation_manifest.get("task_scale")
    if not isinstance(task_scale, dict) or set(task_scale) != set(expected_tasks):
        raise IntegrityError(f"{evaluation_manifest_path} task-scale set is invalid.")

    arrays: dict[str, ArrayDescriptor] = {}
    metric_rows: list[dict[str, Any]] = []
    for task in expected_tasks:
        values = results[task]
        if not isinstance(values, dict):
            raise IntegrityError(f"{metrics_path}: task {task} is not an object.")
        for name in METRICS:
            if name not in values or not math.isfinite(float(values[name])):
                raise IntegrityError(f"{metrics_path}: task {task} has invalid {name}.")
        for name in PERCENT_METRICS:
            value = float(values[name])
            if value < 0.0 or value > 1.0:
                raise IntegrityError(f"{metrics_path}: task {task} {name} outside [0, 1].")
        scale = task_scale[task]
        if not isinstance(scale, dict):
            raise IntegrityError(f"{evaluation_manifest_path}: invalid scale for {task}.")
        require_equal(
            int(values.get("queries", -1)),
            int(scale.get("queries", -2)),
            f"{task} query scale",
        )
        require_equal(
            int(values.get("gallery", -1)),
            int(scale.get("gallery_images", -2)),
            f"{task} gallery scale",
        )
        array_relative = f"per_query_arrays/{slugify(task)}_per_query.npz"
        array_path = spec.evaluation_dir / Path(array_relative)
        if not array_path.is_file():
            raise IntegrityError(f"Missing per-query arrays: {array_path}")
        array_sha = sha256_file(array_path)
        declared_array = declared_artifact_hash(
            evaluation_manifest, array_relative, evaluation_manifest_path
        )
        if array_sha != declared_array:
            raise IntegrityError(f"Per-query array hash mismatch for {array_path}.")
        membership_sha, queries = validate_per_query_arrays(array_path, values)
        arrays[task] = ArrayDescriptor(
            path=array_path,
            sha256=array_sha,
            query_membership_sha256=membership_sha,
            queries=queries,
        )
        input_artifacts.append(
            record_artifact(
                array_path,
                delivery_root,
                spec,
                f"per_query_arrays:{task}",
                actual_sha256=array_sha,
            )
        )
        metric_rows.append(
            metrics_row(
                spec,
                task,
                values,
                run_config_sha,
                checkpoint_sha,
                metrics_sha,
                array_sha,
                membership_sha,
                protocol_membership,
            )
        )
    return ValidRun(
        spec=spec,
        metric_rows=metric_rows,
        arrays=arrays,
        run_config_sha256=run_config_sha,
        checkpoint_sha256=checkpoint_sha,
        metrics_sha256=metrics_sha,
        protocol_membership_sha256=protocol_membership,
        code_sha256=formal_script_sha256,
        input_artifacts=input_artifacts,
    )


def classify_run(
    spec: RunSpec,
    delivery_root: Path,
    formal_script_sha256: str,
) -> tuple[dict[str, Any], ValidRun | None, str | None]:
    training_manifest_path = spec.run_dir / "run_manifest.json"
    evaluation_manifest_path = spec.evaluation_dir / "evaluation_manifest.json"
    audit = {
        "identifier": spec.identifier,
        "family": spec.family,
        "dataset": spec.dataset,
        "variant": spec.variant,
        "seed": spec.seed,
        "backbone": spec.backbone,
        "embed_dim": spec.embed_dim,
        "setting": spec.setting,
        "training_manifest": str(training_manifest_path),
        "evaluation_manifest": str(evaluation_manifest_path),
        "status": "",
        "reason": "",
    }
    if not training_manifest_path.is_file():
        audit.update(status="incomplete", reason="training manifest missing")
        return audit, None, None
    try:
        training_manifest = load_json(training_manifest_path)
    except IntegrityError as error:
        audit.update(status="invalid", reason=str(error))
        return audit, None, str(error)
    training_status = training_manifest.get("status")
    if training_status != "completed":
        if evaluation_manifest_path.is_file():
            try:
                evaluation = load_json(evaluation_manifest_path)
            except IntegrityError:
                evaluation = {}
            if evaluation.get("status") == "completed":
                message = "official evaluation completed before frozen training completed"
                audit.update(status="invalid", reason=message)
                return audit, None, message
        audit.update(
            status="incomplete",
            reason=f"training status is {training_status!r}, not 'completed'",
        )
        return audit, None, None
    if not evaluation_manifest_path.is_file():
        audit.update(status="incomplete", reason="evaluation manifest missing")
        return audit, None, None
    try:
        evaluation_manifest = load_json(evaluation_manifest_path)
    except IntegrityError as error:
        audit.update(status="invalid", reason=str(error))
        return audit, None, str(error)
    if evaluation_manifest.get("status") != "completed":
        audit.update(
            status="incomplete",
            reason=(
                f"evaluation status is {evaluation_manifest.get('status')!r}, "
                "not 'completed'"
            ),
        )
        return audit, None, None
    try:
        valid = validate_completed_run(spec, delivery_root, formal_script_sha256)
    except (IntegrityError, OSError, ValueError, TypeError) as error:
        message = f"{type(error).__name__}: {error}"
        audit.update(status="invalid", reason=message)
        return audit, None, message
    audit.update(status="valid", reason="")
    return audit, valid, None


def ensure_cross_run_consistency(valid_runs: Sequence[ValidRun]) -> None:
    memberships: dict[tuple[str, str], set[str]] = {}
    scales: dict[tuple[str, str], set[tuple[int, int]]] = {}
    protocol_hashes: dict[str, set[str]] = {}
    for run in valid_runs:
        protocol_hashes.setdefault(run.spec.dataset, set()).add(
            run.protocol_membership_sha256
        )
        for row in run.metric_rows:
            key = (run.spec.dataset, str(row["task"]))
            memberships.setdefault(key, set()).add(str(row["query_membership_sha256"]))
            scales.setdefault(key, set()).add((int(row["queries"]), int(row["gallery"])))
    for key, values in memberships.items():
        if len(values) != 1:
            raise IntegrityError(f"Query membership differs across runs for {key}.")
    for key, values in scales.items():
        if len(values) != 1:
            raise IntegrityError(f"Official task scale differs across runs for {key}.")
    for dataset, values in protocol_hashes.items():
        if len(values) != 1:
            raise IntegrityError(
                f"Protocol-membership hash differs across completed {dataset} runs."
            )


def main_metric_rows(valid_runs: Sequence[ValidRun]) -> list[dict[str, Any]]:
    rows = [
        row
        for run in valid_runs
        if run.spec.family == "formal_main"
        for row in run.metric_rows
    ]
    rows.sort(
        key=lambda row: (
            DATASET_ORDER.index(str(row["dataset"])),
            TASKS[str(row["dataset"])].index(str(row["task"])),
            VARIANT_ORDER.index(str(row["variant"])),
            int(row["seed"]),
        )
    )
    return rows


def sensitivity_metric_rows(valid_runs: Sequence[ValidRun]) -> list[dict[str, Any]]:
    setting_order = ("backbone_resnet50", "embed_dim_256", "embed_dim_1024")
    rows = [
        row
        for run in valid_runs
        if run.spec.family == "formal_sensitivity"
        for row in run.metric_rows
    ]
    rows.sort(
        key=lambda row: (
            DATASET_ORDER.index(str(row["dataset"])),
            TASKS[str(row["dataset"])].index(str(row["task"])),
            setting_order.index(str(row["setting"])),
        )
    )
    return rows


def summarize_main(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    index: dict[tuple[str, str, str], list[Mapping[str, Any]]] = {}
    for row in rows:
        key = (str(row["dataset"]), str(row["task"]), str(row["variant"]))
        index.setdefault(key, []).append(row)
    summaries: list[dict[str, Any]] = []
    for dataset in DATASET_ORDER:
        for task in TASKS[dataset]:
            for variant in VARIANT_ORDER:
                values = sorted(
                    index.get((dataset, task, variant), []),
                    key=lambda row: int(row["seed"]),
                )
                seeds = [int(row["seed"]) for row in values]
                summary: dict[str, Any] = {
                    "dataset": dataset,
                    "task": task,
                    "variant": variant,
                    "n_seeds": len(values),
                    "seeds": "|".join(str(seed) for seed in seeds),
                    "complete_seed_triplet": seeds == list(MAIN_SEEDS),
                    "queries": int(values[0]["queries"]) if values else None,
                    "gallery": int(values[0]["gallery"]) if values else None,
                }
                for metric in SUMMARY_METRICS:
                    key = f"{metric}_pct"
                    observations = [float(row[key]) for row in values]
                    summary[f"{metric}_mean_pct"] = (
                        statistics.fmean(observations) if observations else None
                    )
                    summary[f"{metric}_sample_sd_pct"] = (
                        statistics.stdev(observations)
                        if len(observations) >= 2
                        else None
                    )
                summaries.append(summary)
    return summaries


def load_pair_arrays(
    visual: ArrayDescriptor,
    full: ArrayDescriptor,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    def selected(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        with np.load(path, allow_pickle=False) as payload:
            paths = np.asarray(
                [canonical_query_path(item) for item in payload["query_paths"]],
                dtype=str,
            )
            labels = as_text_array(payload["query_labels"])
            correct = np.asarray(payload["correct"], dtype=bool)
        return paths, labels, correct

    visual_paths, visual_labels, visual_correct = selected(visual.path)
    full_paths, full_labels, full_correct = selected(full.path)
    if len(visual_paths) != len(set(visual_paths.tolist())):
        raise IntegrityError(f"Duplicate visual query paths in {visual.path}.")
    if len(full_paths) != len(set(full_paths.tolist())):
        raise IntegrityError(f"Duplicate full query paths in {full.path}.")
    lookup = {path: index for index, path in enumerate(full_paths.tolist())}
    if set(visual_paths.tolist()) != set(lookup):
        raise IntegrityError(
            f"Visual/full query membership differs: {visual.path} vs {full.path}."
        )
    order = np.asarray([lookup[path] for path in visual_paths.tolist()], dtype=np.int64)
    aligned_labels = full_labels[order]
    if not np.array_equal(visual_labels, aligned_labels):
        raise IntegrityError(
            f"Visual/full query labels differ after path alignment for {visual.path}."
        )
    return visual_correct, full_correct[order], visual_paths


def paired_binary_bootstrap(
    difference: np.ndarray,
    samples: int,
    seed: int,
) -> tuple[float, float]:
    """Exact ordinary query bootstrap via the {-1, 0, +1} count distribution."""
    values = np.asarray(difference, dtype=np.int8)
    if values.ndim != 1 or values.size == 0 or not np.all(np.isin(values, (-1, 0, 1))):
        raise ValueError("Paired binary difference must be a non-empty {-1,0,1} vector.")
    counts = np.asarray(
        [np.sum(values == -1), np.sum(values == 0), np.sum(values == 1)],
        dtype=np.int64,
    )
    probabilities = counts.astype(np.float64) / values.size
    rng = np.random.default_rng(seed)
    draws = rng.multinomial(values.size, probabilities, size=samples)
    means = (draws[:, 2] - draws[:, 0]).astype(np.float64) / values.size
    return (
        float(np.quantile(means, 0.025)),
        float(np.quantile(means, 0.975)),
    )


def exact_two_sided_mcnemar_log10(a_only: int, b_only: int) -> float:
    """Return log10 of the two-sided exact conditional McNemar p-value."""
    if a_only < 0 or b_only < 0:
        raise ValueError("Discordant counts cannot be negative.")
    discordant = a_only + b_only
    if discordant == 0:
        return 0.0
    smaller = min(a_only, b_only)
    log_terms = np.empty(smaller + 1, dtype=np.float64)
    log_terms[0] = -discordant * math.log(2.0)
    if smaller:
        k = np.arange(1, smaller + 1, dtype=np.float64)
        increments = np.log(discordant - k + 1.0) - np.log(k)
        log_terms[1:] = log_terms[0] + np.cumsum(increments)
    maximum = float(np.max(log_terms))
    log_cdf = maximum + math.log(float(np.exp(log_terms - maximum).sum()))
    natural_log_p = min(0.0, math.log(2.0) + log_cdf)
    return natural_log_p / math.log(10.0)


def probability_text(log10_p: float) -> str:
    """Format a probability without ever emitting a floating-point zero."""
    if not math.isfinite(log10_p) or log10_p > 1e-12:
        raise ValueError(f"Invalid log10 probability {log10_p}.")
    if log10_p >= -1e-12:
        return "1"
    if log10_p < -300.0:
        return "<1e-300"
    exponent = math.floor(log10_p)
    mantissa = 10.0 ** (log10_p - exponent)
    return f"{mantissa:.8g}e{exponent:+d}"


def holm_logspace(rows: list[dict[str, Any]]) -> None:
    order = sorted(
        range(len(rows)),
        key=lambda index: float(rows[index]["exact_mcnemar_log10_p"]),
    )
    running = -math.inf
    family_size = len(rows)
    for rank, index in enumerate(order):
        factor = family_size - rank
        candidate = float(rows[index]["exact_mcnemar_log10_p"]) + math.log10(factor)
        running = min(0.0, max(running, candidate))
        rows[index]["holm_adjusted_log10_p"] = running
        rows[index]["holm_adjusted_p"] = probability_text(running)
        rows[index]["holm_family_size"] = family_size
        rows[index]["holm_family"] = (
            "all 33 visual-vs-full task-by-seed comparisons"
        )
        rows[index]["reject_holm_0_05"] = bool(running < math.log10(0.05))
        rows[index]["holm_status"] = "complete"


def visual_full_statistics(
    valid_runs: Sequence[ValidRun],
    samples: int,
    bootstrap_seed: int,
    full_matrix: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    lookup = {
        (run.spec.dataset, run.spec.variant, run.spec.seed): run
        for run in valid_runs
        if run.spec.family == "formal_main"
    }
    bootstrap_rows: list[dict[str, Any]] = []
    mcnemar_rows: list[dict[str, Any]] = []
    comparison_index = 0
    for dataset in DATASET_ORDER:
        for task in TASKS[dataset]:
            for seed in MAIN_SEEDS:
                visual = lookup.get((dataset, "visual", seed))
                full = lookup.get((dataset, "full", seed))
                if visual is None or full is None:
                    comparison_index += 1
                    continue
                visual_correct, full_correct, query_paths = load_pair_arrays(
                    visual.arrays[task], full.arrays[task]
                )
                difference = (
                    full_correct.astype(np.int8) - visual_correct.astype(np.int8)
                )
                current_seed = bootstrap_seed + comparison_index
                low, high = paired_binary_bootstrap(difference, samples, current_seed)
                visual_only = int(np.sum(visual_correct & ~full_correct))
                full_only = int(np.sum(~visual_correct & full_correct))
                common = {
                    "dataset": dataset,
                    "task": task,
                    "seed": seed,
                    "method_a": "visual",
                    "method_b": "full",
                    "difference_definition": "full minus visual",
                    "paired_queries": int(len(difference)),
                    "query_membership_sha256": canonical_sha256(
                        sorted(query_paths.tolist())
                    ),
                    "visual_r_at_1_pct": 100.0 * float(np.mean(visual_correct)),
                    "full_r_at_1_pct": 100.0 * float(np.mean(full_correct)),
                    "difference_r_at_1_pp": 100.0 * float(np.mean(difference)),
                }
                bootstrap_rows.append(
                    {
                        **common,
                        "ci95_low_pp": 100.0 * low,
                        "ci95_high_pp": 100.0 * high,
                        "bootstrap_samples": samples,
                        "bootstrap_seed": current_seed,
                        "bootstrap_unit": "path-aligned official query",
                        "bootstrap_algorithm": (
                            "ordinary paired resampling; exact multinomial "
                            "category-count equivalent for binary R@1 differences"
                        ),
                    }
                )
                log10_p = exact_two_sided_mcnemar_log10(visual_only, full_only)
                mcnemar_rows.append(
                    {
                        **common,
                        "visual_correct_full_wrong": visual_only,
                        "visual_wrong_full_correct": full_only,
                        "discordant_queries": visual_only + full_only,
                        "exact_mcnemar_log10_p": log10_p,
                        "exact_mcnemar_p": probability_text(log10_p),
                        "holm_adjusted_log10_p": None,
                        "holm_adjusted_p": "",
                        "holm_family_size": None,
                        "holm_family": "",
                        "reject_holm_0_05": None,
                        "holm_status": "withheld_until_complete_33-test_family",
                    }
                )
                comparison_index += 1
    expected = EXPECTED_PAIRWISE_TESTS
    if full_matrix:
        if len(mcnemar_rows) != expected:
            raise IntegrityError(
                f"Full matrix yielded {len(mcnemar_rows)} visual/full comparisons, "
                f"expected {expected}."
            )
        holm_logspace(mcnemar_rows)
    return bootstrap_rows, mcnemar_rows


def sensitivity_with_reference(
    main_rows: Sequence[Mapping[str, Any]],
    sensitivity_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    base = [
        {**dict(row), "sensitivity_role": "main_full_seed1_reference"}
        for row in main_rows
        if row["variant"] == "full" and int(row["seed"]) == 1
    ]
    sensitivity = [
        {**dict(row), "sensitivity_role": "frozen_sensitivity_run"}
        for row in sensitivity_rows
    ]
    setting_order = {
        "full": 0,
        "backbone_resnet50": 1,
        "embed_dim_256": 2,
        "embed_dim_1024": 3,
    }
    rows = base + sensitivity
    rows.sort(
        key=lambda row: (
            DATASET_ORDER.index(str(row["dataset"])),
            TASKS[str(row["dataset"])].index(str(row["task"])),
            setting_order[str(row["setting"])],
        )
    )
    return rows


def csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({field: csv_value(row.get(field)) for field in fields})
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def ordered_fields(rows: Sequence[Mapping[str, Any]], preferred: Sequence[str]) -> list[str]:
    seen = set(preferred)
    remaining = sorted({key for row in rows for key in row} - seen)
    return list(preferred) + remaining


TASK_LABELS = {
    "university1652_drone_to_satellite": r"Drone$\rightarrow$Satellite",
    "university1652_satellite_to_drone": r"Satellite$\rightarrow$Drone",
    "university1652_street_to_satellite": r"Street$\rightarrow$Satellite",
    **{
        f"sues200_uav_{altitude}m_to_satellite": (
            rf"UAV {altitude}\,m$\rightarrow$Satellite"
        )
        for altitude in SUES_ALTITUDES
    },
    **{
        f"sues200_satellite_to_uav_{altitude}m": (
            rf"Satellite$\rightarrow$UAV {altitude}\,m"
        )
        for altitude in SUES_ALTITUDES
    },
}

VARIANT_LABELS = {
    "visual": "Visual",
    "content": "Content",
    "style": "Style",
    "visual_content": "Visual+Content",
    "visual_style": "Visual+Style",
    "full": "Full",
}

SETTING_LABELS = {
    "full": "ResNet-18, 512-D (main reference)",
    "backbone_resnet50": "ResNet-50, 512-D",
    "embed_dim_256": "ResNet-18, 256-D",
    "embed_dim_1024": "ResNet-18, 1024-D",
}


def mean_sd_tex(row: Mapping[str, Any], metric: str) -> str:
    mean = row.get(f"{metric}_mean_pct")
    sd = row.get(f"{metric}_sample_sd_pct")
    count = int(row.get("n_seeds", 0))
    if mean is None:
        return "--"
    if sd is None:
        return rf"{float(mean):.2f}\;(n={count};\ \mathrm{{SD\ n/a}})"
    return rf"{float(mean):.2f}\pm{float(sd):.2f}"


def main_latex_table(
    dataset: str,
    summary_rows: Sequence[Mapping[str, Any]],
    complete: bool,
) -> str:
    dataset_name = "University-1652" if dataset == "university1652" else "SUES-200"
    rows = [
        row
        for row in summary_rows
        if row["dataset"] == dataset and int(row["n_seeds"]) > 0
    ]
    status_note = (
        "All cells are mean $\\pm$ sample SD over the three frozen seeds."
        if complete
        else (
            "Partial audit output: cells with fewer than three seeds are explicitly "
            "marked and are not final manuscript evidence."
        )
    )
    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        (
            rf"\caption{{Frozen main-matrix results on {dataset_name}, reported "
            rf"task by task. {status_note} No macro or duplicate overall/subset "
            r"average is formed.}"
        ),
        rf"\label{{tab:formal_main_{dataset}}}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{llrrrrr}",
        r"\toprule",
        r"Task & Variant & R@1 & R@5 & R@10 & R@20 & Official mAP \\",
        r"\midrule",
    ]
    previous_task = None
    for row in rows:
        task = str(row["task"])
        if previous_task is not None and task != previous_task:
            lines.append(r"\addlinespace")
        lines.append(
            " & ".join(
                [
                    TASK_LABELS[task],
                    VARIANT_LABELS[str(row["variant"])],
                    mean_sd_tex(row, "r_at_1"),
                    mean_sd_tex(row, "r_at_5"),
                    mean_sd_tex(row, "r_at_10"),
                    mean_sd_tex(row, "r_at_20"),
                    mean_sd_tex(row, "official_trapezoid_mAP"),
                ]
            )
            + r" \\"
        )
        previous_task = task
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}%",
            r"}",
            r"\end{table*}",
        ]
    )
    return "\n".join(lines)


def sensitivity_latex_table(
    dataset: str,
    rows: Sequence[Mapping[str, Any]],
    complete: bool,
) -> str:
    dataset_name = "University-1652" if dataset == "university1652" else "SUES-200"
    selected = [row for row in rows if row["dataset"] == dataset]
    status_note = (
        "The main full seed-1 setting is included only as a reference."
        if complete
        else "Partial audit output; missing settings are not imputed."
    )
    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        (
            rf"\caption{{Frozen sensitivity results on {dataset_name}, task by task. "
            rf"{status_note} No task-level macro average is formed.}}"
        ),
        rf"\label{{tab:formal_sensitivity_{dataset}}}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{llrrrrr}",
        r"\toprule",
        r"Task & Setting & R@1 & R@5 & R@10 & R@20 & Official mAP \\",
        r"\midrule",
    ]
    previous_task = None
    for row in selected:
        task = str(row["task"])
        if previous_task is not None and task != previous_task:
            lines.append(r"\addlinespace")
        lines.append(
            " & ".join(
                [
                    TASK_LABELS[task],
                    SETTING_LABELS[str(row["setting"])],
                    f"{float(row['r_at_1_pct']):.2f}",
                    f"{float(row['r_at_5_pct']):.2f}",
                    f"{float(row['r_at_10_pct']):.2f}",
                    f"{float(row['r_at_20_pct']):.2f}",
                    f"{float(row['official_trapezoid_mAP_pct']):.2f}",
                ]
            )
            + r" \\"
        )
        previous_task = task
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}%",
            r"}",
            r"\end{table*}",
        ]
    )
    return "\n".join(lines)


def p_tex(log10_p: float | None, text: str) -> str:
    if log10_p is None or not text:
        return "--"
    if text.startswith("<"):
        return r"$<10^{-300}$"
    if log10_p >= -3:
        return f"{10.0 ** log10_p:.3f}"
    exponent = math.floor(log10_p)
    mantissa = 10.0 ** (log10_p - exponent)
    return rf"${mantissa:.2f}\times10^{{{exponent}}}$"


def pairwise_latex_table(
    dataset: str,
    bootstrap_rows: Sequence[Mapping[str, Any]],
    mcnemar_rows: Sequence[Mapping[str, Any]],
    complete: bool,
) -> str:
    dataset_name = "University-1652" if dataset == "university1652" else "SUES-200"
    bootstrap_index = {
        (row["dataset"], row["task"], int(row["seed"])): row
        for row in bootstrap_rows
    }
    tests = [row for row in mcnemar_rows if row["dataset"] == dataset]
    status_note = (
        "Exact McNemar values are Holm-adjusted in one family over all 33 "
        "task-by-seed tests."
        if complete
        else "Holm-adjusted values are withheld until all 33 planned tests exist."
    )
    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        (
            rf"\caption{{Visual versus full R@1 on {dataset_name}. Differences "
            r"are full minus visual in percentage points; intervals use 10,000 "
            rf"path-paired query bootstrap samples. {status_note}}}"
        ),
        rf"\label{{tab:formal_visual_full_{dataset}}}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        r"Task & Seed & Visual R@1 & Full R@1 & $\Delta$R@1 & 95\% CI & $p_{\mathrm{Holm}}$ \\",
        r"\midrule",
    ]
    previous_task = None
    for test in tests:
        key = (test["dataset"], test["task"], int(test["seed"]))
        bootstrap = bootstrap_index[key]
        task = str(test["task"])
        if previous_task is not None and task != previous_task:
            lines.append(r"\addlinespace")
        lines.append(
            " & ".join(
                [
                    TASK_LABELS[task],
                    str(test["seed"]),
                    f"{float(test['visual_r_at_1_pct']):.2f}",
                    f"{float(test['full_r_at_1_pct']):.2f}",
                    f"{float(test['difference_r_at_1_pp']):+.2f}",
                    (
                        f"[{float(bootstrap['ci95_low_pp']):+.2f}, "
                        f"{float(bootstrap['ci95_high_pp']):+.2f}]"
                    ),
                    p_tex(
                        (
                            float(test["holm_adjusted_log10_p"])
                            if test["holm_adjusted_log10_p"] is not None
                            else None
                        ),
                        str(test["holm_adjusted_p"]),
                    ),
                ]
            )
            + r" \\"
        )
        previous_task = task
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}%",
            r"}",
            r"\end{table*}",
        ]
    )
    return "\n".join(lines)


def validate_global_provenance(
    delivery_root: Path,
    specs: Sequence[RunSpec],
    allow_partial: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    aggregator = Path(__file__).resolve()
    protocol = delivery_root / "FORMAL_EXPERIMENT_PROTOCOL.md"
    runner = (
        delivery_root
        / "lgm_game_pytorch"
        / "experiments"
        / "run_frozen_formal_matrix.py"
    )
    formal = (
        delivery_root
        / "lgm_game_pytorch"
        / "lgm_game_pytorch"
        / "formal_retrieval.py"
    )
    for path in (protocol, runner, formal):
        if not path.is_file():
            raise IntegrityError(f"Frozen provenance file is missing: {path}")
    hashes = {
        "aggregator_path": str(aggregator),
        "aggregator_sha256": sha256_file(aggregator),
        "protocol_path": str(protocol),
        "protocol_sha256": sha256_file(protocol),
        "runner_path": str(runner),
        "runner_sha256": sha256_file(runner),
        "formal_script_path": str(formal),
        "formal_script_sha256": sha256_file(formal),
    }
    artifacts = [
        record_artifact(
            aggregator, delivery_root, None, "formal_result_aggregation_code"
        ),
        record_artifact(protocol, delivery_root, None, "frozen_protocol"),
        record_artifact(runner, delivery_root, None, "frozen_matrix_runner"),
        record_artifact(formal, delivery_root, None, "formal_training_evaluation_code"),
    ]
    issues: list[str] = []
    ledger_path = (
        delivery_root
        / "lgm_game_pytorch"
        / "runs"
        / "frozen_formal_matrix_ledger.json"
    )
    if not ledger_path.is_file():
        issues.append("frozen matrix ledger is not yet present")
        hashes["ledger_path"] = str(ledger_path)
        hashes["ledger_sha256"] = None
        if not allow_partial:
            raise MatrixIncompleteError(issues[-1])
        return hashes, artifacts, issues
    ledger = load_json(ledger_path)
    require_equal(
        ledger.get("protocol_sha256"),
        hashes["protocol_sha256"],
        "ledger protocol hash",
    )
    require_equal(
        ledger.get("formal_script_sha256"),
        hashes["formal_script_sha256"],
        "ledger formal-script hash",
    )
    require_equal(
        ledger.get("runner_sha256"),
        hashes["runner_sha256"],
        "ledger matrix-runner hash",
    )
    require_equal(
        int(ledger.get("registered_main_run_count", -1)),
        EXPECTED_MAIN_RUNS,
        "ledger registered main run count",
    )
    require_equal(
        int(ledger.get("registered_sensitivity_run_count", -1)),
        EXPECTED_SENSITIVITY_RUNS,
        "ledger registered sensitivity run count",
    )
    ledger_sha = sha256_file(ledger_path)
    hashes["ledger_path"] = str(ledger_path)
    hashes["ledger_sha256"] = ledger_sha
    artifacts.append(
        record_artifact(
            ledger_path,
            delivery_root,
            None,
            "frozen_matrix_ledger",
            actual_sha256=ledger_sha,
        )
    )
    registered = ledger.get("runs")
    if isinstance(registered, dict):
        missing_identifiers = [
            spec.identifier for spec in specs if spec.identifier not in registered
        ]
        if missing_identifiers:
            issues.append(
                f"ledger lacks {len(missing_identifiers)} expected run identifiers"
            )
            if not allow_partial:
                raise MatrixIncompleteError(issues[-1])
    return hashes, artifacts, issues


def output_artifact_records(output_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(output_dir.iterdir(), key=lambda item: item.name):
        if not path.is_file() or path.name == "aggregate_manifest.json":
            continue
        rows.append(
            {
                "path": path.name,
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    return rows


def aggregate(
    delivery_root: Path,
    output_dir: Path,
    *,
    allow_partial: bool,
    bootstrap_samples: int = BOOTSTRAP_SAMPLES,
    bootstrap_seed: int = 20260727,
) -> dict[str, Any]:
    delivery_root = delivery_root.resolve(strict=True)
    output_dir = output_dir.resolve()
    if bootstrap_samples != BOOTSTRAP_SAMPLES:
        raise ValueError(
            f"Frozen protocol requires exactly {BOOTSTRAP_SAMPLES} bootstrap samples."
        )
    specs = expected_specs(delivery_root)
    provenance, provenance_artifacts, global_issues = validate_global_provenance(
        delivery_root, specs, allow_partial
    )
    formal_script_sha = str(provenance["formal_script_sha256"])
    audits: list[dict[str, Any]] = []
    valid_runs: list[ValidRun] = []
    integrity_errors: list[str] = []
    for spec in specs:
        audit, valid, error = classify_run(spec, delivery_root, formal_script_sha)
        audits.append(audit)
        if valid is not None:
            valid_runs.append(valid)
        if error is not None:
            integrity_errors.append(f"{spec.identifier}: {error}")

    output_dir.mkdir(parents=True, exist_ok=True)
    audit_fields = (
        "identifier",
        "family",
        "dataset",
        "variant",
        "seed",
        "backbone",
        "embed_dim",
        "setting",
        "status",
        "reason",
        "training_manifest",
        "evaluation_manifest",
    )
    write_csv(output_dir / "run_audit.csv", audits, audit_fields)
    valid_main = sum(run.spec.family == "formal_main" for run in valid_runs)
    valid_sensitivity = sum(
        run.spec.family == "formal_sensitivity" for run in valid_runs
    )
    incomplete = [row for row in audits if row["status"] == "incomplete"]
    completeness = {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": utc_now(),
        "mode": "allow_partial" if allow_partial else "fail_closed",
        "expected_main_runs": EXPECTED_MAIN_RUNS,
        "expected_sensitivity_runs": EXPECTED_SENSITIVITY_RUNS,
        "valid_main_runs": valid_main,
        "valid_sensitivity_runs": valid_sensitivity,
        "incomplete_runs": len(incomplete),
        "invalid_runs": len(integrity_errors),
        "global_issues": global_issues,
        "run_audit": audits,
    }
    atomic_write_json(output_dir / "matrix_completeness_audit.json", completeness)
    if integrity_errors:
        raise IntegrityError(
            "One or more completed artifacts failed integrity validation:\n"
            + "\n".join(integrity_errors[:10])
        )
    full_matrix = (
        valid_main == EXPECTED_MAIN_RUNS
        and valid_sensitivity == EXPECTED_SENSITIVITY_RUNS
        and not incomplete
        and not global_issues
    )
    if not full_matrix and not allow_partial:
        raise MatrixIncompleteError(
            f"Frozen matrix incomplete: {valid_main}/36 main and "
            f"{valid_sensitivity}/6 sensitivity runs are valid.  "
            "Use --allow-partial only for a clearly marked progress audit."
        )
    ensure_cross_run_consistency(valid_runs)

    main_rows = main_metric_rows(valid_runs)
    sensitivity_rows = sensitivity_metric_rows(valid_runs)
    summary_rows = summarize_main(main_rows)
    sensitivity_reference_rows = sensitivity_with_reference(
        main_rows, sensitivity_rows
    )
    bootstrap_rows, mcnemar_rows = visual_full_statistics(
        valid_runs,
        bootstrap_samples,
        bootstrap_seed,
        full_matrix,
    )
    input_artifacts = provenance_artifacts + [
        artifact for run in valid_runs for artifact in run.input_artifacts
    ]

    main_fields = ordered_fields(
        main_rows,
        (
            "family",
            "dataset",
            "task",
            "variant",
            "seed",
            "queries",
            "gallery",
            "r_at_1_pct",
            "r_at_5_pct",
            "r_at_10_pct",
            "r_at_20_pct",
            "official_trapezoid_mAP_pct",
            "MRR_pct",
            "mean_top1_margin",
        ),
    )
    write_csv(output_dir / "main_metrics_by_seed.csv", main_rows, main_fields)
    summary_fields = ordered_fields(
        summary_rows,
        (
            "dataset",
            "task",
            "variant",
            "n_seeds",
            "seeds",
            "complete_seed_triplet",
            "queries",
            "gallery",
        ),
    )
    write_csv(
        output_dir / "main_three_seed_mean_sample_sd.csv",
        summary_rows,
        summary_fields,
    )
    sensitivity_fields = ordered_fields(
        sensitivity_rows,
        (
            "family",
            "dataset",
            "task",
            "setting",
            "backbone",
            "embed_dim",
            "seed",
            "queries",
            "gallery",
            "r_at_1_pct",
            "r_at_5_pct",
            "r_at_10_pct",
            "r_at_20_pct",
            "official_trapezoid_mAP_pct",
            "MRR_pct",
        ),
    )
    write_csv(
        output_dir / "sensitivity_metrics.csv",
        sensitivity_rows,
        sensitivity_fields,
    )
    sensitivity_reference_fields = ordered_fields(
        sensitivity_reference_rows,
        ("sensitivity_role",) + tuple(sensitivity_fields),
    )
    write_csv(
        output_dir / "sensitivity_with_main_reference.csv",
        sensitivity_reference_rows,
        sensitivity_reference_fields,
    )
    bootstrap_fields = ordered_fields(
        bootstrap_rows,
        (
            "dataset",
            "task",
            "seed",
            "method_a",
            "method_b",
            "visual_r_at_1_pct",
            "full_r_at_1_pct",
            "difference_r_at_1_pp",
            "ci95_low_pp",
            "ci95_high_pp",
            "paired_queries",
            "bootstrap_samples",
            "bootstrap_seed",
            "bootstrap_unit",
            "bootstrap_algorithm",
        ),
    )
    write_csv(
        output_dir / "visual_vs_full_paired_bootstrap.csv",
        bootstrap_rows,
        bootstrap_fields,
    )
    mcnemar_fields = ordered_fields(
        mcnemar_rows,
        (
            "dataset",
            "task",
            "seed",
            "method_a",
            "method_b",
            "visual_r_at_1_pct",
            "full_r_at_1_pct",
            "difference_r_at_1_pp",
            "visual_correct_full_wrong",
            "visual_wrong_full_correct",
            "discordant_queries",
            "paired_queries",
            "exact_mcnemar_log10_p",
            "exact_mcnemar_p",
            "holm_adjusted_log10_p",
            "holm_adjusted_p",
            "holm_family_size",
            "holm_family",
            "reject_holm_0_05",
            "holm_status",
        ),
    )
    write_csv(
        output_dir / "visual_vs_full_exact_mcnemar_holm.csv",
        mcnemar_rows,
        mcnemar_fields,
    )
    input_fields = (
        "run_identifier",
        "role",
        "path",
        "sha256",
        "bytes",
        "verification",
    )
    write_csv(
        output_dir / "input_artifact_sha256.csv",
        input_artifacts,
        input_fields,
    )

    for dataset in DATASET_ORDER:
        atomic_write_text(
            output_dir / f"main_{dataset}_mean_sample_sd.tex",
            main_latex_table(dataset, summary_rows, full_matrix),
        )
        atomic_write_text(
            output_dir / f"sensitivity_{dataset}.tex",
            sensitivity_latex_table(
                dataset, sensitivity_reference_rows, full_matrix
            ),
        )
        atomic_write_text(
            output_dir / f"visual_vs_full_{dataset}.tex",
            pairwise_latex_table(
                dataset, bootstrap_rows, mcnemar_rows, full_matrix
            ),
        )

    result_payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "complete" if full_matrix else "partial_audit_only",
        "units": {
            "aggregate_metrics": "percentage",
            "top1_margin": "cosine-similarity units",
            "pairwise_difference": "percentage points",
        },
        "main_three_seed_summary": summary_rows,
        "sensitivity_runs": sensitivity_rows,
        "sensitivity_with_main_reference": sensitivity_reference_rows,
        "visual_vs_full_paired_bootstrap": bootstrap_rows,
        "visual_vs_full_exact_mcnemar_holm": mcnemar_rows,
    }
    atomic_write_json(output_dir / "aggregate_results.json", result_payload)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "status": "complete" if full_matrix else "partial_audit_only",
        "generated_utc": utc_now(),
        "delivery_root": str(delivery_root),
        "output_dir": str(output_dir),
        "allow_partial": allow_partial,
        "matrix": {
            "expected_main_runs": EXPECTED_MAIN_RUNS,
            "valid_main_runs": valid_main,
            "expected_sensitivity_runs": EXPECTED_SENSITIVITY_RUNS,
            "valid_sensitivity_runs": valid_sensitivity,
            "expected_pairwise_tests": EXPECTED_PAIRWISE_TESTS,
            "completed_pairwise_tests": len(mcnemar_rows),
        },
        "statistics": {
            "main_summary": "mean and sample SD (ddof=1) over frozen seeds 1,2,3",
            "paired_bootstrap_samples": bootstrap_samples,
            "paired_bootstrap_seed": bootstrap_seed,
            "paired_bootstrap_unit": "path-aligned official query",
            "paired_bootstrap_metric": "R@1",
            "mcnemar": "two-sided exact conditional test",
            "holm_family": (
                "all 33 visual-vs-full task-by-seed comparisons"
                if full_matrix
                else "withheld until all 33 comparisons are available"
            ),
            "underflow_policy": (
                "log10 probabilities are retained and printable probabilities "
                "use '<1e-300'; exact zero is never emitted"
            ),
        },
        "task_policy": {
            "university1652_tasks": list(TASKS["university1652"]),
            "sues200_tasks": list(TASKS["sues200"]),
            "task_level_only": True,
            "macro_average_rows_generated": False,
            "overall_plus_subset_duplicate_average_generated": False,
        },
        "provenance": provenance,
        "input_artifact_count": len(input_artifacts),
        "output_artifacts": output_artifact_records(output_dir),
    }
    manifest["payload_sha256"] = canonical_sha256(manifest)
    atomic_write_json(output_dir / "aggregate_manifest.json", manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    script = Path(__file__).resolve()
    delivery_root = script.parents[2]
    parser = argparse.ArgumentParser(
        description=(
            "Fail-closed audit and task-level aggregation of the frozen 36+6 "
            "formal experiment matrix."
        )
    )
    parser.add_argument("--delivery-root", type=Path, default=delivery_root)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Default: <delivery-root>/lgm_game_pytorch/results/"
            "formal_matrix_aggregate"
        ),
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help=(
            "Write an explicitly partial progress audit. Missing values are never "
            "imputed and Holm adjustment is withheld until all 33 tests exist."
        ),
    )
    parser.add_argument(
        "--bootstrap-samples",
        type=int,
        choices=(BOOTSTRAP_SAMPLES,),
        default=BOOTSTRAP_SAMPLES,
        help="Frozen by protocol at exactly 10,000.",
    )
    parser.add_argument("--bootstrap-seed", type=int, default=20260727)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    delivery_root = args.delivery_root.expanduser().resolve()
    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir is not None
        else (
            delivery_root
            / "lgm_game_pytorch"
            / "results"
            / "formal_matrix_aggregate"
        )
    )
    try:
        manifest = aggregate(
            delivery_root,
            output_dir,
            allow_partial=bool(args.allow_partial),
            bootstrap_samples=int(args.bootstrap_samples),
            bootstrap_seed=int(args.bootstrap_seed),
        )
    except MatrixIncompleteError as error:
        print(f"INCOMPLETE: {error}", file=sys.stderr)
        raise SystemExit(2) from error
    except IntegrityError as error:
        print(f"INTEGRITY FAILURE: {error}", file=sys.stderr)
        raise SystemExit(3) from error
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "output_dir": str(output_dir),
                "payload_sha256": manifest["payload_sha256"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
