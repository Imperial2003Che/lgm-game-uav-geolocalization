from __future__ import annotations

import argparse
import csv
import json
import math
import random
import time
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from tqdm import tqdm

from run_real_imtmn_benchmark import (
    IMAGE_EXTS,
    PALETTE,
    ImageItem,
    build_tasks,
    extract_features,
    feature_transform,
    load_model,
    save_figure,
    setup_style,
)


@dataclass(frozen=True)
class FeaturePack:
    features: torch.Tensor
    labels: list[str]
    paths: list[str]
    tags: list[str]


class LGMGameLiteHead(nn.Module):
    """Trainable feature alignment head used for the executable paper suite.

    The full manuscript proposes language anchors and map tokens. The current
    local datasets do not contain VLM captions or vector-map alignments, so this
    head trains the available content-alignment part on cached real features.
    """

    def __init__(self, dim: int, hidden_dim: int = 128, dropout: float = 0.05) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, dim),
        )
        self.residual_scale = nn.Parameter(torch.tensor(0.25))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = x + self.residual_scale.tanh() * self.net(x)
        return F.normalize(y, dim=-1)


def collect_university_train(root: Path, view_dir: str) -> list[ImageItem]:
    base = root / "University-1652" / "train" / view_dir
    items: list[ImageItem] = []
    if not base.exists():
        return items
    for path in sorted(base.rglob("*")):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            rel = path.relative_to(base).parts
            if len(rel) >= 2:
                items.append(ImageItem(str(path), rel[0], view_dir))
    return items


def as_pack(data: dict) -> FeaturePack:
    return FeaturePack(
        features=data["features"].float(),
        labels=list(data["labels"]),
        paths=list(data.get("paths", [])),
        tags=list(data.get("tags", [])),
    )


def clone_pack(pack: FeaturePack, features: torch.Tensor) -> FeaturePack:
    return FeaturePack(features=features.float().cpu(), labels=pack.labels, paths=pack.paths, tags=pack.tags)


def labels_to_indices(labels: list[str]) -> dict[str, list[int]]:
    grouped: dict[str, list[int]] = {}
    for idx, label in enumerate(labels):
        grouped.setdefault(label, []).append(idx)
    return grouped


def common_labels(*packs: FeaturePack) -> list[str]:
    sets = [set(pack.labels) for pack in packs]
    return sorted(set.intersection(*sets)) if sets else []


def sample_feature(pack: FeaturePack, grouped: dict[str, list[int]], label: str, rng: random.Random) -> torch.Tensor:
    idx = rng.choice(grouped[label])
    return pack.features[idx]


def feature_augment(x: torch.Tensor, rng: torch.Generator, noise_std: float = 0.035, drop_prob: float = 0.08) -> torch.Tensor:
    noise = torch.randn(x.shape, generator=rng, device=x.device, dtype=x.dtype) * noise_std
    keep = (torch.rand(x.shape, generator=rng, device=x.device) > drop_prob).float()
    return x * keep + noise


def contrastive_loss(q: torch.Tensor, g: torch.Tensor, temperature: float) -> torch.Tensor:
    logits = q @ g.t() / temperature
    labels = torch.arange(logits.shape[0], device=logits.device)
    return (F.cross_entropy(logits, labels) + F.cross_entropy(logits.t(), labels)) * 0.5


