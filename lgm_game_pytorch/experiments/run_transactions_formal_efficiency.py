#!/usr/bin/env python3
"""Benchmark the registered primary-model component of T6 on one exclusive GPU."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence

import numpy as np
import torch

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DELIVERY_ROOT_DEFAULT = PACKAGE_ROOT.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from experiments import aggregate_frozen_formal_results as aggregate
from experiments.transactions_efficiency_analysis import (
    ENCODING_TIMED_REPETITIONS,
    ENCODING_WARMUP_REPETITIONS,
    GALLERY_SAMPLING_SEED,
    RANKING_TIMED_REPETITIONS,
    RANKING_WARMUP_REPETITIONS,
    EfficiencyIntegrityError,
    count_conv_linear_macs,
    formal_model_descriptor_bytes,
    gallery_scaling_metrics,
    latency_summary,
    parameter_counts,
    registered_gallery_sizes,
    synchronize_cuda_latency,
)
from lgm_game_pytorch import formal_retrieval as core


CONFIG_SCHEMA = "lgm-game.transactions-t6-formal-config.v1"
RESULT_SCHEMA = "lgm-game.transactions-t6-formal-results.v1"
MANIFEST_SCHEMA = "lgm-game.transactions-t6-formal-manifest.v1"
STATUS_SCHEMA = "lgm-game.transactions-t6-formal-status.v1"
EXPECTED_CORE_SHA256 = (
    "081f327f8f83d79ab078adc61e76070c140f13e0ac9a0d8f423bfad15df59862"
)
EXPECTED_COMPONENT_RUNS = 4


class FormalEfficiencyIntegrityError(RuntimeError):
    """The primary T6 component failed its registered evidence contract."""


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
        raise FormalEfficiencyIntegrityError(
            f"Stale temporary file exists: {temporary}"
        )
    temporary.write_bytes(serialized)
    temporary.replace(path)


def immutable_json(path: Path, payload: Any) -> str:
    serialized = canonical_bytes(payload)
    digest = hashlib.sha256(serialized).hexdigest()
    if path.exists():
        if path.read_bytes() != serialized:
            raise FormalEfficiencyIntegrityError(
                f"Existing immutable artifact differs: {path}"
            )
        return digest
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(serialized)
    return digest


def registered_specs(delivery: Path) -> list[aggregate.RunSpec]:
    specs = [
        spec
        for spec in aggregate.expected_specs(delivery)
        if spec.family == "formal_main"
        and spec.variant in {"visual", "full"}
        and spec.seed == 1
    ]
    expected = [
        (dataset, variant, 1)
        for dataset in aggregate.DATASET_ORDER
        for variant in ("visual", "full")
    ]
    observed = [(spec.dataset, spec.variant, spec.seed) for spec in specs]
    if observed != expected or len(specs) != EXPECTED_COMPONENT_RUNS:
        raise FormalEfficiencyIntegrityError(
            "T6 formal registry is not exactly two datasets x two variants x seed 1."
        )
    return specs


def validate_sources(
    delivery: Path,
) -> tuple[list[aggregate.ValidRun], str]:
    formal = (
        delivery
        / "lgm_game_pytorch"
        / "lgm_game_pytorch"
        / "formal_retrieval.py"
    ).resolve(strict=True)
    formal_sha = sha256_file(formal)
    if formal_sha != EXPECTED_CORE_SHA256:
        raise FormalEfficiencyIntegrityError("Frozen formal core hash changed.")
    valid = []
    incomplete = {}
    for spec in registered_specs(delivery):
        try:
            valid.append(
                aggregate.validate_completed_run(
                    spec,
                    delivery,
                    formal_sha,
                )
            )
        except (aggregate.IntegrityError, OSError, ValueError) as error:
            incomplete[spec.identifier] = str(error)
    if incomplete:
        raise FormalEfficiencyIntegrityError(
            "T6 formal timing requires four complete seed-1 visual/full source "
            f"runs and official evaluations; {len(incomplete)} are unavailable. "
            f"Examples: {list(incomplete.items())[:3]}"
        )
    return valid, formal_sha


def _nvidia_smi(arguments: Sequence[str]) -> str:
    completed = subprocess.run(
        ["nvidia-smi", *arguments],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise FormalEfficiencyIntegrityError(
            f"nvidia-smi failed: {completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def assert_exclusive_gpu() -> None:
    text = _nvidia_smi(
        (
            "--query-compute-apps=pid,process_name",
            "--format=csv,noheader,nounits",
        )
    )
    conflicts = []
    for line in text.splitlines():
        if not line.strip():
            continue
        fields = [value.strip() for value in line.split(",", 1)]
        if len(fields) != 2:
            continue
        try:
            pid = int(fields[0])
        except ValueError:
            continue
        if pid != os.getpid():
            conflicts.append({"pid": pid, "process_name": fields[1]})
    if conflicts:
        raise FormalEfficiencyIntegrityError(
            f"T6 requires an exclusive GPU; active compute processes: {conflicts}"
        )


def gpu_snapshot(device_index: int) -> dict[str, Any]:
    fields = (
        "index,name,uuid,driver_version,memory.total,temperature.gpu,"
        "power.draw,power.limit,clocks.current.graphics,clocks.current.memory"
    )
    row = _nvidia_smi(
        (
            f"--query-gpu={fields}",
            "--format=csv,noheader,nounits",
            "-i",
            str(device_index),
        )
    ).splitlines()
    if len(row) != 1:
        raise FormalEfficiencyIntegrityError("GPU snapshot returned multiple rows.")
    values = [value.strip() for value in row[0].split(",")]
    names = fields.split(",")
    if len(values) != len(names):
        raise FormalEfficiencyIntegrityError("GPU snapshot field count mismatch.")
    return dict(zip(names, values, strict=True))


def _dataset_inputs(
    args: argparse.Namespace,
    dataset: str,
) -> tuple[Path, Path, Path | None]:
    delivery = args.delivery_root.resolve(strict=True)
    if dataset == "university1652":
        return (
            args.university_root.resolve(strict=True),
            (
                delivery
                / "lgm_game_pytorch"
                / "evidence_cache"
                / "university1652_clip_image_evidence.npz"
            ).resolve(strict=True),
            None,
        )
    return (
        args.sues_root.resolve(strict=True),
        (
            delivery
            / "lgm_game_pytorch"
            / "evidence_cache"
            / "sues200_clip_image_evidence.npz"
        ).resolve(strict=True),
        (
            delivery
            / "lgm_game_pytorch"
            / "manifests"
            / "sues200_official_train_ids.yaml"
        ).resolve(strict=True),
    )


def build_dataset_context(
    args: argparse.Namespace,
    dataset: str,
) -> tuple[
    core.EvidenceStore,
    list[core.RetrievalTask],
    dict[str, Any],
]:
    data_root, evidence_path, manifest_path = _dataset_inputs(args, dataset)
    store = core.EvidenceStore.load([evidence_path])
    records = core.derive_all_records(store, data_root, dataset)
    train_ids, manifest = core.parse_sues_manifest(manifest_path)
    tasks = core.build_official_evaluation_tasks(records, dataset, train_ids)
    if tuple(task.name for task in tasks) != aggregate.TASKS[dataset]:
        raise FormalEfficiencyIntegrityError(
            f"T6 {dataset} official task set changed."
        )
    descriptor = {
        "data_root": str(data_root),
        "evidence_path": str(evidence_path),
        "evidence_sha256": sha256_file(evidence_path),
        "evidence_meta_path": store.cache_descriptors[0].meta_path,
        "evidence_meta_sha256": store.cache_descriptors[0].meta_sha256,
        "sues_manifest": manifest if dataset == "sues200" else None,
        "protocol_membership_sha256": core.protocol_membership_hash(tasks),
    }
    return store, tasks, descriptor


def load_model(
    run: aggregate.ValidRun,
    device: torch.device,
) -> tuple[core.FormalRetrievalModel, dict[str, Any], dict[str, Any]]:
    checkpoint_path = run.spec.run_dir / "best.pt"
    checkpoint = core.load_torch_checkpoint(checkpoint_path, "cpu")
    if (
        checkpoint.get("schema_version") != core.SCHEMA_VERSION
        or checkpoint.get("epoch") != 79
        or checkpoint.get("best_epoch") != 79
        or checkpoint.get("immutable_config", {}).get("dataset")
        != run.spec.dataset
        or checkpoint.get("model_config", {}).get("variant")
        != run.spec.variant
    ):
        raise FormalEfficiencyIntegrityError(
            f"T6 source checkpoint provenance mismatch: {run.spec.identifier}"
        )
    config = dict(checkpoint["model_config"])
    model = core.FormalRetrievalModel(
        variant=config["variant"],
        backbone=config["backbone"],
        embed_dim=int(config["embed_dim"]),
        dropout=float(config["dropout"]),
        pretrained=False,
    )
    model.load_state_dict(checkpoint["model_state"], strict=True)
    model.to(device).eval()
    return model, config, checkpoint


def benchmark_encoding(
    model: core.FormalRetrievalModel,
    config: Mapping[str, Any],
    store: core.EvidenceStore,
    record: core.EvidenceRecord,
    device: torch.device,
) -> dict[str, Any]:
    _, transform = core.build_transforms(
        int(config["resize_size"]),
        int(config["image_size"]),
    )
    image = transform(core.load_rgb(record.absolute_path)).unsqueeze(0).to(device)
    content = torch.from_numpy(
        store.content_probs[record.evidence_index]
    ).unsqueeze(0).to(device)
    style = torch.from_numpy(
        store.style_probs[record.evidence_index]
    ).unsqueeze(0).to(device)
    amp_enabled = device.type == "cuda"

    def operation() -> torch.Tensor:
        with core.amp_context(device, amp_enabled):
            return model.encode_image(image, content, style)

    macs = count_conv_linear_macs(model, operation)
    torch.cuda.synchronize(device)
    torch.cuda.reset_peak_memory_stats(device)
    output = operation()
    torch.cuda.synchronize(device)
    peak_allocated = int(torch.cuda.max_memory_allocated(device))
    peak_reserved = int(torch.cuda.max_memory_reserved(device))
    descriptor_dimension = int(output.shape[1])
    del output
    timing = synchronize_cuda_latency(
        operation,
        device=device,
        warmup_repetitions=ENCODING_WARMUP_REPETITIONS,
        timed_repetitions=ENCODING_TIMED_REPETITIONS,
    )
    if timing["repetitions"] != ENCODING_TIMED_REPETITIONS:
        raise FormalEfficiencyIntegrityError(
            "T6 encoding timing repetition count changed."
        )
    return {
        **parameter_counts(model),
        "MACs": macs,
        "input_image_path": record.relative_path,
        "input_image_sha256": sha256_file(record.absolute_path),
        "batch_size": 1,
        "amp": amp_enabled,
        "descriptor_dimension": descriptor_dimension,
        "descriptor_storage_dtype": "float32",
        "descriptor_bytes_per_image": formal_model_descriptor_bytes(model),
        "peak_allocated_gpu_bytes_model_resident_batch1": peak_allocated,
        "peak_reserved_gpu_bytes_model_resident_batch1": peak_reserved,
        "encoding_latency": timing,
    }


def encode_dataset(
    model: core.FormalRetrievalModel,
    config: Mapping[str, Any],
    store: core.EvidenceStore,
    tasks: Sequence[core.RetrievalTask],
    device: torch.device,
    seed: int,
) -> dict[str, np.ndarray]:
    _, transform = core.build_transforms(
        int(config["resize_size"]),
        int(config["image_size"]),
    )
    records = [
        record
        for task in tasks
        for record in (*task.query, *task.gallery)
    ]
    return core.encode_records(
        model,
        records,
        store,
        transform,
        device,
        batch_size=128,
        workers=8,
        amp_enabled=True,
        seed=seed,
    )


def _stack_features(
    records: Sequence[core.EvidenceRecord],
    encoded: Mapping[str, np.ndarray],
) -> np.ndarray:
    values = np.stack(
        [encoded[record.relative_path.casefold()] for record in records]
    ).astype(np.float32, copy=False)
    norms = np.linalg.norm(values, axis=1)
    if not np.isfinite(values).all() or not np.allclose(
        norms,
        1.0,
        rtol=2e-4,
        atol=2e-4,
    ):
        raise FormalEfficiencyIntegrityError(
            "T6 encoded descriptors are non-finite or not L2-normalized."
        )
    return values


def _reported_metrics(
    run: aggregate.ValidRun,
    task: str,
) -> Mapping[str, Any]:
    payload = aggregate.load_json(run.spec.evaluation_dir / "metrics.json")
    result = payload.get("results", {}).get(task)
    if not isinstance(result, dict):
        raise FormalEfficiencyIntegrityError(
            f"T6 cannot find reported metrics for {task}."
        )
    return result


def _verify_full_gallery_metrics(
    observed: Mapping[str, Any],
    reported: Mapping[str, Any],
    identifier: str,
) -> None:
    for metric in (
        "r_at_1",
        "r_at_5",
        "r_at_10",
        "r_at_20",
        "official_trapezoid_mAP",
        "MRR",
    ):
        if not math.isclose(
            float(observed[metric]),
            float(reported[metric]),
            rel_tol=2e-6,
            abs_tol=2e-7,
        ):
            raise FormalEfficiencyIntegrityError(
                f"{identifier}: T6 full-gallery {metric} does not reproduce "
                "the completed official evaluation."
            )


def benchmark_task(
    run: aggregate.ValidRun,
    task: core.RetrievalTask,
    encoded: Mapping[str, np.ndarray],
    device: torch.device,
) -> dict[str, Any]:
    query = _stack_features(task.query, encoded)
    gallery = _stack_features(task.gallery, encoded)
    query_labels = [record.label for record in task.query]
    gallery_labels = [record.label for record in task.gallery]
    gallery_paths = [record.relative_path for record in task.gallery]
    scores = query @ gallery.T
    scaling_rows = []
    for requested in registered_gallery_sizes(len(task.gallery)):
        row = gallery_scaling_metrics(
            scores,
            query_labels,
            gallery_labels,
            gallery_paths,
            requested,
            sampling_seed=GALLERY_SAMPLING_SEED,
        )
        scaling_rows.append(row)
    full = scaling_rows[-1]
    _verify_full_gallery_metrics(
        full,
        _reported_metrics(run, task.name),
        f"{run.spec.identifier}/{task.name}",
    )

    query_gpu = torch.from_numpy(query).to(device)
    gallery_gpu = torch.from_numpy(gallery).to(device)

    def rank_operation() -> torch.Tensor:
        score = query_gpu @ gallery_gpu.T
        return torch.argsort(score, dim=1, descending=True, stable=True)

    torch.cuda.synchronize(device)
    torch.cuda.reset_peak_memory_stats(device)
    ranking = rank_operation()
    torch.cuda.synchronize(device)
    peak_allocated = int(torch.cuda.max_memory_allocated(device))
    peak_reserved = int(torch.cuda.max_memory_reserved(device))
    del ranking
    timing = synchronize_cuda_latency(
        rank_operation,
        device=device,
        warmup_repetitions=RANKING_WARMUP_REPETITIONS,
        timed_repetitions=RANKING_TIMED_REPETITIONS,
    )
    timing["queries_per_second"] = (
        len(task.query) / (timing["median"] / 1000.0)
    )
    return {
        "dataset": run.spec.dataset,
        "variant": run.spec.variant,
        "seed": run.spec.seed,
        "task": task.name,
        "queries": len(task.query),
        "gallery_images": len(task.gallery),
        "protocol": task.protocol,
        "ranking_definition": (
            "CUDA float32 complete cosine score matrix plus stable full argsort"
        ),
        "ranking_latency": timing,
        "ranking_peak_allocated_gpu_bytes": peak_allocated,
        "ranking_peak_reserved_gpu_bytes": peak_reserved,
        "gallery_sampling_seed": GALLERY_SAMPLING_SEED,
        "gallery_scaling": scaling_rows,
    }


def write_model_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fields = (
        "dataset",
        "variant",
        "seed",
        "total_parameters",
        "trainable_parameters",
        "MACs_per_image",
        "descriptor_dimension",
        "descriptor_bytes_per_image",
        "peak_allocated_gpu_bytes",
        "encoding_latency_median_ms",
        "encoding_latency_q1_ms",
        "encoding_latency_q3_ms",
    )
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            encoding = row["encoding"]
            latency = encoding["encoding_latency"]
            writer.writerow(
                {
                    "dataset": row["dataset"],
                    "variant": row["variant"],
                    "seed": row["seed"],
                    "total_parameters": encoding["total_parameters"],
                    "trainable_parameters": encoding["trainable_parameters"],
                    "MACs_per_image": encoding["MACs"]["MACs_per_image"],
                    "descriptor_dimension": encoding["descriptor_dimension"],
                    "descriptor_bytes_per_image": encoding[
                        "descriptor_bytes_per_image"
                    ],
                    "peak_allocated_gpu_bytes": encoding[
                        "peak_allocated_gpu_bytes_model_resident_batch1"
                    ],
                    "encoding_latency_median_ms": latency["median"],
                    "encoding_latency_q1_ms": latency["q1"],
                    "encoding_latency_q3_ms": latency["q3"],
                }
            )
    temporary.replace(path)


def write_task_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fields = (
        "dataset",
        "variant",
        "seed",
        "task",
        "queries",
        "gallery_images",
        "ranking_latency_median_ms",
        "ranking_queries_per_second",
        "requested_gallery_size",
        "mean_effective_gallery_size",
        "r_at_1",
        "official_trapezoid_mAP",
        "MRR",
        "full_gallery",
    )
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            for scale in row["gallery_scaling"]:
                writer.writerow(
                    {
                        "dataset": row["dataset"],
                        "variant": row["variant"],
                        "seed": row["seed"],
                        "task": row["task"],
                        "queries": row["queries"],
                        "gallery_images": row["gallery_images"],
                        "ranking_latency_median_ms": row[
                            "ranking_latency"
                        ]["median"],
                        "ranking_queries_per_second": row[
                            "ranking_latency"
                        ]["queries_per_second"],
                        "requested_gallery_size": scale[
                            "requested_gallery_size"
                        ],
                        "mean_effective_gallery_size": scale[
                            "mean_effective_gallery_size"
                        ],
                        "r_at_1": scale["r_at_1"],
                        "official_trapezoid_mAP": scale[
                            "official_trapezoid_mAP"
                        ],
                        "MRR": scale["MRR"],
                        "full_gallery": scale["full_gallery"],
                    }
                )
    temporary.replace(path)


def build_config(
    args: argparse.Namespace,
    runs: Sequence[aggregate.ValidRun],
    formal_sha: str,
) -> dict[str, Any]:
    delivery = args.delivery_root.resolve(strict=True)
    protocol = (delivery / "TRANSACTIONS_EXTENSION_PROTOCOL.md").resolve(
        strict=True
    )
    primitive = (
        Path(__file__).resolve().parent / "transactions_efficiency_analysis.py"
    ).resolve(strict=True)
    datasets = {}
    for dataset in aggregate.DATASET_ORDER:
        data_root, evidence, manifest = _dataset_inputs(args, dataset)
        metadata = core.find_meta_path(evidence).resolve(strict=True)
        datasets[dataset] = {
            "data_root": str(data_root),
            "evidence_path": str(evidence),
            "evidence_bytes": evidence.stat().st_size,
            "evidence_sha256": sha256_file(evidence),
            "evidence_meta_path": str(metadata),
            "evidence_meta_bytes": metadata.stat().st_size,
            "evidence_meta_sha256": sha256_file(metadata),
            "sues_manifest": (
                {
                    "path": str(manifest),
                    "bytes": manifest.stat().st_size,
                    "sha256": sha256_file(manifest),
                }
                if manifest is not None
                else None
            ),
        }
    return {
        "schema_version": CONFIG_SCHEMA,
        "scope": "primary visual/full seed-1 component of T6",
        "component_complete_is_full_t6_complete": False,
        "registered_run_count": len(runs),
        "registered_runs": [
            {
                "dataset": run.spec.dataset,
                "variant": run.spec.variant,
                "seed": run.spec.seed,
                "checkpoint_sha256": run.checkpoint_sha256,
                "evaluation_metrics_sha256": run.metrics_sha256,
                "protocol_membership_sha256": (
                    run.protocol_membership_sha256
                ),
            }
            for run in runs
        ],
        "device_index": args.device_index,
        "encoding_timing": {
            "batch_size": 1,
            "warmup_repetitions": ENCODING_WARMUP_REPETITIONS,
            "timed_repetitions": ENCODING_TIMED_REPETITIONS,
            "CUDA_AMP": True,
        },
        "ranking_timing": {
            "warmup_repetitions": RANKING_WARMUP_REPETITIONS,
            "timed_repetitions": RANKING_TIMED_REPETITIONS,
            "operation": "float32 score matrix plus stable full argsort",
        },
        "gallery_scaling": {
            "candidate_sizes": [100, 250, 500, 1000, 5000, 10000],
            "full_gallery_always_included": True,
            "sampling_seed": GALLERY_SAMPLING_SEED,
            "policy": (
                "retain all positives and take fixed BLAKE2b "
                "path-hash-ordered negatives"
            ),
        },
        "formal_core_sha256": formal_sha,
        "datasets": datasets,
        "runner_path": str(Path(__file__).resolve()),
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "primitive_path": str(primitive),
        "primitive_sha256": sha256_file(primitive),
        "protocol_path": str(protocol),
        "protocol_sha256": sha256_file(protocol),
    }


def run_benchmark(args: argparse.Namespace) -> dict[str, Any]:
    delivery = args.delivery_root.resolve(strict=True)
    runs, formal_sha = validate_sources(delivery)
    assert_exclusive_gpu()
    if not torch.cuda.is_available():
        raise FormalEfficiencyIntegrityError("CUDA is unavailable for T6.")
    device = torch.device(f"cuda:{args.device_index}")
    if args.device_index >= torch.cuda.device_count():
        raise FormalEfficiencyIntegrityError("T6 CUDA device index is unavailable.")
    torch.cuda.set_device(device)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    core.seed_everything(20260730)
    config = build_config(args, runs, formal_sha)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    config_path = output / "transactions_t6_formal_config.json"
    config_sha = immutable_json(config_path, config)
    manifest_path = output / "transactions_t6_formal_manifest.json"
    if manifest_path.exists():
        raise FormalEfficiencyIntegrityError(
            "T6 formal component already has a complete manifest."
        )
    retained = [path for path in output.iterdir() if path != config_path]
    if retained:
        raise FormalEfficiencyIntegrityError(
            "T6 formal output retains an incomplete attempt; archive it before "
            f"an explicit restart: {[path.name for path in retained]}"
        )
    status_path = output / "transactions_t6_formal_status.json"
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
    before = gpu_snapshot(args.device_index)
    try:
        model_rows = []
        task_rows = []
        run_index = {
            (run.spec.dataset, run.spec.variant): run for run in runs
        }
        for dataset in aggregate.DATASET_ORDER:
            store, tasks, dataset_descriptor = build_dataset_context(
                args,
                dataset,
            )
            for variant in ("visual", "full"):
                run = run_index[(dataset, variant)]
                model, model_config, _ = load_model(run, device)
                fixed_record = tasks[0].query[0]
                encoding = benchmark_encoding(
                    model,
                    model_config,
                    store,
                    fixed_record,
                    device,
                )
                model_rows.append(
                    {
                        "dataset": dataset,
                        "variant": variant,
                        "seed": 1,
                        "checkpoint_sha256": run.checkpoint_sha256,
                        "dataset_evidence": dataset_descriptor,
                        "encoding": encoding,
                    }
                )
                encoded = encode_dataset(
                    model,
                    model_config,
                    store,
                    tasks,
                    device,
                    seed=1,
                )
                for task in tasks:
                    task_rows.append(
                        benchmark_task(
                            run,
                            task,
                            encoded,
                            device,
                        )
                    )
                del encoded
                del model
                torch.cuda.empty_cache()
        expected_tasks = 2 * sum(
            len(aggregate.TASKS[dataset])
            for dataset in aggregate.DATASET_ORDER
        )
        if len(model_rows) != 4 or len(task_rows) != expected_tasks:
            raise FormalEfficiencyIntegrityError(
                "T6 formal component output coverage changed."
            )
        after = gpu_snapshot(args.device_index)
        results_payload = {
            "schema_version": RESULT_SCHEMA,
            "status": "completed_primary_component",
            "manuscript_result": False,
            "full_t6_complete": False,
            "unit": "fraction",
            "config_sha256": config_sha,
            "gpu_before": before,
            "gpu_after": after,
            "model_rows": model_rows,
            "task_rows": task_rows,
            "note": (
                "Real primary-model component; withheld from manuscript until "
                "the registered locally trained baseline efficiency rows are "
                "measured and the combined T6 manifest is complete."
            ),
        }
        results_payload["payload_sha256"] = canonical_sha256(results_payload)
        results_path = output / "transactions_t6_formal_results.json"
        immutable_json(results_path, results_payload)
        model_csv = output / "transactions_t6_formal_models.csv"
        task_csv = output / "transactions_t6_formal_tasks.csv"
        write_model_csv(model_csv, model_rows)
        write_task_csv(task_csv, task_rows)
        manifest_payload = {
            "schema_version": MANIFEST_SCHEMA,
            "status": "completed_primary_component",
            "manuscript_result": False,
            "full_t6_complete": False,
            "config_path": str(config_path),
            "config_sha256": config_sha,
            "results_path": str(results_path.resolve()),
            "results_sha256": sha256_file(results_path),
            "model_csv_path": str(model_csv.resolve()),
            "model_csv_sha256": sha256_file(model_csv),
            "task_csv_path": str(task_csv.resolve()),
            "task_csv_sha256": sha256_file(task_csv),
            "model_row_count": len(model_rows),
            "task_row_count": len(task_rows),
            "elapsed_seconds": time.perf_counter() - started,
            "completed_utc": utc_now(),
        }
        manifest = {
            **manifest_payload,
            "payload_sha256": canonical_sha256(manifest_payload),
        }
        immutable_json(manifest_path, manifest)
        atomic_json(
            status_path,
            {
                "schema_version": STATUS_SCHEMA,
                "status": "completed_primary_component",
                "config_sha256": config_sha,
                "manifest_sha256": sha256_file(manifest_path),
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
        "--delivery-root",
        type=Path,
        default=DELIVERY_ROOT_DEFAULT,
    )
    parser.add_argument("--university-root", type=Path, required=True)
    parser.add_argument("--sues-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--device-index", type=int, default=0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.device_index < 0:
        raise SystemExit("ERROR: --device-index must be non-negative.")
    if args.output_dir is None:
        args.output_dir = (
            args.delivery_root
            / "lgm_game_pytorch"
            / "analysis"
            / "transactions_t6_formal"
        )
    try:
        manifest = run_benchmark(args)
    except (
        FormalEfficiencyIntegrityError,
        EfficiencyIntegrityError,
        aggregate.IntegrityError,
        OSError,
        ValueError,
        RuntimeError,
    ) as error:
        raise SystemExit(f"ERROR: {error}") from error
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
