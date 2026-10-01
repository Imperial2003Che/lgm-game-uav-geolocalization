from __future__ import annotations

from pathlib import Path
import json
import tempfile
import unittest

import numpy as np
import torch

from external_baselines.mccg_official_evaluation import mccg_postprocess
from external_baselines.official_descriptor_evaluation import (
    ALL_FITS_GATE_SCHEMA,
    DescriptorEvaluationError,
    DescriptorTask,
    begin_evaluation_output,
    canonical_sha256,
    complete_evaluation_output,
    evaluate_descriptor_task,
    recompute_metrics,
    sha256_file,
    validate_all_fits_gate,
    validate_completed_evaluation,
)
from external_baselines.qdfl_official_evaluation import qdfl_postprocess


class OfficialDescriptorEvaluationTests(unittest.TestCase):
    def test_full_query_metrics_and_arrays_are_recomputable(self) -> None:
        task = DescriptorTask(
            name="fixture",
            protocol="fixture full gallery",
            query_descriptors=np.asarray([[1.0, 0.0], [0.0, 1.0]]),
            query_labels=np.asarray(["a", "b"]),
            query_paths=np.asarray(["q/a.jpg", "q/b.jpg"]),
            gallery_descriptors=np.asarray(
                [[1.0, 0.0], [0.0, 1.0], [0.8, 0.2]]
            ),
            gallery_labels=np.asarray(["a", "b", "c"]),
            gallery_paths=np.asarray(["g/a.jpg", "g/b.jpg", "g/c.jpg"]),
        )
        metrics, arrays = evaluate_descriptor_task(task, chunk_size=1)
        self.assertAlmostEqual(metrics["r_at_1"], 1.0)
        self.assertAlmostEqual(metrics["official_trapezoid_mAP"], 1.0)
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "arrays.npz"
            np.savez_compressed(path, **arrays)
            observed = recompute_metrics(path)
            self.assertAlmostEqual(observed["r_at_1"], metrics["r_at_1"])
            self.assertAlmostEqual(
                observed["official_trapezoid_mAP"],
                metrics["official_trapezoid_mAP"],
            )

    def test_stable_tie_uses_frozen_gallery_order(self) -> None:
        task = DescriptorTask(
            name="tie",
            protocol="fixture",
            query_descriptors=np.asarray([[1.0, 0.0]]),
            query_labels=np.asarray(["a"]),
            query_paths=np.asarray(["q/a.jpg"]),
            gallery_descriptors=np.asarray([[1.0, 0.0], [1.0, 0.0]]),
            gallery_labels=np.asarray(["b", "a"]),
            gallery_paths=np.asarray(["g/b.jpg", "g/a.jpg"]),
        )
        metrics, arrays = evaluate_descriptor_task(task)
        self.assertAlmostEqual(metrics["r_at_1"], 0.0)
        self.assertEqual(arrays["top1_gallery_paths"].tolist(), ["g/b.jpg"])
        self.assertAlmostEqual(metrics["MRR"], 0.5)

    def test_missing_positive_fails_closed(self) -> None:
        task = DescriptorTask(
            name="missing",
            protocol="fixture",
            query_descriptors=np.asarray([[1.0, 0.0]]),
            query_labels=np.asarray(["a"]),
            query_paths=np.asarray(["q/a.jpg"]),
            gallery_descriptors=np.asarray([[0.0, 1.0]]),
            gallery_labels=np.asarray(["b"]),
            gallery_paths=np.asarray(["g/b.jpg"]),
        )
        with self.assertRaises(DescriptorEvaluationError):
            evaluate_descriptor_task(task)

    def test_squared_l2_preserves_public_qdfl_ranking(self) -> None:
        base = dict(
            name="distance",
            protocol="fixture",
            query_descriptors=np.asarray([[1.0, 0.0]], dtype=np.float32),
            query_labels=np.asarray(["a"]),
            query_paths=np.asarray(["q/a.jpg"]),
            gallery_descriptors=np.asarray(
                [[1.0, 0.0], [2.0, 0.0]],
                dtype=np.float32,
            ),
            gallery_labels=np.asarray(["a", "b"]),
            gallery_paths=np.asarray(["g/a.jpg", "g/b.jpg"]),
        )
        inner, _ = evaluate_descriptor_task(
            DescriptorTask(**base, score_type="inner_product")
        )
        squared_l2, arrays = evaluate_descriptor_task(
            DescriptorTask(**base, score_type="squared_l2")
        )
        self.assertEqual(inner["r_at_1"], 0.0)
        self.assertEqual(squared_l2["r_at_1"], 1.0)
        self.assertEqual(arrays["top1_gallery_paths"].tolist(), ["g/a.jpg"])

    def test_qdfl_upstream_flip_normalization_is_exact(self) -> None:
        output = torch.tensor(
            [[[3.0, 0.0], [4.0, 2.0]]],
            dtype=torch.float32,
        )
        mirrored = torch.tensor(
            [[[1.0, 3.0], [0.0, 4.0]]],
            dtype=torch.float32,
        )
        first = output / torch.linalg.vector_norm(
            output, dim=1, keepdim=True
        )
        expected = first + mirrored
        expected = expected / torch.linalg.vector_norm(
            expected, dim=1, keepdim=True
        )
        expected = expected.reshape(1, -1)
        observed = qdfl_postprocess(output, mirrored)
        self.assertTrue(torch.equal(observed, expected))

    def test_mccg_part_normalization_has_unit_flat_norm(self) -> None:
        output = torch.tensor(
            [[[3.0, 0.0], [4.0, 2.0]]],
            dtype=torch.float32,
        )
        observed = mccg_postprocess(output)
        self.assertEqual(tuple(observed.shape), (1, 4))
        self.assertAlmostEqual(
            float(torch.linalg.vector_norm(observed, dim=1)[0]),
            1.0,
            places=6,
        )

    def test_completed_bundle_is_hash_and_array_auditable(self) -> None:
        task = DescriptorTask(
            name="fixture",
            protocol="fixture",
            query_descriptors=np.asarray([[1.0, 0.0]]),
            query_labels=np.asarray(["a"]),
            query_paths=np.asarray(["q/a.jpg"]),
            gallery_descriptors=np.asarray([[1.0, 0.0], [0.0, 1.0]]),
            gallery_labels=np.asarray(["a", "b"]),
            gallery_paths=np.asarray(["g/a.jpg", "g/b.jpg"]),
        )
        result = evaluate_descriptor_task(task)
        with tempfile.TemporaryDirectory() as name:
            output = Path(name) / "evaluation"
            config_payload = {
                "schema_version": "fixture",
                "value": 1,
            }
            output, config_sha = begin_evaluation_output(
                output,
                {
                    **config_payload,
                    "payload_sha256": canonical_sha256(config_payload),
                },
            )
            complete_evaluation_output(
                output,
                evaluation_config_sha256=config_sha,
                method="Fixture",
                config_id="fixture",
                seed=1,
                results={"fixture": result},
                descriptor_fingerprints={
                    "query": {
                        "shape": [1, 2],
                        "dtype": "float32",
                        "sha256": "0" * 64,
                    }
                },
                elapsed_seconds=1.0,
            )
            manifest = validate_completed_evaluation(output)
            self.assertEqual(manifest["status"], "completed")
            arrays = output / "per_query_arrays" / "fixture_per_query.npz"
            with arrays.open("ab") as stream:
                stream.write(b"tamper")
            with self.assertRaises(DescriptorEvaluationError):
                validate_completed_evaluation(output)

    def test_all_fits_gate_binds_current_fit_and_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            manifest_path = root / "fit_manifest.json"
            checkpoint_path = root / "last.ckpt"
            manifest_path.write_text("manifest", encoding="utf-8")
            checkpoint_path.write_bytes(b"checkpoint")
            rows = []
            for index in range(7):
                if index == 0:
                    fit_path = manifest_path
                    checkpoint = checkpoint_path
                    run_id = "target/seed_1"
                else:
                    fit_path = root / f"fit_{index}.json"
                    checkpoint = root / f"checkpoint_{index}.pt"
                    fit_path.write_text(str(index), encoding="utf-8")
                    checkpoint.write_bytes(bytes([index]))
                    run_id = f"other_{index}/seed_1"
                rows.append(
                    {
                        "run_id": run_id,
                        "fit_manifest_path": str(fit_path.resolve()),
                        "fit_manifest_sha256": sha256_file(fit_path),
                        "checkpoint_path": str(checkpoint.resolve()),
                        "checkpoint_sha256": sha256_file(checkpoint),
                    }
                )
            payload = {
                "schema_version": ALL_FITS_GATE_SCHEMA,
                "status": "all_seven_fits_validated",
                "registered_run_count": 7,
                "runs": rows,
            }
            gate = {
                **payload,
                "payload_sha256": canonical_sha256(payload),
            }
            gate_path = root / "gate.json"
            gate_path.write_text(
                json.dumps(gate, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            _, selected = validate_all_fits_gate(
                gate_path,
                run_id="target/seed_1",
                fit_manifest_path=manifest_path,
                checkpoint_path=checkpoint_path,
            )
            self.assertEqual(selected["run_id"], "target/seed_1")
            checkpoint_path.write_bytes(b"changed")
            with self.assertRaises(DescriptorEvaluationError):
                validate_all_fits_gate(
                    gate_path,
                    run_id="target/seed_1",
                    fit_manifest_path=manifest_path,
                    checkpoint_path=checkpoint_path,
                )


if __name__ == "__main__":
    unittest.main()
