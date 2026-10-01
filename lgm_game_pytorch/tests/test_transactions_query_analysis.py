from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import numpy as np

from experiments.transactions_query_analysis import (
    QueryAnalysisError,
    QueryArrays,
    align_visual_full,
    apply_holm_logspace,
    calibration_summary,
    exact_two_sided_mcnemar_log10,
    load_query_arrays,
    native_risk_coverage,
    normalized_entropy,
    paired_coverage_comparison,
    quartile_assignment,
    semantic_nearest_labels,
    stratum_summary,
)
from experiments.run_transactions_query_analysis import (
    EXPECTED_T4_ROWS,
    EXPECTED_T5_COMPARISONS,
    EXPECTED_T5_NATIVE_ROWS,
    _bootstrap_seed,
    _strata_for_pair,
    registered_specs,
)


def query_arrays(
    *,
    paths: tuple[str, ...] = ("q0.jpg", "q1.jpg", "q2.jpg", "q3.jpg"),
    correct: tuple[bool, ...] = (True, False, True, False),
    margin: tuple[float, ...] = (0.8, 0.7, 0.2, 0.1),
) -> QueryArrays:
    labels = np.asarray(["0", "1", "2", "3"], dtype=str)
    top1_labels = np.asarray(
        [
            label if outcome else f"wrong-{label}"
            for label, outcome in zip(labels, correct, strict=True)
        ],
        dtype=str,
    )
    reciprocal = np.asarray(
        [1.0 if outcome else 0.5 for outcome in correct],
        dtype=np.float64,
    )
    return QueryArrays(
        paths=np.asarray(paths, dtype=str),
        labels=labels,
        correct=np.asarray(correct, dtype=np.bool_),
        official_ap=np.asarray(
            [1.0 if outcome else 0.4 for outcome in correct],
            dtype=np.float64,
        ),
        reciprocal_rank=reciprocal,
        margin=np.asarray(margin, dtype=np.float64),
        top1_gallery_indices=np.arange(4, dtype=np.int64),
        top1_gallery_paths=np.asarray(
            [f"g{index}.jpg" for index in range(4)],
            dtype=str,
        ),
        top1_gallery_labels=top1_labels,
    )


