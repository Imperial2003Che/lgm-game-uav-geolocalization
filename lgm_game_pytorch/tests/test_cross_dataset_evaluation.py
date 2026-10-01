from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

from experiments.run_cross_dataset_evaluation import (
    EXPECTED_EVIDENCE,
    EXPECTED_TASKS,
    TransferIntegrityError,
    recompute_metrics_from_arrays,
    sha256_file,
)
from experiments.run_transactions_t3_transfer_matrix import (
    EXPECTED_ROWS,
    T3IntegrityError,
    evaluation_command,
    evaluation_paths,
    validate_matrix,
)


class CrossDatasetEvaluationTests(unittest.TestCase):
    def _write_arrays(
        self,
        path: Path,
        include_all: bool = True,
        contradictory_top1: bool = False,
    ) -> None:
        payload = {
            "margin": np.asarray([0.9, 0.2, 0.1], dtype=np.float32),
            "correct": np.asarray([True, False, False], dtype=np.bool_),
            "per_query_official_trapezoid_AP": np.asarray(
                [1.0, 0.5, 0.25],
                dtype=np.float32,
            ),
            "reciprocal_rank": np.asarray(
                [1.0, 0.5, 0.1],
                dtype=np.float32,
            ),
            "query_paths": np.asarray(["q1.jpg", "q2.jpg", "q3.jpg"]),
            "query_labels": np.asarray(["1", "2", "3"]),
            "top1_gallery_indices": np.asarray([0, 1, 2], dtype=np.int64),
            "top1_gallery_paths": np.asarray(["g1.jpg", "g2.jpg", "g3.jpg"]),
            "top1_gallery_labels": np.asarray(["1", "9", "8"]),
        }
        if not include_all:
            payload.pop("query_labels")
        if contradictory_top1:
            payload["top1_gallery_labels"][0] = "not-query-1"
        np.savez_compressed(path, **payload)

    def test_expected_target_task_coverage_is_exact(self) -> None:
        self.assertEqual(len(EXPECTED_TASKS["university1652"]), 3)
        self.assertEqual(len(EXPECTED_TASKS["sues200"]), 8)
        self.assertEqual(len(set(EXPECTED_TASKS["sues200"])), 8)

    def test_registered_evidence_hashes_match_delivery_caches(self) -> None:
        evidence_root = Path(__file__).resolve().parents[1] / "evidence_cache"
        for dataset in ("university1652", "sues200"):
            stem = (
                "university1652_clip_image_evidence"
                if dataset == "university1652"
                else "sues200_clip_image_evidence"
            )
            cache = evidence_root / f"{stem}.npz"
            metadata = evidence_root / f"{stem}.meta.json"
            self.assertEqual(
                sha256_file(cache),
                EXPECTED_EVIDENCE[dataset]["sha256"],
            )
            self.assertEqual(
                sha256_file(metadata),
                EXPECTED_EVIDENCE[dataset]["meta_sha256"],
            )

    def test_metrics_are_recomputed_from_per_query_arrays(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "arrays.npz"
            self._write_arrays(path)
            metrics = recompute_metrics_from_arrays(path)
            self.assertAlmostEqual(metrics["r_at_1"], 1.0 / 3.0)
            self.assertAlmostEqual(metrics["r_at_5"], 2.0 / 3.0)
            self.assertAlmostEqual(metrics["r_at_10"], 1.0)
            self.assertAlmostEqual(metrics["official_trapezoid_mAP"], 1.75 / 3.0)
            self.assertAlmostEqual(metrics["MRR"], (1.0 + 0.5 + 0.1) / 3.0)

    def test_incomplete_per_query_schema_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "arrays.npz"
            self._write_arrays(path, include_all=False)
            with self.assertRaises(TransferIntegrityError):
                recompute_metrics_from_arrays(path)

    def test_contradictory_top1_semantics_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "arrays.npz"
            self._write_arrays(path, contradictory_top1=True)
            with self.assertRaises(TransferIntegrityError):
                recompute_metrics_from_arrays(path)

    def test_t3_matrix_registers_exact_bidirectional_product(self) -> None:
        matrix_path = (
            Path(__file__).resolve().parents[1]
            / "experiments"
            / "transactions_t3_transfer_matrix.json"
        )
        matrix = validate_matrix(matrix_path)
        observed = tuple(
            (
                row["evaluation_id"],
                row["source_dataset"],
                row["target_dataset"],
                row["variant"],
                row["seed"],
                row["expected_target_task_count"],
            )
            for row in matrix["evaluations"]
        )
        self.assertEqual(observed, EXPECTED_ROWS)

    def test_t3_matrix_semantic_change_fails_closed(self) -> None:
        matrix_path = (
            Path(__file__).resolve().parents[1]
            / "experiments"
            / "transactions_t3_transfer_matrix.json"
        )
        payload = json.loads(matrix_path.read_text(encoding="utf-8"))
        payload["evaluations"][0]["expected_target_task_count"] = 7
        with tempfile.TemporaryDirectory() as name:
            changed = Path(name) / "changed.json"
            changed.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(T3IntegrityError):
                validate_matrix(changed)

    def test_t3_command_uses_source_checkpoint_and_target_only_for_eval(self) -> None:
        delivery = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as name:
            temporary = Path(name)
            university_root = temporary / "university"
            sues_root = temporary / "sues"
            university_root.mkdir()
            sues_root.mkdir()
            args = argparse.Namespace(
                delivery_root=delivery,
                university_root=university_root,
                sues_root=sues_root,
                python=Path(sys.executable),
                device_index=0,
            )
            row = {
                "source_dataset": "university1652",
                "target_dataset": "sues200",
                "variant": "full",
                "seed": 3,
            }
            checkpoint, output, evidence = evaluation_paths(args, row)
            command = evaluation_command(
                args,
                row,
                checkpoint,
                output,
                evidence,
            )
            self.assertIn(
                str(
                    delivery
                    / "lgm_game_pytorch"
                    / "runs"
                    / "formal_main"
                    / "university1652"
                    / "full"
                    / "seed_3"
                    / "best.pt"
                ),
                command,
            )
            self.assertIn(str(sues_root.resolve()), command)
            self.assertIn("--target-dataset", command)
            self.assertNotIn("train", command)


if __name__ == "__main__":
    unittest.main()
