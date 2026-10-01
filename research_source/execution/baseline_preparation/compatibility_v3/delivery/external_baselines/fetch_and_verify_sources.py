#!/usr/bin/env python3
"""Fetch and verify pinned third-party source snapshots without overwriting data."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from typing import Any, Iterable
import urllib.request
import zipfile


SCHEMA_VERSION = "lgm-game.external-source-verification.v1"
CHUNK_BYTES = 1024 * 1024


class IntegrityError(RuntimeError):
    """Raised when a pinned external artifact fails a closed integrity check."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_tree_payload(root: Path) -> tuple[bytes, int]:
    root = root.resolve(strict=True)
    rows: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        rows.append(f"{relative}\t{sha256_file(path)}\t{path.stat().st_size}\n")
    rows.sort()
    return "".join(rows).encode("utf-8"), len(rows)


def canonical_tree_hash(root: Path) -> tuple[str, int]:
    payload, file_count = canonical_tree_payload(root)
    return hashlib.sha256(payload).hexdigest(), file_count


def load_registry(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    registry = json.loads(raw.decode("utf-8"))
    if registry.get("schema_version") != "lgm-game.transactions-external-sources.v1":
        raise IntegrityError(f"Unsupported registry schema: {registry.get('schema_version')!r}")
    sources = registry.get("sources")
    if not isinstance(sources, list) or not sources:
        raise IntegrityError("Registry must contain a non-empty sources list.")
    ids = [source.get("id") for source in sources]
    if len(ids) != len(set(ids)) or any(not value for value in ids):
        raise IntegrityError("Registry source IDs must be present and unique.")
    return registry, hashlib.sha256(raw).hexdigest()


def verify_archive(path: Path, source: dict[str, Any]) -> dict[str, Any]:
    if not path.is_file():
        raise IntegrityError(f"Archive does not exist: {path}")
    actual_bytes = path.stat().st_size
    expected_bytes = int(source["archive_bytes"])
    if actual_bytes != expected_bytes:
        raise IntegrityError(
            f"{source['id']} archive byte count mismatch: "
            f"expected {expected_bytes}, got {actual_bytes}"
        )
    actual_sha = sha256_file(path)
    expected_sha = source["archive_sha256"]
    if actual_sha != expected_sha:
        raise IntegrityError(
            f"{source['id']} archive SHA-256 mismatch: expected {expected_sha}, got {actual_sha}"
        )
    return {
        "archive_path": str(path.resolve()),
        "archive_bytes": actual_bytes,
        "archive_sha256": actual_sha,
    }


def verify_source_tree(root: Path, source: dict[str, Any]) -> dict[str, Any]:
    if not root.is_dir():
        raise IntegrityError(f"Source root does not exist: {root}")
    actual_sha, actual_count = canonical_tree_hash(root)
    expected_sha = source["source_tree_sha256"]
    expected_count = int(source["source_file_count"])
    if actual_count != expected_count:
        raise IntegrityError(
            f"{source['id']} source file count mismatch: "
            f"expected {expected_count}, got {actual_count}"
        )
    if actual_sha != expected_sha:
        raise IntegrityError(
            f"{source['id']} source-tree SHA-256 mismatch: "
            f"expected {expected_sha}, got {actual_sha}"
        )
    return {
        "source_root": str(root.resolve()),
        "source_file_count": actual_count,
        "source_tree_sha256": actual_sha,
    }


def download_archive(source: dict[str, Any], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        verify_archive(destination, source)
        return
    temporary = destination.with_name(f"{destination.name}.part.{os.getpid()}")
    if temporary.exists():
        raise IntegrityError(f"Refusing to overwrite stale partial download: {temporary}")
    request = urllib.request.Request(
        source["archive_url"],
        headers={"User-Agent": "LGM-GAME-Reproducibility-Audit/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response, temporary.open("xb") as out:
            shutil.copyfileobj(response, out, length=CHUNK_BYTES)
        verify_archive(temporary, source)
        temporary.replace(destination)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise


def _safe_zip_members(archive: zipfile.ZipFile) -> tuple[list[zipfile.ZipInfo], str]:
    members = [member for member in archive.infolist() if member.filename]
    if not members:
        raise IntegrityError("Source archive is empty.")
    roots: set[str] = set()
    for member in members:
        posix = PurePosixPath(member.filename)
        if posix.is_absolute() or ".." in posix.parts or not posix.parts:
            raise IntegrityError(f"Unsafe archive member: {member.filename!r}")
        roots.add(posix.parts[0])
        unix_mode = member.external_attr >> 16
        if (unix_mode & 0o170000) == 0o120000:
            raise IntegrityError(f"Symbolic links are not accepted: {member.filename!r}")
    if len(roots) != 1:
        raise IntegrityError(f"Archive must have one top-level directory, found {sorted(roots)}")
    return members, next(iter(roots))


def extract_verified_archive(
    archive_path: Path,
    destination: Path,
    source: dict[str, Any],
) -> dict[str, Any]:
    if destination.exists():
        return verify_source_tree(destination, source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{source['id']}-extract-",
        dir=destination.parent,
    ) as temporary_name:
        temporary = Path(temporary_name)
        with zipfile.ZipFile(archive_path) as archive:
            members, top_level = _safe_zip_members(archive)
            archive.extractall(temporary, members=members)
        extracted = temporary / top_level
        verification = verify_source_tree(extracted, source)
        if destination.exists():
            raise IntegrityError(f"Destination appeared during extraction: {destination}")
        shutil.move(str(extracted), str(destination))
    return {
        **verification,
        "source_root": str(destination.resolve()),
    }


def parse_source_root(values: Iterable[str]) -> dict[str, Path]:
    parsed: dict[str, Path] = {}
    for value in values:
        source_id, separator, raw_path = value.partition("=")
        if not separator or not source_id or not raw_path:
            raise IntegrityError("--source-root values must use ID=PATH syntax.")
        if source_id in parsed:
            raise IntegrityError(f"Duplicate --source-root mapping for {source_id!r}.")
        parsed[source_id] = Path(raw_path)
    return parsed


def select_sources(registry: dict[str, Any], selected_ids: list[str]) -> list[dict[str, Any]]:
    by_id = {source["id"]: source for source in registry["sources"]}
    if not selected_ids:
        return list(registry["sources"])
    unknown = sorted(set(selected_ids) - set(by_id))
    if unknown:
        raise IntegrityError(f"Unknown source IDs: {unknown}")
    return [by_id[source_id] for source_id in selected_ids]


def run(args: argparse.Namespace) -> dict[str, Any]:
    registry, registry_sha = load_registry(args.registry)
    sources = select_sources(registry, args.source_id)
    explicit_roots = parse_source_root(args.source_root)
    selected_ids = {source["id"] for source in sources}
    unused_roots = sorted(set(explicit_roots) - selected_ids)
    if unused_roots:
        raise IntegrityError(f"Source-root mappings are not selected: {unused_roots}")

    result_rows: list[dict[str, Any]] = []
    for source in sources:
        source_id = source["id"]
        row: dict[str, Any] = {
            "id": source_id,
            "method": source["method"],
            "commit": source["commit"],
            "execution_status": source["execution_status"],
        }
        explicit = explicit_roots.get(source_id)
        if explicit is not None:
            row.update(verify_source_tree(explicit, source))
            row["mode"] = "verified_explicit_source_root"
        else:
            if args.work_root is None:
                raise IntegrityError(
                    f"{source_id} needs either --source-root {source_id}=PATH or --work-root."
                )
            archive_path = args.work_root / "archives" / source["archive_filename"]
            if args.download:
                download_archive(source, archive_path)
            row.update(verify_archive(archive_path, source))
            destination = args.work_root / "sources" / source_id
            if args.extract:
                row.update(extract_verified_archive(archive_path, destination, source))
                row["mode"] = "verified_archive_and_source_tree"
            else:
                row["mode"] = "verified_archive"
        result_rows.append(row)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "registry_path": str(args.registry.resolve()),
        "registry_sha256": registry_sha,
        "sources": result_rows,
    }
    if args.manifest is not None:
        if args.manifest.exists() and not args.allow_identical_manifest:
            raise IntegrityError(f"Refusing to overwrite existing manifest: {args.manifest}")
        serialized = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        if args.manifest.exists():
            existing = args.manifest.read_text(encoding="utf-8")
            if existing != serialized:
                raise IntegrityError(f"Existing manifest differs: {args.manifest}")
        else:
            args.manifest.parent.mkdir(parents=True, exist_ok=True)
            args.manifest.write_text(serialized, encoding="utf-8", newline="\n")
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path(__file__).with_name("transactions_baseline_registry.json"),
    )
    parser.add_argument("--source-id", action="append", default=[], help="Repeat to select IDs.")
    parser.add_argument(
        "--source-root",
        action="append",
        default=[],
        metavar="ID=PATH",
        help="Verify an already extracted source root.",
    )
    parser.add_argument("--work-root", type=Path, help="External archive/source working directory.")
    parser.add_argument("--download", action="store_true", help="Download a missing pinned archive.")
    parser.add_argument("--extract", action="store_true", help="Extract and verify the source tree.")
    parser.add_argument("--manifest", type=Path, help="Write a non-overwriting JSON manifest.")
    parser.add_argument(
        "--allow-identical-manifest",
        action="store_true",
        help="Accept an existing manifest only when its bytes are identical.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        manifest = run(args)
    except (IntegrityError, OSError, ValueError, zipfile.BadZipFile) as error:
        raise SystemExit(f"ERROR: {error}") from error
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
