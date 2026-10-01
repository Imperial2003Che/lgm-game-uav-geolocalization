"""Generate leakage-free, image-level CLIP evidence caches.

The CLIP model sees one image at a time and a fixed, class-agnostic text
vocabulary.  This command deliberately has no class-id, label, pair-file, or
positive-match input.  Dataset directory names are used only to discover
images and (for SUES-200) to reproduce a train/test partition; they are never
passed to CLIP.

The compressed NPZ schema is intentionally small and stable:

* ``paths``: paths relative to ``--dataset-root`` with POSIX separators;
* ``content_probs``: float16 array with shape [N, 11];
* ``style_probs``: float16 array with shape [N, 10];
* ``views``: per-image view strings;
* ``altitudes``: per-image altitude strings.

The sibling ``.meta.json`` records the model, ordered candidate texts, hashes,
runtime configuration, and coverage audit.  The sibling ``.failures.json``
records unreadable images without stopping the rest of a full-dataset run.

Example
-------
python -m lgm_game_pytorch.generate_clip_image_evidence \
  --dataset university1652 \
  --dataset-root C:/datasets/University-1652 \
  --output results/clip_evidence/university1652_clip.npz \
  --batch-size 256 --device cuda
"""

from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import hashlib
import json
import os
import platform
import random
import re
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
from PIL import Image


SCHEMA_VERSION = "lgm-game.clip-image-evidence.v1"
IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"})
KNOWN_ALTITUDES = frozenset({"150", "200", "250", "300"})

# These ordered candidates match the project's fixed PromptVocabulary.  They
# contain no location identifier and therefore cannot encode a positive match.
CONTENT_CANDIDATES: tuple[tuple[str, str], ...] = (
    ("campus", "a university campus scene"),
    ("building", "campus buildings and rooftops"),
    ("road", "roads and paved paths"),
    ("intersection", "road intersections and geometric junctions"),
    ("parking", "parking lots and regular parked vehicles"),
    ("vegetation", "trees lawns and vegetation blocks"),
    ("sports_field", "sports field or playground"),
    ("open_area", "open plaza or square"),
    ("water", "water body or river boundary"),
    ("dense_layout", "dense urban layout"),
    ("stable_layout", "stable spatial layout useful for geo localization"),
)

STYLE_CANDIDATES: tuple[tuple[str, str], ...] = (
    ("uav_oblique", "an oblique UAV aerial photograph"),
    ("satellite_nadir", "a nadir satellite image"),
    ("viewpoint_gap", "a large viewpoint difference between UAV and satellite"),
    ("sensor_gap", "different sensors and image styles"),
    ("low_altitude", "low altitude UAV image with detailed facade cues"),
    ("high_altitude", "high altitude UAV image with smaller objects"),
    ("strong_shadow", "strong building shadows"),
    ("bright_light", "bright daylight illumination"),
    ("low_contrast", "low contrast remote sensing image"),
    ("seasonal_vegetation", "seasonal vegetation appearance"),
)

if len(CONTENT_CANDIDATES) != 11 or len(STYLE_CANDIDATES) != 10:
    raise RuntimeError("The evidence schema requires exactly 11 content and 10 style candidates.")


@dataclass(frozen=True)
class ImageRecord:
    """Image metadata that is safe to retain alongside independent evidence."""

    absolute_path: Path
    relative_path: str
    split: str
    view: str
    altitude: str


