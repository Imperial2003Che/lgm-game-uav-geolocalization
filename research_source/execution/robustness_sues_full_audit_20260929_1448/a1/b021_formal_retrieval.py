"""Leakage-controlled image-level training and official full-gallery evaluation.

This module is deliberately self-contained.  It consumes the NPZ produced by
``generate_clip_image_evidence`` but derives identity labels, train/test
membership, views, and official retrieval roles from the dataset paths.  Cache
labels or cache split annotations are never used.

Supported protocols
-------------------
University-1652
    Official ``train`` identities for fitting, with a deterministic
    identity-disjoint validation holdout.  Evaluation covers Drone->Satellite,
    Satellite->Drone, and Street->Satellite using every official query and
    every image in the corresponding official gallery.

SUES-200
    The fixed 120 training identities from the official ``indexs.yaml`` (with
    an embedded fallback) and the remaining 80 test identities.  Evaluation
    covers UAV<->Satellite at 150/200/250/300 m.  Every gallery retains all 200
    identities, so non-test identities remain as distractors.

The six variants are strict:
``visual`` uses only the independently encoded image; ``content`` uses only
the 11-D content probability vector; ``style`` uses only the 10-D style
probability vector; ``visual_content`` and ``visual_style`` are leave-one-cue
fusion controls; and ``full`` fuses all three independently computed branches.
No encoder receives a paired image or gallery context.

Examples
--------
Train (the training command never evaluates on the official test split)::

    python -m lgm_game_pytorch.formal_retrieval train \
      --dataset university1652 --data-root /data/University-1652 \
      --evidence /cache/university1652_clip_image_evidence.npz \
      --output-dir runs/u1652_full_seed1 --variant full --backbone resnet50

Evaluate the selected checkpoint on every official task::

    python -m lgm_game_pytorch.formal_retrieval evaluate \
      --dataset university1652 --data-root /data/University-1652 \
      --evidence /cache/university1652_clip_image_evidence.npz \
      --checkpoint runs/u1652_full_seed1/best.pt \
      --output-dir runs/u1652_full_seed1/evaluation
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import dataclasses
import datetime as dt
import hashlib
import importlib.metadata
import json
import logging
import math
import os
import platform
import random
import re
import sys
import tempfile
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Iterator, Mapping, Sequence

import numpy as np
from PIL import Image, ImageFile
import torch
from torch import nn
import torch.nn.functional as F
from torch.utils.data import BatchSampler, DataLoader, Dataset
import torchvision
from torchvision import models, transforms


LOGGER = logging.getLogger("formal_retrieval")
SCHEMA_VERSION = "formal-retrieval-v1"
CONTENT_DIM = 11
STYLE_DIM = 10
SUES_ALTITUDES = ("150", "200", "250", "300")
VARIANTS = (
    "visual",
    "content",
    "style",
    "visual_content",
    "visual_style",
    "full",
)
SUES_MANIFEST_SOURCE = (
    "https://github.com/Reza-Zhu/SUES-200-Benchmark/"
    "blob/master/script/indexs.yaml"
)

# Exact list published in the official SUES-200 benchmark indexs.yaml.  The
# manifest shipped beside this module is preferred; this is an auditable
# fallback for a copied standalone file.
SUES_OFFICIAL_TRAIN_IDS = (
    "0001", "0002", "0003", "0004", "0005", "0006", "0007", "0009",
    "0010", "0011", "0013", "0015", "0016", "0020", "0021", "0024",
    "0025", "0026", "0027", "0028", "0029", "0030", "0031", "0032",
    "0033", "0034", "0036", "0037", "0039", "0043", "0044", "0045",
    "0051", "0055", "0056", "0057", "0058", "0060", "0064", "0066",
    "0067", "0069", "0070", "0073", "0074", "0076", "0077", "0080",
    "0081", "0082", "0084", "0085", "0086", "0087", "0088", "0089",
    "0090", "0091", "0094", "0096", "0097", "0100", "0101", "0102",
    "0103", "0104", "0105", "0106", "0113", "0116", "0118", "0119",
    "0120", "0123", "0125", "0126", "0127", "0129", "0132", "0134",
    "0137", "0139", "0141", "0142", "0145", "0146", "0147", "0148",
    "0149", "0151", "0152", "0155", "0156", "0157", "0158", "0159",
    "0160", "0163", "0166", "0167", "0168", "0169", "0171", "0174",
    "0179", "0180", "0182", "0183", "0184", "0185", "0186", "0187",
    "0191", "0192", "0193", "0196", "0197", "0198", "0199", "0200",
)


@dataclass(frozen=True)
class EvidenceRecord:
    """One independently generated image-evidence row."""

    evidence_index: int
    relative_path: str
    absolute_path: Path
    label: str
    partition: str
    view: str
    role: str
    altitude: str


@dataclass(frozen=True)
class RetrievalTask:
    name: str
    query: tuple[EvidenceRecord, ...]
    gallery: tuple[EvidenceRecord, ...]
    protocol: str


@dataclass(frozen=True)
class CacheDescriptor:
    path: str
    sha256: str
    bytes: int
    meta_path: str
    meta_sha256: str
    model: str
    dataset_root_hint: str
    rows: int


@dataclass
class TrainingProtocol:
    train_queries: list[EvidenceRecord]
    train_gallery_by_label: dict[str, list[EvidenceRecord]]
    validation_tasks: list[RetrievalTask]
    train_ids: list[str]
    validation_ids: list[str]
    official_train_ids: list[str]
    protocol_summary: dict[str, Any]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(block_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def atomic_json_dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, default=str)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_torch_save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    os.close(fd)
    try:
        torch.save(value, temporary)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_torch_checkpoint(path: Path, map_location: str | torch.device) -> dict[str, Any]:
    try:
        return torch.load(path, map_location=map_location, weights_only=False)
    except TypeError:
        return torch.load(path, map_location=map_location)


def slugify(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return value.strip("_") or "task"


def normalize_dataset_name(value: str) -> str:
    normalized = re.sub(r"[-_\s]", "", value.lower())
    if normalized in {"university1652", "university", "u1652"}:
        return "university1652"
    if normalized in {"sues200", "sues"}:
        return "sues200"
    raise ValueError(f"Unsupported dataset {value!r}; choose university1652 or sues200.")


def normalized_relative_path(value: Any) -> str:
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    text = str(value).strip().replace("\\", "/")
    text = re.sub(r"/+", "/", text)
    while text.startswith("./"):
        text = text[2:]
    if not text:
        raise ValueError("Evidence cache contains an empty path.")
    if text.startswith("/") or re.match(r"^[A-Za-z]:", text):
        raise ValueError(f"Evidence paths must be relative to --data-root, got {text!r}.")
    pure = PurePosixPath(text)
    if any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError(f"Unsafe or non-canonical evidence path {text!r}.")
    return pure.as_posix()


def find_meta_path(npz_path: Path) -> Path:
    candidate = npz_path.with_suffix(".meta.json")
    if candidate.exists():
        return candidate
    alternate = Path(f"{npz_path}.meta.json")
    if alternate.exists():
        return alternate
    raise FileNotFoundError(
        f"Required evidence metadata is missing for {npz_path}; expected {candidate.name}."
    )


def _pick_npz_array(payload: Mapping[str, np.ndarray], names: Sequence[str]) -> np.ndarray:
    for name in names:
        if name in payload:
            return np.asarray(payload[name])
    raise KeyError(f"Evidence cache is missing all accepted keys: {', '.join(names)}")


def _validate_probability_array(array: np.ndarray, rows: int, width: int, name: str) -> np.ndarray:
    if array.ndim != 2 or array.shape != (rows, width):
        raise ValueError(f"{name} must have shape [{rows}, {width}], got {array.shape}.")
    if not np.issubdtype(array.dtype, np.floating):
        raise TypeError(f"{name} must be floating point, got {array.dtype}.")
    values = np.asarray(array, dtype=np.float32)
    if not np.isfinite(values).all():
        raise ValueError(f"{name} contains NaN or infinity.")
    if values.min(initial=0.0) < -1e-4 or values.max(initial=1.0) > 1.0001:
        raise ValueError(f"{name} contains values outside probability range [0, 1].")
    row_sums = values.sum(axis=1)
    if not np.allclose(row_sums, 1.0, atol=2e-2, rtol=2e-2):
        bad = int(np.argmax(np.abs(row_sums - 1.0)))
        raise ValueError(
            f"{name} rows must be probability distributions; row {bad} sums to "
            f"{row_sums[bad]:.6f}."
        )
    return values


class EvidenceStore:
    """Merged, path-indexed image evidence with strict schema checks."""

    def __init__(
        self,
        paths: list[str],
        content_probs: np.ndarray,
        style_probs: np.ndarray,
        content_candidates: tuple[str, ...],
        style_candidates: tuple[str, ...],
        cache_descriptors: list[CacheDescriptor],
    ) -> None:
        self.paths = paths
        self.content_probs = content_probs
        self.style_probs = style_probs
        self.content_candidates = content_candidates
        self.style_candidates = style_candidates
        self.cache_descriptors = cache_descriptors
        self.path_to_index = {path.casefold(): index for index, path in enumerate(paths)}

    @classmethod
    def load(cls, cache_paths: Sequence[Path]) -> "EvidenceStore":
        if not cache_paths:
            raise ValueError("At least one --evidence NPZ is required.")
        merged_paths: list[str] = []
        content_parts: list[np.ndarray] = []
        style_parts: list[np.ndarray] = []
        descriptors: list[CacheDescriptor] = []
        seen: set[str] = set()
        expected_content_candidates: tuple[str, ...] | None = None
        expected_style_candidates: tuple[str, ...] | None = None

        for cache_path in cache_paths:
            cache_path = cache_path.expanduser().resolve(strict=True)
            meta_path = find_meta_path(cache_path)
            with meta_path.open("r", encoding="utf-8") as handle:
                metadata = json.load(handle)
            coverage = metadata.get("coverage", {})
            if metadata.get("status") != "complete" or coverage.get("complete") is not True:
                raise ValueError(
                    f"Evidence cache {cache_path} is not a completed full scan; "
                    f"status={metadata.get('status')!r}, complete={coverage.get('complete')!r}."
                )
            if (
                int(coverage.get("failed_images", -1)) != 0
                or int(coverage.get("missing_images", -1)) != 0
                or int(coverage.get("extra_cached_paths", -1)) != 0
                or float(coverage.get("coverage_fraction", -1.0)) != 1.0
            ):
                raise ValueError(
                    f"Evidence cache {cache_path} failed the 100% coverage gate: "
                    f"{coverage}."
                )
            actual_cache_sha = sha256_file(cache_path)
            declared_sha = str(metadata.get("cache_sha256", "")).lower()
            if not declared_sha:
                raise ValueError(f"{meta_path} does not declare cache_sha256.")
            if declared_sha != actual_cache_sha:
                raise ValueError(
                    f"Evidence hash mismatch for {cache_path}: metadata={declared_sha}, "
                    f"actual={actual_cache_sha}."
                )

            with np.load(cache_path, allow_pickle=False) as payload:
                paths_array = _pick_npz_array(payload, ("paths", "relative_paths"))
                raw_content = _pick_npz_array(payload, ("content_probs", "content_prob"))
                raw_style = _pick_npz_array(payload, ("style_probs", "style_prob"))
                if paths_array.ndim != 1:
                    raise ValueError(f"paths must be one-dimensional, got {paths_array.shape}.")
                rows = int(paths_array.shape[0])
                content = _validate_probability_array(
                    raw_content, rows, CONTENT_DIM, "content_probs"
                )
                style = _validate_probability_array(
                    raw_style, rows, STYLE_DIM, "style_probs"
                )
                for optional_key in ("views", "altitudes"):
                    if optional_key in payload and np.asarray(payload[optional_key]).shape != (rows,):
                        raise ValueError(
                            f"{optional_key} must have shape [{rows}], got "
                            f"{np.asarray(payload[optional_key]).shape}."
                        )
                cache_rel_paths = [normalized_relative_path(item) for item in paths_array]

            content_candidates = tuple(str(item) for item in metadata.get("content_candidates", ()))
            style_candidates = tuple(str(item) for item in metadata.get("style_candidates", ()))
            if len(content_candidates) != CONTENT_DIM:
                raise ValueError(
                    f"{meta_path} must contain {CONTENT_DIM} content_candidates."
                )
            if len(style_candidates) != STYLE_DIM:
                raise ValueError(f"{meta_path} must contain {STYLE_DIM} style_candidates.")
            if expected_content_candidates is None:
                expected_content_candidates = content_candidates
                expected_style_candidates = style_candidates
            elif (
                content_candidates != expected_content_candidates
                or style_candidates != expected_style_candidates
            ):
                raise ValueError("All evidence caches must use identical candidate ordering.")

            for rel_path in cache_rel_paths:
                key = rel_path.casefold()
                if key in seen:
                    raise ValueError(f"Duplicate evidence row for {rel_path!r}.")
                seen.add(key)
            merged_paths.extend(cache_rel_paths)
            content_parts.append(content)
            style_parts.append(style)
            descriptors.append(
                CacheDescriptor(
                    path=str(cache_path),
                    sha256=actual_cache_sha,
                    bytes=cache_path.stat().st_size,
                    meta_path=str(meta_path.resolve()),
                    meta_sha256=sha256_file(meta_path),
                    model=str(metadata.get("model", "")),
                    dataset_root_hint=str(metadata.get("dataset_root_hint", "")),
                    rows=rows,
                )
            )

        return cls(
            paths=merged_paths,
            content_probs=np.concatenate(content_parts, axis=0),
            style_probs=np.concatenate(style_parts, axis=0),
            content_candidates=expected_content_candidates or (),
            style_candidates=expected_style_candidates or (),
            cache_descriptors=descriptors,
        )


def _component_after(parts: Sequence[str], token_index: int, path: str) -> str:
    if token_index + 1 >= len(parts):
        raise ValueError(f"Cannot derive identity from {path!r}.")
    label = parts[token_index + 1]
    if not label:
        raise ValueError(f"Empty identity component in {path!r}.")
    return label


def derive_record(
    evidence_index: int,
    relative_path: str,
    dataset_root: Path,
    dataset: str,
) -> EvidenceRecord:
    """Derive all protocol attributes from the path, never from cache annotations."""

    pure = PurePosixPath(relative_path)
    parts = list(pure.parts)
    lower = [part.lower() for part in parts]
    absolute = (dataset_root / Path(*parts)).resolve(strict=True)
    try:
        absolute.relative_to(dataset_root)
    except ValueError as exc:
        raise ValueError(f"Evidence path escapes --data-root: {relative_path}") from exc
    if not absolute.is_file():
        raise FileNotFoundError(f"Evidence row is not an image file: {absolute}")

    if dataset == "university1652":
        known_roles = {
            "drone": ("train", "drone", "train_drone"),
            "satellite": ("train", "satellite", "train_satellite"),
            "street": ("train", "street", "train_street"),
            "query_drone": ("test", "drone", "query_drone"),
            "gallery_drone": ("test", "drone", "gallery_drone"),
            "query_satellite": ("test", "satellite", "query_satellite"),
            "gallery_satellite": ("test", "satellite", "gallery_satellite"),
            "query_street": ("test", "street", "query_street"),
            "gallery_street": ("test", "street", "gallery_street"),
        }
        role_indices = [(i, known_roles[token]) for i, token in enumerate(lower) if token in known_roles]
        if not role_indices:
            # Google imagery and other auxiliary directories are intentionally
            # outside the supported official retrieval protocol.
            raise ValueError(
                f"University-1652 path has no supported official view role: {relative_path}"
            )
        token_index, (partition, view, role) = role_indices[-1]
        label = _component_after(parts, token_index, relative_path)
        return EvidenceRecord(
            evidence_index=evidence_index,
            relative_path=relative_path,
            absolute_path=absolute,
            label=label,
            partition=partition,
            view=view,
            role=role,
            altitude="",
        )

    if dataset == "sues200":
        if "drone_view_512" in lower:
            token_index = len(lower) - 1 - lower[::-1].index("drone_view_512")
            label = _component_after(parts, token_index, relative_path)
            altitude_index = token_index + 2
            if altitude_index >= len(parts):
                raise ValueError(f"Cannot derive SUES altitude from {relative_path!r}.")
            altitude = re.sub(r"[^0-9]", "", parts[altitude_index])
            if altitude not in SUES_ALTITUDES:
                raise ValueError(
                    f"Unsupported SUES altitude {parts[altitude_index]!r} in {relative_path!r}."
                )
            return EvidenceRecord(
                evidence_index=evidence_index,
                relative_path=relative_path,
                absolute_path=absolute,
                label=label,
                partition="protocol_derived",
                view="drone",
                role="drone",
                altitude=altitude,
            )
        if "satellite-view" in lower:
            token_index = len(lower) - 1 - lower[::-1].index("satellite-view")
            label = _component_after(parts, token_index, relative_path)
            return EvidenceRecord(
                evidence_index=evidence_index,
                relative_path=relative_path,
                absolute_path=absolute,
                label=label,
                partition="protocol_derived",
                view="satellite",
                role="satellite",
                altitude="",
            )
        raise ValueError(f"SUES-200 path has no official view role: {relative_path}")

    raise AssertionError(dataset)


def derive_all_records(
    store: EvidenceStore,
    dataset_root: Path,
    dataset: str,
) -> list[EvidenceRecord]:
    dataset_root = dataset_root.expanduser().resolve(strict=True)
    records: list[EvidenceRecord] = []
    unsupported: list[str] = []
    for index, relative_path in enumerate(store.paths):
        try:
            records.append(derive_record(index, relative_path, dataset_root, dataset))
        except ValueError as exc:
            # University-1652 caches may legitimately contain auxiliary Google
            # images.  They are excluded explicitly, while malformed official
            # roles remain fatal below.
            if dataset == "university1652" and any(
                token in relative_path.lower().replace("\\", "/").split("/")
                for token in ("google", "4k_drone")
            ):
                unsupported.append(relative_path)
                continue
            raise exc
    if not records:
        raise RuntimeError(f"No supported {dataset} records were found in the evidence cache.")
    LOGGER.info(
        "Derived %d official-protocol image records from paths (%d auxiliary rows ignored).",
        len(records),
        len(unsupported),
    )
    return records


def parse_sues_manifest(path: Path | None) -> tuple[list[str], dict[str, Any]]:
    if path is not None and path.exists():
        text = path.read_text(encoding="utf-8")
        ids = re.findall(r'^\s*-\s*["\']?([0-9]{4})["\']?\s*$', text, flags=re.MULTILINE)
        if not ids:
            # Also accept the original one-line ``index: ['0001', ...]``.
            ids = re.findall(r"['\"]([0-9]{4})['\"]", text)
        ids = list(dict.fromkeys(ids))
        source = str(path.resolve())
        manifest_sha = sha256_file(path)
    else:
        ids = list(SUES_OFFICIAL_TRAIN_IDS)
        source = "embedded official indexs.yaml fallback"
        manifest_sha = canonical_sha256(ids)
    expected_all = {f"{index:04d}" for index in range(1, 201)}
    if len(ids) != 120 or len(set(ids)) != 120 or not set(ids) <= expected_all:
        raise ValueError(
            f"SUES manifest must contain 120 unique IDs in 0001..0200; got {len(ids)}."
        )
    if tuple(ids) != SUES_OFFICIAL_TRAIN_IDS:
        raise ValueError(
            "SUES manifest does not match the official fixed indexs.yaml ordering/content."
        )
    return ids, {
        "path_or_source": source,
        "sha256": manifest_sha,
        "official_source_url": SUES_MANIFEST_SOURCE,
        "train_id_count": 120,
        "test_id_count": 80,
    }


def stable_identity_holdout(
    identities: Sequence[str], fraction: float, seed: int
) -> tuple[list[str], list[str]]:
    identities = sorted(set(identities))
    if len(identities) < 2:
        raise ValueError("At least two identities are needed for an identity-disjoint holdout.")
    if fraction == 0.0:
        return identities, []
    if not 0.0 < fraction < 0.5:
        raise ValueError("--val-fraction must be 0 (fixed-schedule final fit) or lie in (0, 0.5).")
    count = max(1, min(len(identities) - 1, int(round(len(identities) * fraction))))
    ordered = sorted(
        identities,
        key=lambda identity: hashlib.sha256(
            f"{seed}:{identity}".encode("utf-8")
        ).hexdigest(),
    )
    validation = sorted(ordered[:count])
    training = sorted(set(identities) - set(validation))
    return training, validation


def _group_by_label(records: Iterable[EvidenceRecord]) -> dict[str, list[EvidenceRecord]]:
    grouped: dict[str, list[EvidenceRecord]] = defaultdict(list)
    for record in records:
        grouped[record.label].append(record)
    return {key: sorted(value, key=lambda item: item.relative_path) for key, value in grouped.items()}


def _assert_task(task: RetrievalTask) -> None:
    if not task.query or not task.gallery:
        raise RuntimeError(
            f"Task {task.name} is empty: query={len(task.query)}, gallery={len(task.gallery)}."
        )
    gallery_labels = {record.label for record in task.gallery}
    missing = sorted({record.label for record in task.query} - gallery_labels)
    if missing:
        raise RuntimeError(
            f"Task {task.name} has {len(missing)} query identities without positives; "
            f"first={missing[:5]}."
        )
    query_paths = {record.relative_path.casefold() for record in task.query}
    gallery_paths = {record.relative_path.casefold() for record in task.gallery}
    overlap = query_paths & gallery_paths
    if overlap:
        raise RuntimeError(f"Task {task.name} reuses {len(overlap)} images across query/gallery.")


def build_training_protocol(
    records: Sequence[EvidenceRecord],
    dataset: str,
    val_fraction: float,
    seed: int,
    sues_train_ids: Sequence[str],
) -> TrainingProtocol:
    if dataset == "university1652":
        train_partition = [record for record in records if record.partition == "train"]
        official_ids = sorted(
            {record.label for record in train_partition if record.role == "train_satellite"}
            & {
                record.label
                for record in train_partition
                if record.role in {"train_drone", "train_street"}
            }
        )
        train_ids, validation_ids = stable_identity_holdout(
            official_ids, val_fraction, seed
        )
        train_set, val_set = set(train_ids), set(validation_ids)
        train_queries = [
            record
            for record in train_partition
            if record.label in train_set and record.role in {"train_drone", "train_street"}
        ]
        train_gallery = _group_by_label(
            record
            for record in train_partition
            if record.label in train_set and record.role == "train_satellite"
        )
        tasks: list[RetrievalTask] = []
        if val_set:
            val_drone = tuple(
                record
                for record in train_partition
                if record.label in val_set and record.role == "train_drone"
            )
            val_street = tuple(
                record
                for record in train_partition
                if record.label in val_set and record.role == "train_street"
            )
            val_satellite = tuple(
                record
                for record in train_partition
                if record.label in val_set and record.role == "train_satellite"
            )
            tasks.extend(
                (
                    RetrievalTask(
                        "validation_drone_to_satellite",
                        val_drone,
                        val_satellite,
                        "identity-disjoint official-train holdout",
                    ),
                    RetrievalTask(
                        "validation_satellite_to_drone",
                        val_satellite,
                        val_drone,
                        "identity-disjoint official-train holdout",
                    ),
                )
            )
            if val_street:
                tasks.append(
                    RetrievalTask(
                        "validation_street_to_satellite",
                        val_street,
                        val_satellite,
                        "identity-disjoint official-train holdout",
                    )
                )
    else:
        official_ids = list(sues_train_ids)
        train_ids, validation_ids = stable_identity_holdout(
            official_ids, val_fraction, seed
        )
        train_set, val_set = set(train_ids), set(validation_ids)
        train_queries = [
            record
            for record in records
            if record.view == "drone" and record.label in train_set
        ]
        train_gallery = _group_by_label(
            record
            for record in records
            if record.view == "satellite" and record.label in train_set
        )
        tasks = []
        if val_set:
            for altitude in SUES_ALTITUDES:
                val_drone = tuple(
                    record
                    for record in records
                    if record.view == "drone"
                    and record.label in val_set
                    and record.altitude == altitude
                )
                val_satellite = tuple(
                    record
                    for record in records
                    if record.view == "satellite" and record.label in val_set
                )
                tasks.extend(
                    (
                        RetrievalTask(
                            f"validation_uav_{altitude}m_to_satellite",
                            val_drone,
                            val_satellite,
                            "identity-disjoint official-120-train holdout",
                        ),
                        RetrievalTask(
                            f"validation_satellite_to_uav_{altitude}m",
                            val_satellite,
                            val_drone,
                            "identity-disjoint official-120-train holdout",
                        ),
                    )
                )

    if not train_queries or not train_gallery:
        raise RuntimeError("Training protocol produced no query/gallery records.")
    missing_gallery = sorted({record.label for record in train_queries} - set(train_gallery))
    if missing_gallery:
        raise RuntimeError(
            f"{len(missing_gallery)} training identities have no satellite positive."
        )
    train_paths = {record.relative_path.casefold() for record in train_queries}
    train_paths |= {
        record.relative_path.casefold()
        for values in train_gallery.values()
        for record in values
    }
    validation_paths = {
        record.relative_path.casefold()
        for task in tasks
        for record in (*task.query, *task.gallery)
    }
    if train_paths & validation_paths:
        raise RuntimeError("Train and validation image paths overlap.")
    for task in tasks:
        _assert_task(task)

    summary = {
        "split_kind": (
            "fixed_schedule_all_official_train_identities"
            if not validation_ids
            else "deterministic_identity_disjoint_holdout_within_official_train"
        ),
        "holdout_seed": seed,
        "holdout_fraction": val_fraction,
        "official_train_identity_count": len(official_ids),
        "fit_identity_count": len(train_ids),
        "validation_identity_count": len(validation_ids),
        "fit_query_image_count": len(train_queries),
        "fit_gallery_image_count": sum(len(value) for value in train_gallery.values()),
        "validation_tasks": {
            task.name: {"queries": len(task.query), "gallery": len(task.gallery)}
            for task in tasks
        },
        "official_test_images_used_by_train_or_validation": 0,
        "fit_identity_sha256": canonical_sha256(train_ids),
        "validation_identity_sha256": canonical_sha256(validation_ids),
    }
    return TrainingProtocol(
        train_queries=sorted(train_queries, key=lambda record: record.relative_path),
        train_gallery_by_label=train_gallery,
        validation_tasks=tasks,
        train_ids=train_ids,
        validation_ids=validation_ids,
        official_train_ids=official_ids,
        protocol_summary=summary,
    )


def build_official_evaluation_tasks(
    records: Sequence[EvidenceRecord],
    dataset: str,
    sues_train_ids: Sequence[str],
) -> list[RetrievalTask]:
    if dataset == "university1652":
        role = _group_by_label([])  # typed placeholder for the comprehension below
        del role
        by_role: dict[str, list[EvidenceRecord]] = defaultdict(list)
        for record in records:
            if record.partition == "test":
                by_role[record.role].append(record)
        tasks = [
            RetrievalTask(
                "university1652_drone_to_satellite",
                tuple(sorted(by_role["query_drone"], key=lambda item: item.relative_path)),
                tuple(sorted(by_role["gallery_satellite"], key=lambda item: item.relative_path)),
                "official test/query_drone -> test/gallery_satellite",
            ),
            RetrievalTask(
                "university1652_satellite_to_drone",
                tuple(sorted(by_role["query_satellite"], key=lambda item: item.relative_path)),
                tuple(sorted(by_role["gallery_drone"], key=lambda item: item.relative_path)),
                "official test/query_satellite -> test/gallery_drone",
            ),
            RetrievalTask(
                "university1652_street_to_satellite",
                tuple(sorted(by_role["query_street"], key=lambda item: item.relative_path)),
                tuple(sorted(by_role["gallery_satellite"], key=lambda item: item.relative_path)),
                "official test/query_street -> test/gallery_satellite",
            ),
        ]
    else:
        all_ids = {f"{index:04d}" for index in range(1, 201)}
        test_ids = all_ids - set(sues_train_ids)
        satellite_all = tuple(
            sorted(
                (
                    record
                    for record in records
                    if record.view == "satellite" and record.label in all_ids
                ),
                key=lambda item: item.relative_path,
            )
        )
        satellite_query = tuple(
            record for record in satellite_all if record.label in test_ids
        )
        if {record.label for record in satellite_all} != all_ids:
            missing = sorted(all_ids - {record.label for record in satellite_all})
            raise RuntimeError(
                f"SUES full satellite gallery must retain all 200 identities; missing {missing[:8]}."
            )
        tasks = []
        for altitude in SUES_ALTITUDES:
            drone_all = tuple(
                sorted(
                    (
                        record
                        for record in records
                        if record.view == "drone"
                        and record.altitude == altitude
                        and record.label in all_ids
                    ),
                    key=lambda item: item.relative_path,
                )
            )
            if {record.label for record in drone_all} != all_ids:
                missing = sorted(all_ids - {record.label for record in drone_all})
                raise RuntimeError(
                    f"SUES {altitude}m UAV gallery must retain all 200 identities; "
                    f"missing {missing[:8]}."
                )
            drone_query = tuple(record for record in drone_all if record.label in test_ids)
            tasks.extend(
                (
                    RetrievalTask(
                        f"sues200_uav_{altitude}m_to_satellite",
                        drone_query,
                        satellite_all,
                        "official 80 test IDs as query; all 200 satellite IDs in gallery",
                    ),
                    RetrievalTask(
                        f"sues200_satellite_to_uav_{altitude}m",
                        satellite_query,
                        drone_all,
                        f"official 80 test IDs as query; all 200 {altitude}m UAV IDs in gallery",
                    ),
                )
            )
    for task in tasks:
        _assert_task(task)
    return tasks


def build_transforms(resize_size: int, image_size: int) -> tuple[transforms.Compose, transforms.Compose]:
    if resize_size < image_size:
        raise ValueError("--resize-size must be at least --image-size.")
    train_transform = transforms.Compose(
        [
            transforms.RandomResizedCrop(
                image_size, scale=(0.70, 1.0), ratio=(0.75, 1.333333)
            ),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.ColorJitter(
                brightness=0.20, contrast=0.20, saturation=0.15, hue=0.03
            ),
            transforms.RandomGrayscale(p=0.05),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)
            ),
            transforms.RandomErasing(
                p=0.25, scale=(0.02, 0.15), ratio=(0.3, 3.3), value="random"
            ),
        ]
    )
    eval_transform = transforms.Compose(
        [
            transforms.Resize(resize_size, interpolation=transforms.InterpolationMode.BICUBIC),
            transforms.CenterCrop(image_size),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)
            ),
        ]
    )
    return train_transform, eval_transform


def load_rgb(path: Path) -> Image.Image:
    ImageFile.LOAD_TRUNCATED_IMAGES = False
    with Image.open(path) as image:
        return image.convert("RGB")


def variant_uses_visual(variant: str) -> bool:
    return variant in {"visual", "visual_content", "visual_style", "full"}


class FormalRetrievalModel(nn.Module):
    """Independent per-image visual/content/style encoders with strict switches."""

    def __init__(
        self,
        variant: str,
        backbone: str,
        embed_dim: int,
        dropout: float,
        pretrained: bool,
    ) -> None:
        super().__init__()
        if variant not in VARIANTS:
            raise ValueError(f"Unknown variant {variant!r}.")
        if backbone not in {"resnet18", "resnet50"}:
            raise ValueError("Only resnet18 and resnet50 are supported.")
        self.variant = variant
        self.backbone_name = backbone
        self.embed_dim = embed_dim

        self.visual_backbone: nn.Module | None = None
        self.visual_projection: nn.Module | None = None
        self.content_mlp: nn.Module | None = None
        self.style_mlp: nn.Module | None = None
        self.fusion: nn.Module | None = None

        if variant_uses_visual(variant):
            if backbone == "resnet18":
                weights = models.ResNet18_Weights.DEFAULT if pretrained else None
                visual = models.resnet18(weights=weights)
            else:
                weights = models.ResNet50_Weights.DEFAULT if pretrained else None
                visual = models.resnet50(weights=weights)
            visual_width = int(visual.fc.in_features)
            visual.fc = nn.Identity()
            self.visual_backbone = visual
            self.visual_projection = nn.Sequential(
                nn.Linear(visual_width, embed_dim),
                nn.LayerNorm(embed_dim),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(embed_dim, embed_dim),
            )
        if variant in {"content", "visual_content", "full"}:
            self.content_mlp = self._probability_mlp(CONTENT_DIM, embed_dim, dropout)
        if variant in {"style", "visual_style", "full"}:
            self.style_mlp = self._probability_mlp(STYLE_DIM, embed_dim, dropout)
        fusion_branches = {
            "visual_content": 2,
            "visual_style": 2,
            "full": 3,
        }.get(variant)
        if fusion_branches is not None:
            self.fusion = nn.Sequential(
                nn.LayerNorm(embed_dim * fusion_branches),
                nn.Linear(embed_dim * fusion_branches, embed_dim * 2),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(embed_dim * 2, embed_dim),
                nn.LayerNorm(embed_dim),
            )
        self.logit_scale = nn.Parameter(torch.tensor(math.log(1.0 / 0.07)))

    @staticmethod
    def _probability_mlp(width: int, embed_dim: int, dropout: float) -> nn.Sequential:
        return nn.Sequential(
            nn.LayerNorm(width),
            nn.Linear(width, embed_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(embed_dim, embed_dim),
            nn.LayerNorm(embed_dim),
        )

    def encode_image(
        self,
        image: torch.Tensor,
        content_prob: torch.Tensor,
        style_prob: torch.Tensor,
    ) -> torch.Tensor:
        """Encode one batch of images without any paired-image or gallery input."""

        if self.variant == "visual":
            if self.visual_backbone is None or self.visual_projection is None:
                raise AssertionError("visual branch is not initialized")
            return F.normalize(
                self.visual_projection(self.visual_backbone(image)), dim=-1
            )
        if self.variant == "content":
            if self.content_mlp is None:
                raise AssertionError("content branch is not initialized")
            return F.normalize(self.content_mlp(content_prob), dim=-1)
        if self.variant == "style":
            if self.style_mlp is None:
                raise AssertionError("style branch is not initialized")
            return F.normalize(self.style_mlp(style_prob), dim=-1)
        if self.visual_backbone is None or self.visual_projection is None:
            raise AssertionError("fusion variant visual branch is not initialized")
        if self.fusion is None:
            raise AssertionError("fusion variant head is not initialized")
        visual = F.normalize(
            self.visual_projection(self.visual_backbone(image)), dim=-1
        )
        branches = [visual]
        if self.variant in {"visual_content", "full"}:
            if self.content_mlp is None:
                raise AssertionError("content branch is not initialized")
            branches.append(F.normalize(self.content_mlp(content_prob), dim=-1))
        if self.variant in {"visual_style", "full"}:
            if self.style_mlp is None:
                raise AssertionError("style branch is not initialized")
            branches.append(F.normalize(self.style_mlp(style_prob), dim=-1))
        return F.normalize(self.fusion(torch.cat(branches, dim=-1)), dim=-1)

    def similarity_logits(self, first: torch.Tensor, second: torch.Tensor) -> torch.Tensor:
        scale = self.logit_scale.clamp(
            min=math.log(1.0 / 0.2), max=math.log(100.0)
        ).exp()
        return scale * first @ second.t()


def pretrained_weight_record(
    backbone: str,
    enabled: bool,
) -> dict[str, Any]:
    if not enabled:
        return {
            "enabled": False,
            "weight_enum": None,
            "source_url": None,
            "cached_file": None,
            "cached_file_sha256": None,
        }
    weights = (
        models.ResNet18_Weights.DEFAULT
        if backbone == "resnet18"
        else models.ResNet50_Weights.DEFAULT
    )
    filename = str(weights.url).rsplit("/", 1)[-1]
    cached_file = Path(torch.hub.get_dir()) / "checkpoints" / filename
    if not cached_file.is_file():
        raise FileNotFoundError(
            "Torchvision reported a successful pretrained initialization, but "
            f"the expected immutable weight file is missing: {cached_file}"
        )
    return {
        "enabled": True,
        "weight_enum": str(weights),
        "source_url": str(weights.url),
        "cached_file": str(cached_file.resolve()),
        "cached_file_sha256": sha256_file(cached_file),
        "cached_file_bytes": cached_file.stat().st_size,
    }


class PairTrainingDataset(Dataset[dict[str, Any]]):
    def __init__(
        self,
        query_records: Sequence[EvidenceRecord],
        gallery_by_label: Mapping[str, Sequence[EvidenceRecord]],
        store: EvidenceStore,
        transform: transforms.Compose,
        variant: str,
        seed: int,
    ) -> None:
        self.query_records = list(query_records)
        self.gallery_by_label = {
            label: list(records) for label, records in gallery_by_label.items()
        }
        self.store = store
        self.transform = transform
        self.variant = variant
        self.seed = seed
        self.epoch = 0
        labels = sorted(self.gallery_by_label)
        self.label_to_int = {label: index for index, label in enumerate(labels)}
        self.query_labels = [record.label for record in self.query_records]

    def set_epoch(self, epoch: int) -> None:
        self.epoch = epoch

    def __len__(self) -> int:
        return len(self.query_records)

    def _gallery_for(self, query: EvidenceRecord, index: int) -> EvidenceRecord:
        candidates = self.gallery_by_label[query.label]
        digest = hashlib.sha256(
            f"{self.seed}:{self.epoch}:{index}:{query.relative_path}".encode("utf-8")
        ).digest()
        selected = int.from_bytes(digest[:8], "little") % len(candidates)
        return candidates[selected]

    def _image(self, record: EvidenceRecord) -> torch.Tensor:
        if variant_uses_visual(self.variant):
            return self.transform(load_rgb(record.absolute_path))
        return torch.empty(0, dtype=torch.float32)

    def __getitem__(self, index: int) -> dict[str, Any]:
        query = self.query_records[index]
        gallery = self._gallery_for(query, index)
        return {
            "query_image": self._image(query),
            "gallery_image": self._image(gallery),
            "query_content": torch.from_numpy(
                self.store.content_probs[query.evidence_index]
            ),
            "gallery_content": torch.from_numpy(
                self.store.content_probs[gallery.evidence_index]
            ),
            "query_style": torch.from_numpy(self.store.style_probs[query.evidence_index]),
            "gallery_style": torch.from_numpy(
                self.store.style_probs[gallery.evidence_index]
            ),
            "label": torch.tensor(self.label_to_int[query.label], dtype=torch.long),
        }


class IdentityBalancedBatchSampler(BatchSampler):
    """Cover every query by default while retaining multi-positive identity chunks.

    ``samples_per_class_per_epoch=0`` means every query image is used at least
    once.  A positive value provides an explicit per-identity epoch budget.
    ``steps_per_epoch=0`` leaves the epoch untruncated; a positive value is an
    explicit override.  Defaults therefore impose neither a class cap nor a
    step cap.
    """

    def __init__(
        self,
        labels: Sequence[str],
        identities_per_batch: int,
        instances_per_identity: int,
        samples_per_class_per_epoch: int,
        steps_per_epoch: int,
        seed: int,
    ) -> None:
        if identities_per_batch < 2:
            raise ValueError("--identities-per-batch must be at least 2.")
        if instances_per_identity < 2:
            raise ValueError(
                "--instances-per-identity must be at least 2 for multi-positive InfoNCE."
            )
        if samples_per_class_per_epoch < 0 or steps_per_epoch < 0:
            raise ValueError("Sampling limits cannot be negative.")
        self.identities_per_batch = identities_per_batch
        self.instances_per_identity = instances_per_identity
        self.samples_per_class_per_epoch = samples_per_class_per_epoch
        self.steps_per_epoch = steps_per_epoch
        self.seed = seed
        self.epoch = 0
        self.by_label: dict[str, list[int]] = defaultdict(list)
        for index, label in enumerate(labels):
            self.by_label[label].append(index)
        if len(self.by_label) < identities_per_batch:
            raise ValueError(
                f"Only {len(self.by_label)} identities are available, fewer than "
                f"--identities-per-batch={identities_per_batch}."
            )
        self._cached_epoch: int | None = None
        self._cached_batches: list[list[int]] = []

    def set_epoch(self, epoch: int) -> None:
        self.epoch = epoch
        self._cached_epoch = None
        self._cached_batches = []

    def _indices_for_label(self, indices: list[int], rng: random.Random) -> list[int]:
        shuffled = indices[:]
        rng.shuffle(shuffled)
        limit = self.samples_per_class_per_epoch
        if limit > 0:
            if len(shuffled) >= limit:
                shuffled = shuffled[:limit]
            else:
                shuffled.extend(rng.choices(indices, k=limit - len(shuffled)))
        remainder = len(shuffled) % self.instances_per_identity
        if remainder:
            shuffled.extend(
                rng.choices(indices, k=self.instances_per_identity - remainder)
            )
        return shuffled

    def _build(self) -> list[list[int]]:
        rng = random.Random(self.seed + 1_000_003 * self.epoch)
        chunks_by_label: dict[str, list[list[int]]] = {}
        covered_real_indices: set[int] = set()
        for label, indices in sorted(self.by_label.items()):
            selected = self._indices_for_label(indices, rng)
            covered_real_indices.update(selected)
            chunks = [
                selected[start : start + self.instances_per_identity]
                for start in range(0, len(selected), self.instances_per_identity)
            ]
            rng.shuffle(chunks)
            chunks_by_label[label] = chunks

        if self.samples_per_class_per_epoch == 0:
            expected = set(range(sum(len(values) for values in self.by_label.values())))
            if not expected <= covered_real_indices:
                missing = sorted(expected - covered_real_indices)
                raise AssertionError(
                    "Full-coverage sampler omitted real query indices; "
                    f"first missing={missing[:10]}."
                )

        total_chunks = sum(len(chunks) for chunks in chunks_by_label.values())
        maximum_class_chunks = max(len(chunks) for chunks in chunks_by_label.values())
        fixed_batch_count = max(
            math.ceil(total_chunks / self.identities_per_batch),
            maximum_class_chunks,
        )
        assigned: list[list[tuple[str, list[int]]]] = [
            [] for _ in range(fixed_batch_count)
        ]

        # Allocate the largest identities first.  Each identity contributes at
        # most one chunk to a batch, and least-loaded-bin assignment keeps the
        # number of optimizer steps invariant across epochs and seeds.
        label_order = list(chunks_by_label)
        rng.shuffle(label_order)
        label_order.sort(key=lambda label: -len(chunks_by_label[label]))
        for label in label_order:
            chunks = chunks_by_label[label]
            available = [
                index
                for index, batch_chunks in enumerate(assigned)
                if len(batch_chunks) < self.identities_per_batch
            ]
            rng.shuffle(available)
            available.sort(key=lambda index: len(assigned[index]))
            if len(available) < len(chunks):
                raise RuntimeError(
                    "Fixed identity-balanced allocation has insufficient batch "
                    f"capacity for {label}: chunks={len(chunks)}, "
                    f"available={len(available)}."
                )
            for batch_index, chunk in zip(available[: len(chunks)], chunks):
                assigned[batch_index].append((label, chunk))

        batches: list[list[int]] = []
        all_labels = list(self.by_label)
        for batch_chunks in assigned:
            present = {label for label, _ in batch_chunks}
            if len(present) != len(batch_chunks):
                raise AssertionError("An identity was assigned twice to one batch.")
            missing_identities = self.identities_per_batch - len(batch_chunks)
            if missing_identities:
                fillers = [label for label in all_labels if label not in present]
                for label in rng.sample(fillers, k=missing_identities):
                    batch_chunks.append(
                        (
                            label,
                            rng.choices(
                                self.by_label[label],
                                k=self.instances_per_identity,
                            ),
                        )
                    )
            batch = [index for _, chunk in batch_chunks for index in chunk]
            if len(batch) != self.identities_per_batch * self.instances_per_identity:
                raise AssertionError("Identity-balanced batch has an invalid size.")
            rng.shuffle(batch)
            batches.append(batch)

        if self.steps_per_epoch > 0:
            if len(batches) > self.steps_per_epoch:
                batches = batches[: self.steps_per_epoch]
            while len(batches) < self.steps_per_epoch:
                labels = rng.sample(
                    list(self.by_label), k=self.identities_per_batch
                )
                batch = []
                for label in labels:
                    batch.extend(
                        rng.choices(
                            self.by_label[label], k=self.instances_per_identity
                        )
                    )
                rng.shuffle(batch)
                batches.append(batch)
        return batches

    def _ensure(self) -> None:
        if self._cached_epoch != self.epoch:
            self._cached_batches = self._build()
            self._cached_epoch = self.epoch

    def __iter__(self) -> Iterator[list[int]]:
        self._ensure()
        yield from self._cached_batches

    def __len__(self) -> int:
        self._ensure()
        return len(self._cached_batches)


class RecordDataset(Dataset[dict[str, Any]]):
    def __init__(
        self,
        records: Sequence[EvidenceRecord],
        store: EvidenceStore,
        transform: transforms.Compose,
        variant: str,
    ) -> None:
        self.records = list(records)
        self.store = store
        self.transform = transform
        self.variant = variant

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> dict[str, Any]:
        record = self.records[index]
        image = (
            self.transform(load_rgb(record.absolute_path))
            if variant_uses_visual(self.variant)
            else torch.empty(0, dtype=torch.float32)
        )
        return {
            "image": image,
            "content": torch.from_numpy(self.store.content_probs[record.evidence_index]),
            "style": torch.from_numpy(self.store.style_probs[record.evidence_index]),
            "relative_path": record.relative_path,
        }


def seed_everything(seed: int) -> None:
    os.environ.setdefault("PYTHONHASHSEED", str(seed))
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)


def seed_worker(worker_id: int) -> None:
    del worker_id
    worker_seed = torch.initial_seed() % (2**32)
    np.random.seed(worker_seed)
    random.seed(worker_seed)


def capture_rng_state() -> dict[str, Any]:
    return {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch_cpu": torch.get_rng_state(),
        "torch_cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
    }


def restore_rng_state(state: Mapping[str, Any]) -> None:
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.set_rng_state(state["torch_cpu"])
    if torch.cuda.is_available() and state.get("torch_cuda"):
        torch.cuda.set_rng_state_all(state["torch_cuda"])


def choose_device(requested: str) -> torch.device:
    if requested == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    device = torch.device(requested)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but torch.cuda.is_available() is false.")
    return device


def environment_manifest(device: torch.device) -> dict[str, Any]:
    packages: dict[str, str] = {}
    for name in ("numpy", "Pillow", "torch", "torchvision"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = "not-installed"
    device_info: dict[str, Any] = {"requested_or_selected": str(device)}
    if device.type == "cuda":
        props = torch.cuda.get_device_properties(device)
        device_info.update(
            {
                "name": props.name,
                "total_memory_bytes": props.total_memory,
                "compute_capability": f"{props.major}.{props.minor}",
                "cuda_runtime": torch.version.cuda,
                "cudnn": torch.backends.cudnn.version(),
                "device_index": device.index if device.index is not None else torch.cuda.current_device(),
            }
        )
    else:
        device_info.update({"processor": platform.processor(), "machine": platform.machine()})
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "packages": packages,
        "torch_cuda_available": torch.cuda.is_available(),
        "device": device_info,
    }


def inventory_hash(
    records: Sequence[EvidenceRecord], mode: str
) -> dict[str, Any]:
    unique = {
        record.relative_path: record.absolute_path for record in records
    }
    digest = hashlib.sha256()
    total_bytes = 0
    for relative_path, absolute_path in sorted(unique.items()):
        stat = absolute_path.stat()
        total_bytes += stat.st_size
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(stat.st_size).encode("ascii"))
        digest.update(b"\0")
        if mode == "content":
            digest.update(sha256_file(absolute_path).encode("ascii"))
        elif mode == "metadata":
            digest.update(str(stat.st_mtime_ns).encode("ascii"))
        elif mode != "none":
            raise ValueError(mode)
        digest.update(b"\n")
    return {
        "mode": mode,
        "sha256": digest.hexdigest() if mode != "none" else "",
        "file_count": len(unique),
        "total_bytes": total_bytes,
    }


def protocol_membership_hash(tasks: Sequence[RetrievalTask]) -> str:
    payload = [
        {
            "name": task.name,
            "protocol": task.protocol,
            "query": [record.relative_path for record in task.query],
            "gallery": [record.relative_path for record in task.gallery],
        }
        for task in tasks
    ]
    return canonical_sha256(payload)


def multi_positive_infonce(
    logits: torch.Tensor,
    first_labels: torch.Tensor,
    second_labels: torch.Tensor,
) -> torch.Tensor:
    positive = first_labels[:, None].eq(second_labels[None, :])
    if not bool(positive.any(dim=1).all()):
        raise RuntimeError("A batch contains an anchor without a positive.")
    positive_logits = logits.masked_fill(~positive, -torch.inf)
    return (
        torch.logsumexp(logits, dim=1)
        - torch.logsumexp(positive_logits, dim=1)
    ).mean()


def symmetric_multi_positive_loss(
    model: FormalRetrievalModel,
    query_embeddings: torch.Tensor,
    gallery_embeddings: torch.Tensor,
    labels: torch.Tensor,
) -> torch.Tensor:
    logits = model.similarity_logits(query_embeddings, gallery_embeddings)
    return 0.5 * (
        multi_positive_infonce(logits, labels, labels)
        + multi_positive_infonce(logits.t(), labels, labels)
    )


def amp_context(device: torch.device, enabled: bool) -> contextlib.AbstractContextManager[Any]:
    if enabled and device.type == "cuda":
        return torch.autocast(device_type="cuda", dtype=torch.float16)
    return contextlib.nullcontext()


def make_grad_scaler(enabled: bool) -> Any:
    try:
        return torch.amp.GradScaler("cuda", enabled=enabled)
    except (AttributeError, TypeError):
        return torch.cuda.amp.GradScaler(enabled=enabled)


def move_batch_tensor(batch: Mapping[str, Any], key: str, device: torch.device) -> torch.Tensor:
    return batch[key].to(device, non_blocking=device.type == "cuda")


def supervised_batch_accuracy(
    query_embeddings: torch.Tensor,
    gallery_embeddings: torch.Tensor,
    labels: torch.Tensor,
) -> float:
    nearest = (query_embeddings @ gallery_embeddings.t()).argmax(dim=1)
    return float(labels[nearest].eq(labels).float().mean().item())


@torch.inference_mode()
def encode_records(
    model: FormalRetrievalModel,
    records: Sequence[EvidenceRecord],
    store: EvidenceStore,
    transform: transforms.Compose,
    device: torch.device,
    batch_size: int,
    workers: int,
    amp_enabled: bool,
    seed: int,
) -> dict[str, np.ndarray]:
    unique_by_path: dict[str, EvidenceRecord] = {}
    for record in records:
        unique_by_path.setdefault(record.relative_path.casefold(), record)
    ordered = sorted(unique_by_path.values(), key=lambda item: item.relative_path)
    dataset = RecordDataset(ordered, store, transform, model.variant)
    generator = torch.Generator()
    generator.manual_seed(seed)
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=workers,
        pin_memory=device.type == "cuda",
        worker_init_fn=seed_worker,
        generator=generator,
        persistent_workers=False,
    )
    model.eval()
    encoded: dict[str, np.ndarray] = {}
    cursor = 0
    for batch in loader:
        with amp_context(device, amp_enabled):
            features = model.encode_image(
                move_batch_tensor(batch, "image", device),
                move_batch_tensor(batch, "content", device),
                move_batch_tensor(batch, "style", device),
            )
        values = features.float().cpu().numpy()
        for offset, value in enumerate(values):
            encoded[ordered[cursor + offset].relative_path.casefold()] = value
        cursor += len(values)
    if cursor != len(ordered):
        raise RuntimeError("Feature extraction count mismatch.")
    return encoded


def official_trapezoid_ap(positive_positions: np.ndarray) -> float:
    if positive_positions.size == 0:
        return 0.0
    positions = positive_positions.astype(np.float64)
    indices = np.arange(len(positions), dtype=np.float64)
    precision = (indices + 1.0) / (positions + 1.0)
    old_precision = np.ones_like(positions)
    nonzero = positions != 0.0
    old_precision[nonzero] = indices[nonzero] / positions[nonzero]
    return float(np.mean((old_precision + precision) * 0.5))


def rank_task(
    task: RetrievalTask,
    encoded: Mapping[str, np.ndarray],
    chunk_size: int,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    query_features = np.stack(
        [encoded[record.relative_path.casefold()] for record in task.query]
    ).astype(np.float32, copy=False)
    gallery_features = np.stack(
        [encoded[record.relative_path.casefold()] for record in task.gallery]
    ).astype(np.float32, copy=False)
    query_labels = np.asarray([record.label for record in task.query])
    gallery_labels = np.asarray([record.label for record in task.gallery])
    recalls = {1: 0, 5: 0, 10: 0, 20: 0}
    aps = np.empty(len(task.query), dtype=np.float32)
    reciprocal_ranks = np.empty(len(task.query), dtype=np.float32)
    margins = np.empty(len(task.query), dtype=np.float32)
    correct = np.empty(len(task.query), dtype=np.bool_)
    top1_indices = np.empty(len(task.query), dtype=np.int64)

    for start in range(0, len(task.query), chunk_size):
        stop = min(start + chunk_size, len(task.query))
        scores = query_features[start:stop] @ gallery_features.T
        # Stable tie-breaking makes repeated CPU ranking deterministic.
        order = np.argsort(-scores, axis=1, kind="stable")
        for local_index in range(stop - start):
            query_index = start + local_index
            ranking = order[local_index]
            relevant = gallery_labels[ranking] == query_labels[query_index]
            positions = np.flatnonzero(relevant)
            if positions.size == 0:
                raise RuntimeError(
                    f"No positive for {task.name} query {task.query[query_index].relative_path}."
                )
            first_rank = int(positions[0])
            for k in recalls:
                recalls[k] += int(first_rank < min(k, len(task.gallery)))
            aps[query_index] = official_trapezoid_ap(positions)
            reciprocal_ranks[query_index] = 1.0 / (first_rank + 1.0)
            top1 = int(ranking[0])
            top1_indices[query_index] = top1
            correct[query_index] = bool(first_rank == 0)
            margins[query_index] = (
                float(scores[local_index, ranking[0]] - scores[local_index, ranking[1]])
                if len(ranking) > 1
                else math.inf
            )

    count = len(task.query)
    metrics: dict[str, Any] = {
        "unit": "fraction",
        "queries": count,
        "gallery": len(task.gallery),
        "query_identities": len(set(query_labels.tolist())),
        "gallery_identities": len(set(gallery_labels.tolist())),
        "r_at_1": recalls[1] / count,
        "r_at_5": recalls[5] / count,
        "r_at_10": recalls[10] / count,
        "r_at_20": recalls[20] / count,
        "official_trapezoid_mAP": float(aps.mean()),
        "MRR": float(reciprocal_ranks.mean()),
        "mean_top1_margin": float(np.mean(margins)),
    }
    arrays = {
        "margin": margins,
        "correct": correct,
        "per_query_official_trapezoid_AP": aps,
        "reciprocal_rank": reciprocal_ranks,
        "query_paths": np.asarray([record.relative_path for record in task.query]),
        "query_labels": query_labels,
        "top1_gallery_indices": top1_indices,
        "top1_gallery_paths": np.asarray(
            [task.gallery[index].relative_path for index in top1_indices]
        ),
        "top1_gallery_labels": gallery_labels[top1_indices],
    }
    return metrics, arrays


@torch.inference_mode()
def evaluate_tasks(
    model: FormalRetrievalModel,
    tasks: Sequence[RetrievalTask],
    store: EvidenceStore,
    transform: transforms.Compose,
    device: torch.device,
    batch_size: int,
    workers: int,
    amp_enabled: bool,
    seed: int,
    chunk_size: int,
    arrays_dir: Path | None,
) -> dict[str, dict[str, Any]]:
    union: list[EvidenceRecord] = []
    for task in tasks:
        union.extend(task.query)
        union.extend(task.gallery)
    encoded = encode_records(
        model,
        union,
        store,
        transform,
        device,
        batch_size,
        workers,
        amp_enabled,
        seed,
    )
    results: dict[str, dict[str, Any]] = {}
    for task in tasks:
        metrics, arrays = rank_task(task, encoded, chunk_size)
        metrics["protocol"] = task.protocol
        results[task.name] = metrics
        if arrays_dir is not None:
            arrays_dir.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(arrays_dir / f"{slugify(task.name)}_per_query.npz", **arrays)
        LOGGER.info(
            "%s: R@1 %.2f, R@5 %.2f, R@10 %.2f, R@20 %.2f, "
            "trapezoid mAP %.2f, MRR %.2f",
            task.name,
            100.0 * metrics["r_at_1"],
            100.0 * metrics["r_at_5"],
            100.0 * metrics["r_at_10"],
            100.0 * metrics["r_at_20"],
            100.0 * metrics["official_trapezoid_mAP"],
            100.0 * metrics["MRR"],
        )
    return results


def mean_validation_metric(metrics: Mapping[str, Mapping[str, Any]]) -> float:
    if not metrics:
        raise RuntimeError("No validation metrics were produced.")
    return float(
        np.mean(
            [float(result["official_trapezoid_mAP"]) for result in metrics.values()]
        )
    )


def optimizer_for_model(
    model: FormalRetrievalModel,
    learning_rate: float,
    backbone_lr_multiplier: float,
    weight_decay: float,
) -> torch.optim.Optimizer:
    backbone_params: list[nn.Parameter] = []
    other_params: list[nn.Parameter] = []
    backbone_ids = (
        {id(parameter) for parameter in model.visual_backbone.parameters()}
        if model.visual_backbone is not None
        else set()
    )
    for parameter in model.parameters():
        if not parameter.requires_grad:
            continue
        if id(parameter) in backbone_ids:
            backbone_params.append(parameter)
        else:
            other_params.append(parameter)
    groups: list[dict[str, Any]] = []
    if backbone_params:
        groups.append(
            {"params": backbone_params, "lr": learning_rate * backbone_lr_multiplier}
        )
    if other_params:
        groups.append({"params": other_params, "lr": learning_rate})
    return torch.optim.AdamW(groups, lr=learning_rate, weight_decay=weight_decay)


def cosine_warmup_scheduler(
    optimizer: torch.optim.Optimizer, total_steps: int, warmup_steps: int
) -> torch.optim.lr_scheduler.LambdaLR:
    if total_steps <= 0:
        raise ValueError("Training has zero optimizer steps.")
    warmup_steps = min(max(0, warmup_steps), max(0, total_steps - 1))

    def multiplier(step: int) -> float:
        if warmup_steps and step < warmup_steps:
            return float(step + 1) / float(warmup_steps)
        progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
        progress = min(max(progress, 0.0), 1.0)
        return 0.5 * (1.0 + math.cos(math.pi * progress))

    return torch.optim.lr_scheduler.LambdaLR(optimizer, multiplier)


def resolve_resume(output_dir: Path, requested: str) -> Path | None:
    if requested.lower() in {"", "none", "false", "0"}:
        return None
    if requested.lower() in {"last", "best"}:
        path = output_dir / f"{requested.lower()}.pt"
    else:
        path = Path(requested).expanduser()
    return path.resolve(strict=True)


def checkpoint_payload(
    *,
    epoch: int,
    model: FormalRetrievalModel,
    optimizer: torch.optim.Optimizer,
    scheduler: torch.optim.lr_scheduler.LRScheduler,
    scaler: Any,
    best_metric: float,
    best_epoch: int,
    epochs_without_improvement: int,
    history: list[dict[str, Any]],
    immutable_config: dict[str, Any],
    run_config_sha256: str,
    model_config: dict[str, Any],
    evidence_schema: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "epoch": epoch,
        "model_state": model.state_dict(),
        "optimizer_state": optimizer.state_dict(),
        "scheduler_state": scheduler.state_dict(),
        "scaler_state": scaler.state_dict(),
        "best_validation_mAP": best_metric,
        "best_epoch": best_epoch,
        "epochs_without_improvement": epochs_without_improvement,
        "history": history,
        "rng_state": capture_rng_state(),
        "immutable_config": immutable_config,
        "run_config_sha256": run_config_sha256,
        "model_config": model_config,
        "evidence_schema": evidence_schema,
    }


def configure_logging(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    LOGGER.setLevel(logging.INFO)
    LOGGER.handlers.clear()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(formatter)
    file_handler = logging.FileHandler(output_dir / "run.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    LOGGER.addHandler(stream)
    LOGGER.addHandler(file_handler)


def records_for_training_inventory(protocol: TrainingProtocol) -> list[EvidenceRecord]:
    records = list(protocol.train_queries)
    for values in protocol.train_gallery_by_label.values():
        records.extend(values)
    for task in protocol.validation_tasks:
        records.extend(task.query)
        records.extend(task.gallery)
    return records


def args_to_json(args: argparse.Namespace) -> dict[str, Any]:
    return {
        key: [str(item) for item in value]
        if isinstance(value, list) and value and isinstance(value[0], Path)
        else str(value)
        if isinstance(value, Path)
        else value
        for key, value in vars(args).items()
    }


def run_train(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir).expanduser().resolve()
    configure_logging(output_dir)
    dataset = normalize_dataset_name(args.dataset)
    device = choose_device(args.device)
    seed_everything(args.seed)
    data_root = Path(args.data_root).expanduser().resolve(strict=True)
    evidence_paths = [Path(path) for path in args.evidence]
    store = EvidenceStore.load(evidence_paths)
    records = derive_all_records(store, data_root, dataset)
    manifest_path = Path(args.sues_manifest).expanduser() if args.sues_manifest else None
    sues_train_ids, sues_manifest_info = parse_sues_manifest(manifest_path)
    protocol = build_training_protocol(
        records,
        dataset,
        args.val_fraction,
        args.seed,
        sues_train_ids,
    )
    train_transform, eval_transform = build_transforms(
        args.resize_size, args.image_size
    )
    train_dataset = PairTrainingDataset(
        protocol.train_queries,
        protocol.train_gallery_by_label,
        store,
        train_transform,
        args.variant,
        args.seed,
    )
    batch_sampler = IdentityBalancedBatchSampler(
        train_dataset.query_labels,
        args.identities_per_batch,
        args.instances_per_identity,
        args.samples_per_class_per_epoch,
        args.steps_per_epoch,
        args.seed,
    )
    audited_step_counts: list[int] = []
    for audit_epoch in range(args.epochs):
        batch_sampler.set_epoch(audit_epoch)
        audited_step_counts.append(len(batch_sampler))
    if len(set(audited_step_counts)) != 1:
        raise RuntimeError(
            "The formal sampler must expose a fixed optimizer-step count across "
            f"the frozen schedule; observed {sorted(set(audited_step_counts))}."
        )
    batch_sampler.set_epoch(0)
    steps_in_epoch = audited_step_counts[0]
    total_steps = steps_in_epoch * args.epochs
    warmup_steps = steps_in_epoch * args.warmup_epochs

    resume_path = resolve_resume(output_dir, args.resume)
    model_config = {
        "variant": args.variant,
        "backbone": args.backbone,
        "embed_dim": args.embed_dim,
        "dropout": args.dropout,
        "image_size": args.image_size,
        "resize_size": args.resize_size,
    }
    model = FormalRetrievalModel(
        variant=args.variant,
        backbone=args.backbone,
        embed_dim=args.embed_dim,
        dropout=args.dropout,
        pretrained=args.pretrained and resume_path is None,
    ).to(device)
    model_config["pretrained_initialization"] = pretrained_weight_record(
        args.backbone,
        bool(args.pretrained and variant_uses_visual(args.variant)),
    )
    optimizer = optimizer_for_model(
        model,
        args.learning_rate,
        args.backbone_lr_multiplier,
        args.weight_decay,
    )
    scheduler = cosine_warmup_scheduler(optimizer, total_steps, warmup_steps)
    amp_enabled = bool(args.amp and device.type == "cuda")
    scaler = make_grad_scaler(amp_enabled)

    evidence_schema = {
        "content_dim": CONTENT_DIM,
        "style_dim": STYLE_DIM,
        "content_candidates": list(store.content_candidates),
        "style_candidates": list(store.style_candidates),
    }
    inventory = inventory_hash(
        records_for_training_inventory(protocol), args.data_hash_mode
    )
    immutable_config = {
        "schema_version": SCHEMA_VERSION,
        "command": "train",
        "dataset": dataset,
        "data_root": str(data_root),
        "model": model_config,
        "optimization": {
            "epochs": args.epochs,
            "learning_rate": args.learning_rate,
            "backbone_lr_multiplier": args.backbone_lr_multiplier,
            "weight_decay": args.weight_decay,
            "warmup_epochs": args.warmup_epochs,
            "gradient_clip_norm": args.gradient_clip_norm,
            "identities_per_batch": args.identities_per_batch,
            "instances_per_identity": args.instances_per_identity,
            "samples_per_class_per_epoch": args.samples_per_class_per_epoch,
            "steps_per_epoch_requested": args.steps_per_epoch,
            "steps_per_epoch_actual": steps_in_epoch,
            "sampler_schedule_audited_epochs": args.epochs,
            "sampler_step_count_fixed_across_epochs": True,
            "sampler_step_count_schedule_sha256": canonical_sha256(
                audited_step_counts
            ),
            "amp": amp_enabled,
        },
        "selection": {
            "metric": (
                "mean official trapezoid mAP over fixed validation tasks"
                if protocol.validation_tasks
                else "none; pre-specified final epoch with no validation selection"
            ),
            "patience": args.patience,
        },
        "seed": args.seed,
        "protocol": protocol.protocol_summary,
        "train_ids": protocol.train_ids,
        "validation_ids": protocol.validation_ids,
        "sues_manifest": sues_manifest_info if dataset == "sues200" else None,
        "evidence_schema": evidence_schema,
        "evidence_caches": [dataclasses.asdict(item) for item in store.cache_descriptors],
        "image_inventory": inventory,
        "code_sha256": sha256_file(Path(__file__).resolve()),
    }
    run_config_sha = canonical_sha256(immutable_config)
    run_config = {
        "created_utc": utc_now(),
        "immutable_config": immutable_config,
        "run_config_sha256": run_config_sha,
        "environment": environment_manifest(device),
        "cli": args_to_json(args),
    }
    atomic_json_dump(output_dir / "run_config.json", run_config)
    LOGGER.info(
        "Training %s/%s on %s: %d fit IDs, %d validation IDs, %d query images, "
        "%d optimizer steps/epoch (no default class or step cap).",
        dataset,
        args.variant,
        device,
        len(protocol.train_ids),
        len(protocol.validation_ids),
        len(protocol.train_queries),
        steps_in_epoch,
    )

    start_epoch = 0
    best_metric = -math.inf
    best_epoch = -1
    epochs_without_improvement = 0
    history: list[dict[str, Any]] = []
    if resume_path is not None:
        # Keep CPU/CUDA RNG tensors on their original devices while loading.
        state = load_torch_checkpoint(resume_path, "cpu")
        if state.get("run_config_sha256") != run_config_sha:
            raise RuntimeError(
                "Resume checkpoint configuration hash differs from the current run. "
                "Use the exact original model, data, split, sampling, and optimization settings."
            )
        model.load_state_dict(state["model_state"], strict=True)
        optimizer.load_state_dict(state["optimizer_state"])
        scheduler.load_state_dict(state["scheduler_state"])
        scaler.load_state_dict(state["scaler_state"])
        restore_rng_state(state["rng_state"])
        start_epoch = int(state["epoch"]) + 1
        best_metric = float(state["best_validation_mAP"])
        best_epoch = int(state["best_epoch"])
        epochs_without_improvement = int(state["epochs_without_improvement"])
        history = list(state["history"])
        LOGGER.info("Resumed %s at epoch %d.", resume_path, start_epoch)

    training_started = time.perf_counter()
    status = "completed"
    for epoch in range(start_epoch, args.epochs):
        epoch_started = time.perf_counter()
        train_dataset.set_epoch(epoch)
        batch_sampler.set_epoch(epoch)
        if len(batch_sampler) != steps_in_epoch:
            raise RuntimeError(
                f"Sampler step count changed at epoch {epoch}: "
                f"{len(batch_sampler)} != {steps_in_epoch}."
            )
        # An epoch-derived worker seed makes augmentation exactly resumable;
        # it does not depend on how many prior DataLoader iterators existed.
        epoch_generator = torch.Generator()
        epoch_generator.manual_seed(args.seed + 1_000_003 * epoch)
        loader = DataLoader(
            train_dataset,
            batch_sampler=batch_sampler,
            num_workers=args.workers,
            pin_memory=device.type == "cuda",
            worker_init_fn=seed_worker,
            generator=epoch_generator,
            persistent_workers=False,
        )
        model.train()
        loss_sum = 0.0
        accuracy_sum = 0.0
        example_count = 0
        optimizer.zero_grad(set_to_none=True)
        for batch in loader:
            labels = move_batch_tensor(batch, "label", device)
            with amp_context(device, amp_enabled):
                query_embeddings = model.encode_image(
                    move_batch_tensor(batch, "query_image", device),
                    move_batch_tensor(batch, "query_content", device),
                    move_batch_tensor(batch, "query_style", device),
                )
                gallery_embeddings = model.encode_image(
                    move_batch_tensor(batch, "gallery_image", device),
                    move_batch_tensor(batch, "gallery_content", device),
                    move_batch_tensor(batch, "gallery_style", device),
                )
                loss = symmetric_multi_positive_loss(
                    model, query_embeddings, gallery_embeddings, labels
                )
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            if args.gradient_clip_norm > 0:
                nn.utils.clip_grad_norm_(model.parameters(), args.gradient_clip_norm)
            scaler.step(optimizer)
            scaler.update()
            optimizer.zero_grad(set_to_none=True)
            with torch.no_grad():
                model.logit_scale.clamp_(
                    min=math.log(1.0 / 0.2), max=math.log(100.0)
                )
            scheduler.step()
            count = int(labels.numel())
            loss_sum += float(loss.detach().item()) * count
            accuracy_sum += (
                supervised_batch_accuracy(
                    query_embeddings.detach(), gallery_embeddings.detach(), labels
                )
                * count
            )
            example_count += count

        if protocol.validation_tasks:
            validation = evaluate_tasks(
                model,
                protocol.validation_tasks,
                store,
                eval_transform,
                device,
                args.eval_batch_size,
                args.workers,
                amp_enabled,
                args.seed,
                args.eval_chunk_size,
                arrays_dir=None,
            )
            selection_metric = mean_validation_metric(validation)
            improved = selection_metric > best_metric + args.min_delta
            if improved:
                best_metric = selection_metric
                best_epoch = epoch
                epochs_without_improvement = 0
            else:
                epochs_without_improvement += 1
            selection_basis = "identity-disjoint validation macro mAP"
        else:
            # A zero validation fraction is the final-fit protocol: the epoch
            # count is fixed before test evaluation and every official
            # training identity is used.  best.pt intentionally tracks the
            # final completed epoch; no test or train metric selects it.
            validation = {}
            selection_metric = None
            improved = True
            best_metric = 0.0
            best_epoch = epoch
            epochs_without_improvement = 0
            selection_basis = "pre-specified final epoch (no validation selection)"
        epoch_row = {
            "epoch": epoch,
            "train_loss": loss_sum / max(example_count, 1),
            "train_batch_top1": accuracy_sum / max(example_count, 1),
            "examples_seen": example_count,
            "optimizer_steps": len(batch_sampler),
            "learning_rates": [group["lr"] for group in optimizer.param_groups],
            "validation_selection_mAP": selection_metric,
            "selection_basis": selection_basis,
            "validation": validation,
            "improved": improved,
            "elapsed_seconds": time.perf_counter() - epoch_started,
        }
        history.append(epoch_row)
        payload = checkpoint_payload(
            epoch=epoch,
            model=model,
            optimizer=optimizer,
            scheduler=scheduler,
            scaler=scaler,
            best_metric=best_metric,
            best_epoch=best_epoch,
            epochs_without_improvement=epochs_without_improvement,
            history=history,
            immutable_config=immutable_config,
            run_config_sha256=run_config_sha,
            model_config=model_config,
            evidence_schema=evidence_schema,
        )
        atomic_torch_save(output_dir / "last.pt", payload)
        if improved:
            atomic_torch_save(output_dir / "best.pt", payload)
        atomic_json_dump(output_dir / "history.json", history)
        running_manifest = {
            "schema_version": SCHEMA_VERSION,
            "status": "running",
            "updated_utc": utc_now(),
            "run_config_sha256": run_config_sha,
            "last_completed_epoch": epoch,
            "best_epoch": best_epoch,
            "best_validation_mAP": (
                best_metric if protocol.validation_tasks else None
            ),
            "history_rows": len(history),
        }
        running_manifest["payload_sha256"] = canonical_sha256(running_manifest)
        atomic_json_dump(output_dir / "run_manifest.json", running_manifest)
        if protocol.validation_tasks:
            LOGGER.info(
                "Epoch %d/%d | loss %.6f | batch R@1 %.2f | validation mAP %.2f | "
                "best %.2f at epoch %d | %.1fs",
                epoch + 1,
                args.epochs,
                epoch_row["train_loss"],
                100.0 * epoch_row["train_batch_top1"],
                100.0 * float(selection_metric),
                100.0 * best_metric,
                best_epoch + 1,
                epoch_row["elapsed_seconds"],
            )
        else:
            LOGGER.info(
                "Epoch %d/%d | loss %.6f | batch R@1 %.2f | "
                "no validation (fixed 80-epoch schedule) | %.1fs",
                epoch + 1,
                args.epochs,
                epoch_row["train_loss"],
                100.0 * epoch_row["train_batch_top1"],
                epoch_row["elapsed_seconds"],
            )
        if (
            protocol.validation_tasks
            and args.patience > 0
            and epochs_without_improvement >= args.patience
        ):
            status = "early_stopped_by_fixed_validation"
            LOGGER.info(
                "Early stopping after %d epochs without validation improvement.",
                epochs_without_improvement,
            )
            break

    artifact_hashes: dict[str, Any] = {}
    for name in ("run_config.json", "history.json", "last.pt", "best.pt", "run.log"):
        path = output_dir / name
        if path.exists():
            artifact_hashes[name] = {
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
    final_manifest = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "completed_utc": utc_now(),
        "run_config_sha256": run_config_sha,
        "epochs_completed": len(history),
        "best_epoch": best_epoch,
        "best_validation_mAP": best_metric if protocol.validation_tasks else None,
        "total_training_seconds": time.perf_counter() - training_started,
        "sample_scale": protocol.protocol_summary,
        "dependencies_and_device": environment_manifest(device),
        "artifacts": artifact_hashes,
        "test_protocol_was_evaluated": False,
        "note": (
            (
                "The train subcommand used all official training identities for a "
                "pre-specified fixed epoch schedule; best.pt is the final completed "
                "epoch and no validation or test metric selected it."
            )
            if not protocol.validation_tasks
            else (
                "The train subcommand used only the official training identities and "
                "its fixed identity-disjoint validation holdout. Run the evaluate "
                "subcommand separately after model selection."
            )
        ),
    }
    final_manifest["payload_sha256"] = canonical_sha256(final_manifest)
    atomic_json_dump(output_dir / "run_manifest.json", final_manifest)


def validate_checkpoint_evidence_schema(
    checkpoint: Mapping[str, Any], store: EvidenceStore
) -> None:
    expected = checkpoint.get("evidence_schema", {})
    actual = {
        "content_dim": CONTENT_DIM,
        "style_dim": STYLE_DIM,
        "content_candidates": list(store.content_candidates),
        "style_candidates": list(store.style_candidates),
    }
    if expected != actual:
        raise RuntimeError(
            "Checkpoint and evaluation cache use different evidence candidate semantics/order."
        )


def write_metrics_csv(path: Path, results: Mapping[str, Mapping[str, Any]]) -> None:
    fields = (
        "task",
        "queries",
        "gallery",
        "query_identities",
        "gallery_identities",
        "r_at_1",
        "r_at_5",
        "r_at_10",
        "r_at_20",
        "official_trapezoid_mAP",
        "MRR",
        "mean_top1_margin",
        "protocol",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for task, metrics in results.items():
                writer.writerow({"task": task, **{key: metrics.get(key, "") for key in fields[1:]}})
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def run_evaluate(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir).expanduser().resolve()
    configure_logging(output_dir)
    dataset = normalize_dataset_name(args.dataset)
    device = choose_device(args.device)
    seed_everything(args.seed)
    data_root = Path(args.data_root).expanduser().resolve(strict=True)
    checkpoint_path = Path(args.checkpoint).expanduser().resolve(strict=True)
    checkpoint_sha = sha256_file(checkpoint_path)
    checkpoint = load_torch_checkpoint(checkpoint_path, "cpu")
    if checkpoint.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError(
            f"Checkpoint schema {checkpoint.get('schema_version')!r} is not {SCHEMA_VERSION!r}."
        )
    checkpoint_dataset = checkpoint.get("immutable_config", {}).get("dataset")
    if checkpoint_dataset != dataset:
        raise RuntimeError(
            f"Checkpoint was trained for {checkpoint_dataset}, requested {dataset}."
        )

    store = EvidenceStore.load([Path(path) for path in args.evidence])
    validate_checkpoint_evidence_schema(checkpoint, store)
    records = derive_all_records(store, data_root, dataset)
    manifest_path = Path(args.sues_manifest).expanduser() if args.sues_manifest else None
    sues_train_ids, sues_manifest_info = parse_sues_manifest(manifest_path)
    if dataset == "sues200":
        training_manifest = checkpoint["immutable_config"].get("sues_manifest", {})
        if training_manifest.get("sha256") != sues_manifest_info["sha256"]:
            raise RuntimeError(
                "SUES official manifest hash differs between training and evaluation."
            )
    tasks = build_official_evaluation_tasks(records, dataset, sues_train_ids)
    model_config = dict(checkpoint["model_config"])
    model = FormalRetrievalModel(
        variant=model_config["variant"],
        backbone=model_config["backbone"],
        embed_dim=int(model_config["embed_dim"]),
        dropout=float(model_config["dropout"]),
        pretrained=False,
    )
    model.load_state_dict(checkpoint["model_state"], strict=True)
    model.to(device)
    _, eval_transform = build_transforms(
        int(model_config["resize_size"]), int(model_config["image_size"])
    )
    amp_enabled = bool(args.amp and device.type == "cuda")
    evaluation_records = [
        record for task in tasks for record in (*task.query, *task.gallery)
    ]
    inventory = inventory_hash(evaluation_records, args.data_hash_mode)
    started = time.perf_counter()
    arrays_dir = output_dir / "per_query_arrays"
    results = evaluate_tasks(
        model,
        tasks,
        store,
        eval_transform,
        device,
        args.eval_batch_size,
        args.workers,
        amp_enabled,
        args.seed,
        args.eval_chunk_size,
        arrays_dir,
    )
    metrics_payload = {
        "schema_version": SCHEMA_VERSION,
        "unit": "fraction",
        "AP_definition": (
            "Official trapezoidal interpolation used by the University-1652/SUES "
            "reference evaluator: each relevant rank contributes the average of "
            "precision immediately before and at that recall step."
        ),
        "full_gallery": True,
        "results": results,
    }
    atomic_json_dump(output_dir / "metrics.json", metrics_payload)
    write_metrics_csv(output_dir / "metrics.csv", results)

    artifacts: dict[str, Any] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name not in {"evaluation_manifest.json", "run.log"}:
            artifacts[path.relative_to(output_dir).as_posix()] = {
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
    task_scale = {
        task.name: {
            "queries": len(task.query),
            "gallery_images": len(task.gallery),
            "query_identities": len({record.label for record in task.query}),
            "gallery_identities": len({record.label for record in task.gallery}),
            "protocol": task.protocol,
        }
        for task in tasks
    }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "status": "completed",
        "completed_utc": utc_now(),
        "dataset": dataset,
        "checkpoint": {
            "path": str(checkpoint_path),
            "sha256": checkpoint_sha,
            "selected_training_epoch": int(checkpoint["epoch"]),
            "training_run_config_sha256": checkpoint["run_config_sha256"],
            "variant": model_config["variant"],
        },
        "evidence_caches": [dataclasses.asdict(item) for item in store.cache_descriptors],
        "evidence_schema": checkpoint["evidence_schema"],
        "sues_manifest": sues_manifest_info if dataset == "sues200" else None,
        "protocol_membership_sha256": protocol_membership_hash(tasks),
        "task_scale": task_scale,
        "image_inventory": inventory,
        "environment": environment_manifest(device),
        "amp": amp_enabled,
        "elapsed_seconds": time.perf_counter() - started,
        "artifacts": artifacts,
        "leakage_controls": {
            "labels_and_splits_from_cache_used": False,
            "labels_and_splits_derived_from_dataset_paths_and_official_manifest": True,
            "each_image_encoded_independently": True,
            "test_used_during_training_or_model_selection": False,
            "all_official_queries_used": True,
            "all_official_gallery_images_used": True,
        },
    }
    manifest["payload_sha256"] = canonical_sha256(manifest)
    atomic_json_dump(output_dir / "evaluation_manifest.json", manifest)


def default_sues_manifest_path() -> str:
    return str(
        Path(__file__).resolve().parents[1]
        / "manifests"
        / "sues200_official_train_ids.yaml"
    )


def add_common_data_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dataset",
        required=True,
        choices=("university1652", "sues200"),
        help="Official dataset protocol to derive from paths.",
    )
    parser.add_argument("--data-root", required=True, help="Dataset root containing train/test or SUES views.")
    parser.add_argument(
        "--evidence",
        required=True,
        nargs="+",
        help="One or more generate_clip_image_evidence NPZ files with matching .meta.json.",
    )
    parser.add_argument(
        "--sues-manifest",
        default=default_sues_manifest_path(),
        help="Shipped official fixed-120 SUES manifest; embedded exact fallback is used if absent.",
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--device", default="auto", help="auto, cpu, cuda, or cuda:N.")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument(
        "--data-hash-mode",
        choices=("content", "metadata", "none"),
        default="content",
        help="Content hashing is the formal default; metadata/none are explicit weaker modes.",
    )
    parser.add_argument(
        "--amp",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Use CUDA automatic mixed precision when available.",
    )
    parser.add_argument("--eval-batch-size", type=int, default=128)
    parser.add_argument(
        "--eval-chunk-size",
        type=int,
        default=128,
        help="Query rows per exact full-gallery ranking chunk; no gallery subsampling occurs.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Formal, leakage-controlled image-level training and exact official "
            "full-gallery retrieval evaluation."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    train = subparsers.add_parser(
        "train",
        help="Fit on official training identities and select only on a fixed train holdout.",
    )
    add_common_data_arguments(train)
    train.add_argument("--variant", choices=VARIANTS, required=True)
    train.add_argument("--backbone", choices=("resnet18", "resnet50"), default="resnet50")
    train.add_argument("--embed-dim", type=int, default=512)
    train.add_argument("--dropout", type=float, default=0.20)
    train.add_argument(
        "--pretrained",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Initialize active visual backbone from torchvision ImageNet weights.",
    )
    train.add_argument("--image-size", type=int, default=224)
    train.add_argument("--resize-size", type=int, default=256)
    train.add_argument("--epochs", type=int, default=80)
    train.add_argument("--warmup-epochs", type=int, default=5)
    train.add_argument("--learning-rate", type=float, default=3e-4)
    train.add_argument("--backbone-lr-multiplier", type=float, default=0.1)
    train.add_argument("--weight-decay", type=float, default=1e-4)
    train.add_argument("--gradient-clip-norm", type=float, default=5.0)
    train.add_argument("--identities-per-batch", type=int, default=16)
    train.add_argument("--instances-per-identity", type=int, default=4)
    train.add_argument(
        "--samples-per-class-per-epoch",
        type=int,
        default=0,
        help="0 uses every query image; positive values impose an explicit per-class budget.",
    )
    train.add_argument(
        "--steps-per-epoch",
        type=int,
        default=0,
        help="0 leaves the full sampler untruncated; positive values explicitly override it.",
    )
    train.add_argument("--val-fraction", type=float, default=0.10)
    train.add_argument(
        "--patience",
        type=int,
        default=15,
        help="Validation epochs without improvement before stopping; 0 disables.",
    )
    train.add_argument("--min-delta", type=float, default=1e-5)
    train.add_argument(
        "--resume",
        default="none",
        help="none, last, best, or an explicit checkpoint path.",
    )

    evaluate = subparsers.add_parser(
        "evaluate",
        help="Evaluate a selected checkpoint on every official full-query/full-gallery task.",
    )
    add_common_data_arguments(evaluate)
    evaluate.add_argument("--checkpoint", required=True)
    return parser


def validate_cli(args: argparse.Namespace) -> None:
    if args.workers < 0:
        raise ValueError("--workers cannot be negative.")
    if args.eval_batch_size <= 0 or args.eval_chunk_size <= 0:
        raise ValueError("Evaluation batch and chunk sizes must be positive.")
    if args.command == "train":
        if args.epochs <= 0:
            raise ValueError("--epochs must be positive.")
        if args.warmup_epochs < 0 or args.warmup_epochs >= args.epochs:
            raise ValueError("--warmup-epochs must be nonnegative and smaller than --epochs.")
        if args.embed_dim <= 0:
            raise ValueError("--embed-dim must be positive.")
        if not 0.0 <= args.dropout < 1.0:
            raise ValueError("--dropout must lie in [0, 1).")
        if args.learning_rate <= 0 or args.weight_decay < 0:
            raise ValueError("Learning rate must be positive and weight decay nonnegative.")
        if not 0.0 < args.backbone_lr_multiplier <= 1.0:
            raise ValueError("--backbone-lr-multiplier must lie in (0, 1].")
        if args.patience < 0:
            raise ValueError("--patience cannot be negative.")


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    validate_cli(args)
    if args.command == "train":
        run_train(args)
    elif args.command == "evaluate":
        run_evaluate(args)
    else:
        raise AssertionError(args.command)


if __name__ == "__main__":
    main()
