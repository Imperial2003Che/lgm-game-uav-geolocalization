"""Run the frozen formal training matrix sequentially and resumably.

The experiment specification is recorded in ``FORMAL_EXPERIMENT_PROTOCOL.md``.
This runner never changes a hyperparameter from observed metrics.  It trains
all registered checkpoints before entering the separate official-test
evaluation stage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


MAIN_VARIANTS = (
    "content",
    "style",
    "visual",
    "visual_content",
    "visual_style",
    "full",
)
MAIN_SEEDS = (1, 2, 3)
DATASETS = ("university1652", "sues200")
EXPECTED_MAIN_RUN_COUNT = 36
EXPECTED_SENSITIVITY_RUN_COUNT = 6
FROZEN_EPOCHS = 80


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}.")
    return value


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    data_root: Path
    evidence: Path
    evidence_sha256: str


@dataclass(frozen=True)
class RunSpec:
    family: str
    dataset: str
    variant: str
    seed: int
    backbone: str
    embed_dim: int
    run_dir: Path
    evaluation_dir: Path

    @property
    def identifier(self) -> str:
        return (
            f"{self.family}/{self.dataset}/{self.variant}/seed_{self.seed}/"
            f"{self.backbone}/dim_{self.embed_dim}"
        )


def parse_args() -> argparse.Namespace:
    script = Path(__file__).resolve()
    delivery_root = script.parents[2]
    parser = argparse.ArgumentParser()
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
        "--stage",
        choices=("main", "sensitivity", "evaluate", "all"),
        default="all",
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=DATASETS,
        default=DATASETS,
    )
    parser.add_argument(
        "--variants",
        nargs="+",
        choices=MAIN_VARIANTS,
        default=MAIN_VARIANTS,
        help="Main-stage subset; the frozen default is all six variants.",
    )
    parser.add_argument(
        "--seeds",
        nargs="+",
        type=int,
        default=MAIN_SEEDS,
        help="Main-stage subset; the frozen default is seeds 1, 2, and 3.",
    )
    return parser.parse_args()


def dataset_specs(
    delivery_root: Path,
    university_root: Path,
    sues_root: Path,
) -> dict[str, DatasetSpec]:
    package_root = delivery_root / "lgm_game_pytorch"
    university_evidence = (
        package_root
        / "evidence_cache"
        / "university1652_clip_image_evidence.npz"
    ).resolve(strict=True)
    sues_evidence = (
        package_root / "evidence_cache" / "sues200_clip_image_evidence.npz"
    ).resolve(strict=True)
    return {
        "university1652": DatasetSpec(
            "university1652",
            university_root.resolve(strict=True),
            university_evidence,
            sha256_file(university_evidence),
        ),
        "sues200": DatasetSpec(
            "sues200",
            sues_root.resolve(strict=True),
            sues_evidence,
            sha256_file(sues_evidence),
        ),
    }


def main_run_specs(
    delivery_root: Path,
    datasets: Iterable[str],
    variants: Iterable[str],
    seeds: Iterable[int],
) -> list[RunSpec]:
    package_root = delivery_root / "lgm_game_pytorch"
    specs: list[RunSpec] = []
    for dataset in datasets:
        for variant in variants:
            for seed in seeds:
                specs.append(
                    RunSpec(
                        family="formal_main",
                        dataset=dataset,
                        variant=variant,
                        seed=int(seed),
                        backbone="resnet18",
                        embed_dim=512,
                        run_dir=(
                            package_root
                            / "runs"
                            / "formal_main"
                            / dataset
                            / variant
                            / f"seed_{seed}"
                        ),
                        evaluation_dir=(
                            package_root
                            / "evaluations"
                            / "formal_main"
                            / dataset
                            / variant
                            / f"seed_{seed}"
                        ),
                    )
                )
    return specs


def sensitivity_run_specs(
    delivery_root: Path,
    datasets: Iterable[str],
) -> list[RunSpec]:
    package_root = delivery_root / "lgm_game_pytorch"
    settings = (
        ("resnet50", 512, "backbone_resnet50"),
        ("resnet18", 256, "embed_dim_256"),
        ("resnet18", 1024, "embed_dim_1024"),
    )
    specs: list[RunSpec] = []
    for dataset in datasets:
        for backbone, embed_dim, label in settings:
            specs.append(
                RunSpec(
                    family="formal_sensitivity",
                    dataset=dataset,
                    variant="full",
                    seed=1,
                    backbone=backbone,
                    embed_dim=embed_dim,
                    run_dir=(
                        package_root
                        / "runs"
                        / "formal_sensitivity"
                        / dataset
                        / label
                        / "seed_1"
                    ),
                    evaluation_dir=(
                        package_root
                        / "evaluations"
                        / "formal_sensitivity"
                        / dataset
                        / label
                        / "seed_1"
                    ),
                )
            )
    return specs


def validate_registry(
    main_specs: list[RunSpec],
    sensitivity_specs: list[RunSpec],
) -> None:
    if len(main_specs) != EXPECTED_MAIN_RUN_COUNT:
        raise RuntimeError(
            f"Frozen main registry contains {len(main_specs)} runs, "
            f"expected {EXPECTED_MAIN_RUN_COUNT}."
        )
    if len(sensitivity_specs) != EXPECTED_SENSITIVITY_RUN_COUNT:
        raise RuntimeError(
            f"Frozen sensitivity registry contains {len(sensitivity_specs)} runs, "
            f"expected {EXPECTED_SENSITIVITY_RUN_COUNT}."
        )
    all_specs = main_specs + sensitivity_specs
    identifiers = [spec.identifier for spec in all_specs]
    run_dirs = [str(spec.run_dir.resolve()) for spec in all_specs]
    evaluation_dirs = [str(spec.evaluation_dir.resolve()) for spec in all_specs]
    if len(identifiers) != len(set(identifiers)):
        raise RuntimeError("Frozen registry contains duplicate run identifiers.")
    if len(run_dirs) != len(set(run_dirs)):
        raise RuntimeError("Frozen registry contains duplicate training directories.")
    if len(evaluation_dirs) != len(set(evaluation_dirs)):
        raise RuntimeError("Frozen registry contains duplicate evaluation directories.")


def registry_sha256(specs: list[RunSpec]) -> str:
    return canonical_sha256(
        [
            {
                "identifier": spec.identifier,
                "family": spec.family,
                "dataset": spec.dataset,
                "variant": spec.variant,
                "seed": spec.seed,
                "backbone": spec.backbone,
                "embed_dim": spec.embed_dim,
                "run_dir": str(spec.run_dir.resolve()),
                "evaluation_dir": str(spec.evaluation_dir.resolve()),
            }
            for spec in specs
        ]
    )


def training_completion_issues(
    spec: RunSpec,
    dataset: DatasetSpec,
    formal_script_sha256: str,
) -> list[str]:
    """Return all reasons a directory is not admissible as a completed run.

    This intentionally checks the immutable run configuration and the full
    fixed-epoch history.  A merely present ``best.pt`` must never cause a
    mismatched or partial manual run to be skipped.
    """

    manifest_path = spec.run_dir / "run_manifest.json"
    config_path = spec.run_dir / "run_config.json"
    history_path = spec.run_dir / "history.json"
    best_path = spec.run_dir / "best.pt"
    last_path = spec.run_dir / "last.pt"
    if not manifest_path.is_file():
        return ["run_manifest.json is absent"]
    manifest = load_json(manifest_path)
    if manifest.get("status") != "completed":
        return [f"manifest status is {manifest.get('status')!r}"]

    issues: list[str] = []
    if manifest.get("schema_version") != "formal-retrieval-v1":
        issues.append("unexpected manifest schema")
    payload = dict(manifest)
    declared_payload_sha = payload.pop("payload_sha256", None)
    if declared_payload_sha != canonical_sha256(payload):
        issues.append("training manifest payload hash is invalid")
    if int(manifest.get("epochs_completed", -1)) != FROZEN_EPOCHS:
        issues.append("epochs_completed is not 80")
    if int(manifest.get("best_epoch", -1)) != FROZEN_EPOCHS - 1:
        issues.append("best_epoch is not the pre-specified final epoch")
    if manifest.get("best_validation_mAP") is not None:
        issues.append("a validation metric selected the checkpoint")
    if manifest.get("test_protocol_was_evaluated") is not False:
        issues.append("training manifest does not explicitly deny test evaluation")
    for path in (config_path, history_path, best_path, last_path):
        if not path.is_file() or path.stat().st_size <= 0:
            issues.append(f"missing or empty artifact: {path.name}")
    if issues:
        return issues

    config = load_json(config_path)
    immutable = config.get("immutable_config")
    if not isinstance(immutable, dict):
        return ["run_config immutable_config is absent or invalid"]
    declared_config_sha = config.get("run_config_sha256")
    if declared_config_sha != canonical_sha256(immutable):
        issues.append("run_config_sha256 does not match immutable_config")
    if manifest.get("run_config_sha256") != declared_config_sha:
        issues.append("manifest and run_config hashes differ")
    if immutable.get("schema_version") != "formal-retrieval-v1":
        issues.append("unexpected run_config schema")
    if immutable.get("command") != "train":
        issues.append("run_config command is not train")
    if immutable.get("dataset") != spec.dataset:
        issues.append("dataset differs from frozen registry")
    if int(immutable.get("seed", -1)) != spec.seed:
        issues.append("seed differs from frozen registry")
    if Path(str(immutable.get("data_root", ""))).resolve() != dataset.data_root:
        issues.append("dataset root differs from frozen registry")
    if immutable.get("code_sha256") != formal_script_sha256:
        issues.append("formal code hash differs from the frozen runner gate")

    model = immutable.get("model")
    if not isinstance(model, dict):
        issues.append("model configuration is absent")
    else:
        expected_model = {
            "variant": spec.variant,
            "backbone": spec.backbone,
            "embed_dim": spec.embed_dim,
            "dropout": 0.20,
            "image_size": 224,
            "resize_size": 256,
        }
        for key, expected in expected_model.items():
            if model.get(key) != expected:
                issues.append(f"model.{key} differs from frozen registry")
        pretrained = model.get("pretrained_initialization")
        expected_pretrained = spec.variant in {
            "visual",
            "visual_content",
            "visual_style",
            "full",
        }
        if (
            not isinstance(pretrained, dict)
            or pretrained.get("enabled") is not expected_pretrained
        ):
            issues.append("pretrained visual initialization differs from protocol")
        elif expected_pretrained:
            if not str(pretrained.get("weight_enum", "")).startswith(
                f"{spec.backbone.replace('resnet', 'ResNet')}_Weights."
            ):
                issues.append("unexpected torchvision pretrained weight enum")
            if len(str(pretrained.get("cached_file_sha256", ""))) != 64:
                issues.append("pretrained weight SHA-256 is absent")

    optimization = immutable.get("optimization")
    if not isinstance(optimization, dict):
        issues.append("optimization configuration is absent")
        expected_steps = -1
    else:
        expected_optimization = {
            "epochs": FROZEN_EPOCHS,
            "learning_rate": 0.0003,
            "backbone_lr_multiplier": 0.1,
            "weight_decay": 0.0001,
            "warmup_epochs": 5,
            "gradient_clip_norm": 5.0,
            "identities_per_batch": 16,
            "instances_per_identity": 4,
            "samples_per_class_per_epoch": 0,
            "steps_per_epoch_requested": 0,
            "sampler_schedule_audited_epochs": FROZEN_EPOCHS,
            "sampler_step_count_fixed_across_epochs": True,
            "amp": True,
        }
        for key, expected in expected_optimization.items():
            if optimization.get(key) != expected:
                issues.append(f"optimization.{key} differs from frozen protocol")
        expected_steps = int(optimization.get("steps_per_epoch_actual", -1))
        if expected_steps <= 0:
            issues.append("steps_per_epoch_actual is not positive")

    selection = immutable.get("selection")
    if not isinstance(selection, dict) or selection.get("patience") != 0:
        issues.append("checkpoint-selection configuration is not fixed/no-validation")
    if immutable.get("validation_ids") != []:
        issues.append("validation_ids is not empty")
    protocol = immutable.get("protocol")
    if (
        not isinstance(protocol, dict)
        or float(protocol.get("holdout_fraction", -1.0)) != 0.0
        or int(protocol.get("official_test_images_used_by_train_or_validation", -1))
        != 0
    ):
        issues.append("training protocol does not prove zero holdout/test use")

    evidence_descriptors = immutable.get("evidence_caches")
    if not isinstance(evidence_descriptors, list) or len(evidence_descriptors) != 1:
        issues.append("expected exactly one frozen evidence cache")
    else:
        descriptor = evidence_descriptors[0]
        if Path(str(descriptor.get("path", ""))).resolve() != dataset.evidence:
            issues.append("evidence path differs from frozen registry")
        if descriptor.get("sha256") != dataset.evidence_sha256:
            issues.append("evidence hash differs from frozen registry")
    image_inventory = immutable.get("image_inventory")
    if (
        not isinstance(image_inventory, dict)
        or image_inventory.get("mode") != "content"
        or len(str(image_inventory.get("sha256", ""))) != 64
        or int(image_inventory.get("file_count", -1)) <= 0
    ):
        issues.append("content-hashed image inventory is absent or invalid")

    try:
        history = json.loads(history_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        issues.append(f"history.json cannot be read: {error}")
        history = []
    if not isinstance(history, list) or len(history) != FROZEN_EPOCHS:
        issues.append("history does not contain exactly 80 epochs")
    else:
        for epoch, row in enumerate(history):
            if not isinstance(row, dict):
                issues.append(f"history row {epoch} is not an object")
                break
            if int(row.get("epoch", -1)) != epoch:
                issues.append(f"history row {epoch} has a non-contiguous epoch")
                break
            if int(row.get("optimizer_steps", -1)) != expected_steps:
                issues.append(f"history row {epoch} has a variable step count")
                break
            if row.get("validation_selection_mAP") is not None:
                issues.append(f"history row {epoch} contains validation selection")
                break
            if row.get("validation") != {}:
                issues.append(f"history row {epoch} contains validation/test metrics")
                break

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        issues.append("manifest artifact inventory is absent")
    else:
        for name, path in (
            ("run_config.json", config_path),
            ("history.json", history_path),
            ("best.pt", best_path),
            ("last.pt", last_path),
        ):
            record = artifacts.get(name)
            if not isinstance(record, dict):
                issues.append(f"manifest omits artifact record for {name}")
                continue
            if int(record.get("bytes", -1)) != path.stat().st_size:
                issues.append(f"artifact byte count differs for {name}")
            declared_sha = str(record.get("sha256", ""))
            if len(declared_sha) != 64:
                issues.append(f"artifact SHA-256 is invalid for {name}")
    return issues


def training_complete(
    spec: RunSpec,
    dataset: DatasetSpec,
    formal_script_sha256: str,
) -> bool:
    return not training_completion_issues(
        spec,
        dataset,
        formal_script_sha256,
    )


def checkpoint_artifact_hash_issues(
    spec: RunSpec,
    names: tuple[str, ...] = ("best.pt", "last.pt"),
) -> list[str]:
    manifest = load_json(spec.run_dir / "run_manifest.json")
    artifacts = manifest.get("artifacts", {})
    issues: list[str] = []
    for name in names:
        path = spec.run_dir / name
        record = artifacts.get(name) if isinstance(artifacts, dict) else None
        if not path.is_file() or not isinstance(record, dict):
            issues.append(f"cannot hash-audit checkpoint artifact {name}")
        elif record.get("sha256") != sha256_file(path):
            issues.append(f"checkpoint artifact SHA-256 differs for {name}")
    return issues


def evaluation_completion_issues(
    spec: RunSpec,
    dataset: DatasetSpec,
) -> list[str]:
    manifest = load_json(spec.evaluation_dir / "evaluation_manifest.json")
    if manifest.get("status") != "completed":
        return [f"evaluation manifest status is {manifest.get('status')!r}"]
    issues: list[str] = []
    if manifest.get("schema_version") != "formal-retrieval-v1":
        issues.append("unexpected evaluation manifest schema")
    payload = dict(manifest)
    declared_payload_sha = payload.pop("payload_sha256", None)
    if declared_payload_sha != canonical_sha256(payload):
        issues.append("evaluation manifest payload hash is invalid")
    if manifest.get("dataset") != spec.dataset:
        issues.append("evaluation dataset differs from frozen registry")
    checkpoint = manifest.get("checkpoint")
    best_path = spec.run_dir / "best.pt"
    if not isinstance(checkpoint, dict):
        issues.append("evaluation checkpoint provenance is absent")
    else:
        if Path(str(checkpoint.get("path", ""))).resolve() != best_path.resolve():
            issues.append("evaluation used a checkpoint outside the frozen run")
        if checkpoint.get("variant") != spec.variant:
            issues.append("evaluation checkpoint variant differs from registry")
        if int(checkpoint.get("selected_training_epoch", -1)) != FROZEN_EPOCHS - 1:
            issues.append("evaluation did not use the pre-specified final epoch")
        if best_path.is_file():
            if checkpoint.get("sha256") != sha256_file(best_path):
                issues.append("evaluated checkpoint SHA-256 does not match best.pt")
        else:
            issues.append("best.pt is absent")
    evidence = manifest.get("evidence_caches")
    if not isinstance(evidence, list) or len(evidence) != 1:
        issues.append("evaluation evidence provenance is absent")
    else:
        descriptor = evidence[0]
        if Path(str(descriptor.get("path", ""))).resolve() != dataset.evidence:
            issues.append("evaluation evidence path differs from frozen registry")
        if descriptor.get("sha256") != dataset.evidence_sha256:
            issues.append("evaluation evidence hash differs from frozen registry")
    controls = manifest.get("leakage_controls")
    if (
        not isinstance(controls, dict)
        or controls.get("test_used_during_training_or_model_selection") is not False
        or controls.get("all_official_queries_used") is not True
        or controls.get("all_official_gallery_images_used") is not True
    ):
        issues.append("evaluation leakage/full-protocol controls are incomplete")

    metrics_path = spec.evaluation_dir / "metrics.json"
    csv_path = spec.evaluation_dir / "metrics.csv"
    for path in (metrics_path, csv_path):
        if not path.is_file() or path.stat().st_size <= 0:
            issues.append(f"missing or empty evaluation artifact: {path.name}")
    if metrics_path.is_file():
        metrics = load_json(metrics_path)
        results = metrics.get("results")
        expected_tasks = 3 if spec.dataset == "university1652" else 8
        if (
            metrics.get("schema_version") != "formal-retrieval-v1"
            or metrics.get("full_gallery") is not True
            or not isinstance(results, dict)
            or len(results) != expected_tasks
        ):
            issues.append("metrics.json does not contain every official task")
    artifacts = manifest.get("artifacts")
    if isinstance(artifacts, dict):
        for name, path in (("metrics.json", metrics_path), ("metrics.csv", csv_path)):
            record = artifacts.get(name)
            if not isinstance(record, dict):
                issues.append(f"evaluation manifest omits {name}")
            elif path.is_file() and (
                int(record.get("bytes", -1)) != path.stat().st_size
                or record.get("sha256") != sha256_file(path)
            ):
                issues.append(f"evaluation artifact hash differs for {name}")
    else:
        issues.append("evaluation artifact inventory is absent")
    return issues


def evaluation_complete(spec: RunSpec, dataset: DatasetSpec) -> bool:
    return not evaluation_completion_issues(spec, dataset)


def base_environment(delivery_root: Path, seed: int) -> dict[str, str]:
    environment = dict(os.environ)
    package_root = delivery_root / "lgm_game_pytorch"
    old_pythonpath = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = (
        str(package_root)
        if not old_pythonpath
        else str(package_root) + os.pathsep + old_pythonpath
    )
    environment["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    environment["PYTHONHASHSEED"] = str(seed)
    return environment


def train_command(
    formal_script: Path,
    dataset: DatasetSpec,
    spec: RunSpec,
) -> list[str]:
    last_checkpoint = spec.run_dir / "last.pt"
    resume = "last" if last_checkpoint.is_file() else "none"
    if resume == "none" and spec.run_dir.exists():
        retained_artifacts = [
            path
            for path in (
                spec.run_dir / "run_config.json",
                spec.run_dir / "run_manifest.json",
                spec.run_dir / "history.json",
                spec.run_dir / "best.pt",
                spec.run_dir / "run.log",
            )
            if path.exists()
        ]
        if retained_artifacts:
            names = ", ".join(path.name for path in retained_artifacts)
            raise RuntimeError(
                f"{spec.identifier} has retained run artifacts but no resumable "
                f"last.pt ({names}); refusing to overwrite a failed run."
            )
    return [
        sys.executable,
        str(formal_script),
        "train",
        "--dataset",
        dataset.name,
        "--data-root",
        str(dataset.data_root),
        "--evidence",
        str(dataset.evidence),
        "--output-dir",
        str(spec.run_dir),
        "--device",
        "cuda",
        "--workers",
        "8",
        "--seed",
        str(spec.seed),
        "--data-hash-mode",
        "content",
        "--amp",
        "--eval-batch-size",
        "128",
        "--eval-chunk-size",
        "128",
        "--variant",
        spec.variant,
        "--backbone",
        spec.backbone,
        "--embed-dim",
        str(spec.embed_dim),
        "--dropout",
        "0.20",
        "--pretrained",
        "--image-size",
        "224",
        "--resize-size",
        "256",
        "--epochs",
        "80",
        "--warmup-epochs",
        "5",
        "--learning-rate",
        "0.0003",
        "--backbone-lr-multiplier",
        "0.1",
        "--weight-decay",
        "0.0001",
        "--gradient-clip-norm",
        "5.0",
        "--identities-per-batch",
        "16",
        "--instances-per-identity",
        "4",
        "--samples-per-class-per-epoch",
        "0",
        "--steps-per-epoch",
        "0",
        "--val-fraction",
        "0",
        "--patience",
        "0",
        "--resume",
        resume,
    ]


def evaluation_command(
    formal_script: Path,
    dataset: DatasetSpec,
    spec: RunSpec,
) -> list[str]:
    return [
        sys.executable,
        str(formal_script),
        "evaluate",
        "--dataset",
        dataset.name,
        "--data-root",
        str(dataset.data_root),
        "--evidence",
        str(dataset.evidence),
        "--output-dir",
        str(spec.evaluation_dir),
        "--device",
        "cuda",
        "--workers",
        "8",
        "--seed",
        str(spec.seed),
        "--data-hash-mode",
        "content",
        "--amp",
        "--eval-batch-size",
        "128",
        "--eval-chunk-size",
        "128",
        "--checkpoint",
        str(spec.run_dir / "best.pt"),
    ]


def run_command(
    command: list[str],
    output_dir: Path,
    environment: dict[str, str],
) -> tuple[int, float]:
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with (output_dir / "process_stdout.log").open(
        "a", encoding="utf-8", newline="\n"
    ) as stdout_handle, (output_dir / "process_stderr.log").open(
        "a", encoding="utf-8", newline="\n"
    ) as stderr_handle:
        completed = subprocess.run(
            command,
            cwd=output_dir,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=stdout_handle,
            stderr=stderr_handle,
            check=False,
        )
    return completed.returncode, time.perf_counter() - started


def update_ledger(
    ledger_path: Path,
    ledger: dict[str, Any],
    spec: RunSpec,
    stage: str,
    status: str,
    **extra: Any,
) -> None:
    runs = ledger.setdefault("runs", {})
    record = runs.setdefault(spec.identifier, {})
    event = {
        "family": spec.family,
        "dataset": spec.dataset,
        "variant": spec.variant,
        "seed": spec.seed,
        "backbone": spec.backbone,
        "embed_dim": spec.embed_dim,
        "stage": stage,
        "status": status,
        "updated_utc": utc_now(),
        **extra,
    }
    record.setdefault("events", []).append(event)
    record.update(event)
    ledger["updated_utc"] = utc_now()
    atomic_json(ledger_path, ledger)


def pin_dataset_fingerprint(
    ledger_path: Path,
    ledger: dict[str, Any],
    spec: RunSpec,
) -> None:
    immutable = load_json(spec.run_dir / "run_config.json")["immutable_config"]
    payload = {
        "dataset": spec.dataset,
        "data_root": immutable["data_root"],
        "image_inventory": immutable["image_inventory"],
        "train_ids_sha256": canonical_sha256(immutable["train_ids"]),
        "sues_manifest": immutable.get("sues_manifest"),
        "evidence_caches": immutable["evidence_caches"],
    }
    fingerprint = {
        "sha256": canonical_sha256(payload),
        "payload": payload,
        "pinned_from": spec.identifier,
        "updated_utc": utc_now(),
    }
    stored = ledger.setdefault("dataset_fingerprints", {}).get(spec.dataset)
    if stored is not None and stored.get("sha256") != fingerprint["sha256"]:
        raise RuntimeError(
            f"{spec.dataset} content/protocol fingerprint changed between "
            f"formal runs ({stored.get('sha256')} != {fingerprint['sha256']})."
        )
    if stored is None:
        ledger["dataset_fingerprints"][spec.dataset] = fingerprint
        atomic_json(ledger_path, ledger)


def train_specs(
    specs: list[RunSpec],
    data: dict[str, DatasetSpec],
    formal_script: Path,
    delivery_root: Path,
    ledger_path: Path,
    ledger: dict[str, Any],
    formal_script_sha256: str,
) -> None:
    for index, spec in enumerate(specs, start=1):
        completion_issues = training_completion_issues(
            spec,
            data[spec.dataset],
            formal_script_sha256,
        )
        if not completion_issues:
            completion_issues.extend(checkpoint_artifact_hash_issues(spec))
        if not completion_issues:
            pin_dataset_fingerprint(ledger_path, ledger, spec)
            update_ledger(
                ledger_path,
                ledger,
                spec,
                "train",
                "skipped_already_complete",
                ordinal=index,
                total=len(specs),
                run_config_sha256=load_json(
                    spec.run_dir / "run_manifest.json"
                ).get("run_config_sha256"),
                checkpoint_sha256=sha256_file(spec.run_dir / "best.pt"),
            )
            continue
        manifest = load_json(spec.run_dir / "run_manifest.json")
        if manifest.get("status") == "completed":
            update_ledger(
                ledger_path,
                ledger,
                spec,
                "train",
                "failed_completion_audit",
                ordinal=index,
                total=len(specs),
                completion_issues=completion_issues,
            )
            raise RuntimeError(
                f"Completed run {spec.identifier} failed the frozen completion "
                f"audit: {completion_issues[:5]}"
            )
        try:
            command = train_command(formal_script, data[spec.dataset], spec)
        except Exception as error:
            update_ledger(
                ledger_path,
                ledger,
                spec,
                "train",
                "failed_prelaunch",
                ordinal=index,
                total=len(specs),
                completion_issues=completion_issues,
                error_type=type(error).__name__,
                error=str(error),
            )
            raise
        update_ledger(
            ledger_path,
            ledger,
            spec,
            "train",
            "running",
            ordinal=index,
            total=len(specs),
            command=command,
        )
        try:
            return_code, elapsed = run_command(
                command,
                spec.run_dir,
                base_environment(delivery_root, spec.seed),
            )
        except BaseException as error:
            update_ledger(
                ledger_path,
                ledger,
                spec,
                "train",
                "interrupted",
                error_type=type(error).__name__,
                error=str(error),
            )
            raise
        completion_issues = training_completion_issues(
            spec,
            data[spec.dataset],
            formal_script_sha256,
        )
        if not completion_issues:
            completion_issues.extend(checkpoint_artifact_hash_issues(spec))
        if return_code != 0 or completion_issues:
            update_ledger(
                ledger_path,
                ledger,
                spec,
                "train",
                "failed",
                return_code=return_code,
                elapsed_seconds=elapsed,
                completion_issues=completion_issues,
            )
            raise RuntimeError(
                f"Formal training failed for {spec.identifier}; return code "
                f"{return_code}; completion audit: {completion_issues[:5]}."
            )
        try:
            pin_dataset_fingerprint(ledger_path, ledger, spec)
        except Exception as error:
            update_ledger(
                ledger_path,
                ledger,
                spec,
                "train",
                "failed_dataset_fingerprint_gate",
                error_type=type(error).__name__,
                error=str(error),
            )
            raise
        update_ledger(
            ledger_path,
            ledger,
            spec,
            "train",
            "completed",
            return_code=return_code,
            elapsed_seconds=elapsed,
            checkpoint_sha256=sha256_file(spec.run_dir / "best.pt"),
        )


def evaluate_specs(
    specs: list[RunSpec],
    data: dict[str, DatasetSpec],
    formal_script: Path,
    delivery_root: Path,
    ledger_path: Path,
    ledger: dict[str, Any],
    formal_script_sha256: str,
) -> None:
    incomplete: list[dict[str, Any]] = []
    for spec in specs:
        issues = training_completion_issues(
            spec,
            data[spec.dataset],
            formal_script_sha256,
        )
        if not issues:
            issues.extend(
                checkpoint_artifact_hash_issues(spec, names=("best.pt",))
            )
        if issues:
            incomplete.append(
                {"identifier": spec.identifier, "issues": issues[:5]}
            )
        else:
            pin_dataset_fingerprint(ledger_path, ledger, spec)
    if incomplete:
        raise RuntimeError(
            "Official evaluation is gated until every registered training run is "
            f"complete; first incomplete runs: {incomplete[:5]}"
        )
    for index, spec in enumerate(specs, start=1):
        completion_issues = evaluation_completion_issues(
            spec, data[spec.dataset]
        )
        if not completion_issues:
            update_ledger(
                ledger_path,
                ledger,
                spec,
                "evaluate",
                "skipped_already_complete",
                ordinal=index,
                total=len(specs),
                metrics_sha256=sha256_file(
                    spec.evaluation_dir / "metrics.json"
                ),
            )
            continue
        manifest = load_json(spec.evaluation_dir / "evaluation_manifest.json")
        if manifest.get("status") == "completed":
            update_ledger(
                ledger_path,
                ledger,
                spec,
                "evaluate",
                "failed_completion_audit",
                ordinal=index,
                total=len(specs),
                completion_issues=completion_issues,
            )
            raise RuntimeError(
                f"Completed evaluation {spec.identifier} failed the frozen "
                f"completion audit: {completion_issues[:5]}"
            )
        command = evaluation_command(formal_script, data[spec.dataset], spec)
        update_ledger(
            ledger_path,
            ledger,
            spec,
            "evaluate",
            "running",
            ordinal=index,
            total=len(specs),
            command=command,
        )
        try:
            return_code, elapsed = run_command(
                command,
                spec.evaluation_dir,
                base_environment(delivery_root, spec.seed),
            )
        except BaseException as error:
            update_ledger(
                ledger_path,
                ledger,
                spec,
                "evaluate",
                "interrupted",
                error_type=type(error).__name__,
                error=str(error),
            )
            raise
        completion_issues = evaluation_completion_issues(
            spec, data[spec.dataset]
        )
        if return_code != 0 or completion_issues:
            update_ledger(
                ledger_path,
                ledger,
                spec,
                "evaluate",
                "failed",
                return_code=return_code,
                elapsed_seconds=elapsed,
                completion_issues=completion_issues,
            )
            raise RuntimeError(
                f"Formal evaluation failed for {spec.identifier}; return code "
                f"{return_code}; completion audit: {completion_issues[:5]}."
            )
        update_ledger(
            ledger_path,
            ledger,
            spec,
            "evaluate",
            "completed",
            return_code=return_code,
            elapsed_seconds=elapsed,
            metrics_sha256=sha256_file(spec.evaluation_dir / "metrics.json"),
        )


def main() -> None:
    args = parse_args()
    delivery_root = args.delivery_root.resolve(strict=True)
    protocol = (delivery_root / "FORMAL_EXPERIMENT_PROTOCOL.md").resolve(strict=True)
    formal_script = (
        delivery_root
        / "lgm_game_pytorch"
        / "lgm_game_pytorch"
        / "formal_retrieval.py"
    ).resolve(strict=True)
    data = dataset_specs(
        delivery_root,
        args.university_root,
        args.sues_root,
    )
    registered_main_specs = main_run_specs(
        delivery_root,
        DATASETS,
        MAIN_VARIANTS,
        MAIN_SEEDS,
    )
    registered_sensitivity_specs = sensitivity_run_specs(delivery_root, DATASETS)
    validate_registry(registered_main_specs, registered_sensitivity_specs)
    registered_specs = registered_main_specs + registered_sensitivity_specs
    registered_registry_sha256 = registry_sha256(registered_specs)
    protocol_sha256 = sha256_file(protocol)
    formal_script_sha256 = sha256_file(formal_script)
    runner_path = Path(__file__).resolve()
    runner_sha256 = sha256_file(runner_path)
    selected_datasets = tuple(args.datasets)
    main_specs = main_run_specs(
        delivery_root,
        selected_datasets,
        tuple(args.variants),
        tuple(args.seeds),
    )
    sensitivity_specs = sensitivity_run_specs(delivery_root, selected_datasets)
    ledger_path = (
        delivery_root
        / "lgm_game_pytorch"
        / "runs"
        / "frozen_formal_matrix_ledger.json"
    )
    ledger = load_json(ledger_path)
    if not ledger:
        ledger = {
            "schema_version": "lgm-game.frozen-formal-matrix.v1",
            "created_utc": utc_now(),
            "protocol_path": str(protocol),
            "protocol_sha256": protocol_sha256,
            "runner_path": str(runner_path),
            "runner_sha256": runner_sha256,
            "formal_script_path": str(formal_script),
            "formal_script_sha256": formal_script_sha256,
            "registered_main_run_count": EXPECTED_MAIN_RUN_COUNT,
            "registered_sensitivity_run_count": EXPECTED_SENSITIVITY_RUN_COUNT,
            "registered_run_count": len(registered_specs),
            "registered_registry_sha256": registered_registry_sha256,
            "frozen_inputs": {
                name: {
                    "data_root": str(spec.data_root),
                    "evidence_path": str(spec.evidence),
                    "evidence_sha256": spec.evidence_sha256,
                }
                for name, spec in data.items()
            },
            "official_test_gate": (
                "after all 42 registered training runs pass the frozen "
                "completion audit"
            ),
            "runs": {},
        }
        atomic_json(ledger_path, ledger)
    elif ledger.get("protocol_sha256") != protocol_sha256:
        raise RuntimeError(
            "Frozen protocol hash changed after ledger creation; refusing to continue."
        )
    elif ledger.get("formal_script_sha256") != formal_script_sha256:
        raise RuntimeError(
            "Formal training/evaluation code hash changed after matrix creation; "
            "refusing to mix implementations."
        )
    elif ledger.get("runner_sha256") != runner_sha256:
        raise RuntimeError(
            "Frozen matrix runner hash changed after ledger creation; refusing "
            "to alter orchestration semantics mid-matrix."
        )
    elif ledger.get("registered_registry_sha256") != registered_registry_sha256:
        raise RuntimeError(
            "Frozen 36+6 run registry changed after ledger creation; refusing "
            "to continue."
        )
    elif ledger.get("frozen_inputs") != {
        name: {
            "data_root": str(spec.data_root),
            "evidence_path": str(spec.evidence),
            "evidence_sha256": spec.evidence_sha256,
        }
        for name, spec in data.items()
    }:
        raise RuntimeError(
            "Frozen dataset roots or evidence-cache hashes changed after ledger "
            "creation; refusing to mix inputs."
        )

    invocation = {
        "started_utc": utc_now(),
        "stage": args.stage,
        "selected_datasets": list(selected_datasets),
        "selected_variants": list(args.variants),
        "selected_seeds": list(args.seeds),
    }
    ledger.setdefault("invocations", []).append(invocation)
    ledger["status"] = "running_selected_stage"
    atomic_json(ledger_path, ledger)
    try:
        if args.stage in {"main", "all"}:
            train_specs(
                main_specs,
                data,
                formal_script,
                delivery_root,
                ledger_path,
                ledger,
                formal_script_sha256,
            )
        if args.stage in {"sensitivity", "all"}:
            train_specs(
                sensitivity_specs,
                data,
                formal_script,
                delivery_root,
                ledger_path,
                ledger,
                formal_script_sha256,
            )
        if args.stage in {"evaluate", "all"}:
            # Evaluation is deliberately registered-matrix-wide even if a
            # training invocation used subset filters.  Subset completion can
            # never unlock official test evaluation.
            evaluate_specs(
                registered_specs,
                data,
                formal_script,
                delivery_root,
                ledger_path,
                ledger,
                formal_script_sha256,
            )
    except BaseException as error:
        invocation["finished_utc"] = utc_now()
        invocation["status"] = "failed_or_interrupted"
        invocation["error_type"] = type(error).__name__
        invocation["error"] = str(error)
        ledger["status"] = "failed_or_interrupted_selected_stage"
        ledger["last_error"] = {
            "utc": utc_now(),
            "type": type(error).__name__,
            "message": str(error),
        }
        atomic_json(ledger_path, ledger)
        raise
    invocation["finished_utc"] = utc_now()
    invocation["status"] = "completed"
    ledger["status"] = "completed_selected_stage"
    ledger["completed_utc"] = utc_now()
    ledger.pop("last_error", None)
    atomic_json(ledger_path, ledger)


if __name__ == "__main__":
    main()
