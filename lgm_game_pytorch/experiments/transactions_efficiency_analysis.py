"""Auditable T6 complexity, timing, and gallery-scaling primitives."""

from __future__ import annotations

import hashlib
import math
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import torch
from torch import nn

from lgm_game_pytorch import formal_retrieval as core


GALLERY_SAMPLING_SEED = 20260727
ENCODING_WARMUP_REPETITIONS = 20
ENCODING_TIMED_REPETITIONS = 100
RANKING_WARMUP_REPETITIONS = 5
RANKING_TIMED_REPETITIONS = 20


class EfficiencyIntegrityError(RuntimeError):
    """An efficiency/scaling input violates the registered T6 contract."""


def canonical_path(value: Any) -> str:
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return str(value).strip().replace("\\", "/").casefold()


def stable_gallery_permutation(
    gallery_paths: Sequence[str],
    seed: int = GALLERY_SAMPLING_SEED,
) -> np.ndarray:
    """Match the existing controlled-baseline path-hash negative ordering."""

    canonical = [canonical_path(path) for path in gallery_paths]
    if len(canonical) <= 0 or len(set(canonical)) != len(canonical):
        raise EfficiencyIntegrityError("Gallery paths are empty or duplicated.")
    hashes = np.empty(len(canonical), dtype=np.uint64)
    for index, path in enumerate(canonical):
        payload = f"{seed}|{path}".encode("utf-8")
        hashes[index] = int.from_bytes(
            hashlib.blake2b(payload, digest_size=8).digest(),
            "little",
        )
    return np.argsort(hashes, kind="stable").astype(np.int64, copy=False)


def official_trapezoid_ap(positive_zero_based_ranks: np.ndarray) -> float:
    positions = np.asarray(positive_zero_based_ranks, dtype=np.int64)
    if positions.ndim != 1 or positions.size <= 0 or (positions < 0).any():
        raise EfficiencyIntegrityError("Positive ranks must be non-empty and valid.")
    indices = np.arange(len(positions), dtype=np.float64)
    ranks = positions.astype(np.float64)
    precision = (indices + 1.0) / (ranks + 1.0)
    old_precision = np.ones_like(ranks)
    nonzero = ranks != 0.0
    old_precision[nonzero] = indices[nonzero] / ranks[nonzero]
    return float(np.mean((old_precision + precision) * 0.5))


