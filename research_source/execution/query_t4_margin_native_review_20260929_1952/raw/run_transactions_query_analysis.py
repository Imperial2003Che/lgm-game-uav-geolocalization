#!/usr/bin/env python3
"""Run the registered T4 strata and T5 selective/calibration analyses."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Mapping, Sequence

import numpy as np

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DELIVERY_ROOT_DEFAULT = PACKAGE_ROOT.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from experiments import aggregate_frozen_formal_results as aggregate
from experiments.transactions_query_analysis import (
    DEFAULT_BOOTSTRAP_SAMPLES,
    DEFAULT_ECE_BINS,
    DEFAULT_MINIMUM_STRATUM_QUERIES,
    QUARTILE_LABELS,
    SELECTIVE_COVERAGES,
    QueryAnalysisError,
    QueryArrays,
    align_visual_full,
    apply_holm_logspace,
    calibration_summary,
    canonical_query_path,
    canonical_sha256,
    load_query_arrays,
    native_risk_coverage,
    normalized_entropy,
    paired_coverage_comparison,
    quartile_assignment,
    semantic_nearest_labels,
    stratum_summary,
)
from lgm_game_pytorch import formal_retrieval as core


CONFIG_SCHEMA = "lgm-game.transactions-query-analysis-config.v1"
T4_SCHEMA = "lgm-game.transactions-t4-strata.v1"
T5_SCHEMA = "lgm-game.transactions-t5-selective-calibration.v1"
MANIFEST_SCHEMA = "lgm-game.transactions-query-analysis-manifest.v1"
STATUS_SCHEMA = "lgm-game.transactions-query-analysis-status.v1"
EXPECTED_CORE_SHA256 = (
    "081f327f8f83d79ab078adc61e76070c140f13e0ac9a0d8f423bfad15df59862"
)
EXPECTED_SOURCE_RUNS = 12
EXPECTED_TASK_SEED_PAIRS = 33
EXPECTED_T4_ROWS = EXPECTED_TASK_SEED_PAIRS * 14
EXPECTED_T5_NATIVE_ROWS = EXPECTED_TASK_SEED_PAIRS * 2
EXPECTED_T5_COMPARISONS = EXPECTED_TASK_SEED_PAIRS * len(SELECTIVE_COVERAGES)


class QueryRunnerIntegrityError(RuntimeError):
    """The complete-matrix query-analysis evidence contract was violated."""


@dataclass(frozen=True)
class TaskEvidence:
    dataset: str
    task: str
    query_paths: np.ndarray
    query_labels: np.ndarray
    content_entropy: np.ndarray
    style_entropy: np.ndarray
    semantic_nearest_labels: np.ndarray
    protocol: str
    gallery_images: int
    protocol_membership_sha256: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def atomic_json(path: Path, payload: Any) -> None:
    serialized = canonical_bytes(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    if temporary.exists():
        raise QueryRunnerIntegrityError(f"Stale temporary file exists: {temporary}")
    temporary.write_bytes(serialized)
    temporary.replace(path)


def immutable_json(path: Path, payload: Any) -> str:
    serialized = canonical_bytes(payload)
    digest = hashlib.sha256(serialized).hexdigest()
    if path.exists():
        if path.read_bytes() != serialized:
            raise QueryRunnerIntegrityError(f"Immutable artifact differs: {path}")
        return digest
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(serialized)
    return digest


def registered_specs(delivery_root: Path) -> list[aggregate.RunSpec]:
    specs = [
        spec
        for spec in aggregate.expected_specs(delivery_root)
        if spec.family == "formal_main"
        and spec.variant in {"visual", "full"}
        and spec.seed in {1, 2, 3}
    ]
    observed = [
        (spec.dataset, spec.variant, spec.seed)
        for spec in specs
    ]
    expected = [
        (dataset, variant, seed)
        for dataset in aggregate.DATASET_ORDER
        for variant in ("visual", "full")
        for seed in aggregate.MAIN_SEEDS
    ]
    if observed != expected or len(specs) != EXPECTED_SOURCE_RUNS:
        raise QueryRunnerIntegrityError(
            "T4/T5 source registry is not the exact 2 x 2 x 3 matrix."
        )
    return specs


def validate_source_runs(
    delivery_root: Path,
) -> tuple[list[aggregate.ValidRun], str]:
    formal_path = (
        delivery_root
        / "lgm_game_pytorch"
        / "lgm_game_pytorch"
        / "formal_retrieval.py"
    ).resolve(strict=True)
    formal_sha = sha256_file(formal_path)
    if formal_sha != EXPECTED_CORE_SHA256:
        raise QueryRunnerIntegrityError("Frozen formal core hash changed.")
    valid = []
    incomplete = {}
    for spec in registered_specs(delivery_root):
        try:
            valid.append(
                aggregate.validate_completed_run(
                    spec,
                    delivery_root,
                    formal_sha,
                )
            )
        except (aggregate.IntegrityError, OSError, ValueError) as error:
            incomplete[spec.identifier] = str(error)
    if incomplete:
        examples = list(incomplete.items())[:3]
        raise QueryRunnerIntegrityError(
            "T4/T5 requires all 12 visual/full primary runs and evaluations; "
            f"{len(incomplete)} are incomplete or invalid. Examples: {examples}"
        )
    return valid, formal_sha


def _dataset_paths(
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
    manifest = (
        delivery
        / "lgm_game_pytorch"
        / "manifests"
        / "sues200_official_train_ids.yaml"
    ).resolve(strict=True)
    return (
        args.sues_root.resolve(strict=True),
        (
            delivery
            / "lgm_game_pytorch"
            / "evidence_cache"
            / "sues200_clip_image_evidence.npz"
        ).resolve(strict=True),
        manifest,
    )


def build_task_evidence(
    args: argparse.Namespace,
    dataset: str,
) -> tuple[dict[str, TaskEvidence], dict[str, Any]]:
    data_root, evidence_path, sues_manifest = _dataset_paths(args, dataset)
    store = core.EvidenceStore.load([evidence_path])
    records = core.derive_all_records(store, data_root, dataset)
    train_ids, manifest_info = core.parse_sues_manifest(sues_manifest)
    tasks = core.build_official_evaluation_tasks(records, dataset, train_ids)
    expected_tasks = aggregate.TASKS[dataset]
    if tuple(task.name for task in tasks) != expected_tasks:
        raise QueryRunnerIntegrityError(
            f"{dataset} official T4/T5 task set changed."
        )
    contexts = {}
    for task in tasks:
        query_indices = np.asarray(
            [record.evidence_index for record in task.query],
            dtype=np.int64,
        )
        gallery_indices = np.asarray(
            [record.evidence_index for record in task.gallery],
            dtype=np.int64,
        )
        query_paths = np.asarray(
            [canonical_query_path(record.relative_path) for record in task.query],
            dtype=str,
        )
        query_labels = np.asarray(
            [str(record.label) for record in task.query],
            dtype=str,
        )
        semantic_labels = semantic_nearest_labels(
            store.content_probs[query_indices],
            store.style_probs[query_indices],
            store.content_probs[gallery_indices],
            store.style_probs[gallery_indices],
            [record.label for record in task.gallery],
        )
        contexts[task.name] = TaskEvidence(
            dataset=dataset,
            task=task.name,
            query_paths=query_paths,
            query_labels=query_labels,
            content_entropy=normalized_entropy(
                store.content_probs[query_indices]
            ),
            style_entropy=normalized_entropy(store.style_probs[query_indices]),
            semantic_nearest_labels=semantic_labels,
            protocol=task.protocol,
            gallery_images=len(task.gallery),
            protocol_membership_sha256=core.protocol_membership_hash([task]),
        )
    descriptor = {
        "dataset": dataset,
        "data_root": str(data_root),
        "evidence_path": str(evidence_path),
        "evidence_bytes": evidence_path.stat().st_size,
        "evidence_sha256": sha256_file(evidence_path),
        "evidence_meta_path": store.cache_descriptors[0].meta_path,
        "evidence_meta_sha256": store.cache_descriptors[0].meta_sha256,
        "sues_manifest": manifest_info if dataset == "sues200" else None,
        "task_names": list(expected_tasks),
        "task_protocol_membership": {
            task: contexts[task].protocol_membership_sha256
            for task in expected_tasks
        },
    }
    return contexts, descriptor


def _load_aligned_pair(
    visual_run: aggregate.ValidRun,
    full_run: aggregate.ValidRun,
    task: str,
    evidence: TaskEvidence,
) -> tuple[QueryArrays, QueryArrays, dict[str, np.ndarray]]:
    visual = load_query_arrays(visual_run.arrays[task].path)
    full = load_query_arrays(full_run.arrays[task].path)
    visual, full = align_visual_full(visual, full)
    evidence_lookup = {
        path: index for index, path in enumerate(evidence.query_paths.tolist())
    }
    if set(visual.paths.tolist()) != set(evidence_lookup):
        raise QueryRunnerIntegrityError(
            f"{task}: retained query paths differ from the official task."
        )
    order = np.asarray(
        [evidence_lookup[path] for path in visual.paths],
        dtype=np.int64,
    )
    official_labels = evidence.query_labels[order]
    if not np.array_equal(visual.labels, official_labels):
        raise QueryRunnerIntegrityError(
            f"{task}: retained query labels differ from path-derived labels."
        )
    aligned_evidence = {
        "content_entropy": evidence.content_entropy[order],
        "style_entropy": evidence.style_entropy[order],
        "semantic_nearest_labels": evidence.semantic_nearest_labels[order],
    }
    return visual, full, aligned_evidence


def _bootstrap_seed(
    base: int,
    dataset: str,
    task: str,
    seed: int,
    factor: str,
    level: str,
) -> int:
    payload = f"{base}|{dataset}|{task}|{seed}|{factor}|{level}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % (
        2**32
    )


def _empty_stratum(
    minimum_queries: int,
) -> dict[str, Any]:
    return {
        "queries": 0,
        "minimum_queries_for_claim": minimum_queries,
        "performance_claim_eligible": False,
        "metrics": None,
        "top1_discordance": None,
        "warning": "empty stratum retained; no metric or inference computed",
    }


def _strata_for_pair(
    dataset: str,
    task: str,
    seed: int,
    visual: QueryArrays,
    full: QueryArrays,
    evidence: Mapping[str, np.ndarray],
    bootstrap_samples: int,
    bootstrap_seed: int,
    minimum_queries: int,
) -> list[dict[str, Any]]:
    factor_rows: list[tuple[str, str, np.ndarray, dict[str, Any]]] = []
    for factor, values in (
        ("content_entropy_quartile", evidence["content_entropy"]),
        ("style_entropy_quartile", evidence["style_entropy"]),
        ("visual_margin_quartile", visual.margin),
    ):
        assignments, cuts = quartile_assignment(values)
        for index, level in enumerate(QUARTILE_LABELS):
            factor_rows.append(
                (
                    factor,
                    level,
                    assignments == index,
                    {
                        "quartile_cutpoints": cuts.tolist(),
                        "boundary_rule": (
                            "linear quantiles; values equal to a cutpoint enter "
                            "the lower interval"
                        ),
                    },
                )
            )
    agreement = (
        visual.top1_gallery_labels == evidence["semantic_nearest_labels"]
    )
    factor_rows.extend(
        (
            (
                "visual_semantic_top1_identity_agreement",
                "agree",
                agreement,
                {
                    "semantic_neighbour": (
                        "cosine nearest neighbour of equal-weight L2-normalized "
                        "content/style probability blocks"
                    )
                },
            ),
            (
                "visual_semantic_top1_identity_agreement",
                "disagree",
                ~agreement,
                {
                    "semantic_neighbour": (
                        "cosine nearest neighbour of equal-weight L2-normalized "
                        "content/style probability blocks"
                    )
                },
            ),
        )
    )
    rows = []
    for factor, level, mask, metadata in factor_rows:
        count = int(np.sum(mask))
        if count:
            summary = stratum_summary(
                visual,
                full,
                mask,
                minimum_queries=minimum_queries,
                bootstrap_samples=bootstrap_samples,
                bootstrap_seed=_bootstrap_seed(
                    bootstrap_seed,
                    dataset,
                    task,
                    seed,
                    factor,
                    level,
                ),
            )
        else:
            summary = _empty_stratum(minimum_queries)
        selected_paths = sorted(visual.paths[np.asarray(mask, dtype=bool)].tolist())
        rows.append(
            {
                "dataset": dataset,
                "task": task,
                "seed": seed,
                "factor": factor,
                "level": level,
                "membership_sha256": canonical_sha256(selected_paths),
                "metadata": metadata,
                "summary": summary,
            }
        )
    if len(rows) != 14:
        raise QueryRunnerIntegrityError("T4 factor expansion is not exactly 14 rows.")
    return rows


def _native_t5_row(
    dataset: str,
    task: str,
    seed: int,
    variant: str,
    arrays: QueryArrays,
) -> dict[str, Any]:
    return {
        "dataset": dataset,
        "task": task,
        "seed": seed,
        "variant": variant,
        "query_membership_sha256": canonical_sha256(
            sorted(
                zip(
                    arrays.paths.tolist(),
                    arrays.labels.tolist(),
                    strict=True,
                )
            )
        ),
        "risk_coverage": native_risk_coverage(
            arrays.margin,
            arrays.correct,
        ),
        "calibration": calibration_summary(
            arrays.margin,
            arrays.correct,
            bins=DEFAULT_ECE_BINS,
        ),
    }


def _input_artifacts(
    delivery: Path,
    valid_runs: Sequence[aggregate.ValidRun],
) -> list[dict[str, Any]]:
    rows = []
    seen = set()
    for run in valid_runs:
        for task, descriptor in run.arrays.items():
            path = descriptor.path.resolve(strict=True)
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "role": "primary_per_query_arrays",
                    "dataset": run.spec.dataset,
                    "variant": run.spec.variant,
                    "seed": run.spec.seed,
                    "task": task,
                    "path": str(path),
                    "relative_path": path.relative_to(delivery).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": descriptor.sha256,
                    "query_membership_sha256": (
                        descriptor.query_membership_sha256
                    ),
                }
            )
    return sorted(
        rows,
        key=lambda row: (
            row["dataset"],
            row["variant"],
            row["seed"],
            row["task"],
        ),
    )


def build_config(
    args: argparse.Namespace,
    valid_runs: Sequence[aggregate.ValidRun],
    formal_sha: str,
    evidence_descriptors: Mapping[str, Any],
) -> dict[str, Any]:
    delivery = args.delivery_root.resolve(strict=True)
    protocol = (delivery / "TRANSACTIONS_EXTENSION_PROTOCOL.md").resolve(
        strict=True
    )
    return {
        "schema_version": CONFIG_SCHEMA,
        "registered_source_run_count": len(valid_runs),
        "registered_task_seed_pair_count": EXPECTED_TASK_SEED_PAIRS,
        "registered_t4_row_count": EXPECTED_T4_ROWS,
        "registered_t5_native_row_count": EXPECTED_T5_NATIVE_ROWS,
        "registered_t5_comparison_count": EXPECTED_T5_COMPARISONS,
        "bootstrap": {
            "samples": args.bootstrap_samples,
            "seed": args.bootstrap_seed,
            "confidence": 0.95,
            "unit": "paired official query",
        },
        "minimum_stratum_queries_for_claim": args.minimum_stratum_queries,
        "calibration": {
            "bins": DEFAULT_ECE_BINS,
            "confidence": (
                "clip(cosine_top1_minus_top2_margin / 2, 0, 1)"
            ),
            "fitted_parameter": False,
        },
        "selective_retrieval": {
            "confidence_order": "descending raw cosine Top-1 margin",
            "tie_break": "stable official query order",
            "paired_test_outcome": (
                "selected AND top1-correct over the common full query set"
            ),
        },
        "formal_core_sha256": formal_sha,
        "analysis_code_path": str(Path(__file__).resolve()),
        "analysis_code_sha256": sha256_file(Path(__file__).resolve()),
        "primitive_code_path": str(
            (
                Path(__file__).resolve().parent
                / "transactions_query_analysis.py"
            ).resolve()
        ),
        "primitive_code_sha256": sha256_file(
            Path(__file__).resolve().parent / "transactions_query_analysis.py"
        ),
        "protocol_path": str(protocol),
        "protocol_sha256": sha256_file(protocol),
        "evidence": dict(evidence_descriptors),
        "input_artifacts": _input_artifacts(delivery, valid_runs),
    }


def run_analysis(args: argparse.Namespace) -> dict[str, Any]:
    if args.bootstrap_samples != DEFAULT_BOOTSTRAP_SAMPLES:
        raise QueryRunnerIntegrityError(
            f"T4/T5 requires exactly {DEFAULT_BOOTSTRAP_SAMPLES} bootstrap samples."
        )
    if args.minimum_stratum_queries != DEFAULT_MINIMUM_STRATUM_QUERIES:
        raise QueryRunnerIntegrityError(
            "T4 minimum stratum size is frozen at 100 official queries."
        )
    delivery = args.delivery_root.resolve(strict=True)
    valid_runs, formal_sha = validate_source_runs(delivery)
    run_index = {
        (run.spec.dataset, run.spec.variant, run.spec.seed): run
        for run in valid_runs
    }
    contexts = {}
    evidence_descriptors = {}
    for dataset in aggregate.DATASET_ORDER:
        dataset_contexts, descriptor = build_task_evidence(args, dataset)
        contexts.update(
            {(dataset, task): row for task, row in dataset_contexts.items()}
        )
        evidence_descriptors[dataset] = descriptor
    config = build_config(args, valid_runs, formal_sha, evidence_descriptors)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    config_path = output / "transactions_query_analysis_config.json"
    config_sha = immutable_json(config_path, config)
    manifest_path = output / "transactions_query_analysis_manifest.json"
    if manifest_path.exists():
        raise QueryRunnerIntegrityError(
            "A completed T4/T5 manifest already exists; validate it instead of "
            "overwriting the registered result."
        )
    retained = [path for path in output.iterdir() if path != config_path]
    if retained:
        raise QueryRunnerIntegrityError(
            "T4/T5 output retains an incomplete attempt; archive it before an "
            f"explicit restart: {[path.name for path in retained]}"
        )
    status_path = output / "transactions_query_analysis_status.json"
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
        t4_rows = []
        t5_native = []
        t5_comparisons = []
        for dataset in aggregate.DATASET_ORDER:
            for task in aggregate.TASKS[dataset]:
                context = contexts[(dataset, task)]
                for seed in aggregate.MAIN_SEEDS:
                    visual_run = run_index[(dataset, "visual", seed)]
                    full_run = run_index[(dataset, "full", seed)]
                    visual, full, aligned_evidence = _load_aligned_pair(
                        visual_run,
                        full_run,
                        task,
                        context,
                    )
                    t4_rows.extend(
                        _strata_for_pair(
                            dataset,
                            task,
                            seed,
                            visual,
                            full,
                            aligned_evidence,
                            args.bootstrap_samples,
                            args.bootstrap_seed,
                            args.minimum_stratum_queries,
                        )
                    )
                    t5_native.extend(
                        (
                            _native_t5_row(
                                dataset,
                                task,
                                seed,
                                "visual",
                                visual,
                            ),
                            _native_t5_row(
                                dataset,
                                task,
                                seed,
                                "full",
                                full,
                            ),
                        )
                    )
                    for coverage in SELECTIVE_COVERAGES:
                        comparison = paired_coverage_comparison(
                            visual,
                            full,
                            coverage,
                        )
                        comparison.update(
                            {
                                "dataset": dataset,
                                "task": task,
                                "seed": seed,
                            }
                        )
                        t5_comparisons.append(comparison)
        if (
            len(t4_rows) != EXPECTED_T4_ROWS
            or len(t5_native) != EXPECTED_T5_NATIVE_ROWS
            or len(t5_comparisons) != EXPECTED_T5_COMPARISONS
        ):
            raise QueryRunnerIntegrityError(
                "T4/T5 output row coverage differs from the registered matrix."
            )

        t4_inference = []
        for row in t4_rows:
            summary = row["summary"]
            discordance = summary.get("top1_discordance")
            if summary["performance_claim_eligible"] and discordance is not None:
                proxy = {
                    "raw_log10_p": discordance[
                        "exact_two_sided_mcnemar_log10_p"
                    ],
                    "row": row,
                }
                t4_inference.append(proxy)
            elif discordance is not None:
                discordance["holm_status"] = (
                    "withheld_below_100_query_claim_threshold"
                )
        apply_holm_logspace(
            t4_inference,
            log10_key="raw_log10_p",
            family_name="T4 eligible visual-versus-full stratum R@1 comparisons",
        )
        for proxy in t4_inference:
            discordance = proxy["row"]["summary"]["top1_discordance"]
            for name in (
                "holm_adjusted_log10_p",
                "holm_adjusted_p",
                "holm_family",
                "holm_family_size",
                "reject_holm_0_05",
            ):
                discordance[name] = proxy[name]
            discordance["holm_status"] = "complete"

        t5_inference = []
        for row in t5_comparisons:
            success = row["coverage_constrained_success"]
            proxy = {
                "raw_log10_p": success[
                    "exact_two_sided_mcnemar_log10_p"
                ],
                "row": row,
            }
            t5_inference.append(proxy)
        apply_holm_logspace(
            t5_inference,
            log10_key="raw_log10_p",
            family_name="T5 coverage-constrained visual-versus-full comparisons",
        )
        for proxy in t5_inference:
            success = proxy["row"]["coverage_constrained_success"]
            for name in (
                "holm_adjusted_log10_p",
                "holm_adjusted_p",
                "holm_family",
                "holm_family_size",
                "reject_holm_0_05",
            ):
                success[name] = proxy[name]
            success["holm_status"] = "complete"

        t4_payload = {
            "schema_version": T4_SCHEMA,
            "status": "completed",
            "unit": "fraction",
            "source_config_sha256": config_sha,
            "registered_row_count": EXPECTED_T4_ROWS,
            "observed_row_count": len(t4_rows),
            "minimum_queries_for_performance_claim": (
                args.minimum_stratum_queries
            ),
            "bootstrap_samples": args.bootstrap_samples,
            "rows": t4_rows,
        }
        t4_payload["payload_sha256"] = canonical_sha256(t4_payload)
        t5_payload = {
            "schema_version": T5_SCHEMA,
            "status": "completed",
            "unit": "fraction",
            "source_config_sha256": config_sha,
            "registered_native_row_count": EXPECTED_T5_NATIVE_ROWS,
            "registered_comparison_count": EXPECTED_T5_COMPARISONS,
            "native_rows": t5_native,
            "paired_comparisons": t5_comparisons,
        }
        t5_payload["payload_sha256"] = canonical_sha256(t5_payload)

        t4_path = output / "transactions_t4_strata.json"
        t5_path = output / "transactions_t5_selective_calibration.json"
        immutable_json(t4_path, t4_payload)
        immutable_json(t5_path, t5_payload)
        t4_csv = output / "transactions_t4_strata.csv"
        t5_csv = output / "transactions_t5_selective_comparisons.csv"
        write_t4_csv(t4_csv, t4_rows)
        write_t5_csv(t5_csv, t5_comparisons)
        manifest_payload = {
            "schema_version": MANIFEST_SCHEMA,
            "status": "completed",
            "manuscript_result": True,
            "config_path": str(config_path),
            "config_sha256": config_sha,
            "t4_path": str(t4_path.resolve()),
            "t4_sha256": sha256_file(t4_path),
            "t4_csv_path": str(t4_csv.resolve()),
            "t4_csv_sha256": sha256_file(t4_csv),
            "t5_path": str(t5_path.resolve()),
            "t5_sha256": sha256_file(t5_path),
            "t5_csv_path": str(t5_csv.resolve()),
            "t5_csv_sha256": sha256_file(t5_csv),
            "source_run_count": len(valid_runs),
            "t4_row_count": len(t4_rows),
            "t5_native_row_count": len(t5_native),
            "t5_comparison_count": len(t5_comparisons),
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
                "status": "completed",
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


def write_t4_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fields = (
        "dataset",
        "task",
        "seed",
        "factor",
        "level",
        "queries",
        "performance_claim_eligible",
        "visual_r_at_1",
        "full_r_at_1",
        "full_minus_visual_r_at_1",
        "visual_mAPtrap",
        "full_mAPtrap",
        "full_minus_visual_mAPtrap",
        "visual_MRR",
        "full_MRR",
        "full_minus_visual_MRR",
        "holm_adjusted_p",
        "membership_sha256",
    )
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            summary = row["summary"]
            metrics = summary.get("metrics") or {}
            discordance = summary.get("top1_discordance") or {}
            writer.writerow(
                {
                    "dataset": row["dataset"],
                    "task": row["task"],
                    "seed": row["seed"],
                    "factor": row["factor"],
                    "level": row["level"],
                    "queries": summary["queries"],
                    "performance_claim_eligible": summary[
                        "performance_claim_eligible"
                    ],
                    "visual_r_at_1": (
                        metrics.get("r_at_1", {}).get("visual", "")
                    ),
                    "full_r_at_1": metrics.get("r_at_1", {}).get("full", ""),
                    "full_minus_visual_r_at_1": (
                        metrics.get("r_at_1", {}).get(
                            "full_minus_visual",
                            "",
                        )
                    ),
                    "visual_mAPtrap": (
                        metrics.get("official_trapezoid_mAP", {}).get(
                            "visual",
                            "",
                        )
                    ),
                    "full_mAPtrap": (
                        metrics.get("official_trapezoid_mAP", {}).get(
                            "full",
                            "",
                        )
                    ),
                    "full_minus_visual_mAPtrap": (
                        metrics.get("official_trapezoid_mAP", {}).get(
                            "full_minus_visual",
                            "",
                        )
                    ),
                    "visual_MRR": metrics.get("MRR", {}).get("visual", ""),
                    "full_MRR": metrics.get("MRR", {}).get("full", ""),
                    "full_minus_visual_MRR": (
                        metrics.get("MRR", {}).get("full_minus_visual", "")
                    ),
                    "holm_adjusted_p": discordance.get(
                        "holm_adjusted_p",
                        "",
                    ),
                    "membership_sha256": row["membership_sha256"],
                }
            )
    temporary.replace(path)


def write_t5_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fields = (
        "dataset",
        "task",
        "seed",
        "requested_coverage",
        "realized_coverage",
        "visual_selective_r_at_1",
        "full_selective_r_at_1",
        "full_minus_visual_selective_r_at_1",
        "visual_full_selected_query_overlap",
        "visual_coverage_constrained_success",
        "full_coverage_constrained_success",
        "full_minus_visual_coverage_constrained_success",
        "holm_adjusted_p",
    )
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            success = row["coverage_constrained_success"]
            writer.writerow(
                {
                    "dataset": row["dataset"],
                    "task": row["task"],
                    "seed": row["seed"],
                    "requested_coverage": row["requested_coverage"],
                    "realized_coverage": row["realized_coverage"],
                    "visual_selective_r_at_1": row[
                        "visual_selective_r_at_1"
                    ],
                    "full_selective_r_at_1": row[
                        "full_selective_r_at_1"
                    ],
                    "full_minus_visual_selective_r_at_1": row[
                        "full_minus_visual_selective_r_at_1"
                    ],
                    "visual_full_selected_query_overlap": row[
                        "visual_full_selected_query_overlap"
                    ],
                    "visual_coverage_constrained_success": success[
                        "visual_rate"
                    ],
                    "full_coverage_constrained_success": success[
                        "full_rate"
                    ],
                    "full_minus_visual_coverage_constrained_success": success[
                        "full_minus_visual_rate"
                    ],
                    "holm_adjusted_p": success["holm_adjusted_p"],
                }
            )
    temporary.replace(path)


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
    parser.add_argument(
        "--bootstrap-samples",
        type=int,
        default=DEFAULT_BOOTSTRAP_SAMPLES,
    )
    parser.add_argument("--bootstrap-seed", type=int, default=20260730)
    parser.add_argument(
        "--minimum-stratum-queries",
        type=int,
        default=DEFAULT_MINIMUM_STRATUM_QUERIES,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.output_dir is None:
        args.output_dir = (
            args.delivery_root
            / "lgm_game_pytorch"
            / "analysis"
            / "transactions_t4_t5"
        )
    if args.bootstrap_seed < 0:
        raise SystemExit("ERROR: --bootstrap-seed must be non-negative.")
    try:
        manifest = run_analysis(args)
    except (
        QueryRunnerIntegrityError,
        QueryAnalysisError,
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

