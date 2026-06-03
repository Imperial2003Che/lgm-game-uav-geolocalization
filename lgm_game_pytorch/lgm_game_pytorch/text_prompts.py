from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import torch


PAD_TOKEN = "<pad>"
UNK_TOKEN = "<unk>"

BASE_CONTENT_TOKENS = [
    "campus",
    "urban",
    "building",
    "road",
    "vegetation",
    "parking",
    "open_area",
    "sports_field",
    "water",
    "intersection",
    "stable_layout",
    "geo_place",
]

BASE_STYLE_TOKENS = [
    "uav",
    "satellite",
    "street",
    "nadir",
    "oblique",
    "viewpoint_gap",
    "sensor_gap",
    "height_150",
    "height_200",
    "height_250",
    "height_300",
    "height_unknown",
    "season_unknown",
    "illumination_unknown",
]


@dataclass(frozen=True)
class EncodedPrompt:
    ids: torch.Tensor
    mask: torch.Tensor


class PromptVocabulary:
    """Small word-level prompt vocabulary for metadata-derived text tokens."""

    def __init__(self, tokens: list[str] | None = None) -> None:
        ordered = [PAD_TOKEN, UNK_TOKEN]
        for token in tokens or []:
            if token not in ordered:
                ordered.append(token)
        self.tokens = ordered
        self.token_to_id = {token: idx for idx, token in enumerate(self.tokens)}

    @classmethod
    def default(cls) -> "PromptVocabulary":
        return cls(BASE_CONTENT_TOKENS + BASE_STYLE_TOKENS)

    @classmethod
    def from_tokens(cls, tokens: list[str]) -> "PromptVocabulary":
        return cls(tokens)

    def add_tokens(self, tokens: list[str]) -> None:
        for token in tokens:
            if token not in self.token_to_id:
                self.token_to_id[token] = len(self.tokens)
                self.tokens.append(token)

    def encode(self, tokens: list[str], max_len: int) -> EncodedPrompt:
        token_ids = [self.token_to_id.get(token, self.token_to_id[UNK_TOKEN]) for token in tokens[:max_len]]
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


def content_tokens_for(class_id: str, use_class_token: bool = False) -> list[str]:
    tokens = ["campus", "urban", "building", "road", "vegetation", "stable_layout", "geo_place"]
    if use_class_token:
        tokens.append(f"place_{class_id}")
    return tokens


def style_tokens_for(dataset_name: str, query_path: Path, ref_path: Path) -> list[str]:
    tokens = ["uav", "satellite", "viewpoint_gap", "sensor_gap"]
    altitude = _altitude_from_path(query_path)
    tokens.append(f"height_{altitude}" if altitude else "height_unknown")

    if dataset_name.lower() == "sues200":
        tokens.extend(["oblique", "nadir"])
    elif dataset_name.lower() == "university1652":
        tokens.extend(["oblique", "nadir", "season_unknown"])
    else:
        tokens.extend(["oblique", "nadir"])
    return tokens


def class_tokens_for(class_ids: list[str]) -> list[str]:
    return [f"place_{class_id}" for class_id in class_ids]


def _altitude_from_path(path: Path) -> str | None:
    for part in reversed(path.parts):
        if part in {"150", "200", "250", "300"}:
            return part
    return None