def train_head(
    train_uav: FeaturePack,
    train_sat: FeaturePack,
    seed: int,
    epochs: int,
    batch_classes: int,
    lr: float,
    style_consistency: bool,
    device: torch.device,
) -> tuple[LGMGameLiteHead, dict]:
    torch.manual_seed(seed)
    np.random.seed(seed)
    rng = random.Random(seed)
    torch_rng = torch.Generator(device=device)
    torch_rng.manual_seed(seed)

    dim = int(train_uav.features.shape[1])
    head = LGMGameLiteHead(dim=dim).to(device)
    optimizer = torch.optim.AdamW(head.parameters(), lr=lr, weight_decay=1e-4)
    uav_by_label = labels_to_indices(train_uav.labels)
    sat_by_label = labels_to_indices(train_sat.labels)
    labels = common_labels(train_uav, train_sat)
    steps_per_epoch = max(1, math.ceil(len(labels) / batch_classes))
    history: list[dict] = []

    for epoch in range(epochs):
        rng.shuffle(labels)
        epoch_losses: list[float] = []
        for step in range(steps_per_epoch):
            chosen = labels[step * batch_classes : (step + 1) * batch_classes]
            if len(chosen) < 2:
                continue
            q = torch.stack([sample_feature(train_uav, uav_by_label, label, rng) for label in chosen]).to(device)
            g = torch.stack([sample_feature(train_sat, sat_by_label, label, rng) for label in chosen]).to(device)

            q_emb = head(q)
            g_emb = head(g)
            loss = contrastive_loss(q_emb, g_emb, temperature=0.07)

            if style_consistency:
                q_aug = feature_augment(q, torch_rng)
                g_aug = feature_augment(g, torch_rng)
                q_aug_emb = head(q_aug)
                g_aug_emb = head(g_aug)
                inv_loss = (1.0 - (q_emb.detach() * q_aug_emb).sum(dim=1)).mean()
                inv_loss = inv_loss + (1.0 - (g_emb.detach() * g_aug_emb).sum(dim=1)).mean()
                aug_loss = contrastive_loss(q_aug_emb, g_aug_emb, temperature=0.07)
                loss = loss + 0.35 * inv_loss + 0.25 * aug_loss

            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(head.parameters(), 1.0)
            optimizer.step()
            epoch_losses.append(float(loss.detach().cpu()))

        history.append({"epoch": epoch + 1, "loss": float(np.mean(epoch_losses)) if epoch_losses else 0.0})

    return head.cpu().eval(), {"seed": seed, "epochs": epochs, "history": history}


def transform_pack(pack: FeaturePack, head: LGMGameLiteHead | None, device: torch.device, batch_size: int = 8192) -> FeaturePack:
    if head is None:
        return pack
    head = head.to(device).eval()
    outs: list[torch.Tensor] = []
    with torch.no_grad():
        for start in range(0, pack.features.shape[0], batch_size):
            outs.append(head(pack.features[start : start + batch_size].to(device)).cpu())
    head.cpu()
    return clone_pack(pack, torch.cat(outs, dim=0))


def centered_pack(pack: FeaturePack, mean: torch.Tensor) -> FeaturePack:
    return clone_pack(pack, pack.features - mean.reshape(1, -1))


def encode_labels(query_labels: list[str], gallery_labels: list[str]) -> tuple[torch.Tensor, torch.Tensor]:
    mapping = {label: idx for idx, label in enumerate(sorted(set(query_labels) | set(gallery_labels)))}
    q = torch.tensor([mapping[label] for label in query_labels], dtype=torch.long)
    g = torch.tensor([mapping[label] for label in gallery_labels], dtype=torch.long)
    return q, g


def metrics_from_scores(
    scores: torch.Tensor,
    query_labels: list[str],
    gallery_labels: list[str],
    ks: tuple[int, ...] = (1, 5, 10, 20),
) -> dict:
    q_ids, g_ids = encode_labels(query_labels, gallery_labels)
    sorted_indices = scores.argsort(dim=1, descending=True)
    recalls = {k: [] for k in ks}
    aps: list[float] = []
    rrs: list[float] = []
    best_ranks: list[int] = []

    for qi in range(sorted_indices.shape[0]):
        ranked_labels = g_ids[sorted_indices[qi]]
        positives = (ranked_labels == q_ids[qi]).nonzero(as_tuple=False).flatten()
        if positives.numel() == 0:
            continue
        ranks = positives.float() + 1.0
        best = int(ranks[0].item())
        best_ranks.append(best)
        rrs.append(1.0 / best)
        aps.append((torch.arange(1, ranks.numel() + 1, dtype=torch.float32) / ranks).mean().item())
        for k in ks:
            recalls[k].append(1.0 if best <= k else 0.0)

    n = max(1, len(best_ranks))
    out = {
        "Num_Queries": len(query_labels),
        "Num_Gallery": len(gallery_labels),
        "mAP": float(np.mean(aps) * 100.0) if aps else 0.0,
        "MRR": float(np.mean(rrs) * 100.0) if rrs else 0.0,
        "Median_Rank": float(np.median(best_ranks)) if best_ranks else 0.0,
        "Mean_Rank": float(np.mean(best_ranks)) if best_ranks else 0.0,
    }
    for k in ks:
        out[f"Recall@{k}"] = float(np.mean(recalls[k]) * 100.0) if recalls[k] else 0.0
    return out


def cosine_scores(query: FeaturePack, gallery: FeaturePack) -> torch.Tensor:
    q = F.normalize(query.features.float(), dim=1)
    g = F.normalize(gallery.features.float(), dim=1)
    return q @ g.t()


