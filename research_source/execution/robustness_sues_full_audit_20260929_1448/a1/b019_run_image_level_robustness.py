"""Frozen, image-level robustness evaluation for the formal retrieval models.

This evaluator is intentionally separate from ``formal_retrieval.py`` so the
training/evaluation source frozen before the main matrix is not changed.

The central integrity rule is that every corruption is applied to decoded RGB
query pixels.  Clean gallery pixels/features are never corrupted.  For the
``full`` variant, content/style evidence is recomputed from the corrupted RGB
pixels with the exact pinned CLIP model and candidate texts recorded by the
clean evidence cache.  Reusing clean query evidence under a corruption, or
perturbing an already-computed feature vector, is prohibited.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import dataclasses
import hashlib
import importlib.metadata
import json
import logging
import math
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import torch
from torchvision import transforms


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from lgm_game_pytorch import formal_retrieval as formal  # noqa: E402
from lgm_game_pytorch import generate_clip_image_evidence as clip_evidence  # noqa: E402


LOGGER = logging.getLogger("image_level_robustness")
SCHEMA_VERSION = "lgm-game.image-level-robustness.v1"
DEFAULT_CORRUPTION_SEED = 20260727
CORE_METRICS = (
    "r_at_1",
    "r_at_5",
    "r_at_10",
    "r_at_20",
    "official_trapezoid_mAP",
    "MRR",
)


@dataclass(frozen=True)
class CorruptionSpec:
    name: str
    display_name: str
    parameter: str
    values: tuple[float, ...]
    units: str
    implementation: str


# These values are copied exactly from FORMAL_EXPERIMENT_PROTOCOL.md.  The
# implementation strings remove otherwise hidden ambiguity (fill colour,
# rotation sign, and the scale used by additive noise).
CORRUPTION_SPECS: tuple[CorruptionSpec, ...] = (
    CorruptionSpec(
        name="gaussian_noise",
        display_name="Gaussian noise",
        parameter="standard_deviation",
        values=(0.02, 0.04, 0.08, 0.12, 0.18),
        units="fraction of the [0,1] RGB intensity range",
        implementation=(
            "Independent zero-mean Gaussian noise is sampled for every RGB pixel "
            "with a SHA-256-derived per-image seed, added in float32 [0,1], clipped, "
            "rounded to uint8, and then passed through the unmodified model pipeline."
        ),
    ),
    CorruptionSpec(
        name="gaussian_blur",
        display_name="Gaussian blur",
        parameter="radius",
        values=(0.5, 1.0, 2.0, 3.0, 4.0),
        units="pixels in the decoded source image",
        implementation=(
            "Pillow GaussianBlur is applied to the decoded RGB query at the fixed radius."
        ),
    ),
    CorruptionSpec(
        name="brightness",
        display_name="Brightness",
        parameter="factor",
        values=(0.80, 0.65, 0.50, 0.35, 0.20),
        units="multiplicative Pillow brightness factor",
        implementation=(
            "Pillow ImageEnhance.Brightness is applied to the decoded RGB query."
        ),
    ),
    CorruptionSpec(
        name="contrast",
        display_name="Contrast",
        parameter="factor",
        values=(0.80, 0.65, 0.50, 0.35, 0.20),
        units="multiplicative Pillow contrast factor",
        implementation=(
            "Pillow ImageEnhance.Contrast is applied to the decoded RGB query."
        ),
    ),
    CorruptionSpec(
        name="center_occlusion",
        display_name="Center occlusion",
        parameter="area_fraction",
        values=(0.05, 0.10, 0.20, 0.30, 0.40),
        units="fraction of decoded source-image area",
        implementation=(
            "A centered rectangle with width and height scaled by sqrt(area_fraction) "
            "is filled with the per-image mean RGB colour; integer dimensions are "
            "rounded and clipped to the source image."
        ),
    ),
    CorruptionSpec(
        name="rotation",
        display_name="Rotation",
        parameter="magnitude",
        values=(2.0, 5.0, 10.0, 15.0, 20.0),
        units="degrees",
        implementation=(
            "The absolute angle is fixed by severity; a SHA-256-derived per-image sign "
            "prevents a one-direction bias. Pillow bicubic rotation keeps the original "
            "canvas and fills exposed pixels with the per-image mean RGB colour."
        ),
    ),
)
SPEC_BY_NAME = {spec.name: spec for spec in CORRUPTION_SPECS}


def _configure_logging(output_dir: Path) -> logging.FileHandler:
    output_dir.mkdir(parents=True, exist_ok=True)
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False
    for handler in list(LOGGER.handlers):
        LOGGER.removeHandler(handler)
        handler.close()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(formatter)
    LOGGER.addHandler(stream)
    file_handler = logging.FileHandler(
        output_dir / "run.log", mode="a", encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    LOGGER.addHandler(file_handler)
    return file_handler


def _close_logging() -> None:
    for handler in list(LOGGER.handlers):
        handler.flush()
        LOGGER.removeHandler(handler)
        handler.close()


def _atomic_npz(path: Path, arrays: Mapping[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            np.savez_compressed(handle, **arrays)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _atomic_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in fieldnames})
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def corruption_matrix_payload() -> list[dict[str, Any]]:
    return [
        {
            "name": spec.name,
            "display_name": spec.display_name,
            "parameter": spec.parameter,
            "values": list(spec.values),
            "units": spec.units,
            "implementation": spec.implementation,
        }
        for spec in CORRUPTION_SPECS
    ]


def _per_image_seed(
    global_seed: int,
    corruption: str,
    severity_index: int,
    relative_path: str,
    stream: str,
) -> int:
    payload = (
        f"{SCHEMA_VERSION}\0{global_seed}\0{corruption}\0{severity_index}"
        f"\0{stream}\0{relative_path}"
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "little")


def _mean_rgb(image: Image.Image) -> tuple[int, int, int]:
    pixels = np.asarray(image, dtype=np.float32)
    mean = np.rint(pixels.mean(axis=(0, 1))).clip(0, 255).astype(np.uint8)
    return int(mean[0]), int(mean[1]), int(mean[2])


def apply_image_corruption(
    image: Image.Image,
    corruption: str,
    severity_index: int,
    relative_path: str,
    global_seed: int = DEFAULT_CORRUPTION_SEED,
) -> Image.Image:
    """Apply one frozen corruption to decoded RGB pixels.

    ``severity_index`` is one-based (1..5).  No feature tensor is accepted by
    this function, which makes feature-level surrogate corruptions impossible.
    """

    if not isinstance(image, Image.Image):
        raise TypeError("Image-level corruption requires a PIL.Image input.")
    if image.mode != "RGB":
        image = image.convert("RGB")
    if corruption not in SPEC_BY_NAME:
        raise ValueError(f"Unknown corruption {corruption!r}.")
    if severity_index < 1 or severity_index > 5:
        raise ValueError("severity_index must lie in 1..5.")
    spec = SPEC_BY_NAME[corruption]
    value = spec.values[severity_index - 1]

    if corruption == "gaussian_noise":
        pixels = np.asarray(image, dtype=np.float32) / np.float32(255.0)
        seed = _per_image_seed(
            global_seed, corruption, severity_index, relative_path, "noise"
        )
        rng = np.random.default_rng(seed)
        noise = rng.standard_normal(pixels.shape, dtype=np.float32)
        corrupted = np.clip(pixels + np.float32(value) * noise, 0.0, 1.0)
        uint8 = np.rint(corrupted * np.float32(255.0)).astype(np.uint8)
        return Image.fromarray(uint8, mode="RGB")
    if corruption == "gaussian_blur":
        return image.filter(ImageFilter.GaussianBlur(radius=float(value)))
    if corruption == "brightness":
        return ImageEnhance.Brightness(image).enhance(float(value))
    if corruption == "contrast":
        return ImageEnhance.Contrast(image).enhance(float(value))
    if corruption == "center_occlusion":
        pixels = np.asarray(image, dtype=np.uint8).copy()
        height, width = pixels.shape[:2]
        scale = math.sqrt(float(value))
        occlusion_width = min(width, max(1, int(round(width * scale))))
        occlusion_height = min(height, max(1, int(round(height * scale))))
        left = (width - occlusion_width) // 2
        top = (height - occlusion_height) // 2
        fill = np.asarray(_mean_rgb(image), dtype=np.uint8)
        pixels[
            top : top + occlusion_height,
            left : left + occlusion_width,
            :,
        ] = fill
        return Image.fromarray(pixels, mode="RGB")
    if corruption == "rotation":
        seed = _per_image_seed(
            global_seed, corruption, severity_index, relative_path, "sign"
        )
        signed_angle = float(value) if seed % 2 == 0 else -float(value)
        return image.rotate(
            signed_angle,
            resample=Image.Resampling.BICUBIC,
            expand=False,
            fillcolor=_mean_rgb(image),
        )
    raise AssertionError(corruption)


def _unique_records(
    records: Sequence[formal.EvidenceRecord],
) -> list[formal.EvidenceRecord]:
    by_key: dict[str, formal.EvidenceRecord] = {}
    for record in records:
        key = record.relative_path.casefold()
        previous = by_key.get(key)
        if previous is not None and previous.relative_path != record.relative_path:
            raise RuntimeError(
                "Case-insensitive path collision in official protocol: "
                f"{previous.relative_path!r} vs {record.relative_path!r}."
            )
        by_key[key] = record
    return sorted(by_key.values(), key=lambda item: item.relative_path)


def _path_membership_sha(records: Sequence[formal.EvidenceRecord]) -> str:
    return formal.canonical_sha256([record.relative_path for record in records])


def _encoded_mapping_sha(
    records: Sequence[formal.EvidenceRecord],
    encoded: Mapping[str, np.ndarray],
) -> str:
    digest = hashlib.sha256()
    for record in _unique_records(records):
        value = np.asarray(
            encoded[record.relative_path.casefold()], dtype="<f4", order="C"
        )
        digest.update(record.relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(value.shape).encode("ascii"))
        digest.update(b"\0")
        digest.update(value.tobytes(order="C"))
        digest.update(b"\n")
    return digest.hexdigest()


def _load_images(
    records: Sequence[formal.EvidenceRecord],
    *,
    corruption: str | None,
    severity_index: int | None,
    corruption_seed: int,
    workers: int,
    executor: concurrent.futures.ThreadPoolExecutor | None = None,
) -> list[Image.Image]:
    def load_one(record: formal.EvidenceRecord) -> Image.Image:
        image = formal.load_rgb(record.absolute_path)
        if corruption is None:
            return image
        if severity_index is None:
            raise AssertionError("A corruption requires a severity index.")
        return apply_image_corruption(
            image,
            corruption,
            severity_index,
            record.relative_path,
            corruption_seed,
        )

    if workers <= 1:
        return [load_one(record) for record in records]
    if executor is not None:
        return list(executor.map(load_one, records))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(load_one, records))


def _candidate_payload(
    candidates: Sequence[tuple[str, str]],
) -> list[dict[str, str]]:
    return [{"id": identifier, "text": text} for identifier, text in candidates]


class PinnedClipEvidenceEncoder:
    """Recompute content/style evidence from corrupted RGB query pixels."""

    def __init__(
        self,
        store: formal.EvidenceStore,
        device: torch.device,
        precision_request: str,
        local_files_only: bool,
        hf_cache_dir: Path | None,
    ) -> None:
        try:
            import transformers
            from transformers import CLIPModel, CLIPProcessor
        except ImportError as exc:
            raise RuntimeError(
                "The full-variant robustness run requires transformers and the "
                "pinned CLIP model used to build the clean evidence cache."
            ) from exc

        metadata_rows: list[dict[str, Any]] = []
        for descriptor in store.cache_descriptors:
            meta_path = Path(descriptor.meta_path)
            with meta_path.open("r", encoding="utf-8") as handle:
                metadata_rows.append(json.load(handle))
        if not metadata_rows:
            raise RuntimeError("No evidence metadata is available for CLIP reconstruction.")

        expected_content = _candidate_payload(clip_evidence.CONTENT_CANDIDATES)
        expected_style = _candidate_payload(clip_evidence.STYLE_CANDIDATES)
        reference = metadata_rows[0]
        reference_model = reference.get("model", {})
        reference_hashes = reference.get("hashes", {})
        reference_precision = reference.get("run_configuration", {}).get(
            "precision"
        )
        reference_semantics = reference.get("probability_semantics")
        revision = (
            reference_model.get("revision_resolved")
            or reference_model.get("revision_requested")
        )
        model_name = reference_model.get("name")
        if not model_name or not revision:
            raise RuntimeError(
                "Evidence metadata must pin both CLIP model name and immutable revision."
            )
        for metadata in metadata_rows:
            if metadata.get("content_candidates") != expected_content:
                raise RuntimeError(
                    "Evidence content candidates do not match the executable generator."
                )
            if metadata.get("style_candidates") != expected_style:
                raise RuntimeError(
                    "Evidence style candidates do not match the executable generator."
                )
            model_meta = metadata.get("model", {})
            resolved = model_meta.get("revision_resolved") or model_meta.get(
                "revision_requested"
            )
            if model_meta.get("name") != model_name or resolved != revision:
                raise RuntimeError(
                    "Merged evidence caches do not use one identical pinned CLIP source."
                )
            if (
                metadata.get("hashes", {}).get("combined_candidates_sha256")
                != reference_hashes.get("combined_candidates_sha256")
            ):
                raise RuntimeError("Merged evidence candidate hashes disagree.")
            if (
                metadata.get("hashes", {}).get("model_config_sha256")
                != reference_hashes.get("model_config_sha256")
            ):
                raise RuntimeError("Merged evidence CLIP configuration hashes disagree.")
            if (
                metadata.get("run_configuration", {}).get("precision")
                != reference_precision
            ):
                raise RuntimeError("Merged evidence caches use different CLIP precision.")
            if metadata.get("probability_semantics") != reference_semantics:
                raise RuntimeError(
                    "Merged evidence caches use different probability semantics."
                )

        cache_precision = str(reference_precision or "fp32")
        requested = cache_precision if precision_request == "match-cache" else precision_request
        if requested not in {"fp32", "fp16", "bf16"}:
            raise ValueError(f"Unsupported CLIP precision {requested!r}.")
        if device.type == "cpu" and requested == "fp16":
            raise RuntimeError(
                "The clean cache used fp16 CUDA CLIP inference. A formal full-variant "
                "robustness run must use CUDA to reproduce that evidence path."
            )
        self.precision = requested
        self.autocast_dtype = {
            "fp32": None,
            "fp16": torch.float16,
            "bf16": torch.bfloat16,
        }[requested]
        model_kwargs: dict[str, Any] = {
            "revision": revision,
            "local_files_only": local_files_only,
            "cache_dir": str(hf_cache_dir) if hf_cache_dir else None,
        }
        model_kwargs = {key: value for key, value in model_kwargs.items() if value is not None}
        self.processor = CLIPProcessor.from_pretrained(model_name, **model_kwargs)
        self.model = CLIPModel.from_pretrained(model_name, **model_kwargs).to(device)
        self.model.eval()
        resolved_loaded = getattr(self.model.config, "_commit_hash", None)
        if resolved_loaded and resolved_loaded != revision:
            raise RuntimeError(
                f"Loaded CLIP revision {resolved_loaded} differs from cache {revision}."
            )
        loaded_config_hash = formal.canonical_sha256(self.model.config.to_dict())
        expected_config_hash = reference_hashes.get("model_config_sha256")
        if expected_config_hash and loaded_config_hash != expected_config_hash:
            raise RuntimeError(
                "Loaded CLIP configuration hash differs from the evidence cache."
            )
        self.device = device
        self.content_prototypes = clip_evidence._encode_text_prototypes(
            self.model,
            self.processor,
            clip_evidence.CONTENT_CANDIDATES,
            device,
            self.autocast_dtype,
            torch,
        )
        self.style_prototypes = clip_evidence._encode_text_prototypes(
            self.model,
            self.processor,
            clip_evidence.STYLE_CANDIDATES,
            device,
            self.autocast_dtype,
            torch,
        )
        self.logit_scale = float(
            self.model.logit_scale.detach().float().exp().clamp(max=100.0).cpu()
        )
        self.provenance = {
            "model_name": model_name,
            "revision": revision,
            "loaded_revision": resolved_loaded,
            "model_config_sha256": loaded_config_hash,
            "combined_candidates_sha256": reference_hashes.get(
                "combined_candidates_sha256"
            ),
            "precision": self.precision,
            "local_files_only": local_files_only,
            "transformers_version": transformers.__version__,
            "probability_semantics": reference.get("probability_semantics"),
        }

    def infer(self, images: Sequence[Image.Image]) -> tuple[np.ndarray, np.ndarray]:
        return clip_evidence._infer_probabilities(
            images=images,
            model=self.model,
            processor=self.processor,
            content_prototypes=self.content_prototypes,
            style_prototypes=self.style_prototypes,
            logit_scale=self.logit_scale,
            device=self.device,
            autocast_dtype=self.autocast_dtype,
            torch_module=torch,
        )


@torch.inference_mode()
def encode_records_from_pixels(
    model: formal.FormalRetrievalModel,
    records: Sequence[formal.EvidenceRecord],
    store: formal.EvidenceStore,
    eval_transform: transforms.Compose,
    device: torch.device,
    batch_size: int,
    image_workers: int,
    amp_enabled: bool,
    *,
    corruption: str | None,
    severity_index: int | None,
    corruption_seed: int,
    clip_encoder: PinnedClipEvidenceEncoder | Any | None,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Encode unique records, starting from RGB pixels for every active visual branch."""

    ordered = _unique_records(records)
    encoded: dict[str, np.ndarray] = {}
    model.eval()
    evidence_mode = (
        "clean_cache"
        if corruption is None
        else (
            "recomputed_from_corrupted_rgb_pixels"
            if model.variant == "full"
            else "not_used_by_visual_variant"
        )
    )
    started = time.perf_counter()
    executor = (
        concurrent.futures.ThreadPoolExecutor(max_workers=image_workers)
        if image_workers > 1
        else None
    )
    try:
        for start in range(0, len(ordered), batch_size):
            batch_records = ordered[start : start + batch_size]
            images = _load_images(
                batch_records,
                corruption=corruption,
                severity_index=severity_index,
                corruption_seed=corruption_seed,
                workers=image_workers,
                executor=executor,
            )
            visual = torch.stack([eval_transform(image) for image in images]).to(
                device, non_blocking=device.type == "cuda"
            )
            if corruption is not None and model.variant == "full":
                if clip_encoder is None:
                    raise RuntimeError(
                        "Full-variant corrupted queries require CLIP evidence recomputation."
                    )
                content_np, style_np = clip_encoder.infer(images)
                content_np = np.asarray(content_np, dtype=np.float32)
                style_np = np.asarray(style_np, dtype=np.float32)
            else:
                content_np = np.stack(
                    [store.content_probs[record.evidence_index] for record in batch_records]
                ).astype(np.float32, copy=False)
                style_np = np.stack(
                    [store.style_probs[record.evidence_index] for record in batch_records]
                ).astype(np.float32, copy=False)
            content = torch.from_numpy(content_np).to(
                device, non_blocking=device.type == "cuda"
            )
            style = torch.from_numpy(style_np).to(
                device, non_blocking=device.type == "cuda"
            )
            with formal.amp_context(device, amp_enabled):
                features = model.encode_image(visual, content, style)
            values = features.float().cpu().numpy()
            if values.shape[0] != len(batch_records):
                raise RuntimeError("Model feature count does not match decoded query count.")
            for record, value in zip(batch_records, values):
                key = record.relative_path.casefold()
                if key in encoded:
                    raise RuntimeError(f"Duplicate encoded record {record.relative_path!r}.")
                encoded[key] = np.asarray(value, dtype=np.float32)
    finally:
        if executor is not None:
            executor.shutdown(wait=True)

    expected_keys = {record.relative_path.casefold() for record in ordered}
    actual_keys = set(encoded)
    if actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        extra = sorted(actual_keys - expected_keys)
        raise RuntimeError(
            "Image encoding failed the complete-coverage gate: "
            f"missing={len(missing)}, extra={len(extra)}, "
            f"examples={missing[:3] + extra[:3]}."
        )
    coverage = {
        "expected_unique_images": len(ordered),
        "encoded_unique_images": len(encoded),
        "coverage_fraction": len(encoded) / len(ordered) if ordered else 1.0,
        "missing_images": 0,
        "extra_images": 0,
        "complete": True,
        "path_membership_sha256": _path_membership_sha(ordered),
        "encoded_feature_sha256": _encoded_mapping_sha(ordered, encoded),
        "embedding_dim": (
            int(next(iter(encoded.values())).shape[0]) if encoded else 0
        ),
        "embedding_storage_dtype_for_hash": "little-endian float32",
        "pixels_decoded_for_every_active_visual_embedding": True,
        "corruption_applied_before_all_model_preprocessing": corruption is not None,
        "query_content_style_evidence_mode": evidence_mode,
        "elapsed_seconds": time.perf_counter() - started,
    }
    return encoded, coverage


