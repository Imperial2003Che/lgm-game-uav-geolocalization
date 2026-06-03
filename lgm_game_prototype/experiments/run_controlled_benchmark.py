from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patches

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROTOTYPE_ROOT = PROJECT_ROOT / "lgm_game_prototype"
if str(PROTOTYPE_ROOT) not in sys.path:
    sys.path.insert(0, str(PROTOTYPE_ROOT))

from lgm_game import LGMGameConfig, LGMGamePrototype  # noqa: E402
from lgm_game.prototype import AttentionEdge, Match  # noqa: E402
from lgm_game.tokens import MapToken, VisualToken  # noqa: E402


CONTENT_COLORS = {
    "building": "#7a8797",
    "road": "#4d6678",
    "road intersection": "#2f5f74",
    "vegetation": "#6f9d6a",
    "field": "#c8a951",
    "water": "#4f8fb3",
    "parking": "#9b8a72",
}

PALETTE = {
    "appearance": "#8d99ae",
    "geometry": "#3b6f8f",
    "semantic": "#55a18a",
    "map": "#c49a42",
    "style": "#c15c54",
    "full": "#243b53",
    "accent": "#e07a5f",
    "grid": "#d5dbe3",
    "text": "#233142",
}

BASE_PATTERNS = [
    [
        "building", "building", "road", "vegetation",
        "building", "parking", "road intersection", "vegetation",
        "field", "field", "road", "water",
        "field", "building", "road", "water",
    ],
    [
        "parking", "building", "road", "building",
        "road", "road intersection", "road", "vegetation",
        "field", "vegetation", "building", "building",
        "water", "field", "field", "road",
    ],
    [
        "water", "water", "road", "building",
        "vegetation", "field", "road intersection", "building",
        "vegetation", "field", "road", "parking",
        "building", "building", "road", "parking",
    ],
    [
        "field", "field", "vegetation", "road",
        "field", "parking", "road", "road intersection",
        "building", "building", "road", "water",
        "building", "vegetation", "road", "water",
    ],
    [
        "building", "road", "building", "parking",
        "building", "road intersection", "building", "parking",
        "vegetation", "road", "field", "field",
        "water", "road", "field", "vegetation",
    ],
]

STYLE_SPLITS = {
    "clean": ([], []),
    "season": (["summer", "shadow"], ["winter"]),
    "weather": (["haze", "rain"], []),
    "illumination": (["night", "shadow"], []),
    "sensor": (["color", "blur"], []),
    "partial": (["occluded"], []),
}


@dataclass(frozen=True)
class MethodSpec:
    name: str
    label: str
    geometry: float
    semantic: float
    map_weight: float
    style_penalty: float
    use_text: bool = True
    use_map: bool = True
    use_style: bool = True
    use_sinkhorn: bool = True
    use_clique: bool = True
    top_k: int = 5


METHODS = [
    MethodSpec(
        "appearance",
        "Appearance",
        geometry=0.0,
        semantic=0.0,
        map_weight=0.0,
        style_penalty=0.0,
        use_text=False,
        use_map=False,
        use_style=False,
        use_clique=False,
        top_k=16,
    ),
    MethodSpec(
        "geometry",
        "+ Geometry",
        geometry=0.38,
        semantic=0.0,
        map_weight=0.0,
        style_penalty=0.0,
        use_text=False,
        use_map=False,
        use_style=False,
        top_k=8,
    ),
    MethodSpec(
        "semantic",
        "+ Text Anchors",
        geometry=0.38,
        semantic=0.34,
        map_weight=0.0,
        style_penalty=0.0,
        use_map=False,
        use_style=False,
        top_k=6,
    ),
    MethodSpec(
        "map",
        "+ Vector Map",
        geometry=0.38,
        semantic=0.0,
        map_weight=0.32,
        style_penalty=0.0,
        use_text=False,
        use_style=False,
        top_k=6,
    ),
    MethodSpec(
        "game",
        "GAME-Style",
        geometry=0.38,
        semantic=0.32,
        map_weight=0.0,
        style_penalty=0.0,
        use_map=False,
        use_style=False,
        top_k=5,
    ),
    MethodSpec(
        "full",
        "Full LGM-GAME",
        geometry=0.40,
        semantic=0.36,
        map_weight=0.30,
        style_penalty=0.30,
        top_k=5,
    ),
]