def csls_scores(query: FeaturePack, gallery: FeaturePack, k: int = 10) -> torch.Tensor:
    sim = cosine_scores(query, gallery)
    kq = min(k, sim.shape[1])
    kg = min(k, sim.shape[0])
    rq = sim.topk(kq, dim=1).values.mean(dim=1, keepdim=True)
    rg = sim.topk(kg, dim=0).values.mean(dim=0, keepdim=True)
    return 2.0 * sim - rq - rg


def reciprocal_scores(query: FeaturePack, gallery: FeaturePack, k: int = 10, bonus: float = 0.08) -> torch.Tensor:
    sim = cosine_scores(query, gallery)
    q_top = sim.topk(min(k, sim.shape[1]), dim=1).indices
    g_top = sim.topk(min(k, sim.shape[0]), dim=0).indices.t()
    boosted = sim.clone()
    for qi in range(sim.shape[0]):
        for gi in q_top[qi].tolist():
            if qi in g_top[gi].tolist():
                boosted[qi, gi] += bonus
    return boosted


def evaluate_pack_method(
    task_packs: dict[str, dict[str, FeaturePack]],
    method: str,
    query_transform=None,
    gallery_transform=None,
    scorer: str = "cosine",
) -> dict[str, dict]:
    results: dict[str, dict] = {}
    for task_name, packs in task_packs.items():
        query = packs["query"]
        gallery = packs["gallery"]
        if query_transform:
            query = query_transform(task_name, query)
        if gallery_transform:
            gallery = gallery_transform(task_name, gallery)

        start = time.perf_counter()
        if scorer == "csls":
            scores = csls_scores(query, gallery)
        elif scorer == "reciprocal":
            scores = reciprocal_scores(query, gallery)
        else:
            scores = cosine_scores(query, gallery)
        metrics = metrics_from_scores(scores, query.labels, gallery.labels)
        metrics["Eval_Time_s"] = time.perf_counter() - start
        metrics["Method"] = method
        results[task_name] = metrics
    return results


def macro_metrics(results: dict[str, dict]) -> dict:
    keys = ["Recall@1", "Recall@5", "Recall@10", "mAP", "MRR", "Eval_Time_s"]
    return {key: float(np.mean([m[key] for m in results.values() if key in m])) for key in keys}


def mean_std(values: list[float]) -> str:
    if len(values) <= 1:
        return f"{values[0]:.2f}" if values else "--"
    return f"{np.mean(values):.2f}$\\pm${np.std(values, ddof=1):.2f}"


def write_rows_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def latex_table(path: Path, caption: str, label: str, columns: list[str], rows: list[list[str]], align: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    align = align or ("l" + "r" * (len(columns) - 1))
    lines = [
        "\\begin{table*}[!t]",
        "\\centering",
        "\\footnotesize",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        f"\\begin{{tabular}}{{{align}}}",
        "\\toprule",
        " & ".join(columns) + " \\\\",
        "\\midrule",
    ]
    lines.extend(" & ".join(row) + " \\\\" for row in rows)
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table*}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def save_training_table(tables_dir: Path, train_summary: dict) -> None:
    rows = [
        ["Training split", "University-1652 train drone/satellite"],
        ["Trainable module", "LGM-GAME-lite content alignment head"],
        ["Seeds", ", ".join(str(s) for s in train_summary["seeds"])],
        ["Epochs per seed", str(train_summary["epochs"])],
        ["Classes / UAV / satellite", f"{train_summary['classes']} / {train_summary['uav_images']} / {train_summary['sat_images']}"],
        ["Supervision", "Cross-view class InfoNCE + optional feature-style consistency"],
    ]
    latex_table(
        tables_dir / "publication_training_protocol_table.tex",
        "Executable training protocol used for the current local LGM-GAME-lite experiments.",
        "tab:training_protocol",
        ["Item", "Setting"],
        rows,
        align="lp{0.66\\textwidth}",
    )


def plot_ablation(figures_dir: Path, ablation_rows: list[dict]) -> None:
    names = [row["Variant"] for row in ablation_rows]
    r1 = [float(row["R@1_mean"]) for row in ablation_rows]
    mAP = [float(row["mAP_mean"]) for row in ablation_rows]
    x = np.arange(len(names))
    width = 0.36
    fig, ax = plt.subplots(figsize=(7.2, 2.65))
    ax.bar(x - width / 2, r1, width, label="R@1", color=PALETTE["blue"])
    ax.bar(x + width / 2, mAP, width, label="mAP", color=PALETTE["green"])
    ax.set_ylabel("Macro score (%)", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=18, ha="right", fontsize=7)
    ax.grid(axis="y", color=PALETTE["grid"], linewidth=0.7)
    ax.tick_params(axis="y", labelsize=7)
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper left")
    ax.set_ylim(0, max(max(r1), max(mAP)) * 1.18)
    save_figure(fig, figures_dir, "publication_ablation_bars")