def rank_task_split(
    task: formal.RetrievalTask,
    query_encoded: Mapping[str, np.ndarray],
    gallery_encoded: Mapping[str, np.ndarray],
    chunk_size: int,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """Exact full-gallery ranking with separate query and clean-gallery maps."""

    query_features = np.stack(
        [query_encoded[record.relative_path.casefold()] for record in task.query]
    ).astype(np.float32, copy=False)
    gallery_features = np.stack(
        [gallery_encoded[record.relative_path.casefold()] for record in task.gallery]
    ).astype(np.float32, copy=False)
    query_labels = np.asarray([record.label for record in task.query])
    gallery_labels = np.asarray([record.label for record in task.gallery])
    recalls = {1: 0, 5: 0, 10: 0, 20: 0}
    aps = np.empty(len(task.query), dtype=np.float32)
    reciprocal_ranks = np.empty(len(task.query), dtype=np.float32)
    first_positive_ranks = np.empty(len(task.query), dtype=np.int64)
    margins = np.empty(len(task.query), dtype=np.float32)
    correct = np.empty(len(task.query), dtype=np.bool_)
    top1_indices = np.empty(len(task.query), dtype=np.int64)

    for start in range(0, len(task.query), chunk_size):
        stop = min(start + chunk_size, len(task.query))
        scores = query_features[start:stop] @ gallery_features.T
        order = np.argsort(-scores, axis=1, kind="stable")
        for local_index in range(stop - start):
            query_index = start + local_index
            ranking = order[local_index]
            relevant = gallery_labels[ranking] == query_labels[query_index]
            positions = np.flatnonzero(relevant)
            if positions.size == 0:
                raise RuntimeError(
                    f"No positive for {task.name} query "
                    f"{task.query[query_index].relative_path}."
                )
            first_rank = int(positions[0])
            first_positive_ranks[query_index] = first_rank
            for k in recalls:
                recalls[k] += int(first_rank < min(k, len(task.gallery)))
            aps[query_index] = formal.official_trapezoid_ap(positions)
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
        "protocol": task.protocol,
    }
    arrays = {
        "margin": margins,
        "correct": correct,
        "first_positive_rank_zero_based": first_positive_ranks,
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


def evaluate_tasks_split(
    tasks: Sequence[formal.RetrievalTask],
    query_encoded: Mapping[str, np.ndarray],
    gallery_encoded: Mapping[str, np.ndarray],
    chunk_size: int,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, np.ndarray]]]:
    results: dict[str, dict[str, Any]] = {}
    arrays: dict[str, dict[str, np.ndarray]] = {}
    for task in tasks:
        metrics, task_arrays = rank_task_split(
            task, query_encoded, gallery_encoded, chunk_size
        )
        results[task.name] = metrics
        arrays[task.name] = task_arrays
        LOGGER.info(
            "%s | R@1 %.2f | R@5 %.2f | mAP %.2f | MRR %.2f",
            task.name,
            100.0 * metrics["r_at_1"],
            100.0 * metrics["r_at_5"],
            100.0 * metrics["official_trapezoid_mAP"],
            100.0 * metrics["MRR"],
        )
    return results, arrays