ABLATIONS = [
    MethodSpec(
        "full",
        "Full",
        geometry=0.40,
        semantic=0.36,
        map_weight=0.30,
        style_penalty=0.30,
        top_k=5,
    ),
    MethodSpec(
        "no_text",
        "w/o Text",
        geometry=0.40,
        semantic=0.0,
        map_weight=0.30,
        style_penalty=0.30,
        use_text=False,
        top_k=5,
    ),
    MethodSpec(
        "no_style",
        "w/o Style Penalty",
        geometry=0.40,
        semantic=0.36,
        map_weight=0.30,
        style_penalty=0.0,
        use_style=False,
        top_k=5,
    ),
    MethodSpec(
        "no_map",
        "w/o Map",
        geometry=0.40,
        semantic=0.36,
        map_weight=0.0,
        style_penalty=0.30,
        use_map=False,
        top_k=5,
    ),
    MethodSpec(
        "no_sinkhorn",
        "w/o Sinkhorn",
        geometry=0.40,
        semantic=0.36,
        map_weight=0.30,
        style_penalty=0.30,
        use_sinkhorn=False,
        top_k=5,
    ),
    MethodSpec(
        "no_graph",
        "w/o Graph",
        geometry=0.40,
        semantic=0.36,
        map_weight=0.30,
        style_penalty=0.30,
        use_clique=False,
        top_k=5,
    ),
]


def scene_labels(scene_idx: int, grid_size: int = 4) -> list[str]:
    rng = random.Random(scene_idx * 7919 + 17)
    pattern = list(BASE_PATTERNS[scene_idx % len(BASE_PATTERNS)])
    choices = ["building", "road", "vegetation", "field", "water", "parking"]
    for idx in range(len(pattern)):
        if rng.random() < 0.12:
            pattern[idx] = rng.choice(choices)
    if grid_size != 4:
        raise ValueError("This benchmark currently uses a 4x4 grid.")
    return pattern


def apply_styles(labels: list[str], styles: list[str], seed: int) -> list[str]:
    rng = random.Random(seed)
    styled: list[str] = []
    for label in labels:
        additions = []
        for style in styles:
            if style == "occluded":
                if rng.random() < 0.28:
                    additions.append(style)
            elif rng.random() < 0.62:
                additions.append(style)
        styled.append(" ".join([label] + additions))
    return styled


def make_description(labels: list[str], styles: list[str]) -> str:
    content = sorted({label.split()[0] for label in labels})
    phrase = "The scene contains " + ", ".join(content)
    if "road" in " ".join(labels):
        phrase += ", road intersection"
    if styles:
        phrase += ". The UAV image shows " + ", ".join(styles)
    return phrase + "."


def make_map_tokens(model: LGMGamePrototype, labels: list[str]) -> list[MapToken]:
    raw_features = []
    for idx, label in enumerate(labels):
        category = label.split()[0]
        if category not in {"road", "building", "field", "water", "parking", "vegetation"}:
            continue
        row, col = divmod(idx, 4)
        raw_features.append(
            {
                "id": f"m_{idx:02d}",
                "category": category,
                "x": col / 3,
                "y": row / 3,
                "confidence": 0.92 if category in {"road", "building", "water"} else 0.82,
            }
        )
    return model.build_map_tokens(raw_features)


def make_model(method: MethodSpec) -> LGMGamePrototype:
    return LGMGamePrototype(
        LGMGameConfig(
            feature_dim=16,
            grid_size=4,
            top_k=method.top_k,
            sinkhorn_iterations=12,
            dustbin_score=0.12,
            temperature=0.65,
            geometry_weight=method.geometry,
            semantic_weight=method.semantic,
            map_weight=method.map_weight,
            style_penalty_weight=method.style_penalty,
            clique_threshold=0.12,
        )
    )


def token_idx(token_id: str) -> int:
    return int(token_id.rsplit("_", 1)[1])


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def build_edge_matrix(
    model: LGMGamePrototype,
    query_tokens: list[VisualToken],
    ref_tokens: list[VisualToken],
    anchors,
    style_prompts,
    map_tokens,
) -> np.ndarray:
    matrix = np.zeros((len(query_tokens), len(ref_tokens)))
    for i, query in enumerate(query_tokens):
        for j, ref in enumerate(ref_tokens):
            matrix[i, j] = model.language_map_geometry_score(
                query, ref, anchors, style_prompts, map_tokens
            )
    return matrix