def plot_efficiency(figures_dir: Path, rows: list[dict]) -> None:
    names = [row["Method"] for row in rows]
    times = [float(row["Mean_eval_time_s"]) for row in rows]
    params = [float(row["Trainable_params_M"]) * 1000.0 for row in rows]
    fig, ax = plt.subplots(figsize=(6.8, 2.65))
    ax.scatter(times, params, s=80, color=PALETTE["blue"], edgecolor="white", linewidth=1.0)
    for name, x, y in zip(names, times, params):
        offset = 0.55 if y <= 0.01 else 0.45
        ax.text(x, y + offset, name, fontsize=7, ha="center")
    ax.set_xlabel("Mean ranking time per task (s, CPU)", fontsize=8)
    ax.set_ylabel("Extra params (K)", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.set_ylim(-0.8, max(params) * 1.22 + 0.5)
    ax.set_xlim(min(times) * 0.96, max(times) * 1.03)
    ax.grid(True, color=PALETTE["grid"], linewidth=0.7)
    save_figure(fig, figures_dir, "publication_efficiency_tradeoff")


def plot_robustness(figures_dir: Path, rows: list[dict]) -> None:
    names = [row["Group"] for row in rows]
    raw = [float(row["Raw_R@1"]) for row in rows]
    full = [float(row["Full_R@1"]) for row in rows]
    x = np.arange(len(rows))
    width = 0.36
    fig, ax = plt.subplots(figsize=(7.2, 2.65))
    ax.bar(x - width / 2, raw, width, label="Feature base", color=PALETTE["slate"])
    ax.bar(x + width / 2, full, width, label="LGM-lite", color=PALETTE["green"])
    ax.set_ylabel("Recall@1 (%)", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=20, ha="right", fontsize=7)
    ax.grid(axis="y", color=PALETTE["grid"], linewidth=0.7)
    ax.tick_params(axis="y", labelsize=7)
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper left")
    ax.set_ylim(0, max(max(raw), max(full)) * 1.20)
    save_figure(fig, figures_dir, "publication_robustness_groups")


def perturb_pack(pack: FeaturePack, mode: str, seed: int) -> FeaturePack:
    gen = torch.Generator()
    gen.manual_seed(seed)
    x = pack.features.clone().float()
    if mode == "noise":
        x = x + 0.04 * torch.randn(x.shape, generator=gen)
    elif mode == "dropout":
        mask = (torch.rand(x.shape, generator=gen) > 0.10).float()
        x = x * mask
    elif mode == "scale":
        scale = 0.85 + 0.30 * torch.rand((x.shape[0], 1), generator=gen)
        x = x * scale
    elif mode == "mixed":
        mask = (torch.rand(x.shape, generator=gen) > 0.08).float()
        x = x * mask + 0.03 * torch.randn(x.shape, generator=gen)
    return clone_pack(pack, x)


def subset_by_tag(pack: FeaturePack, tag: str) -> FeaturePack:
    idx = [i for i, item_tag in enumerate(pack.tags) if item_tag == tag]
    if not idx:
        return pack
    return FeaturePack(
        features=pack.features[idx],
        labels=[pack.labels[i] for i in idx],
        paths=[pack.paths[i] for i in idx] if pack.paths else [],
        tags=[pack.tags[i] for i in idx] if pack.tags else [],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LGM-GAME publication experiment suite on cached real features.")
    parser.add_argument("--imtmn-root", type=Path, default=Path(r"C:\Programs\IMTMN"))
    parser.add_argument("--data-root", type=Path, default=Path(r"C:\Programs\IMTMN\datasets"))
    parser.add_argument("--output-root", type=Path, default=Path(r"C:\Programs\lgm-game-uav-geolocalization"))
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    parser.add_argument("--batch-classes", type=int, default=128)
    parser.add_argument("--lr", type=float, default=2e-3)
    parser.add_argument("--extract-batch-size", type=int, default=128)
    parser.add_argument("--force-features", action="store_true")
    args = parser.parse_args()

    setup_style()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, config, checkpoint = load_model(args.imtmn_root, device)
    transform = feature_transform(int(config["data"].get("image_size", 96)))

    results_dir = args.output_root / "lgm_game_prototype" / "results" / "publication_suite"
    cache_dir = args.output_root / "lgm_game_prototype" / "results" / "real_imtmn" / "feature_cache"
    figures_dir = args.output_root / "lgm_game_paper_latex" / "figures"
    tables_dir = args.output_root / "lgm_game_paper_latex" / "tables"
    models_dir = results_dir / "models"
    results_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)

    train_uav_items = collect_university_train(args.data_root, "drone")
    train_sat_items = collect_university_train(args.data_root, "satellite")
    train_uav = as_pack(
        extract_features(
            model,
            "University-1652_train_drone",
            train_uav_items,
            transform,
            cache_dir,
            device,
            args.extract_batch_size,
            args.force_features,
        )
    )
    train_sat = as_pack(
        extract_features(
            model,
            "University-1652_train_satellite",
            train_sat_items,
            transform,
            cache_dir,
            device,
            args.extract_batch_size,
            args.force_features,
        )
    )

    task_packs: dict[str, dict[str, FeaturePack]] = {}
    for task_name, task in build_tasks(args.data_root).items():
        if not task["query_items"] or not task["gallery_items"]:
            continue
        query = as_pack(
            extract_features(
                model,
                f"{task_name}_query",
                task["query_items"],
                transform,
                cache_dir,
                device,
                args.extract_batch_size,
                False,
            )
        )
        gallery = as_pack(
            extract_features(
                model,
                f"{task_name}_gallery",
                task["gallery_items"],
                transform,
                cache_dir,
                device,
                args.extract_batch_size,
                False,
            )
        )
        task_packs[task_name] = {"query": query, "gallery": gallery}

    train_mean_uav = train_uav.features.mean(dim=0)
    train_mean_sat = train_sat.features.mean(dim=0)
    train_mean_all = torch.cat([train_uav.features, train_sat.features], dim=0).mean(dim=0)

    def center_query(task_name: str, pack: FeaturePack) -> FeaturePack:
        if "Satellite $\\rightarrow$ Drone" in task_name:
            return centered_pack(pack, train_mean_sat)
        return centered_pack(pack, train_mean_uav)

    def center_gallery(task_name: str, pack: FeaturePack) -> FeaturePack:
        if "Satellite $\\rightarrow$ Drone" in task_name:
            return centered_pack(pack, train_mean_uav)
        return centered_pack(pack, train_mean_sat)

    baseline_results: dict[str, dict[str, dict]] = {}
    baseline_results["Feature cosine"] = evaluate_pack_method(task_packs, "Feature cosine")
    baseline_results["Domain-centered cosine"] = evaluate_pack_method(
        task_packs,
        "Domain-centered cosine",
        query_transform=center_query,
        gallery_transform=center_gallery,
    )
    baseline_results["CSLS rescoring"] = evaluate_pack_method(task_packs, "CSLS rescoring", scorer="csls")
    baseline_results["Reciprocal graph"] = evaluate_pack_method(task_packs, "Reciprocal graph", scorer="reciprocal")

    heads: dict[str, list[tuple[int, LGMGameLiteHead, dict]]] = {"Projection head": [], "Style-invariant head": []}
    for seed in args.seeds:
        head, info = train_head(
            train_uav,
            train_sat,
            seed=seed,
            epochs=args.epochs,
            batch_classes=args.batch_classes,
            lr=args.lr,
            style_consistency=False,
            device=device,
        )
        torch.save({"model": head.state_dict(), "info": info}, models_dir / f"projection_seed_{seed}.pth")
        heads["Projection head"].append((seed, head, info))

        style_head, style_info = train_head(
            train_uav,
            train_sat,
            seed=seed,
            epochs=args.epochs,
            batch_classes=args.batch_classes,
            lr=args.lr,
            style_consistency=True,
            device=device,
        )
        torch.save({"model": style_head.state_dict(), "info": style_info}, models_dir / f"style_head_seed_{seed}.pth")
        heads["Style-invariant head"].append((seed, style_head, style_info))

    seed_results: dict[str, dict[str, dict[str, dict]]] = {}
    transformed_cache: dict[tuple[str, int, str, str], FeaturePack] = {}
    for variant, seed_heads in heads.items():
        seed_results[variant] = {}
        for seed, head, _ in seed_heads:
            transformed_tasks: dict[str, dict[str, FeaturePack]] = {}
            for task_name, packs in task_packs.items():
                q_key = (variant, seed, task_name, "query")
                g_key = (variant, seed, task_name, "gallery")
                transformed_cache[q_key] = transform_pack(packs["query"], head, device)
                transformed_cache[g_key] = transform_pack(packs["gallery"], head, device)
                transformed_tasks[task_name] = {"query": transformed_cache[q_key], "gallery": transformed_cache[g_key]}
            seed_results[variant][str(seed)] = evaluate_pack_method(transformed_tasks, variant)

    full_seed_results: dict[str, dict[str, dict]] = {}
    for seed, _, _ in heads["Style-invariant head"]:
        transformed_tasks = {
            task_name: {
                "query": transformed_cache[("Style-invariant head", seed, task_name, "query")],
                "gallery": transformed_cache[("Style-invariant head", seed, task_name, "gallery")],
            }
            for task_name in task_packs
        }
        full_seed_results[str(seed)] = evaluate_pack_method(transformed_tasks, "Full LGM-GAME-lite", scorer="reciprocal")

    method_macro_rows: list[dict] = []
    for method, results in baseline_results.items():
        method_macro_rows.append({"Method": method, **macro_metrics(results)})
    for variant in ["Projection head", "Style-invariant head"]:
        macros = [macro_metrics(seed_results[variant][str(seed)]) for seed, _, _ in heads[variant]]
        method_macro_rows.append(
            {
                "Method": variant,
                "Recall@1": float(np.mean([m["Recall@1"] for m in macros])),
                "Recall@5": float(np.mean([m["Recall@5"] for m in macros])),
                "Recall@10": float(np.mean([m["Recall@10"] for m in macros])),
                "mAP": float(np.mean([m["mAP"] for m in macros])),
                "MRR": float(np.mean([m["MRR"] for m in macros])),
                "Eval_Time_s": float(np.mean([m["Eval_Time_s"] for m in macros])),
            }
        )
    full_macros = [macro_metrics(full_seed_results[str(seed)]) for seed, _, _ in heads["Style-invariant head"]]
    method_macro_rows.append(
        {
            "Method": "Full LGM-GAME-lite",
            "Recall@1": float(np.mean([m["Recall@1"] for m in full_macros])),
            "Recall@5": float(np.mean([m["Recall@5"] for m in full_macros])),
            "Recall@10": float(np.mean([m["Recall@10"] for m in full_macros])),
            "mAP": float(np.mean([m["mAP"] for m in full_macros])),
            "MRR": float(np.mean([m["MRR"] for m in full_macros])),
            "Eval_Time_s": float(np.mean([m["Eval_Time_s"] for m in full_macros])),
        }
    )

    write_rows_csv(results_dir / "internal_feature_macro_results.csv", method_macro_rows)
    public_rows = [
        ["CVIM \\cite{cahrs2022}", "63.91", "68.75", "66.47", "68.95"],
        ["Contrastive Loss \\cite{cahrs2022}", "58.49", "63.39", "53.21", "56.88"],
        ["Triplet Loss \\cite{cahrs2022}", "59.53", "64.44", "64.07", "66.28"],
        ["Soft Margin Triplet \\cite{cahrs2022}", "66.65", "71.58", "73.96", "74.79"],
        ["LPN \\cite{lpn2022}", "75.93", "79.14", "86.45", "87.00"],
        ["LPN + CA-HRS \\cite{cahrs2022}", "78.42", "80.96", "89.05", "89.14"],
    ]
    latex_table(
        tables_dir / "publication_baseline_table.tex",
        "Published baseline comparison on University-1652. Values are reported results from public papers and are included as external reference points; they are not produced by the local diagnostic checkpoint.",
        "tab:publication_baselines",
        ["Published method", "D$\\rightarrow$S R@1", "D$\\rightarrow$S AP", "S$\\rightarrow$D R@1", "S$\\rightarrow$D AP"],
        public_rows,
        align="lrrrr",
    )

    ablation_defs = [
        ("Feature baseline", [macro_metrics(baseline_results["Feature cosine"])]),
        ("+ domain centering", [macro_metrics(baseline_results["Domain-centered cosine"])]),
        ("+ CSLS", [macro_metrics(baseline_results["CSLS rescoring"])]),
        ("+ graph consistency", [macro_metrics(baseline_results["Reciprocal graph"])]),
        ("+ trained content head", [macro_metrics(seed_results["Projection head"][str(seed)]) for seed, _, _ in heads["Projection head"]]),
        ("+ style-invariant head", [macro_metrics(seed_results["Style-invariant head"][str(seed)]) for seed, _, _ in heads["Style-invariant head"]]),
        ("Full available model", full_macros),
    ]
    ablation_rows: list[dict] = []
    for name, macros in ablation_defs:
        ablation_rows.append(
            {
                "Variant": name,
                "R@1": mean_std([m["Recall@1"] for m in macros]),
                "R@5": mean_std([m["Recall@5"] for m in macros]),
                "mAP": mean_std([m["mAP"] for m in macros]),
                "R@1_mean": f"{np.mean([m['Recall@1'] for m in macros]):.4f}",
                "mAP_mean": f"{np.mean([m['mAP'] for m in macros]):.4f}",
            }
        )
    write_rows_csv(results_dir / "ablation_macro_results.csv", ablation_rows)
    latex_table(
        tables_dir / "publication_ablation_table.tex",
        "Available-data ablation of the executable LGM-GAME-lite pipeline. Mean and standard deviation are reported over trained seeds when applicable.",
        "tab:publication_ablation",
        ["Variant", "R@1", "R@5", "mAP"],
        [[row["Variant"], row["R@1"], row["R@5"], row["mAP"]] for row in ablation_rows],
        align="lrrr",
    )
    plot_ablation(figures_dir, ablation_rows)

    repeated_rows: list[dict] = []
    for seed, _, info in heads["Style-invariant head"]:
        macro = macro_metrics(full_seed_results[str(seed)])
        repeated_rows.append(
            {
                "Seed": seed,
                "Final_loss": info["history"][-1]["loss"],
                "R@1": macro["Recall@1"],
                "R@5": macro["Recall@5"],
                "mAP": macro["mAP"],
                "MRR": macro["MRR"],
            }
        )
    write_rows_csv(results_dir / "repeated_seed_results.csv", repeated_rows)
    latex_table(
        tables_dir / "publication_repeated_stats_table.tex",
        "Repeated-run statistics for the style-invariant LGM-GAME-lite head with graph consistency.",
        "tab:publication_repeated",
        ["Seed", "Final loss", "R@1", "R@5", "mAP", "MRR"],
        [
            [
                str(row["Seed"]),
                f"{row['Final_loss']:.4f}",
                f"{row['R@1']:.2f}",
                f"{row['R@5']:.2f}",
                f"{row['mAP']:.2f}",
                f"{row['MRR']:.2f}",
            ]
            for row in repeated_rows
        ],
    )

    dim = int(train_uav.features.shape[1])
    head_params = sum(p.numel() for p in heads["Style-invariant head"][0][1].parameters())
    imtmn_params = sum(p.numel() for p in model.parameters())
    total_query_gallery = sum(packs["query"].features.shape[0] * packs["gallery"].features.shape[0] for packs in task_packs.values())
    sim_flops_g = (2.0 * total_query_gallery * dim) / 1e9
    feature_mem_mb = sum(
        (packs["query"].features.numel() + packs["gallery"].features.numel()) * 4.0 / (1024**2)
        for packs in task_packs.values()
    )
    efficiency_rows = [
        {
            "Method": "Feature cosine",
            "Backbone_params_M": imtmn_params / 1e6,
            "Trainable_params_M": 0.0,
            "Similarity_GFLOPs": sim_flops_g,
            "Feature_memory_MB": feature_mem_mb,
            "Mean_eval_time_s": macro_metrics(baseline_results["Feature cosine"])["Eval_Time_s"],
        },
        {
            "Method": "CSLS",
            "Backbone_params_M": imtmn_params / 1e6,
            "Trainable_params_M": 0.0,
            "Similarity_GFLOPs": sim_flops_g,
            "Feature_memory_MB": feature_mem_mb,
            "Mean_eval_time_s": macro_metrics(baseline_results["CSLS rescoring"])["Eval_Time_s"],
        },
        {
            "Method": "LGM-lite",
            "Backbone_params_M": imtmn_params / 1e6,
            "Trainable_params_M": head_params / 1e6,
            "Similarity_GFLOPs": sim_flops_g,
            "Feature_memory_MB": feature_mem_mb,
            "Mean_eval_time_s": float(np.mean([m["Eval_Time_s"] for m in full_macros])),
        },
    ]
    write_rows_csv(results_dir / "efficiency_results.csv", efficiency_rows)
    latex_table(
        tables_dir / "publication_efficiency_table.tex",
        "Efficiency profile on CPU using cached features. Similarity FLOPs are counted for all six full-query ranking tasks.",
        "tab:publication_efficiency",
        ["Method", "Backbone params", "Extra params", "Rank GFLOPs", "Feat. mem.", "Time/task"],
        [
            [
                row["Method"],
                f"{row['Backbone_params_M']:.2f}M",
                f"{row['Trainable_params_M']:.3f}M",
                f"{row['Similarity_GFLOPs']:.2f}",
                f"{row['Feature_memory_MB']:.1f} MB",
                f"{row['Mean_eval_time_s']:.2f}s",
            ]
            for row in efficiency_rows
        ],
    )
    plot_efficiency(figures_dir, efficiency_rows)

    full_seed = heads["Style-invariant head"][0][0]
    full_head = heads["Style-invariant head"][0][1]
    sues_task = "SUES-200 UAV $\\rightarrow$ Satellite"
    sues_query = task_packs[sues_task]["query"]
    sues_gallery = task_packs[sues_task]["gallery"]
    full_gallery = transform_pack(sues_gallery, full_head, device)
    robustness_rows: list[dict] = []
    for tag in ["150", "200", "250", "300"]:
        q_raw = subset_by_tag(sues_query, tag)
        q_full = transform_pack(q_raw, full_head, device)
        raw_m = metrics_from_scores(cosine_scores(q_raw, sues_gallery), q_raw.labels, sues_gallery.labels)
        full_m = metrics_from_scores(reciprocal_scores(q_full, full_gallery), q_full.labels, full_gallery.labels)
        robustness_rows.append(
            {
                "Group": f"SUES {tag}m",
                "Queries": len(q_raw.labels),
                "Raw_R@1": raw_m["Recall@1"],
                "Raw_R@5": raw_m["Recall@5"],
                "Full_R@1": full_m["Recall@1"],
                "Full_R@5": full_m["Recall@5"],
            }
        )
    for mode in ["noise", "dropout", "scale", "mixed"]:
        q_raw = perturb_pack(sues_query, mode, seed=full_seed + 100)
        q_full = transform_pack(q_raw, full_head, device)
        raw_m = metrics_from_scores(cosine_scores(q_raw, sues_gallery), q_raw.labels, sues_gallery.labels)
        full_m = metrics_from_scores(reciprocal_scores(q_full, full_gallery), q_full.labels, full_gallery.labels)
        robustness_rows.append(
            {
                "Group": f"Feature {mode}",
                "Queries": len(q_raw.labels),
                "Raw_R@1": raw_m["Recall@1"],
                "Raw_R@5": raw_m["Recall@5"],
                "Full_R@1": full_m["Recall@1"],
                "Full_R@5": full_m["Recall@5"],
            }
        )
    write_rows_csv(results_dir / "robustness_group_results.csv", robustness_rows)
    latex_table(
        tables_dir / "publication_robustness_table.tex",
        "Robustness grouping on SUES-200 altitude splits and feature-level stress tests. Feature stress is used only because weather/season labels are unavailable in the local datasets.",
        "tab:publication_robustness",
        ["Group", "Queries", "Feature base R@1", "Feature base R@5", "LGM-lite R@1", "LGM-lite R@5"],
        [
            [
                row["Group"],
                str(row["Queries"]),
                f"{row['Raw_R@1']:.2f}",
                f"{row['Raw_R@5']:.2f}",
                f"{row['Full_R@1']:.2f}",
                f"{row['Full_R@5']:.2f}",
            ]
            for row in robustness_rows
        ],
    )
    plot_robustness(figures_dir, robustness_rows)

    train_summary = {
        "seeds": args.seeds,
        "epochs": args.epochs,
        "classes": len(common_labels(train_uav, train_sat)),
        "uav_images": len(train_uav.labels),
        "sat_images": len(train_sat.labels),
    }
    save_training_table(tables_dir, train_summary)

    payload = {
        "note": "Publication experiment suite using cached local real-image features and a trainable LGM-GAME-lite alignment head.",
        "caveat": "Local datasets do not include VLM captions or vector-map alignments; text/map rows should be replaced after those annotations are generated.",
        "device": str(device),
        "checkpoint_epoch": checkpoint.get("epoch"),
        "training": train_summary,
        "baselines": baseline_results,
        "seed_results": seed_results,
        "full_seed_results": full_seed_results,
        "macro": method_macro_rows,
        "ablation": ablation_rows,
        "repeated": repeated_rows,
        "efficiency": efficiency_rows,
        "robustness": robustness_rows,
    }
    (results_dir / "publication_suite_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"results": str(results_dir), "figures": str(figures_dir), "tables": str(tables_dir)}, indent=2))


if __name__ == "__main__":
    main()