def compute_degradation(
    clean_results: Mapping[str, Mapping[str, Any]],
    corrupted_results: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, dict[str, float | None]]]:
    if set(clean_results) != set(corrupted_results):
        raise RuntimeError("Clean and corrupted task sets differ.")
    output: dict[str, dict[str, dict[str, float | None]]] = {}
    for task in clean_results:
        output[task] = {}
        for metric in CORE_METRICS:
            clean = float(clean_results[task][metric])
            corrupted = float(corrupted_results[task][metric])
            absolute_drop = clean - corrupted
            output[task][metric] = {
                "clean": clean,
                "corrupted": corrupted,
                "absolute_drop_fraction": absolute_drop,
                "percentage_point_drop": 100.0 * absolute_drop,
                "relative_drop_fraction": (
                    absolute_drop / clean if clean != 0.0 else None
                ),
                "relative_drop_percent": (
                    100.0 * absolute_drop / clean if clean != 0.0 else None
                ),
            }
    return output


def _augment_with_clean_arrays(
    corrupted: Mapping[str, np.ndarray],
    clean: Mapping[str, np.ndarray],
) -> dict[str, np.ndarray]:
    if not np.array_equal(corrupted["query_paths"], clean["query_paths"]):
        raise RuntimeError("Per-query order differs from the clean baseline.")
    output = {key: np.asarray(value) for key, value in corrupted.items()}
    output.update(
        {
            "clean_margin": np.asarray(clean["margin"]),
            "clean_correct": np.asarray(clean["correct"]),
            "clean_first_positive_rank_zero_based": np.asarray(
                clean["first_positive_rank_zero_based"]
            ),
            "clean_per_query_official_trapezoid_AP": np.asarray(
                clean["per_query_official_trapezoid_AP"]
            ),
            "clean_reciprocal_rank": np.asarray(clean["reciprocal_rank"]),
            "delta_official_trapezoid_AP_corrupted_minus_clean": (
                np.asarray(corrupted["per_query_official_trapezoid_AP"])
                - np.asarray(clean["per_query_official_trapezoid_AP"])
            ),
            "delta_reciprocal_rank_corrupted_minus_clean": (
                np.asarray(corrupted["reciprocal_rank"])
                - np.asarray(clean["reciprocal_rank"])
            ),
            "top1_correctness_transition_corrupted_minus_clean": (
                np.asarray(corrupted["correct"], dtype=np.int8)
                - np.asarray(clean["correct"], dtype=np.int8)
            ),
        }
    )
    return output


