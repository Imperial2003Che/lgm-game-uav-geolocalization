"""CPU-only regression tests for formal orchestration and exact baselines."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.io import savemat
import torch


DELIVERY_ROOT = Path(__file__).resolve().parents[2]


def load_script(name: str, path: Path):
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


RUNNER = load_script(
    "frozen_runner_test_module",
    DELIVERY_ROOT
    / "lgm_game_pytorch"
    / "experiments"
    / "run_frozen_formal_matrix.py",
)
VERIFIER_PATH = (
    DELIVERY_ROOT
    / "lgm_game_prototype"
    / "experiments"
    / "independent_verify_formal_baselines.py"
)
VERIFIER = load_script("exact_verifier_test_module", VERIFIER_PATH)
AGGREGATOR = load_script(
    "exact_aggregator_test_module",
    DELIVERY_ROOT
    / "lgm_game_prototype"
    / "experiments"
    / "aggregate_exact_official_baselines.py",
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_completed_run(
    root: Path,
) -> tuple[object, object, str]:
    evidence = root / "evidence.npz"
    evidence.write_bytes(b"evidence")
    dataset = RUNNER.DatasetSpec(
        "university1652",
        root.resolve(),
        evidence.resolve(),
        file_sha256(evidence),
    )
    spec = RUNNER.RunSpec(
        "formal_main",
        "university1652",
        "content",
        1,
        "resnet18",
        512,
        root / "manual_run",
        root / "manual_evaluation",
    )
    spec.run_dir.mkdir()
    (spec.run_dir / "best.pt").write_bytes(b"best")
    (spec.run_dir / "last.pt").write_bytes(b"last")
    formal_sha256 = "a" * 64
    immutable = {
        "schema_version": "formal-retrieval-v1",
        "command": "train",
        "dataset": "university1652",
        "data_root": str(root.resolve()),
        "model": {
            "variant": "content",
            "backbone": "resnet18",
            "embed_dim": 512,
            "dropout": 0.2,
            "image_size": 224,
            "resize_size": 256,
            "pretrained_initialization": {"enabled": False},
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
            "steps_per_epoch_actual": 3,
            "sampler_schedule_audited_epochs": 80,
            "sampler_step_count_fixed_across_epochs": True,
            "amp": True,
        },
        "selection": {"patience": 0},
        "seed": 1,
        "protocol": {
            "holdout_fraction": 0.0,
            "official_test_images_used_by_train_or_validation": 0,
        },
        "train_ids": ["0001"],
        "validation_ids": [],
        "sues_manifest": None,
        "evidence_caches": [
            {
                "path": str(evidence.resolve()),
                "sha256": file_sha256(evidence),
            }
        ],
        "image_inventory": {
            "mode": "content",
            "sha256": "c" * 64,
            "file_count": 2,
        },
        "code_sha256": formal_sha256,
    }
    config = {
        "immutable_config": immutable,
        "run_config_sha256": RUNNER.canonical_sha256(immutable),
    }
    (spec.run_dir / "run_config.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    history = [
        {
            "epoch": epoch,
            "optimizer_steps": 3,
            "validation_selection_mAP": None,
            "validation": {},
        }
        for epoch in range(80)
    ]
    (spec.run_dir / "history.json").write_text(
        json.dumps(history), encoding="utf-8"
    )
    artifacts = {
        name: {
            "bytes": (spec.run_dir / name).stat().st_size,
            "sha256": file_sha256(spec.run_dir / name),
        }
        for name in ("run_config.json", "history.json", "best.pt", "last.pt")
    }
    manifest = {
        "schema_version": "formal-retrieval-v1",
        "status": "completed",
        "epochs_completed": 80,
        "best_epoch": 79,
        "best_validation_mAP": None,
        "test_protocol_was_evaluated": False,
        "run_config_sha256": config["run_config_sha256"],
        "artifacts": artifacts,
    }
    manifest["payload_sha256"] = RUNNER.canonical_sha256(manifest)
    (spec.run_dir / "run_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return dataset, spec, formal_sha256


class RunnerAndExactBaselineTests(unittest.TestCase):
    def test_frozen_registry_is_exactly_36_plus_6(self) -> None:
        main = RUNNER.main_run_specs(
            DELIVERY_ROOT,
            RUNNER.DATASETS,
            RUNNER.MAIN_VARIANTS,
            RUNNER.MAIN_SEEDS,
        )
        sensitivity = RUNNER.sensitivity_run_specs(
            DELIVERY_ROOT, RUNNER.DATASETS
        )
        RUNNER.validate_registry(main, sensitivity)
        self.assertEqual(len(main), 36)
        self.assertEqual(len(sensitivity), 6)
        self.assertEqual(len({item.identifier for item in main + sensitivity}), 42)

    def test_completed_manual_run_skip_resume_and_evaluation_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dataset, spec, formal_sha256 = write_completed_run(root)
            self.assertEqual(
                RUNNER.training_completion_issues(
                    spec, dataset, formal_sha256
                ),
                [],
            )
            self.assertEqual(RUNNER.checkpoint_artifact_hash_issues(spec), [])
            ledger: dict[str, object] = {}
            ledger_path = root / "ledger.json"
            RUNNER.train_specs(
                [spec],
                {"university1652": dataset},
                root / "formal.py",
                root,
                ledger_path,
                ledger,
                formal_sha256,
            )
            record = ledger["runs"][spec.identifier]
            self.assertEqual(record["status"], "skipped_already_complete")
            self.assertEqual(len(record["events"]), 1)
            self.assertIn("university1652", ledger["dataset_fingerprints"])

            command = RUNNER.train_command(root / "formal.py", dataset, spec)
            self.assertEqual(command[-1], "last")
            dirty = RUNNER.RunSpec(
                "formal_main",
                "university1652",
                "style",
                1,
                "resnet18",
                512,
                root / "dirty",
                root / "dirty_evaluation",
            )
            dirty.run_dir.mkdir()
            (dirty.run_dir / "run_config.json").write_text(
                "{}", encoding="utf-8"
            )
            with self.assertRaisesRegex(RuntimeError, "refusing to overwrite"):
                RUNNER.train_command(root / "formal.py", dataset, dirty)

            incomplete = RUNNER.RunSpec(
                "formal_main",
                "university1652",
                "style",
                2,
                "resnet18",
                512,
                root / "incomplete",
                root / "incomplete_evaluation",
            )
            with self.assertRaisesRegex(
                RuntimeError, "every registered training run"
            ):
                RUNNER.evaluate_specs(
                    [spec, incomplete],
                    {"university1652": dataset},
                    root / "formal.py",
                    root,
                    ledger_path,
                    ledger,
                    formal_sha256,
                )

    def test_cpu_verification_is_not_accepted_as_exact_cuda_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "full_pytorch_result_lpn_drone_to_satellite.mat"
            features = np.eye(2, dtype=np.float32)
            savemat(
                source,
                {
                    "query_f": features,
                    "gallery_f": features,
                    "query_label": np.asarray([[1, 2]]),
                    "gallery_label": np.asarray([[1, 2]]),
                    "query_path": np.asarray(
                        [
                            r"C:\data\test\query_drone\0001\a.jpg",
                            r"C:\data\test\query_drone\0002\b.jpg",
                        ]
                    ),
                },
            )
            record = VERIFIER.verify_mat(
                source, 1, torch.device("cpu"), root / "query_metrics"
            )
            self.assertEqual(record["recall_at_1_percent"], 100.0)
            self.assertFalse(record["exact_public_evaluator_parity"])
            with np.load(record["query_metrics_path"], allow_pickle=False) as data:
                arrays = {
                    name: np.asarray(data[name]).copy() for name in data.files
                }
            self.assertEqual(
                arrays["official_trapezoidal_ap"].dtype, np.float64
            )
            with self.assertRaisesRegex(
                ValueError, "exact public-evaluator mode"
            ):
                AGGREGATOR.validate_record_and_arrays(record, arrays)

    def test_underflowed_exact_probabilities_are_bounds_not_zero(self) -> None:
        log10_p = AGGREGATOR.exact_two_sided_log10(0, 2000)
        rows = [{"ExactMcNemarLog10P": log10_p}]
        AGGREGATOR.holm_logspace(rows)
        exact = AGGREGATOR.probability_for_serialization(log10_p)
        self.assertIsInstance(exact, str)
        self.assertTrue(str(exact).startswith("<"))
        self.assertNotEqual(exact, 0)
        self.assertNotEqual(rows[0]["HolmAdjustedP"], 0)

    def test_metric_bound_tolerance_accepts_roundoff_without_clipping(self) -> None:
        values = np.asarray(
            [0.0, 0.5, 1.0 + np.finfo(np.float64).eps], dtype=np.float64
        )
        original = values.copy()
        AGGREGATOR.validate_unit_interval("ap", values)
        np.testing.assert_array_equal(values, original)
        with self.assertRaisesRegex(ValueError, "beyond atol"):
            AGGREGATOR.validate_unit_interval(
                "ap", np.asarray([1.0 + 2.0 * AGGREGATOR.UNIT_INTERVAL_ATOL])
            )


if __name__ == "__main__":
    unittest.main()
