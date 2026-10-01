"""Shared registry and strict validators for the four-run robustness pipeline."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


SCHEMA_VERSION = "lgm-game.formal-robustness-pipeline.v1"
ROBUSTNESS_MANIFEST_SCHEMA = "lgm-game.image-level-robustness.v1"
DATASETS = ("university1652", "sues200")
VARIANTS = ("visual", "full")
EXPECTED_RUN_COUNT = 4
EXPECTED_CONDITION_COUNT = 30
EXPECTED_SEED = 1

OFFICIAL_TASK_SCALE: dict[str, dict[str, tuple[int, int]]] = {
    "university1652": {
        "university1652_drone_to_satellite": (37855, 951),
        "university1652_satellite_to_drone": (701, 51355),
        "university1652_street_to_satellite": (2579, 951),
    },
    "sues200": {
        "sues200_uav_150m_to_satellite": (4000, 200),
        "sues200_satellite_to_uav_150m": (80, 10000),
        "sues200_uav_200m_to_satellite": (4000, 200),
        "sues200_satellite_to_uav_200m": (80, 10000),
        "sues200_uav_250m_to_satellite": (4000, 200),
        "sues200_satellite_to_uav_250m": (80, 10000),
        "sues200_uav_300m_to_satellite": (4000, 200),
        "sues200_satellite_to_uav_300m": (80, 10000),
    },
}
EXPECTED_UNIQUE_QUERIES = {
    "university1652": 41135,
    "sues200": 16080,
}
EXPECTED_UNIQUE_GALLERIES = {
    "university1652": 52306,
    "sues200": 40200,
}
REQUIRED_METRICS = (
    "r_at_1",
    "r_at_5",
    "r_at_10",
    "r_at_20",
    "official_trapezoid_mAP",
    "MRR",
)
REQUIRED_CLEAN_ARRAYS = (
    "query_paths",
    "query_labels",
    "correct",
    "first_positive_rank_zero_based",
    "per_query_official_trapezoid_AP",
    "reciprocal_rank",
    "top1_gallery_indices",
    "top1_gallery_paths",
    "top1_gallery_labels",
)
REQUIRED_CORRUPTED_ARRAYS = REQUIRED_CLEAN_ARRAYS + (
    "clean_correct",
    "clean_first_positive_rank_zero_based",
    "clean_per_query_official_trapezoid_AP",
    "clean_reciprocal_rank",
    "delta_official_trapezoid_AP_corrupted_minus_clean",
    "delta_reciprocal_rank_corrupted_minus_clean",
    "top1_correctness_transition_corrupted_minus_clean",
)


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
        while True:
            block = handle.read(block_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, default=str)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def verify_payload_hash(
    payload: Mapping[str, Any],
    field: str = "payload_sha256",
) -> bool:
    copied = dict(payload)
    declared = copied.pop(field, None)
    return isinstance(declared, str) and declared == canonical_sha256(copied)


@dataclass(frozen=True)
class RobustnessRunSpec:
    dataset: str
    variant: str
    data_root: Path
    evidence: Path
    checkpoint: Path
    output_dir: Path

    @property
    def identifier(self) -> str:
        return f"{self.dataset}/{self.variant}/seed_1"

    @property
    def robustness_manifest(self) -> Path:
        return self.output_dir / "robustness_manifest.json"


def build_run_specs(
    delivery_root: Path,
    university_root: Path,
    sues_root: Path,
) -> list[RobustnessRunSpec]:
    delivery_root = delivery_root.expanduser().resolve()
    package_root = delivery_root / "lgm_game_pytorch"
    roots = {
        "university1652": university_root.expanduser().resolve(),
        "sues200": sues_root.expanduser().resolve(),
    }
    evidence = {
        "university1652": (
            package_root
            / "evidence_cache"
            / "university1652_clip_image_evidence.npz"
        ),
        "sues200": (
            package_root / "evidence_cache" / "sues200_clip_image_evidence.npz"
        ),
    }
    specs: list[RobustnessRunSpec] = []
    for dataset in DATASETS:
        for variant in VARIANTS:
            specs.append(
                RobustnessRunSpec(
                    dataset=dataset,
                    variant=variant,
                    data_root=roots[dataset],
                    evidence=evidence[dataset],
                    checkpoint=(
                        package_root
                        / "runs"
                        / "formal_main"
                        / dataset
                        / variant
                        / "seed_1"
                        / "best.pt"
                    ),
                    output_dir=(
                        package_root
                        / "runs"
                        / "formal_robustness"
                        / dataset
                        / variant
                        / "seed_1"
                    ),
                )
            )
    if len(specs) != EXPECTED_RUN_COUNT:
        raise AssertionError("The formal robustness registry must contain four runs.")
    return specs


def expected_condition_payloads(evaluator_module: Any) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for spec in evaluator_module.CORRUPTION_SPECS:
        for severity_index in range(1, 6):
            output.append(
                evaluator_module._condition_payload(
                    corruption=spec.name,
                    severity_index=severity_index,
                    corruption_seed=evaluator_module.DEFAULT_CORRUPTION_SEED,
                )
            )
    if len(output) != EXPECTED_CONDITION_COUNT:
        raise AssertionError("The evaluator does not expose the frozen 6x5 matrix.")
    return output


def condition_directory(output_dir: Path, condition: Mapping[str, Any]) -> Path:
    return (
        output_dir
        / "conditions"
        / str(condition["name"])
        / f"severity_{int(condition['severity_index']):02d}"
    )


def _validate_artifact_inventory(
    base_dir: Path,
    artifacts: Any,
    issues: list[str],
    label: str,
) -> None:
    if not isinstance(artifacts, dict) or not artifacts:
        issues.append(f"{label}: artifact inventory is absent or empty")
        return
    for relative_path, descriptor in artifacts.items():
        if not isinstance(relative_path, str) or not isinstance(descriptor, dict):
            issues.append(f"{label}: malformed artifact record")
            continue
        candidate = (base_dir / relative_path).resolve()
        try:
            candidate.relative_to(base_dir.resolve())
        except ValueError:
            issues.append(f"{label}: artifact path escapes output directory")
            continue
        if not candidate.is_file():
            issues.append(f"{label}: missing artifact {relative_path}")
            continue
        if int(descriptor.get("bytes", -1)) != candidate.stat().st_size:
            issues.append(f"{label}: byte count mismatch for {relative_path}")
            continue
        if descriptor.get("sha256") != sha256_file(candidate):
            issues.append(f"{label}: SHA-256 mismatch for {relative_path}")


def _metrics_issues(
    metrics_path: Path,
    dataset: str,
    *,
    condition: Mapping[str, Any],
    expect_degradation: bool,
    expected_task_scale: Mapping[str, tuple[int, int]],
) -> tuple[list[str], dict[str, Any]]:
    issues: list[str] = []
    try:
        metrics = load_json(metrics_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return [f"cannot read metrics {metrics_path}: {error}"], {}
    if metrics.get("schema_version") != ROBUSTNESS_MANIFEST_SCHEMA:
        issues.append(f"{metrics_path}: unexpected metrics schema")
    if metrics.get("full_gallery") is not True:
        issues.append(f"{metrics_path}: full_gallery is not true")
    if metrics.get("clean_gallery_for_every_condition") is not True:
        issues.append(f"{metrics_path}: clean-gallery flag is not true")
    if metrics.get("condition") != condition:
        issues.append(f"{metrics_path}: condition payload differs from registry")
    results = metrics.get("results")
    if not isinstance(results, dict):
        issues.append(f"{metrics_path}: results object is absent")
        results = {}
    if set(results) != set(expected_task_scale):
        issues.append(
            f"{metrics_path}: task set differs from official {dataset} registry"
        )
    for task, (expected_queries, expected_gallery) in expected_task_scale.items():
        row = results.get(task)
        if not isinstance(row, dict):
            continue
        if int(row.get("queries", -1)) != expected_queries:
            issues.append(f"{metrics_path}: {task} query count differs")
        if int(row.get("gallery", -1)) != expected_gallery:
            issues.append(f"{metrics_path}: {task} gallery count differs")
        for metric in REQUIRED_METRICS:
            value = row.get(metric)
            if not isinstance(value, (int, float)) or not np.isfinite(value):
                issues.append(f"{metrics_path}: {task}/{metric} is not finite")
    degradation = metrics.get("degradation_vs_clean")
    if expect_degradation:
        if not isinstance(degradation, dict) or set(degradation) != set(
            expected_task_scale
        ):
            issues.append(f"{metrics_path}: degradation block is incomplete")
        else:
            for task in expected_task_scale:
                task_values = degradation.get(task)
                if not isinstance(task_values, dict):
                    continue
                if set(task_values) != set(REQUIRED_METRICS):
                    issues.append(
                        f"{metrics_path}: degradation metrics differ for {task}"
                    )
    elif degradation is not None:
        issues.append(f"{metrics_path}: clean baseline contains degradation values")
    return issues, metrics


def _per_query_issues(
    arrays_path: Path,
    *,
    expected_queries: int,
    corrupted: bool,
) -> tuple[list[str], str]:
    issues: list[str] = []
    if not arrays_path.is_file():
        return [f"missing per-query artifact: {arrays_path}"], ""
    required = REQUIRED_CORRUPTED_ARRAYS if corrupted else REQUIRED_CLEAN_ARRAYS
    try:
        with np.load(arrays_path, allow_pickle=False) as archive:
            missing = sorted(set(required) - set(archive.files))
            if missing:
                issues.append(
                    f"{arrays_path}: missing arrays {', '.join(missing)}"
                )
                return issues, ""
            query_paths = np.asarray(archive["query_paths"])
            if query_paths.shape != (expected_queries,):
                issues.append(
                    f"{arrays_path}: query_paths shape {query_paths.shape} "
                    f"!= ({expected_queries},)"
                )
            elif len(set(query_paths.astype(str).tolist())) != expected_queries:
                issues.append(f"{arrays_path}: query paths are not unique")
            for name in required:
                values = np.asarray(archive[name])
                if values.shape[0] != expected_queries:
                    issues.append(
                        f"{arrays_path}: {name} first dimension differs from queries"
                    )
                if values.dtype.kind in {"f", "c"} and not np.isfinite(values).all():
                    issues.append(f"{arrays_path}: {name} contains non-finite values")
            path_sha = canonical_sha256(query_paths.astype(str).tolist())
    except (OSError, ValueError, KeyError) as error:
        return [f"cannot validate {arrays_path}: {error}"], ""
    return issues, path_sha


@dataclass
class RobustnessValidation:
    spec: RobustnessRunSpec
    issues: list[str]
    manifest: dict[str, Any]
    run_config: dict[str, Any]
    clean_metrics: dict[str, Any]
    condition_metrics: dict[tuple[str, int], dict[str, Any]]

    @property
    def complete(self) -> bool:
        return not self.issues


def validate_completed_robustness(
    spec: RobustnessRunSpec,
    evaluator_module: Any,
    *,
    verify_artifacts: bool = True,
    verify_per_query: bool = True,
    expected_task_scale: Mapping[str, tuple[int, int]] | None = None,
    expected_evaluator_sha256: str | None = None,
) -> RobustnessValidation:
    """Validate one completed robustness tree; never returns partial metrics as valid."""

    issues: list[str] = []
    manifest: dict[str, Any] = {}
    run_config: dict[str, Any] = {}
    clean_metrics: dict[str, Any] = {}
    condition_metrics: dict[tuple[str, int], dict[str, Any]] = {}
    task_scale = (
        dict(expected_task_scale)
        if expected_task_scale is not None
        else OFFICIAL_TASK_SCALE[spec.dataset]
    )
    try:
        manifest = load_json(spec.robustness_manifest)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return RobustnessValidation(
            spec,
            [f"{spec.identifier}: cannot read robustness manifest: {error}"],
            {},
            {},
            {},
            {},
        )
    if manifest.get("schema_version") != ROBUSTNESS_MANIFEST_SCHEMA:
        issues.append(f"{spec.identifier}: unexpected robustness schema")
    if manifest.get("status") != "completed":
        issues.append(f"{spec.identifier}: robustness status is not completed")
    if not verify_payload_hash(manifest):
        issues.append(f"{spec.identifier}: robustness payload hash is invalid")
    if manifest.get("dataset") != spec.dataset:
        issues.append(f"{spec.identifier}: manifest dataset differs")
    if manifest.get("variant") != spec.variant:
        issues.append(f"{spec.identifier}: manifest variant differs")
    if (
        int(manifest.get("expected_corruption_conditions", -1))
        != EXPECTED_CONDITION_COUNT
        or int(manifest.get("completed_corruption_conditions", -1))
        != EXPECTED_CONDITION_COUNT
        or manifest.get("condition_count_complete") is not True
    ):
        issues.append(f"{spec.identifier}: 30-condition completion gate failed")
    for flag in (
        "full_gallery",
        "clean_gallery_for_every_condition",
        "all_official_queries_for_every_condition",
    ):
        if manifest.get(flag) is not True:
            issues.append(f"{spec.identifier}: {flag} is not true")
    if manifest.get("feature_level_corruption_used") is not False:
        issues.append(f"{spec.identifier}: feature-level corruption flag is unsafe")
    checkpoint = manifest.get("checkpoint")
    if (
        not isinstance(checkpoint, dict)
        or checkpoint.get("variant") != spec.variant
        or int(checkpoint.get("seed", -1)) != EXPECTED_SEED
        or Path(str(checkpoint.get("training_manifest_path", ""))).resolve()
        != (spec.checkpoint.parent / "run_manifest.json").resolve()
    ):
        issues.append(f"{spec.identifier}: checkpoint provenance differs")
    elif spec.checkpoint.is_file() and checkpoint.get(
        "checkpoint_sha256"
    ) != sha256_file(spec.checkpoint):
        issues.append(f"{spec.identifier}: checkpoint SHA-256 differs")

    run_config_path = spec.output_dir / "run_config.json"
    try:
        run_config = load_json(run_config_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        issues.append(f"{spec.identifier}: cannot read run_config.json: {error}")
        run_config = {}
    run_config_sha = manifest.get("run_config_sha256")
    immutable = run_config.get("immutable_config")
    if (
        not isinstance(run_config_sha, str)
        or len(run_config_sha) != 64
        or run_config.get("run_config_sha256") != run_config_sha
        or not isinstance(immutable, dict)
        or canonical_sha256(immutable) != run_config_sha
    ):
        issues.append(f"{spec.identifier}: run configuration hash is invalid")
        immutable = {}
    if immutable.get("dataset") != spec.dataset:
        issues.append(f"{spec.identifier}: run config dataset differs")
    immutable_checkpoint = immutable.get("checkpoint")
    if (
        not isinstance(immutable_checkpoint, dict)
        or immutable_checkpoint.get("variant") != spec.variant
        or int(immutable_checkpoint.get("seed", -1)) != EXPECTED_SEED
    ):
        issues.append(f"{spec.identifier}: run config checkpoint differs")
    if immutable.get("corruption_matrix") != evaluator_module.corruption_matrix_payload():
        issues.append(f"{spec.identifier}: corruption matrix differs from evaluator")
    if int(immutable.get("corruption_seed", -1)) != int(
        evaluator_module.DEFAULT_CORRUPTION_SEED
    ):
        issues.append(f"{spec.identifier}: corruption seed differs")
    sources = immutable.get("sources")
    evaluator_source = (
        sources.get("robustness_evaluator")
        if isinstance(sources, dict)
        else None
    )
    if not isinstance(evaluator_source, dict) or len(
        str(evaluator_source.get("sha256", ""))
    ) != 64:
        issues.append(f"{spec.identifier}: evaluator source provenance is absent")
    elif (
        expected_evaluator_sha256 is not None
        and evaluator_source.get("sha256") != expected_evaluator_sha256
    ):
        issues.append(f"{spec.identifier}: evaluator source SHA-256 differs")
    configured_scale = immutable.get("official_task_scale")
    if not isinstance(configured_scale, dict) or set(configured_scale) != set(
        task_scale
    ):
        issues.append(f"{spec.identifier}: official task registry differs")
    else:
        for task, (queries, gallery) in task_scale.items():
            row = configured_scale.get(task)
            if (
                not isinstance(row, dict)
                or int(row.get("queries", -1)) != queries
                or int(row.get("gallery", -1)) != gallery
            ):
                issues.append(f"{spec.identifier}: task scale differs for {task}")
    expected_unique_queries = (
        EXPECTED_UNIQUE_QUERIES[spec.dataset]
        if expected_task_scale is None
        else int(immutable.get("unique_query_images", -1))
    )
    expected_unique_galleries = (
        EXPECTED_UNIQUE_GALLERIES[spec.dataset]
        if expected_task_scale is None
        else int(immutable.get("unique_clean_gallery_images", -1))
    )
    if int(immutable.get("unique_query_images", -1)) != expected_unique_queries:
        issues.append(f"{spec.identifier}: unique query count differs")
    if (
        int(immutable.get("unique_clean_gallery_images", -1))
        != expected_unique_galleries
    ):
        issues.append(f"{spec.identifier}: unique gallery count differs")

    clean_condition = evaluator_module._condition_payload(
        corruption=None,
        severity_index=None,
        corruption_seed=evaluator_module.DEFAULT_CORRUPTION_SEED,
    )
    clean_dir = spec.output_dir / "clean"
    clean_manifest_path = clean_dir / "condition_manifest.json"
    try:
        clean_manifest = load_json(clean_manifest_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        issues.append(f"{spec.identifier}: cannot read clean condition: {error}")
        clean_manifest = {}
    if (
        clean_manifest.get("status") != "completed"
        or not verify_payload_hash(clean_manifest)
        or clean_manifest.get("condition") != clean_condition
        or clean_manifest.get("run_config_sha256") != run_config_sha
        or clean_manifest.get("all_official_queries_used") is not True
        or clean_manifest.get("clean_gallery_used") is not True
        or clean_manifest.get("feature_level_corruption_used") is not False
    ):
        issues.append(f"{spec.identifier}: clean condition manifest is invalid")
    metrics_issues, clean_metrics = _metrics_issues(
        clean_dir / "metrics.json",
        spec.dataset,
        condition=clean_condition,
        expect_degradation=False,
        expected_task_scale=task_scale,
    )
    issues.extend(metrics_issues)
    if verify_artifacts:
        _validate_artifact_inventory(
            clean_dir,
            clean_manifest.get("artifacts"),
            issues,
            f"{spec.identifier}/clean",
        )

    clean_query_hashes: dict[str, str] = {}
    if verify_per_query:
        for task, (queries, _) in task_scale.items():
            arrays_path = (
                clean_dir
                / "per_query_arrays"
                / f"{evaluator_module.formal.slugify(task)}_per_query.npz"
            )
            array_issues, path_sha = _per_query_issues(
                arrays_path,
                expected_queries=queries,
                corrupted=False,
            )
            issues.extend(array_issues)
            clean_query_hashes[task] = path_sha

    expected_conditions = expected_condition_payloads(evaluator_module)
    expected_keys = {
        (str(condition["name"]), int(condition["severity_index"]))
        for condition in expected_conditions
    }
    actual_condition_manifests = {
        path.parent.relative_to(spec.output_dir / "conditions").as_posix()
        for path in (spec.output_dir / "conditions").glob(
            "*/severity_*/condition_manifest.json"
        )
    }
    expected_relative_dirs = {
        condition_directory(Path("."), condition)
        .relative_to("conditions")
        .as_posix()
        for condition in expected_conditions
    }
    if actual_condition_manifests != expected_relative_dirs:
        issues.append(
            f"{spec.identifier}: condition directories are missing or contain extras"
        )

    for condition in expected_conditions:
        corruption = str(condition["name"])
        severity = int(condition["severity_index"])
        condition_dir = condition_directory(spec.output_dir, condition)
        condition_manifest_path = condition_dir / "condition_manifest.json"
        try:
            condition_manifest = load_json(condition_manifest_path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            issues.append(
                f"{spec.identifier}/{corruption}/{severity}: cannot read manifest: {error}"
            )
            continue
        expected_condition_sha = canonical_sha256(
            {"run_config_sha256": run_config_sha, "condition": condition}
        )
        if (
            condition_manifest.get("status") != "completed"
            or not verify_payload_hash(condition_manifest)
            or condition_manifest.get("condition") != condition
            or condition_manifest.get("run_config_sha256") != run_config_sha
            or condition_manifest.get("condition_sha256")
            != expected_condition_sha
            or condition_manifest.get("all_official_queries_used") is not True
            or condition_manifest.get("clean_gallery_used") is not True
            or condition_manifest.get("feature_level_corruption_used") is not False
        ):
            issues.append(
                f"{spec.identifier}/{corruption}/{severity}: condition manifest invalid"
            )
        coverage = condition_manifest.get("query_coverage")
        expected_evidence_mode = (
            "recomputed_from_corrupted_rgb_pixels"
            if spec.variant == "full"
            else "not_used_by_visual_variant"
        )
        if (
            not isinstance(coverage, dict)
            or coverage.get("complete") is not True
            or float(coverage.get("coverage_fraction", -1.0)) != 1.0
            or int(coverage.get("expected_unique_images", -1))
            != expected_unique_queries
            or int(coverage.get("encoded_unique_images", -1))
            != expected_unique_queries
            or coverage.get("query_content_style_evidence_mode")
            != expected_evidence_mode
            or coverage.get("corruption_applied_before_all_model_preprocessing")
            is not True
            or len(str(coverage.get("encoded_feature_sha256", ""))) != 64
        ):
            issues.append(
                f"{spec.identifier}/{corruption}/{severity}: query coverage invalid"
            )
        metrics_issues, metrics = _metrics_issues(
            condition_dir / "metrics.json",
            spec.dataset,
            condition=condition,
            expect_degradation=True,
            expected_task_scale=task_scale,
        )
        issues.extend(metrics_issues)
        condition_metrics[(corruption, severity)] = metrics
        if verify_artifacts:
            _validate_artifact_inventory(
                condition_dir,
                condition_manifest.get("artifacts"),
                issues,
                f"{spec.identifier}/{corruption}/{severity}",
            )
        if verify_per_query:
            for task, (queries, _) in task_scale.items():
                arrays_path = (
                    condition_dir
                    / "per_query_arrays"
                    / f"{evaluator_module.formal.slugify(task)}_per_query.npz"
                )
                array_issues, path_sha = _per_query_issues(
                    arrays_path,
                    expected_queries=queries,
                    corrupted=True,
                )
                issues.extend(array_issues)
                if clean_query_hashes.get(task) != path_sha:
                    issues.append(
                        f"{arrays_path}: query membership/order differs from clean"
                    )

    if set(condition_metrics) != expected_keys:
        issues.append(f"{spec.identifier}: condition metrics set is incomplete")
    if verify_artifacts:
        _validate_artifact_inventory(
            spec.output_dir,
            manifest.get("artifacts"),
            issues,
            spec.identifier,
        )
    return RobustnessValidation(
        spec=spec,
        issues=issues,
        manifest=manifest,
        run_config=run_config,
        clean_metrics=clean_metrics,
        condition_metrics=condition_metrics,
    )