def _artifact_inventory(directory: Path, excluded_names: set[str]) -> dict[str, Any]:
    artifacts: dict[str, Any] = {}
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name not in excluded_names:
            artifacts[path.relative_to(directory).as_posix()] = {
                "sha256": formal.sha256_file(path),
                "bytes": path.stat().st_size,
            }
    return artifacts


def _condition_payload(
    *,
    corruption: str | None,
    severity_index: int | None,
    corruption_seed: int,
) -> dict[str, Any]:
    if corruption is None:
        return {
            "kind": "clean",
            "name": "clean",
            "query_pixels": "decoded without corruption",
            "gallery": "clean",
        }
    if severity_index is None:
        raise AssertionError("Corruption payload requires severity.")
    spec = SPEC_BY_NAME[corruption]
    return {
        "kind": "corruption",
        "name": spec.name,
        "display_name": spec.display_name,
        "severity_index": severity_index,
        "parameter": spec.parameter,
        "value": spec.values[severity_index - 1],
        "units": spec.units,
        "implementation": spec.implementation,
        "corruption_seed": corruption_seed,
        "query_only": True,
        "gallery": "clean",
    }


def write_condition(
    condition_dir: Path,
    *,
    run_config_sha256: str,
    condition: Mapping[str, Any],
    results: Mapping[str, Mapping[str, Any]],
    arrays: Mapping[str, Mapping[str, np.ndarray]],
    query_coverage: Mapping[str, Any],
    clean_results: Mapping[str, Mapping[str, Any]] | None,
    clean_arrays: Mapping[str, Mapping[str, np.ndarray]] | None,
    elapsed_seconds: float,
) -> dict[str, Any]:
    condition_dir.mkdir(parents=True, exist_ok=True)
    arrays_dir = condition_dir / "per_query_arrays"
    degradation = (
        compute_degradation(clean_results, results)
        if clean_results is not None
        else None
    )
    for task, task_arrays in arrays.items():
        saved = (
            _augment_with_clean_arrays(task_arrays, clean_arrays[task])
            if clean_arrays is not None
            else {key: np.asarray(value) for key, value in task_arrays.items()}
        )
        _atomic_npz(
            arrays_dir / f"{formal.slugify(task)}_per_query.npz",
            saved,
        )

    metrics_payload = {
        "schema_version": SCHEMA_VERSION,
        "unit": "fraction",
        "condition": dict(condition),
        "full_gallery": True,
        "clean_gallery_for_every_condition": True,
        "AP_definition": (
            "Official trapezoidal interpolation used by the University-1652/SUES "
            "reference evaluator."
        ),
        "results": results,
        "degradation_vs_clean": degradation,
    }
    formal.atomic_json_dump(condition_dir / "metrics.json", metrics_payload)
    formal.write_metrics_csv(condition_dir / "metrics.csv", results)
    if degradation is not None:
        rows: list[dict[str, Any]] = []
        for task, task_metrics in degradation.items():
            for metric, values in task_metrics.items():
                rows.append(
                    {
                        "task": task,
                        "metric": metric,
                        **values,
                    }
                )
        _atomic_csv(
            condition_dir / "degradation_vs_clean.csv",
            (
                "task",
                "metric",
                "clean",
                "corrupted",
                "absolute_drop_fraction",
                "percentage_point_drop",
                "relative_drop_fraction",
                "relative_drop_percent",
            ),
            rows,
        )

    condition_sha = formal.canonical_sha256(
        {"run_config_sha256": run_config_sha256, "condition": condition}
    )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "status": "completed",
        "completed_utc": formal.utc_now(),
        "run_config_sha256": run_config_sha256,
        "condition_sha256": condition_sha,
        "condition": dict(condition),
        "query_coverage": dict(query_coverage),
        "all_official_queries_used": bool(query_coverage.get("complete")),
        "clean_gallery_used": True,
        "feature_level_corruption_used": False,
        "elapsed_seconds": elapsed_seconds,
        "artifacts": _artifact_inventory(
            condition_dir, {"condition_manifest.json"}
        ),
    }
    manifest["payload_sha256"] = formal.canonical_sha256(manifest)
    formal.atomic_json_dump(condition_dir / "condition_manifest.json", manifest)
    return metrics_payload


