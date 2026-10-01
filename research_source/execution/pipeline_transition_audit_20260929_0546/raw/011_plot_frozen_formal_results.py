"""Create publication figures from a completed frozen formal aggregation.

The script is CPU-only and fail-closed.  It refuses partial aggregation
manifests, missing rows, unexpected task sets, stale source hashes, or
inconsistent three-seed summaries.  It never constructs placeholder values.
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

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


# Mandatory editable-text and journal export settings.
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = [
    "Arial",
    "DejaVu Sans",
    "Liberation Sans",
]
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["font.size"] = 7
plt.rcParams["axes.spines.right"] = False
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.linewidth"] = 0.8
plt.rcParams["legend.frameon"] = False
plt.rcParams["savefig.facecolor"] = "white"
plt.rcParams["figure.facecolor"] = "white"


SCHEMA_VERSION = "lgm-game.formal-figures.v1"
AGGREGATE_SCHEMA = "lgm-game.formal-aggregate.v1"
MAIN_SEEDS = (1, 2, 3)
VARIANTS = (
    "visual",
    "content",
    "style",
    "visual_content",
    "visual_style",
    "full",
)
SETTINGS = ("full", "backbone_resnet50", "embed_dim_256", "embed_dim_1024")
DATASETS = ("university1652", "sues200")
SUES_ALTITUDES = (150, 200, 250, 300)
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
EXPECTED_SUMMARY_ROWS = 66
EXPECTED_RAW_MAIN_ROWS = 198
EXPECTED_SENSITIVITY_ROWS = 33
EXPECTED_SENSITIVITY_WITH_REFERENCE_ROWS = 44
EXPECTED_PAIRWISE_ROWS = 33
BOOTSTRAP_SAMPLES = 10_000

REQUIRED_CSVS = (
    "main_metrics_by_seed.csv",
    "main_three_seed_mean_sample_sd.csv",
    "sensitivity_metrics.csv",
    "sensitivity_with_main_reference.csv",
    "visual_vs_full_paired_bootstrap.csv",
    "visual_vs_full_exact_mcnemar_holm.csv",
)

METRICS = (
    "r_at_1",
    "r_at_5",
    "r_at_10",
    "r_at_20",
    "official_trapezoid_mAP",
    "MRR",
)

VARIANT_LABELS = {
    "visual": "Visual",
    "content": "Content",
    "style": "Style",
    "visual_content": "Visual + content",
    "visual_style": "Visual + style",
    "full": "Full",
}

SETTING_LABELS = {
    "full": "ResNet-18, 512-D",
    "backbone_resnet50": "ResNet-50, 512-D",
    "embed_dim_256": "ResNet-18, 256-D",
    "embed_dim_1024": "ResNet-18, 1024-D",
}

VARIANT_COLORS = {
    "visual": "#484878",
    "content": "#A8A8C8",
    "style": "#C5CBE3",
    "visual_content": "#B8D8D8",
    "visual_style": "#E4CCD8",
    "full": "#0F4D92",
}

SETTING_COLORS = {
    "full": "#0F4D92",
    "backbone_resnet50": "#9A4D8E",
    "embed_dim_256": "#7884B4",
    "embed_dim_1024": "#42949E",
}

MARKERS = {
    "visual": "o",
    "content": "s",
    "style": "^",
    "visual_content": "D",
    "visual_style": "v",
    "full": "P",
}

COMPLEXITY_CANDIDATES = (
    ("parameters_m", "Parameters (million)", 1.0),
    ("parameter_count", "Parameters (million)", 1e-6),
    ("flops_g", "FLOPs (G)", 1.0),
    ("flops", "FLOPs (G)", 1e-9),
    ("peak_memory_mb", "Peak memory (MB)", 1.0),
    ("online_encoding_ms", "Online encoding (ms/image)", 1.0),
    ("online_encoding_time_ms", "Online encoding (ms/image)", 1.0),
    ("ranking_time_ms", "Ranking time (ms/query)", 1.0),
)


class FigureInputError(RuntimeError):
    """Completed aggregation data are malformed or inconsistent."""


class IncompleteAggregateError(RuntimeError):
    """The aggregate status is not complete."""


@dataclass(frozen=True)
class ComplexityMetric:
    column: str
    label: str
    scale: float


@dataclass
class AggregateData:
    aggregate_dir: Path
    manifest: dict[str, Any]
    manifest_sha256: str
    main_raw: list[dict[str, str]]
    main_summary: list[dict[str, str]]
    sensitivity: list[dict[str, str]]
    sensitivity_reference: list[dict[str, str]]
    bootstrap: list[dict[str, str]]
    mcnemar: list[dict[str, str]]
    csv_headers: dict[str, list[str]]
    csv_sha256: dict[str, str]
    complexity: ComplexityMetric | None


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


def write_csv(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    fields: Sequence[str] | None = None,
) -> None:
    if fields is None:
        fields = list(dict.fromkeys(key for row in rows for key in row))
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        field: "" if row.get(field) is None else row.get(field)
                        for field in fields
                    }
                )
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise FigureInputError(f"Cannot read valid JSON from {path}: {error}") from error
    if not isinstance(value, dict):
        raise FigureInputError(f"Expected a JSON object in {path}.")
    return value


def load_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise FigureInputError(f"{path} has no CSV header.")
            rows = [dict(row) for row in reader]
            return rows, list(reader.fieldnames)
    except OSError as error:
        raise FigureInputError(f"Cannot read CSV {path}: {error}") from error


def verify_payload_hash(payload: Mapping[str, Any], path: Path) -> None:
    declared = payload.get("payload_sha256")
    if not isinstance(declared, str):
        raise FigureInputError(f"{path} does not declare payload_sha256.")
    body = dict(payload)
    body.pop("payload_sha256", None)
    actual = canonical_sha256(body)
    if actual != declared:
        raise FigureInputError(
            f"Aggregate manifest payload hash mismatch: {actual} != {declared}."
        )


def finite_float(row: Mapping[str, str], field: str, context: str) -> float:
    value = row.get(field, "")
    if value is None or str(value).strip() == "":
        raise FigureInputError(f"{context} is missing numeric field {field}.")
    try:
        result = float(value)
    except ValueError as error:
        raise FigureInputError(
            f"{context} has non-numeric {field}={value!r}."
        ) from error
    if not math.isfinite(result):
        raise FigureInputError(f"{context} has non-finite {field}.")
    return result


def integer(row: Mapping[str, str], field: str, context: str) -> int:
    value = finite_float(row, field, context)
    result = int(value)
    if not math.isclose(value, result):
        raise FigureInputError(f"{context} has non-integer {field}={value}.")
    return result


def true_value(value: str) -> bool:
    return str(value).strip().casefold() in {"true", "1", "yes"}


def expected_main_keys() -> set[tuple[str, str, str, int]]:
    return {
        (dataset, task, variant, seed)
        for dataset in DATASETS
        for task in TASKS[dataset]
        for variant in VARIANTS
        for seed in MAIN_SEEDS
    }


def expected_summary_keys() -> set[tuple[str, str, str]]:
    return {
        (dataset, task, variant)
        for dataset in DATASETS
        for task in TASKS[dataset]
        for variant in VARIANTS
    }


def expected_sensitivity_keys() -> set[tuple[str, str, str]]:
    return {
        (dataset, task, setting)
        for dataset in DATASETS
        for task in TASKS[dataset]
        for setting in SETTINGS[1:]
    }


def expected_sensitivity_reference_keys() -> set[tuple[str, str, str]]:
    return {
        (dataset, task, setting)
        for dataset in DATASETS
        for task in TASKS[dataset]
        for setting in SETTINGS
    }


def expected_pairwise_keys() -> set[tuple[str, str, int]]:
    return {
        (dataset, task, seed)
        for dataset in DATASETS
        for task in TASKS[dataset]
        for seed in MAIN_SEEDS
    }


def require_exact_keys(
    actual: Iterable[tuple[Any, ...]],
    expected: set[tuple[Any, ...]],
    context: str,
) -> None:
    actual_list = list(actual)
    actual_set = set(actual_list)
    if len(actual_list) != len(actual_set):
        raise FigureInputError(f"{context} contains duplicate key rows.")
    if actual_set != expected:
        missing = sorted(expected - actual_set)[:5]
        extra = sorted(actual_set - expected)[:5]
        raise FigureInputError(
            f"{context} key set is incomplete or unexpected; missing={missing}, "
            f"extra={extra}."
        )


def validate_manifest(manifest: Mapping[str, Any], path: Path) -> None:
    verify_payload_hash(manifest, path)
    if manifest.get("schema_version") != AGGREGATE_SCHEMA:
        raise FigureInputError(
            f"Unsupported aggregate schema {manifest.get('schema_version')!r}."
        )
    if manifest.get("status") != "complete":
        raise IncompleteAggregateError(
            f"Aggregate status is {manifest.get('status')!r}; figures require "
            "status='complete'."
        )
    matrix = manifest.get("matrix")
    if not isinstance(matrix, dict):
        raise FigureInputError("Aggregate manifest has no matrix record.")
    expected_matrix = {
        "expected_main_runs": 36,
        "valid_main_runs": 36,
        "expected_sensitivity_runs": 6,
        "valid_sensitivity_runs": 6,
        "expected_pairwise_tests": 33,
        "completed_pairwise_tests": 33,
    }
    for key, expected in expected_matrix.items():
        if int(matrix.get(key, -1)) != expected:
            raise FigureInputError(
                f"Aggregate matrix {key}={matrix.get(key)!r}, expected {expected}."
            )
    policy = manifest.get("task_policy")
    if not isinstance(policy, dict):
        raise FigureInputError("Aggregate manifest has no task policy.")
    if policy.get("task_level_only") is not True:
        raise FigureInputError("Aggregate task-level-only policy is not asserted.")
    if policy.get("macro_average_rows_generated") is not False:
        raise FigureInputError("Macro-average rows are forbidden for formal figures.")
    if policy.get("overall_plus_subset_duplicate_average_generated") is not False:
        raise FigureInputError("Duplicate overall/subset averages are forbidden.")
    if tuple(policy.get("university1652_tasks", ())) != TASKS["university1652"]:
        raise FigureInputError("University-1652 task manifest is not the exact 3-task set.")
    if tuple(policy.get("sues200_tasks", ())) != TASKS["sues200"]:
        raise FigureInputError("SUES-200 task manifest is not the exact 8-task set.")
    statistics_record = manifest.get("statistics")
    if not isinstance(statistics_record, dict):
        raise FigureInputError("Aggregate manifest has no statistical-method record.")
    if int(statistics_record.get("paired_bootstrap_samples", -1)) != BOOTSTRAP_SAMPLES:
        raise FigureInputError("Aggregate bootstrap count is not the frozen 10,000.")


def verify_csv_artifacts(
    aggregate_dir: Path,
    manifest: Mapping[str, Any],
) -> tuple[dict[str, list[dict[str, str]]], dict[str, list[str]], dict[str, str]]:
    artifact_records = manifest.get("output_artifacts")
    if not isinstance(artifact_records, list):
        raise FigureInputError("Aggregate manifest has no output-artifact list.")
    artifact_index = {
        str(record.get("path")): record
        for record in artifact_records
        if isinstance(record, dict)
    }
    rows_by_name: dict[str, list[dict[str, str]]] = {}
    headers_by_name: dict[str, list[str]] = {}
    hashes: dict[str, str] = {}
    for name in REQUIRED_CSVS:
        path = aggregate_dir / name
        if not path.is_file():
            raise FigureInputError(f"Required complete aggregate CSV is missing: {path}")
        record = artifact_index.get(name)
        if not isinstance(record, dict) or not isinstance(record.get("sha256"), str):
            raise FigureInputError(f"Aggregate manifest does not hash {name}.")
        actual = sha256_file(path)
        if actual != record["sha256"]:
            raise FigureInputError(f"Aggregate CSV hash mismatch for {name}.")
        if int(record.get("bytes", -1)) != path.stat().st_size:
            raise FigureInputError(f"Aggregate CSV byte count mismatch for {name}.")
        rows, headers = load_csv(path)
        rows_by_name[name] = rows
        headers_by_name[name] = headers
        hashes[name] = actual
    return rows_by_name, headers_by_name, hashes


def validate_main_raw(rows: Sequence[Mapping[str, str]]) -> None:
    if len(rows) != EXPECTED_RAW_MAIN_ROWS:
        raise FigureInputError(
            f"main_metrics_by_seed.csv has {len(rows)} rows, expected 198."
        )
    keys = []
    for index, row in enumerate(rows):
        context = f"main raw row {index + 1}"
        dataset = row.get("dataset", "")
        task = row.get("task", "")
        variant = row.get("variant", "")
        seed = integer(row, "seed", context)
        keys.append((dataset, task, variant, seed))
        if dataset not in DATASETS or task not in TASKS.get(dataset, ()):
            raise FigureInputError(f"{context} has an unofficial task.")
        if variant not in VARIANTS or seed not in MAIN_SEEDS:
            raise FigureInputError(f"{context} has an unregistered variant/seed.")
        for metric in METRICS:
            value = finite_float(row, f"{metric}_pct", context)
            if value < 0.0 or value > 100.0:
                raise FigureInputError(f"{context} {metric} is outside [0, 100].")
        if integer(row, "queries", context) <= 0 or integer(row, "gallery", context) <= 0:
            raise FigureInputError(f"{context} has a non-positive task scale.")
    require_exact_keys(keys, expected_main_keys(), "main raw metrics")


def validate_summary(
    summary: Sequence[Mapping[str, str]],
    raw: Sequence[Mapping[str, str]],
) -> None:
    if len(summary) != EXPECTED_SUMMARY_ROWS:
        raise FigureInputError(
            f"main_three_seed_mean_sample_sd.csv has {len(summary)} rows, expected 66."
        )
    keys = [
        (row.get("dataset", ""), row.get("task", ""), row.get("variant", ""))
        for row in summary
    ]
    require_exact_keys(keys, expected_summary_keys(), "three-seed summary")
    raw_groups: dict[tuple[str, str, str], list[Mapping[str, str]]] = {}
    for row in raw:
        key = (row["dataset"], row["task"], row["variant"])
        raw_groups.setdefault(key, []).append(row)
    for row in summary:
        key = (row["dataset"], row["task"], row["variant"])
        context = f"summary {key}"
        if integer(row, "n_seeds", context) != 3:
            raise FigureInputError(f"{context} is not a three-seed summary.")
        if row.get("seeds") != "1|2|3" or not true_value(
            row.get("complete_seed_triplet", "")
        ):
            raise FigureInputError(f"{context} lacks the exact frozen seed triplet.")
        group = sorted(raw_groups[key], key=lambda item: int(item["seed"]))
        if [int(item["seed"]) for item in group] != [1, 2, 3]:
            raise FigureInputError(f"{context} raw seed membership differs.")
        if len({int(item["queries"]) for item in group}) != 1 or len(
            {int(item["gallery"]) for item in group}
        ) != 1:
            raise FigureInputError(f"{context} task scale differs across seeds.")
        for metric in METRICS:
            observations = [float(item[f"{metric}_pct"]) for item in group]
            expected_mean = statistics.fmean(observations)
            expected_sd = statistics.stdev(observations)
            actual_mean = finite_float(row, f"{metric}_mean_pct", context)
            actual_sd = finite_float(row, f"{metric}_sample_sd_pct", context)
            if not math.isclose(actual_mean, expected_mean, rel_tol=1e-10, abs_tol=1e-10):
                raise FigureInputError(f"{context} has inconsistent {metric} mean.")
            if not math.isclose(actual_sd, expected_sd, rel_tol=1e-10, abs_tol=1e-10):
                raise FigureInputError(f"{context} has inconsistent {metric} sample SD.")
            if actual_mean < 0.0 or actual_mean > 100.0 or actual_sd < 0.0:
                raise FigureInputError(f"{context} has invalid {metric} summary.")


def validate_sensitivity(
    rows: Sequence[Mapping[str, str]],
    reference: Sequence[Mapping[str, str]],
) -> None:
    if len(rows) != EXPECTED_SENSITIVITY_ROWS:
        raise FigureInputError(
            f"sensitivity_metrics.csv has {len(rows)} rows, expected 33."
        )
    keys = [
        (row.get("dataset", ""), row.get("task", ""), row.get("setting", ""))
        for row in rows
    ]
    require_exact_keys(keys, expected_sensitivity_keys(), "sensitivity metrics")
    if len(reference) != EXPECTED_SENSITIVITY_WITH_REFERENCE_ROWS:
        raise FigureInputError(
            "sensitivity_with_main_reference.csv has "
            f"{len(reference)} rows, expected 44."
        )
    ref_keys = [
        (row.get("dataset", ""), row.get("task", ""), row.get("setting", ""))
        for row in reference
    ]
    require_exact_keys(
        ref_keys,
        expected_sensitivity_reference_keys(),
        "sensitivity metrics with main reference",
    )
    sensitivity_lookup = {
        (row["dataset"], row["task"], row["setting"]): row for row in rows
    }
    for index, row in enumerate(reference):
        context = f"sensitivity reference row {index + 1}"
        setting = row["setting"]
        expected_role = (
            "main_full_seed1_reference"
            if setting == "full"
            else "frozen_sensitivity_run"
        )
        if row.get("sensitivity_role") != expected_role:
            raise FigureInputError(f"{context} has incorrect sensitivity role.")
        for metric in METRICS:
            value = finite_float(row, f"{metric}_pct", context)
            if value < 0.0 or value > 100.0:
                raise FigureInputError(f"{context} {metric} outside [0, 100].")
        if setting != "full":
            source = sensitivity_lookup[(row["dataset"], row["task"], setting)]
            for metric in METRICS:
                if not math.isclose(
                    float(row[f"{metric}_pct"]),
                    float(source[f"{metric}_pct"]),
                    rel_tol=0.0,
                    abs_tol=1e-12,
                ):
                    raise FigureInputError(
                        f"{context} differs from the frozen sensitivity source."
                    )


def validate_pairwise(
    bootstrap: Sequence[Mapping[str, str]],
    mcnemar: Sequence[Mapping[str, str]],
) -> None:
    if len(bootstrap) != EXPECTED_PAIRWISE_ROWS or len(mcnemar) != EXPECTED_PAIRWISE_ROWS:
        raise FigureInputError("Pairwise bootstrap/McNemar CSVs must each have 33 rows.")
    boot_keys = [
        (row.get("dataset", ""), row.get("task", ""), int(row.get("seed", -1)))
        for row in bootstrap
    ]
    test_keys = [
        (row.get("dataset", ""), row.get("task", ""), int(row.get("seed", -1)))
        for row in mcnemar
    ]
    expected = expected_pairwise_keys()
    require_exact_keys(boot_keys, expected, "paired bootstrap")
    require_exact_keys(test_keys, expected, "exact McNemar/Holm")
    for index, row in enumerate(bootstrap):
        context = f"bootstrap row {index + 1}"
        if integer(row, "bootstrap_samples", context) != BOOTSTRAP_SAMPLES:
            raise FigureInputError(f"{context} does not use 10,000 samples.")
        estimate = finite_float(row, "difference_r_at_1_pp", context)
        low = finite_float(row, "ci95_low_pp", context)
        high = finite_float(row, "ci95_high_pp", context)
        if low > high:
            raise FigureInputError(f"{context} has reversed confidence bounds.")
        if estimate < -100.0 or estimate > 100.0:
            raise FigureInputError(f"{context} has impossible R@1 difference.")
        if integer(row, "paired_queries", context) <= 0:
            raise FigureInputError(f"{context} has no paired queries.")
    for index, row in enumerate(mcnemar):
        context = f"McNemar row {index + 1}"
        if integer(row, "holm_family_size", context) != EXPECTED_PAIRWISE_ROWS:
            raise FigureInputError(f"{context} is not in the complete 33-test family.")
        if row.get("holm_status") != "complete":
            raise FigureInputError(f"{context} has incomplete Holm status.")
        for field in ("exact_mcnemar_p", "holm_adjusted_p"):
            text = row.get(field, "").strip()
            if not text or text in {"0", "0.0", "0e+0", "0e-0"}:
                raise FigureInputError(f"{context} reports forbidden p=0 in {field}.")
        finite_float(row, "exact_mcnemar_log10_p", context)
        finite_float(row, "holm_adjusted_log10_p", context)


def detect_complexity(
    rows: Sequence[Mapping[str, str]],
    headers: Sequence[str],
) -> ComplexityMetric | None:
    header_set = set(headers)
    for column, label, scale in COMPLEXITY_CANDIDATES:
        if column not in header_set:
            continue
        for index, row in enumerate(rows):
            value = finite_float(row, column, f"complexity row {index + 1}")
            if value < 0.0:
                raise FigureInputError(f"Complexity field {column} cannot be negative.")
        for dataset in DATASETS:
            for setting in SETTINGS:
                values = {
                    float(row[column])
                    for row in rows
                    if row["dataset"] == dataset and row["setting"] == setting
                }
                if len(values) != 1:
                    raise FigureInputError(
                        f"{column} must be setting-level and constant across tasks "
                        f"for {dataset}/{setting}."
                    )
        return ComplexityMetric(column, label, scale)
    return None


def load_completed_aggregate(aggregate_dir: Path) -> AggregateData:
    aggregate_dir = aggregate_dir.resolve(strict=True)
    manifest_path = aggregate_dir / "aggregate_manifest.json"
    if not manifest_path.is_file():
        raise IncompleteAggregateError(f"Missing aggregate manifest: {manifest_path}")
    manifest = load_json(manifest_path)
    validate_manifest(manifest, manifest_path)
    rows, headers, hashes = verify_csv_artifacts(aggregate_dir, manifest)
    main_raw = rows["main_metrics_by_seed.csv"]
    main_summary = rows["main_three_seed_mean_sample_sd.csv"]
    sensitivity = rows["sensitivity_metrics.csv"]
    sensitivity_reference = rows["sensitivity_with_main_reference.csv"]
    bootstrap = rows["visual_vs_full_paired_bootstrap.csv"]
    mcnemar = rows["visual_vs_full_exact_mcnemar_holm.csv"]
    validate_main_raw(main_raw)
    validate_summary(main_summary, main_raw)
    validate_sensitivity(sensitivity, sensitivity_reference)
    validate_pairwise(bootstrap, mcnemar)
    complexity = detect_complexity(
        sensitivity_reference,
        headers["sensitivity_with_main_reference.csv"],
    )
    return AggregateData(
        aggregate_dir=aggregate_dir,
        manifest=manifest,
        manifest_sha256=sha256_file(manifest_path),
        main_raw=main_raw,
        main_summary=main_summary,
        sensitivity=sensitivity,
        sensitivity_reference=sensitivity_reference,
        bootstrap=bootstrap,
        mcnemar=mcnemar,
        csv_headers=headers,
        csv_sha256=hashes,
        complexity=complexity,
    )


def short_task_label(task: str) -> str:
    labels = {
        "university1652_drone_to_satellite": "Drone → satellite",
        "university1652_satellite_to_drone": "Satellite → drone",
        "university1652_street_to_satellite": "Street → satellite",
    }
    if task in labels:
        return labels[task]
    match = re.fullmatch(r"sues200_uav_(\d+)m_to_satellite", task)
    if match:
        return f"UAV {match.group(1)} m → satellite"
    match = re.fullmatch(r"sues200_satellite_to_uav_(\d+)m", task)
    if match:
        return f"Satellite → UAV {match.group(1)} m"
    raise FigureInputError(f"Cannot label unofficial task {task!r}.")


def add_panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.08,
        1.03,
        label,
        transform=ax.transAxes,
        fontsize=8,
        fontweight="bold",
        ha="left",
        va="bottom",
    )


def source_record(path: Path, figure: str, rows: int) -> dict[str, Any]:
    return {
        "figure": figure,
        "role": "source_data",
        "path": path.name,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "rows": rows,
    }


def validate_export(path: Path) -> None:
    if not path.is_file() or path.stat().st_size < 500:
        raise FigureInputError(f"Figure export is missing or implausibly small: {path}")
    suffix = path.suffix.casefold()
    if suffix == ".pdf":
        with path.open("rb") as handle:
            if handle.read(4) != b"%PDF":
                raise FigureInputError(f"Invalid PDF header: {path}")
    elif suffix == ".svg":
        text = path.read_text(encoding="utf-8")
        if "<svg" not in text or "<text" not in text:
            raise FigureInputError(
                f"SVG lacks an SVG root or editable text nodes: {path}"
            )
    elif suffix == ".png":
        image = plt.imread(path)
        if image.ndim not in (2, 3) or min(image.shape[:2]) < 200:
            raise FigureInputError(f"PNG dimensions are too small: {path}")
        if float(np.nanstd(image.astype(np.float64))) < 1e-4:
            raise FigureInputError(f"PNG appears blank: {path}")


def export_figure(
    fig: plt.Figure,
    base: Path,
    *,
    dpi: int,
) -> list[dict[str, Any]]:
    base.parent.mkdir(parents=True, exist_ok=True)
    outputs = []
    for suffix in (".svg", ".pdf", ".png"):
        path = base.with_suffix(suffix)
        kwargs: dict[str, Any] = {
            "bbox_inches": "tight",
            "pad_inches": 0.04,
        }
        if suffix == ".png":
            kwargs["dpi"] = dpi
        fig.savefig(path, **kwargs)
        validate_export(path)
        outputs.append(
            {
                "figure": base.name,
                "role": suffix.lstrip("."),
                "path": path.name,
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    plt.close(fig)
    return outputs


def dynamic_limits(values: Sequence[float], errors: Sequence[float]) -> tuple[float, float]:
    lower = min(value - error for value, error in zip(values, errors, strict=True))
    upper = max(value + error for value, error in zip(values, errors, strict=True))
    span = max(upper - lower, 1.0)
    return max(0.0, lower - 0.10 * span), min(100.0, upper + 0.10 * span)


def plot_main_dataset(
    data: AggregateData,
    dataset: str,
    output_dir: Path,
    dpi: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = [
        row for row in data.main_summary if row["dataset"] == dataset
    ]
    rows.sort(
        key=lambda row: (
            TASKS[dataset].index(row["task"]),
            VARIANTS.index(row["variant"]),
        )
    )
    source_path = output_dir / f"formal_main_{dataset}_variants_source.csv"
    write_csv(source_path, rows)
    task_count = len(TASKS[dataset])
    height = 4.6 if dataset == "university1652" else 7.0
    fig = plt.figure(figsize=(7.2, height))
    grid = fig.add_gridspec(
        2,
        1,
        height_ratios=(1.0, 1.25 if dataset == "university1652" else 1.8),
        hspace=0.48,
    )
    ax_heat = fig.add_subplot(grid[0, 0])
    ax_dot = fig.add_subplot(grid[1, 0])

    lookup = {
        (row["task"], row["variant"]): row for row in rows
    }
    r1 = np.asarray(
        [
            [
                float(lookup[(task, variant)]["r_at_1_mean_pct"])
                for variant in VARIANTS
            ]
            for task in TASKS[dataset]
        ],
        dtype=np.float64,
    )
    r1_sd = np.asarray(
        [
            [
                float(lookup[(task, variant)]["r_at_1_sample_sd_pct"])
                for variant in VARIANTS
            ]
            for task in TASKS[dataset]
        ],
        dtype=np.float64,
    )
    vmin = max(0.0, float(r1.min()) - 0.08 * max(float(np.ptp(r1)), 1.0))
    vmax = min(100.0, float(r1.max()) + 0.04 * max(float(np.ptp(r1)), 1.0))
    image = ax_heat.imshow(
        r1,
        cmap="Blues",
        aspect="auto",
        vmin=vmin,
        vmax=vmax,
        interpolation="nearest",
    )
    ax_heat.set_xticks(np.arange(len(VARIANTS)))
    ax_heat.set_xticklabels(
        [VARIANT_LABELS[variant] for variant in VARIANTS],
        rotation=18,
        ha="right",
    )
    ax_heat.set_yticks(np.arange(task_count))
    ax_heat.set_yticklabels([short_task_label(task) for task in TASKS[dataset]])
    ax_heat.tick_params(length=0)
    for spine in ax_heat.spines.values():
        spine.set_visible(False)
    midpoint = (vmin + vmax) / 2.0
    for row_index in range(task_count):
        for column_index in range(len(VARIANTS)):
            value = r1[row_index, column_index]
            color = "white" if value > midpoint else "#272727"
            ax_heat.text(
                column_index,
                row_index,
                f"{value:.1f}\n±{r1_sd[row_index, column_index]:.1f}",
                ha="center",
                va="center",
                color=color,
                fontsize=5.4,
                linespacing=0.9,
            )
    colorbar = fig.colorbar(image, ax=ax_heat, fraction=0.025, pad=0.018)
    colorbar.set_label("R@1 mean (%)", fontsize=6.5)
    colorbar.ax.tick_params(labelsize=6, length=2)
    ax_heat.set_title(
        "Task-specific R@1 across six frozen variants (mean ± sample SD, n=3 seeds)",
        loc="left",
        fontsize=7.5,
        pad=5,
    )
    add_panel_label(ax_heat, "a")

    task_centers = np.arange(task_count, dtype=np.float64)
    offsets = np.linspace(-0.30, 0.30, len(VARIANTS))
    all_means: list[float] = []
    all_sd: list[float] = []
    for variant_index, variant in enumerate(VARIANTS):
        means = np.asarray(
            [
                float(lookup[(task, variant)]["official_trapezoid_mAP_mean_pct"])
                for task in TASKS[dataset]
            ]
        )
        standard_deviations = np.asarray(
            [
                float(
                    lookup[(task, variant)][
                        "official_trapezoid_mAP_sample_sd_pct"
                    ]
                )
                for task in TASKS[dataset]
            ]
        )
        all_means.extend(means.tolist())
        all_sd.extend(standard_deviations.tolist())
        ax_dot.errorbar(
            means,
            task_centers + offsets[variant_index],
            xerr=standard_deviations,
            fmt=MARKERS[variant],
            color=VARIANT_COLORS[variant],
            markeredgecolor="#272727",
            markeredgewidth=0.35,
            markersize=4.2 if variant != "full" else 5.0,
            elinewidth=0.85,
            capsize=1.8,
            label=VARIANT_LABELS[variant],
            zorder=3 if variant == "full" else 2,
        )
    ax_dot.set_yticks(task_centers)
    ax_dot.set_yticklabels([short_task_label(task) for task in TASKS[dataset]])
    ax_dot.invert_yaxis()
    ax_dot.set_xlabel("Official trapezoidal mAP (%)")
    ax_dot.set_title(
        "Retrieval precision by official task; horizontal bars show sample SD",
        loc="left",
        fontsize=7.5,
        pad=5,
    )
    ax_dot.set_xlim(*dynamic_limits(all_means, all_sd))
    ax_dot.tick_params(axis="both", labelsize=6.3)
    ax_dot.grid(axis="x", color="#D8D8D8", linewidth=0.45, alpha=0.55)
    add_panel_label(ax_dot, "b")
    handles, labels = ax_dot.get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.52, 0.995),
        ncol=3,
        fontsize=6.3,
        handletextpad=0.35,
        columnspacing=1.0,
    )
    fig.subplots_adjust(left=0.22, right=0.96, top=0.91, bottom=0.09)
    base = output_dir / f"formal_main_{dataset}_variants"
    artifacts = export_figure(fig, base, dpi=dpi)
    artifacts.append(source_record(source_path, base.name, len(rows)))
    contract = {
        "figure": base.name,
        "core_conclusion": (
            "Variant performance is reported without cross-task averaging, and "
            "three-seed variation is visible separately for every official task."
        ),
        "panels": {
            "a": "R@1 mean and sample SD heatmap",
            "b": "official mAP mean and sample SD point plot",
        },
        "statistics": "mean ± sample SD over frozen seeds 1, 2, and 3",
        "source_csv": source_path.name,
    }
    return artifacts, contract


def merged_pairwise_rows(data: AggregateData) -> list[dict[str, Any]]:
    tests = {
        (row["dataset"], row["task"], int(row["seed"])): row
        for row in data.mcnemar
    }
    merged: list[dict[str, Any]] = []
    for row in data.bootstrap:
        key = (row["dataset"], row["task"], int(row["seed"]))
        test = tests[key]
        merged.append(
            {
                **row,
                "holm_adjusted_log10_p": test["holm_adjusted_log10_p"],
                "holm_adjusted_p": test["holm_adjusted_p"],
                "reject_holm_0_05": test["reject_holm_0_05"],
                "holm_family_size": test["holm_family_size"],
                "visual_correct_full_wrong": test[
                    "visual_correct_full_wrong"
                ],
                "visual_wrong_full_correct": test[
                    "visual_wrong_full_correct"
                ],
            }
        )
    merged.sort(
        key=lambda row: (
            DATASETS.index(row["dataset"]),
            TASKS[row["dataset"]].index(row["task"]),
            int(row["seed"]),
        )
    )
    return merged


def plot_forest(
    data: AggregateData,
    output_dir: Path,
    dpi: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = merged_pairwise_rows(data)
    source_path = output_dir / "formal_visual_vs_full_forest_source.csv"
    write_csv(source_path, rows)
    fig = plt.figure(figsize=(7.2, 9.0))
    grid = fig.add_gridspec(
        2,
        1,
        height_ratios=(9, 24),
        hspace=0.30,
    )
    axes = [
        fig.add_subplot(grid[0, 0]),
        fig.add_subplot(grid[1, 0]),
    ]
    all_bounds = [
        abs(float(row[field]))
        for row in rows
        for field in ("ci95_low_pp", "ci95_high_pp")
    ]
    limit = max(max(all_bounds) * 1.12, 1.0)
    seed_markers = {1: "o", 2: "s", 3: "^"}
    for panel_index, (dataset, ax) in enumerate(zip(DATASETS, axes, strict=True)):
        selected = [row for row in rows if row["dataset"] == dataset]
        positions = np.arange(len(selected), dtype=np.float64)[::-1]
        for task_index, task in enumerate(TASKS[dataset]):
            task_positions = [
                positions[index]
                for index, row in enumerate(selected)
                if row["task"] == task
            ]
            if task_index % 2 == 0:
                ax.axhspan(
                    min(task_positions) - 0.48,
                    max(task_positions) + 0.48,
                    color="#F2F3F7",
                    zorder=0,
                )
        for position, row in zip(positions, selected, strict=True):
            estimate = float(row["difference_r_at_1_pp"])
            low = float(row["ci95_low_pp"])
            high = float(row["ci95_high_pp"])
            color = "#2E9E44" if estimate >= 0 else "#B64342"
            rejected = true_value(row["reject_holm_0_05"])
            ax.plot([low, high], [position, position], color=color, lw=1.05, zorder=2)
            ax.plot(
                estimate,
                position,
                marker=seed_markers[int(row["seed"])],
                ms=4.2,
                markerfacecolor=color if rejected else "white",
                markeredgecolor=color,
                markeredgewidth=0.9,
                zorder=3,
            )
        labels = [
            f"{short_task_label(row['task'])} · seed {row['seed']}"
            for row in selected
        ]
        ax.set_yticks(positions)
        ax.set_yticklabels(labels, fontsize=5.8)
        ax.axvline(0.0, color="#606060", ls="--", lw=0.8, zorder=1)
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-0.65, len(selected) - 0.35)
        ax.set_xlabel("R@1 difference, full − visual (percentage points)")
        title = "University-1652: three official tasks" if panel_index == 0 else (
            "SUES-200: four altitudes in both directions"
        )
        ax.set_title(title, loc="left", fontsize=7.5, pad=4)
        ax.grid(axis="x", color="#D8D8D8", lw=0.45, alpha=0.55)
        add_panel_label(ax, chr(ord("a") + panel_index))
    fig.text(
        0.99,
        0.012,
        (
            "Intervals: 10,000 path-paired query bootstrap samples. "
            "Filled markers: exact McNemar p remains <0.05 after one "
            "Holm correction over all 33 task-by-seed tests."
        ),
        ha="right",
        va="bottom",
        fontsize=5.5,
        color="#4D4D4D",
    )
    fig.subplots_adjust(left=0.37, right=0.97, top=0.97, bottom=0.06)
    base = output_dir / "formal_visual_vs_full_forest"
    artifacts = export_figure(fig, base, dpi=dpi)
    artifacts.append(source_record(source_path, base.name, len(rows)))
    contract = {
        "figure": base.name,
        "core_conclusion": (
            "The full-versus-visual effect and its query-paired uncertainty are "
            "shown for every task and seed without pooling repeated queries."
        ),
        "panels": {
            "a": "University-1652 task-by-seed effects",
            "b": "SUES-200 task-by-seed effects",
        },
        "statistics": (
            "10,000 path-paired R@1 bootstrap samples; two-sided exact McNemar "
            "with one 33-test Holm family"
        ),
        "source_csv": source_path.name,
    }
    return artifacts, contract


def parse_sues_task(task: str) -> tuple[int, str]:
    match = re.fullmatch(r"sues200_uav_(\d+)m_to_satellite", task)
    if match:
        return int(match.group(1)), "uav_to_satellite"
    match = re.fullmatch(r"sues200_satellite_to_uav_(\d+)m", task)
    if match:
        return int(match.group(1)), "satellite_to_uav"
    raise FigureInputError(f"Not a SUES altitude task: {task}")


def plot_sues_altitude(
    data: AggregateData,
    output_dir: Path,
    dpi: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in data.main_summary:
        if row["dataset"] != "sues200":
            continue
        altitude, direction = parse_sues_task(row["task"])
        rows.append({**row, "altitude_m": altitude, "direction": direction})
    rows.sort(
        key=lambda row: (
            ("uav_to_satellite", "satellite_to_uav").index(row["direction"]),
            int(row["altitude_m"]),
            VARIANTS.index(row["variant"]),
        )
    )
    if len(rows) != 48:
        raise FigureInputError(f"SUES altitude source has {len(rows)} rows, expected 48.")
    source_path = output_dir / "formal_sues_altitude_curves_source.csv"
    write_csv(source_path, rows)
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.8), sharex=True)
    directions = ("uav_to_satellite", "satellite_to_uav")
    metric_rows = (
        ("r_at_1", "R@1 (%)"),
        ("official_trapezoid_mAP", "Official mAP (%)"),
    )
    for row_index, (metric, ylabel) in enumerate(metric_rows):
        for column_index, direction in enumerate(directions):
            ax = axes[row_index, column_index]
            means_for_limits: list[float] = []
            errors_for_limits: list[float] = []
            for variant in VARIANTS:
                selected = [
                    row
                    for row in rows
                    if row["direction"] == direction and row["variant"] == variant
                ]
                selected.sort(key=lambda row: int(row["altitude_m"]))
                x = np.asarray([int(row["altitude_m"]) for row in selected])
                mean = np.asarray(
                    [float(row[f"{metric}_mean_pct"]) for row in selected]
                )
                sd = np.asarray(
                    [float(row[f"{metric}_sample_sd_pct"]) for row in selected]
                )
                means_for_limits.extend(mean.tolist())
                errors_for_limits.extend(sd.tolist())
                ax.errorbar(
                    x,
                    mean,
                    yerr=sd,
                    color=VARIANT_COLORS[variant],
                    marker=MARKERS[variant],
                    markersize=3.6 if variant != "full" else 4.5,
                    markeredgecolor="#272727",
                    markeredgewidth=0.3,
                    linewidth=1.0 if variant != "full" else 1.45,
                    elinewidth=0.7,
                    capsize=1.5,
                    alpha=0.88 if variant != "full" else 1.0,
                    label=VARIANT_LABELS[variant],
                    zorder=3 if variant == "full" else 2,
                )
            ax.set_ylim(*dynamic_limits(means_for_limits, errors_for_limits))
            ax.set_xticks(SUES_ALTITUDES)
            if row_index == 1:
                ax.set_xlabel("UAV altitude (m)")
            if column_index == 0:
                ax.set_ylabel(ylabel)
            direction_title = (
                "UAV → satellite"
                if direction == "uav_to_satellite"
                else "Satellite → UAV"
            )
            if row_index == 0:
                ax.set_title(direction_title, fontsize=7.5, pad=5)
            ax.grid(axis="y", color="#D8D8D8", lw=0.45, alpha=0.55)
            ax.tick_params(labelsize=6.3)
            add_panel_label(ax, chr(ord("a") + row_index * 2 + column_index))
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.52, 0.995),
        ncol=3,
        fontsize=6.2,
        columnspacing=1.0,
        handletextpad=0.35,
    )
    fig.text(
        0.99,
        0.015,
        "Points show mean ± sample SD over three frozen seeds; tasks remain separate.",
        ha="right",
        va="bottom",
        fontsize=5.5,
        color="#4D4D4D",
    )
    fig.subplots_adjust(left=0.10, right=0.98, top=0.89, bottom=0.11, hspace=0.35, wspace=0.25)
    base = output_dir / "formal_sues_altitude_curves"
    artifacts = export_figure(fig, base, dpi=dpi)
    artifacts.append(source_record(source_path, base.name, len(rows)))
    contract = {
        "figure": base.name,
        "core_conclusion": (
            "Altitude-dependent performance is visible in both retrieval "
            "directions for every frozen variant, without combining altitude tasks."
        ),
        "panels": {
            "a": "UAV-to-satellite R@1",
            "b": "satellite-to-UAV R@1",
            "c": "UAV-to-satellite official mAP",
            "d": "satellite-to-UAV official mAP",
        },
        "statistics": "mean ± sample SD over frozen seeds 1, 2, and 3",
        "source_csv": source_path.name,
    }
    return artifacts, contract


def task_palette(dataset: str) -> dict[str, str]:
    if dataset == "university1652":
        colors = ("#0F4D92", "#42949E", "#9A4D8E")
    else:
        colors = (
            "#0F4D92",
            "#3775BA",
            "#42949E",
            "#6EA9A5",
            "#9A4D8E",
            "#C07AA8",
            "#B07A4F",
            "#606060",
        )
    return dict(zip(TASKS[dataset], colors, strict=True))


def plot_sensitivity(
    data: AggregateData,
    output_dir: Path,
    dpi: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in data.sensitivity_reference:
        enriched: dict[str, Any] = dict(row)
        if data.complexity is not None:
            enriched["complexity_metric"] = data.complexity.column
            enriched["complexity_plot_value"] = (
                float(row[data.complexity.column]) * data.complexity.scale
            )
        else:
            enriched["complexity_metric"] = ""
            enriched["complexity_plot_value"] = ""
        rows.append(enriched)
    rows.sort(
        key=lambda row: (
            DATASETS.index(row["dataset"]),
            TASKS[row["dataset"]].index(row["task"]),
            SETTINGS.index(row["setting"]),
        )
    )
    source_path = output_dir / "formal_sensitivity_source.csv"
    write_csv(source_path, rows)
    has_complexity = data.complexity is not None
    if has_complexity:
        fig, axes = plt.subplots(2, 2, figsize=(7.2, 6.2))
    else:
        fig, top_axes = plt.subplots(1, 2, figsize=(7.2, 3.4))
        axes = np.asarray([top_axes])
    for dataset_index, dataset in enumerate(DATASETS):
        ax = axes[0, dataset_index]
        selected_dataset = [row for row in rows if row["dataset"] == dataset]
        x = np.arange(len(TASKS[dataset]), dtype=np.float64)
        offsets = np.linspace(-0.21, 0.21, len(SETTINGS))
        for setting_index, setting in enumerate(SETTINGS):
            values = [
                float(
                    next(
                        row["r_at_1_pct"]
                        for row in selected_dataset
                        if row["task"] == task and row["setting"] == setting
                    )
                )
                for task in TASKS[dataset]
            ]
            ax.plot(
                x + offsets[setting_index],
                values,
                color=SETTING_COLORS[setting],
                marker=("o", "s", "^", "D")[setting_index],
                markersize=4.0,
                linewidth=1.05,
                label=SETTING_LABELS[setting],
            )
        ax.set_xticks(x)
        ax.set_xticklabels(
            [short_task_label(task) for task in TASKS[dataset]],
            rotation=32 if dataset == "sues200" else 18,
            ha="right",
            fontsize=5.7,
        )
        ax.set_ylabel("R@1 (%)" if dataset_index == 0 else "")
        ax.set_title(
            "University-1652" if dataset == "university1652" else "SUES-200",
            fontsize=7.5,
            pad=5,
        )
        ax.grid(axis="y", color="#D8D8D8", lw=0.45, alpha=0.55)
        add_panel_label(ax, chr(ord("a") + dataset_index))
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.52, 0.995),
        ncol=2,
        fontsize=6.1,
        columnspacing=1.0,
        handletextpad=0.35,
    )
    if has_complexity:
        assert data.complexity is not None
        for dataset_index, dataset in enumerate(DATASETS):
            ax = axes[1, dataset_index]
            colors = task_palette(dataset)
            for task in TASKS[dataset]:
                selected = [
                    row
                    for row in rows
                    if row["dataset"] == dataset and row["task"] == task
                ]
                selected.sort(key=lambda row: SETTINGS.index(row["setting"]))
                complexity = np.asarray(
                    [float(row["complexity_plot_value"]) for row in selected]
                )
                accuracy = np.asarray([float(row["r_at_1_pct"]) for row in selected])
                ax.plot(
                    complexity,
                    accuracy,
                    color=colors[task],
                    marker="o",
                    markersize=3.2,
                    linewidth=0.85,
                    alpha=0.9,
                    label=short_task_label(task),
                )
                for x_value, y_value, row in zip(
                    complexity, accuracy, selected, strict=True
                ):
                    if row["setting"] == "full":
                        ax.scatter(
                            [x_value],
                            [y_value],
                            marker="P",
                            s=25,
                            color=colors[task],
                            edgecolor="#272727",
                            linewidth=0.35,
                            zorder=4,
                        )
            ax.set_xlabel(data.complexity.label)
            ax.set_ylabel("R@1 (%)" if dataset_index == 0 else "")
            ax.grid(color="#D8D8D8", lw=0.45, alpha=0.5)
            ax.legend(
                fontsize=4.8,
                ncol=1 if dataset == "university1652" else 2,
                loc="best",
                handlelength=1.4,
                labelspacing=0.25,
            )
            add_panel_label(ax, chr(ord("c") + dataset_index))
        fig.text(
            0.99,
            0.012,
            (
                "Accuracy and complexity remain task-specific. "
                "No cross-task average is plotted; sensitivity runs use frozen seed 1."
            ),
            ha="right",
            va="bottom",
            fontsize=5.3,
            color="#4D4D4D",
        )
        fig.subplots_adjust(
            left=0.10,
            right=0.98,
            top=0.88,
            bottom=0.12,
            hspace=0.55,
            wspace=0.25,
        )
    else:
        fig.text(
            0.99,
            0.018,
            (
                "Frozen seed 1; no error bars. Complexity panel omitted because "
                "the completed aggregate contains no measured complexity field."
            ),
            ha="right",
            va="bottom",
            fontsize=5.3,
            color="#4D4D4D",
        )
        fig.subplots_adjust(left=0.10, right=0.98, top=0.82, bottom=0.27, wspace=0.25)
    base = output_dir / "formal_sensitivity"
    artifacts = export_figure(fig, base, dpi=dpi)
    artifacts.append(source_record(source_path, base.name, len(rows)))
    contract = {
        "figure": base.name,
        "core_conclusion": (
            "Backbone and embedding-dimension sensitivity is shown separately "
            "for every official task."
        ),
        "panels": {
            "a": "University-1652 seed-1 task accuracy",
            "b": "SUES-200 seed-1 task accuracy",
            **(
                {
                    "c": (
                        "University-1652 task-specific accuracy versus "
                        f"{data.complexity.label}"
                    ),
                    "d": (
                        "SUES-200 task-specific accuracy versus "
                        f"{data.complexity.label}"
                    ),
                }
                if data.complexity is not None
                else {}
            ),
        },
        "statistics": "single frozen seed 1; no uncertainty interval is implied",
        "complexity_panel_generated": has_complexity,
        "complexity_field": (
            data.complexity.column if data.complexity is not None else None
        ),
        "complexity_omission_reason": (
            None
            if has_complexity
            else "No complete measured complexity column exists in the aggregate CSV."
        ),
        "source_csv": source_path.name,
    }
    return artifacts, contract


def figure_output_manifest(
    output_dir: Path,
    data: AggregateData,
    artifacts: Sequence[Mapping[str, Any]],
    contracts: Sequence[Mapping[str, Any]],
    script_path: Path,
    dpi: int,
) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "completed",
        "generated_utc": utc_now(),
        "backend": "Python/matplotlib only",
        "png_dpi": dpi,
        "editable_text": {
            "svg_fonttype": "none",
            "pdf_fonttype": 42,
        },
        "input": {
            "aggregate_manifest_sha256": data.manifest_sha256,
            "aggregate_schema": data.manifest["schema_version"],
            "aggregate_status": data.manifest["status"],
            "aggregate_csv_sha256": data.csv_sha256,
        },
        "analysis_code": {
            "path": script_path.name,
            "sha256": sha256_file(script_path),
        },
        "task_policy": {
            "university1652_task_count": 3,
            "sues200_task_count": 8,
            "macro_average_generated": False,
            "overall_plus_subset_duplicate_generated": False,
        },
        "complexity": {
            "detected": data.complexity is not None,
            "field": data.complexity.column if data.complexity else None,
            "label": data.complexity.label if data.complexity else None,
            "policy": (
                "Plot only a complete measured field from the aggregate CSV; "
                "never infer or fabricate complexity."
            ),
        },
        "figure_contracts": list(contracts),
        "artifacts": list(artifacts),
        "qa": {
            "export_formats": ["svg", "pdf", "png"],
            "source_csv_per_figure": True,
            "svg_editable_text_checked": True,
            "pdf_header_checked": True,
            "png_nonblank_and_minimum_dimensions_checked": True,
            "statistics_definitions_embedded_in_contracts": True,
        },
    }
    manifest["payload_sha256"] = canonical_sha256(manifest)
    return manifest


def generate_figures(
    aggregate_dir: Path,
    output_dir: Path,
    *,
    png_dpi: int = 600,
) -> dict[str, Any]:
    if png_dpi < 100:
        raise ValueError("PNG DPI must be at least 100.")
    data = load_completed_aggregate(aggregate_dir)
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict[str, Any]] = []
    contracts: list[dict[str, Any]] = []
    for dataset in DATASETS:
        current_artifacts, contract = plot_main_dataset(
            data, dataset, output_dir, png_dpi
        )
        artifacts.extend(current_artifacts)
        contracts.append(contract)
    current_artifacts, contract = plot_forest(data, output_dir, png_dpi)
    artifacts.extend(current_artifacts)
    contracts.append(contract)
    current_artifacts, contract = plot_sues_altitude(data, output_dir, png_dpi)
    artifacts.extend(current_artifacts)
    contracts.append(contract)
    current_artifacts, contract = plot_sensitivity(data, output_dir, png_dpi)
    artifacts.extend(current_artifacts)
    contracts.append(contract)
    if len(contracts) != 5:
        raise AssertionError("Internal figure plan must contain exactly five figures.")
    script_path = Path(__file__).resolve()
    manifest = figure_output_manifest(
        output_dir,
        data,
        artifacts,
        contracts,
        script_path,
        png_dpi,
    )
    atomic_write_json(output_dir / "formal_figure_manifest.json", manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    script = Path(__file__).resolve()
    delivery_root = script.parents[2]
    parser = argparse.ArgumentParser(
        description=(
            "Fail-closed Nature-style plotting for the completed frozen formal "
            "36+6 aggregate."
        )
    )
    parser.add_argument(
        "--aggregate-dir",
        type=Path,
        default=(
            delivery_root
            / "lgm_game_pytorch"
            / "results"
            / "formal_matrix_aggregate"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            delivery_root
            / "lgm_game_paper_latex"
            / "figures"
            / "formal_results"
        ),
    )
    parser.add_argument(
        "--png-dpi",
        type=int,
        choices=(600,),
        default=600,
        help="Formal export is fixed at 600 dpi.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        manifest = generate_figures(
            args.aggregate_dir.expanduser(),
            args.output_dir.expanduser(),
            png_dpi=int(args.png_dpi),
        )
    except IncompleteAggregateError as error:
        print(f"INCOMPLETE AGGREGATE: {error}", file=sys.stderr)
        raise SystemExit(2) from error
    except FigureInputError as error:
        print(f"FIGURE INPUT FAILURE: {error}", file=sys.stderr)
        raise SystemExit(3) from error
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "figure_count": len(manifest["figure_contracts"]),
                "payload_sha256": manifest["payload_sha256"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
