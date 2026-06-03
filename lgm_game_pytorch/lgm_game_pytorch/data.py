from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image
import torch
from torch.utils.data import Dataset
from torchvision import transforms

from .text_prompts import PromptProvider, PromptVocabulary, class_tokens_for


IMG_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


@dataclass(frozen=True)
class PairRecord:
    class_id: str
    label: int
    query_path: Path
    ref_path: Path
    content_text: str
    style_text: str
    content_tokens: list[str]
    style_tokens: list[str]
    prompt_backend: str


class CrossViewPairDataset(Dataset):
    """Pairs UAV/drone query images with satellite reference images."""

    def __init__(
        self,
        root: str | Path,
        dataset_name: str,
        split: str = "train",
        image_size: int = 224,
        max_classes: int | None = None,
        samples_per_class: int = 1,
        seed: int = 7,
        vocab: PromptVocabulary | None = None,
        use_class_token: bool = False,
        prompt_backend: str = "vlgeo",
        prompt_cache: str | Path | None = None,
        caption_model: str = "Salesforce/blip-image-captioning-base",
        clip_model: str = "openai/clip-vit-base-patch32",
        llava_model: str = "llava",
        llava_endpoint: str = "http://localhost:11434/api/generate",
        prompt_device: str = "auto",
        allow_prompt_fallback: bool = False,
        freeze_vocab: bool = False,
        content_max_len: int = 10,
        style_max_len: int = 10,
    ) -> None:
        self.root = Path(root).expanduser()
        self.dataset_name = _normalize_dataset_name(dataset_name)
        self.split = split
        self.image_size = image_size
        self.content_max_len = content_max_len
        self.style_max_len = style_max_len
        self.use_class_token = use_class_token
        prompt_provider = PromptProvider(
            backend=prompt_backend,
            cache_path=prompt_cache,
            caption_model=caption_model,
            clip_model=clip_model,
            llava_model=llava_model,
            llava_endpoint=llava_endpoint,
            device=prompt_device,
            allow_fallback=allow_prompt_fallback,
        )
        self.records = build_pair_records(
            root=self.root,
            dataset_name=self.dataset_name,
            split=split,
            max_classes=max_classes,
            samples_per_class=samples_per_class,
            seed=seed,
            use_class_token=use_class_token,
            prompt_provider=prompt_provider,
        )
        if not self.records:
            raise RuntimeError(f"No image pairs found for {self.dataset_name} at {self.root} split={split}.")

        self.vocab = vocab or PromptVocabulary.default()
        if not freeze_vocab:
            for record in self.records:
                self.vocab.add_tokens(record.content_tokens + record.style_tokens)
        if use_class_token and not freeze_vocab:
            self.vocab.add_tokens(class_tokens_for(sorted({record.class_id for record in self.records})))

        self.transform = build_transform(image_size=image_size, train=split == "train")

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> dict:
        record = self.records[index]
        query_image = self.transform(_load_rgb(record.query_path))
        ref_image = self.transform(_load_rgb(record.ref_path))
        content = self.vocab.encode(record.content_tokens, self.content_max_len)
        style = self.vocab.encode(record.style_tokens, self.style_max_len)
        return {
            "query_image": query_image,
            "ref_image": ref_image,
            "label": torch.tensor(record.label, dtype=torch.long),
            "class_id": record.class_id,
            "query_path": str(record.query_path),
            "ref_path": str(record.ref_path),
            "content_text": record.content_text,
            "style_text": record.style_text,
            "prompt_backend": record.prompt_backend,
            "content_ids": content.ids,
            "content_mask": content.mask,
            "style_ids": style.ids,
            "style_mask": style.mask,
        }


def build_transform(image_size: int, train: bool) -> transforms.Compose:
    if train:
        return transforms.Compose(
            [
                transforms.Resize((image_size, image_size)),
                transforms.RandomHorizontalFlip(p=0.5),
                transforms.ColorJitter(brightness=0.08, contrast=0.08, saturation=0.05),
                transforms.ToTensor(),
                transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
            ]
        )
    return transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ]
    )