def gallery_scaling_metrics(
    scores: np.ndarray,
    query_labels: Sequence[str],
    gallery_labels: Sequence[str],
    gallery_paths: Sequence[str],
    requested_gallery_size: int | None,
    *,
    sampling_seed: int = GALLERY_SAMPLING_SEED,
) -> dict[str, Any]:
    values = np.asarray(scores, dtype=np.float32)
    query = np.asarray([str(value) for value in query_labels], dtype=str)
    gallery = np.asarray([str(value) for value in gallery_labels], dtype=str)
    if (
        values.ndim != 2
        or values.shape != (len(query), len(gallery))
        or len(query) <= 0
        or len(gallery) <= 0
        or not np.isfinite(values).all()
    ):
        raise EfficiencyIntegrityError("Gallery-scaling score inputs are invalid.")
    if len(gallery_paths) != len(gallery):
        raise EfficiencyIntegrityError("Gallery path/label counts differ.")
    if requested_gallery_size is not None and requested_gallery_size <= 0:
        raise EfficiencyIntegrityError("Requested gallery size must be positive.")
    permutation = stable_gallery_permutation(gallery_paths, sampling_seed)
    full = (
        requested_gallery_size is None
        or requested_gallery_size >= len(gallery)
    )
    recalls = {1: 0, 5: 0, 10: 0, 20: 0}
    aps = np.empty(len(query), dtype=np.float64)
    reciprocal = np.empty(len(query), dtype=np.float64)
    effective = np.empty(len(query), dtype=np.int64)
    selected_memberships = []
    for query_index, label in enumerate(query):
        positive = np.flatnonzero(gallery == label)
        if positive.size <= 0:
            raise EfficiencyIntegrityError(
                f"Query {query_index} has no positive gallery image."
            )
        if full:
            selected = np.arange(len(gallery), dtype=np.int64)
        else:
            requested = max(int(requested_gallery_size), int(positive.size))
            negative_mask = gallery != label
            negative_order = permutation[negative_mask[permutation]]
            needed = min(
                requested - int(positive.size),
                int(negative_order.size),
            )
            # Preserve frozen gallery order for deterministic equal-score ties.
            selected = np.sort(
                np.concatenate((positive, negative_order[:needed]))
            ).astype(np.int64, copy=False)
        ranking = selected[
            np.argsort(-values[query_index, selected], kind="stable")
        ]
        hits = gallery[ranking] == label
        positions = np.flatnonzero(hits)
        if positions.size != positive.size:
            raise EfficiencyIntegrityError(
                "Positive-preserving gallery selection lost a positive."
            )
        first = int(positions[0])
        for cutoff in recalls:
            recalls[cutoff] += int(first < min(cutoff, len(selected)))
        aps[query_index] = official_trapezoid_ap(positions)
        reciprocal[query_index] = 1.0 / (first + 1.0)
        effective[query_index] = len(selected)
        selected_memberships.append(
            hashlib.sha256(
                "\n".join(
                    canonical_path(gallery_paths[index]) for index in selected
                ).encode("utf-8")
            ).hexdigest()
        )
    count = len(query)
    return {
        "requested_gallery_size": (
            len(gallery) if requested_gallery_size is None else requested_gallery_size
        ),
        "full_gallery": full,
        "full_gallery_size": len(gallery),
        "queries": count,
        "mean_effective_gallery_size": float(effective.mean()),
        "minimum_effective_gallery_size": int(effective.min()),
        "maximum_effective_gallery_size": int(effective.max()),
        "r_at_1": recalls[1] / count,
        "r_at_5": recalls[5] / count,
        "r_at_10": recalls[10] / count,
        "r_at_20": recalls[20] / count,
        "official_trapezoid_mAP": float(aps.mean()),
        "MRR": float(reciprocal.mean()),
        "sampling_seed": sampling_seed,
        "negative_sampling": (
            "none; complete gallery"
            if full
            else "all positives plus fixed BLAKE2b path-hash-ordered negatives"
        ),
        "per_query_selection_membership_sha256": hashlib.sha256(
            "\n".join(selected_memberships).encode("utf-8")
        ).hexdigest(),
    }


def registered_gallery_sizes(full_gallery_size: int) -> tuple[int | None, ...]:
    if full_gallery_size <= 0:
        raise EfficiencyIntegrityError("Full gallery size must be positive.")
    candidates = (
        100,
        250,
        500,
        1_000,
        5_000,
        10_000,
    )
    retained = tuple(value for value in candidates if value < full_gallery_size)
    return (*retained, None)


def parameter_counts(model: nn.Module) -> dict[str, int]:
    parameters = list(model.parameters())
    return {
        "total_parameters": int(sum(value.numel() for value in parameters)),
        "trainable_parameters": int(
            sum(value.numel() for value in parameters if value.requires_grad)
        ),
    }