def _load_completed_condition(
    condition_dir: Path,
    *,
    run_config_sha256: str,
    condition: Mapping[str, Any],
) -> dict[str, Any] | None:
    manifest_path = condition_dir / "condition_manifest.json"
    metrics_path = condition_dir / "metrics.json"
    if not manifest_path.is_file() or not metrics_path.is_file():
        return None
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    expected_sha = formal.canonical_sha256(
        {"run_config_sha256": run_config_sha256, "condition": condition}
    )
    if (
        manifest.get("status") != "completed"
        or manifest.get("run_config_sha256") != run_config_sha256
        or manifest.get("condition_sha256") != expected_sha
        or manifest.get("feature_level_corruption_used") is not False
        or manifest.get("clean_gallery_used") is not True
        or manifest.get("all_official_queries_used") is not True
    ):
        return None
    payload_copy = dict(manifest)
    declared_payload_sha = payload_copy.pop("payload_sha256", None)
    if declared_payload_sha != formal.canonical_sha256(payload_copy):
        raise RuntimeError(f"Condition manifest hash mismatch: {manifest_path}")
    for relative, descriptor in manifest.get("artifacts", {}).items():
        path = condition_dir / relative
        if (
            not path.is_file()
            or path.stat().st_size != int(descriptor["bytes"])
            or formal.sha256_file(path) != descriptor["sha256"]
        ):
            raise RuntimeError(f"Completed condition artifact hash mismatch: {path}")
    with metrics_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _validate_frozen_checkpoint(
    checkpoint_path: Path,
    checkpoint: Mapping[str, Any],
    dataset: str,
) -> dict[str, Any]:
    if checkpoint.get("schema_version") != formal.SCHEMA_VERSION:
        raise RuntimeError("Checkpoint does not use the formal retrieval schema.")
    immutable = checkpoint.get("immutable_config", {})
    model_config = checkpoint.get("model_config", {})
    variant = model_config.get("variant")
    if immutable.get("dataset") != dataset:
        raise RuntimeError(
            f"Checkpoint dataset {immutable.get('dataset')!r} != requested {dataset!r}."
        )
    if int(immutable.get("seed", -1)) != 1:
        raise RuntimeError("Frozen robustness evaluation accepts only seed-1 checkpoints.")
    if variant not in {"visual", "full"}:
        raise RuntimeError(
            "Frozen robustness evaluation accepts only visual or full checkpoints."
        )
    expected_model = {
        "backbone": "resnet18",
        "embed_dim": 512,
        "dropout": 0.20,
        "image_size": 224,
        "resize_size": 256,
    }
    for key, expected in expected_model.items():
        if model_config.get(key) != expected:
            raise RuntimeError(
                f"Checkpoint {key}={model_config.get(key)!r}; frozen main value is "
                f"{expected!r}."
            )
    optimization = immutable.get("optimization", {})
    expected_optimization = {
        "epochs": 80,
        "warmup_epochs": 5,
        "identities_per_batch": 16,
        "instances_per_identity": 4,
        "samples_per_class_per_epoch": 0,
        "steps_per_epoch_requested": 0,
        "amp": True,
    }
    for key, expected in expected_optimization.items():
        if optimization.get(key) != expected:
            raise RuntimeError(
                f"Checkpoint optimization.{key}={optimization.get(key)!r}; "
                f"frozen value is {expected!r}."
            )
    expected_steps = 652 if dataset == "university1652" else 375
    if int(optimization.get("steps_per_epoch_actual", -1)) != expected_steps:
        raise RuntimeError(
            f"Frozen {dataset} checkpoint requires {expected_steps} optimizer "
            "steps per epoch."
        )
    history = checkpoint.get("history", [])
    if (
        int(checkpoint.get("epoch", -1)) != 79
        or len(history) != 80
        or int(checkpoint.get("best_epoch", -1)) != 79
    ):
        raise RuntimeError(
            "Frozen no-validation checkpoint must be the pre-specified final epoch "
            "(epoch index 79, 80 history rows, best epoch index 79)."
        )
    if immutable.get("validation_ids"):
        raise RuntimeError("Frozen final-fit checkpoint must have no validation holdout.")
    if any(int(row.get("optimizer_steps", -1)) != expected_steps for row in history):
        raise RuntimeError("Checkpoint history contains a non-frozen optimizer-step count.")

    sibling_manifest = checkpoint_path.parent / "run_manifest.json"
    if not sibling_manifest.is_file():
        raise FileNotFoundError(
            f"Completed training manifest is required beside the checkpoint: "
            f"{sibling_manifest}"
        )
    with sibling_manifest.open("r", encoding="utf-8") as handle:
        training_manifest = json.load(handle)
    if (
        training_manifest.get("status") != "completed"
        or int(training_manifest.get("epochs_completed", -1)) != 80
        or training_manifest.get("test_protocol_was_evaluated") is not False
        or training_manifest.get("run_config_sha256")
        != checkpoint.get("run_config_sha256")
    ):
        raise RuntimeError("Sibling training manifest is not a completed frozen run.")
    return {
        "variant": variant,
        "seed": 1,
        "selected_training_epoch_one_based": 80,
        "checkpoint_sha256": formal.sha256_file(checkpoint_path),
        "training_run_config_sha256": checkpoint.get("run_config_sha256"),
        "training_code_sha256": immutable.get("code_sha256"),
        "training_manifest_path": str(sibling_manifest.resolve()),
        "training_manifest_sha256": formal.sha256_file(sibling_manifest),
    }