@dataclass
class ResultStore:
    """In-memory representation of the stable NPZ schema."""

    paths: list[str]
    content_probs: np.ndarray
    style_probs: np.ndarray
    views: list[str]
    altitudes: list[str]

    @classmethod
    def empty(cls) -> "ResultStore":
        return cls(
            paths=[],
            content_probs=np.empty((0, len(CONTENT_CANDIDATES)), dtype=np.float16),
            style_probs=np.empty((0, len(STYLE_CANDIDATES)), dtype=np.float16),
            views=[],
            altitudes=[],
        )

    @classmethod
    def load(cls, path: Path) -> "ResultStore":
        with np.load(path, allow_pickle=False) as archive:
            required = {"paths", "content_probs", "style_probs", "views", "altitudes"}
            missing = sorted(required.difference(archive.files))
            if missing:
                raise ValueError(f"{path} is missing required arrays: {', '.join(missing)}")
            paths = archive["paths"].astype(str).tolist()
            content = np.asarray(archive["content_probs"], dtype=np.float16)
            style = np.asarray(archive["style_probs"], dtype=np.float16)
            views = archive["views"].astype(str).tolist()
            altitudes = archive["altitudes"].astype(str).tolist()

        n_rows = len(paths)
        if content.shape != (n_rows, len(CONTENT_CANDIDATES)):
            raise ValueError(f"Invalid content_probs shape in {path}: {content.shape}")
        if style.shape != (n_rows, len(STYLE_CANDIDATES)):
            raise ValueError(f"Invalid style_probs shape in {path}: {style.shape}")
        if len(views) != n_rows or len(altitudes) != n_rows:
            raise ValueError(f"String-array lengths do not agree in {path}.")
        if len(set(paths)) != n_rows:
            raise ValueError(f"Duplicate paths found in {path}; refusing ambiguous resume.")
        if not np.isfinite(content).all() or not np.isfinite(style).all():
            raise ValueError(f"Non-finite probabilities found in {path}.")
        return cls(paths, content, style, views, altitudes)

    @property
    def keys(self) -> set[str]:
        return set(self.paths)

    def append_batch(
        self,
        records: Sequence[ImageRecord],
        content_probs: np.ndarray,
        style_probs: np.ndarray,
    ) -> None:
        if content_probs.shape != (len(records), len(CONTENT_CANDIDATES)):
            raise ValueError(f"Unexpected content probability shape: {content_probs.shape}")
        if style_probs.shape != (len(records), len(STYLE_CANDIDATES)):
            raise ValueError(f"Unexpected style probability shape: {style_probs.shape}")
        if not np.isfinite(content_probs).all() or not np.isfinite(style_probs).all():
            raise ValueError("CLIP produced non-finite probabilities.")

        self.paths.extend(record.relative_path for record in records)
        self.views.extend(record.view for record in records)
        self.altitudes.extend(record.altitude for record in records)
        self.content_probs = np.concatenate(
            (self.content_probs, np.asarray(content_probs, dtype=np.float16)), axis=0
        )
        self.style_probs = np.concatenate(
            (self.style_probs, np.asarray(style_probs, dtype=np.float16)), axis=0
        )

    def sorted_arrays(self) -> dict[str, np.ndarray]:
        """Return deterministic, path-sorted arrays without object dtypes."""

        if not self.paths:
            order = np.empty((0,), dtype=np.int64)
        else:
            order = np.argsort(np.asarray(self.paths, dtype=np.str_), kind="stable")
        paths = np.asarray(self.paths, dtype=np.str_)[order]
        views = np.asarray(self.views, dtype=np.str_)[order]
        altitudes = np.asarray(self.altitudes, dtype=np.str_)[order]
        return {
            "paths": paths,
            "content_probs": self.content_probs[order].astype(np.float16, copy=False),
            "style_probs": self.style_probs[order].astype(np.float16, copy=False),
            "views": views,
            "altitudes": altitudes,
        }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Cache independent CLIP content/style evidence for every image in "
            "University-1652 or SUES-200, with resumable coverage auditing."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--dataset",
        required=True,
        choices=("university1652", "sues200"),
        help="Dataset layout to scan.",
    )
    parser.add_argument(
        "--dataset-root",
        required=True,
        type=Path,
        help="Dataset root. Saved image paths are always relative to this directory.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Destination compressed NPZ. Sibling .meta.json and .failures.json are also written.",
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        choices=("train", "test"),
        default=("train", "test"),
        help="Splits to include; both are scanned by default.",
    )
    parser.add_argument(
        "--model-name",
        default="openai/clip-vit-base-patch32",
        help="Hugging Face CLIP model identifier.",
    )
    parser.add_argument(
        "--model-revision",
        default=None,
        help="Optional immutable Hugging Face revision or commit hash.",
    )
    parser.add_argument(
        "--hf-cache-dir",
        type=Path,
        default=None,
        help="Optional Hugging Face model cache directory.",
    )
    parser.add_argument(
        "--local-files-only",
        action="store_true",
        help="Do not contact Hugging Face; require the model to exist in the local cache.",
    )
    parser.add_argument("--batch-size", type=int, default=256, help="CLIP image inference batch size.")
    parser.add_argument(
        "--image-workers",
        type=int,
        default=8,
        help="Threads used only for independent image decoding.",
    )
    parser.add_argument(
        "--device",
        default="auto",
        help="'auto', 'cuda', 'cuda:N', or 'cpu'. Auto prefers CUDA.",
    )
    parser.add_argument(
        "--allow-cpu",
        action="store_true",
        help="Permit a CPU run when CUDA is unavailable (full scans will be much slower).",
    )
    parser.add_argument(
        "--precision",
        choices=("auto", "fp32", "fp16", "bf16"),
        default="auto",
        help="Autocast precision; auto uses fp16 on CUDA and fp32 otherwise.",
    )
    parser.add_argument("--seed", type=int, default=20260727, help="Global deterministic seed.")
    parser.add_argument(
        "--sues-train-manifest",
        type=Path,
        default=(
            Path(__file__).resolve().parents[1]
            / "manifests"
            / "sues200_official_train_ids.yaml"
        ),
        help=(
            "Official SUES-200 fixed-120 training-ID manifest. The remaining "
            "80 IDs are tagged as test; split tags are never model inputs."
        ),
    )
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=10000,
        help="Atomically checkpoint after this many attempted images.",
    )
    parser.add_argument(
        "--print-every",
        type=int,
        default=1000,
        help="Print progress after this many attempted images.",
    )
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=1.0,
        help="Exit non-zero if successful evidence coverage is below this fraction.",
    )
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Load a compatible existing NPZ and skip paths already present.",
    )
    parser.add_argument(
        "--retry-failures",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Retry paths recorded in an existing failure list.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Start a new cache even when output files already exist.",
    )
    args = parser.parse_args(argv)

    if args.batch_size < 1:
        parser.error("--batch-size must be positive.")
    if args.image_workers < 0:
        parser.error("--image-workers cannot be negative.")
    if args.checkpoint_every < 1 or args.print_every < 1:
        parser.error("--checkpoint-every and --print-every must be positive.")
    if not 0.0 <= args.min_coverage <= 1.0:
        parser.error("--min-coverage must be between 0 and 1.")
    if args.overwrite and not args.resume:
        # This combination is harmless, but normalising it avoids ambiguous logs.
        args.resume = False

    args.dataset_root = args.dataset_root.expanduser().resolve()
    args.output = _normalise_npz_path(args.output.expanduser().resolve())
    if args.hf_cache_dir is not None:
        args.hf_cache_dir = args.hf_cache_dir.expanduser().resolve()
    args.splits = tuple(sorted(set(args.splits), key=("train", "test").index))
    return args


