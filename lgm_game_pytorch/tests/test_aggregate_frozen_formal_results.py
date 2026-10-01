"""Synthetic, CPU-only tests for the frozen formal result aggregator."""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "experiments"
    / "aggregate_frozen_formal_results.py"
)
SPEC = importlib.util.spec_from_file_location("formal_aggregate", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot import {SCRIPT}")
aggregate_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = aggregate_module
SPEC.loader.exec_module(aggregate_module)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def with_payload_hash(value: dict[str, object]) -> dict[str, object]:
    result = dict(value)
    result["payload_sha256"] = aggregate_module.canonical_sha256(result)
    return result


def correct_pattern(variant: str, seed: int) -> np.ndarray:
    if variant == "visual":
        base = np.asarray([True, True, False, False, True, False])
    elif variant == "full":
        base = np.asarray([True, True, True, False, False, True])
    elif variant == "content":
        base = np.asarray([True, False, False, False, True, False])
    elif variant == "style":
        base = np.asarray([False, True, False, False, True, False])
    elif variant == "visual_content":
        base = np.asarray([True, True, True, False, True, False])
    else:
        base = np.asarray([True, True, False, True, True, False])
    return np.roll(base, seed - 1)


def make_fixture(root: Path) -> list[object]:
    protocol = root / "FORMAL_EXPERIMENT_PROTOCOL.md"
    runner = root / "lgm_game_pytorch" / "experiments" / "run_frozen_formal_matrix.py"
    formal = (
        root
        / "lgm_game_pytorch"
        / "lgm_game_pytorch"
        / "formal_retrieval.py"
    )
    protocol.parent.mkdir(parents=True, exist_ok=True)
    runner.parent.mkdir(parents=True, exist_ok=True)
    formal.parent.mkdir(parents=True, exist_ok=True)
    protocol.write_text("# frozen synthetic protocol\n", encoding="utf-8")
    runner.write_text("# synthetic runner\n", encoding="utf-8")
    formal.write_text("# synthetic formal implementation\n", encoding="utf-8")
    formal_sha = aggregate_module.sha256_file(formal)
    specs = aggregate_module.expected_specs(root)

    for spec in specs:
        spec.run_dir.mkdir(parents=True, exist_ok=True)
        spec.evaluation_dir.mkdir(parents=True, exist_ok=True)
        immutable = {
            "schema_version": "formal-retrieval-v1",
            "dataset": spec.dataset,
            "seed": spec.seed,
            "model": {
                "variant": spec.variant,
                "backbone": spec.backbone,
                "embed_dim": spec.embed_dim,
                "dropout": 0.2,
                "image_size": 224,
                "resize_size": 256,
                "pretrained_initialization": {
                    "enabled": spec.variant
                    in {"visual", "visual_content", "visual_style", "full"}
                },
            },
            "optimization": {
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
                "steps_per_epoch_actual": 2,
                "sampler_schedule_audited_epochs": 80,
                "sampler_step_count_fixed_across_epochs": True,
                "amp": True,
            },
            "protocol": {
                "holdout_fraction": 0.0,
                "official_test_images_used_by_train_or_validation": 0,
                "official_train_identity_count": (
                    701 if spec.dataset == "university1652" else 120
                ),
                "fit_identity_count": (
                    701 if spec.dataset == "university1652" else 120
                ),
                "fit_query_image_count": (
                    40513 if spec.dataset == "university1652" else 24000
                ),
            },
            "code_sha256": formal_sha,
        }
        config_sha = aggregate_module.canonical_sha256(immutable)
        run_config = {
            "immutable_config": immutable,
            "run_config_sha256": config_sha,
            "cli": {"val_fraction": 0.0, "patience": 0},
        }
        write_json(spec.run_dir / "run_config.json", run_config)
        history = [
            {
                "epoch": epoch,
                "optimizer_steps": 2,
                "validation_selection_mAP": None,
                "validation": {},
            }
            for epoch in range(80)
        ]
        write_json(spec.run_dir / "history.json", history)
        best = spec.run_dir / "best.pt"
        last = spec.run_dir / "last.pt"
        best.write_bytes(f"best:{spec.identifier}".encode())
        last.write_bytes(f"last:{spec.identifier}".encode())
        training_artifacts = {}
        for name in ("run_config.json", "history.json", "best.pt", "last.pt"):
            path = spec.run_dir / name
            training_artifacts[name] = {
                "sha256": aggregate_module.sha256_file(path),
                "bytes": path.stat().st_size,
            }
        run_manifest = with_payload_hash(
            {
                "schema_version": "formal-retrieval-v1",
                "status": "completed",
                "epochs_completed": 80,
                "best_epoch": 79,
                "best_validation_mAP": None,
                "run_config_sha256": config_sha,
                "test_protocol_was_evaluated": False,
                "artifacts": training_artifacts,
            }
        )
        write_json(spec.run_dir / "run_manifest.json", run_manifest)

        results = {}
        task_scale = {}
        array_paths = {}
        arrays_dir = spec.evaluation_dir / "per_query_arrays"
        arrays_dir.mkdir(parents=True, exist_ok=True)
        for task in aggregate_module.TASKS[spec.dataset]:
            count = 6
            correct = correct_pattern(spec.variant, spec.seed)
            query_paths = np.asarray(
                [f"{spec.dataset}/{task}/query_{index}.jpg" for index in range(count)]
            )
            labels = np.asarray([f"id_{index}" for index in range(count)])
            top1_labels = np.asarray(
                [
                    labels[index] if correct[index] else f"wrong_{index}"
                    for index in range(count)
                ]
            )
            reciprocal = np.where(correct, 1.0, 0.5).astype(np.float32)
            ap = np.where(correct, 1.0, 0.25).astype(np.float32)
            margin = np.linspace(0.1, 0.2, count, dtype=np.float32)
            array_path = arrays_dir / f"{task}_per_query.npz"
            np.savez_compressed(
                array_path,
                margin=margin,
                correct=correct,
                per_query_official_trapezoid_AP=ap,
                reciprocal_rank=reciprocal,
                query_paths=query_paths,
                query_labels=labels,
                top1_gallery_indices=np.arange(count, dtype=np.int64),
                top1_gallery_paths=np.asarray(
                    [f"gallery_{index}.jpg" for index in range(count)]
                ),
                top1_gallery_labels=top1_labels,
            )
            array_paths[f"per_query_arrays/{task}_per_query.npz"] = array_path
            results[task] = {
                "unit": "fraction",
                "queries": count,
                "gallery": 10,
                "query_identities": count,
                "gallery_identities": 10,
                "r_at_1": float(np.mean(correct)),
                "r_at_5": 1.0,
                "r_at_10": 1.0,
                "r_at_20": 1.0,
                "official_trapezoid_mAP": float(
                    np.mean(ap.astype(np.float64))
                ),
                "MRR": float(np.mean(reciprocal.astype(np.float64))),
                "mean_top1_margin": float(np.mean(margin.astype(np.float64))),
                "protocol": "synthetic official task",
            }
            task_scale[task] = {
                "queries": count,
                "gallery_images": 10,
                "query_identities": count,
                "gallery_identities": 10,
                "protocol": "synthetic official task",
            }
        metrics = {
            "schema_version": "formal-retrieval-v1",
            "unit": "fraction",
            "full_gallery": True,
            "results": results,
        }
        write_json(spec.evaluation_dir / "metrics.json", metrics)
        with (spec.evaluation_dir / "metrics.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.writer(handle)
            writer.writerow(["task", "r_at_1"])
            for task, values in results.items():
                writer.writerow([task, values["r_at_1"]])
        evaluation_artifacts = {}
        for relative, path in {
            "metrics.json": spec.evaluation_dir / "metrics.json",
            "metrics.csv": spec.evaluation_dir / "metrics.csv",
            **array_paths,
        }.items():
            evaluation_artifacts[relative] = {
                "sha256": aggregate_module.sha256_file(path),
                "bytes": path.stat().st_size,
            }
        evaluation_manifest = with_payload_hash(
            {
                "schema_version": "formal-retrieval-v1",
                "status": "completed",
                "dataset": spec.dataset,
                "checkpoint": {
                    "sha256": aggregate_module.sha256_file(best),
                    "training_run_config_sha256": config_sha,
                    "variant": spec.variant,
                    "selected_training_epoch": 79,
                },
                "protocol_membership_sha256": aggregate_module.canonical_sha256(
                    [spec.dataset, "synthetic official membership"]
                ),
                "task_scale": task_scale,
                "leakage_controls": {
                    "labels_and_splits_from_cache_used": False,
                    "labels_and_splits_derived_from_dataset_paths_and_official_manifest": True,
                    "each_image_encoded_independently": True,
                    "test_used_during_training_or_model_selection": False,
                    "all_official_queries_used": True,
                    "all_official_gallery_images_used": True,
                },
                "artifacts": evaluation_artifacts,
            }
        )
        write_json(
            spec.evaluation_dir / "evaluation_manifest.json",
            evaluation_manifest,
        )

    ledger = {
        "protocol_sha256": aggregate_module.sha256_file(protocol),
        "formal_script_sha256": formal_sha,
        "runner_sha256": aggregate_module.sha256_file(runner),
        "registered_main_run_count": 36,
        "registered_sensitivity_run_count": 6,
        "runs": {spec.identifier: {"status": "completed"} for spec in specs},
    }
    write_json(
        root
        / "lgm_game_pytorch"
        / "runs"
        / "frozen_formal_matrix_ledger.json",
        ledger,
    )
    return specs


class FormalAggregateTests(unittest.TestCase):
    def test_exact_mcnemar_never_formats_underflow_as_zero(self) -> None:
        log10_p = aggregate_module.exact_two_sided_mcnemar_log10(0, 2000)
        self.assertLess(log10_p, -300.0)
        self.assertEqual(aggregate_module.probability_text(log10_p), "<1e-300")
        rows = [
            {"exact_mcnemar_log10_p": log10_p},
            {"exact_mcnemar_log10_p": 0.0},
        ]
        aggregate_module.holm_logspace(rows)
        for row in rows:
            self.assertNotEqual(row["holm_adjusted_p"], "0")
            self.assertNotEqual(row["holm_adjusted_p"], "0.0")

    def test_full_matrix_and_partial_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "delivery"
            specs = make_fixture(root)
            output = root / "lgm_game_pytorch" / "results" / "aggregate_test"
            manifest = aggregate_module.aggregate(
                root,
                output,
                allow_partial=False,
                bootstrap_samples=10_000,
                bootstrap_seed=7,
            )
            self.assertEqual(manifest["status"], "complete")
            self.assertEqual(manifest["matrix"]["valid_main_runs"], 36)
            self.assertEqual(manifest["matrix"]["valid_sensitivity_runs"], 6)
            self.assertEqual(manifest["matrix"]["completed_pairwise_tests"], 33)
            self.assertFalse(
                manifest["task_policy"]["macro_average_rows_generated"]
            )
            with (output / "main_three_seed_mean_sample_sd.csv").open(
                "r", encoding="utf-8", newline=""
            ) as handle:
                summary = list(csv.DictReader(handle))
            self.assertEqual(len(summary), 66)
            self.assertTrue(all(row["n_seeds"] == "3" for row in summary))
            with (output / "visual_vs_full_exact_mcnemar_holm.csv").open(
                "r", encoding="utf-8", newline=""
            ) as handle:
                tests = list(csv.DictReader(handle))
            self.assertEqual(len(tests), 33)
            self.assertTrue(all(row["holm_family_size"] == "33" for row in tests))
            self.assertTrue(all(row["exact_mcnemar_p"] != "0" for row in tests))
            self.assertTrue(all(row["holm_adjusted_p"] != "0" for row in tests))

            missing_manifest = specs[-1].evaluation_dir / "evaluation_manifest.json"
            parked_manifest = missing_manifest.with_suffix(".json.parked")
            missing_manifest.replace(parked_manifest)
            with self.assertRaises(aggregate_module.MatrixIncompleteError):
                aggregate_module.aggregate(
                    root,
                    output,
                    allow_partial=False,
                    bootstrap_samples=10_000,
                    bootstrap_seed=7,
                )
            partial = aggregate_module.aggregate(
                root,
                output,
                allow_partial=True,
                bootstrap_samples=10_000,
                bootstrap_seed=7,
            )
            self.assertEqual(partial["status"], "partial_audit_only")
            self.assertEqual(partial["matrix"]["valid_sensitivity_runs"], 5)
            parked_manifest.replace(missing_manifest)


if __name__ == "__main__":
    unittest.main()
