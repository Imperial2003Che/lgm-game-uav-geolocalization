from __future__ import annotations

import base64
import hashlib
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image
import torch


PAD_TOKEN = "<pad>"
UNK_TOKEN = "<unk>"

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}

CONTENT_CANDIDATES = [
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
]

STYLE_CANDIDATES = [
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
]

BASE_TOKENS = [
    token for token, _ in CONTENT_CANDIDATES + STYLE_CANDIDATES
] + [
    "uav",
    "drone",
    "satellite",
    "nadir",
    "oblique",
    "height_150",
    "height_200",
    "height_250",
    "height_300",
    "height_unknown",
    "caption",
    "vlgeo",
    "blip",
    "clip",
    "llava",
    "geo_place",
]


@dataclass(frozen=True)
class EncodedPrompt:
    ids: torch.Tensor
    mask: torch.Tensor


@dataclass(frozen=True)
class PromptDescription:
    content_text: str
    style_text: str
    content_tokens: list[str]
    style_tokens: list[str]
    backend: str
    raw: dict[str, Any] = field(default_factory=dict)


class PromptVocabulary:
    """Word-level vocabulary built from VLM-generated content/style prompts."""

    def __init__(self, tokens: list[str] | None = None) -> None:
        ordered = [PAD_TOKEN, UNK_TOKEN]
        for token in tokens or []:
            clean = normalize_token(token)
            if clean and clean not in ordered:
                ordered.append(clean)
        self.tokens = ordered
        self.token_to_id = {token: idx for idx, token in enumerate(self.tokens)}

    @classmethod
    def default(cls) -> "PromptVocabulary":
        return cls(BASE_TOKENS)

    @classmethod
    def from_tokens(cls, tokens: list[str]) -> "PromptVocabulary":
        vocab = cls([])
        vocab.tokens = list(tokens)
        vocab.token_to_id = {token: idx for idx, token in enumerate(vocab.tokens)}
        return vocab

    def add_tokens(self, tokens: list[str]) -> None:
        for token in tokens:
            clean = normalize_token(token)
            if clean and clean not in self.token_to_id:
                self.token_to_id[clean] = len(self.tokens)
                self.tokens.append(clean)

    def encode(self, tokens: list[str], max_len: int) -> EncodedPrompt:
        cleaned = [normalize_token(token) for token in tokens]
        cleaned = [token for token in cleaned if token]
        token_ids = [self.token_to_id.get(token, self.token_to_id[UNK_TOKEN]) for token in cleaned[:max_len]]
        mask = [1] * len(token_ids)
        while len(token_ids) < max_len:
            token_ids.append(self.token_to_id[PAD_TOKEN])
            mask.append(0)
        return EncodedPrompt(
            ids=torch.tensor(token_ids, dtype=torch.long),
            mask=torch.tensor(mask, dtype=torch.float32),
        )

    def __len__(self) -> int:
        return len(self.tokens)


class PromptCache:
    """JSONL cache for generated VLM prompts."""

    def __init__(self, path: str | Path | None) -> None:
        self.path = Path(path).expanduser() if path else None
        self.records: dict[str, dict[str, Any]] = {}
        if self.path and self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                item = json.loads(line)
                self.records[item["key"]] = item

    def get(self, key: str) -> dict[str, Any] | None:
        return self.records.get(key)

    def find_pair(self, dataset_name: str, class_id: str, query_path: Path, ref_path: Path) -> dict[str, Any] | None:
        query = str(query_path)
        ref = str(ref_path)
        for item in self.records.values():
            if (
                item.get("dataset") == dataset_name
                and item.get("class_id") == class_id
                and item.get("query_path") == query
                and item.get("ref_path") == ref
            ):
                return item
        return None

    def set(self, key: str, item: dict[str, Any]) -> None:
        self.records[key] = item
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")


