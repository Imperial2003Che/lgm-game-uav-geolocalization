from __future__ import annotations

import torch
from torch.nn import functional as F


def symmetric_contrastive_loss(logits: torch.Tensor) -> torch.Tensor:
    labels = torch.arange(logits.size(0), device=logits.device)
    query_loss = F.cross_entropy(logits, labels)
    ref_loss = F.cross_entropy(logits.t(), labels)
    return 0.5 * (query_loss + ref_loss)


def text_decorrelation_loss(content_text: torch.Tensor, style_text: torch.Tensor) -> torch.Tensor:
    cosine = F.cosine_similarity(content_text, style_text, dim=-1)
    return cosine.abs().mean()