class TransactionsQueryAnalysisTests(unittest.TestCase):
    def test_load_and_align_arrays_are_semantic_and_order_safe(self) -> None:
        fixture = query_arrays()
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "arrays.npz"
            np.savez_compressed(
                path,
                margin=fixture.margin.astype(np.float32),
                correct=fixture.correct,
                per_query_official_trapezoid_AP=fixture.official_ap.astype(
                    np.float32
                ),
                reciprocal_rank=fixture.reciprocal_rank.astype(np.float32),
                query_paths=fixture.paths,
                query_labels=fixture.labels,
                top1_gallery_indices=fixture.top1_gallery_indices,
                top1_gallery_paths=fixture.top1_gallery_paths,
                top1_gallery_labels=fixture.top1_gallery_labels,
            )
            loaded = load_query_arrays(path)
            order = np.asarray([2, 0, 3, 1], dtype=np.int64)
            shuffled = loaded.reordered(order)
            visual, realigned = align_visual_full(loaded, shuffled)
            self.assertEqual(visual.paths.tolist(), realigned.paths.tolist())
            self.assertEqual(visual.labels.tolist(), realigned.labels.tolist())

    def test_load_rejects_contradictory_correctness(self) -> None:
        fixture = query_arrays()
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "arrays.npz"
            labels = fixture.top1_gallery_labels.copy()
            labels[0] = "wrong"
            np.savez_compressed(
                path,
                margin=fixture.margin,
                correct=fixture.correct,
                per_query_official_trapezoid_AP=fixture.official_ap,
                reciprocal_rank=fixture.reciprocal_rank,
                query_paths=fixture.paths,
                query_labels=fixture.labels,
                top1_gallery_indices=fixture.top1_gallery_indices,
                top1_gallery_paths=fixture.top1_gallery_paths,
                top1_gallery_labels=labels,
            )
            with self.assertRaises(QueryAnalysisError):
                load_query_arrays(path)

    def test_entropy_and_quartiles_use_registered_definitions(self) -> None:
        probabilities = np.asarray(
            [
                [1.0, 0.0, 0.0, 0.0],
                [0.25, 0.25, 0.25, 0.25],
            ],
            dtype=np.float64,
        )
        entropy = normalized_entropy(probabilities)
        self.assertAlmostEqual(entropy[0], 0.0)
        self.assertAlmostEqual(entropy[1], 1.0)
        groups, cuts = quartile_assignment(
            np.asarray([0.0, 1.0, 2.0, 3.0], dtype=np.float64)
        )
        self.assertEqual(groups.tolist(), [0, 1, 2, 3])
        np.testing.assert_allclose(cuts, [0.75, 1.5, 2.25])

    def test_semantic_nearest_neighbour_is_deterministic(self) -> None:
        query_content = np.asarray([[0.9, 0.1], [0.1, 0.9]])
        query_style = np.asarray([[0.8, 0.2], [0.2, 0.8]])
        gallery_content = np.asarray([[1.0, 0.0], [0.0, 1.0]])
        gallery_style = np.asarray([[1.0, 0.0], [0.0, 1.0]])
        labels = semantic_nearest_labels(
            query_content,
            query_style,
            gallery_content,
            gallery_style,
            ["a", "b"],
            chunk_size=1,
        )
        self.assertEqual(labels.tolist(), ["a", "b"])

    def test_stratum_summary_reports_paired_effects(self) -> None:
        visual = query_arrays()
        full = query_arrays(correct=(True, True, True, False))
        summary = stratum_summary(
            visual,
            full,
            np.asarray([True, True, True, True]),
            minimum_queries=4,
            bootstrap_samples=200,
            bootstrap_seed=7,
        )
        self.assertTrue(summary["performance_claim_eligible"])
        self.assertAlmostEqual(
            summary["metrics"]["r_at_1"]["full_minus_visual"],
            0.25,
        )
        self.assertEqual(
            summary["top1_discordance"]["full_only_correct"],
            1,
        )
        self.assertEqual(
            summary["top1_discordance"]["visual_only_correct"],
            0,
        )
        withheld = stratum_summary(
            visual,
            full,
            np.asarray([True, True, True, True]),
            minimum_queries=100,
            bootstrap_samples=200,
            bootstrap_seed=7,
        )
        self.assertFalse(withheld["performance_claim_eligible"])
        self.assertIsNone(
            withheld["metrics"]["r_at_1"]["paired_bootstrap_95ci"]
        )
        self.assertIsNone(
            withheld["top1_discordance"][
                "exact_two_sided_mcnemar_log10_p"
            ]
        )

    def test_calibration_uses_fixed_theoretical_margin_scale(self) -> None:
        summary = calibration_summary(
            np.asarray([0.2, 1.8]),
            np.asarray([False, True]),
            bins=2,
        )
        self.assertAlmostEqual(summary["ECE"], 0.1)
        self.assertFalse(summary["fitted_calibration_parameter"])

    def test_risk_coverage_is_margin_sorted_and_complete(self) -> None:
        result = native_risk_coverage(
            np.asarray([0.1, 0.9, 0.8, 0.2]),
            np.asarray([False, True, True, False]),
            coverages=(0.5, 1.0),
        )
        self.assertAlmostEqual(result["rows"][0]["selective_r_at_1"], 1.0)
        self.assertAlmostEqual(result["rows"][1]["selective_r_at_1"], 0.5)

    def test_paired_coverage_and_holm_are_explicit(self) -> None:
        visual = query_arrays()
        full = query_arrays(
            correct=(True, True, False, False),
            margin=(0.9, 0.8, 0.2, 0.1),
        )
        row = paired_coverage_comparison(visual, full, 0.5)
        self.assertEqual(row["selected_queries_per_variant"], 2)
        tests = [
            {"raw": exact_two_sided_mcnemar_log10(0, 3)},
            {"raw": exact_two_sided_mcnemar_log10(1, 2)},
        ]
        apply_holm_logspace(
            tests,
            log10_key="raw",
            family_name="fixture",
        )
        self.assertTrue(all(item["holm_family_size"] == 2 for item in tests))
        self.assertTrue(
            all(item["holm_adjusted_log10_p"] <= 0.0 for item in tests)
        )

    def test_real_runner_registry_is_exactly_twelve_source_runs(self) -> None:
        delivery = Path(__file__).resolve().parents[2]
        specs = registered_specs(delivery)
        self.assertEqual(len(specs), 12)
        self.assertEqual(
            {
                (spec.dataset, spec.variant, spec.seed)
                for spec in specs
            },
            {
                (dataset, variant, seed)
                for dataset in ("university1652", "sues200")
                for variant in ("visual", "full")
                for seed in (1, 2, 3)
            },
        )
        self.assertEqual(EXPECTED_T4_ROWS, 462)
        self.assertEqual(EXPECTED_T5_NATIVE_ROWS, 66)
        self.assertEqual(EXPECTED_T5_COMPARISONS, 132)

    def test_t4_factor_expansion_is_exact_and_deterministic(self) -> None:
        visual = query_arrays()
        full = query_arrays(correct=(True, True, True, False))
        evidence = {
            "content_entropy": np.asarray([0.0, 0.3, 0.6, 0.9]),
            "style_entropy": np.asarray([0.1, 0.4, 0.7, 1.0]),
            "semantic_nearest_labels": np.asarray(
                ["0", "different", "2", "different"],
                dtype=str,
            ),
        }
        rows = _strata_for_pair(
            "university1652",
            "fixture_task",
            1,
            visual,
            full,
            evidence,
            bootstrap_samples=50,
            bootstrap_seed=9,
            minimum_queries=1,
        )
        self.assertEqual(len(rows), 14)
        self.assertEqual(
            {row["factor"] for row in rows},
            {
                "content_entropy_quartile",
                "style_entropy_quartile",
                "visual_margin_quartile",
                "visual_semantic_top1_identity_agreement",
            },
        )
        self.assertEqual(
            _bootstrap_seed(9, "d", "t", 1, "f", "l"),
            _bootstrap_seed(9, "d", "t", 1, "f", "l"),
        )


if __name__ == "__main__":
    unittest.main()