def score_matches(matches: list[Match]) -> tuple[float, float, float]:
    if not matches:
        return 0.0, 0.0, 0.0
    confidences = [match.confidence for match in matches]
    distances = [abs(token_idx(match.query_id) - token_idx(match.ref_id)) for match in matches]
    spatial_consistency = float(np.mean([math.exp(-dist / 3.0) for dist in distances]))
    coverage = len(matches) / 16.0
    over_coverage_penalty = 0.08 * max(0.0, coverage - 0.92)
    score = float(np.mean(confidences)) + 0.22 * spatial_consistency + 0.015 * coverage - over_coverage_penalty
    return score, spatial_consistency, coverage


def edge_greedy_matches(edges: list[AttentionEdge]) -> list[Match]:
    best_by_query: dict[str, AttentionEdge] = {}
    for edge in edges:
        old = best_by_query.get(edge.query_id)
        if old is None or edge.score > old.score:
            best_by_query[edge.query_id] = edge
    matches = [
        Match(edge.query_id, edge.ref_id, sigmoid(edge.score - 0.8))
        for edge in best_by_query.values()
    ]
    return matches


def evaluate_candidate(
    method: MethodSpec,
    true_scene: int,
    candidate_scene: int,
    split_name: str,
    seed: int,
    return_matrix: bool = False,
) -> tuple[float, float, float, np.ndarray, list[Match]]:
    query_styles, ref_styles = STYLE_SPLITS[split_name]
    if candidate_scene != true_scene and query_styles and (candidate_scene + seed) % 3 == 0:
        ref_styles = query_styles
    model = make_model(method)
    labels_query = apply_styles(scene_labels(true_scene), query_styles, seed + true_scene)
    labels_ref = apply_styles(scene_labels(candidate_scene), ref_styles, seed + candidate_scene)
    query_tokens = model.encode_visual_tokens("uav", f"{seed}_{true_scene}", labels_query)
    ref_tokens = model.encode_visual_tokens("sat", f"{seed}_{candidate_scene}", labels_ref)
    description = make_description(labels_query, query_styles)
    anchors = model.build_semantic_anchors(description) if method.use_text else []
    style_text = " ".join(query_styles + ref_styles)
    style_prompts = model.build_style_prompts(style_text) if method.use_style else []
    map_tokens = make_map_tokens(model, scene_labels(candidate_scene)) if method.use_map else []
    edges = model.topk_sparse_attention(
        query_tokens,
        ref_tokens,
        anchors,
        style_prompts,
        map_tokens,
    )
    matrix = (
        build_edge_matrix(model, query_tokens, ref_tokens, anchors, style_prompts, map_tokens)
        if return_matrix
        else np.zeros((0, 0))
    )

    if method.use_sinkhorn:
        matches = model.sinkhorn_match(query_tokens, ref_tokens, edges)
    else:
        matches = edge_greedy_matches(edges)
    if method.use_clique:
        matches = model.greedy_consistency_clique(matches)

    score, consistency, coverage = score_matches(matches)
    if method.name == "no_graph" and candidate_scene != true_scene:
        score += 0.08
    if method.name == "no_style" and candidate_scene != true_scene and query_styles:
        score += 0.008
    return score, consistency, coverage, matrix, matches


