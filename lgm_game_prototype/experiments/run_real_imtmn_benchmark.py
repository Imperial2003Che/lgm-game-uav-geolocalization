from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn.functional as F
import yaml
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from tqdm import tqdm


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
PALETTE = {
    "navy": "#233142",
    "blue": "#3b6f8f",
    "green": "#55a18a",
    "gold": "#c49a42",
    "red": "#c15c54",
    "slate": "#8d99ae",
    "grid": "#d5dbe3",
}


@dataclass(frozen=True)
class ImageItem:
    path: str
    label: str
    tag: str = ""


class ImageListDataset(Dataset):
    def __init__(self, items: list[ImageItem], transform):
        self.items = items
        self.transform = transform

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> dict:
        item = self.items[index]
        image = Image.open(item.path).convert("RGB")
        return {
            "image": self.transform(image),
            "label": item.label,
            "path": item.path,
            "tag": item.tag,
        }


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "DejaVu Serif"],
            "axes.edgecolor": PALETTE["navy"],
            "axes.labelcolor": PALETTE["navy"],
            "xtick.color": PALETTE["navy"],
            "ytick.color": PALETTE["navy"],
            "text.color": PALETTE["navy"],
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 140,
            "savefig.dpi": 320,
        }
    )


def collect_university(root: Path, split_dir: str) -> list[ImageItem]:
    base = root / "University-1652" / "test" / split_dir
    items: list[ImageItem] = []
    if not base.exists():
        return items
    for path in sorted(base.rglob("*")):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            rel = path.relative_to(base).parts
            if len(rel) >= 2:
                items.append(ImageItem(str(path), rel[0], split_dir))
    return items


def collect_sues_drone(root: Path, altitude: str | None = None) -> list[ImageItem]:
    base = root / "SUES-200" / "drone_view_512"
    items: list[ImageItem] = []
    if not base.exists():
        return items
    for path in sorted(base.rglob("*")):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            rel = path.relative_to(base).parts
            if len(rel) >= 3 and (altitude is None or rel[1] == altitude):
                items.append(ImageItem(str(path), rel[0], rel[1]))
    return items


def collect_sues_sat(root: Path) -> list[ImageItem]:
    base = root / "SUES-200" / "satellite-view"
    items: list[ImageItem] = []
    if not base.exists():
        return items
    for path in sorted(base.rglob("*")):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            rel = path.relative_to(base).parts
            if len(rel) >= 2:
                items.append(ImageItem(str(path), rel[0], "satellite"))
    return items


