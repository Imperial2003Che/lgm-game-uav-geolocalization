from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lgm_game_pytorch import formal_retrieval as core
from experiments.run_sues_heldout_fit import (
    filter_heldout_records,
    make_protocol_builder,
    membership_payload,
    validate_frozen_core,
)
from experiments.run_transactions_t2_heldout_matrix import (
    catalog_training_files,
    inventory_from_catalog,
    validate_matrix,
)


def record(
    path: str,
    label: str,
    view: str,
    altitude: str,
    index: int,
) -> core.EvidenceRecord:
    return core.EvidenceRecord(
        evidence_index=index,
        relative_path=path,
        absolute_path=Path(path),
        label=label,
        partition="protocol_derived",
        view=view,
        role=view,
        altitude=altitude,
    )


class SUESHeldoutAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.records = [
            record("satellite-view/0001/a.jpg", "0001", "satellite", "", 0),
            record("satellite-view/0002/a.jpg", "0002", "satellite", "", 1),
            record("drone_view_512/0001/150/a.jpg", "0001", "drone", "150", 2),
            record("drone_view_512/0001/200/a.jpg", "0001", "drone", "200", 3),
            record("drone_view_512/0002/150/a.jpg", "0002", "drone", "150", 4),
            record("drone_view_512/0002/200/a.jpg", "0002", "drone", "200", 5),
        ]

    def test_frozen_core_hash_matches_registered_protocol(self) -> None:
        self.assertEqual(len(validate_frozen_core()), 64)

    def test_filter_removes_only_declared_drone_altitude(self) -> None:
        filtered = filter_heldout_records(self.records, "150")
        self.assertEqual(len(filtered), 4)
        self.assertFalse(
            any(row.view == "drone" and row.altitude == "150" for row in filtered)
        )
        self.assertEqual(
            sum(row.view == "satellite" for row in filtered),
            2,
        )

    def test_membership_and_protocol_summary_are_auditable(self) -> None:
        filtered = filter_heldout_records(self.records, "150")
        membership = membership_payload(
            self.records,
            filtered,
            "150",
            ["0001"],
        )
        self.assertEqual(
            membership["excluded_heldout_drone_record_count_official_train_ids"],
            1,
        )
        self.assertFalse(membership["official_test_metric_access"])

        def original(
            rows,
            dataset,
            val_fraction,
            seed,
            sues_train_ids,
        ):
            queries = [
                row
                for row in rows
                if row.view == "drone" and row.label in set(sues_train_ids)
            ]
            galleries = {
                "0001": [
                    row
                    for row in rows
                    if row.view == "satellite" and row.label == "0001"
                ]
            }
            return core.TrainingProtocol(
                train_queries=queries,
                train_gallery_by_label=galleries,
                validation_tasks=[],
                train_ids=["0001"],
                validation_ids=[],
                official_train_ids=["0001"],
                protocol_summary={"official_test_images_used_by_train_or_validation": 0},
            )

        with tempfile.TemporaryDirectory() as name:
            membership_path = Path(name) / "membership.json"
            builder = make_protocol_builder(original, "150", membership_path)
            protocol = builder(self.records, "sues200", 0.0, 1, ["0001"])
            self.assertTrue(membership_path.is_file())
            self.assertEqual(
                protocol.protocol_summary["heldout_altitude_fit_query_image_count"],
                0,
            )
            self.assertEqual(
                {row.altitude for row in protocol.train_queries},
                {"200"},
            )

    def test_t2_matrix_registers_exact_cartesian_product(self) -> None:
        matrix_path = (
            Path(__file__).resolve().parents[1]
            / "experiments"
            / "transactions_t2_heldout_matrix.json"
        )
        matrix = validate_matrix(matrix_path)
        self.assertEqual(len(matrix["runs"]), 24)
        self.assertEqual(
            {
                (
                    row["heldout_altitude_m"],
                    row["variant"],
                    row["seed"],
                )
                for row in matrix["runs"]
            },
            {
                (altitude, variant, seed)
                for altitude in core.SUES_ALTITUDES
                for variant in ("visual", "full")
                for seed in (1, 2, 3)
            },
        )

    def test_catalog_inventory_matches_frozen_core_algorithm(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            rows = []
            specifications = (
                ("satellite-view/0001/a.jpg", "satellite", ""),
                ("drone_view_512/0001/150/a.jpg", "drone", "150"),
                ("drone_view_512/0001/200/a.jpg", "drone", "200"),
            )
            for index, (relative, view, altitude) in enumerate(specifications):
                absolute = root / relative
                absolute.parent.mkdir(parents=True, exist_ok=True)
                absolute.write_bytes(f"fixture-{index}".encode("utf-8"))
                rows.append(
                    core.EvidenceRecord(
                        evidence_index=index,
                        relative_path=relative,
                        absolute_path=absolute,
                        label="0001",
                        partition="protocol_derived",
                        view=view,
                        role=view,
                        altitude=altitude,
                    )
                )
            catalog = catalog_training_files(rows, ["0001"])
            observed = inventory_from_catalog(catalog, "150")
            expected = core.inventory_hash(
                filter_heldout_records(rows, "150"),
                "content",
            )
            self.assertEqual(observed, expected)


if __name__ == "__main__":
    unittest.main()
