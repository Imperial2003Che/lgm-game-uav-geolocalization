from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from external_baselines.fetch_and_verify_sources import IntegrityError
from external_baselines.run_transactions_t1_matrix import (
    EXPECTED_RUNS,
    WEIGHT_FILES,
    validate_matrix,
    validate_profile,
)


class TransactionsT1MatrixTests(unittest.TestCase):
    @property
    def root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def test_registered_matrix_is_exactly_seven_prespecified_fits(self) -> None:
        matrix = validate_matrix(self.root / "transactions_t1_matrix.json")
        self.assertEqual(len(matrix["runs"]), 7)
        self.assertEqual(len(EXPECTED_RUNS), 7)
        self.assertEqual(
            {row["initialization_id"] for row in matrix["runs"]},
            set(WEIGHT_FILES),
        )

    def test_matrix_semantic_drift_fails_closed(self) -> None:
        matrix = json.loads(
            (self.root / "transactions_t1_matrix.json").read_text(encoding="utf-8")
        )
        matrix["runs"][0]["epochs"] = 1
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "matrix.json"
            path.write_text(json.dumps(matrix), encoding="utf-8")
            with self.assertRaises(IntegrityError):
                validate_matrix(path)

    def test_unfrozen_resource_template_cannot_launch_training(self) -> None:
        matrix = validate_matrix(self.root / "transactions_t1_matrix.json")
        with self.assertRaises(IntegrityError):
            validate_profile(
                self.root / "transactions_t1_resource_profile.template.json",
                matrix,
            )


if __name__ == "__main__":
    unittest.main()