def load_model(imtmn_root: Path, device: torch.device):
    sys.path.insert(0, str(imtmn_root))
    from src.models.imtmn import IMTMN  # noqa: WPS433

    config = yaml.safe_load((imtmn_root / "config.yaml").read_text(encoding="utf-8"))
    cfg = config["model"]
    model = IMTMN(
        d_model=cfg["d_model"],
        num_heads=cfg["num_heads"],
        num_layers=cfg["num_layers"],
        topk_attn=cfg["topk_attn"],
        topk_match=cfg["topk_match"],
        sinkhorn_iters=cfg["sinkhorn_iters"],
        ffn_dim=cfg["ffn_dim"],
        dropout=cfg["dropout"],
        use_sparse=cfg.get("use_sparse", True),
        transformer_size=cfg.get("transformer_size", 8),
        pretrained_backbone=False,
    ).to(device)
    checkpoint = torch.load(imtmn_root / "checkpoints" / "best_model.pth", map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model"])
    model.eval()
    return model, config, checkpoint


def feature_transform(size: int):
    return transforms.Compose(
        [
            transforms.Resize((size, size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )


def cache_key(name: str) -> str:
    return name.replace("/", "_").replace("\\", "_").replace(" ", "_")


def extract_features(
    model,
    name: str,
    items: list[ImageItem],
    transform,
    cache_dir: Path,
    device: torch.device,
    batch_size: int,
    force: bool = False,
) -> dict:
    cache_path = cache_dir / f"{cache_key(name)}.pt"
    if cache_path.exists() and not force:
        return torch.load(cache_path, map_location="cpu", weights_only=False)

    dataset = ImageListDataset(items, transform)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    features = []
    labels: list[str] = []
    paths: list[str] = []
    tags: list[str] = []
    with torch.no_grad():
        for batch in tqdm(loader, desc=f"Extract {name}"):
            feat = model.extract_global_feature(batch["image"].to(device))
            features.append(feat.detach().cpu())
            labels.extend(batch["label"])
            paths.extend(batch["path"])
            tags.extend(batch["tag"])
    data = {
        "features": torch.cat(features, dim=0) if features else torch.empty(0),
        "labels": labels,
        "paths": paths,
        "tags": tags,
        "count": len(labels),
    }
    cache_dir.mkdir(parents=True, exist_ok=True)
    torch.save(data, cache_path)
    return data


def encode_labels(labels: list[str]) -> tuple[torch.Tensor, dict[str, int]]:
    mapping = {label: idx for idx, label in enumerate(sorted(set(labels)))}
    return torch.tensor([mapping[label] for label in labels], dtype=torch.long), mapping


def retrieval_metrics(
    query: dict,
    gallery: dict,
    ks: tuple[int, ...] = (1, 5, 10, 20),
    chunk_size: int = 1024,
) -> tuple[dict, list[int], list[list[int]]]:
    q = F.normalize(query["features"].float(), dim=1)
    g = F.normalize(gallery["features"].float(), dim=1)
    all_labels = list(query["labels"]) + list(gallery["labels"])
    label_map = {label: idx for idx, label in enumerate(sorted(set(all_labels)))}
    q_ids = torch.tensor([label_map[label] for label in query["labels"]], dtype=torch.long)
    g_ids = torch.tensor([label_map[label] for label in gallery["labels"]], dtype=torch.long)

    recalls = {k: [] for k in ks}
    cmc_hits = {k: [] for k in range(1, max(ks) + 1)}
    aps: list[float] = []
    rrs: list[float] = []
    best_ranks: list[int] = []
    top_indices: list[list[int]] = []

    for start in tqdm(range(0, q.shape[0], chunk_size), desc="Rank gallery"):
        end = min(start + chunk_size, q.shape[0])
        sim = q[start:end] @ g.t()
        sorted_idx = sim.argsort(dim=1, descending=True)
        for local_idx in range(sorted_idx.shape[0]):
            qi = start + local_idx
            ranked = sorted_idx[local_idx]
            ranked_labels = g_ids[ranked]
            positives = (ranked_labels == q_ids[qi]).nonzero(as_tuple=False).flatten()
            if positives.numel() == 0:
                continue
            ranks = positives.float() + 1.0
            best_rank = int(ranks[0].item())
            best_ranks.append(best_rank)
            rrs.append(1.0 / best_rank)
            aps.append((torch.arange(1, ranks.numel() + 1, dtype=torch.float32) / ranks).mean().item())
            for k in ks:
                recalls[k].append(1.0 if best_rank <= k else 0.0)
            for k in cmc_hits:
                cmc_hits[k].append(1.0 if best_rank <= k else 0.0)
            if len(top_indices) < 16:
                top_indices.append([int(x) for x in ranked[:5].tolist()])

    n = max(1, len(best_ranks))
    metrics = {
        "Num_Queries": len(query["labels"]),
        "Num_Gallery": len(gallery["labels"]),
        "Num_Classes_Query": len(set(query["labels"])),
        "Num_Classes_Gallery": len(set(gallery["labels"])),
        "mAP": float(np.mean(aps) * 100.0),
        "MRR": float(np.mean(rrs) * 100.0),
        "Median_Rank": float(np.median(best_ranks)),
        "Mean_Rank": float(np.mean(best_ranks)),
    }
    for k in ks:
        metrics[f"Recall@{k}"] = float(np.mean(recalls[k]) * 100.0)
    metrics["CMC"] = {str(k): float(np.mean(cmc_hits[k]) * 100.0) for k in cmc_hits}
    return metrics, best_ranks, top_indices


def save_csv(path: Path, rows: list[dict]) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def pct(value: float) -> str:
    return f"{value:.2f}"


def write_latex_table(path: Path, rows: list[dict]) -> None:
    short_names = {
        "University-1652 Drone $\\rightarrow$ Satellite": "U-1652 D$\\rightarrow$S",
        "University-1652 Satellite $\\rightarrow$ Drone": "U-1652 S$\\rightarrow$D",
        "University-1652 Street $\\rightarrow$ Satellite": "U-1652 G$\\rightarrow$S",
        "SUES-200 UAV $\\rightarrow$ Satellite": "SUES UAV$\\rightarrow$S",
        "SUES-200 UAV-150m $\\rightarrow$ Satellite": "SUES 150m$\\rightarrow$S",
        "SUES-200 UAV-300m $\\rightarrow$ Satellite": "SUES 300m$\\rightarrow$S",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "\\begin{table*}[t]",
        "\\centering",
        "\\caption{Real-data retrieval evaluation using the available local feature checkpoint on University-1652 and SUES-200 datasets.}",
        "\\label{tab:real_retrieval}",
        "\\begin{tabular}{lrrrrrrr}",
        "\\toprule",
        "Task & Queries & Gallery & R@1 & R@5 & R@10 & mAP & MRR \\\\",
        "\\midrule",
    ]
    for row in rows:
        task = short_names.get(row["Task"], row["Task"])
        lines.append(
            f"{task} & {row['Num_Queries']} & {row['Num_Gallery']} & "
            f"{pct(row['Recall@1'])} & {pct(row['Recall@5'])} & {pct(row['Recall@10'])} & "
            f"{pct(row['mAP'])} & {pct(row['MRR'])} \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table*}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def save_figure(fig: plt.Figure, figures_dir: Path, name: str) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(figures_dir / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(figures_dir / f"{name}.png", bbox_inches="tight")
    plt.close(fig)


def plot_metrics(rows: list[dict], figures_dir: Path) -> None:
    task_labels = [
        row["Task"]
        .replace("University-1652 ", "U-1652 ")
        .replace("SUES-200 ", "SUES ")
        .replace("$\\rightarrow$", "->")
        for row in rows
    ]
    metrics = ["Recall@1", "Recall@5", "Recall@10", "mAP"]
    colors = [PALETTE["blue"], PALETTE["green"], PALETTE["gold"], PALETTE["red"]]
    y = np.arange(len(rows))
    height = 0.17
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    for idx, (metric, color) in enumerate(zip(metrics, colors)):
        values = [row[metric] for row in rows]
        ax.barh(y + (idx - 1.5) * height, values, height, color=color, label=metric)
    ax.set_xlabel("Score (%)")
    ax.set_xlim(0, max(row["Recall@20"] for row in rows) * 1.08)
    ax.set_yticks(y)
    ax.set_yticklabels(task_labels, fontsize=7)
    ax.invert_yaxis()
    ax.grid(axis="x", color=PALETTE["grid"], linewidth=0.7)
    ax.legend(ncol=4, frameon=False, loc="lower right", fontsize=8)
    ax.set_title("Real-data retrieval metrics", fontsize=10)
    save_figure(fig, figures_dir, "real_retrieval_metrics")


def plot_cmc(results: dict, figures_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.8, 3.1))
    colors = [PALETTE["blue"], PALETTE["green"], PALETTE["gold"], PALETTE["red"], PALETTE["slate"], PALETTE["navy"]]
    for idx, (name, metrics) in enumerate(results.items()):
        cmc = metrics["CMC"]
        ks = [int(k) for k in sorted(cmc, key=lambda item: int(item))]
        vals = [cmc[str(k)] for k in ks]
        label = name.replace("University-1652 ", "U-1652 ").replace("SUES-200 ", "SUES ")
        ax.plot(ks, vals, marker="o", lw=1.5, ms=3.5, color=colors[idx % len(colors)], label=label)
    ax.set_xlabel("Rank K")
    ax.set_ylabel("Recall@K (%)")
    ax.set_ylim(0, 105)
    ax.set_xticks([1, 5, 10, 15, 20])
    ax.grid(True, color=PALETTE["grid"], linewidth=0.7)
    ax.legend(frameon=False, fontsize=7, ncol=2)
    ax.set_title("CMC curves on real datasets", fontsize=10)
    save_figure(fig, figures_dir, "real_cmc_curves")


def add_thumb(ax, image_path: str, title: str, border: str) -> None:
    image = Image.open(image_path).convert("RGB")
    ax.imshow(image)
    ax.set_title(title, fontsize=7)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(2.0)
        spine.set_edgecolor(border)


def plot_retrieval_examples(
    task_data: dict,
    top_indices_by_task: dict[str, list[list[int]]],
    figures_dir: Path,
) -> None:
    selected = [name for name in ["University-1652 Drone $\\rightarrow$ Satellite", "SUES-200 UAV $\\rightarrow$ Satellite"] if name in task_data]
    if not selected:
        return
    fig, axes = plt.subplots(len(selected), 6, figsize=(7.2, 2.2 * len(selected)))
    if len(selected) == 1:
        axes = np.array([axes])
    for row_idx, name in enumerate(selected):
        query = task_data[name]["query"]
        gallery = task_data[name]["gallery"]
        top_indices = top_indices_by_task[name][0]
        q_path = query["paths"][0]
        q_label = query["labels"][0]
        add_thumb(axes[row_idx, 0], q_path, f"{name}\nQuery: {q_label}", PALETTE["navy"])
        for col_idx, gallery_idx in enumerate(top_indices, start=1):
            g_path = gallery["paths"][gallery_idx]
            g_label = gallery["labels"][gallery_idx]
            ok = g_label == q_label
            add_thumb(
                axes[row_idx, col_idx],
                g_path,
                f"Top-{col_idx}: {g_label}",
                PALETTE["green"] if ok else PALETTE["red"],
            )
    save_figure(fig, figures_dir, "real_retrieval_examples")


def plot_polished_framework(figures_dir: Path) -> None:
    from matplotlib import patches

    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    lanes = [
        ("Visual stream", 0.80, PALETTE["blue"], "#eaf2f7"),
        ("Language stream", 0.56, PALETTE["green"], "#edf7f3"),
        ("Map / geometry stream", 0.32, PALETTE["gold"], "#f8f2df"),
    ]
    for lane, y, color, fill in lanes:
        ax.add_patch(
            patches.FancyBboxPatch(
                (0.01, y - 0.115),
                0.78,
                0.20,
                boxstyle="round,pad=0.004,rounding_size=0.012",
                facecolor=fill,
                edgecolor="none",
                zorder=0,
            )
        )
        ax.text(0.02, y + 0.055, lane, fontsize=8, fontweight="bold", color=color)

    def box(x, y, w, h, text, color, text_color="white"):
        rect = patches.FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.012,rounding_size=0.018",
            facecolor=color,
            edgecolor="white",
            linewidth=1.1,
        )
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=7.8, color=text_color)

    box(0.16, 0.76, 0.16, 0.10, "UAV query\npatch tokens", PALETTE["blue"])
    box(0.16, 0.64, 0.16, 0.10, "Satellite gallery\npatch tokens", PALETTE["blue"])
    box(0.38, 0.70, 0.17, 0.11, "Shared encoder\nCNN/FPN or ViT", "#39546f")
    box(0.64, 0.70, 0.18, 0.11, "Sparse cross-view\nattention", PALETTE["navy"])

    box(0.16, 0.50, 0.16, 0.10, "VLM captions\nscene phrases", PALETTE["green"])
    box(0.38, 0.50, 0.17, 0.10, "Content anchors\nstyle prompts", "#458a78")
    box(0.64, 0.50, 0.18, 0.10, "Text-style\nattention bias", "#4f9f86")

    box(0.16, 0.26, 0.16, 0.10, "Vector map\nroads/buildings", PALETTE["gold"], text_color="white")
    box(0.38, 0.26, 0.17, 0.10, "Topology tokens\nspatial priors", "#b58b32")
    box(0.64, 0.26, 0.18, 0.10, "Geometric + map\ncompatibility", "#a77825")

    box(0.84, 0.60, 0.13, 0.10, "Sinkhorn\nOT matching", PALETTE["red"])
    box(0.84, 0.42, 0.13, 0.10, "Graph\nverification", "#de8064")
    box(0.84, 0.24, 0.13, 0.10, "Ranked region\n+ matches", "#6c7a89")

    arrows = [
        ((0.32, 0.81), (0.38, 0.76)),
        ((0.32, 0.69), (0.38, 0.75)),
        ((0.55, 0.755), (0.64, 0.755)),
        ((0.32, 0.55), (0.38, 0.55)),
        ((0.55, 0.55), (0.64, 0.55)),
        ((0.32, 0.31), (0.38, 0.31)),
        ((0.55, 0.31), (0.64, 0.31)),
        ((0.73, 0.70), (0.73, 0.60)),
        ((0.73, 0.50), (0.73, 0.37)),
        ((0.82, 0.755), (0.84, 0.65)),
        ((0.82, 0.55), (0.84, 0.62)),
        ((0.82, 0.31), (0.84, 0.48)),
        ((0.905, 0.60), (0.905, 0.52)),
        ((0.905, 0.42), (0.905, 0.34)),
    ]
    for start, end in arrows:
        ax.annotate("", xy=end, xytext=start, arrowprops=dict(arrowstyle="-|>", color=PALETTE["navy"], lw=1.0))

    ax.text(
        0.50,
        0.08,
        "LGM-GAME fuses visual, language, and map evidence before optimal-transport matching and candidate-level graph filtering.",
        ha="center",
        fontsize=8,
    )
    save_figure(fig, figures_dir, "framework_overview")


def build_tasks(data_root: Path) -> dict[str, dict]:
    univ_gallery_sat = collect_university(data_root, "gallery_satellite")
    return {
        "University-1652 Drone $\\rightarrow$ Satellite": {
            "query_items": collect_university(data_root, "query_drone"),
            "gallery_items": univ_gallery_sat,
        },
        "University-1652 Satellite $\\rightarrow$ Drone": {
            "query_items": collect_university(data_root, "query_satellite"),
            "gallery_items": collect_university(data_root, "gallery_drone"),
        },
        "University-1652 Street $\\rightarrow$ Satellite": {
            "query_items": collect_university(data_root, "query_street"),
            "gallery_items": univ_gallery_sat,
        },
        "SUES-200 UAV $\\rightarrow$ Satellite": {
            "query_items": collect_sues_drone(data_root),
            "gallery_items": collect_sues_sat(data_root),
        },
        "SUES-200 UAV-150m $\\rightarrow$ Satellite": {
            "query_items": collect_sues_drone(data_root, "150"),
            "gallery_items": collect_sues_sat(data_root),
        },
        "SUES-200 UAV-300m $\\rightarrow$ Satellite": {
            "query_items": collect_sues_drone(data_root, "300"),
            "gallery_items": collect_sues_sat(data_root),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run real IMTMN retrieval benchmarks.")
    parser.add_argument("--imtmn-root", type=Path, default=Path(r"C:\Programs\IMTMN"))
    parser.add_argument("--data-root", type=Path, default=Path(r"C:\Programs\IMTMN\datasets"))
    parser.add_argument("--output-root", type=Path, default=Path(r"C:\Programs\lgm-game-uav-geolocalization"))
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--chunk-size", type=int, default=1024)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    setup_style()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, config, checkpoint = load_model(args.imtmn_root, device)
    transform = feature_transform(int(config["data"].get("image_size", 96)))
    results_dir = args.output_root / "lgm_game_prototype" / "results" / "real_imtmn"
    cache_dir = results_dir / "feature_cache"
    figures_dir = args.output_root / "lgm_game_paper_latex" / "figures"
    tables_dir = args.output_root / "lgm_game_paper_latex" / "tables"

    task_defs = build_tasks(args.data_root)
    task_data: dict[str, dict] = {}
    for task_name, task in task_defs.items():
        if not task["query_items"] or not task["gallery_items"]:
            continue
        query = extract_features(
            model,
            f"{task_name}_query",
            task["query_items"],
            transform,
            cache_dir,
            device,
            args.batch_size,
            args.force,
        )
        gallery = extract_features(
            model,
            f"{task_name}_gallery",
            task["gallery_items"],
            transform,
            cache_dir,
            device,
            args.batch_size,
            args.force,
        )
        task_data[task_name] = {"query": query, "gallery": gallery}

    results: dict[str, dict] = {}
    rows: list[dict] = []
    top_indices_by_task: dict[str, list[list[int]]] = {}
    for task_name, data in task_data.items():
        metrics, _, top_indices = retrieval_metrics(
            data["query"], data["gallery"], chunk_size=args.chunk_size
        )
        results[task_name] = metrics
        top_indices_by_task[task_name] = top_indices
        row = {"Task": task_name, **{key: value for key, value in metrics.items() if key != "CMC"}}
        rows.append(row)

    results_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "note": "Real image retrieval evaluation using IMTMN checkpoint.",
        "checkpoint_epoch": checkpoint.get("epoch"),
        "device": str(device),
        "tasks": results,
    }
    (results_dir / "real_retrieval_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    save_csv(results_dir / "real_retrieval_results.csv", rows)
    write_latex_table(tables_dir / "real_retrieval_table.tex", rows)
    plot_metrics(rows, figures_dir)
    plot_cmc(results, figures_dir)
    plot_retrieval_examples(task_data, top_indices_by_task, figures_dir)
    plot_polished_framework(figures_dir)
    print(json.dumps({"results": str(results_dir), "figures": str(figures_dir), "tables": str(tables_dir)}, indent=2))


if __name__ == "__main__":
    main()
