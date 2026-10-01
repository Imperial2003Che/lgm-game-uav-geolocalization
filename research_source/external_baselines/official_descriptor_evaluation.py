"""Fail-closed full-query descriptor evaluation for locally trained baselines."""

from __future__ import annotations

from dataclasses import dataclass
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


METRIC_SCHEMA = "lgm-game.external-descriptor-metrics.v1"
EVALUATION_CONFIG_SCHEMA = "lgm-game.external-official-evaluation-config.v1"
EVALUATION_MANIFEST_SCHEMA = "lgm-game.external-official-evaluation-manifest.v1"
EVALUATION_STATUS_SCHEMA = "lgm-game.external-official-evaluation-status.v1"
ALL_FITS_GATE_SCHEMA = "lgm-game.transactions-t1-all-fits-gate.v1"
TEST_INVENTORY_GATE_SCHEMA = (
    "lgm-game.transactions-t1-official-test-inventory-gate.v1"
)
ARRAY_FIELDS = {
    "margin",
    "correct",
    "per_query_official_trapezoid_AP",
    "reciprocal_rank",
    "query_paths",
    "query_labels",
    "top1_gallery_indices",
    "top1_gallery_paths",
    "top1_gallery_labels",
}


class DescriptorEvaluationError(RuntimeError):
    """External descriptor evidence is incomplete or semantically inconsistent."""


def canonical_path(value: Any) -> str:
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return str(value).strip().replace("\\", "/").casefold()


def canonical_sha256(payload: Any) -> str:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


@dataclass(frozen=True)
class DescriptorTask:
    name: str
    protocol: str
    query_descriptors: np.ndarray
    query_labels: np.ndarray
    query_paths: np.ndarray
    gallery_descriptors: np.ndarray
    gallery_labels: np.ndarray
    gallery_paths: np.ndarray
    score_type: str = "inner_product"


def official_trapezoid_ap(positive_positions: np.ndarray) -> float:
    positions = np.asarray(positive_positions, dtype=np.int64)
    if positions.ndim != 1 or positions.size <= 0 or (positions < 0).any():
        raise DescriptorEvaluationError("Positive positions are invalid.")
    values = positions.astype(np.float64)
    offsets = np.arange(len(values), dtype=np.float64)
    precision = (offsets + 1.0) / (values + 1.0)
    old_precision = np.ones_like(values)
    nonzero = values != 0.0
    old_precision[nonzero] = offsets[nonzero] / values[nonzero]
    return float(np.mean((old_precision + precision) * 0.5))


def _validate_task(task: DescriptorTask) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
]:
    query = np.asarray(task.query_descriptors, dtype=np.float32)
    gallery = np.asarray(task.gallery_descriptors, dtype=np.float32)
    query_labels = np.asarray(
        [str(value) for value in np.asarray(task.query_labels).reshape(-1)],
        dtype=str,
    )
    gallery_labels = np.asarray(
        [str(value) for value in np.asarray(task.gallery_labels).reshape(-1)],
        dtype=str,
    )
    query_paths = np.asarray(
        [canonical_path(value) for value in np.asarray(task.query_paths).reshape(-1)],
        dtype=str,
    )
    gallery_paths = np.asarray(
        [
            canonical_path(value)
            for value in np.asarray(task.gallery_paths).reshape(-1)
        ],
        dtype=str,
    )
    if (
        query.ndim != 2
        or gallery.ndim != 2
        or query.shape[1] != gallery.shape[1]
        or query.shape[0] != len(query_labels)
        or query.shape[0] != len(query_paths)
        or gallery.shape[0] != len(gallery_labels)
        or gallery.shape[0] != len(gallery_paths)
        or query.shape[0] <= 0
        or gallery.shape[0] <= 0
        or query.shape[1] <= 0
    ):
        raise DescriptorEvaluationError(f"{task.name}: descriptor/task shapes differ.")
    if not np.isfinite(query).all() or not np.isfinite(gallery).all():
        raise DescriptorEvaluationError(f"{task.name}: descriptors are non-finite.")
    if (np.linalg.norm(query, axis=1) <= 0.0).any() or (
        np.linalg.norm(gallery, axis=1) <= 0.0
    ).any():
        raise DescriptorEvaluationError(f"{task.name}: descriptor has zero norm.")
    if (
        len(set(query_paths.tolist())) != len(query_paths)
        or len(set(gallery_paths.tolist())) != len(gallery_paths)
        or any(not value for value in query_paths)
        or any(not value for value in gallery_paths)
    ):
        raise DescriptorEvaluationError(
            f"{task.name}: query/gallery paths are empty or duplicated."
        )
    missing = sorted(set(query_labels.tolist()) - set(gallery_labels.tolist()))
    if missing:
        raise DescriptorEvaluationError(
            f"{task.name}: query identities lack gallery positives: {missing[:8]}"
        )
    return (
        query,
        gallery,
        query_labels,
        gallery_labels,
        query_paths,
        gallery_paths,
    )