def _clip_clean_reproduction_audit(
    clip_encoder: PinnedClipEvidenceEncoder,
    records: Sequence[formal.EvidenceRecord],
    store: formal.EvidenceStore,
    sample_count: int,
    seed: int,
    workers: int,
    output_path: Path,
) -> dict[str, Any]:
    ordered = sorted(
        _unique_records(records),
        key=lambda record: hashlib.sha256(
            f"{seed}\0{record.relative_path}".encode("utf-8")
        ).hexdigest(),
    )[:sample_count]
    content_parts: list[np.ndarray] = []
    style_parts: list[np.ndarray] = []
    batch_size = min(128, max(1, sample_count))
    for start in range(0, len(ordered), batch_size):
        batch_records = ordered[start : start + batch_size]
        images = _load_images(
            batch_records,
            corruption=None,
            severity_index=None,
            corruption_seed=seed,
            workers=workers,
        )
        content, style = clip_encoder.infer(images)
        content_parts.append(np.asarray(content, dtype=np.float32))
        style_parts.append(np.asarray(style, dtype=np.float32))
    predicted_content = np.concatenate(content_parts, axis=0)
    predicted_style = np.concatenate(style_parts, axis=0)
    cached_content = np.stack(
        [store.content_probs[record.evidence_index] for record in ordered]
    ).astype(np.float32)
    cached_style = np.stack(
        [store.style_probs[record.evidence_index] for record in ordered]
    ).astype(np.float32)
    content_error = np.abs(predicted_content - cached_content)
    style_error = np.abs(predicted_style - cached_style)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "purpose": (
            "Audit that the pinned CLIP executable path reproduces clean cached "
            "evidence before it is used on corrupted pixels."
        ),
        "samples": len(ordered),
        "sample_path_membership_sha256": _path_membership_sha(ordered),
        "selection_seed": seed,
        "content": {
            "mean_absolute_error": float(content_error.mean()),
            "max_absolute_error": float(content_error.max(initial=0.0)),
            "float16_exact_fraction": float(
                np.mean(
                    predicted_content.astype(np.float16)
                    == cached_content.astype(np.float16)
                )
            ),
        },
        "style": {
            "mean_absolute_error": float(style_error.mean()),
            "max_absolute_error": float(style_error.max(initial=0.0)),
            "float16_exact_fraction": float(
                np.mean(
                    predicted_style.astype(np.float16)
                    == cached_style.astype(np.float16)
                )
            ),
        },
        "clip_provenance": clip_encoder.provenance,
    }
    payload["payload_sha256"] = formal.canonical_sha256(payload)
    formal.atomic_json_dump(output_path, payload)
    return payload


def _summary_rows(
    condition: Mapping[str, Any],
    metrics_payload: Mapping[str, Any],
) -> list[dict[str, Any]]:
    degradation = metrics_payload.get("degradation_vs_clean")
    if degradation is None:
        return []
    rows: list[dict[str, Any]] = []
    for task, task_metrics in degradation.items():
        for metric, values in task_metrics.items():
            rows.append(
                {
                    "corruption": condition["name"],
                    "severity_index": condition["severity_index"],
                    "parameter": condition["parameter"],
                    "value": condition["value"],
                    "units": condition["units"],
                    "task": task,
                    "metric": metric,
                    **values,
                }
            )
    return rows


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the frozen six-corruption by five-severity image-level robustness "
            "matrix with corrupted official queries and clean full galleries."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--dataset",
        required=True,
        choices=("university1652", "sues200"),
    )
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--evidence", required=True, nargs="+", type=Path)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--sues-manifest",
        type=Path,
        default=Path(formal.default_sues_manifest_path()),
    )
    parser.add_argument("--device", default="auto")
    parser.add_argument("--eval-batch-size", type=int, default=128)
    parser.add_argument("--eval-chunk-size", type=int, default=128)
    parser.add_argument("--image-workers", type=int, default=8)
    parser.add_argument(
        "--amp",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--corruption-seed",
        type=int,
        default=DEFAULT_CORRUPTION_SEED,
        help="Fixed global seed used only for Gaussian-noise samples and rotation signs.",
    )
    parser.add_argument(
        "--clip-precision",
        choices=("match-cache", "fp32", "fp16", "bf16"),
        default="match-cache",
    )
    parser.add_argument(
        "--clip-local-files-only",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Require the exact pinned CLIP revision in the local Hugging Face cache.",
    )
    parser.add_argument("--hf-cache-dir", type=Path, default=None)
    parser.add_argument(
        "--clip-clean-audit-samples",
        type=int,
        default=64,
    )
    args = parser.parse_args(argv)
    if args.eval_batch_size <= 0 or args.eval_chunk_size <= 0:
        parser.error("Evaluation batch and ranking chunk sizes must be positive.")
    if args.image_workers < 0:
        parser.error("--image-workers cannot be negative.")
    if args.clip_clean_audit_samples <= 0:
        parser.error("--clip-clean-audit-samples must be positive.")
    return args