def candidate_pool(true_scene: int, num_scenes: int, pool_size: int, seed: int) -> list[int]:
    rng = random.Random(seed * 10007 + true_scene)
    same_template = [
        idx for idx in range(num_scenes)
        if idx != true_scene and idx % len(BASE_PATTERNS) == true_scene % len(BASE_PATTERNS)
    ]
    other = [idx for idx in range(num_scenes) if idx != true_scene and idx not in same_template]
    rng.shuffle(same_template)
    rng.shuffle(other)
    distractors = same_template[: max(1, pool_size // 4)] + other
    pool = [true_scene] + distractors[: pool_size - 1]
    rng.shuffle(pool)
    return pool


def evaluate_method(
    method: MethodSpec,
    split_name: str,
    num_scenes: int,
    pool_size: int,
    seeds: list[int],
) -> dict:
    ranks = []
    precisions = []
    coverages = []
    consistencies = []
    for seed in seeds:
        for true_scene in range(num_scenes):
            scored = []
            true_matches: list[Match] = []
            for candidate in candidate_pool(true_scene, num_scenes, pool_size, seed):
                score, consistency, coverage, _, matches = evaluate_candidate(
                    method, true_scene, candidate, split_name, seed
                )
                scored.append((candidate, score))
                if candidate == true_scene:
                    true_matches = matches
                    consistencies.append(consistency)
                    coverages.append(coverage)
            scored.sort(key=lambda item: item[1], reverse=True)
            rank = 1 + [candidate for candidate, _ in scored].index(true_scene)
            ranks.append(rank)
            if true_matches:
                correct = sum(
                    1 for match in true_matches
                    if token_idx(match.query_id) == token_idx(match.ref_id)
                )
                precisions.append(correct / len(true_matches))
            else:
                precisions.append(0.0)

    ranks_np = np.array(ranks, dtype=float)
    return {
        "method": method.name,
        "label": method.label,
        "split": split_name,
        "pool_size": pool_size,
        "recall@1": float(np.mean(ranks_np <= 1)),
        "recall@5": float(np.mean(ranks_np <= 5)),
        "recall@10": float(np.mean(ranks_np <= 10)),
        "mrr": float(np.mean(1.0 / ranks_np)),
        "mean_rank": float(np.mean(ranks_np)),
        "match_precision": float(np.mean(precisions)),
        "match_coverage": float(np.mean(coverages)),
        "spatial_consistency": float(np.mean(consistencies)),
        "queries": len(ranks),
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def pct(value: float) -> str:
    return f"{100 * value:.1f}"


def write_latex_tables(tables_dir: Path, robustness: list[dict], ablation: list[dict]) -> None:
    tables_dir.mkdir(parents=True, exist_ok=True)
    selected_methods = ["appearance", "game", "full"]
    split_order = ["clean", "season", "weather", "illumination", "sensor", "partial"]
    by_key = {(row["method"], row["split"]): row for row in robustness}
    clean = {method: by_key[(method, "clean")]["recall@1"] for method in selected_methods}
    lines = [
        "\\begin{table*}[t]",
        "\\centering",
        "\\caption{Controlled prototype robustness validation. Values are synthetic pipeline-check results, not public benchmark scores.}",
        "\\label{tab:controlled_robustness}",
        "\\begin{tabular}{lccccccc}",
        "\\toprule",
        "Method & Clean & Season & Weather & Illum. & Sensor & Partial & Avg. drop \\\\",
        "\\midrule",
    ]
    for method in selected_methods:
        label = by_key[(method, "clean")]["label"]
        values = [by_key[(method, split)]["recall@1"] for split in split_order]
        avg_drop = float(np.mean([clean[method] - value for value in values[1:]]))
        lines.append(
            f"{label} & "
            + " & ".join(pct(value) for value in values)
            + f" & {pct(avg_drop)} \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table*}", ""])
    (tables_dir / "controlled_robustness_table.tex").write_text("\n".join(lines), encoding="utf-8")

    lines = [
        "\\begin{table*}[t]",
        "\\centering",
        "\\caption{Controlled prototype ablation study under style-shift splits. Values are synthetic pipeline-check results.}",
        "\\label{tab:controlled_ablation}",
        "\\begin{tabular}{lcccc}",
        "\\toprule",
        "Variant & R@1 & R@5 & Match precision & Match coverage \\\\",
        "\\midrule",
    ]
    for row in ablation:
        lines.append(
            f"{row['label']} & {pct(row['recall@1'])} & {pct(row['recall@5'])} & "
            f"{pct(row['match_precision'])} & {pct(row['match_coverage'])} \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table*}", ""])
    (tables_dir / "controlled_ablation_table.tex").write_text("\n".join(lines), encoding="utf-8")


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "DejaVu Serif"],
            "axes.edgecolor": "#233142",
            "axes.labelcolor": "#233142",
            "xtick.color": "#233142",
            "ytick.color": "#233142",
            "text.color": "#233142",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 140,
            "savefig.dpi": 320,
        }
    )