def _normalise_npz_path(path: Path) -> Path:
    if path.suffix.lower() == ".npz":
        return path
    return path.with_suffix(path.suffix + ".npz") if path.suffix else path.with_suffix(".npz")


def _sidecar_paths(output: Path) -> tuple[Path, Path]:
    return output.with_suffix(".meta.json"), output.with_suffix(".failures.json")


def _iter_image_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            yield path


def scan_dataset(
    dataset: str,
    root: Path,
    splits: Sequence[str],
    sues_train_manifest: Path,
) -> list[ImageRecord]:
    if not root.is_dir():
        raise FileNotFoundError(f"Dataset root does not exist or is not a directory: {root}")
    if dataset == "university1652":
        records = _scan_university1652(root, splits)
    elif dataset == "sues200":
        records = _scan_sues200(root, splits, sues_train_manifest)
    else:
        raise ValueError(f"Unsupported dataset: {dataset}")

    records.sort(key=lambda record: record.relative_path)
    paths = [record.relative_path for record in records]
    if not records:
        raise RuntimeError(f"No supported images found for {dataset} at {root}.")
    if len(paths) != len(set(paths)):
        raise RuntimeError("Dataset scan produced duplicate relative paths.")
    return records


def _scan_university1652(root: Path, splits: Sequence[str]) -> list[ImageRecord]:
    records: list[ImageRecord] = []
    for split in splits:
        split_root = root / split
        if not split_root.is_dir():
            raise FileNotFoundError(f"University-1652 is missing requested split directory: {split_root}")
        for path in _iter_image_files(split_root):
            relative = path.relative_to(root).as_posix()
            records.append(
                ImageRecord(
                    absolute_path=path,
                    relative_path=relative,
                    split=split,
                    view=_infer_view(path.relative_to(split_root).parts),
                    altitude=_infer_altitude(path.relative_to(root).parts),
                )
            )
    return records