def count_conv_linear_macs(
    model: nn.Module,
    encode_call: Callable[[], torch.Tensor],
) -> dict[str, Any]:
    """Count Conv2d/Linear MACs for one registered encoding forward pass."""

    module_names = {module: name for name, module in model.named_modules()}
    rows: dict[str, dict[str, Any]] = {}
    handles = []

    def hook(module: nn.Module, inputs: tuple[Any, ...], output: Any) -> None:
        if not isinstance(output, torch.Tensor):
            raise EfficiencyIntegrityError(
                f"MAC-counted module {module_names[module]} returned non-tensor output."
            )
        if isinstance(module, nn.Conv2d):
            kernel = module.kernel_size
            operations = (
                output.numel()
                * (module.in_channels // module.groups)
                * kernel[0]
                * kernel[1]
            )
            kind = "Conv2d"
        elif isinstance(module, nn.Linear):
            operations = output.numel() * module.in_features
            kind = "Linear"
        else:
            return
        name = module_names[module]
        row = rows.setdefault(
            name,
            {
                "module": name,
                "type": kind,
                "calls": 0,
                "MACs": 0,
            },
        )
        row["calls"] += 1
        row["MACs"] += int(operations)

    for module in model.modules():
        if isinstance(module, (nn.Conv2d, nn.Linear)):
            handles.append(module.register_forward_hook(hook))
    try:
        with torch.inference_mode():
            result = encode_call()
        if not isinstance(result, torch.Tensor) or result.ndim != 2:
            raise EfficiencyIntegrityError(
                "Registered encoding call did not return a B x D descriptor."
            )
    finally:
        for handle in handles:
            handle.remove()
    ordered = [rows[name] for name in sorted(rows)]
    total = int(sum(row["MACs"] for row in ordered))
    return {
        "scope": "Conv2d and Linear multiply-accumulate operations",
        "excluded_operations": [
            "normalization",
            "activation",
            "pooling",
            "elementwise fusion",
            "descriptor L2 normalization",
        ],
        "batch_size": int(result.shape[0]),
        "descriptor_dimension": int(result.shape[1]),
        "MACs_per_batch": total,
        "MACs_per_image": total / int(result.shape[0]),
        "module_rows": ordered,
    }


def latency_summary(samples_ms: Sequence[float]) -> dict[str, Any]:
    values = np.asarray(samples_ms, dtype=np.float64)
    if (
        values.ndim != 1
        or values.size <= 0
        or not np.isfinite(values).all()
        or (values <= 0.0).any()
    ):
        raise EfficiencyIntegrityError("Latency samples must be finite and positive.")
    return {
        "repetitions": int(values.size),
        "unit": "ms",
        "median": float(np.median(values)),
        "q1": float(np.quantile(values, 0.25, method="linear")),
        "q3": float(np.quantile(values, 0.75, method="linear")),
        "IQR": float(
            np.quantile(values, 0.75, method="linear")
            - np.quantile(values, 0.25, method="linear")
        ),
        "minimum": float(values.min()),
        "maximum": float(values.max()),
        "mean": float(values.mean()),
        "sample_sd": (
            float(values.std(ddof=1)) if values.size >= 2 else None
        ),
    }


def synchronize_cuda_latency(
    operation: Callable[[], Any],
    *,
    device: torch.device,
    warmup_repetitions: int,
    timed_repetitions: int,
) -> dict[str, Any]:
    if device.type != "cuda":
        raise EfficiencyIntegrityError("Registered T6 timing requires CUDA.")
    if warmup_repetitions < 0 or timed_repetitions <= 0:
        raise EfficiencyIntegrityError("Timing repetition counts are invalid.")
    for _ in range(warmup_repetitions):
        operation()
    torch.cuda.synchronize(device)
    samples = []
    for _ in range(timed_repetitions):
        start = torch.cuda.Event(enable_timing=True)
        stop = torch.cuda.Event(enable_timing=True)
        start.record()
        operation()
        stop.record()
        stop.synchronize()
        elapsed = float(start.elapsed_time(stop))
        if not math.isfinite(elapsed) or elapsed <= 0.0:
            raise EfficiencyIntegrityError("CUDA event returned invalid latency.")
        samples.append(elapsed)
    return {
        "warmup_repetitions": warmup_repetitions,
        **latency_summary(samples),
    }


def formal_model_descriptor_bytes(model: core.FormalRetrievalModel) -> int:
    if int(model.embed_dim) <= 0:
        raise EfficiencyIntegrityError("Formal descriptor dimension is invalid.")
    return int(model.embed_dim) * np.dtype(np.float32).itemsize

