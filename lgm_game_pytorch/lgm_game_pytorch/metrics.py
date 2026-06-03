from __future__ import annotations

import torch


@torch.no_grad()
def recall_at_k(logits: torch.Tensor, query_labels: torch.Tensor, ref_labels: torch.Tensor, ks: tuple[int, ...] = (1, 5)) -> dict[str, float]:
    ranked = logits.argsort(dim=1, descending=True)
    matches = ref_labels[ranked] == query_labels.unsqueeze(1)
    results: dict[str, float] = {}
    for k in ks:
        k = min(k, ranked.size(1))
        results[f"r@{k}"] = matches[:, :k].any(dim=1).float().mean().item()
    return results


class AverageMeter:
    def __init__(self) -> None:
        self.total = 0.0
        self.count = 0

    def update(self, value: float, n: int = 1) -> None:
        self.total += value * n
        self.count += n

    @property
    def avg(self) -> float:
        return self.total / max(self.count, 1)