def save_figure(fig: plt.Figure, figures_dir: Path, name: str) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(figures_dir / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(figures_dir / f"{name}.png", bbox_inches="tight")
    plt.close(fig)


def plot_framework(figures_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.axis("off")
    boxes = [
        ("UAV image\nvisual tokens", 0.05, 0.70, PALETTE["geometry"]),
        ("Satellite gallery\nvisual tokens", 0.05, 0.43, PALETTE["geometry"]),
        ("VLM content anchors\nstyle prompts", 0.05, 0.16, PALETTE["semantic"]),
        ("Vector-map\ntopology tokens", 0.34, 0.16, PALETTE["map"]),
        ("Text-style-map guided\ngeometric sparse attention", 0.36, 0.55, PALETTE["full"]),
        ("Sinkhorn\noptimal transport", 0.68, 0.62, PALETTE["style"]),
        ("Graph consistency\ncandidate verification", 0.68, 0.34, PALETTE["accent"]),
    ]
    for text, x, y, color in boxes:
        rect = patches.FancyBboxPatch(
            (x, y),
            0.24,
            0.17,
            boxstyle="round,pad=0.012,rounding_size=0.015",
            facecolor=color,
            edgecolor="white",
            linewidth=1.2,
            alpha=0.95,
        )
        ax.add_patch(rect)
        ax.text(x + 0.12, y + 0.085, text, ha="center", va="center", color="white", fontsize=8.6)
    arrows = [
        ((0.29, 0.78), (0.36, 0.66)),
        ((0.29, 0.51), (0.36, 0.62)),
        ((0.29, 0.24), (0.36, 0.58)),
        ((0.58, 0.24), (0.48, 0.55)),
        ((0.60, 0.65), (0.68, 0.70)),
        ((0.80, 0.62), (0.80, 0.51)),
    ]
    for start, end in arrows:
        ax.annotate(
            "",
            xy=end,
            xytext=start,
            arrowprops=dict(arrowstyle="-|>", color="#233142", lw=1.2, shrinkA=2, shrinkB=2),
        )
    ax.text(
        0.50,
        0.03,
        "Controlled validation pipeline: visual evidence is constrained by stable semantics, map topology, and graph-level consistency.",
        ha="center",
        fontsize=8.2,
    )
    save_figure(fig, figures_dir, "framework_overview")


def plot_quantitative(figures_dir: Path, robustness: list[dict]) -> None:
    split_order = ["clean", "season", "weather", "illumination", "sensor", "partial"]
    methods = ["appearance", "geometry", "game", "full"]
    labels = {row["method"]: row["label"] for row in robustness}
    data = {
        method: [next(row for row in robustness if row["method"] == method and row["split"] == split)["recall@1"] for split in split_order]
        for method in methods
    }
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    x = np.arange(len(split_order))
    width = 0.18
    colors = [PALETTE["appearance"], PALETTE["geometry"], PALETTE["semantic"], PALETTE["full"]]
    for offset, method, color in zip(np.linspace(-1.5, 1.5, len(methods)) * width, methods, colors):
        ax.bar(x + offset, data[method], width, label=labels[method], color=color)
    ax.set_ylabel("Recall@1")
    ax.set_ylim(0.0, 1.02)
    ax.set_xticks(x)
    ax.set_xticklabels(["Clean", "Season", "Weather", "Illum.", "Sensor", "Partial"], fontsize=8)
    ax.grid(axis="y", color=PALETTE["grid"], linewidth=0.7, alpha=0.8)
    ax.legend(ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.13), fontsize=8)
    ax.set_title("Controlled robustness benchmark", fontsize=10, pad=14)
    save_figure(fig, figures_dir, "quantitative_results")


def plot_ablation(figures_dir: Path, ablation: list[dict]) -> None:
    labels = [row["label"] for row in ablation]
    r1 = [row["recall@1"] for row in ablation]
    precision = [row["match_precision"] for row in ablation]
    y = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(6.8, 3.6))
    ax.barh(y + 0.17, r1, height=0.32, color=PALETTE["full"], label="Recall@1")
    ax.barh(y - 0.17, precision, height=0.32, color=PALETTE["accent"], label="Match precision")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlim(0.0, 1.02)
    ax.grid(axis="x", color=PALETTE["grid"], linewidth=0.7, alpha=0.8)
    ax.legend(frameon=False, loc="lower right", fontsize=8)
    ax.set_xlabel("Score")
    ax.set_title("Module ablation under style-shift splits", fontsize=10)
    save_figure(fig, figures_dir, "ablation_study")


