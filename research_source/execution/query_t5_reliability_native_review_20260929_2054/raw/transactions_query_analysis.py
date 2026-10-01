"""Pure, auditable T4/T5 query-level analysis primitives.

This module does not discover experiment files or write manuscript artifacts.
It validates retained per-query arrays and implements the pre-specified
semantic strata, paired summaries, calibration, and selective-retrieval
calculations used by the Transactions extension runner.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


ARRAY_FIELDS = {
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
STRATUM_METRICS = (
    "r_at_1",
    "official_trapezoid_mAP",
    "MRR",
)
DEFAULT_BOOTSTRAP_SAMPLES = 10_000
DEFAULT_MINIMUM_STRATUM_QUERIES = 100
DEFAULT_ECE_BINS = 15
RISK_COVERAGES = tuple(index / 10.0 for index in range(1, 11))
SELECTIVE_COVERAGES = (0.50, 0.75, 0.90, 1.00)
QUARTILE_LABELS = (
    "q1_low",
    "q2_mid_low",
    "q3_mid_high",
    "q4_high",
)


class QueryAnalysisError(RuntimeError):
    """A query-level artifact violates the registered analysis contract."""


def canonical_query_path(value: Any) -> str:
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return str(value).strip().replace("\\", "/").casefold()


def text_array(values: np.ndarray) -> np.ndarray:
    return np.asarray(
        [
            value.decode("utf-8") if isinstance(value, bytes) else str(value)
            for value in np.asarray(values).reshape(-1)
        ],
        dtype=str,
    )


def canonical_sha256(value: Any) -> str:
    serialized = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


@dataclass(frozen=True)
class QueryArrays:
    paths: np.ndarray
    labels: np.ndarray
    correct: np.ndarray
    official_ap: np.ndarray
    reciprocal_rank: np.ndarray
    margin: np.ndarray
    top1_gallery_indices: np.ndarray
    top1_gallery_paths: np.ndarray
    top1_gallery_labels: np.ndarray

    @property
    def size(self) -> int:
        return int(len(self.paths))

    def reordered(self, indices: np.ndarray) -> "QueryArrays":
        order = np.asarray(indices, dtype=np.int64)
        if order.ndim != 1 or len(order) != self.size:
            raise QueryAnalysisError("A query-array reorder must be a full vector.")
        if set(order.tolist()) != set(range(self.size)):
            raise QueryAnalysisError("A query-array reorder must be a permutation.")
        return QueryArrays(
            paths=self.paths[order],
            labels=self.labels[order],
            correct=self.correct[order],
            official_ap=self.official_ap[order],
            reciprocal_rank=self.reciprocal_rank[order],
            margin=self.margin[order],
            top1_gallery_indices=self.top1_gallery_indices[order],
            top1_gallery_paths=self.top1_gallery_paths[order],
            top1_gallery_labels=self.top1_gallery_labels[order],
        )


def load_query_arrays(path: Path) -> QueryArrays:
    try:
        with np.load(path, allow_pickle=False) as archive:
            if set(archive.files) != ARRAY_FIELDS:
                raise QueryAnalysisError(
                    f"{path}: per-query field set changed; "
                    f"expected {sorted(ARRAY_FIELDS)}, found {sorted(archive.files)}."
                )
            raw = {name: np.asarray(archive[name]) for name in ARRAY_FIELDS}
    except (OSError, ValueError) as error:
        if isinstance(error, QueryAnalysisError):
            raise
        raise QueryAnalysisError(f"Cannot read {path}: {error}") from error
    shapes = {name: value.shape for name, value in raw.items()}
    if any(len(shape) != 1 for shape in shapes.values()):
        raise QueryAnalysisError(f"{path}: all per-query arrays must be vectors: {shapes}")
    lengths = {shape[0] for shape in shapes.values()}
    if len(lengths) != 1 or next(iter(lengths), 0) <= 0:
        raise QueryAnalysisError(f"{path}: per-query vector lengths are invalid.")
    count = lengths.pop()
    if raw["correct"].dtype.kind != "b":
        raise QueryAnalysisError(f"{path}: correct must have Boolean dtype.")
    if raw["top1_gallery_indices"].dtype.kind not in {"i", "u"}:
        raise QueryAnalysisError(f"{path}: top-1 indices must have integer dtype.")
    for name in (
        "query_paths",
        "query_labels",
        "top1_gallery_paths",
        "top1_gallery_labels",
    ):
        if raw[name].dtype.kind not in {"U", "S"}:
            raise QueryAnalysisError(f"{path}: {name} must be a text vector.")

    paths = np.asarray(
        [canonical_query_path(value) for value in raw["query_paths"]],
        dtype=str,
    )
    labels = text_array(raw["query_labels"])
    top1_paths = np.asarray(
        [canonical_query_path(value) for value in raw["top1_gallery_paths"]],
        dtype=str,
    )
    top1_labels = text_array(raw["top1_gallery_labels"])
    correct = np.asarray(raw["correct"], dtype=np.bool_)
    official_ap = np.asarray(
        raw["per_query_official_trapezoid_AP"],
        dtype=np.float64,
    )
    reciprocal = np.asarray(raw["reciprocal_rank"], dtype=np.float64)
    margin = np.asarray(raw["margin"], dtype=np.float64)
    indices = np.asarray(raw["top1_gallery_indices"], dtype=np.int64)

    if len(set(paths.tolist())) != count or any(not value for value in paths):
        raise QueryAnalysisError(f"{path}: query paths are empty or duplicated.")
    if any(not value for value in top1_paths):
        raise QueryAnalysisError(f"{path}: top-1 gallery paths are empty.")
    if not np.array_equal(correct, labels == top1_labels):
        raise QueryAnalysisError(
            f"{path}: correctness disagrees with query/top-1 labels."
        )
    if (
        not np.isfinite(official_ap).all()
        or (official_ap < 0.0).any()
        or (official_ap > 1.0).any()
    ):
        raise QueryAnalysisError(f"{path}: official AP values are invalid.")
    if (
        not np.isfinite(reciprocal).all()
        or (reciprocal <= 0.0).any()
        or (reciprocal > 1.0).any()
    ):
        raise QueryAnalysisError(f"{path}: reciprocal ranks are invalid.")
    first_ranks = np.rint(1.0 / reciprocal).astype(np.int64)
    if (
        (first_ranks < 1).any()
        or not np.allclose(
            reciprocal,
            1.0 / first_ranks,
            rtol=2e-6,
            atol=2e-7,
        )
        or not np.array_equal(correct, first_ranks == 1)
    ):
        raise QueryAnalysisError(
            f"{path}: reciprocal ranks do not encode correctness-consistent "
            "positive integer ranks."
        )
    if not np.isfinite(margin).all() or (margin < -2e-6).any():
        raise QueryAnalysisError(f"{path}: top-1 margins are invalid.")
    if (indices < 0).any():
        raise QueryAnalysisError(f"{path}: top-1 gallery indices are negative.")

    return QueryArrays(
        paths=paths,
        labels=labels,
        correct=correct,
        official_ap=official_ap,
        reciprocal_rank=reciprocal,
        margin=margin,
        top1_gallery_indices=indices,
        top1_gallery_paths=top1_paths,
        top1_gallery_labels=top1_labels,
    )


def align_visual_full(
    visual: QueryArrays,
    full: QueryArrays,
) -> tuple[QueryArrays, QueryArrays]:
    if visual.size != full.size:
        raise QueryAnalysisError("Visual/full query counts differ.")
    lookup = {path: index for index, path in enumerate(full.paths.tolist())}
    if set(visual.paths.tolist()) != set(lookup):
        raise QueryAnalysisError("Visual/full query path membership differs.")
    order = np.asarray([lookup[path] for path in visual.paths], dtype=np.int64)
    aligned = full.reordered(order)
    if not np.array_equal(visual.labels, aligned.labels):
        raise QueryAnalysisError("Visual/full query labels differ after alignment.")
    return visual, aligned


def normalized_entropy(probabilities: np.ndarray) -> np.ndarray:
    values = np.asarray(probabilities, dtype=np.float64)
    if values.ndim != 2 or values.shape[0] <= 0 or values.shape[1] < 2:
        raise QueryAnalysisError("Entropy input must be a non-empty N x K matrix.")
    if not np.isfinite(values).all() or (values < 0.0).any():
        raise QueryAnalysisError("Entropy probabilities are non-finite or negative.")
    totals = values.sum(axis=1)
    if not np.allclose(totals, 1.0, rtol=2e-2, atol=2e-2):
        raise QueryAnalysisError("Entropy rows do not sum to one.")
    normalized = values / totals[:, None]
    terms = np.zeros_like(normalized)
    positive = normalized > 0.0
    terms[positive] = normalized[positive] * np.log(normalized[positive])
    entropy = -terms.sum(axis=1) / math.log(values.shape[1])
    if not np.isfinite(entropy).all() or (entropy < -1e-12).any() or (
        entropy > 1.0 + 1e-12
    ).any():
        raise QueryAnalysisError("Normalized entropy left [0, 1].")
    return np.clip(entropy, 0.0, 1.0)


def quartile_assignment(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    vector = np.asarray(values, dtype=np.float64)
    if vector.ndim != 1 or vector.size <= 0 or not np.isfinite(vector).all():
        raise QueryAnalysisError("Quartile input must be a finite non-empty vector.")
    cuts = np.quantile(vector, (0.25, 0.50, 0.75), method="linear")
    groups = np.searchsorted(cuts, vector, side="left").astype(np.int8)
    if (groups < 0).any() or (groups > 3).any():
        raise QueryAnalysisError("Quartile assignment left the registered range.")
    return groups, np.asarray(cuts, dtype=np.float64)


def balanced_semantic_features(
    content_probabilities: np.ndarray,
    style_probabilities: np.ndarray,
) -> np.ndarray:
    content = np.asarray(content_probabilities, dtype=np.float64)
    style = np.asarray(style_probabilities, dtype=np.float64)
    if (
        content.ndim != 2
        or style.ndim != 2
        or content.shape[0] != style.shape[0]
        or content.shape[0] <= 0
    ):
        raise QueryAnalysisError("Content/style semantic matrices are incompatible.")
    if (
        not np.isfinite(content).all()
        or not np.isfinite(style).all()
        or (content < 0.0).any()
        or (style < 0.0).any()
    ):
        raise QueryAnalysisError("Semantic probability matrices are invalid.")
    content_norm = np.linalg.norm(content, axis=1, keepdims=True)
    style_norm = np.linalg.norm(style, axis=1, keepdims=True)
    if (content_norm <= 0.0).any() or (style_norm <= 0.0).any():
        raise QueryAnalysisError("A semantic probability block has zero norm.")
    content_unit = content / content_norm
    style_unit = style / style_norm
    features = np.concatenate((content_unit, style_unit), axis=1)
    features /= np.linalg.norm(features, axis=1, keepdims=True)
    return features.astype(np.float32)


def semantic_nearest_labels(
    query_content: np.ndarray,
    query_style: np.ndarray,
    gallery_content: np.ndarray,
    gallery_style: np.ndarray,
    gallery_labels: Sequence[str],
    chunk_size: int = 512,
) -> np.ndarray:
    if chunk_size <= 0:
        raise QueryAnalysisError("Semantic-neighbour chunk size must be positive.")
    query = balanced_semantic_features(query_content, query_style)
    gallery = balanced_semantic_features(gallery_content, gallery_style)
    labels = np.asarray([str(value) for value in gallery_labels], dtype=str)
    if len(labels) != gallery.shape[0] or gallery.shape[0] <= 0:
        raise QueryAnalysisError("Semantic gallery labels do not match its rows.")
    output = np.empty(query.shape[0], dtype=labels.dtype)
    for start in range(0, query.shape[0], chunk_size):
        stop = min(start + chunk_size, query.shape[0])
        scores = query[start:stop] @ gallery.T
        # np.argmax returns the first maximum, matching the frozen gallery order.
        output[start:stop] = labels[np.argmax(scores, axis=1)]
    return output


def _paired_metric_matrix(
    visual: QueryArrays,
    full: QueryArrays,
    mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    selected = np.asarray(mask, dtype=np.bool_)
    if selected.shape != (visual.size,) or not selected.any():
        raise QueryAnalysisError("A stratum mask must select at least one query.")
    visual_values = np.column_stack(
        (
            visual.correct.astype(np.float64),
            visual.official_ap,
            visual.reciprocal_rank,
        )
    )[selected]
    full_values = np.column_stack(
        (
            full.correct.astype(np.float64),
            full.official_ap,
            full.reciprocal_rank,
        )
    )[selected]
    return visual_values, full_values, full_values - visual_values


def paired_bootstrap_mean_ci(
    differences: np.ndarray,
    samples: int = DEFAULT_BOOTSTRAP_SAMPLES,
    seed: int = 20260730,
    confidence: float = 0.95,
) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(differences, dtype=np.float64)
    if values.ndim == 1:
        values = values[:, None]
    if (
        values.ndim != 2
        or values.shape[0] <= 0
        or values.shape[1] <= 0
        or not np.isfinite(values).all()
    ):
        raise QueryAnalysisError("Bootstrap differences must be a finite N x M matrix.")
    if samples <= 0 or not 0.0 < confidence < 1.0:
        raise QueryAnalysisError("Bootstrap samples/confidence are invalid.")
    rng = np.random.default_rng(seed)
    query_count, metric_count = values.shape
    draws = np.empty((samples, metric_count), dtype=np.float64)
    max_index_elements = 2_000_000
    batch_size = max(1, min(samples, max_index_elements // query_count))
    cursor = 0
    while cursor < samples:
        stop = min(cursor + batch_size, samples)
        indices = rng.integers(
            0,
            query_count,
            size=(stop - cursor, query_count),
            dtype=np.int64,
        )
        draws[cursor:stop] = values[indices].mean(axis=1, dtype=np.float64)
        cursor = stop
    alpha = (1.0 - confidence) / 2.0
    return (
        np.quantile(draws, alpha, axis=0),
        np.quantile(draws, 1.0 - alpha, axis=0),
    )


def _logsumexp(values: Sequence[float]) -> float:
    maximum = max(values)
    return maximum + math.log(sum(math.exp(value - maximum) for value in values))


def exact_two_sided_mcnemar_log10(
    first_only: int,
    second_only: int,
) -> float:
    if first_only < 0 or second_only < 0:
        raise QueryAnalysisError("McNemar discordant counts cannot be negative.")
    discordant = first_only + second_only
    if discordant == 0:
        return 0.0
    tail = min(first_only, second_only)
    log_terms = [
        math.lgamma(discordant + 1)
        - math.lgamma(index + 1)
        - math.lgamma(discordant - index + 1)
        - discordant * math.log(2.0)
        for index in range(tail + 1)
    ]
    log_p = math.log(2.0) + _logsumexp(log_terms)
    return min(0.0, log_p / math.log(10.0))


def probability_text(log10_probability: float) -> str:
    if not math.isfinite(log10_probability) or log10_probability > 1e-12:
        raise QueryAnalysisError("A log10 probability is invalid.")
    if log10_probability >= -300:
        value = 10.0**log10_probability
        return f"{min(1.0, value):.12g}"
    exponent = math.floor(log10_probability)
    mantissa = 10.0 ** (log10_probability - exponent)
    return f"{mantissa:.8f}e{exponent:+d}"


def stratum_summary(
    visual: QueryArrays,
    full: QueryArrays,
    mask: np.ndarray,
    *,
    minimum_queries: int = DEFAULT_MINIMUM_STRATUM_QUERIES,
    bootstrap_samples: int = DEFAULT_BOOTSTRAP_SAMPLES,
    bootstrap_seed: int = 20260730,
) -> dict[str, Any]:
    visual, full = align_visual_full(visual, full)
    selected = np.asarray(mask, dtype=np.bool_)
    visual_values, full_values, differences = _paired_metric_matrix(
        visual,
        full,
        selected,
    )
    count = int(selected.sum())
    claim_eligible = count >= minimum_queries
    if claim_eligible:
        lower, upper = paired_bootstrap_mean_ci(
            differences,
            samples=bootstrap_samples,
            seed=bootstrap_seed,
        )
    else:
        lower = np.full(len(STRATUM_METRICS), np.nan, dtype=np.float64)
        upper = np.full(len(STRATUM_METRICS), np.nan, dtype=np.float64)
    visual_only = int(
        np.sum(visual.correct[selected] & ~full.correct[selected])
    )
    full_only = int(
        np.sum(~visual.correct[selected] & full.correct[selected])
    )
    log10_p = (
        exact_two_sided_mcnemar_log10(visual_only, full_only)
        if claim_eligible
        else None
    )
    metrics: dict[str, Any] = {}
    for index, name in enumerate(STRATUM_METRICS):
        metrics[name] = {
            "visual": float(visual_values[:, index].mean(dtype=np.float64)),
            "full": float(full_values[:, index].mean(dtype=np.float64)),
            "full_minus_visual": float(
                differences[:, index].mean(dtype=np.float64)
            ),
            "paired_bootstrap_95ci": (
                [float(lower[index]), float(upper[index])]
                if claim_eligible
                else None
            ),
        }
    result = {
        "queries": count,
        "minimum_queries_for_claim": int(minimum_queries),
        "performance_claim_eligible": bool(claim_eligible),
        "metrics": metrics,
        "top1_discordance": {
            "visual_only_correct": visual_only,
            "full_only_correct": full_only,
            "exact_two_sided_mcnemar_log10_p": log10_p,
            "exact_two_sided_mcnemar_p": (
                probability_text(log10_p) if log10_p is not None else None
            ),
        },
    }
    if not claim_eligible:
        result["warning"] = (
            "descriptive values retained below the registered 100-query "
            "claim threshold; confidence interval and hypothesis test withheld"
        )
    return result


def calibration_confidence_from_margin(margin: np.ndarray) -> np.ndarray:
    values = np.asarray(margin, dtype=np.float64)
    if values.ndim != 1 or values.size <= 0 or not np.isfinite(values).all():
        raise QueryAnalysisError("Calibration margins must be a finite vector.")
    if (values < -2e-6).any():
        raise QueryAnalysisError("Calibration margins cannot be materially negative.")
    # Cosine similarities lie in [-1, 1], so their Top-1 minus Top-2 margin
    # has the fixed theoretical range [0, 2]. No test-set parameter is fitted.
    return np.clip(values / 2.0, 0.0, 1.0)


def calibration_summary(
    margin: np.ndarray,
    correct: np.ndarray,
    bins: int = DEFAULT_ECE_BINS,
) -> dict[str, Any]:
    confidence = calibration_confidence_from_margin(margin)
    outcomes = np.asarray(correct, dtype=np.bool_)
    if outcomes.shape != confidence.shape or bins <= 0:
        raise QueryAnalysisError("Calibration outcomes/bins are invalid.")
    indices = np.minimum((confidence * bins).astype(np.int64), bins - 1)
    rows = []
    ece = 0.0
    for index in range(bins):
        mask = indices == index
        count = int(mask.sum())
        lower = index / bins
        upper = (index + 1) / bins
        if count:
            accuracy = float(outcomes[mask].mean())
            mean_confidence = float(confidence[mask].mean())
            contribution = count / len(outcomes) * abs(
                accuracy - mean_confidence
            )
            ece += contribution
        else:
            accuracy = None
            mean_confidence = None
            contribution = 0.0
        rows.append(
            {
                "bin": index + 1,
                "lower_inclusive": lower,
                "upper_inclusive_only_for_last_bin": upper,
                "count": count,
                "accuracy": accuracy,
                "mean_fixed_normalized_margin_confidence": mean_confidence,
                "weighted_absolute_gap": contribution,
            }
        )
    return {
        "confidence_definition": "clip(cosine_top1_minus_top2_margin / 2, 0, 1)",
        "fitted_calibration_parameter": False,
        "bins": bins,
        "ECE": float(ece),
        "reliability_bins": rows,
    }


def _coverage_count(query_count: int, requested: float) -> int:
    if query_count <= 0 or not 0.0 < requested <= 1.0:
        raise QueryAnalysisError("Coverage count inputs are invalid.")
    return min(query_count, max(1, int(math.ceil(requested * query_count))))


def native_risk_coverage(
    margin: np.ndarray,
    correct: np.ndarray,
    coverages: Sequence[float] = RISK_COVERAGES,
) -> dict[str, Any]:
    confidence = np.asarray(margin, dtype=np.float64)
    outcomes = np.asarray(correct, dtype=np.bool_)
    if (
        confidence.ndim != 1
        or confidence.size <= 0
        or outcomes.shape != confidence.shape
        or not np.isfinite(confidence).all()
    ):
        raise QueryAnalysisError("Risk--coverage inputs are invalid.")
    order = np.argsort(-confidence, kind="stable")
    ordered_correct = outcomes[order]
    cumulative_risk = np.cumsum(~ordered_correct, dtype=np.float64) / np.arange(
        1,
        len(outcomes) + 1,
        dtype=np.float64,
    )
    rows = []
    for requested in coverages:
        count = _coverage_count(len(outcomes), float(requested))
        selected = order[:count]
        selective_r1 = float(outcomes[selected].mean())
        rows.append(
            {
                "requested_coverage": float(requested),
                "selected_queries": count,
                "realized_coverage": count / len(outcomes),
                "selective_r_at_1": selective_r1,
                "selective_risk": 1.0 - selective_r1,
                "selection_index_membership_sha256": canonical_sha256(
                    sorted(int(index) for index in selected.tolist())
                ),
            }
        )
    return {
        "ranking": "descending raw cosine Top-1 margin with stable query-order ties",
        "queries": int(len(outcomes)),
        "AURC_discrete_all_prefixes": float(cumulative_risk.mean()),
        "rows": rows,
    }


def paired_coverage_comparison(
    visual: QueryArrays,
    full: QueryArrays,
    requested_coverage: float,
) -> dict[str, Any]:
    visual, full = align_visual_full(visual, full)
    count = _coverage_count(visual.size, requested_coverage)
    visual_order = np.argsort(-visual.margin, kind="stable")
    full_order = np.argsort(-full.margin, kind="stable")
    visual_selected = np.zeros(visual.size, dtype=np.bool_)
    full_selected = np.zeros(full.size, dtype=np.bool_)
    visual_selected[visual_order[:count]] = True
    full_selected[full_order[:count]] = True
    visual_utility = visual_selected & visual.correct
    full_utility = full_selected & full.correct
    visual_only = int(np.sum(visual_utility & ~full_utility))
    full_only = int(np.sum(~visual_utility & full_utility))
    log10_p = exact_two_sided_mcnemar_log10(visual_only, full_only)
    visual_selective = float(visual.correct[visual_selected].mean())
    full_selective = float(full.correct[full_selected].mean())
    return {
        "requested_coverage": float(requested_coverage),
        "selected_queries_per_variant": count,
        "realized_coverage": count / visual.size,
        "visual_selective_r_at_1": visual_selective,
        "full_selective_r_at_1": full_selective,
        "full_minus_visual_selective_r_at_1": (
            full_selective - visual_selective
        ),
        "visual_full_selected_query_overlap": int(
            np.sum(visual_selected & full_selected)
        ),
        "coverage_constrained_success": {
            "definition": "selected AND top1-correct over the common full query set",
            "visual_rate": float(visual_utility.mean()),
            "full_rate": float(full_utility.mean()),
            "full_minus_visual_rate": float(
                full_utility.mean() - visual_utility.mean()
            ),
            "visual_only_success": visual_only,
            "full_only_success": full_only,
            "exact_two_sided_mcnemar_log10_p": log10_p,
            "exact_two_sided_mcnemar_p": probability_text(log10_p),
        },
    }


def apply_holm_logspace(
    rows: list[dict[str, Any]],
    *,
    log10_key: str,
    family_name: str,
) -> None:
    if not rows:
        raise QueryAnalysisError("Holm correction requires a non-empty family.")
    indexed = []
    for index, row in enumerate(rows):
        value = float(row[log10_key])
        if not math.isfinite(value) or value > 1e-12:
            raise QueryAnalysisError("Holm family contains an invalid probability.")
        indexed.append((value, index))
    indexed.sort(key=lambda item: item[0])
    family_size = len(rows)
    running = -math.inf
    for rank, (raw_log10, index) in enumerate(indexed):
        multiplier = family_size - rank
        candidate = min(0.0, raw_log10 + math.log10(multiplier))
        running = max(running, candidate)
        rows[index]["holm_adjusted_log10_p"] = running
        rows[index]["holm_adjusted_p"] = probability_text(running)
        rows[index]["holm_family"] = family_name
        rows[index]["holm_family_size"] = family_size
        rows[index]["reject_holm_0_05"] = bool(running < math.log10(0.05))
