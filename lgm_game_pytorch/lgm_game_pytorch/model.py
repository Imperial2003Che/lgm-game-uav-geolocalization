from __future__ import annotations

import math

import torch
from torch import nn
import torch.nn.functional as F
from torchvision import models


class VisualEncoder(nn.Module):
    """ResNet visual encoder for UAV and satellite images."""

    def __init__(self, backbone: str = "resnet18", embed_dim: int = 256, pretrained: bool = False) -> None:
        super().__init__()
        if not hasattr(models, backbone):
            raise ValueError(f"Unknown torchvision backbone: {backbone}")
        weights = "DEFAULT" if pretrained else None
        net = getattr(models, backbone)(weights=weights)
        in_features = net.fc.in_features
        net.fc = nn.Identity()
        self.backbone = net
        self.proj = nn.Sequential(
            nn.Linear(in_features, embed_dim),
            nn.LayerNorm(embed_dim),
            nn.GELU(),
            nn.Linear(embed_dim, embed_dim),
        )

    def forward(self, images: torch.Tensor) -> torch.Tensor:
        features = self.backbone(images)
        return F.normalize(self.proj(features), dim=-1)


class TextEncoder(nn.Module):
    """A lightweight token encoder used separately for content and style prompts."""

    def __init__(self, vocab_size: int, embed_dim: int = 256, token_dim: int = 128, padding_idx: int = 0) -> None:
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, token_dim, padding_idx=padding_idx)
        self.proj = nn.Sequential(
            nn.LayerNorm(token_dim),
            nn.Linear(token_dim, embed_dim),
            nn.GELU(),
            nn.Linear(embed_dim, embed_dim),
        )

    def forward(self, token_ids: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        token_embeddings = self.embedding(token_ids)
        mask = mask.unsqueeze(-1)
        pooled = (token_embeddings * mask).sum(dim=1) / mask.sum(dim=1).clamp_min(1.0)
        return F.normalize(self.proj(pooled), dim=-1)


class MatchingHead(nn.Module):
    """Combines image content with text guidance and suppresses style leakage."""

    def __init__(self, embed_dim: int = 256, content_weight: float = 0.25, style_suppression: float = 0.20) -> None:
        super().__init__()
        self.content_weight = content_weight
        self.style_suppression = style_suppression
        self.query_gate = nn.Sequential(nn.Linear(embed_dim * 3, embed_dim), nn.GELU(), nn.Linear(embed_dim, embed_dim))
        self.ref_gate = nn.Sequential(nn.Linear(embed_dim * 3, embed_dim), nn.GELU(), nn.Linear(embed_dim, embed_dim))
        self.logit_scale = nn.Parameter(torch.tensor(math.log(1 / 0.07)))

    def forward(
        self,
        query_visual: torch.Tensor,
        ref_visual: torch.Tensor,
        content_text: torch.Tensor,
        style_text: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        query_clean = self._suppress_style(query_visual, style_text)
        ref_clean = self._suppress_style(ref_visual, style_text)
        query_delta = self.query_gate(torch.cat([query_clean, content_text, style_text], dim=-1))
        ref_delta = self.ref_gate(torch.cat([ref_clean, content_text, style_text], dim=-1))
        query_embed = F.normalize(query_clean + self.content_weight * content_text + query_delta, dim=-1)
        ref_embed = F.normalize(ref_clean + self.content_weight * content_text + ref_delta, dim=-1)
        scale = self.logit_scale.exp().clamp(max=100)
        logits = scale * query_embed @ ref_embed.t()
        return {
            "logits": logits,
            "query_embed": query_embed,
            "ref_embed": ref_embed,
            "logit_scale": scale.detach(),
        }

    def _suppress_style(self, visual: torch.Tensor, style: torch.Tensor) -> torch.Tensor:
        style = F.normalize(style, dim=-1)
        projection = (visual * style).sum(dim=-1, keepdim=True) * style
        return F.normalize(visual - self.style_suppression * projection, dim=-1)


class LGMGameModel(nn.Module):
    """Content/style text encoders + visual encoder + matching head."""

    def __init__(
        self,
        vocab_size: int,
        backbone: str = "resnet18",
        embed_dim: int = 256,
        token_dim: int = 128,
        pretrained: bool = False,
        content_weight: float = 0.25,
        style_suppression: float = 0.20,
    ) -> None:
        super().__init__()
        self.visual_encoder = VisualEncoder(backbone=backbone, embed_dim=embed_dim, pretrained=pretrained)
        self.content_encoder = TextEncoder(vocab_size=vocab_size, embed_dim=embed_dim, token_dim=token_dim)
        self.style_encoder = TextEncoder(vocab_size=vocab_size, embed_dim=embed_dim, token_dim=token_dim)
        self.matching_head = MatchingHead(
            embed_dim=embed_dim,
            content_weight=content_weight,
            style_suppression=style_suppression,
        )

    def forward(
        self,
        query_image: torch.Tensor,
        ref_image: torch.Tensor,
        content_ids: torch.Tensor,
        content_mask: torch.Tensor,
        style_ids: torch.Tensor,
        style_mask: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        query_visual = self.visual_encoder(query_image)
        ref_visual = self.visual_encoder(ref_image)
        content_text = self.content_encoder(content_ids, content_mask)
        style_text = self.style_encoder(style_ids, style_mask)
        matched = self.matching_head(query_visual, ref_visual, content_text, style_text)
        matched.update(
            {
                "query_visual": query_visual,
                "ref_visual": ref_visual,
                "content_text": content_text,
                "style_text": style_text,
            }
        )
        return matched