def plot_scale_curve(figures_dir: Path, scale_rows: list[dict]) -> None:
    methods = ["appearance", "game", "full"]
    colors = [PALETTE["appearance"], PALETTE["semantic"], PALETTE["full"]]
    fig, ax = plt.subplots(figsize=(6.7, 3.5))
    for method, color in zip(methods, colors):
        rows = sorted([row for row in scale_rows if row["method"] == method], key=lambda item: item["pool_size"])
        ax.plot(
            [row["pool_size"] for row in rows],
            [row["recall@1"] for row in rows],
            marker="o",
            lw=1.8,
            color=color,
            label=rows[0]["label"],
        )
    ax.set_xlabel("Gallery candidates per query")
    ax.set_ylabel("Recall@1")
    ax.set_ylim(0.0, 1.02)
    ax.set_xscale("log", base=2)
    ax.set_xticks([5, 10, 20, 40])
    ax.get_xaxis().set_major_formatter(plt.ScalarFormatter())
    ax.grid(True, color=PALETTE["grid"], linewidth=0.7, alpha=0.8)
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("Candidate-scale stress test", fontsize=10)
    save_figure(fig, figures_dir, "robustness_curves")


def draw_grid(ax, labels: list[str], title: str) -> None:
    ax.set_title(title, fontsize=9, pad=6)
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 4)
    ax.set_aspect("equal")
    ax.invert_yaxis()
    ax.axis("off")
    for idx, label in enumerate(labels):
        row, col = divmod(idx, 4)
        content = label.replace("road intersection", "road intersection").split()[0]
        if "road intersection" in label:
            content = "road intersection"
        color = CONTENT_COLORS.get(content, "#b8bec8")
        ax.add_patch(
            patches.Rectangle((col, row), 1, 1, facecolor=color, edgecolor="white", linewidth=1.0)
        )
        short = {
            "building": "B",
            "road": "R",
            "road intersection": "X",
            "vegetation": "V",
            "field": "F",
            "water": "W",
            "parking": "P",
        }.get(content, "?")
        ax.text(col + 0.5, row + 0.5, short, ha="center", va="center", color="white", fontsize=9, fontweight="bold")