def evaluate_descriptor_task(
    task: DescriptorTask,
    *,
    chunk_size: int = 128,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    if chunk_size <= 0:
        raise DescriptorEvaluationError("Descriptor ranking chunk must be positive.")
    (
        query,
        gallery,
        query_labels,
        gallery_labels,
        query_paths,
        gallery_paths,
    ) = _validate_task(task)
    count = len(query)
    recalls = {1: 0, 5: 0, 10: 0, 20: 0}
    aps = np.empty(count, dtype=np.float32)
    reciprocal = np.empty(count, dtype=np.float32)
    margins = np.empty(count, dtype=np.float32)
    correct = np.empty(count, dtype=np.bool_)
    top1_indices = np.empty(count, dtype=np.int64)
    gallery_squared_norm = np.sum(gallery * gallery, axis=1, dtype=np.float32)
    for start in range(0, count, chunk_size):
        stop = min(start + chunk_size, count)
        dot_products = query[start:stop] @ gallery.T
        if task.score_type == "inner_product":
            scores = dot_products
            score_backend = (
                "NumPy float32 query @ gallery.T; stable descending argsort"
            )
        elif task.score_type == "squared_l2":
            query_squared_norm = np.sum(
                query[start:stop] * query[start:stop],
                axis=1,
                dtype=np.float32,
            )
            squared_distance = (
                query_squared_norm[:, None]
                + gallery_squared_norm[None, :]
                - np.float32(2.0) * dot_products
            )
            scores = -squared_distance
            score_backend = (
                "NumPy float32 negative squared L2 via norm expansion; "
                "stable descending argsort"
            )
        else:
            raise DescriptorEvaluationError(
                f"{task.name}: unsupported score type {task.score_type!r}."
            )
        order = np.argsort(-scores, axis=1, kind="stable")
        for local in range(stop - start):
            index = start + local
            ranking = order[local]
            positive = gallery_labels[ranking] == query_labels[index]
            positions = np.flatnonzero(positive)
            if positions.size <= 0:
                raise DescriptorEvaluationError(
                    f"{task.name}: query {query_paths[index]} has no positive."
                )
            first = int(positions[0])
            for cutoff in recalls:
                recalls[cutoff] += int(first < min(cutoff, len(gallery)))
            aps[index] = official_trapezoid_ap(positions)
            reciprocal[index] = 1.0 / (first + 1.0)
            top1 = int(ranking[0])
            top1_indices[index] = top1
            correct[index] = bool(first == 0)
            margins[index] = (
                float(scores[local, ranking[0]] - scores[local, ranking[1]])
                if len(ranking) > 1
                else math.inf
            )
    metrics = {
        "unit": "fraction",
        "queries": count,
        "gallery": len(gallery),
        "query_identities": len(set(query_labels.tolist())),
        "gallery_identities": len(set(gallery_labels.tolist())),
        "descriptor_dimension": int(query.shape[1]),
        "r_at_1": recalls[1] / count,
        "r_at_5": recalls[5] / count,
        "r_at_10": recalls[10] / count,
        "r_at_20": recalls[20] / count,
        "official_trapezoid_mAP": float(aps.mean()),
        "MRR": float(reciprocal.mean()),
        "mean_top1_margin": float(margins.mean()),
        "protocol": task.protocol,
        "score_type": task.score_type,
        "score_backend": score_backend,
    }
    arrays = {
        "margin": margins,
        "correct": correct,
        "per_query_official_trapezoid_AP": aps,
        "reciprocal_rank": reciprocal,
        "query_paths": query_paths,
        "query_labels": query_labels,
        "top1_gallery_indices": top1_indices,
        "top1_gallery_paths": gallery_paths[top1_indices],
        "top1_gallery_labels": gallery_labels[top1_indices],
    }
    return metrics, arrays


def recompute_metrics(
    arrays_path: Path,
) -> dict[str, float]:
    with np.load(arrays_path, allow_pickle=False) as archive:
        if set(archive.files) != ARRAY_FIELDS:
            raise DescriptorEvaluationError(
                f"{arrays_path}: per-query array field set changed."
            )
        values = {name: np.asarray(archive[name]) for name in ARRAY_FIELDS}
    lengths = {len(value) for value in values.values() if value.ndim == 1}
    if any(value.ndim != 1 for value in values.values()) or len(lengths) != 1:
        raise DescriptorEvaluationError(
            f"{arrays_path}: per-query vector shapes differ."
        )
    count = lengths.pop()
    if count <= 0:
        raise DescriptorEvaluationError(f"{arrays_path}: per-query data is empty.")
    query_labels = np.asarray(values["query_labels"]).astype(str)
    top1_labels = np.asarray(values["top1_gallery_labels"]).astype(str)
    correct = np.asarray(values["correct"], dtype=np.bool_)
    if not np.array_equal(correct, query_labels == top1_labels):
        raise DescriptorEvaluationError(
            f"{arrays_path}: correctness and Top-1 labels disagree."
        )
    aps = np.asarray(
        values["per_query_official_trapezoid_AP"],
        dtype=np.float64,
    )
    reciprocal = np.asarray(values["reciprocal_rank"], dtype=np.float64)
    margin = np.asarray(values["margin"], dtype=np.float64)
    if (
        not np.isfinite(aps).all()
        or not np.isfinite(reciprocal).all()
        or not np.isfinite(margin).all()
        or (aps < 0.0).any()
        or (aps > 1.0).any()
        or (reciprocal <= 0.0).any()
        or (reciprocal > 1.0).any()
    ):
        raise DescriptorEvaluationError(
            f"{arrays_path}: per-query metric values are invalid."
        )
    ranks = np.rint(1.0 / reciprocal).astype(np.int64)
    if not np.allclose(
        reciprocal,
        1.0 / ranks,
        rtol=2e-6,
        atol=2e-7,
    ) or not np.array_equal(correct, ranks == 1):
        raise DescriptorEvaluationError(
            f"{arrays_path}: reciprocal ranks are inconsistent."
        )
    return {
        "queries": float(count),
        "r_at_1": float(correct.mean()),
        "r_at_5": float(np.mean(ranks <= 5)),
        "r_at_10": float(np.mean(ranks <= 10)),
        "r_at_20": float(np.mean(ranks <= 20)),
        "official_trapezoid_mAP": float(aps.mean()),
        "MRR": float(reciprocal.mean()),
        "mean_top1_margin": float(margin.mean()),
    }


IMAGE_EXTENSIONS = frozenset(
    {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
)
UNIVERSITY1652_T1_ROLES = (
    "query_drone",
    "gallery_satellite",
    "query_satellite",
    "gallery_drone",
)
UNIVERSITY1652_T1_EXPECTED_SCALE = {
    "query_drone": {"images": 37855, "identities": 701},
    "gallery_satellite": {"images": 951, "identities": 951},
    "query_satellite": {"images": 701, "identities": 701},
    "gallery_drone": {"images": 51355, "identities": 951},
}
UNIVERSITY1652_T1_EXPECTED_INVENTORY = {
    "total_images": 90862,
    "total_bytes": 5704769123,
    "membership_sha256": (
        "19c26d413c79b77785ca05c02962ed30135c9e2c43a712a3db52c8dda59ff6b7"
    ),
    "roles": {
        "query_drone": {
            "bytes": 2392313456,
            "membership_sha256": (
                "3735cbdd4acb7bda37c0ee15d0dff93b58ed1902936d7d798c75245fb93a4720"
            ),
        },
        "gallery_satellite": {
            "bytes": 53483814,
            "membership_sha256": (
                "eafd0a660290bd3500616f80b89ffaea475dd6d34b3f980592fd4e05c8efd5d7"
            ),
        },
        "query_satellite": {
            "bytes": 39737395,
            "membership_sha256": (
                "dbe2e9ba39bb19b5d81b5a06c39f9f7de47a9e7898f04ce1ed2ec1cd74f2fdb9"
            ),
        },
        "gallery_drone": {
            "bytes": 3219234458,
            "membership_sha256": (
                "2c11adbaf902fb5dc73041ba7453d84a9bb725833f90ec8e378d81d7855060a6"
            ),
        },
    },
}
SUES200_ALTITUDES = ("150", "200", "250", "300")
SUES200_TRAIN_MANIFEST_SHA256 = (
    "c1386d5c746aca48bbb2793ed1ee19d6cd7330a7f5f1b27a5ec43727317ec226"
)
SUES200_T1_EXPECTED_SCALE = {
    "satellite_all": {"images": 200, "identities": 200},
    "drone_150_all": {"images": 10000, "identities": 200},
    "drone_200_all": {"images": 10000, "identities": 200},
    "drone_250_all": {"images": 10000, "identities": 200},
    "drone_300_all": {"images": 10000, "identities": 200},
}
# Filled from the same path/size algorithm used below.  The full content hash
# is frozen only after all seven fits complete, because official-test access is
# prohibited before that gate.
SUES200_T1_EXPECTED_INVENTORY = {
    "total_images": 40200,
    "total_bytes": 5693433493,
    "membership_sha256": (
        "dc6742e45599231b53f16730771cb5eab45d5b0ef6aed8d1663324207a15f706"
    ),
    "roles": {
        "satellite_all": {
            "bytes": 69450154,
            "membership_sha256": (
                "c38d09d7fd1b560bb1a4c0d5139b0e0b89abf0b7b40f156598ea1c4d31b0e203"
            ),
        },
        "drone_150_all": {
            "bytes": 1423851503,
            "membership_sha256": (
                "fe974d3fc3b20d66486ba925b490319631b89fcd9fca61d50083b18b9e88d105"
            ),
        },
        "drone_200_all": {
            "bytes": 1409126823,
            "membership_sha256": (
                "a007245c42bc223b5bdef65235f55ee1b9518ac23a901f658c53dc67020d8681"
            ),
        },
        "drone_250_all": {
            "bytes": 1401733635,
            "membership_sha256": (
                "b292dc07356a083e33261efbd33b9bdafc27b7898d6ce6f085f6bb1a96f7891e"
            ),
        },
        "drone_300_all": {
            "bytes": 1389271378,
            "membership_sha256": (
                "799716f42cfeb167e655455ac7d6c6c9d7b0051d1b85eb7f5c2d3f7469de347e"
            ),
        },
    },
}


@dataclass(frozen=True)
class FrozenImageView:
    role: str
    paths: tuple[Path, ...]
    relative_paths: np.ndarray
    labels: np.ndarray


def sha256_file(path: Path, chunk_bytes: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            block = stream.read(chunk_bytes)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def atomic_write_json(path: Path, payload: Any) -> None:
    serialized = canonical_json_bytes(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    if temporary.exists():
        raise DescriptorEvaluationError(
            f"Refusing to overwrite stale temporary file: {temporary}"
        )
    temporary.write_bytes(serialized)
    temporary.replace(path)


def write_immutable_json(path: Path, payload: Any) -> str:
    serialized = canonical_json_bytes(payload)
    digest = hashlib.sha256(serialized).hexdigest()
    if path.exists():
        if path.read_bytes() != serialized:
            raise DescriptorEvaluationError(
                f"Existing immutable JSON differs: {path}"
            )
        return digest
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(serialized)
    return digest


def _scan_image_view(test_root: Path, role: str) -> FrozenImageView:
    role_root = test_root / role
    if not role_root.is_dir():
        raise DescriptorEvaluationError(
            f"University-1652 official test role is absent: {role_root}"
        )
    class_dirs = sorted(
        (path for path in role_root.iterdir() if path.is_dir()),
        key=lambda path: path.name,
    )
    if not class_dirs or any(not path.name.isdigit() for path in class_dirs):
        raise DescriptorEvaluationError(
            f"{role}: identity directories are empty or non-numeric."
        )
    paths: list[Path] = []
    labels: list[str] = []
    relative_paths: list[str] = []
    for class_dir in class_dirs:
        nested_dirs = [path for path in class_dir.rglob("*") if path.is_dir()]
        if nested_dirs:
            raise DescriptorEvaluationError(
                f"{role}: nested identity directories are not part of the protocol."
            )
        candidates = sorted(
            (path for path in class_dir.iterdir() if path.is_file()),
            key=lambda path: path.name,
        )
        unsupported = [
            path.name
            for path in candidates
            if path.suffix.casefold() not in IMAGE_EXTENSIONS
        ]
        if unsupported:
            raise DescriptorEvaluationError(
                f"{role}/{class_dir.name}: unsupported files found: "
                f"{unsupported[:8]}"
            )
        if not candidates:
            raise DescriptorEvaluationError(
                f"{role}/{class_dir.name}: identity has no images."
            )
        for path in candidates:
            paths.append(path.resolve())
            labels.append(class_dir.name)
            relative_paths.append(path.relative_to(test_root).as_posix())
    expected = UNIVERSITY1652_T1_EXPECTED_SCALE[role]
    if len(paths) != expected["images"] or len(class_dirs) != expected["identities"]:
        raise DescriptorEvaluationError(
            f"{role}: expected {expected}, got "
            f"images={len(paths)}, identities={len(class_dirs)}."
        )
    return FrozenImageView(
        role=role,
        paths=tuple(paths),
        relative_paths=np.asarray(relative_paths, dtype=str),
        labels=np.asarray(labels, dtype=str),
    )


def scan_university1652_official_test(
    test_root: Path,
    *,
    hash_contents: bool = True,
) -> tuple[dict[str, FrozenImageView], dict[str, Any]]:
    """Freeze the two public University-1652 cross-view test directions.

    The inventory is intentionally computed only after a completed-fit gate has
    passed in a framework adapter.  It never participates in fitting or model
    selection.
    """

    root = test_root.resolve(strict=True)
    views = {
        role: _scan_image_view(root, role)
        for role in UNIVERSITY1652_T1_ROLES
    }
    membership_digest = hashlib.sha256()
    content_digest = hashlib.sha256()
    total_bytes = 0
    role_rows: dict[str, Any] = {}
    for role in UNIVERSITY1652_T1_ROLES:
        view = views[role]
        role_bytes = 0
        role_membership = hashlib.sha256()
        role_content = hashlib.sha256()
        for path, relative, label in zip(
            view.paths,
            view.relative_paths.tolist(),
            view.labels.tolist(),
            strict=True,
        ):
            size = path.stat().st_size
            row = (
                f"{relative}\0{label}\0{size}\n"
            ).encode("utf-8")
            membership_digest.update(row)
            role_membership.update(row)
            content_digest.update(row)
            role_content.update(row)
            if hash_contents:
                file_hash = sha256_file(path).encode("ascii")
                content_digest.update(file_hash)
                content_digest.update(b"\n")
                role_content.update(file_hash)
                role_content.update(b"\n")
            role_bytes += size
            total_bytes += size
        role_rows[role] = {
            "images": len(view.paths),
            "identities": len(set(view.labels.tolist())),
            "bytes": role_bytes,
            "membership_sha256": role_membership.hexdigest(),
            "content_sha256": (
                role_content.hexdigest() if hash_contents else None
            ),
        }
    inventory = {
        "dataset": "University-1652",
        "split": "official test",
        "roles": role_rows,
        "total_images": sum(len(view.paths) for view in views.values()),
        "total_bytes": total_bytes,
        "membership_sha256": membership_digest.hexdigest(),
        "content_sha256": content_digest.hexdigest() if hash_contents else None,
        "content_hashed": hash_contents,
        "relative_to": "University-1652/test",
    }
    return views, inventory


def validate_university1652_test_inventory(
    inventory: Mapping[str, Any],
) -> None:
    expected = UNIVERSITY1652_T1_EXPECTED_INVENTORY
    for field in ("total_images", "total_bytes", "membership_sha256"):
        if inventory.get(field) != expected[field]:
            raise DescriptorEvaluationError(
                f"University-1652 test inventory {field} changed: "
                f"expected {expected[field]!r}, got {inventory.get(field)!r}."
            )
    roles = inventory.get("roles")
    if not isinstance(roles, Mapping) or set(roles) != set(
        UNIVERSITY1652_T1_ROLES
    ):
        raise DescriptorEvaluationError(
            "University-1652 test inventory role set changed."
        )
    for role in UNIVERSITY1652_T1_ROLES:
        expected_role = {
            **UNIVERSITY1652_T1_EXPECTED_SCALE[role],
            **expected["roles"][role],
        }
        for field, value in expected_role.items():
            if roles[role].get(field) != value:
                raise DescriptorEvaluationError(
                    f"University-1652 {role} inventory {field} changed: "
                    f"expected {value!r}, got {roles[role].get(field)!r}."
                )


def parse_sues200_train_manifest(
    manifest_path: Path,
) -> tuple[tuple[str, ...], tuple[str, ...], dict[str, Any]]:
    if not manifest_path.is_file():
        raise DescriptorEvaluationError(
            f"SUES-200 official split manifest is absent: {manifest_path}"
        )
    if sha256_file(manifest_path) != SUES200_TRAIN_MANIFEST_SHA256:
        raise DescriptorEvaluationError(
            "SUES-200 official split manifest SHA-256 changed."
        )
    try:
        import yaml
    except ImportError as error:
        raise DescriptorEvaluationError(
            "PyYAML is required for the SUES-200 split manifest."
        ) from error
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise DescriptorEvaluationError(
            "SUES-200 official split manifest is not a mapping."
        )
    train_ids = tuple(str(value) for value in payload.get("train_ids", []))
    all_ids = tuple(f"{index:04d}" for index in range(1, 201))
    if (
        len(train_ids) != 120
        or len(set(train_ids)) != 120
        or not set(train_ids).issubset(set(all_ids))
    ):
        raise DescriptorEvaluationError(
            "SUES-200 official train split must contain 120 unique IDs."
        )
    test_ids = tuple(value for value in all_ids if value not in set(train_ids))
    if len(test_ids) != 80:
        raise DescriptorEvaluationError(
            "SUES-200 official test split must contain 80 IDs."
        )
    return train_ids, test_ids, {
        "path": str(manifest_path.resolve()),
        "sha256": sha256_file(manifest_path),
        "train_identity_count": len(train_ids),
        "test_identity_count": len(test_ids),
        "train_ids_sha256": canonical_sha256(list(train_ids)),
        "test_ids_sha256": canonical_sha256(list(test_ids)),
    }


def _scan_sues_view(
    dataset_root: Path,
    role: str,
) -> FrozenImageView:
    all_ids = tuple(f"{index:04d}" for index in range(1, 201))
    paths: list[Path] = []
    labels: list[str] = []
    relative_paths: list[str] = []
    if role == "satellite_all":
        base = dataset_root / "satellite-view"
        per_identity = 1
        altitude = None
    elif role.startswith("drone_") and role.endswith("_all"):
        altitude = role.removeprefix("drone_").removesuffix("_all")
        if altitude not in SUES200_ALTITUDES:
            raise DescriptorEvaluationError(f"Unknown SUES-200 role: {role}")
        base = dataset_root / "drone_view_512"
        per_identity = 50
    else:
        raise DescriptorEvaluationError(f"Unknown SUES-200 role: {role}")
    if not base.is_dir():
        raise DescriptorEvaluationError(f"SUES-200 view root is absent: {base}")
    observed_ids = tuple(
        sorted(path.name for path in base.iterdir() if path.is_dir())
    )
    if observed_ids != all_ids:
        raise DescriptorEvaluationError(
            f"SUES-200 {role} identity set differs from 0001..0200."
        )
    for identity in all_ids:
        identity_root = base / identity
        image_root = (
            identity_root if altitude is None else identity_root / altitude
        )
        if not image_root.is_dir():
            raise DescriptorEvaluationError(
                f"SUES-200 {role}/{identity} is absent."
            )
        nested = [path for path in image_root.iterdir() if path.is_dir()]
        if nested:
            raise DescriptorEvaluationError(
                f"SUES-200 {role}/{identity} contains nested directories."
            )
        candidates = sorted(
            (path for path in image_root.iterdir() if path.is_file()),
            key=lambda path: path.name,
        )
        unsupported = [
            path.name
            for path in candidates
            if path.suffix.casefold() not in IMAGE_EXTENSIONS
        ]
        if unsupported or len(candidates) != per_identity:
            raise DescriptorEvaluationError(
                f"SUES-200 {role}/{identity} expected {per_identity} images; "
                f"got {len(candidates)}, unsupported={unsupported[:8]}."
            )
        for path in candidates:
            paths.append(path.resolve())
            labels.append(identity)
            relative_paths.append(path.relative_to(dataset_root).as_posix())
    expected = SUES200_T1_EXPECTED_SCALE[role]
    if len(paths) != expected["images"]:
        raise DescriptorEvaluationError(
            f"SUES-200 {role} image count changed."
        )
    return FrozenImageView(
        role=role,
        paths=tuple(paths),
        relative_paths=np.asarray(relative_paths, dtype=str),
        labels=np.asarray(labels, dtype=str),
    )


def scan_sues200_official_test(
    dataset_root: Path,
    manifest_path: Path,
    *,
    hash_contents: bool = True,
) -> tuple[
    dict[str, FrozenImageView],
    dict[str, Any],
    tuple[str, ...],
]:
    root = dataset_root.resolve(strict=True)
    _, test_ids, split_manifest = parse_sues200_train_manifest(manifest_path)
    roles = ("satellite_all",) + tuple(
        f"drone_{altitude}_all" for altitude in SUES200_ALTITUDES
    )
    views = {role: _scan_sues_view(root, role) for role in roles}
    membership_digest = hashlib.sha256()
    content_digest = hashlib.sha256()
    total_bytes = 0
    role_rows: dict[str, Any] = {}
    for role in roles:
        view = views[role]
        role_bytes = 0
        role_membership = hashlib.sha256()
        role_content = hashlib.sha256()
        for path, relative, label in zip(
            view.paths,
            view.relative_paths.tolist(),
            view.labels.tolist(),
            strict=True,
        ):
            size = path.stat().st_size
            row = f"{relative}\0{label}\0{size}\n".encode("utf-8")
            membership_digest.update(row)
            role_membership.update(row)
            content_digest.update(row)
            role_content.update(row)
            if hash_contents:
                file_hash = sha256_file(path).encode("ascii")
                content_digest.update(file_hash)
                content_digest.update(b"\n")
                role_content.update(file_hash)
                role_content.update(b"\n")
            role_bytes += size
            total_bytes += size
        role_rows[role] = {
            "images": len(view.paths),
            "identities": len(set(view.labels.tolist())),
            "bytes": role_bytes,
            "membership_sha256": role_membership.hexdigest(),
            "content_sha256": (
                role_content.hexdigest() if hash_contents else None
            ),
        }
    inventory = {
        "dataset": "SUES-200",
        "split": "official fixed 120-train/80-test identity protocol",
        "roles": role_rows,
        "total_images": sum(len(view.paths) for view in views.values()),
        "total_bytes": total_bytes,
        "membership_sha256": membership_digest.hexdigest(),
        "content_sha256": content_digest.hexdigest() if hash_contents else None,
        "content_hashed": hash_contents,
        "relative_to": "SUES-200",
        "split_manifest": split_manifest,
    }
    return views, inventory, test_ids


def validate_sues200_test_inventory(
    inventory: Mapping[str, Any],
) -> None:
    if (
        inventory.get("dataset") != "SUES-200"
        or inventory.get("total_images")
        != SUES200_T1_EXPECTED_INVENTORY["total_images"]
        or set(inventory.get("roles", {})) != set(
            SUES200_T1_EXPECTED_SCALE
        )
    ):
        raise DescriptorEvaluationError(
            "SUES-200 official-test inventory scale changed."
        )
    for role, expected in SUES200_T1_EXPECTED_SCALE.items():
        observed = inventory["roles"][role]
        expected_role = {
            **expected,
            **SUES200_T1_EXPECTED_INVENTORY["roles"][role],
        }
        for field, value in expected_role.items():
            if observed.get(field) != value:
                raise DescriptorEvaluationError(
                    f"SUES-200 {role} {field} changed."
                )
    expected_bytes = SUES200_T1_EXPECTED_INVENTORY["total_bytes"]
    expected_membership = SUES200_T1_EXPECTED_INVENTORY[
        "membership_sha256"
    ]
    if expected_bytes is not None and inventory.get("total_bytes") != expected_bytes:
        raise DescriptorEvaluationError("SUES-200 official-test bytes changed.")
    if (
        expected_membership is not None
        and inventory.get("membership_sha256") != expected_membership
    ):
        raise DescriptorEvaluationError(
            "SUES-200 official-test membership changed."
        )


def validate_all_fits_gate(
    gate_path: Path,
    *,
    run_id: str,
    fit_manifest_path: Path,
    checkpoint_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not gate_path.is_file():
        raise DescriptorEvaluationError(
            f"All-fits official-test gate is absent: {gate_path}"
        )
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if (
        gate.get("schema_version") != ALL_FITS_GATE_SCHEMA
        or gate.get("status") != "all_seven_fits_validated"
        or gate.get("registered_run_count") != 7
    ):
        raise DescriptorEvaluationError(
            "All-fits official-test gate is incomplete."
        )
    payload = dict(gate)
    declared = payload.pop("payload_sha256", None)
    if declared != canonical_sha256(payload):
        raise DescriptorEvaluationError(
            "All-fits official-test gate payload hash mismatch."
        )
    rows = gate.get("runs")
    if (
        not isinstance(rows, list)
        or len(rows) != 7
        or len({row.get("run_id") for row in rows}) != 7
    ):
        raise DescriptorEvaluationError(
            "All-fits official-test gate run registry is invalid."
        )
    selected = next(
        (row for row in rows if row.get("run_id") == run_id),
        None,
    )
    if selected is None:
        raise DescriptorEvaluationError(
            f"All-fits official-test gate omits {run_id}."
        )
    expected = (
        (
            "fit_manifest_path",
            fit_manifest_path.resolve(),
            "fit_manifest_sha256",
        ),
        (
            "checkpoint_path",
            checkpoint_path.resolve(),
            "checkpoint_sha256",
        ),
    )
    for path_field, path, hash_field in expected:
        if (
            Path(str(selected.get(path_field, ""))).resolve() != path
            or not path.is_file()
            or selected.get(hash_field) != sha256_file(path)
        ):
            raise DescriptorEvaluationError(
                f"All-fits gate evidence changed for {run_id}: {path_field}."
            )
    return gate, selected


def validate_test_inventory_gate(
    gate_path: Path,
    *,
    test_root: Path,
    sues_root: Path,
    sues_manifest: Path,
    all_fits_gate_path: Path,
    inventory: Mapping[str, Any],
) -> dict[str, Any]:
    if not gate_path.is_file():
        raise DescriptorEvaluationError(
            f"Official-test inventory gate is absent: {gate_path}"
        )
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if (
        gate.get("schema_version") != TEST_INVENTORY_GATE_SCHEMA
        or gate.get("status") != "content_frozen_after_all_fits_gate"
    ):
        raise DescriptorEvaluationError(
            "Official-test inventory gate is incomplete."
        )
    payload = dict(gate)
    declared = payload.pop("payload_sha256", None)
    if declared != canonical_sha256(payload):
        raise DescriptorEvaluationError(
            "Official-test inventory gate payload hash mismatch."
        )
    if (
        Path(str(gate.get("test_root", ""))).resolve()
        != test_root.resolve()
        or Path(str(gate.get("sues_root", ""))).resolve()
        != sues_root.resolve()
        or Path(str(gate.get("sues_manifest_path", ""))).resolve()
        != sues_manifest.resolve()
        or gate.get("sues_manifest_sha256") != sha256_file(sues_manifest)
        or Path(str(gate.get("all_fits_gate_path", ""))).resolve()
        != all_fits_gate_path.resolve()
        or gate.get("all_fits_gate_sha256")
        != sha256_file(all_fits_gate_path)
        or gate.get("inventory") != dict(inventory)
    ):
        raise DescriptorEvaluationError(
            "Official-test data differ from the post-fit frozen inventory."
        )
    return gate


def descriptor_sha256(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(np.asarray(array, dtype=np.float32))
    digest = hashlib.sha256()
    digest.update(str(contiguous.shape).encode("ascii"))
    digest.update(b"\0")
    digest.update(contiguous.dtype.str.encode("ascii"))
    digest.update(b"\0")
    digest.update(contiguous.tobytes(order="C"))
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def begin_evaluation_output(
    output_dir: Path,
    evaluation_config: Mapping[str, Any],
) -> tuple[Path, str]:
    config_payload = dict(evaluation_config)
    declared_payload_sha = config_payload.pop("payload_sha256", None)
    if declared_payload_sha != canonical_sha256(config_payload):
        raise DescriptorEvaluationError(
            "Evaluation configuration payload hash is absent or invalid."
        )
    output = output_dir.resolve()
    if output.exists():
        retained = sorted(path.name for path in output.iterdir())
        if retained:
            raise DescriptorEvaluationError(
                "Evaluation output is non-empty; preserve/archive the prior "
                f"attempt before retrying: {retained}"
            )
    output.mkdir(parents=True, exist_ok=True)
    config_path = output / "evaluation_config.json"
    config_sha = write_immutable_json(config_path, dict(evaluation_config))
    atomic_write_json(
        output / "status.json",
        {
            "schema_version": EVALUATION_STATUS_SCHEMA,
            "status": "running",
            "evaluation_config_sha256": config_sha,
            "started_utc": utc_now(),
        },
    )
    return output, config_sha


def mark_evaluation_failed(
    output_dir: Path,
    evaluation_config_sha256: str,
    error: BaseException,
) -> None:
    atomic_write_json(
        output_dir / "status.json",
        {
            "schema_version": EVALUATION_STATUS_SCHEMA,
            "status": "failed",
            "evaluation_config_sha256": evaluation_config_sha256,
            "failed_utc": utc_now(),
            "error_type": type(error).__name__,
            "error": str(error),
        },
    )


def _write_metrics_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fieldnames = (
        "task",
        "protocol",
        "score_type",
        "queries",
        "gallery",
        "query_identities",
        "gallery_identities",
        "descriptor_dimension",
        "r_at_1",
        "r_at_5",
        "r_at_10",
        "r_at_20",
        "official_trapezoid_mAP",
        "MRR",
        "mean_top1_margin",
    )
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row[name] for name in fieldnames})


def complete_evaluation_output(
    output_dir: Path,
    *,
    evaluation_config_sha256: str,
    method: str,
    config_id: str,
    seed: int,
    results: Mapping[
        str,
        tuple[Mapping[str, Any], Mapping[str, np.ndarray]],
    ],
    descriptor_fingerprints: Mapping[str, Mapping[str, Any]],
    elapsed_seconds: float,
) -> dict[str, Any]:
    if not results:
        raise DescriptorEvaluationError("Official evaluation has no task results.")
    arrays_dir = output_dir / "per_query_arrays"
    arrays_dir.mkdir(parents=False, exist_ok=False)
    metric_rows: list[dict[str, Any]] = []
    for task_name, (metrics, arrays) in results.items():
        if set(arrays) != ARRAY_FIELDS:
            raise DescriptorEvaluationError(
                f"{task_name}: per-query array field set changed."
            )
        row = {"task": task_name, **dict(metrics)}
        metric_rows.append(row)
        arrays_path = arrays_dir / f"{task_name}_per_query.npz"
        with arrays_path.open("xb") as stream:
            np.savez_compressed(stream, **arrays)
        recomputed = recompute_metrics(arrays_path)
        for field in (
            "queries",
            "r_at_1",
            "r_at_5",
            "r_at_10",
            "r_at_20",
            "official_trapezoid_mAP",
            "MRR",
            "mean_top1_margin",
        ):
            if not math.isclose(
                float(recomputed[field]),
                float(metrics[field]),
                rel_tol=2e-6,
                abs_tol=2e-7,
            ):
                raise DescriptorEvaluationError(
                    f"{task_name}: saved arrays disagree on {field}."
                )
    metrics_payload = {
        "schema_version": METRIC_SCHEMA,
        "status": "completed",
        "method": method,
        "config_id": config_id,
        "seed": seed,
        "unit": "fraction",
        "tasks": metric_rows,
        "descriptor_fingerprints": dict(descriptor_fingerprints),
    }
    write_immutable_json(output_dir / "metrics.json", metrics_payload)
    _write_metrics_csv(output_dir / "metrics.csv", metric_rows)

    artifacts: dict[str, Any] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name not in {
            "evaluation_manifest.json",
            "status.json",
        }:
            artifacts[path.relative_to(output_dir).as_posix()] = {
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
    manifest_payload = {
        "schema_version": EVALUATION_MANIFEST_SCHEMA,
        "status": "completed",
        "method": method,
        "config_id": config_id,
        "seed": seed,
        "evaluation_config_sha256": evaluation_config_sha256,
        "completed_utc": utc_now(),
        "elapsed_seconds": elapsed_seconds,
        "task_names": list(results),
        "artifacts": artifacts,
        "leakage_controls": {
            "fit_completion_verified_before_test_access": True,
            "official_test_used_during_fit_or_model_selection": False,
            "all_official_queries_used": True,
            "all_official_gallery_images_used": True,
            "deterministic_sorted_path_order": True,
        },
    }
    manifest = {
        **manifest_payload,
        "payload_sha256": canonical_sha256(manifest_payload),
    }
    write_immutable_json(output_dir / "evaluation_manifest.json", manifest)
    atomic_write_json(
        output_dir / "status.json",
        {
            "schema_version": EVALUATION_STATUS_SCHEMA,
            "status": "completed",
            "evaluation_config_sha256": evaluation_config_sha256,
            "evaluation_manifest_sha256": sha256_file(
                output_dir / "evaluation_manifest.json"
            ),
            "completed_utc": manifest["completed_utc"],
        },
    )
    return manifest


def validate_completed_evaluation(output_dir: Path) -> dict[str, Any]:
    manifest_path = output_dir / "evaluation_manifest.json"
    config_path = output_dir / "evaluation_config.json"
    metrics_path = output_dir / "metrics.json"
    csv_path = output_dir / "metrics.csv"
    for path in (manifest_path, config_path, metrics_path, csv_path):
        if not path.is_file():
            raise DescriptorEvaluationError(
                f"Completed evaluation artifact is absent: {path}"
            )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("schema_version") != EVALUATION_MANIFEST_SCHEMA
        or manifest.get("status") != "completed"
    ):
        raise DescriptorEvaluationError("Evaluation manifest is not completed.")
    payload = dict(manifest)
    declared = payload.pop("payload_sha256", None)
    if declared != canonical_sha256(payload):
        raise DescriptorEvaluationError("Evaluation manifest payload hash mismatch.")
    if manifest.get("evaluation_config_sha256") != sha256_file(config_path):
        raise DescriptorEvaluationError("Evaluation configuration hash mismatch.")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config_payload = dict(config)
    config_declared = config_payload.pop("payload_sha256", None)
    if config_declared != canonical_sha256(config_payload):
        raise DescriptorEvaluationError(
            "Evaluation configuration payload hash mismatch."
        )
    declared_artifacts = manifest.get("artifacts")
    if not isinstance(declared_artifacts, Mapping):
        raise DescriptorEvaluationError(
            "Evaluation artifact registry is invalid."
        )
    actual_artifacts = {
        path.relative_to(output_dir).as_posix()
        for path in output_dir.rglob("*")
        if path.is_file()
        and path.name not in {"evaluation_manifest.json", "status.json"}
    }
    if set(declared_artifacts) != actual_artifacts:
        raise DescriptorEvaluationError(
            "Evaluation artifact registry has missing or extra files."
        )
    for relative, evidence in declared_artifacts.items():
        path = (output_dir / relative).resolve()
        if not path.is_relative_to(output_dir.resolve()):
            raise DescriptorEvaluationError(
                f"Evaluation artifact escapes output directory: {relative}"
            )
        if (
            not path.is_file()
            or sha256_file(path) != evidence.get("sha256")
            or path.stat().st_size != int(evidence.get("bytes", -1))
        ):
            raise DescriptorEvaluationError(
                f"Evaluation artifact hash/size mismatch: {path}"
            )
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    if (
        metrics.get("schema_version") != METRIC_SCHEMA
        or metrics.get("status") != "completed"
        or metrics.get("method") != manifest.get("method")
        or metrics.get("config_id") != manifest.get("config_id")
        or metrics.get("seed") != manifest.get("seed")
        or metrics.get("unit") != "fraction"
    ):
        raise DescriptorEvaluationError(
            "Evaluation metric metadata disagree with the manifest."
        )
    task_names = [row.get("task") for row in metrics.get("tasks", [])]
    if task_names != manifest.get("task_names") or len(set(task_names)) != len(
        task_names
    ):
        raise DescriptorEvaluationError("Evaluation task registry mismatch.")
    for row in metrics["tasks"]:
        arrays_path = output_dir / "per_query_arrays" / (
            f"{row['task']}_per_query.npz"
        )
        recomputed = recompute_metrics(arrays_path)
        for field, value in recomputed.items():
            if not math.isclose(
                float(value),
                float(row[field]),
                rel_tol=2e-6,
                abs_tol=2e-7,
            ):
                raise DescriptorEvaluationError(
                    f"{row['task']}: persisted metric {field} differs."
                )
    with csv_path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        csv_rows = list(reader)
    expected_fields = [
        "task",
        "protocol",
        "score_type",
        "queries",
        "gallery",
        "query_identities",
        "gallery_identities",
        "descriptor_dimension",
        "r_at_1",
        "r_at_5",
        "r_at_10",
        "r_at_20",
        "official_trapezoid_mAP",
        "MRR",
        "mean_top1_margin",
    ]
    if reader.fieldnames != expected_fields:
        raise DescriptorEvaluationError("Evaluation CSV field set changed.")
    if [row["task"] for row in csv_rows] != task_names:
        raise DescriptorEvaluationError("Evaluation CSV task order mismatch.")
    integer_fields = (
        "queries",
        "gallery",
        "query_identities",
        "gallery_identities",
        "descriptor_dimension",
    )
    float_fields = (
        "r_at_1",
        "r_at_5",
        "r_at_10",
        "r_at_20",
        "official_trapezoid_mAP",
        "MRR",
        "mean_top1_margin",
    )
    for json_row, csv_row in zip(metrics["tasks"], csv_rows, strict=True):
        for field in ("task", "protocol", "score_type"):
            if csv_row[field] != str(json_row[field]):
                raise DescriptorEvaluationError(
                    f"{json_row['task']}: CSV {field} differs from JSON."
                )
        for field in integer_fields:
            if int(csv_row[field]) != int(json_row[field]):
                raise DescriptorEvaluationError(
                    f"{json_row['task']}: CSV {field} differs from JSON."
                )
        for field in float_fields:
            if not math.isclose(
                float(csv_row[field]),
                float(json_row[field]),
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                raise DescriptorEvaluationError(
                    f"{json_row['task']}: CSV {field} differs from JSON."
                )
    status = json.loads(
        (output_dir / "status.json").read_text(encoding="utf-8")
    )
    if (
        status.get("schema_version") != EVALUATION_STATUS_SCHEMA
        or status.get("status") != "completed"
        or status.get("evaluation_config_sha256")
        != manifest["evaluation_config_sha256"]
        or status.get("evaluation_manifest_sha256")
        != sha256_file(manifest_path)
    ):
        raise DescriptorEvaluationError(
            "Evaluation completion status evidence is inconsistent."
        )
    return manifest