class PromptProvider:
    """Generate content/style text with BLIP, CLIP, LLaVA, or cached VLGeo-style prompts."""

    def __init__(
        self,
        backend: str = "vlgeo",
        cache_path: str | Path | None = None,
        caption_model: str = "Salesforce/blip-image-captioning-base",
        clip_model: str = "openai/clip-vit-base-patch32",
        llava_model: str = "llava",
        llava_endpoint: str = "http://localhost:11434/api/generate",
        device: str = "auto",
        allow_fallback: bool = False,
    ) -> None:
        self.backend = normalize_backend(backend)
        self.cache = PromptCache(cache_path)
        self.caption_model_name = caption_model
        self.clip_model_name = clip_model
        self.llava_model = llava_model
        self.llava_endpoint = llava_endpoint
        self.device = _choose_device(device)
        self.allow_fallback = allow_fallback
        self._blip_processor = None
        self._blip_model = None
        self._clip_processor = None
        self._clip_model = None

    def describe_pair(
        self,
        dataset_name: str,
        class_id: str,
        query_path: Path,
        ref_path: Path,
        use_class_token: bool = False,
    ) -> PromptDescription:
        key = cache_key(dataset_name, class_id, query_path, ref_path, self.backend)
        cached = self.cache.get(key)
        if cached is None and self.backend == "cache":
            cached = self.cache.find_pair(dataset_name, class_id, query_path, ref_path)
        if cached is not None:
            return prompt_from_cache(cached)

        if self.backend == "cache":
            raise RuntimeError(f"Prompt cache miss for {query_path} <-> {ref_path}.")

        try:
            if self.backend == "metadata":
                prompt = metadata_prompt(dataset_name, class_id, query_path, ref_path, use_class_token)
            elif self.backend == "clip":
                prompt = self._clip_prompt(dataset_name, class_id, query_path, ref_path, use_class_token)
            elif self.backend == "blip":
                prompt = self._blip_prompt(dataset_name, class_id, query_path, ref_path, use_class_token)
            elif self.backend in {"blip_clip", "vlgeo"}:
                prompt = self._vlgeo_prompt(dataset_name, class_id, query_path, ref_path, use_class_token)
            elif self.backend == "llava":
                prompt = self._llava_prompt(dataset_name, class_id, query_path, ref_path, use_class_token)
            else:
                raise ValueError(f"Unsupported prompt backend: {self.backend}")
        except Exception as exc:
            if not self.allow_fallback:
                raise
            prompt = metadata_prompt(dataset_name, class_id, query_path, ref_path, use_class_token)
            prompt = PromptDescription(
                content_text=prompt.content_text,
                style_text=prompt.style_text,
                content_tokens=prompt.content_tokens,
                style_tokens=prompt.style_tokens,
                backend=f"metadata_fallback_after_{self.backend}",
                raw={"error": f"{type(exc).__name__}: {exc}"},
            )

        self.cache.set(key, cache_payload(key, dataset_name, class_id, query_path, ref_path, prompt))
        return prompt

    def _vlgeo_prompt(
        self,
        dataset_name: str,
        class_id: str,
        query_path: Path,
        ref_path: Path,
        use_class_token: bool,
    ) -> PromptDescription:
        query_caption = self._caption(query_path)
        ref_caption = self._caption(ref_path)
        content_labels = self._clip_labels([query_path, ref_path], CONTENT_CANDIDATES, top_k=5)
        style_labels = self._clip_labels([query_path, ref_path], STYLE_CANDIDATES, top_k=5)
        altitude = altitude_from_path(query_path)

        content_text = (
            f"VLGeo content description for place {class_id}. "
            f"UAV caption: {query_caption}. Satellite caption: {ref_caption}. "
            f"Stable geo-localization landmarks: {', '.join(label for label, _ in content_labels)}."
        )
        style_text = (
            f"VLGeo style description for place {class_id}. "
            f"Cross-view nuisance factors: {', '.join(label for label, _ in style_labels)}. "
            f"UAV altitude cue: {altitude or 'unknown'}."
        )
        return PromptDescription(
            content_text=content_text,
            style_text=style_text,
            content_tokens=tokens_from_text(content_text, extra=[label for label, _ in content_labels] + class_token(class_id, use_class_token)),
            style_tokens=tokens_from_text(style_text, extra=[label for label, _ in style_labels] + altitude_tokens(query_path)),
            backend=self.backend,
            raw={
                "query_caption": query_caption,
                "ref_caption": ref_caption,
                "content_labels": content_labels,
                "style_labels": style_labels,
            },
        )

    def _blip_prompt(
        self,
        dataset_name: str,
        class_id: str,
        query_path: Path,
        ref_path: Path,
        use_class_token: bool,
    ) -> PromptDescription:
        query_caption = self._caption(query_path)
        ref_caption = self._caption(ref_path)
        content_text = f"BLIP content description for place {class_id}. UAV caption: {query_caption}. Satellite caption: {ref_caption}."
        style_text = (
            f"BLIP style description for place {class_id}. "
            f"The pair contains UAV and satellite viewpoint differences, sensor style differences, and altitude {altitude_from_path(query_path) or 'unknown'}."
        )
        return PromptDescription(
            content_text=content_text,
            style_text=style_text,
            content_tokens=tokens_from_text(content_text, extra=class_token(class_id, use_class_token)),
            style_tokens=tokens_from_text(style_text, extra=altitude_tokens(query_path)),
            backend="blip",
            raw={"query_caption": query_caption, "ref_caption": ref_caption},
        )

    def _clip_prompt(
        self,
        dataset_name: str,
        class_id: str,
        query_path: Path,
        ref_path: Path,
        use_class_token: bool,
    ) -> PromptDescription:
        content_labels = self._clip_labels([query_path, ref_path], CONTENT_CANDIDATES, top_k=6)
        style_labels = self._clip_labels([query_path, ref_path], STYLE_CANDIDATES, top_k=6)
        content_text = f"CLIP content labels for place {class_id}: {', '.join(label for label, _ in content_labels)}."
        style_text = f"CLIP style labels for place {class_id}: {', '.join(label for label, _ in style_labels)}."
        return PromptDescription(
            content_text=content_text,
            style_text=style_text,
            content_tokens=tokens_from_text(content_text, extra=[label for label, _ in content_labels] + class_token(class_id, use_class_token)),
            style_tokens=tokens_from_text(style_text, extra=[label for label, _ in style_labels] + altitude_tokens(query_path)),
            backend="clip",
            raw={"content_labels": content_labels, "style_labels": style_labels},
        )

    def _llava_prompt(
        self,
        dataset_name: str,
        class_id: str,
        query_path: Path,
        ref_path: Path,
        use_class_token: bool,
    ) -> PromptDescription:
        query_text = self._ollama_llava(query_path, "Describe stable geo-localization content and nuisance style factors in this UAV or satellite image.")
        ref_text = self._ollama_llava(ref_path, "Describe stable geo-localization content and nuisance style factors in this satellite or UAV image.")
        content_text = f"LLaVA content description for place {class_id}. UAV image: {query_text}. Satellite image: {ref_text}."
        style_text = (
            f"LLaVA style description for place {class_id}. Extract viewpoint, altitude, illumination, season, weather, and sensor-style differences. "
            f"UAV image: {query_text}. Satellite image: {ref_text}. Altitude cue: {altitude_from_path(query_path) or 'unknown'}."
        )
        return PromptDescription(
            content_text=content_text,
            style_text=style_text,
            content_tokens=tokens_from_text(content_text, extra=class_token(class_id, use_class_token)),
            style_tokens=tokens_from_text(style_text, extra=altitude_tokens(query_path)),
            backend="llava",
            raw={"query_llava": query_text, "ref_llava": ref_text},
        )

    def _caption(self, path: Path) -> str:
        self._ensure_blip()
        image = load_rgb(path)
        inputs = self._blip_processor(image, return_tensors="pt").to(self.device)
        with torch.no_grad():
            output = self._blip_model.generate(**inputs, max_new_tokens=40)
        return self._blip_processor.decode(output[0], skip_special_tokens=True)

    def _clip_labels(
        self,
        image_paths: list[Path],
        candidates: list[tuple[str, str]],
        top_k: int,
    ) -> list[tuple[str, float]]:
        self._ensure_clip()
        texts = [text for _, text in candidates]
        scores = torch.zeros(len(candidates), dtype=torch.float32)
        for path in image_paths:
            image = load_rgb(path)
            inputs = self._clip_processor(text=texts, images=image, return_tensors="pt", padding=True).to(self.device)
            with torch.no_grad():
                logits = self._clip_model(**inputs).logits_per_image[0].float().cpu()
            scores += logits.softmax(dim=0)
        scores /= max(len(image_paths), 1)
        top = scores.argsort(descending=True)[:top_k]
        return [(candidates[idx][0], float(scores[idx])) for idx in top.tolist()]

    def _ensure_blip(self) -> None:
        if self._blip_model is not None:
            return
        from transformers import BlipForConditionalGeneration, BlipProcessor

        self._blip_processor = BlipProcessor.from_pretrained(self.caption_model_name)
        self._blip_model = BlipForConditionalGeneration.from_pretrained(self.caption_model_name).to(self.device)
        self._blip_model.eval()

    def _ensure_clip(self) -> None:
        if self._clip_model is not None:
            return
        from transformers import CLIPModel, CLIPProcessor

        self._clip_processor = CLIPProcessor.from_pretrained(self.clip_model_name)
        self._clip_model = CLIPModel.from_pretrained(self.clip_model_name).to(self.device)
        self._clip_model.eval()

    def _ollama_llava(self, image_path: Path, prompt: str) -> str:
        image_b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
        payload = {
            "model": self.llava_model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
        }
        request = urllib.request.Request(
            self.llava_endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Cannot reach local LLaVA endpoint {self.llava_endpoint}: {exc}") from exc
        return str(data.get("response", "")).strip()


def metadata_prompt(
    dataset_name: str,
    class_id: str,
    query_path: Path,
    ref_path: Path,
    use_class_token: bool = False,
) -> PromptDescription:
    altitude = altitude_from_path(query_path)
    content_text = (
        f"Metadata content description for place {class_id}: campus buildings, roads, vegetation, parking areas, and stable spatial layout."
    )
    style_text = (
        f"Metadata style description for place {class_id}: UAV to satellite viewpoint gap, sensor gap, oblique and nadir views, "
        f"altitude {altitude or 'unknown'}, unknown season and illumination."
    )
    content_tokens = tokens_from_text(content_text, extra=["campus", "building", "road", "vegetation", "stable_layout"] + class_token(class_id, use_class_token))
    style_tokens = tokens_from_text(style_text, extra=["uav_oblique", "satellite_nadir", "viewpoint_gap", "sensor_gap"] + altitude_tokens(query_path))
    return PromptDescription(
        content_text=content_text,
        style_text=style_text,
        content_tokens=content_tokens,
        style_tokens=style_tokens,
        backend="metadata",
        raw={"dataset": dataset_name, "query_path": str(query_path), "ref_path": str(ref_path)},
    )


def prompt_from_cache(item: dict[str, Any]) -> PromptDescription:
    return PromptDescription(
        content_text=str(item["content_text"]),
        style_text=str(item["style_text"]),
        content_tokens=list(item["content_tokens"]),
        style_tokens=list(item["style_tokens"]),
        backend=str(item.get("backend", "cache")),
        raw=dict(item.get("raw", {})),
    )


def cache_payload(
    key: str,
    dataset_name: str,
    class_id: str,
    query_path: Path,
    ref_path: Path,
    prompt: PromptDescription,
) -> dict[str, Any]:
    return {
        "key": key,
        "dataset": dataset_name,
        "class_id": class_id,
        "query_path": str(query_path),
        "ref_path": str(ref_path),
        "backend": prompt.backend,
        "content_text": prompt.content_text,
        "style_text": prompt.style_text,
        "content_tokens": prompt.content_tokens,
        "style_tokens": prompt.style_tokens,
        "raw": prompt.raw,
    }


def cache_key(dataset_name: str, class_id: str, query_path: Path, ref_path: Path, backend: str) -> str:
    text = f"{backend}|{dataset_name}|{class_id}|{query_path.resolve()}|{ref_path.resolve()}"
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def tokens_from_text(text: str, extra: list[str] | None = None, max_tokens: int = 64) -> list[str]:
    tokens = [normalize_token(token) for token in re.findall(r"[A-Za-z0-9_]+", text.lower())]
    tokens = [token for token in tokens if token and token not in STOPWORDS and len(token) > 1]
    for token in extra or []:
        clean = normalize_token(token)
        if clean:
            tokens.append(clean)

    seen: set[str] = set()
    unique: list[str] = []
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        unique.append(token)
        if len(unique) >= max_tokens:
            break
    return unique


def class_token(class_id: str, enabled: bool) -> list[str]:
    return [f"place_{class_id}"] if enabled else []


def class_tokens_for(class_ids: list[str]) -> list[str]:
    return [f"place_{class_id}" for class_id in class_ids]


def altitude_tokens(path: Path) -> list[str]:
    altitude = altitude_from_path(path)
    return [f"height_{altitude}" if altitude else "height_unknown"]


def altitude_from_path(path: Path) -> str | None:
    for part in reversed(path.parts):
        if part in {"150", "200", "250", "300"}:
            return part
    return None


def load_rgb(path: Path) -> Image.Image:
    with Image.open(path) as image:
        return image.convert("RGB")


def normalize_backend(backend: str) -> str:
    normalized = backend.lower().replace("-", "_")
    aliases = {
        "vlgeo_blip_clip": "vlgeo",
        "vlgeo_style": "vlgeo",
        "blipclip": "blip_clip",
        "cache_only": "cache",
    }
    return aliases.get(normalized, normalized)


def normalize_token(token: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", token.strip().lower()).strip("_")


def _choose_device(requested: str) -> torch.device:
    if requested != "auto":
        return torch.device(requested)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")