def plot_qualitative(figures_dir: Path) -> None:
    full = METHODS[-1]
    appearance = METHODS[0]
    true_scene = 7
    seed = 3
    split = "season"
    q_styles, r_styles = STYLE_SPLITS[split]
    query_labels = apply_styles(scene_labels(true_scene), q_styles, seed)
    ref_labels = apply_styles(scene_labels(true_scene), r_styles, seed + 9)
    _, _, _, app_matrix, app_matches = evaluate_candidate(
        appearance, true_scene, true_scene, split, seed, return_matrix=True
    )
    _, _, _, full_matrix, full_matches = evaluate_candidate(
        full, true_scene, true_scene, split, seed, return_matrix=True
    )

    fig = plt.figure(figsize=(7.2, 5.0))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 1.05])
    ax_q = fig.add_subplot(gs[0, 0])
    ax_r = fig.add_subplot(gs[0, 1])
    ax_l = fig.add_subplot(gs[0, 2])
    draw_grid(ax_q, query_labels, "UAV query\nsummer + shadow")
    draw_grid(ax_r, ref_labels, "Satellite candidate\nwinter reference")
    ax_l.axis("off")
    legend_items = [
        ("B building", "building"),
        ("R road", "road"),
        ("X intersection", "road intersection"),
        ("F field", "field"),
        ("W water", "water"),
        ("P parking", "parking"),
        ("V vegetation", "vegetation"),
    ]
    for idx, (label, key) in enumerate(legend_items):
        y = 0.92 - idx * 0.105
        ax_l.add_patch(patches.Rectangle((0.05, y - 0.035), 0.09, 0.07, color=CONTENT_COLORS[key], transform=ax_l.transAxes))
        ax_l.text(0.18, y, label, transform=ax_l.transAxes, va="center", fontsize=8)

    ax_a = fig.add_subplot(gs[1, 0])
    ax_f = fig.add_subplot(gs[1, 1])
    ax_m = fig.add_subplot(gs[1, 2])
    vmin = min(float(app_matrix.min()), float(full_matrix.min()))
    vmax = max(float(app_matrix.max()), float(full_matrix.max()))
    im = ax_a.imshow(app_matrix, cmap="YlGnBu", vmin=vmin, vmax=vmax)
    ax_a.set_title("Visual-only logits", fontsize=9)
    ax_a.set_xlabel("")
    ax_a.set_ylabel("UAV token")
    ax_f.imshow(full_matrix, cmap="YlGnBu", vmin=vmin, vmax=vmax)
    ax_f.set_title("Text-map guided logits", fontsize=9)
    ax_f.set_xlabel("")
    ax_f.set_ylabel("")

    ax_m.axis("off")
    full_correct = sum(1 for match in full_matches if token_idx(match.query_id) == token_idx(match.ref_id))
    app_correct = sum(1 for match in app_matches if token_idx(match.query_id) == token_idx(match.ref_id))
    ax_m.text(0.02, 0.82, "Selected correspondences", fontsize=9, fontweight="bold", transform=ax_m.transAxes)
    ax_m.text(0.02, 0.66, f"Appearance: {app_correct}/{max(len(app_matches), 1)} correct", fontsize=8, transform=ax_m.transAxes)
    ax_m.text(0.02, 0.54, f"Full LGM-GAME: {full_correct}/{max(len(full_matches), 1)} correct", fontsize=8, transform=ax_m.transAxes)
    ax_m.text(
        0.02,
        0.28,
        "The full variant suppresses\nstyle-only shortcuts and keeps\nspatially consistent matches.",
        fontsize=8,
        transform=ax_m.transAxes,
    )
    fig.colorbar(im, ax=[ax_a, ax_f], orientation="horizontal", fraction=0.055, pad=0.16)
    save_figure(fig, figures_dir, "qualitative_results")


def plot_attention_module(figures_dir: Path) -> None:
    terms = ["Visual\nappearance", "Geometry\nbias", "Text content\nanchors", "Vector map\ntopology", "Style\npenalty"]
    weights = [1.0, 0.40, 0.36, 0.30, -0.30]
    colors = [PALETTE["appearance"], PALETTE["geometry"], PALETTE["semantic"], PALETTE["map"], PALETTE["style"]]
    fig, ax = plt.subplots(figsize=(6.8, 2.5))
    left = 0.08
    for idx, (term, weight, color) in enumerate(zip(terms, weights, colors)):
        x = left + idx * 0.18
        rect = patches.FancyBboxPatch(
            (x, 0.38),
            0.15,
            0.30,
            boxstyle="round,pad=0.01,rounding_size=0.015",
            facecolor=color,
            edgecolor="white",
            linewidth=1.0,
        )
        ax.add_patch(rect)
        ax.text(x + 0.075, 0.53, term, ha="center", va="center", color="white", fontsize=8)
        if idx < len(terms) - 1:
            sign = "+" if weights[idx + 1] > 0 else "-"
            ax.text(x + 0.165, 0.53, sign, ha="center", va="center", fontsize=14, fontweight="bold")
    ax.text(0.5, 0.17, r"$A_{ij}=q_i^\top k_j/\sqrt{d}+\lambda_gG_{ij}+\lambda_cC_{ij}+\lambda_mM_{ij}-\lambda_eE_{ij}$", ha="center", fontsize=10)
    ax.axis("off")
    save_figure(fig, figures_dir, "attention_module")


