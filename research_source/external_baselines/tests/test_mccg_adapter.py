from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from external_baselines.fetch_and_verify_sources import IntegrityError
from external_baselines.mccg_adapter import (
    PUBLISHED_RECIPE,
    parse_training_history,
)


class MCCGAdapterTests(unittest.TestCase):
    def test_complete_training_log_parses_all_fixed_epochs(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "train.txt"
            lines: list[str] = []
            for epoch in range(PUBLISHED_RECIPE["epochs"]):
                lines.extend(
                    [
                        f"Epoch {epoch}/199",
                        "----------",
                        (
                            "train Loss: 1.0000 Cls_Loss:0.5000 "
                            "KL_Loss:0.0000 Triplet_Loss 0.5000 "
                            "Satellite_Acc: 0.7500  Drone_Acc: 0.7000"
                        ),
                    ]
                )
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            history = parse_training_history(path)
            self.assertEqual(len(history["records"]), 200)
            self.assertEqual(history["records"][-1]["epoch_index"], 199)

    def test_incomplete_training_log_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "train.txt"
            path.write_text(
                "Epoch 0/199\n"
                "train Loss: 1.0000 Cls_Loss:0.5000 KL_Loss:0.0000 "
                "Triplet_Loss 0.5000 Satellite_Acc: 0.7500  "
                "Drone_Acc: 0.7000\n",
                encoding="utf-8",
            )
            with self.assertRaises(IntegrityError):
                parse_training_history(path)

    def test_unpaired_epoch_and_metric_blocks_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "train.txt"
            epoch_lines = "".join(f"Epoch {epoch}/199\n" for epoch in range(200))
            metric_lines = "".join(
                "train Loss: 1.0000 Cls_Loss:0.5000 KL_Loss:0.0000 "
                "Triplet_Loss 0.5000 Satellite_Acc: 0.7500  "
                "Drone_Acc: 0.7000\n"
                for _ in range(200)
            )
            path.write_text(epoch_lines + metric_lines, encoding="utf-8")
            with self.assertRaises(IntegrityError):
                parse_training_history(path)


if __name__ == "__main__":
    unittest.main()