def build_pair_records(
    root: Path,
    dataset_name: str,
    split: str,
    max_classes: int | None,
    samples_per_class: int,
    seed: int,
    use_class_token: bool,
    prompt_provider: PromptProvider,
) -> list[PairRecord]:
    dataset_name = _normalize_dataset_name(dataset_name)
    if dataset_name == "sues200":
        class_to_paths = _scan_sues200(root, split=split, seed=seed)
    elif dataset_name == "university1652":
        class_to_paths = _scan_university1652(root, split=split)
    else:
        raise ValueError(f"Unsupported dataset: {dataset_name}")

    class_ids = sorted(class_to_paths)
    if max_classes is not None:
        class_ids = class_ids[:max_classes]

    rng = random.Random(seed)
    records: list[PairRecord] = []
    for label, class_id in enumerate(class_ids):
        query_paths, ref_paths = class_to_paths[class_id]
        if not query_paths or not ref_paths:
            continue
        query_paths = sorted(query_paths)
        ref_paths = sorted(ref_paths)
        if samples_per_class > 0:
            chosen_queries = query_paths[:]
            rng.shuffle(chosen_queries)
            chosen_queries = chosen_queries[: min(samples_per_class, len(chosen_queries))]
        else:
            chosen_queries = query_paths
        for idx, query_path in enumerate(chosen_queries):
            ref_path = ref_paths[idx % len(ref_paths)]
            prompt = prompt_provider.describe_pair(
                dataset_name=dataset_name,
                class_id=class_id,
                query_path=query_path,
                ref_path=ref_path,
                use_class_token=use_class_token,
            )
            records.append(
                PairRecord(
                    class_id=class_id,
                    label=label,
                    query_path=query_path,
                    ref_path=ref_path,
                    content_text=prompt.content_text,
                    style_text=prompt.style_text,
                    content_tokens=prompt.content_tokens,
                    style_tokens=prompt.style_tokens,
                    prompt_backend=prompt.backend,
                )
            )
    return records


def summarize_records(records: list[PairRecord]) -> dict:
    class_ids = sorted({record.class_id for record in records})
    return {
        "num_pairs": len(records),
        "num_classes": len(class_ids),
        "first_classes": class_ids[:8],
        "first_query": str(records[0].query_path) if records else "",
        "first_reference": str(records[0].ref_path) if records else "",
        "first_content_text": records[0].content_text if records else "",
        "first_style_text": records[0].style_text if records else "",
        "prompt_backends": sorted({record.prompt_backend for record in records}),
    }


def _scan_sues200(root: Path, split: str, seed: int, train_ratio: float = 0.8) -> dict[str, tuple[list[Path], list[Path]]]:
    drone_root = root / "drone_view_512"
    satellite_root = root / "satellite-view"
    if not drone_root.exists() or not satellite_root.exists():
        raise FileNotFoundError(f"SUES-200 expects drone_view_512 and satellite-view under {root}.")

    ids = sorted({p.name for p in drone_root.iterdir() if p.is_dir()} & {p.name for p in satellite_root.iterdir() if p.is_dir()})
    shuffled = ids[:]
    random.Random(seed).shuffle(shuffled)
    split_at = int(len(shuffled) * train_ratio)
    selected = set(shuffled[:split_at] if split == "train" else shuffled[split_at:])

    class_to_paths: dict[str, tuple[list[Path], list[Path]]] = {}
    for class_id in ids:
        if class_id not in selected:
            continue
        query_paths = list(_image_files(drone_root / class_id))
        ref_paths = list(_image_files(satellite_root / class_id))
        if query_paths and ref_paths:
            class_to_paths[class_id] = (query_paths, ref_paths)
    return class_to_paths


def _scan_university1652(root: Path, split: str) -> dict[str, tuple[list[Path], list[Path]]]:
    if split == "train":
        query_root = root / "train" / "drone"
        ref_root = root / "train" / "satellite"
    else:
        query_root = root / "test" / "query_drone"
        ref_root = root / "test" / "gallery_satellite"
        if not query_root.exists():
            query_root = root / "test" / "gallery_drone"
        if not ref_root.exists():
            ref_root = root / "test" / "query_satellite"

    if not query_root.exists() or not ref_root.exists():
        raise FileNotFoundError(f"University-1652 split={split} expects {query_root} and {ref_root}.")

    class_ids = sorted({p.name for p in query_root.iterdir() if p.is_dir()} & {p.name for p in ref_root.iterdir() if p.is_dir()})
    class_to_paths: dict[str, tuple[list[Path], list[Path]]] = {}
    for class_id in class_ids:
        query_paths = list(_image_files(query_root / class_id))
        ref_paths = list(_image_files(ref_root / class_id))
        if query_paths and ref_paths:
            class_to_paths[class_id] = (query_paths, ref_paths)
    return class_to_paths


def _image_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMG_EXTENSIONS:
            yield path


def _load_rgb(path: Path) -> Image.Image:
    with Image.open(path) as image:
        return image.convert("RGB")


def _normalize_dataset_name(name: str) -> str:
    normalized = name.lower().replace("-", "").replace("_", "")
    if normalized in {"sues200", "sues"}:
        return "sues200"
    if normalized in {"university1652", "university"}:
        return "university1652"
    return normalized