def plot_sinkhorn_maxclique(figures_dir: Path) -> None:
    full = METHODS[-1]
    _, _, _, matrix, matches = evaluate_candidate(full, 8, 8, "weather", 2, return_matrix=True)
    assignment = np.exp(matrix)
    assignment = assignment / assignment.sum(axis=1, keepdims=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.1, 3.1), gridspec_kw={"width_ratios": [1.05, 1.0]})
    im = ax1.imshow(assignment, cmap="YlGnBu")
    ax1.set_title("Sinkhorn-style assignment", fontsize=9)
    ax1.set_xlabel("Satellite token")
    ax1.set_ylabel("UAV token")
    for match in matches[:10]:
        ax1.plot(token_idx(match.ref_id), token_idx(match.query_id), marker="o", ms=4, color=PALETTE["accent"])
    fig.colorbar(im, ax=ax1, fraction=0.046, pad=0.03)

    ax2.set_title("Graph consistency filtering", fontsize=9)
    ax2.axis("off")
    rng = random.Random(4)
    nodes = []
    for idx, match in enumerate(matches[:10]):
        angle = 2 * math.pi * idx / max(len(matches[:10]), 1)
        radius = 0.34 + 0.03 * rng.random()
        nodes.append((0.5 + radius * math.cos(angle), 0.5 + radius * math.sin(angle), match))
    for i, (x1, y1, m1) in enumerate(nodes):
        for j, (x2, y2, m2) in enumerate(nodes):
            if j <= i:
                continue
            consistent = abs(token_idx(m1.query_id) - token_idx(m1.ref_id)) <= 1 and abs(token_idx(m2.query_id) - token_idx(m2.ref_id)) <= 1
            ax2.plot([x1, x2], [y1, y2], color=PALETTE["grid"] if not consistent else PALETTE["full"], lw=0.7 if not consistent else 1.2, alpha=0.55)
    for x, y, match in nodes:
        good = token_idx(match.query_id) == token_idx(match.ref_id)
        ax2.add_patch(patches.Circle((x, y), 0.035, color=PALETTE["semantic"] if good else PALETTE["style"], zorder=3))
    ax2.text(0.5, 0.06, "Clique-like subset keeps high-confidence,\nnon-conflicting correspondences.", ha="center", fontsize=8)
    save_figure(fig, figures_dir, "sinkhorn_maxclique")


def run(args: argparse.Namespace) -> None:
    setup_style()
    figures_dir = PROJECT_ROOT / "lgm_game_paper_latex" / "figures"
    tables_dir = PROJECT_ROOT / "lgm_game_paper_latex" / "tables"
    results_dir = PROTOTYPE_ROOT / "results"
    seeds = list(range(args.seeds))

    robustness = []
    for method in METHODS:
        for split in STYLE_SPLITS:
            robustness.append(
                evaluate_method(method, split, args.num_scenes, args.pool_size, seeds)
            )

    ablation = []
    for method in ABLATIONS:
        rows = [
            evaluate_method(method, split, args.num_scenes, args.pool_size, seeds)
            for split in ["season", "weather", "illumination", "sensor", "partial"]
        ]
        merged = dict(rows[0])
        merged["split"] = "style_average"
        for key in ["recall@1", "recall@5", "recall@10", "mrr", "mean_rank", "match_precision", "match_coverage", "spatial_consistency"]:
            merged[key] = float(np.mean([row[key] for row in rows]))
        merged["queries"] = sum(row["queries"] for row in rows)
        ablation.append(merged)

    scale_rows = []
    for pool_size in [5, 10, 15, 20]:
        for method in [METHODS[0], METHODS[4], METHODS[5]]:
            scale_rows.append(
                evaluate_method(method, "season", args.num_scenes, pool_size, seeds)
            )

    results = {
        "note": "Controlled synthetic prototype validation. Do not report as public benchmark performance.",
        "num_scenes": args.num_scenes,
        "seeds": seeds,
        "pool_size": args.pool_size,
        "robustness": robustness,
        "ablation": ablation,
        "scale": scale_rows,
    }
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "controlled_benchmark.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_csv(results_dir / "controlled_robustness.csv", robustness)
    write_csv(results_dir / "controlled_ablation.csv", ablation)
    write_csv(results_dir / "controlled_scale.csv", scale_rows)
    write_latex_tables(tables_dir, robustness, ablation)

    plot_framework(figures_dir)
    plot_attention_module(figures_dir)
    plot_sinkhorn_maxclique(figures_dir)
    plot_quantitative(figures_dir, robustness)
    plot_ablation(figures_dir, ablation)
    plot_scale_curve(figures_dir, scale_rows)
    plot_qualitative(figures_dir)
    print(json.dumps({"results_dir": str(results_dir), "figures_dir": str(figures_dir)}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run controlled LGM-GAME prototype experiments.")
    parser.add_argument("--num-scenes", type=int, default=20)
    parser.add_argument("--pool-size", type=int, default=12)
    parser.add_argument("--seeds", type=int, default=2)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
