from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from external_baselines.fetch_and_verify_sources import IntegrityError, canonical_tree_hash
from external_baselines.source_patching import PatchSpec, _apply_patches, patch_plan_hash


class SourcePatchingTests(unittest.TestCase):
    def test_exact_patch_and_hash(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            path = root / "module.py"
            path.write_text("VALUE = 'old'\n", encoding="utf-8", newline="\n")
            spec = PatchSpec("module.py", "'old'", "'new'", rationale="test")
            records = _apply_patches(root, [spec])
            self.assertEqual(path.read_text(encoding="utf-8"), "VALUE = 'new'\n")
            self.assertEqual(records[0]["replacement_count"], 1)
            self.assertEqual(canonical_tree_hash(root)[1], 1)

    def test_patch_fails_if_upstream_text_drifted(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / "module.py").write_text("VALUE = 'other'\n", encoding="utf-8")
            spec = PatchSpec("module.py", "'old'", "'new'")
            with self.assertRaises(IntegrityError):
                _apply_patches(root, [spec])

    def test_plan_hash_changes_with_semantics(self) -> None:
        first = PatchSpec("module.py", "old", "new")
        second = replace(first, new="different")
        self.assertNotEqual(
            patch_plan_hash("source", [first]),
            patch_plan_hash("source", [second]),
        )


if __name__ == "__main__":
    unittest.main()
