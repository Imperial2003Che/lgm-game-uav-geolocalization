"""Synthetic, CPU-only tests for the formal publication figure pipeline."""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PLOT_SCRIPT = PACKAGE_ROOT / "experiments" / "plot_frozen_formal_results.py"
AGGREGATE_SCRIPT = (
    PACKAGE_ROOT / "experiments" / "aggregate_frozen_formal_results.py"
)
AGGREGATE_TEST = (
    PACKAGE_ROOT / "tests" / "test_aggregate_frozen_formal_results.py"
)


def import_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


plot_module = import_path("formal_plot", PLOT_SCRIPT)
aggregate_module = import_path("formal_aggregate_for_plot_test", AGGREGATE_SCRIPT)
fixture_module = import_path("formal_aggregate_fixture", AGGREGATE_TEST)


def write_json(path: Path, value: object) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def add_synthetic_complexity(aggregate_dir: Path) -> None:
    path = aggregate_dir / "sensitivity_with_main_reference.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    fields.append("parameter_count")
    values = {
        "full": 11_700_000,
        "backbone_resnet50": 25_600_000,
        "embed_dim_256": 11_400_000,
        "embed_dim_1024": 12_200_000,
    }
    for row in rows:
        row["parameter_count"] = str(values[row["setting"]])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    manifest_path = aggregate_dir / "aggregate_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("payload_sha256")
    for record in manifest["output_artifacts"]:
        if record["path"] == path.name:
            record["sha256"] = plot_module.sha256_file(path)
            record["bytes"] = path.stat().st_size
            break
    else:
        raise AssertionError("Synthetic aggregate manifest lacks sensitivity CSV.")
    manifest["payload_sha256"] = plot_module.canonical_sha256(manifest)
    write_json(manifest_path, manifest)


class FormalFigureTests(unittest.TestCase):
    def test_complete_gate_exports_and_optional_complexity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "delivery"
            fixture_module.make_fixture(root)
            aggregate_dir = (
                root / "lgm_game_pytorch" / "results" / "formal_matrix_aggregate"
            )
            aggregate_module.aggregate(
                root,
                aggregate_dir,
                allow_partial=False,
                bootstrap_samples=10_000,
                bootstrap_seed=11,
            )
            output = root / "lgm_game_paper_latex" / "figures" / "formal_results"
            manifest = plot_module.generate_figures(
                aggregate_dir,
                output,
                png_dpi=100,
            )
            self.assertEqual(manifest["status"], "completed")
            self.assertEqual(len(manifest["figure_contracts"]), 5)
            self.assertFalse(manifest["complexity"]["detected"])
            expected_bases = (
                "formal_main_university1652_variants",
                "formal_main_sues200_variants",
                "formal_visual_vs_full_forest",
                "formal_sues_altitude_curves",
                "formal_sensitivity",
            )
            for base in expected_bases:
                for suffix in (".svg", ".pdf", ".png"):
                    path = output / f"{base}{suffix}"
                    self.assertTrue(path.is_file())
                    self.assertGreater(path.stat().st_size, 500)
                svg = (output / f"{base}.svg").read_text(encoding="utf-8")
                self.assertIn("<text", svg)
            expected_source_rows = {
                "formal_main_university1652_variants_source.csv": 18,
                "formal_main_sues200_variants_source.csv": 48,
                "formal_visual_vs_full_forest_source.csv": 33,
                "formal_sues_altitude_curves_source.csv": 48,
                "formal_sensitivity_source.csv": 44,
            }
            for name, expected in expected_source_rows.items():
                with (output / name).open(
                    "r", encoding="utf-8", newline=""
                ) as handle:
                    self.assertEqual(len(list(csv.DictReader(handle))), expected)

            manifest_path = aggregate_dir / "aggregate_manifest.json"
            original_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            partial_manifest = dict(original_manifest)
            partial_manifest.pop("payload_sha256")
            partial_manifest["status"] = "partial_audit_only"
            partial_manifest["payload_sha256"] = plot_module.canonical_sha256(
                partial_manifest
            )
            write_json(manifest_path, partial_manifest)
            with self.assertRaises(plot_module.IncompleteAggregateError):
                plot_module.generate_figures(
                    aggregate_dir,
                    root / "must_not_exist",
                    png_dpi=100,
                )
            self.assertFalse((root / "must_not_exist").exists())
            write_json(manifest_path, original_manifest)

            add_synthetic_complexity(aggregate_dir)
            complete_data = plot_module.load_completed_aggregate(aggregate_dir)
            self.assertIsNotNone(complete_data.complexity)
            self.assertEqual(complete_data.complexity.column, "parameter_count")
            complexity_output = root / "complexity_branch"
            artifacts, contract = plot_module.plot_sensitivity(
                complete_data,
                complexity_output,
                dpi=100,
            )
            self.assertTrue(contract["complexity_panel_generated"])
            self.assertEqual(contract["complexity_field"], "parameter_count")
            self.assertEqual(len(artifacts), 4)
            self.assertTrue((complexity_output / "formal_sensitivity.svg").is_file())


if __name__ == "__main__":
    unittest.main()