def _scan_sues200(
    root: Path,
    splits: Sequence[str],
    train_manifest: Path,
) -> list[ImageRecord]:
    view_roots = {
        "drone": root / "drone_view_512",
        "satellite": root / "satellite-view",
    }
    missing = [str(path) for path in view_roots.values() if not path.is_dir()]
    if missing:
        raise FileNotFoundError("SUES-200 is missing required view roots: " + ", ".join(missing))

    if not train_manifest.is_file():
        raise FileNotFoundError(
            f"Official SUES-200 training-ID manifest is missing: {train_manifest}"
        )
    manifest_text = train_manifest.read_text(encoding="utf-8")
    manifest_ids = re.findall(
        r'^\s*-\s*["\']?([0-9]{4})["\']?\s*$',
        manifest_text,
        flags=re.MULTILINE,
    )
    if not manifest_ids:
        manifest_ids = re.findall(r"['\"]([0-9]{4})['\"]", manifest_text)
    train_tokens = set(manifest_ids)
    valid_tokens = {f"{index:04d}" for index in range(1, 201)}
    if len(manifest_ids) != 120 or len(train_tokens) != 120 or not train_tokens <= valid_tokens:
        raise ValueError(
            "SUES-200 manifest must contain exactly 120 unique IDs in 0001..0200."
        )

    # Partition tokens are used only for coverage auditing against the
    # published fixed split. They are not saved as labels and are never passed
    # to CLIP.
    all_tokens: set[str] = set()
    view_files: dict[str, list[tuple[Path, str]]] = {}
    for view, view_root in view_roots.items():
        entries: list[tuple[Path, str]] = []
        for path in _iter_image_files(view_root):
            relative_to_view = path.relative_to(view_root)
            token = relative_to_view.parts[0]
            all_tokens.add(token)
            entries.append((path, token))
        view_files[view] = entries

    if all_tokens != valid_tokens:
        missing = sorted(valid_tokens - all_tokens)
        extra = sorted(all_tokens - valid_tokens)
        raise RuntimeError(
            "SUES-200 directory IDs do not match 0001..0200; "
            f"missing={missing[:5]}, extra={extra[:5]}."
        )
    requested = set(splits)

    records: list[ImageRecord] = []
    for view, entries in view_files.items():
        for path, token in entries:
            split = "train" if token in train_tokens else "test"
            if split not in requested:
                continue
            records.append(
                ImageRecord(
                    absolute_path=path,
                    relative_path=path.relative_to(root).as_posix(),
                    split=split,
                    view=view,
                    altitude=_infer_altitude(path.relative_to(root).parts),
                )
            )
    return records


def _infer_view(parts: Sequence[str]) -> str:
    lowered = [part.lower().replace("-", "_") for part in parts]
    if any("satellite" in part for part in lowered):
        return "satellite"
    if any("street" in part or "google" in part for part in lowered):
        return "street"
    if any("drone" in part or "uav" in part for part in lowered):
        return "drone"
    return "unknown"


def _infer_altitude(parts: Sequence[str]) -> str:
    for part in reversed(parts):
        if part in KNOWN_ALTITUDES:
            return part
    return "unknown"


def _candidate_payload(candidates: Sequence[tuple[str, str]]) -> list[dict[str, str]]:
    return [{"id": candidate_id, "text": text} for candidate_id, text in candidates]


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def _json_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _scan_manifest_hash(records: Sequence[ImageRecord]) -> str:
    digest = hashlib.sha256()
    for record in records:
        stat = record.absolute_path.stat()
        digest.update(record.relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(stat.st_size).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _set_determinism(seed: int, torch_module: Any) -> None:
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    random.seed(seed)
    np.random.seed(seed)
    torch_module.manual_seed(seed)
    if torch_module.cuda.is_available():
        torch_module.cuda.manual_seed_all(seed)
    if hasattr(torch_module.backends, "cudnn"):
        torch_module.backends.cudnn.benchmark = False
        torch_module.backends.cudnn.deterministic = True
    torch_module.use_deterministic_algorithms(True, warn_only=True)


def _resolve_device(requested: str, allow_cpu: bool, torch_module: Any) -> Any:
    if requested == "auto":
        device = torch_module.device("cuda" if torch_module.cuda.is_available() else "cpu")
    else:
        device = torch_module.device(requested)
    if device.type == "cuda" and not torch_module.cuda.is_available():
        raise RuntimeError(f"CUDA device requested but CUDA is unavailable: {requested}")
    if device.type == "cpu" and not allow_cpu:
        raise RuntimeError(
            "CUDA is unavailable (or CPU was requested). A full image scan is intended for "
            "batched GPU inference; pass --allow-cpu only when a slow CPU run is intentional."
        )
    return device


def _resolve_precision(requested: str, device: Any, torch_module: Any) -> tuple[str, Any | None]:
    resolved = "fp16" if requested == "auto" and device.type == "cuda" else requested
    if resolved == "auto":
        resolved = "fp32"
    if device.type == "cpu" and resolved == "fp16":
        raise ValueError("fp16 autocast is not supported for this CPU path; use fp32 or bf16.")
    dtype = {
        "fp32": None,
        "fp16": torch_module.float16,
        "bf16": torch_module.bfloat16,
    }[resolved]
    return resolved, dtype


def _autocast_context(device: Any, dtype: Any | None, torch_module: Any) -> Any:
    if dtype is None:
        return contextlib.nullcontext()
    return torch_module.autocast(device_type=device.type, dtype=dtype)


def _normalise_features(features: Any, torch_module: Any) -> Any:
    if not torch_module.is_tensor(features):
        if hasattr(features, "pooler_output"):
            features = features.pooler_output
        else:
            raise TypeError(f"Unexpected CLIP feature output: {type(features)!r}")
    return torch_module.nn.functional.normalize(features.float(), dim=-1)


def _encode_text_prototypes(
    model: Any,
    processor: Any,
    candidates: Sequence[tuple[str, str]],
    device: Any,
    autocast_dtype: Any | None,
    torch_module: Any,
) -> Any:
    texts = [text for _, text in candidates]
    encoded = processor(text=texts, padding=True, truncation=True, return_tensors="pt")
    model_inputs = {
        key: value.to(device, non_blocking=True)
        for key, value in encoded.items()
        if key in {"input_ids", "attention_mask", "position_ids"}
    }
    with torch_module.inference_mode(), _autocast_context(device, autocast_dtype, torch_module):
        features = model.get_text_features(**model_inputs)
    return _normalise_features(features, torch_module)


def _load_rgb(record: ImageRecord) -> tuple[ImageRecord, Image.Image | None, str | None]:
    try:
        with Image.open(record.absolute_path) as image:
            rgb = image.convert("RGB").copy()
        return record, rgb, None
    except Exception as exc:  # PIL raises several format-specific exception classes.
        return record, None, f"{type(exc).__name__}: {exc}"


def _load_batch(
    records: Sequence[ImageRecord],
    workers: int,
) -> list[tuple[ImageRecord, Image.Image | None, str | None]]:
    if workers <= 1:
        return [_load_rgb(record) for record in records]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(_load_rgb, records))


