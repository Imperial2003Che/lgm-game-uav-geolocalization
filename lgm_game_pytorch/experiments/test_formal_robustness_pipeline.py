"""CPU-only structural tests for orchestration, validation, aggregation, and plots."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

import numpy as np


EXPERIMENTS_DIR = Path(__file__).resolve().parent
if str(EXPERIMENTS_DIR) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS_DIR))

import aggregate_formal_robustness as aggregate
import formal_robustness_common as common
import run_frozen_robustness_matrix as orchestrator
import run_image_level_robustness as evaluator


def metric_row(queries: int, gallery: int, value: float) -> dict[str, object]:
    return {
        "unit": "fraction",
        "queries": queries,
        "gallery": gallery,
        "query_identities": queries,
        "gallery_identities": gallery,
        "r_at_1": value,
        "r_at_5": min(1.0, value + 0.10),
        "r_at_10": min(1.0, value + 0.15),
        "r_at_20": min(1.0, value + 0.20),
        "official_trapezoid_mAP": min(1.0, value + 0.05),
        "MRR": min(1.0, value + 0.03),
        "mean_top1_margin": 0.2,
        "protocol": "synthetic structure test",
    }


def task_arrays(task: str, queries: int) -> dict[str, np.ndarray]:
    paths = np.asarray([f"{task}/query_{index}.jpg" for index in range(queries)])
    labels = np.asarray([f"id_{index}" for index in range(queries)])
    return {
        "margin": np.full(queries, 0.2, dtype=np.float32),
        "correct": np.ones(queries, dtype=np.bool_),
        "first_positive_rank_zero_based": np.zeros(queries, dtype=np.int64),
        "per_query_official_trapezoid_AP": np.ones(queries, dtype=np.float32),
        "reciprocal_rank": np.ones(queries, dtype=np.float32),
        "query_paths": paths,
        "query_labels": labels,
        "top1_gallery_indices": np.zeros(queries, dtype=np.int64),
        "top1_gallery_paths": np.asarray(
            [f"{task}/gallery_0.jpg"] * queries
        ),
        "top1_gallery_labels": labels,
    }


def make_synthetic_tree(
    root: Path,
    *,
    variant: str = "visual",
    task: str = "synthetic_task",
    queries: int = 2,
    gallery: int = 3,
) -> tuple[common.RobustnessRunSpec, dict[str, tuple[int, int]]]:
    data_root = root / "data"
    data_root.mkdir(parents=True)
    evidence = root / "evidence.npz"
    evidence.write_bytes(b"synthetic evidence")
    checkpoint = root / "training" / "best.pt"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_bytes(b"synthetic checkpoint")
    training_manifest = checkpoint.parent / "run_manifest.json"
    common.atomic_json(training_manifest, {"status": "synthetic"})
    output_dir = root / "robustness"
    spec = common.RobustnessRunSpec(
        dataset="university1652",
        variant=variant,
        data_root=data_root,
        evidence=evidence,
        checkpoint=checkpoint,
        output_dir=output_dir,
    )
    task_scale = {task: (queries, gallery)}
    immutable = {
        "schema_version": evaluator.SCHEMA_VERSION,
        "dataset": spec.dataset,
        "checkpoint": {
            "variant": variant,
            "seed": 1,
            "checkpoint_sha256": common.sha256_file(checkpoint),
        },
        "official_task_scale": {
            task: {
                "queries": queries,
                "gallery": gallery,
                "protocol": "synthetic",
            }
        },
        "unique_query_images": queries,
        "unique_clean_gallery_images": gallery,
        "corruption_matrix": evaluator.corruption_matrix_payload(),
        "corruption_seed": evaluator.DEFAULT_CORRUPTION_SEED,
        "sources": {
            "robustness_evaluator": {
                "sha256": common.sha256_file(Path(evaluator.__file__).resolve())
            },
            "formal_retrieval": {"sha256": "1" * 64},
            "frozen_protocol": {"sha256": "2" * 64},
        },
    }
    run_sha = common.canonical_sha256(immutable)
    common.atomic_json(
        output_dir / "run_config.json",
        {
            "created_utc": evaluator.formal.utc_now(),
            "run_config_sha256": run_sha,
            "immutable_config": immutable,
        },
    )
    clean_results = {task: metric_row(queries, gallery, 0.80)}
    clean_arrays = {task: task_arrays(task, queries)}
    clean_coverage = {
        "complete": True,
        "coverage_fraction": 1.0,
        "expected_unique_images": queries,
        "encoded_unique_images": queries,
        "path_membership_sha256": "3" * 64,
        "encoded_feature_sha256": "4" * 64,
        "query_content_style_evidence_mode": "clean_cache",
        "corruption_applied_before_all_model_preprocessing": False,
    }
    evaluator.write_condition(
        output_dir / "clean",
        run_config_sha256=run_sha,
        condition=evaluator._condition_payload(
            corruption=None,
            severity_index=None,
            corruption_seed=evaluator.DEFAULT_CORRUPTION_SEED,
        ),
        results=clean_results,
        arrays=clean_arrays,
        query_coverage=clean_coverage,
        clean_results=None,
        clean_arrays=None,
        elapsed_seconds=0.01,
    )
    for condition in common.expected_condition_payloads(evaluator):
        severity = int(condition["severity_index"])
        corrupted_results = {
            task: metric_row(
                queries, gallery, 0.80 - 0.02 * severity
            )
        }
        corrupted_arrays = {task: task_arrays(task, queries)}
        coverage = {
            **clean_coverage,
            "query_content_style_evidence_mode": (
                "recomputed_from_corrupted_rgb_pixels"
                if variant == "full"
                else "not_used_by_visual_variant"
            ),
            "corruption_applied_before_all_model_preprocessing": True,
        }
        evaluator.write_condition(
            common.condition_directory(output_dir, condition),
            run_config_sha256=run_sha,
            condition=condition,
            results=corrupted_results,
            arrays=corrupted_arrays,
            query_coverage=coverage,
            clean_results=clean_results,
            clean_arrays=clean_arrays,
            elapsed_seconds=0.01,
        )
    manifest = {
        "schema_version": evaluator.SCHEMA_VERSION,
        "status": "completed",
        "completed_utc": evaluator.formal.utc_now(),
        "run_config_sha256": run_sha,
        "dataset": spec.dataset,
        "variant": variant,
        "checkpoint": {
            "variant": variant,
            "seed": 1,
            "checkpoint_sha256": common.sha256_file(checkpoint),
            "training_manifest_path": str(training_manifest.resolve()),
        },
        "expected_corruption_conditions": 30,
        "completed_corruption_conditions": 30,
        "condition_count_complete": True,
        "clean_query_coverage": clean_coverage,
        "clean_gallery_coverage": {
            **clean_coverage,
            "expected_unique_images": gallery,
            "encoded_unique_images": gallery,
        },
        "full_gallery": True,
        "clean_gallery_for_every_condition": True,
        "all_official_queries_for_every_condition": True,
        "feature_level_corruption_used": False,
        "artifacts": evaluator._artifact_inventory(
            output_dir, {"robustness_manifest.json", "run.log"}
        ),
    }
    manifest["payload_sha256"] = common.canonical_sha256(manifest)
    common.atomic_json(output_dir / "robustness_manifest.json", manifest)
    return spec, task_scale


def in_memory_validations() -> list[common.RobustnessValidation]:
    validations: list[common.RobustnessValidation] = []
    for dataset in common.DATASETS:
        for variant in common.VARIANTS:
            spec = common.RobustnessRunSpec(
                dataset=dataset,
                variant=variant,
                data_root=Path("."),
                evidence=Path("evidence"),
                checkpoint=Path("checkpoint"),
                output_dir=Path("output"),
            )
            task_scale = common.OFFICIAL_TASK_SCALE[dataset]
            clean_results = {
                task: metric_row(queries, gallery, 0.80)
                for task, (queries, gallery) in task_scale.items()
            }
            conditions: dict[tuple[str, int], dict[str, object]] = {}
            for condition in common.expected_condition_payloads(evaluator):
                severity = int(condition["severity_index"])
                results = {
                    task: metric_row(
                        queries,
                        gallery,
                        0.80 - 0.02 * severity - (0.01 if variant == "visual" else 0.0),
                    )
                    for task, (queries, gallery) in task_scale.items()
                }
                degradation = aggregate.evaluator.compute_degradation(
                    clean_results, results
                )
                conditions[(condition["name"], severity)] = {
                    "results": results,
                    "degradation_vs_clean": degradation,
                }
            validations.append(
                common.RobustnessValidation(
                    spec=spec,
                    issues=[],
                    manifest={
                        "checkpoint": {"checkpoint_sha256": "a" * 64},
                        "run_config_sha256": "b" * 64,
                    },
                    run_config={
                        "immutable_config": {
                            "sources": {
                                "robustness_evaluator": {"sha256": "c" * 64},
                                "frozen_protocol": {"sha256": "d" * 64},
                            }
                        }
                    },
                    clean_metrics={"results": clean_results},
                    condition_metrics=conditions,
                )
            )
    return validations


class FormalRobustnessPipelineTests(unittest.TestCase):
    def test_registry_and_command_are_exactly_four_sequential_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            delivery = root / "delivery"
            (delivery / "lgm_game_pytorch").mkdir(parents=True)
            specs = common.build_run_specs(
                delivery, root / "university", root / "sues"
            )
            self.assertEqual(len(specs), 4)
            self.assertEqual(
                {(spec.dataset, spec.variant) for spec in specs},
                {
                    ("university1652", "visual"),
                    ("university1652", "full"),
                    ("sues200", "visual"),
                    ("sues200", "full"),
                },
            )
            args = orchestrator.parse_args(
                [
                    "--delivery-root",
                    str(delivery),
                    "--university-root",
                    str(root / "university"),
                    "--sues-root",
                    str(root / "sues"),
                ]
            )
            command = orchestrator.robustness_command(
                args,
                specs[0],
                Path(evaluator.__file__),
                root / "manifest.yaml",
            )
            self.assertIn("--checkpoint", command)
            self.assertIn("--corruption-seed", command)
            self.assertIn("--clip-local-files-only", command)
            self.assertNotIn("&", command)

    def test_completed_tree_passes_and_missing_condition_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            spec, task_scale = make_synthetic_tree(Path(temporary))
            validation = common.validate_completed_robustness(
                spec,
                evaluator,
                verify_artifacts=True,
                verify_per_query=True,
                expected_task_scale=task_scale,
                expected_evaluator_sha256=common.sha256_file(
                    Path(evaluator.__file__).resolve()
                ),
            )
            self.assertTrue(validation.complete, msg=validation.issues[:10])
            missing = (
                spec.output_dir
                / "conditions"
                / "rotation"
                / "severity_05"
                / "condition_manifest.json"
            )
            missing.unlink()
            rejected = common.validate_completed_robustness(
                spec,
                evaluator,
                verify_artifacts=True,
                verify_per_query=False,
                expected_task_scale=task_scale,
                expected_evaluator_sha256=common.sha256_file(
                    Path(evaluator.__file__).resolve()
                ),
            )
            self.assertFalse(rejected.complete)
            self.assertTrue(
                any(
                    "condition directories" in issue
                    or "cannot read manifest" in issue
                    or "missing artifact" in issue
                    for issue in rejected.issues
                )
            )

    def test_flattening_is_task_separated_and_complete(self) -> None:
        validations = in_memory_validations()
        rows = aggregate.flatten_validations(validations)
        expected = (2 * 3 + 2 * 8) * 30 * 6
        self.assertEqual(len(rows), expected)
        self.assertEqual(len({row["task"] for row in rows}), 11)
        self.assertTrue(all("task" in row for row in rows))
        self.assertNotIn("macro", {row["task"] for row in rows})

    def test_latex_and_python_figure_have_source_traceability(self) -> None:
        validations = in_memory_validations()
        rows = aggregate.flatten_validations(validations)
        task = "university1652_drone_to_satellite"
        source = aggregate.figure_source_rows(
            rows, "university1652", task, "r_at_1"
        )
        self.assertEqual(len(source), 60)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tex = aggregate.write_task_latex(
                rows, root / "tables", "r_at_1"
            )
            self.assertTrue(tex.is_file())
            text = tex.read_text(encoding="utf-8")
            self.assertEqual(text.count(r"\begin{table*}"), 11)
            outputs = aggregate.plot_task_metric(
                source,
                root / "figure",
                dataset="university1652",
                task=task,
                metric="r_at_1",
                dpi=300,
            )
            self.assertEqual(set(outputs), {"pdf", "svg", "png"})
            self.assertTrue(all(path.stat().st_size > 0 for path in outputs.values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