def run(args: argparse.Namespace) -> None:
    output_dir = args.output_dir.expanduser().resolve()
    _configure_logging(output_dir)
    started = time.perf_counter()
    try:
        formal.seed_everything(1)
        dataset = formal.normalize_dataset_name(args.dataset)
        data_root = args.data_root.expanduser().resolve(strict=True)
        checkpoint_path = args.checkpoint.expanduser().resolve(strict=True)
        device = formal.choose_device(args.device)
        amp_enabled = bool(args.amp and device.type == "cuda")
        checkpoint = formal.load_torch_checkpoint(checkpoint_path, "cpu")
        checkpoint_info = _validate_frozen_checkpoint(
            checkpoint_path, checkpoint, dataset
        )
        store = formal.EvidenceStore.load(
            [path.expanduser().resolve(strict=True) for path in args.evidence]
        )
        formal.validate_checkpoint_evidence_schema(checkpoint, store)
        records = formal.derive_all_records(store, data_root, dataset)
        sues_manifest_path = args.sues_manifest.expanduser()
        sues_train_ids, sues_manifest_info = formal.parse_sues_manifest(
            sues_manifest_path
        )
        if dataset == "sues200":
            trained_manifest = checkpoint["immutable_config"].get("sues_manifest", {})
            if trained_manifest.get("sha256") != sues_manifest_info["sha256"]:
                raise RuntimeError(
                    "SUES official manifest hash differs between training and robustness."
                )
        tasks = formal.build_official_evaluation_tasks(
            records, dataset, sues_train_ids
        )
        query_records = _unique_records(
            [record for task in tasks for record in task.query]
        )
        gallery_records = _unique_records(
            [record for task in tasks for record in task.gallery]
        )
        protocol_sha = formal.protocol_membership_hash(tasks)
        inventory = formal.inventory_hash(
            [record for task in tasks for record in (*task.query, *task.gallery)],
            "content",
        )
        delivery_root = Path(__file__).resolve().parents[2]
        protocol_path = delivery_root / "FORMAL_EXPERIMENT_PROTOCOL.md"
        sources = {
            "robustness_evaluator": {
                "path": str(Path(__file__).resolve()),
                "sha256": formal.sha256_file(Path(__file__).resolve()),
            },
            "formal_retrieval": {
                "path": str(Path(formal.__file__).resolve()),
                "sha256": formal.sha256_file(Path(formal.__file__).resolve()),
            },
            "clip_evidence_generator": {
                "path": str(Path(clip_evidence.__file__).resolve()),
                "sha256": formal.sha256_file(Path(clip_evidence.__file__).resolve()),
            },
            "frozen_protocol": {
                "path": str(protocol_path.resolve(strict=True)),
                "sha256": formal.sha256_file(protocol_path),
            },
        }
        environment = formal.environment_manifest(device)
        for package_name in (
            "transformers",
            "huggingface-hub",
            "tokenizers",
            "safetensors",
        ):
            try:
                environment["packages"][package_name] = importlib.metadata.version(
                    package_name
                )
            except importlib.metadata.PackageNotFoundError:
                environment["packages"][package_name] = "not-installed"
        run_config_immutable = {
            "schema_version": SCHEMA_VERSION,
            "dataset": dataset,
            "data_root": str(data_root),
            "checkpoint": checkpoint_info,
            "evidence_caches": [
                dataclasses.asdict(descriptor)
                for descriptor in store.cache_descriptors
            ],
            "sues_manifest": (
                sues_manifest_info if dataset == "sues200" else None
            ),
            "protocol_membership_sha256": protocol_sha,
            "image_inventory": inventory,
            "official_task_scale": {
                task.name: {
                    "queries": len(task.query),
                    "gallery": len(task.gallery),
                    "query_identities": len({record.label for record in task.query}),
                    "gallery_identities": len({record.label for record in task.gallery}),
                    "protocol": task.protocol,
                }
                for task in tasks
            },
            "unique_query_images": len(query_records),
            "unique_clean_gallery_images": len(gallery_records),
            "query_path_membership_sha256": _path_membership_sha(query_records),
            "gallery_path_membership_sha256": _path_membership_sha(gallery_records),
            "corruption_matrix": corruption_matrix_payload(),
            "corruption_seed": args.corruption_seed,
            "ranking": {
                "score": "float32 query matrix @ float32 clean-gallery matrix.T",
                "sort": "numpy stable descending argsort",
                "chunk_size": args.eval_chunk_size,
                "full_gallery": True,
            },
            "encoding": {
                "eval_batch_size": args.eval_batch_size,
                "image_workers": args.image_workers,
                "amp": amp_enabled,
                "clip_precision": args.clip_precision,
                "clip_local_files_only": args.clip_local_files_only,
                "clip_clean_audit_samples": args.clip_clean_audit_samples,
            },
            "sources": sources,
            "environment": environment,
            "environment_sha256": formal.canonical_sha256(environment),
            "integrity_constraints": {
                "corrupt_decoded_query_rgb_pixels": True,
                "feature_level_corruption": False,
                "clean_gallery_for_all_conditions": True,
                "recompute_full_variant_query_clip_evidence_after_corruption": True,
                "all_official_queries_required": True,
                "condition_failures_never_skipped": True,
            },
        }
        run_config_sha = formal.canonical_sha256(run_config_immutable)
        run_config_path = output_dir / "run_config.json"
        if run_config_path.is_file():
            with run_config_path.open("r", encoding="utf-8") as handle:
                existing = json.load(handle)
            if existing.get("run_config_sha256") != run_config_sha:
                raise RuntimeError(
                    "Output directory contains a different robustness configuration. "
                    "Use a new output directory; results are never mixed or deleted."
                )
        else:
            formal.atomic_json_dump(
                run_config_path,
                {
                    "created_utc": formal.utc_now(),
                    "run_config_sha256": run_config_sha,
                    "immutable_config": run_config_immutable,
                    "environment": environment,
                },
            )

        model_config = dict(checkpoint["model_config"])
        model = formal.FormalRetrievalModel(
            variant=model_config["variant"],
            backbone=model_config["backbone"],
            embed_dim=int(model_config["embed_dim"]),
            dropout=float(model_config["dropout"]),
            pretrained=False,
        )
        model.load_state_dict(checkpoint["model_state"], strict=True)
        model.to(device)
        _, eval_transform = formal.build_transforms(
            int(model_config["resize_size"]), int(model_config["image_size"])
        )

        LOGGER.info(
            "Encoding %d unique clean gallery images for %s/%s.",
            len(gallery_records),
            dataset,
            model.variant,
        )
        clean_gallery_encoded, gallery_coverage = encode_records_from_pixels(
            model,
            gallery_records,
            store,
            eval_transform,
            device,
            args.eval_batch_size,
            args.image_workers,
            amp_enabled,
            corruption=None,
            severity_index=None,
            corruption_seed=args.corruption_seed,
            clip_encoder=None,
        )
        LOGGER.info("Encoding %d unique clean query images.", len(query_records))
        clean_query_encoded, clean_query_coverage = encode_records_from_pixels(
            model,
            query_records,
            store,
            eval_transform,
            device,
            args.eval_batch_size,
            args.image_workers,
            amp_enabled,
            corruption=None,
            severity_index=None,
            corruption_seed=args.corruption_seed,
            clip_encoder=None,
        )
        clean_results, clean_arrays = evaluate_tasks_split(
            tasks,
            clean_query_encoded,
            clean_gallery_encoded,
            args.eval_chunk_size,
        )
        clean_condition = _condition_payload(
            corruption=None,
            severity_index=None,
            corruption_seed=args.corruption_seed,
        )
        clean_payload = write_condition(
            output_dir / "clean",
            run_config_sha256=run_config_sha,
            condition=clean_condition,
            results=clean_results,
            arrays=clean_arrays,
            query_coverage=clean_query_coverage,
            clean_results=None,
            clean_arrays=None,
            elapsed_seconds=float(clean_query_coverage["elapsed_seconds"]),
        )

        clip_encoder: PinnedClipEvidenceEncoder | None = None
        clip_audit: dict[str, Any] | None = None
        if model.variant == "full":
            clip_encoder = PinnedClipEvidenceEncoder(
                store=store,
                device=device,
                precision_request=args.clip_precision,
                local_files_only=args.clip_local_files_only,
                hf_cache_dir=args.hf_cache_dir,
            )
            clip_audit = _clip_clean_reproduction_audit(
                clip_encoder=clip_encoder,
                records=query_records,
                store=store,
                sample_count=min(
                    args.clip_clean_audit_samples, len(query_records)
                ),
                seed=args.corruption_seed,
                workers=args.image_workers,
                output_path=output_dir / "clip_clean_reproduction_audit.json",
            )

        all_summary_rows: list[dict[str, Any]] = []
        condition_records: list[dict[str, Any]] = []
        for spec in CORRUPTION_SPECS:
            for severity_index in range(1, 6):
                condition = _condition_payload(
                    corruption=spec.name,
                    severity_index=severity_index,
                    corruption_seed=args.corruption_seed,
                )
                condition_dir = (
                    output_dir
                    / "conditions"
                    / spec.name
                    / f"severity_{severity_index:02d}"
                )
                completed = _load_completed_condition(
                    condition_dir,
                    run_config_sha256=run_config_sha,
                    condition=condition,
                )
                if completed is not None:
                    LOGGER.info(
                        "Verified and skipped completed %s severity %d.",
                        spec.name,
                        severity_index,
                    )
                    all_summary_rows.extend(
                        _summary_rows(condition, completed)
                    )
                    condition_records.append(
                        {
                            "condition": condition,
                            "status": "verified_existing",
                            "directory": str(condition_dir),
                        }
                    )
                    continue

                LOGGER.info(
                    "Encoding every official query: %s severity %d (%s=%s).",
                    spec.name,
                    severity_index,
                    spec.parameter,
                    spec.values[severity_index - 1],
                )
                condition_started = time.perf_counter()
                corrupted_encoded, query_coverage = encode_records_from_pixels(
                    model,
                    query_records,
                    store,
                    eval_transform,
                    device,
                    args.eval_batch_size,
                    args.image_workers,
                    amp_enabled,
                    corruption=spec.name,
                    severity_index=severity_index,
                    corruption_seed=args.corruption_seed,
                    clip_encoder=clip_encoder,
                )
                results, arrays = evaluate_tasks_split(
                    tasks,
                    corrupted_encoded,
                    clean_gallery_encoded,
                    args.eval_chunk_size,
                )
                payload = write_condition(
                    condition_dir,
                    run_config_sha256=run_config_sha,
                    condition=condition,
                    results=results,
                    arrays=arrays,
                    query_coverage=query_coverage,
                    clean_results=clean_results,
                    clean_arrays=clean_arrays,
                    elapsed_seconds=time.perf_counter() - condition_started,
                )
                all_summary_rows.extend(_summary_rows(condition, payload))
                condition_records.append(
                    {
                        "condition": condition,
                        "status": "completed",
                        "directory": str(condition_dir),
                    }
                )

        summary_fields = (
            "corruption",
            "severity_index",
            "parameter",
            "value",
            "units",
            "task",
            "metric",
            "clean",
            "corrupted",
            "absolute_drop_fraction",
            "percentage_point_drop",
            "relative_drop_fraction",
            "relative_drop_percent",
        )
        _atomic_csv(
            output_dir / "robustness_summary.csv",
            summary_fields,
            all_summary_rows,
        )
        summary_payload = {
            "schema_version": SCHEMA_VERSION,
            "run_config_sha256": run_config_sha,
            "clean": clean_payload,
            "corruption_conditions": condition_records,
            "rows": all_summary_rows,
        }
        formal.atomic_json_dump(
            output_dir / "robustness_summary.json", summary_payload
        )

        final_manifest = {
            "schema_version": SCHEMA_VERSION,
            "status": "completed",
            "completed_utc": formal.utc_now(),
            "run_config_sha256": run_config_sha,
            "dataset": dataset,
            "variant": model.variant,
            "checkpoint": checkpoint_info,
            "expected_corruption_conditions": 30,
            "completed_corruption_conditions": len(condition_records),
            "condition_count_complete": len(condition_records) == 30,
            "clean_query_coverage": clean_query_coverage,
            "clean_gallery_coverage": gallery_coverage,
            "clip_clean_reproduction_audit": clip_audit,
            "full_gallery": True,
            "clean_gallery_for_every_condition": True,
            "all_official_queries_for_every_condition": True,
            "feature_level_corruption_used": False,
            "elapsed_seconds": time.perf_counter() - started,
            "artifacts": _artifact_inventory(
                output_dir,
                {"robustness_manifest.json", "run.log"},
            ),
        }
        final_manifest["payload_sha256"] = formal.canonical_sha256(final_manifest)
        formal.atomic_json_dump(
            output_dir / "robustness_manifest.json", final_manifest
        )
        LOGGER.info(
            "Completed %s/%s robustness matrix: 30/30 image-level conditions.",
            dataset,
            model.variant,
        )
    finally:
        _close_logging()


def main(argv: Sequence[str] | None = None) -> None:
    run(_parse_args(argv))


if __name__ == "__main__":
    main()
