"""Integrity-controlled execution adapter for the published MCCG training code."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
from typing import Any

from external_baselines.fetch_and_verify_sources import IntegrityError, sha256_file
from external_baselines.qdfl_adapter import (
    canonical_object_sha256,
    load_weight_registry,
    training_class_inventory,
    training_content_inventory,
    verify_patched_source,
    verify_weight,
    write_immutable_json,
)


RUN_CONFIG_SCHEMA = "lgm-game.mccg-run-config.v2"
FIT_MANIFEST_SCHEMA = "lgm-game.mccg-fit.v2"
STATUS_SCHEMA = "lgm-game.mccg-fit-status.v2"
HISTORY_SCHEMA = "lgm-game.mccg-epoch-history.v2"
WEIGHT_ID = "mccg_convnext_tiny_22k_1k_224"

PUBLISHED_RECIPE = {
    "backbone": "convnext_tiny",
    "initialization": WEIGHT_ID,
    "epochs": 200,
    "batch_size": 8,
    "views": 2,
    "image_size": [256, 256],
    "padding": 10,
    "random_erasing_probability": 0.5,
    "color_jitter": True,
    "imagenet_autoaugment": True,
    "triplet_margin": 0.3,
    "sample_num": 1,
    "classifier_blocks": 2,
    "optimizer": "SGD",
    "learning_rate": 0.01,
    "backbone_learning_rate_multiplier": 0.3,
    "weight_decay": 0.0005,
    "momentum": 0.9,
    "nesterov": True,
    "scheduler": "MultiStepLR",
    "scheduler_milestones": [80, 120],
    "scheduler_gamma": 0.1,
    "mixed_precision": True,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_json(path: Path, payload: Any) -> None:
    serialized = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    if temporary.exists():
        raise IntegrityError(f"Refusing to overwrite stale temporary file: {temporary}")
    temporary.write_bytes(serialized)
    temporary.replace(path)


def adapter_file_hash() -> str:
    return sha256_file(Path(__file__))


def shared_integrity_module_hash() -> str:
    from external_baselines import qdfl_adapter

    return sha256_file(Path(qdfl_adapter.__file__))


def validate_published_recipe(source_root: Path) -> None:
    run_script = (source_root / "run.sh").read_text(encoding="utf-8")
    expected_run_lines = (
        'name="convnext_tri"',
        "lr=0.01",
        "batchsize=8",
        "triplet_loss=0.3",
        "num_epochs=200",
        "views=2",
    )
    missing = [line for line in expected_run_lines if line not in run_script]
    if missing:
        raise IntegrityError(f"MCCG run.sh recipe drifted; missing lines: {missing}")

    train_source = (source_root / "train.py").read_text(encoding="utf-8")
    optimizer_source = (
        source_root / "optimizers" / "make_optimizer.py"
    ).read_text(encoding="utf-8")
    model_source = (
        source_root / "models" / "ConvNext" / "make_model.py"
    ).read_text(encoding="utf-8")
    required_fragments = {
        "train.py": (
            "parser.add_argument('--batchsize', default=8",
            "parser.add_argument('--lr', default=0.01",
            "parser.add_argument('--triplet_loss', default=0.3",
            "parser.add_argument('--block', default=2",
            "parser.add_argument('--epochs', default=200",
            "parser.add_argument('--steps', default=[80,120]",
            "if epoch == num_epochs - 1:",
            "save_network(model, opt.name, 'last')",
        ),
        "optimizers/make_optimizer.py": (
            "'params': base_params, 'lr': 0.3 * opt.lr",
            "weight_decay=5e-4, momentum=0.9, nesterov=True",
            "milestones=opt.steps, gamma=0.1",
        ),
        "models/ConvNext/make_model.py": (
            'convnext_name = "convnext_tiny"',
            "ClassBlock(self.in_planes, num_classes, 0.5",
        ),
    }
    sources = {
        "train.py": train_source,
        "optimizers/make_optimizer.py": optimizer_source,
        "models/ConvNext/make_model.py": model_source,
    }
    for relative, fragments in required_fragments.items():
        absent = [fragment for fragment in fragments if fragment not in sources[relative]]
        if absent:
            raise IntegrityError(
                f"MCCG published recipe validation failed for {relative}: {absent}"
            )


def assert_fit_environment_has_no_test_roots() -> None:
    forbidden = sorted(
        name
        for name in (
            "LGM_MCCG_TEST_ROOT",
            "LGM_QDFL_U1652_TEST_ROOT",
            "LGM_QDFL_SUES_TEST_ROOT",
        )
        if os.environ.get(name)
    )
    if forbidden:
        raise IntegrityError(
            f"Official-test environment variables are forbidden during MCCG fitting: {forbidden}"
        )


def dependency_versions() -> dict[str, str]:
    modules = {
        "matplotlib": "matplotlib",
        "numpy": "numpy",
        "torch": "torch",
        "torchvision": "torchvision",
        "timm": "timm",
        "yaml": "yaml",
    }
    versions: dict[str, str] = {}
    for label, module_name in modules.items():
        module = __import__(module_name)
        versions[label] = str(getattr(module, "__version__", "unknown"))
    versions["pillow"] = importlib.metadata.version("pillow")
    return versions


def runtime_environment(device_index: int) -> dict[str, Any]:
    import torch

    if not torch.cuda.is_available():
        raise IntegrityError("MCCG fitting requires CUDA.")
    if device_index < 0 or device_index >= torch.cuda.device_count():
        raise IntegrityError(f"Invalid CUDA device index: {device_index}")
    properties = torch.cuda.get_device_properties(device_index)
    distributions = sorted(
        {
            (
                str(distribution.metadata.get("Name", "")).strip().lower(),
                distribution.version,
            )
            for distribution in importlib.metadata.distributions()
            if str(distribution.metadata.get("Name", "")).strip()
        }
    )
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "dependencies": dependency_versions(),
        "installed_distributions": {
            "distribution_count": len(distributions),
            "sha256": canonical_object_sha256(distributions),
        },
        "cuda": {
            "device_index": device_index,
            "device_name": properties.name,
            "device_total_memory_bytes": int(properties.total_memory),
            "compute_capability": f"{properties.major}.{properties.minor}",
            "torch_cuda_runtime": torch.version.cuda,
            "cudnn": torch.backends.cudnn.version(),
        },
    }


def build_run_config(args: argparse.Namespace) -> dict[str, Any]:
    if args.seed < 0:
        raise IntegrityError("MCCG seed must be non-negative.")
    patch_manifest = verify_patched_source(
        args.source_root,
        args.patch_manifest,
        expected_source_id="mccg",
    )
    validate_published_recipe(args.source_root)
    class_inventory = training_class_inventory(args.train_root)
    class_inventory["content_inventory"] = training_content_inventory(args.train_root)
    assert_fit_environment_has_no_test_roots()

    registry_path = Path(__file__).with_name("transactions_weight_registry.json")
    weight_registry, weight_registry_sha = load_weight_registry(registry_path)
    if WEIGHT_ID not in weight_registry:
        raise IntegrityError(f"Weight registry omits {WEIGHT_ID}.")
    registered_weight = weight_registry[WEIGHT_ID]
    weight = verify_weight(
        args.convnext_weight,
        str(registered_weight["sha256"]),
        int(registered_weight["bytes"]),
        "MCCG ConvNeXt-T ImageNet-22K/1K initialization",
    )
    return {
        "schema_version": RUN_CONFIG_SCHEMA,
        "method": "MCCG",
        "config_id": "mccg_convnext_tiny",
        "seed": args.seed,
        "source_root": str(args.source_root.resolve()),
        "source_tree_sha256": patch_manifest["patched_tree_sha256"],
        "patch_manifest_path": str(args.patch_manifest.resolve()),
        "patch_manifest_sha256": sha256_file(args.patch_manifest),
        "published_recipe": PUBLISHED_RECIPE,
        "checkpoint_selection": "pre-specified final epoch",
        "official_test_access_during_fit": False,
        "resume_policy": (
            "no in-place resume: the published loop saves model-only state; "
            "a failed attempt is archived and restarted from epoch zero"
        ),
        "determinism": {
            "python_numpy_torch_cuda_seeded": True,
            "cudnn_benchmark": False,
            "cudnn_deterministic": True,
            "torch_deterministic_algorithms": "warn_only",
        },
        "dataset": class_inventory,
        "initialization": {
            **weight,
            "id": WEIGHT_ID,
            "source_url": registered_weight["source_url"],
            "load_contract": registered_weight["load_contract"],
        },
        "initialization_registry_path": str(registry_path.resolve()),
        "initialization_registry_sha256": weight_registry_sha,
        "adapter_path": str(Path(__file__).resolve()),
        "adapter_sha256": adapter_file_hash(),
        "shared_integrity_module_sha256": shared_integrity_module_hash(),
        "environment": runtime_environment(args.device_index),
    }


METRIC_PATTERN = re.compile(
    r"^train Loss: (?P<loss>[-+0-9.eE]+) "
    r"Cls_Loss:(?P<classification_loss>[-+0-9.eE]+) "
    r"KL_Loss:(?P<kl_loss>[-+0-9.eE]+) "
    r"Triplet_Loss (?P<triplet_loss>[-+0-9.eE]+) "
    r"Satellite_Acc: (?P<satellite_accuracy>[-+0-9.eE]+)\s+"
    r"Drone_Acc: (?P<drone_accuracy>[-+0-9.eE]+)$"
)
EPOCH_PATTERN = re.compile(r"^Epoch (?P<epoch>\d+)/199$")


def parse_training_history(log_path: Path) -> dict[str, Any]:
    if not log_path.is_file():
        raise IntegrityError(f"MCCG training log is absent: {log_path}")
    lines = log_path.read_text(encoding="utf-8").splitlines()
    records: list[dict[str, Any]] = []
    current_epoch: int | None = None
    for line in lines:
        epoch_match = EPOCH_PATTERN.match(line)
        if epoch_match:
            if current_epoch is not None:
                raise IntegrityError(
                    f"MCCG epoch {current_epoch} has no paired training metrics."
                )
            epoch = int(epoch_match.group("epoch"))
            if epoch != len(records):
                raise IntegrityError(
                    "MCCG log epoch markers are duplicated, missing, or out of order."
                )
            current_epoch = epoch
            continue
        metric_match = METRIC_PATTERN.match(line)
        if metric_match:
            if current_epoch is None:
                raise IntegrityError(
                    "MCCG training metrics are not paired with an epoch marker."
                )
            records.append(
                {
                    "epoch_index": current_epoch,
                    "completed_epochs": current_epoch + 1,
                    "metrics": {
                        key: float(value)
                        for key, value in metric_match.groupdict().items()
                    },
                }
            )
            current_epoch = None
    if current_epoch is not None:
        raise IntegrityError(f"MCCG epoch {current_epoch} has no paired training metrics.")
    if len(records) != PUBLISHED_RECIPE["epochs"]:
        raise IntegrityError(
            f"MCCG log has {len(records)} paired epoch records, expected 200."
        )
    if [record["epoch_index"] for record in records] != list(
        range(PUBLISHED_RECIPE["epochs"])
    ):
        raise IntegrityError(
            "MCCG log does not contain the contiguous fixed 200-epoch schedule."
        )
    return {
        "schema_version": HISTORY_SCHEMA,
        "expected_epochs": PUBLISHED_RECIPE["epochs"],
        "source_log_path": str(log_path.resolve()),
        "source_log_sha256": sha256_file(log_path),
        "records": records,
    }


def validate_options(
    path: Path,
    expected_output_name: str,
    seed: int,
    train_root: Path,
    device_index: int,
) -> None:
    import yaml

    if not path.is_file():
        raise IntegrityError(f"MCCG options file is absent: {path}")
    options = yaml.safe_load(path.read_text(encoding="utf-8"))
    expected = {
        "name": expected_output_name,
        "gpu_ids": str(device_index),
        "train_all": True,
        "color_jitter": True,
        "views": PUBLISHED_RECIPE["views"],
        "lr": PUBLISHED_RECIPE["learning_rate"],
        "batchsize": PUBLISHED_RECIPE["batch_size"],
        "pad": PUBLISHED_RECIPE["padding"],
        "h": PUBLISHED_RECIPE["image_size"][0],
        "w": PUBLISHED_RECIPE["image_size"][1],
        "erasing_p": PUBLISHED_RECIPE["random_erasing_probability"],
        "DA": PUBLISHED_RECIPE["imagenet_autoaugment"],
        "resnet": False,
        "share": True,
        "resume": False,
        "autocast": PUBLISHED_RECIPE["mixed_precision"],
        "fp16": False,
        "triplet_loss": PUBLISHED_RECIPE["triplet_margin"],
        "epochs": PUBLISHED_RECIPE["epochs"],
        "block": PUBLISHED_RECIPE["classifier_blocks"],
        "sample_num": PUBLISHED_RECIPE["sample_num"],
        "steps": PUBLISHED_RECIPE["scheduler_milestones"],
        "seed": seed,
    }
    for name, value in expected.items():
        if options.get(name) != value:
            raise IntegrityError(
                f"MCCG options {name} mismatch: expected {value!r}, "
                f"got {options.get(name)!r}"
            )
    if Path(str(options.get("data_dir", ""))).resolve() != train_root.resolve():
        raise IntegrityError("MCCG options data_dir differs from the frozen train root.")


def inspect_model_checkpoint(path: Path) -> int:
    import torch

    payload = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
    try:
        if not isinstance(payload, dict) or not payload:
            raise IntegrityError("MCCG final checkpoint is not a non-empty state dictionary.")
        if not all(hasattr(value, "shape") for value in payload.values()):
            raise IntegrityError("MCCG final checkpoint contains non-tensor state.")
        return len(payload)
    finally:
        del payload


def _manifest_with_payload_hash(payload: dict[str, Any]) -> dict[str, Any]:
    return {**payload, "payload_sha256": canonical_object_sha256(payload)}


def validate_completed_fit(
    manifest_path: Path,
    output_dir: Path,
    run_config_sha: str,
    seed: int,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != FIT_MANIFEST_SCHEMA:
        raise IntegrityError("MCCG fit-manifest schema mismatch.")
    payload = dict(manifest)
    declared_hash = payload.pop("payload_sha256", None)
    if declared_hash != canonical_object_sha256(payload):
        raise IntegrityError("MCCG fit-manifest payload hash mismatch.")
    expected = {
        "status": "completed",
        "method": "MCCG",
        "config_id": "mccg_convnext_tiny",
        "seed": seed,
        "run_config_sha256": run_config_sha,
        "completed_epochs": PUBLISHED_RECIPE["epochs"],
        "final_epoch_index": PUBLISHED_RECIPE["epochs"] - 1,
        "official_test_access_during_fit": False,
        "checkpoint_selection": "pre-specified final epoch",
    }
    for name, value in expected.items():
        if manifest.get(name) != value:
            raise IntegrityError(f"MCCG fit-manifest {name} mismatch.")
    expected_paths = {
        "run_config": output_dir / "run_config.json",
        "checkpoint": output_dir / "net_last.pth",
        "history": output_dir / "history.json",
        "runtime_metrics": output_dir / "runtime_metrics.json",
        "training_log": output_dir / "train.txt",
        "options": output_dir / "opts.yaml",
        "source_train_copy": output_dir / "train.py",
        "source_model_copy": output_dir / "model.py",
        "process_stdout": output_dir / "process_stdout.log",
        "process_stderr": output_dir / "process_stderr.log",
    }
    for label, path in expected_paths.items():
        declared_path = Path(manifest[f"{label}_path"]).resolve()
        if declared_path != path.resolve() or not path.is_file():
            raise IntegrityError(f"MCCG {label} path mismatch or artifact is absent.")
        if sha256_file(path) != manifest[f"{label}_sha256"]:
            raise IntegrityError(f"MCCG {label} SHA-256 mismatch.")
    history = json.loads(expected_paths["history"].read_text(encoding="utf-8"))
    if history.get("schema_version") != HISTORY_SCHEMA:
        raise IntegrityError("MCCG completed history schema mismatch.")
    if history.get("expected_epochs") != PUBLISHED_RECIPE["epochs"]:
        raise IntegrityError("MCCG completed history expected-epoch count mismatch.")
    if len(history.get("records", [])) != PUBLISHED_RECIPE["epochs"]:
        raise IntegrityError("MCCG completed history row count mismatch.")
    if history.get("source_log_sha256") != sha256_file(
        expected_paths["training_log"]
    ):
        raise IntegrityError("MCCG history source-log hash mismatch.")
    indices = [
        int(record.get("epoch_index", -1))
        for record in history.get("records", [])
    ]
    if indices != list(range(PUBLISHED_RECIPE["epochs"])):
        raise IntegrityError("MCCG completed history indices are not contiguous.")
    runtime = json.loads(
        expected_paths["runtime_metrics"].read_text(encoding="utf-8")
    )
    if runtime.get("completed_epochs") != PUBLISHED_RECIPE["epochs"]:
        raise IntegrityError("MCCG runtime completion count mismatch.")
    if runtime.get("final_epoch_index") != PUBLISHED_RECIPE["epochs"] - 1:
        raise IntegrityError("MCCG runtime final-epoch index mismatch.")
    if int(runtime.get("peak_gpu_memory_bytes", 0)) <= 0:
        raise IntegrityError("MCCG runtime peak GPU memory is invalid.")
    run_config = json.loads(expected_paths["run_config"].read_text(encoding="utf-8"))
    source_root = Path(run_config["source_root"])
    source_pairs = (
        (expected_paths["source_train_copy"], source_root / "train.py"),
        (
            expected_paths["source_model_copy"],
            source_root / "models" / "ConvNext" / "backbones" / "model_convnext.py",
        ),
    )
    for copied, source in source_pairs:
        if not source.is_file() or sha256_file(copied) != sha256_file(source):
            raise IntegrityError(
                f"MCCG copied source artifact differs from the pinned source: {copied}"
            )
    if inspect_model_checkpoint(expected_paths["checkpoint"]) != int(
        manifest.get("checkpoint_tensor_count", -1)
    ):
        raise IntegrityError("MCCG checkpoint tensor-count mismatch.")
    return manifest


def run_fit(args: argparse.Namespace, run_config: dict[str, Any]) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    run_config_path = output_dir / "run_config.json"
    run_config_sha = write_immutable_json(run_config_path, run_config)
    manifest_path = output_dir / "fit_manifest.json"
    if manifest_path.exists():
        return validate_completed_fit(
            manifest_path, output_dir, run_config_sha, args.seed
        )

    allowed_before_launch = {run_config_path.name}
    retained = [
        path
        for path in output_dir.iterdir()
        if path.name not in allowed_before_launch
    ]
    if retained:
        raise IntegrityError(
            "MCCG output contains non-resumable retained artifacts; archive the "
            f"failed attempt before restarting: {[path.name for path in retained]}"
        )

    assert_fit_environment_has_no_test_roots()
    status_path = output_dir / "status.json"
    started_utc = utc_now()
    atomic_write_json(
        status_path,
        {
            "schema_version": STATUS_SCHEMA,
            "status": "running",
            "run_config_sha256": run_config_sha,
            "attempt_started_utc": started_utc,
        },
    )
    command = [
        sys.executable,
        "-B",
        str((args.source_root / "train.py").resolve()),
        "--name",
        output_dir.name,
        "--data_dir",
        str(args.train_root.resolve()),
        "--gpu_ids",
        str(args.device_index),
        "--views",
        str(PUBLISHED_RECIPE["views"]),
        "--lr",
        str(PUBLISHED_RECIPE["learning_rate"]),
        "--batchsize",
        str(PUBLISHED_RECIPE["batch_size"]),
        "--triplet_loss",
        str(PUBLISHED_RECIPE["triplet_margin"]),
        "--epochs",
        str(PUBLISHED_RECIPE["epochs"]),
        "--seed",
        str(args.seed),
    ]
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONHASHSEED"] = str(args.seed)
    environment["LGM_MCCG_OUTPUT_ROOT"] = str(output_dir.parent)
    environment["LGM_MCCG_CONVNEXT_T_22K_WEIGHTS"] = str(
        args.convnext_weight.resolve()
    )
    old_pythonpath = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = (
        str(args.source_root.resolve())
        if not old_pythonpath
        else str(args.source_root.resolve()) + os.pathsep + old_pythonpath
    )
    stdout_path = output_dir / "process_stdout.log"
    stderr_path = output_dir / "process_stderr.log"
    started = time.perf_counter()
    try:
        with stdout_path.open("x", encoding="utf-8", newline="\n") as stdout, (
            stderr_path.open("x", encoding="utf-8", newline="\n")
        ) as stderr:
            completed = subprocess.run(
                command,
                cwd=args.source_root,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                check=False,
            )
        duration = time.perf_counter() - started
        if completed.returncode != 0:
            raise IntegrityError(
                f"MCCG training returned non-zero exit code {completed.returncode}."
            )
        verify_patched_source(
            args.source_root,
            args.patch_manifest,
            expected_source_id="mccg",
        )

        checkpoint_path = output_dir / "net_last.pth"
        competing = [
            path.name
            for path in output_dir.glob("net_*.pth")
            if path.name != checkpoint_path.name
        ]
        if competing:
            raise IntegrityError(
                f"MCCG produced non-final selected checkpoints: {competing}"
            )
        checkpoint_tensor_count = inspect_model_checkpoint(checkpoint_path)
        log_path = output_dir / "train.txt"
        history = parse_training_history(log_path)
        history_path = output_dir / "history.json"
        write_immutable_json(history_path, history)
        options_path = output_dir / "opts.yaml"
        validate_options(
            options_path,
            output_dir.name,
            args.seed,
            args.train_root,
            args.device_index,
        )
        runtime_path = output_dir / "runtime_metrics.json"
        if not runtime_path.is_file():
            raise IntegrityError("MCCG runtime metrics are absent.")
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
        if int(runtime.get("completed_epochs", -1)) != PUBLISHED_RECIPE["epochs"]:
            raise IntegrityError("MCCG runtime completion count mismatch.")
        source_train_copy = output_dir / "train.py"
        source_model_copy = output_dir / "model.py"
        source_pairs = (
            (source_train_copy, args.source_root / "train.py"),
            (
                source_model_copy,
                args.source_root
                / "models"
                / "ConvNext"
                / "backbones"
                / "model_convnext.py",
            ),
        )
        for copied, source in source_pairs:
            if not copied.is_file() or sha256_file(copied) != sha256_file(source):
                raise IntegrityError(
                    f"MCCG copied source artifact differs from the pinned source: {copied}"
                )

        manifest_payload = {
            "schema_version": FIT_MANIFEST_SCHEMA,
            "status": "completed",
            "method": "MCCG",
            "config_id": "mccg_convnext_tiny",
            "seed": args.seed,
            "run_config_path": str(run_config_path),
            "run_config_sha256": run_config_sha,
            "checkpoint_path": str(checkpoint_path.resolve()),
            "checkpoint_sha256": sha256_file(checkpoint_path),
            "checkpoint_tensor_count": checkpoint_tensor_count,
            "completed_epochs": PUBLISHED_RECIPE["epochs"],
            "final_epoch_index": PUBLISHED_RECIPE["epochs"] - 1,
            "history_path": str(history_path.resolve()),
            "history_sha256": sha256_file(history_path),
            "runtime_metrics_path": str(runtime_path.resolve()),
            "runtime_metrics_sha256": sha256_file(runtime_path),
            "training_log_path": str(log_path.resolve()),
            "training_log_sha256": sha256_file(log_path),
            "options_path": str(options_path.resolve()),
            "options_sha256": sha256_file(options_path),
            "source_train_copy_path": str(source_train_copy.resolve()),
            "source_train_copy_sha256": sha256_file(source_train_copy),
            "source_model_copy_path": str(source_model_copy.resolve()),
            "source_model_copy_sha256": sha256_file(source_model_copy),
            "peak_gpu_memory_bytes": int(runtime["peak_gpu_memory_bytes"]),
            "final_invocation_duration_seconds": duration,
            "process_stdout_path": str(stdout_path.resolve()),
            "process_stdout_sha256": sha256_file(stdout_path),
            "process_stderr_path": str(stderr_path.resolve()),
            "process_stderr_sha256": sha256_file(stderr_path),
            "official_test_access_during_fit": False,
            "checkpoint_selection": "pre-specified final epoch",
            "completed_utc": utc_now(),
            "dependencies": dependency_versions(),
        }
        manifest = _manifest_with_payload_hash(manifest_payload)
        write_immutable_json(manifest_path, manifest)
        manifest = validate_completed_fit(
            manifest_path, output_dir, run_config_sha, args.seed
        )
        atomic_write_json(
            status_path,
            {
                "schema_version": STATUS_SCHEMA,
                "status": "completed",
                "run_config_sha256": run_config_sha,
                "fit_manifest_sha256": sha256_file(manifest_path),
                "completed_utc": manifest["completed_utc"],
            },
        )
        return manifest
    except BaseException as error:
        atomic_write_json(
            status_path,
            {
                "schema_version": STATUS_SCHEMA,
                "status": "failed",
                "run_config_sha256": run_config_sha,
                "attempt_started_utc": started_utc,
                "failed_utc": utc_now(),
                "attempt_duration_seconds": time.perf_counter() - started,
                "error_type": type(error).__name__,
                "error": str(error),
            },
        )
        raise


def add_fit_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--patch-manifest", type=Path, required=True)
    parser.add_argument("--train-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--convnext-weight", type=Path, required=True)
    parser.add_argument("--device-index", type=int, default=0)
    parser.add_argument("--preflight-only", action="store_true")
