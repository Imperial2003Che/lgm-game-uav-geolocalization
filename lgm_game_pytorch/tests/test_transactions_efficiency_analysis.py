from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np
import torch
from torch import nn

from experiments.transactions_efficiency_analysis import (
    count_conv_linear_macs,
    gallery_scaling_metrics,
    latency_summary,
    parameter_counts,
    registered_gallery_sizes,
    stable_gallery_permutation,
)
from experiments.run_transactions_formal_efficiency import (
    EXPECTED_COMPONENT_RUNS,
    registered_specs,
)


class TinyEncoder(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.conv = nn.Conv2d(3, 2, kernel_size=3, bias=False)
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.projection = nn.Linear(2, 4, bias=False)

    def encode(self, image: torch.Tensor) -> torch.Tensor:
        value = self.pool(self.conv(image)).flatten(1)
        return self.projection(value)


class TransactionsEfficiencyAnalysisTests(unittest.TestCase):
    def test_gallery_hash_order_is_path_stable(self) -> None:
        first = ["g/c.jpg", "g/a.jpg", "g/b.jpg"]
        second = ["g/b.jpg", "g/c.jpg", "g/a.jpg"]
        first_order = stable_gallery_permutation(first)
        second_order = stable_gallery_permutation(second)
        self.assertEqual(
            [first[index] for index in first_order],
            [second[index] for index in second_order],
        )

    def test_positive_preserving_gallery_metrics_are_complete(self) -> None:
        scores = np.asarray(
            [
                [0.9, 0.8, 0.2, 0.1],
                [0.7, 0.6, 0.95, 0.1],
            ],
            dtype=np.float32,
        )
        result = gallery_scaling_metrics(
            scores,
            query_labels=["a", "b"],
            gallery_labels=["a", "a", "b", "c"],
            gallery_paths=["g0.jpg", "g1.jpg", "g2.jpg", "g3.jpg"],
            requested_gallery_size=2,
        )
        self.assertEqual(result["queries"], 2)
        self.assertEqual(result["minimum_effective_gallery_size"], 2)
        self.assertEqual(result["maximum_effective_gallery_size"], 2)
        self.assertAlmostEqual(result["r_at_1"], 1.0)
        self.assertAlmostEqual(result["official_trapezoid_mAP"], 1.0)
        self.assertFalse(result["full_gallery"])

    def test_registered_gallery_sizes_include_full_once(self) -> None:
        self.assertEqual(registered_gallery_sizes(200), (100, None))
        self.assertEqual(
            registered_gallery_sizes(12000),
            (100, 250, 500, 1000, 5000, 10000, None),
        )

    def test_parameter_and_mac_counts_are_exact_for_tiny_encoder(self) -> None:
        model = TinyEncoder().eval()
        counts = parameter_counts(model)
        self.assertEqual(counts["total_parameters"], 3 * 2 * 3 * 3 + 2 * 4)
        image = torch.ones((1, 3, 5, 5), dtype=torch.float32)
        macs = count_conv_linear_macs(model, lambda: model.encode(image))
        # Conv: 1*2*3*3 outputs, each with 3*3*3 MACs. Linear: 4*2.
        self.assertEqual(macs["MACs_per_batch"], 18 * 27 + 8)
        self.assertEqual(macs["descriptor_dimension"], 4)

    def test_latency_summary_reports_median_and_iqr(self) -> None:
        summary = latency_summary([1.0, 2.0, 3.0, 4.0])
        self.assertAlmostEqual(summary["median"], 2.5)
        self.assertAlmostEqual(summary["q1"], 1.75)
        self.assertAlmostEqual(summary["q3"], 3.25)
        self.assertAlmostEqual(summary["IQR"], 1.5)

    def test_formal_t6_registry_is_exactly_four_seed1_components(self) -> None:
        delivery = Path(__file__).resolve().parents[2]
        specs = registered_specs(delivery)
        self.assertEqual(len(specs), EXPECTED_COMPONENT_RUNS)
        self.assertEqual(
            {
                (spec.dataset, spec.variant, spec.seed)
                for spec in specs
            },
            {
                (dataset, variant, 1)
                for dataset in ("university1652", "sues200")
                for variant in ("visual", "full")
            },
        )


if __name__ == "__main__":
    unittest.main()
