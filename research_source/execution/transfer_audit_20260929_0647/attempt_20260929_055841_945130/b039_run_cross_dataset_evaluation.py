#!/usr/bin/env python3
"""Evaluate one frozen primary checkpoint zero-shot on the other dataset."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Any, Mapping, Sequence

import numpy as np

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from lgm_game_pytorch import formal_retrieval as core


CONFIG_SCHEMA = "lgm-game.cross-dataset-evaluation-config.v1"
METRICS_SCHEMA = "lgm-game.cross-dataset-metrics.v1"
MANIFEST_SCHEMA = "lgm-game.cross-dataset-evaluation.v1"
STATUS_SCHEMA = "lgm-game.cross-dataset-evaluation-status.v1"
EXPECTED_CORE_SHA256 = (
    "081f327f8f83d79ab078adc61e76070c140f13e0ac9a0d8f423bfad15df59862"
)
EXPECTED_EVIDENCE = {
    "university1652": {
        "sha256": "8a2333d58dbb0ca56c5d5829159a32f294e11e686bb6b91d05098d4b170c2bc3",
        "meta_sha256": "3731072d3a1c8a3b9fe8d880fd791dfbe7eb82f2d93be85b82be229ff8512dbf",
    },
    "sues200": {
        "sha256": "6c3a82fdcf59e401f5da4ed0f3d9dca99fdcbab0a46aa66fb47a055c832cdabd",
        "meta_sha256": "3dc42892bbff9339d058fc0d6abaf2fd9e92cc94f9f9b7fd58ed0ae725b57dca",
    },
}
EXPECTED_SUES_MANIFEST_SHA256 = (
    "c1386d5c746aca48bbb2793ed1ee19d6cd7330a7f5f1b27a5ec43727317ec226"
)
EXPECTED_TASKS = {
    "university1652": (
        "university1652_drone_to_satellite",
        "university1652_satellite_to_drone",
        "university1652_street_to_satellite",
    ),
    "sues200": tuple(
        name
        for altitude in core.SUES_ALTITUDES
        for name in (
            f"sues200_uav_{altitude}m_to_satellite",
            f"sues200_satellite_to_uav_{altitude}m",
        )
    ),
}


class TransferIntegrityError(RuntimeError):
    """Raised when a zero-shot transfer artifact fails closed."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(payload: Any) -> str:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def canonical_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def atomic_json(path: Path, payload: Any) -> None:
    serialized = canonical_bytes(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    if temporary.exists():
        raise TransferIntegrityError(
            f"Refusing to overwrite stale temporary file: {temporary}"
        )
    temporary.write_bytes(serialized)
    temporary.replace(path)


def immutable_json(path: Path, payload: Any) -> str:
    serialized = canonical_bytes(payload)
    digest = hashlib.sha256(serialized).hexdigest()
    if path.exists():
        if path.read_bytes() != serialized:
            raise TransferIntegrityError(f"Existing immutable JSON differs: {path}")
        return digest
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(serialized)
    return digest


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise TransferIntegrityError(f"Required JSON artifact is absent: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TransferIntegrityError(f"JSON root must be a mapping: {path}")
    return value


def validate_payload_hash(payload: dict[str, Any], label: str) -> None:
    body = dict(payload)
    declared = body.pop("payload_sha256", None)
    if declared != canonical_sha256(body):
        raise TransferIntegrityError(f"{label} payload hash mismatch.")


def adapter_sha256() -> str:
    return sha256_file(Path(__file__).resolve())


def validate_core_hash() -> None:
    actual = sha256_file(Path(core.__file__).resolve())
    if actual != EXPECTED_CORE_SHA256:
        raise TransferIntegrityError(
            f"Frozen formal core changed: expected {EXPECTED_CORE_SHA256}, got {actual}"
        )


def inspect_source_checkpoint(
    checkpoint_path: Path,
    source_dataset: str,
    variant: str,
    seed: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    checkpoint_path = checkpoint_path.resolve(strict=True)
    if checkpoint_path.name != "best.pt":
        raise TransferIntegrityError("T3 requires the registered final best.pt path.")
    sibling_last = checkpoint_path.with_name("last.pt")
    if (
        not sibling_last.is_file()
        or sha256_file(sibling_last) != sha256_file(checkpoint_path)
    ):
        raise TransferIntegrityError("T3 source best.pt and last.pt differ.")
    run_manifest = load_json(checkpoint_path.parent / "run_manifest.json")
    validate_payload_hash(run_manifest, "T3 source training manifest")
    if (
        run_manifest.get("status") != "completed"
        or run_manifest.get("epochs_completed") != 80
        or run_manifest.get("best_epoch") != 79
        or run_manifest.get("best_validation_mAP") is not None
        or run_manifest.get("test_protocol_was_evaluated") is not False
    ):
        raise TransferIntegrityError("T3 source training run is not admissible.")

    checkpoint = core.load_torch_checkpoint(checkpoint_path, "cpu")
    immutable = checkpoint.get("immutable_config", {})
    model_config = checkpoint.get("model_config", {})
    if (
        checkpoint.get("schema_version") != core.SCHEMA_VERSION
        or checkpoint.get("epoch") != 79
        or len(checkpoint.get("history", [])) != 80
        or immutable.get("dataset") != source_dataset
        or immutable.get("model", {}).get("variant") != variant
        or model_config != immutable.get("model")
        or model_config.get("variant") != variant
        or immutable.get("seed") != seed
        or immutable.get("code_sha256") != EXPECTED_CORE_SHA256
        or checkpoint.get("best_epoch") != 79
    ):
        raise TransferIntegrityError("T3 source checkpoint provenance mismatch.")
    required_state = (
        "model_state",
        "optimizer_state",
        "scheduler_state",
        "scaler_state",
        "rng_state",
        "run_config_sha256",
        "model_config",
        "evidence_schema",
    )
    missing = [name for name in required_state if name not in checkpoint]
    if missing:
        raise TransferIntegrityError(
            f"T3 source checkpoint is not full-state: {missing}"
        )
    return checkpoint, run_manifest


def evidence_descriptor(path: Path, target_dataset: str) -> dict[str, Any]:
    path = path.resolve(strict=True)
    meta_path = core.find_meta_path(path).resolve(strict=True)
    expected = EXPECTED_EVIDENCE[target_dataset]
    row = {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "meta_path": str(meta_path),
        "meta_bytes": meta_path.stat().st_size,
        "meta_sha256": sha256_file(meta_path),
    }
    if (
        row["sha256"] != expected["sha256"]
        or row["meta_sha256"] != expected["meta_sha256"]
    ):
        raise TransferIntegrityError(
            f"T3 target evidence differs from the frozen {target_dataset} cache."
        )
    return row


def validate_args(args: argparse.Namespace) -> None:
    if args.source_dataset == args.target_dataset:
        raise TransferIntegrityError("T3 source and target datasets must differ.")
    if args.variant not in {"visual", "full"}:
        raise TransferIntegrityError("T3 permits only visual and full checkpoints.")
    if args.seed not in {1, 2, 3}:
        raise TransferIntegrityError("T3 permits only registered seeds 1, 2, and 3.")
    if args.workers != 8:
        raise TransferIntegrityError("T3 frozen worker count is 8.")
    if args.eval_batch_size != 128 or args.eval_chunk_size != 128:
        raise TransferIntegrityError("T3 frozen evaluation batch/chunk size is 128.")
    if args.data_hash_mode != "content":
        raise TransferIntegrityError("T3 requires content image hashing.")
    if not args.amp:
        raise TransferIntegrityError("T3 requires the frozen CUDA AMP setting.")
    if args.target_dataset == "sues200":
        manifest = Path(args.sues_manifest).expanduser().resolve(strict=True)
        if sha256_file(manifest) != EXPECTED_SUES_MANIFEST_SHA256:
            raise TransferIntegrityError("T3 SUES official manifest changed.")


def build_config(
    args: argparse.Namespace,
    checkpoint: Mapping[str, Any],
    source_manifest: Mapping[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    checkpoint_path = Path(args.checkpoint).expanduser().resolve(strict=True)
    config = {
        "schema_version": CONFIG_SCHEMA,
        "design": "bidirectional_zero_shot_cross_dataset_transfer",
        "source_dataset": args.source_dataset,
        "target_dataset": args.target_dataset,
        "variant": args.variant,
        "seed": args.seed,
        "checkpoint": {
            "path": str(checkpoint_path),
            "bytes": checkpoint_path.stat().st_size,
            "sha256": sha256_file(checkpoint_path),
            "selected_training_epoch": int(checkpoint["epoch"]),
            "training_run_config_sha256": checkpoint["run_config_sha256"],
            "training_manifest_payload_sha256": source_manifest["payload_sha256"],
        },
        "target": {
            "data_root": str(Path(args.data_root).expanduser().resolve(strict=True)),
            "evidence": evidence,
            "sues_manifest": (
                {
                    "path": str(
                        Path(args.sues_manifest).expanduser().resolve(strict=True)
                    ),
                    "sha256": sha256_file(
                        Path(args.sues_manifest).expanduser().resolve(strict=True)
                    ),
                }
                if args.target_dataset == "sues200"
                else None
            ),
        },
        "evaluation": {
            "device": args.device,
            "workers": args.workers,
            "eval_batch_size": args.eval_batch_size,
            "eval_chunk_size": args.eval_chunk_size,
            "data_hash_mode": args.data_hash_mode,
            "amp": args.amp,
            "all_official_queries": True,
            "all_official_gallery_images": True,
        },
        "controls": {
            "target_dataset_used_for_training": False,
            "target_dataset_used_for_checkpoint_selection": False,
            "target_dataset_used_for_calibration": False,
            "target_labels_used_only_by_evaluator": True,
        },
        "frozen_core": {
            "path": str(Path(core.__file__).resolve()),
            "sha256": EXPECTED_CORE_SHA256,
        },
        "adapter": {
            "path": str(Path(__file__).resolve()),
            "sha256": adapter_sha256(),
        },
    }
    return config


def recompute_metrics_from_arrays(path: Path) -> dict[str, float]:
    with np.load(path, allow_pickle=False) as arrays:
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
        if set(arrays.files) != required:
            raise TransferIntegrityError(
                f"T3 per-query array schema mismatch: {path.name}"
            )
        raw = {name: np.asarray(arrays[name]) for name in required}
        non_vectors = {
            name: value.shape
            for name, value in raw.items()
            if value.ndim != 1
        }
        if non_vectors:
            raise TransferIntegrityError(
                f"T3 per-query arrays must be one-dimensional: {non_vectors}"
            )
        lengths = {len(value) for value in raw.values()}
        if len(lengths) != 1:
            raise TransferIntegrityError(
                f"T3 per-query array lengths differ: {path.name}"
            )
        count = lengths.pop()
        if count <= 0:
            raise TransferIntegrityError(f"T3 per-query array is empty: {path.name}")
        if raw["correct"].dtype.kind != "b":
            raise TransferIntegrityError(
                f"T3 correct array must be Boolean: {path.name}"
            )
        if raw["top1_gallery_indices"].dtype.kind not in {"i", "u"}:
            raise TransferIntegrityError(
                f"T3 top-1 indices must be integers: {path.name}"
            )
        for name in (
            "query_paths",
            "query_labels",
            "top1_gallery_paths",
            "top1_gallery_labels",
        ):
            if raw[name].dtype.kind not in {"U", "S"}:
                raise TransferIntegrityError(
                    f"T3 {name} must be a non-object text array: {path.name}"
                )
        margins = np.asarray(raw["margin"], dtype=np.float64)
        correct = np.asarray(raw["correct"], dtype=np.bool_)
        aps = np.asarray(
            raw["per_query_official_trapezoid_AP"],
            dtype=np.float64,
        )
        reciprocal = np.asarray(raw["reciprocal_rank"], dtype=np.float64)
        if (
            not np.isfinite(margins).all()
            or not np.isfinite(aps).all()
            or not np.isfinite(reciprocal).all()
            or (aps < 0).any()
            or (aps > 1).any()
            or (reciprocal <= 0).any()
            or (reciprocal > 1).any()
        ):
            raise TransferIntegrityError(
                f"T3 per-query arrays contain invalid values: {path.name}"
            )
        first_rank_one_based = np.rint(1.0 / reciprocal).astype(np.int64)
        if (first_rank_one_based <= 0).any():
            raise TransferIntegrityError(
                f"T3 reciprocal ranks cannot be inverted: {path.name}"
            )
        if not np.allclose(
            reciprocal * first_rank_one_based,
            np.ones(count, dtype=np.float64),
            rtol=1e-6,
            atol=1e-7,
        ):
            raise TransferIntegrityError(
                f"T3 reciprocal ranks are not reciprocal integers: {path.name}"
            )
        top1_indices = np.asarray(raw["top1_gallery_indices"], dtype=np.int64)
        if (top1_indices < 0).any():
            raise TransferIntegrityError(
                f"T3 top-1 gallery indices are negative: {path.name}"
            )
        query_paths = raw["query_paths"].astype(str)
        top1_paths = raw["top1_gallery_paths"].astype(str)
        if (
            any(not value for value in query_paths)
            or any(not value for value in top1_paths)
            or len(set(query_paths.tolist())) != count
        ):
            raise TransferIntegrityError(
                f"T3 query/top-1 path semantics are invalid: {path.name}"
            )
        query_labels = raw["query_labels"].astype(str)
        top1_labels = raw["top1_gallery_labels"].astype(str)
        semantic_correct = query_labels == top1_labels
        if not np.array_equal(correct, semantic_correct):
            raise TransferIntegrityError(
                f"T3 correct flags disagree with top-1 labels: {path.name}"
            )
        if not np.array_equal(correct, first_rank_one_based == 1):
            raise TransferIntegrityError(
                f"T3 correct flags disagree with reciprocal ranks: {path.name}"
            )
        return {
            "queries": float(count),
            "r_at_1": float(correct.mean()),
            "r_at_5": float(np.mean(first_rank_one_based <= 5)),
            "r_at_10": float(np.mean(first_rank_one_based <= 10)),
            "r_at_20": float(np.mean(first_rank_one_based <= 20)),
            "official_trapezoid_mAP": float(aps.mean()),
            "MRR": float(reciprocal.mean()),
            "mean_top1_margin": float(margins.mean()),
        }


def validate_metrics_csv(
    path: Path,
    results: Mapping[str, Mapping[str, Any]],
) -> None:
    expected_fields = (
        "task",
        "queries",
        "gallery",
        "query_identities",
        "gallery_identities",
        "r_at_1",
        "r_at_5",
        "r_at_10",
        "r_at_20",
        "official_trapezoid_mAP",
        "MRR",
        "mean_top1_margin",
        "protocol",
    )
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != expected_fields:
            raise TransferIntegrityError("T3 metrics CSV field order changed.")
        rows = list(reader)
    if len(rows) != len(results):
        raise TransferIntegrityError("T3 metrics CSV row count mismatch.")
    observed = {row.get("task"): row for row in rows}
    if set(observed) != set(results):
        raise TransferIntegrityError("T3 metrics CSV task coverage mismatch.")
    integer_fields = (
        "queries",
        "gallery",
        "query_identities",
        "gallery_identities",
    )
    float_fields = (
        "r_at_1",
        "r_at_5",
        "r_at_10",
        "r_at_20",
        "official_trapezoid_mAP",
        "MRR",
        "mean_top1_margin",
    )
    for task_name, reported in results.items():
        row = observed[task_name]
        for field in integer_fields:
            if int(row[field]) != int(reported[field]):
                raise TransferIntegrityError(
                    f"T3 metrics CSV {field} mismatch for {task_name}."
                )
        for field in float_fields:
            if not math.isclose(
                float(row[field]),
                float(reported[field]),
                rel_tol=1e-9,
                abs_tol=1e-12,
            ):
                raise TransferIntegrityError(
                    f"T3 metrics CSV {field} mismatch for {task_name}."
                )
        if row["protocol"] != str(reported["protocol"]):
            raise TransferIntegrityError(
                f"T3 metrics CSV protocol mismatch for {task_name}."
            )


def validate_completed(
    output_dir: Path,
    config_sha: str,
    source_dataset: str,
    target_dataset: str,
    variant: str,
    seed: int,
) -> dict[str, Any]:
    manifest_path = output_dir / "transfer_evaluation_manifest.json"
    manifest = load_json(manifest_path)
    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise TransferIntegrityError("T3 evaluation-manifest schema mismatch.")
    validate_payload_hash(manifest, "T3 evaluation manifest")
    expected = {
        "status": "completed",
        "source_dataset": source_dataset,
        "target_dataset": target_dataset,
        "variant": variant,
        "seed": seed,
        "config_sha256": config_sha,
        "target_dataset_used_for_training": False,
        "target_dataset_used_for_selection_or_calibration": False,
        "all_official_queries_used": True,
        "all_official_gallery_images_used": True,
    }
    for name, value in expected.items():
        if manifest.get(name) != value:
            raise TransferIntegrityError(f"T3 evaluation-manifest {name} mismatch.")
    config_path = output_dir / "transfer_evaluation_config.json"
    metrics_path = output_dir / "metrics.json"
    csv_path = output_dir / "metrics.csv"
    for name, path in (
        ("config", config_path),
        ("metrics", metrics_path),
        ("metrics_csv", csv_path),
    ):
        if Path(manifest[f"{name}_path"]).resolve() != path.resolve():
            raise TransferIntegrityError(f"T3 {name} path mismatch.")
        if not path.is_file() or sha256_file(path) != manifest[f"{name}_sha256"]:
            raise TransferIntegrityError(f"T3 {name} artifact hash mismatch.")
    config = load_json(config_path)
    config_expected = {
        "schema_version": CONFIG_SCHEMA,
        "source_dataset": source_dataset,
        "target_dataset": target_dataset,
        "variant": variant,
        "seed": seed,
    }
    for name, value in config_expected.items():
        if config.get(name) != value:
            raise TransferIntegrityError(f"T3 evaluation config {name} mismatch.")
    controls = config.get("controls", {})
    if controls != {
        "target_dataset_used_for_training": False,
        "target_dataset_used_for_checkpoint_selection": False,
        "target_dataset_used_for_calibration": False,
        "target_labels_used_only_by_evaluator": True,
    }:
        raise TransferIntegrityError("T3 target-use controls changed.")
    if config.get("checkpoint", {}).get("sha256") != manifest.get(
        "checkpoint_sha256"
    ):
        raise TransferIntegrityError("T3 checkpoint hash differs across artifacts.")
    metrics = load_json(metrics_path)
    if metrics.get("schema_version") != METRICS_SCHEMA:
        raise TransferIntegrityError("T3 metrics schema mismatch.")
    validate_payload_hash(metrics, "T3 metrics")
    metrics_expected = {
        "unit": "fraction",
        "source_dataset": source_dataset,
        "target_dataset": target_dataset,
        "variant": variant,
        "seed": seed,
        "full_gallery": True,
    }
    for name, value in metrics_expected.items():
        if metrics.get(name) != value:
            raise TransferIntegrityError(f"T3 metrics {name} mismatch.")
    if set(metrics.get("results", {})) != set(EXPECTED_TASKS[target_dataset]):
        raise TransferIntegrityError("T3 target task set mismatch.")
    validate_metrics_csv(csv_path, metrics["results"])
    artifact_rows = manifest.get("per_query_arrays")
    if not isinstance(artifact_rows, dict) or set(artifact_rows) != set(
        EXPECTED_TASKS[target_dataset]
    ):
        raise TransferIntegrityError("T3 per-query artifact coverage mismatch.")
    for task_name in EXPECTED_TASKS[target_dataset]:
        row = artifact_rows[task_name]
        path = Path(row["path"])
        expected_path = (
            output_dir
            / "per_query_arrays"
            / f"{core.slugify(task_name)}_per_query.npz"
        )
        if path.resolve() != expected_path.resolve():
            raise TransferIntegrityError(f"T3 array path mismatch for {task_name}.")
        if not path.is_file() or sha256_file(path) != row["sha256"]:
            raise TransferIntegrityError(f"T3 array hash mismatch for {task_name}.")
        recomputed = recompute_metrics_from_arrays(path)
        reported = metrics["results"][task_name]
        scale = manifest.get("target_task_scale", {}).get(task_name)
        if not isinstance(scale, dict):
            raise TransferIntegrityError(
                f"T3 target task-scale row is absent for {task_name}."
            )
        for name, source_name in (
            ("queries", "queries"),
            ("gallery", "gallery_images"),
            ("query_identities", "query_identities"),
            ("gallery_identities", "gallery_identities"),
            ("protocol", "protocol"),
        ):
            if reported[name] != scale[source_name]:
                raise TransferIntegrityError(
                    f"T3 {name} differs from task scale for {task_name}."
                )
        with np.load(path, allow_pickle=False) as arrays:
            top1_indices = np.asarray(arrays["top1_gallery_indices"])
            if (top1_indices >= int(reported["gallery"])).any():
                raise TransferIntegrityError(
                    f"T3 top-1 index exceeds gallery for {task_name}."
                )
        for metric, value in recomputed.items():
            if metric == "queries":
                if int(value) != int(reported["queries"]):
                    raise TransferIntegrityError(
                        f"T3 query count mismatch for {task_name}."
                    )
            elif not math.isclose(
                value,
                float(reported[metric]),
                rel_tol=1e-6,
                abs_tol=1e-7,
            ):
                raise TransferIntegrityError(
                    f"T3 {metric} does not match per-query arrays for {task_name}."
                )
    return manifest


def write_metrics_csv(
    path: Path,
    results: Mapping[str, Mapping[str, Any]],
) -> None:
    fields = (
        "task",
        "queries",
        "gallery",
        "query_identities",
        "gallery_identities",
        "r_at_1",
        "r_at_5",
        "r_at_10",
        "r_at_20",
        "official_trapezoid_mAP",
        "MRR",
        "mean_top1_margin",
        "protocol",
    )
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    if temporary.exists():
        raise TransferIntegrityError(f"Stale T3 CSV temporary file: {temporary}")
    with temporary.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for task_name, metrics in results.items():
            writer.writerow(
                {
                    "task": task_name,
                    **{key: metrics.get(key, "") for key in fields[1:]},
                }
            )
    temporary.replace(path)


def run_evaluation(
    args: argparse.Namespace,
    checkpoint: dict[str, Any],
    source_manifest: dict[str, Any],
    evidence_row: dict[str, Any],
) -> dict[str, Any]:
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    config = build_config(args, checkpoint, source_manifest, evidence_row)
    config_path = output_dir / "transfer_evaluation_config.json"
    config_sha = immutable_json(config_path, config)
    complete_path = output_dir / "transfer_evaluation_manifest.json"
    if complete_path.exists():
        return validate_completed(
            output_dir,
            config_sha,
            args.source_dataset,
            args.target_dataset,
            args.variant,
            args.seed,
        )
    retained = [
        path
        for path in output_dir.iterdir()
        if path.name != config_path.name
    ]
    if retained:
        raise TransferIntegrityError(
            "T3 output contains an incomplete retained attempt; archive it "
            f"before restarting: {[path.name for path in retained]}"
        )
    status_path = output_dir / "transfer_evaluation_status.json"
    started_utc = utc_now()
    atomic_json(
        status_path,
        {
            "schema_version": STATUS_SCHEMA,
            "status": "running",
            "config_sha256": config_sha,
            "started_utc": started_utc,
        },
    )
    started = time.perf_counter()
    try:
        core.configure_logging(output_dir)
        device = core.choose_device(args.device)
        core.seed_everything(args.seed)
        data_root = Path(args.data_root).expanduser().resolve(strict=True)
        store = core.EvidenceStore.load([Path(args.evidence)])
        core.validate_checkpoint_evidence_schema(checkpoint, store)
        records = core.derive_all_records(
            store,
            data_root,
            args.target_dataset,
        )
        sues_ids, sues_info = core.parse_sues_manifest(
            Path(args.sues_manifest).expanduser()
            if args.target_dataset == "sues200"
            else None
        )
        tasks = core.build_official_evaluation_tasks(
            records,
            args.target_dataset,
            sues_ids,
        )
        if tuple(task.name for task in tasks) != EXPECTED_TASKS[args.target_dataset]:
            raise TransferIntegrityError("T3 official task set changed.")
        model_config = dict(checkpoint["model_config"])
        model = core.FormalRetrievalModel(
            variant=model_config["variant"],
            backbone=model_config["backbone"],
            embed_dim=int(model_config["embed_dim"]),
            dropout=float(model_config["dropout"]),
            pretrained=False,
        )
        model.load_state_dict(checkpoint["model_state"], strict=True)
        model.to(device)
        _, transform = core.build_transforms(
            int(model_config["resize_size"]),
            int(model_config["image_size"]),
        )
        amp_enabled = bool(args.amp and device.type == "cuda")
        evaluation_records = [
            row for task in tasks for row in (*task.query, *task.gallery)
        ]
        inventory = core.inventory_hash(
            evaluation_records,
            args.data_hash_mode,
        )
        arrays_dir = output_dir / "per_query_arrays"
        results = core.evaluate_tasks(
            model,
            tasks,
            store,
            transform,
            device,
            args.eval_batch_size,
            args.workers,
            amp_enabled,
            args.seed,
            args.eval_chunk_size,
            arrays_dir,
        )
        metrics_payload = {
            "schema_version": METRICS_SCHEMA,
            "unit": "fraction",
            "source_dataset": args.source_dataset,
            "target_dataset": args.target_dataset,
            "variant": args.variant,
            "seed": args.seed,
            "AP_definition": (
                "Official trapezoidal interpolation used by the frozen "
                "University-1652/SUES evaluator."
            ),
            "full_gallery": True,
            "results": results,
        }
        metrics = {
            **metrics_payload,
            "payload_sha256": canonical_sha256(metrics_payload),
        }
        metrics_path = output_dir / "metrics.json"
        atomic_json(metrics_path, metrics)
        csv_path = output_dir / "metrics.csv"
        write_metrics_csv(csv_path, results)
        array_rows = {}
        for task in tasks:
            path = (
                arrays_dir / f"{core.slugify(task.name)}_per_query.npz"
            ).resolve()
            array_rows[task.name] = {
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        task_scale = {
            task.name: {
                "queries": len(task.query),
                "gallery_images": len(task.gallery),
                "query_identities": len({row.label for row in task.query}),
                "gallery_identities": len({row.label for row in task.gallery}),
                "protocol": task.protocol,
            }
            for task in tasks
        }
        manifest_payload = {
            "schema_version": MANIFEST_SCHEMA,
            "status": "completed",
            "source_dataset": args.source_dataset,
            "target_dataset": args.target_dataset,
            "variant": args.variant,
            "seed": args.seed,
            "config_path": str(config_path),
            "config_sha256": config_sha,
            "metrics_path": str(metrics_path.resolve()),
            "metrics_sha256": sha256_file(metrics_path),
            "metrics_csv_path": str(csv_path.resolve()),
            "metrics_csv_sha256": sha256_file(csv_path),
            "checkpoint_path": str(
                Path(args.checkpoint).expanduser().resolve()
            ),
            "checkpoint_sha256": sha256_file(
                Path(args.checkpoint).expanduser().resolve()
            ),
            "selected_training_epoch": int(checkpoint["epoch"]),
            "target_evidence_sha256": evidence_row["sha256"],
            "target_protocol_membership_sha256": core.protocol_membership_hash(
                tasks
            ),
            "target_task_scale": task_scale,
            "target_image_inventory": inventory,
            "sues_manifest": (
                sues_info if args.target_dataset == "sues200" else None
            ),
            "per_query_arrays": array_rows,
            "environment": core.environment_manifest(device),
            "amp": amp_enabled,
            "elapsed_seconds": time.perf_counter() - started,
            "target_dataset_used_for_training": False,
            "target_dataset_used_for_selection_or_calibration": False,
            "all_official_queries_used": True,
            "all_official_gallery_images_used": True,
            "completed_utc": utc_now(),
        }
        manifest = {
            **manifest_payload,
            "payload_sha256": canonical_sha256(manifest_payload),
        }
        immutable_json(complete_path, manifest)
        manifest = validate_completed(
            output_dir,
            config_sha,
            args.source_dataset,
            args.target_dataset,
            args.variant,
            args.seed,
        )
        atomic_json(
            status_path,
            {
                "schema_version": STATUS_SCHEMA,
                "status": "completed",
                "config_sha256": config_sha,
                "manifest_sha256": sha256_file(complete_path),
                "completed_utc": manifest["completed_utc"],
            },
        )
        return manifest
    except BaseException as error:
        atomic_json(
            status_path,
            {
                "schema_version": STATUS_SCHEMA,
                "status": "failed",
                "config_sha256": config_sha,
                "started_utc": started_utc,
                "failed_utc": utc_now(),
                "elapsed_seconds": time.perf_counter() - started,
                "error_type": type(error).__name__,
                "error": str(error),
            },
        )
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-dataset",
        choices=("university1652", "sues200"),
        required=True,
    )
    parser.add_argument(
        "--target-dataset",
        choices=("university1652", "sues200"),
        required=True,
    )
    parser.add_argument("--variant", choices=("visual", "full"), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--sues-manifest", type=Path, default=core.default_sues_manifest_path())
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--data-hash-mode", choices=("content",), default="content")
    parser.add_argument(
        "--amp",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--eval-batch-size", type=int, default=128)
    parser.add_argument("--eval-chunk-size", type=int, default=128)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        validate_core_hash()
        validate_args(args)
        checkpoint, source_manifest = inspect_source_checkpoint(
            Path(args.checkpoint),
            args.source_dataset,
            args.variant,
            args.seed,
        )
        evidence = evidence_descriptor(
            Path(args.evidence),
            args.target_dataset,
        )
        manifest = run_evaluation(
            args,
            checkpoint,
            source_manifest,
            evidence,
        )
    except (TransferIntegrityError, OSError, ValueError, RuntimeError) as error:
        raise SystemExit(f"ERROR: {error}") from error
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
