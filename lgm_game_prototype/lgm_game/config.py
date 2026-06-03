from dataclasses import dataclass


@dataclass(frozen=True)
class LGMGameConfig:
    """Weights for the prototype scoring function."""

    feature_dim: int = 8
    grid_size: int = 4
    top_k: int = 3
    sinkhorn_iterations: int = 25
    dustbin_score: float = 0.15
    temperature: float = 0.8
    geometry_weight: float = 0.35
    semantic_weight: float = 0.25
    map_weight: float = 0.25
    clique_threshold: float = 0.48