def _infer_probabilities(
    images: Sequence[Image.Image],
    model: Any,
    processor: Any,
    content_prototypes: Any,
    style_prototypes: Any,
    logit_scale: float,
    device: Any,
    autocast_dtype: Any | None,
    torch_module: Any,
) -> tuple[np.ndarray, np.ndarray]:
    # Only pixels enter this processor call.  Paths, split metadata, directory
    # tokens, labels, and cross-view pairing information are not model inputs.
    encoded = processor(images=list(images), return_tensors="pt")
    pixel_values = encoded["pixel_values"].to(device, non_blocking=True)
    with torch_module.inference_mode(), _autocast_context(device, autocast_dtype, torch_module):
        image_features = model.get_image_features(pixel_values=pixel_values)
    image_features = _normalise_features(image_features, torch_module)

    content_logits = logit_scale * (image_features @ content_prototypes.T)
    style_logits = logit_scale * (image_features @ style_prototypes.T)
    content = torch_module.softmax(content_logits, dim=-1).cpu().numpy().astype(np.float16)
    style = torch_module.softmax(style_logits, dim=-1).cpu().numpy().astype(np.float16)
    return content, style


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True, default=str)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary_name)
        raise


def _write_npz_atomic(path: Path, store: ResultStore) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".npz", dir=path.parent)
    os.close(fd)
    try:
        np.savez_compressed(temporary_name, **store.sorted_arrays())
        os.replace(temporary_name, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary_name)
        raise


def _coverage_summary(
    records: Sequence[ImageRecord],
    successful_paths: set[str],
    failures: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    expected_paths = {record.relative_path for record in records}
    succeeded = expected_paths.intersection(successful_paths)
    failed = expected_paths.intersection(failures).difference(succeeded)
    missing = expected_paths.difference(succeeded).difference(failed)
    extra = successful_paths.difference(expected_paths)

    expected_groups: dict[str, int] = {}
    success_groups: dict[str, int] = {}
    for record in records:
        group = f"{record.split}/{record.view}/altitude_{record.altitude}"
        expected_groups[group] = expected_groups.get(group, 0) + 1
        if record.relative_path in succeeded:
            success_groups[group] = success_groups.get(group, 0) + 1
    group_coverage = {
        group: {
            "expected": expected,
            "succeeded": success_groups.get(group, 0),
            "coverage_fraction": success_groups.get(group, 0) / expected if expected else 1.0,
        }
        for group, expected in sorted(expected_groups.items())
    }

    expected_count = len(expected_paths)
    success_count = len(succeeded)
    return {
        "expected_images": expected_count,
        "succeeded_images": success_count,
        "failed_images": len(failed),
        "missing_images": len(missing),
        "extra_cached_paths": len(extra),
        "coverage_fraction": success_count / expected_count if expected_count else 1.0,
        "complete": success_count == expected_count and not extra,
        "groups": group_coverage,
        "missing_path_examples": sorted(missing)[:20],
        "extra_path_examples": sorted(extra)[:20],
    }


def _runtime_versions(torch_module: Any, transformers_module: Any) -> dict[str, str]:
    import PIL

    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pillow": PIL.__version__,
        "torch": str(torch_module.__version__),
        "transformers": str(transformers_module.__version__),
    }


