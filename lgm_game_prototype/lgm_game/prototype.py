from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from typing import Iterable

from .config import LGMGameConfig
from .tokens import MapToken, SemanticAnchor, StylePrompt, VisualToken


@dataclass(frozen=True)
class AttentionEdge:
    query_id: str
    ref_id: str
    score: float


@dataclass(frozen=True)
class Match:
    query_id: str
    ref_id: str
    confidence: float


class LGMGamePrototype:
    """A small, runnable prototype of the proposed LGM-GAME pipeline."""

    def __init__(self, config: LGMGameConfig | None = None) -> None:
        self.config = config or LGMGameConfig()

    def encode_visual_tokens(
        self,
        view: str,
        scene_name: str,
        label_grid: list[str] | None = None,
    ) -> list[VisualToken]:
        """Create deterministic fake visual tokens for a scene.

        Replace this method with a real CNN/FPN/ViT encoder in a full model.
        """
        rng = random.Random(self._seed(f"{view}:{scene_name}"))
        tokens: list[VisualToken] = []
        grid_size = self.config.grid_size
        for row in range(grid_size):
            for col in range(grid_size):
                idx = row * grid_size + col
                label = label_grid[idx] if label_grid and idx < len(label_grid) else ""
                feature = self._make_feature(rng, label)
                tokens.append(
                    VisualToken(
                        token_id=f"{view}_{idx:02d}",
                        view=view,
                        x=col / max(grid_size - 1, 1),
                        y=row / max(grid_size - 1, 1),
                        feature=feature,
                        label_hint=label,
                    )
                )
        return tokens

    def build_semantic_anchors(self, description: str) -> list[SemanticAnchor]:
        """Extract a small set of stable semantic anchors from text."""
        keywords = {
            "road": ("road", 1.0),
            "intersection": ("road_intersection", 1.2),
            "building": ("building_footprint", 1.0),
            "field": ("sports_field", 0.9),
            "water": ("water_boundary", 0.9),
            "parking": ("parking_grid", 0.8),
            "vegetation": ("vegetation_block", 0.7),
        }
        anchors: dict[str, SemanticAnchor] = {}
        lower = description.lower()
        for key, (name, weight) in keywords.items():
            if key in lower:
                anchors[name] = SemanticAnchor(name=name, weight=weight)
        return list(anchors.values())

    def build_style_prompts(self, description: str) -> list[StylePrompt]:
        """Extract nuisance style prompts from text.

        In the full paper idea, these prompts supervise style-invariant content
        features. Here they become a simple penalty against style-only matches.
        """
        keywords = {
            "snow": ("snow_cover", 1.2),
            "winter": ("winter_leafless", 1.0),
            "summer": ("summer_vegetation", 0.8),
            "shadow": ("strong_shadow", 1.0),
            "night": ("low_illumination", 1.1),
            "haze": ("haze_low_contrast", 0.9),
            "rain": ("rain_degradation", 0.9),
            "blur": ("sensor_blur", 0.8),
            "color": ("color_tone_shift", 0.7),
        }
        prompts: dict[str, StylePrompt] = {}
        lower = description.lower()
        for key, (name, weight) in keywords.items():
            if key in lower:
                prompts[name] = StylePrompt(name=name, weight=weight)
        return list(prompts.values())

    def build_map_tokens(self, raw_features: Iterable[dict]) -> list[MapToken]:
        """Convert simplified vector-map features into topology tokens."""
        tokens: list[MapToken] = []
        for idx, item in enumerate(raw_features):
            tokens.append(
                MapToken(
                    token_id=str(item.get("id", f"map_{idx:02d}")),
                    category=str(item.get("category", "unknown")),
                    x=float(item.get("x", 0.5)),
                    y=float(item.get("y", 0.5)),
                    orientation=float(item.get("orientation", 0.0)),
                    confidence=float(item.get("confidence", 1.0)),
                )
            )
        return tokens

    def topk_sparse_attention(
        self,
        query_tokens: list[VisualToken],
        ref_tokens: list[VisualToken],
        anchors: list[SemanticAnchor],
        style_prompts: list[StylePrompt],
        map_tokens: list[MapToken],
    ) -> list[AttentionEdge]:
        """Keep only top-k reference tokens for each query token."""
        edges: list[AttentionEdge] = []
        for query in query_tokens:
            scored = [
                AttentionEdge(
                    query_id=query.token_id,
                    ref_id=ref.token_id,
                    score=self.language_map_geometry_score(
                        query, ref, anchors, style_prompts, map_tokens
                    ),
                )
                for ref in ref_tokens
            ]
            scored.sort(key=lambda edge: edge.score, reverse=True)
            edges.extend(scored[: self.config.top_k])
        return edges

    def language_map_geometry_score(
        self,
        query: VisualToken,
        ref: VisualToken,
        anchors: list[SemanticAnchor],
        style_prompts: list[StylePrompt],
        map_tokens: list[MapToken],
    ) -> float:
        """Simulated attention logit with content reward and style penalty."""
        appearance = self._cosine(query.feature, ref.feature)
        geometry = self._geometry_bias(query, ref)
        semantic = self._semantic_bias(query, ref, anchors)
        map_bias = self._map_bias(query, ref, map_tokens)
        style_penalty = self._style_penalty(query, ref, style_prompts)
        return (
            appearance
            + self.config.geometry_weight * geometry
            + self.config.semantic_weight * semantic
            + self.config.map_weight * map_bias
            - self.config.style_penalty_weight * style_penalty
        )

    def sinkhorn_match(
        self,
        query_tokens: list[VisualToken],
        ref_tokens: list[VisualToken],
        edges: list[AttentionEdge],
    ) -> list[Match]:
        """Run a tiny Sinkhorn-style assignment with a dustbin row/column."""
        q_index = {token.token_id: idx for idx, token in enumerate(query_tokens)}
        r_index = {token.token_id: idx for idx, token in enumerate(ref_tokens)}
        rows = len(query_tokens) + 1
        cols = len(ref_tokens) + 1
        matrix = [[self.config.dustbin_score for _ in range(cols)] for _ in range(rows)]

        for edge in edges:
            i = q_index[edge.query_id]
            j = r_index[edge.ref_id]
            matrix[i][j] = math.exp(edge.score / max(self.config.temperature, 1e-6))

        for _ in range(self.config.sinkhorn_iterations):
            self._normalize_rows(matrix)
            self._normalize_cols(matrix)

        matches: list[Match] = []
        for query in query_tokens:
            i = q_index[query.token_id]
            best_j = max(range(len(ref_tokens)), key=lambda j: matrix[i][j])
            confidence = matrix[i][best_j]
            if confidence > matrix[i][-1]:
                matches.append(Match(query.token_id, ref_tokens[best_j].token_id, confidence))
        return matches

    def greedy_consistency_clique(self, matches: list[Match]) -> list[Match]:
        """Select a self-consistent high-confidence subset.

        This is a placeholder for maximal clique or graph optimization.
        """
        ordered = sorted(matches, key=lambda item: item.confidence, reverse=True)
        chosen: list[Match] = []
        used_refs: set[str] = set()
        for match in ordered:
            if match.confidence < self.config.clique_threshold:
                continue
            if match.ref_id in used_refs:
                continue
            chosen.append(match)
            used_refs.add(match.ref_id)
        return chosen

    @staticmethod
    def _seed(text: str) -> int:
        return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)

    def _make_feature(self, rng: random.Random, label: str) -> tuple[float, ...]:
        base = [rng.uniform(-0.5, 0.5) for _ in range(self.config.feature_dim)]
        if label:
            label_rng = random.Random(self._seed(label))
            base = [value + label_rng.uniform(-0.8, 0.8) for value in base]
        norm = math.sqrt(sum(value * value for value in base)) or 1.0
        return tuple(value / norm for value in base)

    @staticmethod
    def _cosine(a: tuple[float, ...], b: tuple[float, ...]) -> float:
        return sum(x * y for x, y in zip(a, b))

    @staticmethod
    def _geometry_bias(query: VisualToken, ref: VisualToken) -> float:
        distance = math.sqrt((query.x - ref.x) ** 2 + (query.y - ref.y) ** 2)
        return 1.0 - min(distance, 1.0)

    @staticmethod
    def _semantic_bias(
        query: VisualToken,
        ref: VisualToken,
        anchors: list[SemanticAnchor],
    ) -> float:
        if not anchors:
            return 0.0
        score = 0.0
        for anchor in anchors:
            q_hit = anchor.name.split("_")[0] in query.label_hint
            r_hit = anchor.name.split("_")[0] in ref.label_hint
            if q_hit and r_hit:
                score += anchor.weight
        return score / max(len(anchors), 1)

    @staticmethod
    def _style_penalty(
        query: VisualToken,
        ref: VisualToken,
        style_prompts: list[StylePrompt],
    ) -> float:
        if not style_prompts:
            return 0.0
        penalty = 0.0
        for prompt in style_prompts:
            style_key = prompt.name.split("_")[0]
            q_hit = style_key in query.label_hint
            r_hit = style_key in ref.label_hint
            if q_hit != r_hit:
                penalty += 0.35 * prompt.weight
            elif q_hit and r_hit:
                penalty += 0.15 * prompt.weight
        return penalty / max(len(style_prompts), 1)

    @staticmethod
    def _map_bias(
        query: VisualToken,
        ref: VisualToken,
        map_tokens: list[MapToken],
    ) -> float:
        if not map_tokens:
            return 0.0
        midpoint_x = (query.x + ref.x) / 2.0
        midpoint_y = (query.y + ref.y) / 2.0
        best = 0.0
        for token in map_tokens:
            distance = math.sqrt((midpoint_x - token.x) ** 2 + (midpoint_y - token.y) ** 2)
            spatial = 1.0 - min(distance, 1.0)
            best = max(best, spatial * token.confidence)
        return best

    @staticmethod
    def _normalize_rows(matrix: list[list[float]]) -> None:
        for row in matrix:
            total = sum(row) or 1.0
            for idx in range(len(row)):
                row[idx] /= total

    @staticmethod
    def _normalize_cols(matrix: list[list[float]]) -> None:
        if not matrix:
            return
        cols = len(matrix[0])
        for col in range(cols):
            total = sum(row[col] for row in matrix) or 1.0
            for row in matrix:
                row[col] /= total
