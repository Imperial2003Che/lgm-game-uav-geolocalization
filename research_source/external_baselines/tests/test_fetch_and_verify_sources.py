from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from external_baselines.fetch_and_verify_sources import (
    IntegrityError,
    canonical_tree_hash,
    extract_verified_archive,
    verify_archive,
    verify_source_tree,
)


class ExternalSourceVerificationTests(unittest.TestCase):
    def make_source_and_archive(self, root: Path) -> tuple[Path, Path, dict[str, object]]:
        source_root = root / "fixture-source"
        (source_root / "nested").mkdir(parents=True)
        (source_root / "a.txt").write_text("alpha\n", encoding="utf-8", newline="\n")
        (source_root / "nested" / "b.bin").write_bytes(bytes(range(32)))
        tree_sha, count = canonical_tree_hash(source_root)

        archive_path = root / "fixture.zip"
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(source_root.rglob("*")):
                if path.is_file():
                    archive.write(path, Path("fixture-commit") / path.relative_to(source_root))
        archive_sha = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        source = {
            "id": "fixture",
            "method": "Fixture",
            "archive_bytes": archive_path.stat().st_size,
            "archive_sha256": archive_sha,
            "source_file_count": count,
            "source_tree_sha256": tree_sha,
        }
        return source_root, archive_path, source

    def test_archive_and_tree_verify(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source_root, archive_path, source = self.make_source_and_archive(root)
            self.assertEqual(verify_archive(archive_path, source)["archive_sha256"], source["archive_sha256"])
            self.assertEqual(
                verify_source_tree(source_root, source)["source_tree_sha256"],
                source["source_tree_sha256"],
            )

    def test_extract_is_verified_and_existing_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            _, archive_path, source = self.make_source_and_archive(root)
            destination = root / "materialized"
            result = extract_verified_archive(archive_path, destination, source)
            self.assertEqual(result["source_file_count"], 2)
            (destination / "a.txt").write_text("tampered\n", encoding="utf-8")
            with self.assertRaises(IntegrityError):
                extract_verified_archive(archive_path, destination, source)

    def test_path_traversal_archive_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            archive_path = root / "unsafe.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../escape.txt", "unsafe")
            source = {
                "id": "unsafe",
                "archive_bytes": archive_path.stat().st_size,
                "archive_sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
                "source_file_count": 1,
                "source_tree_sha256": "0" * 64,
            }
            with self.assertRaises(IntegrityError):
                extract_verified_archive(archive_path, root / "out", source)

    def test_registry_fixture_is_json_serializable(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            _, _, source = self.make_source_and_archive(root)
            json.dumps(source)


if __name__ == "__main__":
    unittest.main()