def _device_metadata(device: Any, precision: str, torch_module: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"device": str(device), "precision": precision}
    if device.type == "cuda":
        index = device.index if device.index is not None else torch_module.cuda.current_device()
        properties = torch_module.cuda.get_device_properties(index)
        result.update(
            {
                "cuda_device_name": properties.name,
                "cuda_total_memory_bytes": int(properties.total_memory),
                "cuda_version": torch_module.version.cuda,
                "cudnn_version": torch_module.backends.cudnn.version(),
            }
        )
    return result


def _build_config_payload(
    args: argparse.Namespace,
    precision: str,
    device_type: str,
) -> dict[str, Any]:
    content_payload = _candidate_payload(CONTENT_CANDIDATES)
    style_payload = _candidate_payload(STYLE_CANDIDATES)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "dataset": args.dataset,
        "splits": list(args.splits),
        "model_name": args.model_name,
        "model_revision_requested": args.model_revision,
        "content_candidates": content_payload,
        "style_candidates": style_payload,
        "probability_semantics": (
            "softmax of pretrained CLIP logit-scale cosine similarities within each ordered "
            "candidate family; relative zero-shot evidence, not a calibrated posterior"
        ),
        "precision": precision,
        "device_type": device_type,
        "deterministic_seed": args.seed,
    }
    if args.dataset == "sues200":
        payload["sues_train_manifest_sha256"] = _file_sha256(
            args.sues_train_manifest
        )
    else:
        # Retain the v1 University-1652 configuration payload exactly so
        # caches started before the official SUES manifest option can resume
        # without recomputing any image evidence.
        payload["sues_split_seed"] = None
        payload["sues_train_ratio"] = None
    return payload


def _build_metadata(
    args: argparse.Namespace,
    config_payload: dict[str, Any],
    config_hash: str,
    records: Sequence[ImageRecord],
    scan_hash: str,
    store: ResultStore,
    failures: dict[str, dict[str, Any]],
    status: str,
    runtime: dict[str, Any],
) -> dict[str, Any]:
    content_payload = config_payload["content_candidates"]
    style_payload = config_payload["style_candidates"]
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": args.dataset,
        "dataset_root_hint": {
            "directory_name": args.dataset_root.name,
            "paths_are_relative_to_dataset_root": True,
            "expected_layout": (
                "train/* and test/*"
                if args.dataset == "university1652"
                else "drone_view_512/* and satellite-view/*"
            ),
        },
        "splits": list(args.splits),
        "model": {
            "name": args.model_name,
            "revision_requested": args.model_revision,
            **runtime.get("model", {}),
        },
        "content_candidates": content_payload,
        "style_candidates": style_payload,
        "hashes": {
            "content_candidates_sha256": _json_sha256(content_payload),
            "style_candidates_sha256": _json_sha256(style_payload),
            "combined_candidates_sha256": _json_sha256(
                {"content": content_payload, "style": style_payload}
            ),
            "evidence_config_sha256": config_hash,
            "scan_manifest_sha256": scan_hash,
            **runtime.get("hashes", {}),
        },
        "npz_schema": {
            "paths": "unicode[N], relative to dataset root, POSIX separators",
            "content_probs": f"float16[N,{len(CONTENT_CANDIDATES)}]",
            "style_probs": f"float16[N,{len(STYLE_CANDIDATES)}]",
            "views": "unicode[N]",
            "altitudes": "unicode[N]",
        },
        "probability_semantics": config_payload["probability_semantics"],
        "anti_leakage_guarantee": {
            "independent_per_image": True,
            "class_id_input": False,
            "label_input": False,
            "positive_match_input": False,
            "pair_input": False,
            "model_inputs": ["image_pixels", "fixed_class_agnostic_candidate_texts"],
        },
        "determinism": {
            "seed": args.seed,
            "torch_deterministic_algorithms": True,
            "cudnn_benchmark": False,
            "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
        },
        "run_configuration": {
            "batch_size": args.batch_size,
            "image_workers": args.image_workers,
            "precision": config_payload["precision"],
            "device_type": config_payload["device_type"],
            "checkpoint_every": args.checkpoint_every,
            "sues_train_manifest": (
                str(args.sues_train_manifest.resolve())
                if args.dataset == "sues200"
                else None
            ),
            "sues_train_manifest_sha256": config_payload[
                "sues_train_manifest_sha256"
            ]
            if args.dataset == "sues200"
            else None,
        },
        "coverage": _coverage_summary(records, store.keys, failures),
        "failure_list": args.output.with_suffix(".failures.json").name,
        "software": runtime.get("software", {}),
        "hardware": runtime.get("hardware", {}),
    }
    return metadata


