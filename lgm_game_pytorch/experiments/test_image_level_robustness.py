"""Lightweight CPU tests for the image-level robustness evaluator.

These tests use tiny generated RGB images and mock encoders.  They verify
determinism, pixel-space corruption, full query coverage, clean-gallery
ranking, per-query output, and the rule that a corrupted ``full`` query
recomputes content/style evidence.  They do not evaluate either real dataset.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

import numpy as np
from PIL import Image
import torch
from torch import nn
import torch.nn.functional as F
from torchvision import transforms


EXPERIMENTS_DIR = Path(__file__).resolve().parent
if str(EXPERIMENTS_DIR) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS_DIR))

import run_image_level_robustness as robustness


formal = robustness.formal


class TinyModel(nn.Module):
    def __init__(self, variant: str) -> None:
        super().__init__()
        self.variant = variant

    def encode_image(
        self,
        image: torch.Tensor,
        content_prob: torch.Tensor,
        style_prob: torch.Tensor,
    ) -> torch.Tensor:
        visual = image.mean(dim=(2, 3))
        if self.variant == "visual":
            return F.normalize(visual, dim=-1)
        combined = torch.cat(
            (visual, content_prob[:, :2], style_prob[:, :1]), dim=1
        )
        return F.normalize(combined, dim=-1)


class CountingClipEncoder:
    def __init__(self) -> None:
        self.calls = 0
        self.images = 0

    def infer(
        self, images: list[Image.Image]
    ) -> tuple[np.ndarray, np.ndarray]:
        self.calls += 1
        self.images += len(images)
        means = np.asarray(
            [
                np.asarray(image, dtype=np.float32).mean() / 255.0
                for image in images
            ],
            dtype=np.float32,
        )
        content = np.full((len(images), formal.CONTENT_DIM), 0.01, dtype=np.float32)
        style = np.full((len(images), formal.STYLE_DIM), 0.01, dtype=np.float32)
        content[:, 0] = 0.2 + means
        content[:, 1] = 0.8 - means
        style[:, 0] = 0.2 + means
        content /= content.sum(axis=1, keepdims=True)
        style /= style.sum(axis=1, keepdims=True)
        return content, style


class RobustnessTests(unittest.TestCase):
    def test_all_corruptions_are_deterministic_pixel_operations(self) -> None:
        y, x = np.mgrid[0:31, 0:47]
        pixels = np.stack(
            (
                (x * 5 + y * 2) % 256,
                (x * 3 + y * 7) % 256,
                (x * 11 + y) % 256,
            ),
            axis=-1,
        ).astype(np.uint8)
        image = Image.fromarray(pixels, mode="RGB")
        for spec in robustness.CORRUPTION_SPECS:
            first = robustness.apply_image_corruption(
                image, spec.name, 3, "query/example.jpg", 20260727
            )
            second = robustness.apply_image_corruption(
                image, spec.name, 3, "query/example.jpg", 20260727
            )
            self.assertEqual(first.mode, "RGB")
            self.assertEqual(first.size, image.size)
            self.assertTrue(
                np.array_equal(np.asarray(first), np.asarray(second)),
                msg=f"{spec.name} was not deterministic",
            )
            self.assertFalse(
                np.array_equal(np.asarray(first), np.asarray(image)),
                msg=f"{spec.name} did not alter decoded pixels",
            )

    def test_gaussian_noise_uses_path_specific_stream(self) -> None:
        image = Image.new("RGB", (24, 24), (100, 120, 140))
        first = robustness.apply_image_corruption(
            image, "gaussian_noise", 2, "a/query.jpg", 7
        )
        second = robustness.apply_image_corruption(
            image, "gaussian_noise", 2, "b/query.jpg", 7
        )
        self.assertFalse(np.array_equal(np.asarray(first), np.asarray(second)))

    def test_center_occlusion_area_matches_frozen_fraction(self) -> None:
        pixels = np.zeros((100, 200, 3), dtype=np.uint8)
        pixels[..., 0] = np.arange(200, dtype=np.uint8)[None, :]
        pixels[..., 1] = np.arange(100, dtype=np.uint8)[:, None]
        image = Image.fromarray(pixels, mode="RGB")
        output = robustness.apply_image_corruption(
            image, "center_occlusion", 3, "q.jpg", 1
        )
        changed = np.any(np.asarray(output) != pixels, axis=2)
        changed_fraction = float(changed.mean())
        self.assertAlmostEqual(changed_fraction, 0.20, delta=0.015)

    def test_split_ranking_uses_corrupt_query_and_clean_gallery_maps(self) -> None:
        base = Path("C:/synthetic")
        q_a = formal.EvidenceRecord(
            0, "query/a.jpg", base / "query/a.jpg", "a", "test", "drone", "q", ""
        )
        q_b = formal.EvidenceRecord(
            1, "query/b.jpg", base / "query/b.jpg", "b", "test", "drone", "q", ""
        )
        g_a = formal.EvidenceRecord(
            2, "gallery/a.jpg", base / "gallery/a.jpg", "a", "test", "satellite", "g", ""
        )
        g_b = formal.EvidenceRecord(
            3, "gallery/b.jpg", base / "gallery/b.jpg", "b", "test", "satellite", "g", ""
        )
        task = formal.RetrievalTask(
            "tiny",
            (q_a, q_b),
            (g_a, g_b),
            "synthetic unit-test protocol",
        )
        clean_gallery = {
            "gallery/a.jpg": np.asarray([1.0, 0.0], dtype=np.float32),
            "gallery/b.jpg": np.asarray([0.0, 1.0], dtype=np.float32),
        }
        corrupt_query = {
            "query/a.jpg": np.asarray([0.8, 0.2], dtype=np.float32),
            "query/b.jpg": np.asarray([0.1, 0.9], dtype=np.float32),
        }
        metrics, arrays = robustness.rank_task_split(
            task, corrupt_query, clean_gallery, chunk_size=1
        )
        self.assertEqual(metrics["queries"], 2)
        self.assertEqual(metrics["gallery"], 2)
        self.assertEqual(metrics["r_at_1"], 1.0)
        self.assertTrue(arrays["correct"].all())
        self.assertEqual(arrays["query_paths"].tolist(), ["query/a.jpg", "query/b.jpg"])

    def test_full_corrupted_encoding_recomputes_clip_for_every_query(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths: list[str] = []
            records: list[formal.EvidenceRecord] = []
            for index, colour in enumerate(((220, 20, 20), (20, 220, 20), (20, 20, 220))):
                relative = f"query/{index}.png"
                absolute = root / relative
                absolute.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGB", (16, 16), colour).save(absolute)
                paths.append(relative)
                records.append(
                    formal.EvidenceRecord(
                        evidence_index=index,
                        relative_path=relative,
                        absolute_path=absolute,
                        label=str(index),
                        partition="test",
                        view="drone",
                        role="query",
                        altitude="",
                    )
                )
            content = np.full(
                (len(records), formal.CONTENT_DIM),
                1.0 / formal.CONTENT_DIM,
                dtype=np.float32,
            )
            style = np.full(
                (len(records), formal.STYLE_DIM),
                1.0 / formal.STYLE_DIM,
                dtype=np.float32,
            )
            store = formal.EvidenceStore(
                paths=paths,
                content_probs=content,
                style_probs=style,
                content_candidates=tuple(str(index) for index in range(formal.CONTENT_DIM)),
                style_candidates=tuple(str(index) for index in range(formal.STYLE_DIM)),
                cache_descriptors=[],
            )
            clip = CountingClipEncoder()
            model = TinyModel("full")
            eval_transform = transforms.Compose(
                [transforms.Resize((12, 12)), transforms.ToTensor()]
            )
            encoded, coverage = robustness.encode_records_from_pixels(
                model=model,
                records=records,
                store=store,
                eval_transform=eval_transform,
                device=torch.device("cpu"),
                batch_size=2,
                image_workers=0,
                amp_enabled=False,
                corruption="brightness",
                severity_index=3,
                corruption_seed=20260727,
                clip_encoder=clip,
            )
            self.assertEqual(len(encoded), len(records))
            self.assertEqual(clip.images, len(records))
            self.assertEqual(clip.calls, 2)
            self.assertTrue(coverage["complete"])
            self.assertEqual(coverage["coverage_fraction"], 1.0)
            self.assertEqual(
                coverage["query_content_style_evidence_mode"],
                "recomputed_from_corrupted_rgb_pixels",
            )
            self.assertTrue(
                coverage["corruption_applied_before_all_model_preprocessing"]
            )

    def test_condition_artifacts_are_hashed_and_resumable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            condition_dir = Path(temporary) / "condition"
            condition = robustness._condition_payload(
                corruption="gaussian_blur",
                severity_index=1,
                corruption_seed=20260727,
            )
            clean_results = {
                "tiny": {
                    "unit": "fraction",
                    "queries": 2,
                    "gallery": 2,
                    "query_identities": 2,
                    "gallery_identities": 2,
                    "r_at_1": 1.0,
                    "r_at_5": 1.0,
                    "r_at_10": 1.0,
                    "r_at_20": 1.0,
                    "official_trapezoid_mAP": 1.0,
                    "MRR": 1.0,
                    "mean_top1_margin": 0.5,
                    "protocol": "synthetic",
                }
            }
            corrupted_results = {
                "tiny": {**clean_results["tiny"], "r_at_1": 0.5, "MRR": 0.75}
            }
            clean_arrays = {
                "tiny": {
                    "margin": np.asarray([0.5, 0.5], dtype=np.float32),
                    "correct": np.asarray([True, True]),
                    "first_positive_rank_zero_based": np.asarray([0, 0]),
                    "per_query_official_trapezoid_AP": np.asarray(
                        [1.0, 1.0], dtype=np.float32
                    ),
                    "reciprocal_rank": np.asarray([1.0, 1.0], dtype=np.float32),
                    "query_paths": np.asarray(["q/a.jpg", "q/b.jpg"]),
                    "query_labels": np.asarray(["a", "b"]),
                    "top1_gallery_indices": np.asarray([0, 1]),
                    "top1_gallery_paths": np.asarray(["g/a.jpg", "g/b.jpg"]),
                    "top1_gallery_labels": np.asarray(["a", "b"]),
                }
            }
            corrupted_arrays = {
                "tiny": {
                    **clean_arrays["tiny"],
                    "correct": np.asarray([True, False]),
                    "first_positive_rank_zero_based": np.asarray([0, 1]),
                    "reciprocal_rank": np.asarray([1.0, 0.5], dtype=np.float32),
                }
            }
            run_sha = "a" * 64
            robustness.write_condition(
                condition_dir,
                run_config_sha256=run_sha,
                condition=condition,
                results=corrupted_results,
                arrays=corrupted_arrays,
                query_coverage={
                    "complete": True,
                    "coverage_fraction": 1.0,
                    "expected_unique_images": 2,
                    "encoded_unique_images": 2,
                },
                clean_results=clean_results,
                clean_arrays=clean_arrays,
                elapsed_seconds=0.01,
            )
            loaded = robustness._load_completed_condition(
                condition_dir,
                run_config_sha256=run_sha,
                condition=condition,
            )
            self.assertIsNotNone(loaded)
            self.assertEqual(
                loaded["degradation_vs_clean"]["tiny"]["r_at_1"][
                    "relative_drop_percent"
                ],
                50.0,
            )
            arrays_path = (
                condition_dir / "per_query_arrays" / "tiny_per_query.npz"
            )
            with np.load(arrays_path, allow_pickle=False) as arrays:
                self.assertIn(
                    "top1_correctness_transition_corrupted_minus_clean",
                    arrays.files,
                )
                self.assertEqual(
                    arrays[
                        "top1_correctness_transition_corrupted_minus_clean"
                    ].tolist(),
                    [0, -1],
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
