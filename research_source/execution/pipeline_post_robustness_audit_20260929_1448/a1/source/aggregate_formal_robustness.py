"""Strict four-run aggregation and publication plotting for robustness results.

No value is aggregated across official tasks.  Every CSV row, LaTeX table, and
figure remains task-specific.  The CLI refuses to emit outputs unless all four
University/SUES x visual/full robustness trees pass the complete manifest,
artifact, per-query, source, and protocol gates.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


EXPERIMENTS_DIR = Path(__file__).resolve().parent
if str(EXPERIMENTS_DIR) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS_DIR))

import formal_robustness_common as common  # noqa: E402
import run_image_level_robustness as evaluator  # noqa: E402


PLOT_METRICS = ("r_at_1", "official_trapezoid_mAP")
METRIC_LABELS = {
    "r_at_1": "Recall@1",
    "r_at_5": "Recall@5",
    "r_at_10": "Recall@10",
    "r_at_20": "Recall@20",
    "official_trapezoid_mAP": "Official trapezoidal mAP",
    "MRR": "MRR",
}
VARIANT_LABELS = {
    "visual": "Visual",
    "full": "Full",
}
VARIANT_STYLE = {
    "visual": {
        "color": "#6B7280",
        "linestyle": "--",
        "marker": "o",
    },
    "full": {
        "color": "#1769AA",
        "linestyle": "-",
        "marker": "s",
    },
}
CORRUPTION_LABELS = {
    "gaussian_noise": "Gaussian noise",
    "gaussian_blur": "Gaussian blur",
    "brightness": "Brightness",
    "contrast": "Contrast",
    "center_occlusion": "Center occlusion",
    "rotation": "Rotation",
}
TASK_LABELS = {
    "university1652_drone_to_satellite": "University-1652: drone to satellite",
    "university1652_satellite_to_drone": "University-1652: satellite to drone",
    "university1652_street_to_satellite": "University-1652: street to satellite",
    "sues200_uav_150m_to_satellite": "SUES-200: 150 m UAV to satellite",
    "sues200_satellite_to_uav_150m": "SUES-200: satellite to 150 m UAV",
    "sues200_uav_200m_to_satellite": "SUES-200: 200 m UAV to satellite",
    "sues200_satellite_to_uav_200m": "SUES-200: satellite to 200 m UAV",
    "sues200_uav_250m_to_satellite": "SUES-200: 250 m UAV to satellite",
    "sues200_satellite_to_uav_250m": "SUES-200: satellite to 250 m UAV",
    "sues200_uav_300m_to_satellite": "SUES-200: 300 m UAV to satellite",
    "sues200_satellite_to_uav_300m": "SUES-200: satellite to 300 m UAV",
}

FIGURE_CONTRACT = {
    "core_conclusion": (
        "For each official task separately, quantify how much clean retrieval "
        "performance the visual and full models retain as six image corruptions "
        "increase through five frozen severities."
    ),
    "archetype": "quantitative grid",
    "backend": "Python/matplotlib only",
    "target": "double-column high-impact-journal figure",
    "final_size_mm": {"width": 183, "height": 132},
    "panel_map": (
        "Six panels map one-to-one to the six frozen corruptions; each panel "
        "contains only visual and full trajectories for one task and one metric."
    ),
    "evidence_hierarchy": {
        "hero": "performance retained from each variant's own clean baseline",
        "validation": "absolute clean/corrupted metrics in task-separated source data",
        "controls": "fixed seed-1 checkpoint, complete official queries, clean full gallery",
    },
    "statistics": (
        "Descriptive seed-1 robustness curves only; no error bars or inferential "
        "statistics are fabricated."
    ),
    "reviewer_risks": (
        "No task macro-average, no truncated y-axis, no clean-evidence reuse for "
        "corrupted full queries, and source CSV beside every figure."
    ),
}


def configure_matplotlib() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "font.size": 7,
            "axes.titlesize": 7,
            "axes.labelsize": 7,
            "xtick.labelsize": 6,
            "ytick.labelsize": 6,
            "legend.fontsize": 7,
            "axes.linewidth": 0.7,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "legend.frameon": False,
            "svg.fonttype": "none",
            "svg.hashsalt": "lgm-game-formal-robustness",
            "pdf.fonttype": 42,
            "savefig.facecolor": "white",
            "figure.facecolor": "white",
        }
    )


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def atomic_csv(
    path: Path,
    fieldnames: Sequence[str],
    rows: Sequence[Mapping[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in fieldnames})
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _close_enough(first: float, second: float, tolerance: float = 1e-10) -> bool:
    return math.isclose(first, second, rel_tol=tolerance, abs_tol=tolerance)


def flatten_validations(
    validations: Sequence[common.RobustnessValidation],
) -> list[dict[str, Any]]:
    """Create one row per dataset/variant/task/corruption/severity/metric."""

    rows: list[dict[str, Any]] = []
    for validation in validations:
        if not validation.complete:
            raise RuntimeError(
                f"Cannot flatten incomplete {validation.spec.identifier}: "
                f"{validation.issues[:5]}"
            )
        clean_results = validation.clean_metrics["results"]
        checkpoint = validation.manifest["checkpoint"]
        immutable = validation.run_config["immutable_config"]
        evaluator_sha = immutable["sources"]["robustness_evaluator"]["sha256"]
        protocol_sha = immutable["sources"]["frozen_protocol"]["sha256"]
        for condition in common.expected_condition_payloads(evaluator):
            corruption = str(condition["name"])
            severity = int(condition["severity_index"])
            metrics_payload = validation.condition_metrics[(corruption, severity)]
            results = metrics_payload["results"]
            degradation = metrics_payload["degradation_vs_clean"]
            for task in sorted(results):
                clean_row = clean_results[task]
                corrupted_row = results[task]
                for metric in common.REQUIRED_METRICS:
                    clean = float(clean_row[metric])
                    corrupted = float(corrupted_row[metric])
                    absolute_drop = clean - corrupted
                    relative_drop = absolute_drop / clean if clean != 0.0 else None
                    declared = degradation[task][metric]
                    checks = (
                        (float(declared["clean"]), clean),
                        (float(declared["corrupted"]), corrupted),
                        (
                            float(declared["absolute_drop_fraction"]),
                            absolute_drop,
                        ),
                        (
                            float(declared["percentage_point_drop"]),
                            100.0 * absolute_drop,
                        ),
                    )
                    if any(not _close_enough(a, b) for a, b in checks):
                        raise RuntimeError(
                            f"Degradation arithmetic mismatch for "
                            f"{validation.spec.identifier}/{task}/{corruption}/"
                            f"{severity}/{metric}."
                        )
                    declared_relative = declared["relative_drop_fraction"]
                    if relative_drop is None:
                        if declared_relative is not None:
                            raise RuntimeError("Undefined relative drop was materialized.")
                    elif not _close_enough(
                        float(declared_relative), relative_drop
                    ):
                        raise RuntimeError("Relative-drop arithmetic mismatch.")
                    rows.append(
                        {
                            "dataset": validation.spec.dataset,
                            "variant": validation.spec.variant,
                            "seed": 1,
                            "task": task,
                            "queries": int(corrupted_row["queries"]),
                            "gallery": int(corrupted_row["gallery"]),
                            "corruption": corruption,
                            "corruption_display": condition["display_name"],
                            "severity_index": severity,
                            "parameter": condition["parameter"],
                            "value": float(condition["value"]),
                            "units": condition["units"],
                            "metric": metric,
                            "clean_fraction": clean,
                            "corrupted_fraction": corrupted,
                            "absolute_drop_fraction": absolute_drop,
                            "percentage_point_drop": 100.0 * absolute_drop,
                            "relative_drop_fraction": relative_drop,
                            "relative_drop_percent": (
                                100.0 * relative_drop
                                if relative_drop is not None
                                else None
                            ),
                            "retained_percent_of_clean": (
                                100.0 * corrupted / clean
                                if clean != 0.0
                                else None
                            ),
                            "checkpoint_sha256": checkpoint[
                                "checkpoint_sha256"
                            ],
                            "robustness_run_config_sha256": validation.manifest[
                                "run_config_sha256"
                            ],
                            "evaluator_sha256": evaluator_sha,
                            "frozen_protocol_sha256": protocol_sha,
                        }
                    )
    expected_rows = sum(
        len(common.OFFICIAL_TASK_SCALE[validation.spec.dataset])
        * common.EXPECTED_CONDITION_COUNT
        * len(common.REQUIRED_METRICS)
        for validation in validations
    )
    if len(rows) != expected_rows:
        raise RuntimeError(
            f"Flattened {len(rows)} rows; complete registry requires {expected_rows}."
        )
    return rows


def nested_json_payload(
    validations: Sequence[common.RobustnessValidation],
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    nested: dict[str, Any] = {}
    for validation in validations:
        dataset_node = nested.setdefault(validation.spec.dataset, {})
        variant_node = dataset_node.setdefault(validation.spec.variant, {})
        for task, metrics in validation.clean_metrics["results"].items():
            variant_node.setdefault(task, {})["clean"] = metrics
            variant_node[task]["corruptions"] = {}
        for (corruption, severity), payload in sorted(
            validation.condition_metrics.items()
        ):
            for task, metrics in payload["results"].items():
                corruption_node = (
                    variant_node[task]["corruptions"]
                    .setdefault(corruption, {})
                )
                corruption_node[str(severity)] = {
                    "metrics": metrics,
                    "degradation_vs_clean": payload[
                        "degradation_vs_clean"
                    ][task],
                }
    return {
        "schema_version": common.SCHEMA_VERSION,
        "task_aggregation_used": False,
        "official_tasks_remain_separate": True,
        "run_count": len(validations),
        "flat_row_count": len(rows),
        "results": nested,
    }


def latex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(character, character) for character in value)


def write_task_latex(
    rows: Sequence[Mapping[str, Any]],
    output_dir: Path,
    metric: str,
) -> Path:
    selected = [row for row in rows if row["metric"] == metric]
    tasks = sorted({str(row["task"]) for row in selected})
    lines = [
        "% Auto-generated from four strictly validated formal robustness runs.",
        "% Requires \\usepackage{booktabs}. Values are percentages.",
        "",
    ]
    for task in tasks:
        task_rows = [row for row in selected if row["task"] == task]
        dataset_values = {str(row["dataset"]) for row in task_rows}
        if len(dataset_values) != 1:
            raise RuntimeError(f"Task {task} spans multiple datasets.")
        lines.extend(
            [
                r"\begin{table*}[t]",
                r"\centering",
                (
                    r"\caption{Task-separated image-level robustness for "
                    + latex_escape(TASK_LABELS.get(task, task))
                    + " using "
                    + latex_escape(METRIC_LABELS[metric])
                    + r". Clean is the uncorrupted baseline; S1--S5 follow "
                    r"the frozen severity order.}"
                ),
                r"\setlength{\tabcolsep}{4pt}",
                r"\begin{tabular}{llrrrrrr}",
                r"\toprule",
                r"Variant & Corruption & Clean & S1 & S2 & S3 & S4 & S5 \\",
                r"\midrule",
            ]
        )
        for variant in common.VARIANTS:
            for corruption_spec in evaluator.CORRUPTION_SPECS:
                group = sorted(
                    (
                        row
                        for row in task_rows
                        if row["variant"] == variant
                        and row["corruption"] == corruption_spec.name
                    ),
                    key=lambda row: int(row["severity_index"]),
                )
                if len(group) != 5:
                    raise RuntimeError(
                        f"Missing LaTeX cells for {task}/{variant}/"
                        f"{corruption_spec.name}/{metric}."
                    )
                values = [100.0 * float(row["corrupted_fraction"]) for row in group]
                clean = 100.0 * float(group[0]["clean_fraction"])
                lines.append(
                    "{} & {} & {:.2f} & {} \\\\".format(
                        latex_escape(VARIANT_LABELS[variant]),
                        latex_escape(
                            CORRUPTION_LABELS[corruption_spec.name]
                        ),
                        clean,
                        " & ".join(f"{value:.2f}" for value in values),
                    )
                )
            if variant != common.VARIANTS[-1]:
                lines.append(r"\addlinespace")
        lines.extend(
            [
                r"\bottomrule",
                r"\end{tabular}",
                (
                    r"\label{tab:robustness-"
                    + slug(task)
                    + "-"
                    + slug(metric)
                    + "}"
                ),
                r"\end{table*}",
                "",
            ]
        )
    path = output_dir / f"robustness_{slug(metric)}_task_tables.tex"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path


def _format_parameter_values(
    rows: Sequence[Mapping[str, Any]],
) -> str:
    parameter = str(rows[0]["parameter"])
    values = [float(row["value"]) for row in rows]
    compact = ", ".join(f"{value:g}" for value in values)
    labels = {
        "standard_deviation": r"$\sigma$",
        "radius": "radius",
        "factor": "factor",
        "area_fraction": "area",
        "magnitude": "angle",
    }
    return f"{labels.get(parameter, parameter)}: {compact}"


def figure_source_rows(
    rows: Sequence[Mapping[str, Any]],
    dataset: str,
    task: str,
    metric: str,
) -> list[dict[str, Any]]:
    selected = [
        dict(row)
        for row in rows
        if row["dataset"] == dataset
        and row["task"] == task
        and row["metric"] == metric
    ]
    expected = len(common.VARIANTS) * common.EXPECTED_CONDITION_COUNT
    if len(selected) != expected:
        raise RuntimeError(
            f"Figure source for {task}/{metric} has {len(selected)} rows; "
            f"expected {expected}."
        )
    return sorted(
        selected,
        key=lambda row: (
            common.VARIANTS.index(str(row["variant"])),
            [spec.name for spec in evaluator.CORRUPTION_SPECS].index(
                str(row["corruption"])
            ),
            int(row["severity_index"]),
        ),
    )


def plot_task_metric(
    source_rows: Sequence[Mapping[str, Any]],
    output_stem: Path,
    *,
    dataset: str,
    task: str,
    metric: str,
    dpi: int,
) -> dict[str, Path]:
    """Render one task/metric as a six-panel severity-retention grid."""

    configure_matplotlib()
    width_inches = FIGURE_CONTRACT["final_size_mm"]["width"] / 25.4
    height_inches = FIGURE_CONTRACT["final_size_mm"]["height"] / 25.4
    fig, axes = plt.subplots(
        2,
        3,
        figsize=(width_inches, height_inches),
        sharey=True,
        constrained_layout=False,
    )
    fig.subplots_adjust(
        left=0.105,
        right=0.985,
        bottom=0.115,
        top=0.805,
        wspace=0.19,
        hspace=0.43,
    )
    all_retention = [
        float(row["retained_percent_of_clean"])
        for row in source_rows
        if row["retained_percent_of_clean"] is not None
    ]
    if len(all_retention) != len(source_rows):
        raise RuntimeError(
            f"Cannot plot retention for zero-clean metric: {task}/{metric}."
        )
    y_max = max(110.0, 10.0 * math.ceil(max(all_retention) * 1.05 / 10.0))
    panel_letters = "abcdef"
    for panel_index, (axis, corruption_spec) in enumerate(
        zip(axes.flat, evaluator.CORRUPTION_SPECS)
    ):
        panel_rows = [
            row
            for row in source_rows
            if row["corruption"] == corruption_spec.name
        ]
        for variant in common.VARIANTS:
            variant_rows = sorted(
                (row for row in panel_rows if row["variant"] == variant),
                key=lambda row: int(row["severity_index"]),
            )
            if len(variant_rows) != 5:
                raise RuntimeError(
                    f"Plot source is incomplete for {task}/{metric}/"
                    f"{corruption_spec.name}/{variant}."
                )
            y_values = [100.0] + [
                float(row["retained_percent_of_clean"])
                for row in variant_rows
            ]
            style = VARIANT_STYLE[variant]
            axis.plot(
                np.arange(6),
                y_values,
                label=VARIANT_LABELS[variant],
                color=style["color"],
                linestyle=style["linestyle"],
                marker=style["marker"],
                markersize=3.2,
                linewidth=1.25,
                markerfacecolor="white",
                markeredgewidth=0.8,
            )
        parameter_text = _format_parameter_values(
            sorted(
                (
                    row
                    for row in panel_rows
                    if row["variant"] == common.VARIANTS[0]
                ),
                key=lambda row: int(row["severity_index"]),
            )
        )
        axis.set_title(
            f"{CORRUPTION_LABELS[corruption_spec.name]}\n{parameter_text}",
            pad=4,
        )
        axis.set_xticks(np.arange(6))
        axis.set_xticklabels(("C", "1", "2", "3", "4", "5"))
        axis.set_xlim(-0.15, 5.15)
        axis.set_ylim(0.0, y_max)
        axis.grid(axis="y", color="#D7DCE2", linewidth=0.45, alpha=0.8)
        axis.axhline(100.0, color="#9CA3AF", linewidth=0.55, zorder=0)
        axis.text(
            -0.15,
            1.08,
            panel_letters[panel_index],
            transform=axis.transAxes,
            fontsize=8,
            fontweight="bold",
            va="top",
            ha="left",
        )
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.900),
        ncol=2,
        handlelength=2.6,
    )
    fig.suptitle(
        f"{TASK_LABELS.get(task, task)} — {METRIC_LABELS[metric]}",
        fontsize=8,
        y=0.975,
    )
    fig.supxlabel(
        "Clean baseline (C) and frozen corruption severity (1–5)", y=0.025
    )
    fig.supylabel("Performance retained from clean (%)", x=0.025)
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    outputs = {
        "pdf": output_stem.with_suffix(".pdf"),
        "svg": output_stem.with_suffix(".svg"),
        "png": output_stem.with_suffix(".png"),
    }
    fig.savefig(
        outputs["pdf"],
        bbox_inches="tight",
        metadata={
            "Title": f"{task} {metric} robustness",
            "Creator": "LGM-GAME formal robustness aggregator",
            "CreationDate": None,
            "ModDate": None,
        },
    )
    fig.savefig(
        outputs["svg"],
        bbox_inches="tight",
        metadata={
            "Title": f"{task} {metric} robustness",
            "Creator": "LGM-GAME formal robustness aggregator",
            "Date": None,
        },
    )
    fig.savefig(
        outputs["png"],
        dpi=dpi,
        bbox_inches="tight",
        metadata={"Software": "LGM-GAME formal robustness aggregator"},
    )
    plt.close(fig)
    return outputs


def artifact_inventory(
    directory: Path,
    excluded_names: set[str],
) -> dict[str, dict[str, Any]]:
    artifacts: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name not in excluded_names:
            artifacts[path.relative_to(directory).as_posix()] = {
                "sha256": common.sha256_file(path),
                "bytes": path.stat().st_size,
            }
    return artifacts


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    delivery_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description=(
            "Strictly aggregate exactly four completed formal robustness trees "
            "and create task-separated publication tables/figures."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--delivery-root", type=Path, default=delivery_root)
    parser.add_argument(
        "--university-root",
        type=Path,
        default=Path(r"C:\项目\IMTMN\datasets\University-1652"),
    )
    parser.add_argument(
        "--sues-root",
        type=Path,
        default=Path(r"C:\项目\IMTMN\datasets\SUES-200"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Defaults to lgm_game_pytorch/results/formal_robustness_aggregate.",
    )
    parser.add_argument(
        "--plot-metrics",
        nargs="+",
        choices=PLOT_METRICS,
        default=PLOT_METRICS,
    )
    parser.add_argument("--png-dpi", type=int, default=600)
    args = parser.parse_args(argv)
    if args.png_dpi < 300:
        parser.error("--png-dpi must be at least 300 for publication previews.")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    delivery_root = args.delivery_root.expanduser().resolve(strict=True)
    specs = common.build_run_specs(
        delivery_root, args.university_root, args.sues_root
    )
    expected_keys = {
        (dataset, variant)
        for dataset in common.DATASETS
        for variant in common.VARIANTS
    }
    if {(spec.dataset, spec.variant) for spec in specs} != expected_keys:
        raise RuntimeError("Aggregator input registry is not exactly 2x2.")
    evaluator_sha = common.sha256_file(Path(evaluator.__file__).resolve())
    validations: list[common.RobustnessValidation] = []
    all_issues: dict[str, list[str]] = {}
    for spec in specs:
        validation = common.validate_completed_robustness(
            spec,
            evaluator,
            verify_artifacts=True,
            verify_per_query=True,
            expected_evaluator_sha256=evaluator_sha,
        )
        validations.append(validation)
        if validation.issues:
            all_issues[spec.identifier] = validation.issues
    if all_issues:
        raise RuntimeError(
            "Four-run robustness gate failed; no aggregate output was written:\n"
            + json.dumps(all_issues, ensure_ascii=False, indent=2)
        )
    if len(validations) != common.EXPECTED_RUN_COUNT:
        raise AssertionError("Exactly four validations are required.")

    # Cross-run source/protocol/corruption identity must be identical.
    shared_fingerprints: dict[str, set[str]] = {
        "evaluator": set(),
        "formal_retrieval": set(),
        "frozen_protocol": set(),
        "corruption_matrix": set(),
    }
    for validation in validations:
        immutable = validation.run_config["immutable_config"]
        sources = immutable["sources"]
        shared_fingerprints["evaluator"].add(
            sources["robustness_evaluator"]["sha256"]
        )
        shared_fingerprints["formal_retrieval"].add(
            sources["formal_retrieval"]["sha256"]
        )
        shared_fingerprints["frozen_protocol"].add(
            sources["frozen_protocol"]["sha256"]
        )
        shared_fingerprints["corruption_matrix"].add(
            common.canonical_sha256(immutable["corruption_matrix"])
        )
    if any(len(values) != 1 for values in shared_fingerprints.values()):
        raise RuntimeError(
            f"Four completed runs do not share one source/protocol matrix: "
            f"{shared_fingerprints}"
        )

    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir is not None
        else (
            delivery_root
            / "lgm_game_pytorch"
            / "results"
            / "formal_robustness_aggregate"
        )
    )
    input_manifests = {
        validation.spec.identifier: {
            "path": str(validation.spec.robustness_manifest.resolve()),
            "sha256": common.sha256_file(
                validation.spec.robustness_manifest
            ),
            "run_config_sha256": validation.manifest["run_config_sha256"],
        }
        for validation in validations
    }
    immutable_config = {
        "schema_version": common.SCHEMA_VERSION,
        "input_manifests": input_manifests,
        "aggregator_sha256": common.sha256_file(Path(__file__).resolve()),
        "common_validator_sha256": common.sha256_file(
            Path(common.__file__).resolve()
        ),
        "evaluator_sha256": evaluator_sha,
        "plot_metrics": list(args.plot_metrics),
        "png_dpi": args.png_dpi,
        "task_aggregation_used": False,
        "figure_contract": FIGURE_CONTRACT,
        "shared_fingerprints": {
            key: next(iter(values))
            for key, values in shared_fingerprints.items()
        },
    }
    config_sha = common.canonical_sha256(immutable_config)
    output_dir.mkdir(parents=True, exist_ok=True)
    config_path = output_dir / "aggregation_run_config.json"
    if config_path.is_file():
        existing = common.load_json(config_path)
        if (
            existing.get("config_sha256") != config_sha
            or existing.get("immutable_config") != immutable_config
        ):
            raise RuntimeError(
                "Aggregation output directory contains a different immutable "
                "input/configuration. Use a new output directory."
            )
    else:
        common.atomic_json(
            config_path,
            {
                "created_utc": evaluator.formal.utc_now(),
                "config_sha256": config_sha,
                "immutable_config": immutable_config,
            },
        )

    rows = flatten_validations(validations)
    fields = (
        "dataset",
        "variant",
        "seed",
        "task",
        "queries",
        "gallery",
        "corruption",
        "corruption_display",
        "severity_index",
        "parameter",
        "value",
        "units",
        "metric",
        "clean_fraction",
        "corrupted_fraction",
        "absolute_drop_fraction",
        "percentage_point_drop",
        "relative_drop_fraction",
        "relative_drop_percent",
        "retained_percent_of_clean",
        "checkpoint_sha256",
        "robustness_run_config_sha256",
        "evaluator_sha256",
        "frozen_protocol_sha256",
    )
    source_dir = output_dir / "source_data"
    atomic_csv(
        source_dir / "robustness_all_tasks_source.csv",
        fields,
        rows,
    )
    common.atomic_json(
        output_dir / "robustness_all_tasks.json",
        nested_json_payload(validations, rows),
    )
    table_paths = [
        write_task_latex(rows, output_dir / "tables", metric)
        for metric in args.plot_metrics
    ]

    figure_records: list[dict[str, Any]] = []
    for dataset in common.DATASETS:
        for task in common.OFFICIAL_TASK_SCALE[dataset]:
            for metric in args.plot_metrics:
                figure_rows = figure_source_rows(
                    rows, dataset, task, metric
                )
                stem = (
                    output_dir
                    / "figures"
                    / dataset
                    / slug(task)
                    / f"{slug(metric)}_retention"
                )
                figure_source = (
                    output_dir
                    / "figures"
                    / "source_data"
                    / f"{slug(task)}__{slug(metric)}.csv"
                )
                atomic_csv(figure_source, fields, figure_rows)
                outputs = plot_task_metric(
                    figure_rows,
                    stem,
                    dataset=dataset,
                    task=task,
                    metric=metric,
                    dpi=args.png_dpi,
                )
                figure_records.append(
                    {
                        "dataset": dataset,
                        "task": task,
                        "metric": metric,
                        "source_csv": str(figure_source.relative_to(output_dir)),
                        "outputs": {
                            format_name: str(path.relative_to(output_dir))
                            for format_name, path in outputs.items()
                        },
                    }
                )
    expected_figures = sum(
        len(common.OFFICIAL_TASK_SCALE[dataset])
        for dataset in common.DATASETS
    ) * len(args.plot_metrics)
    if len(figure_records) != expected_figures:
        raise AssertionError(
            f"Generated {len(figure_records)} task figures, expected {expected_figures}."
        )
    common.atomic_json(
        output_dir / "figure_index.json",
        {
            "schema_version": common.SCHEMA_VERSION,
            "figure_contract": FIGURE_CONTRACT,
            "task_aggregation_used": False,
            "figures": figure_records,
        },
    )

    manifest = {
        "schema_version": common.SCHEMA_VERSION,
        "status": "completed",
        "completed_utc": evaluator.formal.utc_now(),
        "config_sha256": config_sha,
        "validated_input_run_count": len(validations),
        "expected_input_run_count": common.EXPECTED_RUN_COUNT,
        "all_four_inputs_complete": True,
        "task_aggregation_used": False,
        "flat_source_rows": len(rows),
        "latex_tables": [
            str(path.relative_to(output_dir)) for path in table_paths
        ],
        "figure_count": len(figure_records),
        "figure_formats": ["pdf", "svg", "png"],
        "source_csv_for_every_figure": True,
        "artifacts": artifact_inventory(
            output_dir, {"aggregation_manifest.json"}
        ),
    }
    manifest["payload_sha256"] = common.canonical_sha256(manifest)
    common.atomic_json(output_dir / "aggregation_manifest.json", manifest)
    print(
        f"Validated 4/4 robustness runs and generated {len(figure_records)} "
        f"task-separated figures at {output_dir}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