def _validate_existing_metadata(
    metadata: dict[str, Any],
    config_hash: str,
    output: Path,
) -> None:
    if metadata.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"Cannot resume {output}: schema is {metadata.get('schema_version')!r}, "
            f"expected {SCHEMA_VERSION!r}. Use --overwrite to start again."
        )
    old_hash = metadata.get("hashes", {}).get("evidence_config_sha256")
    if old_hash != config_hash:
        raise ValueError(
            f"Cannot resume {output}: evidence configuration hash differs. "
            "This prevents mixing models, candidate orders, precision modes, or split rules. "
            "Use a new --output or pass --overwrite."
        )


def _failure_payload(
    record: ImageRecord,
    error: str,
    previous: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "path": record.relative_path,
        "view": record.view,
        "altitude": record.altitude,
        "split": record.split,
        "error": error,
        "attempts": int((previous or {}).get("attempts", 0)) + 1,
        "last_attempt_utc": datetime.now(timezone.utc).isoformat(),
    }


def run(args: argparse.Namespace) -> int:
    try:
        import torch
        import transformers
        from transformers import CLIPModel, CLIPProcessor
    except ImportError as exc:
        raise RuntimeError(
            "This command requires torch, transformers, Pillow, and NumPy. "
            "Install the project's image-evidence dependencies before running it."
        ) from exc

    _set_determinism(args.seed, torch)
    device = _resolve_device(args.device, args.allow_cpu, torch)
    precision, autocast_dtype = _resolve_precision(args.precision, device, torch)
    config_payload = _build_config_payload(args, precision, device.type)
    config_hash = _json_sha256(config_payload)
    meta_path, failure_path = _sidecar_paths(args.output)

    print(f"Scanning {args.dataset} at {args.dataset_root} ...", flush=True)
    records = scan_dataset(
        dataset=args.dataset,
        root=args.dataset_root,
        splits=args.splits,
        sues_train_manifest=args.sues_train_manifest,
    )
    scan_hash = _scan_manifest_hash(records)
    expected_paths = {record.relative_path for record in records}
    print(
        f"Found {len(records):,} unique images across splits {', '.join(args.splits)}; "
        f"scan hash {scan_hash[:12]}.",
        flush=True,
    )

    if args.output.exists() and not args.overwrite:
        if not args.resume:
            raise FileExistsError(
                f"{args.output} already exists. Use --resume or explicitly pass --overwrite."
            )
        if not meta_path.exists():
            raise FileNotFoundError(
                f"{args.output} exists without {meta_path.name}; safe resume cannot verify its schema."
            )
        existing_metadata = _load_json(meta_path, {})
        _validate_existing_metadata(existing_metadata, config_hash, args.output)
        store = ResultStore.load(args.output)
        extra = store.keys.difference(expected_paths)
        if extra:
            raise ValueError(
                f"Existing cache has {len(extra)} path(s) outside the current scan. "
                "Use the same root/splits or pass --overwrite."
            )
        print(f"Resuming with {len(store.paths):,} successful images already cached.", flush=True)
    else:
        store = ResultStore.empty()

    raw_failures = {} if args.overwrite else _load_json(failure_path, {})
    if isinstance(raw_failures, list):
        failures = {
            str(item["path"]): item
            for item in raw_failures
            if isinstance(item, dict) and "path" in item
        }
    elif isinstance(raw_failures, dict):
        failures = {
            str(path): value
            for path, value in raw_failures.items()
            if isinstance(value, dict)
        }
    else:
        raise ValueError(f"Failure list has unsupported structure: {failure_path}")
    for completed_path in store.keys:
        failures.pop(completed_path, None)

    completed_keys = store.keys
    pending_records = [
        record
        for record in records
        if record.relative_path not in completed_keys
        and (args.retry_failures or record.relative_path not in failures)
    ]
    print(f"{len(pending_records):,} images remain for inference.", flush=True)

    model_kwargs: dict[str, Any] = {
        "revision": args.model_revision,
        "cache_dir": str(args.hf_cache_dir) if args.hf_cache_dir else None,
        "local_files_only": args.local_files_only,
    }
    model_kwargs = {key: value for key, value in model_kwargs.items() if value is not None}
    processor = CLIPProcessor.from_pretrained(args.model_name, **model_kwargs)
    model = CLIPModel.from_pretrained(args.model_name, **model_kwargs).to(device)
    model.eval()

    content_prototypes = _encode_text_prototypes(
        model,
        processor,
        CONTENT_CANDIDATES,
        device,
        autocast_dtype,
        torch,
    )
    style_prototypes = _encode_text_prototypes(
        model,
        processor,
        STYLE_CANDIDATES,
        device,
        autocast_dtype,
        torch,
    )
    logit_scale = float(model.logit_scale.detach().float().exp().clamp(max=100.0).cpu())
    model_config = model.config.to_dict()
    runtime: dict[str, Any] = {
        "model": {
            "revision_resolved": getattr(model.config, "_commit_hash", None),
            "architecture": model.__class__.__name__,
            "pretrained_logit_scale": logit_scale,
        },
        "hashes": {
            "model_config_sha256": _json_sha256(model_config),
        },
        "software": _runtime_versions(torch, transformers),
        "hardware": _device_metadata(device, precision, torch),
    }

    def checkpoint(status: str) -> None:
        # The NPZ is written first so the metadata can bind the exact cache
        # bytes consumed by the formal trainer.  This prevents a stale or
        # silently modified cache from entering a reported experiment.
        _write_npz_atomic(args.output, store)
        cache_sha256 = _file_sha256(args.output)
        metadata = _build_metadata(
            args=args,
            config_payload=config_payload,
            config_hash=config_hash,
            records=records,
            scan_hash=scan_hash,
            store=store,
            failures=failures,
            status=status,
            runtime=runtime,
        )
        metadata["cache_sha256"] = cache_sha256
        metadata.setdefault("hashes", {})["cache_sha256"] = cache_sha256
        ordered_failures = {path: failures[path] for path in sorted(failures)}
        _write_json_atomic(failure_path, ordered_failures)
        _write_json_atomic(meta_path, metadata)

    attempted_since_checkpoint = 0
    attempted_since_print = 0
    attempted_total = 0
    start_time = time.perf_counter()
    status = "running"
    try:
        for offset in range(0, len(pending_records), args.batch_size):
            batch_records = pending_records[offset : offset + args.batch_size]
            loaded = _load_batch(batch_records, args.image_workers)
            good_records: list[ImageRecord] = []
            good_images: list[Image.Image] = []
            for record, image, error in loaded:
                attempted_total += 1
                attempted_since_checkpoint += 1
                attempted_since_print += 1
                if error is not None or image is None:
                    failures[record.relative_path] = _failure_payload(
                        record,
                        error or "Unknown image decoding failure",
                        failures.get(record.relative_path),
                    )
                    continue
                good_records.append(record)
                good_images.append(image)

            if good_images:
                try:
                    content_probs, style_probs = _infer_probabilities(
                        images=good_images,
                        model=model,
                        processor=processor,
                        content_prototypes=content_prototypes,
                        style_prototypes=style_prototypes,
                        logit_scale=logit_scale,
                        device=device,
                        autocast_dtype=autocast_dtype,
                        torch_module=torch,
                    )
                finally:
                    for image in good_images:
                        image.close()
                store.append_batch(good_records, content_probs, style_probs)
                for record in good_records:
                    failures.pop(record.relative_path, None)
                    completed_keys.add(record.relative_path)

            if attempted_since_print >= args.print_every:
                elapsed = max(time.perf_counter() - start_time, 1e-9)
                coverage = len(expected_paths.intersection(completed_keys)) / len(expected_paths)
                print(
                    f"Attempted {attempted_total:,}/{len(pending_records):,} pending images; "
                    f"cached {len(completed_keys):,}/{len(records):,} "
                    f"({coverage:.2%}); failures {len(failures):,}; "
                    f"{attempted_total / elapsed:.1f} images/s.",
                    flush=True,
                )
                attempted_since_print = 0

            if attempted_since_checkpoint >= args.checkpoint_every:
                checkpoint("partial")
                attempted_since_checkpoint = 0

        status = "complete"
    except KeyboardInterrupt:
        status = "interrupted"
        print("Interrupted; writing an atomic resume checkpoint.", flush=True)
        raise
    except BaseException:
        status = "error"
        print("Run failed; writing completed batches as an atomic resume checkpoint.", flush=True)
        raise
    finally:
        checkpoint(status)

    coverage = _coverage_summary(records, store.keys, failures)
    print(json.dumps({"coverage": coverage}, ensure_ascii=False, indent=2), flush=True)
    if coverage["coverage_fraction"] < args.min_coverage or coverage["extra_cached_paths"]:
        print(
            f"Coverage gate failed: {coverage['coverage_fraction']:.6f} < "
            f"{args.min_coverage:.6f}, or extra cached paths were present.",
            flush=True,
        )
        return 2
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
