"""Integrity and execution helpers for QDFL-framework published baselines."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import random
import sys
import time
from typing import Any

from external_baselines.fetch_and_verify_sources import (
    IntegrityError,
    canonical_tree_hash,
    sha256_file,
)
from external_baselines.source_patching import PATCH_SCHEMA


FIT_MANIFEST_SCHEMA = "lgm-game.qdfl-fit.v3"
RUN_CONFIG_SCHEMA = "lgm-game.qdfl-run-config.v3"
STATUS_SCHEMA = "lgm-game.qdfl-fit-status.v3"
HISTORY_SCHEMA = "lgm-game.qdfl-epoch-history.v3"
RNG_STATE_SCHEMA = "lgm-game.qdfl-rng-state.v1"
EPOCH_AUDIT_STATE_KEY = "lgm-game.qdfl-epoch-audit.v2"
WEIGHT_REGISTRY_SCHEMA = "lgm-game.transactions-initialization-weights.v1"

UNIVERSITY1652_TRAIN_CONTENT_INVENTORY = {
    "mode": "content",
    "sha256": "61852ee531d095ae4fd7507c12555fe9cac130df84a1308cacf00b2ca97bf3a6",
    "file_count": 41214,
    "total_bytes": 2670030871,
    "relative_path_prefix": "train",
}


@dataclass(frozen=True)
class QDFLConfigSpec:
    config_id: str
    method: str
    filename: str
    sha256: str
    epochs: int
    nominal_batch_size: int
    image_size: tuple[int, int]
    backbone_name: str
    components_name: str
    initialization: str


CONFIG_SPECS: dict[str, QDFLConfigSpec] = {
    "qdfl_dinov2_b14": QDFLConfigSpec(
        config_id="qdfl_dinov2_b14",
        method="QDFL",
        filename="dino_b_QDFL.yaml",
        sha256="a862feb327091a213bb0aa0dffffa2ae65d0708443586cee2c1606c744a282e1",
        epochs=160,
        nominal_batch_size=24,
        image_size=(224, 224),
        backbone_name="dinov2_vitb14",
        components_name="QDFL",
        initialization="dinov2_vitb14",
    ),
    "fsra_vit": QDFLConfigSpec(
        config_id="fsra_vit",
        method="FSRA",
        filename="vit_fsra_FSRA.yaml",
        sha256="c31e6ba8fd13d763a90763dfc8d8e9db57420ff97c9338423397a9a07c9db237",
        epochs=120,
        nominal_batch_size=8,
        image_size=(256, 256),
        backbone_name="vit_fsra",
        components_name="FSRA",
        initialization="fsra_vit_base",
    ),
    "sdpl_swinv2_b": QDFLConfigSpec(
        config_id="sdpl_swinv2_b",
        method="SDPL",
        filename="swinv2_b_SDPL.yaml",
        sha256="2ae46e9a7858cdd770435fb4bd045fcf9501ac6d61eaa43e375494c678b618d1",
        epochs=160,
        nominal_batch_size=24,
        image_size=(256, 256),
        backbone_name="swinv2_base",
        components_name="SDPL",
        initialization="swin_v2_b_imagenet1k_v1",
    ),
    "ccr_convnext_b": QDFLConfigSpec(
        config_id="ccr_convnext_b",
        method="CCR",
        filename="convnext_b_CCR.yaml",
        sha256="4201b4748644aa729336df62601e01416b3545436db51006b60f4520432c1bcd",
        epochs=200,
        nominal_batch_size=8,
        image_size=(384, 384),
        backbone_name="convnext_base",
        components_name="CCR",
        initialization="convnext_base_22k_1k_224",
    ),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def canonical_object_sha256(payload: Any) -> str:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    if temporary.exists():
        raise IntegrityError(f"Refusing to overwrite stale temporary file: {temporary}")
    temporary.write_bytes(canonical_json_bytes(payload))
    temporary.replace(path)


def write_immutable_json(path: Path, payload: Any) -> str:
    serialized = canonical_json_bytes(payload)
    digest = hashlib.sha256(serialized).hexdigest()
    if path.exists():
        if path.read_bytes() != serialized:
            raise IntegrityError(f"Existing immutable JSON differs: {path}")
        return digest
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(serialized)
    return digest


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as error:
        raise IntegrityError("PyYAML is required by the QDFL adapter.") from error
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise IntegrityError(f"Configuration must be a mapping: {path}")
    return payload


def validate_official_config(source_root: Path, spec: QDFLConfigSpec) -> tuple[Path, dict[str, Any]]:
    path = source_root / "model_configs" / spec.filename
    if not path.is_file():
        raise IntegrityError(f"Official configuration does not exist: {path}")
    actual_hash = sha256_file(path)
    if actual_hash != spec.sha256:
        raise IntegrityError(
            f"{spec.config_id} configuration SHA-256 mismatch: "
            f"expected {spec.sha256}, got {actual_hash}"
        )
    config = load_yaml(path)
    model_config = config.get("model_configs", {})
    observed = {
        "epochs": config.get("max_epochs"),
        "batch_size": config.get("batch_size"),
        "image_size": tuple(config.get("image_size", [])),
        "backbone_name": model_config.get("backbone_name"),
        "components_name": model_config.get("components_name"),
    }
    expected = {
        "epochs": spec.epochs,
        "batch_size": spec.nominal_batch_size,
        "image_size": spec.image_size,
        "backbone_name": spec.backbone_name,
        "components_name": spec.components_name,
    }
    if observed != expected:
        raise IntegrityError(
            f"{spec.config_id} official configuration semantics changed: "
            f"expected {expected}, got {observed}"
        )
    return path, config


def verify_patched_source(
    source_root: Path,
    patch_manifest_path: Path,
    expected_source_id: str = "qdfl",
) -> dict[str, Any]:
    if not patch_manifest_path.is_file():
        raise IntegrityError(f"Patch manifest does not exist: {patch_manifest_path}")
    manifest = json.loads(patch_manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != PATCH_SCHEMA:
        raise IntegrityError(f"Unsupported patch manifest schema: {manifest.get('schema_version')!r}")
    if manifest.get("source_id") != expected_source_id:
        raise IntegrityError(
            f"Patch manifest is not for {expected_source_id!r}."
        )
    actual_hash, actual_count = canonical_tree_hash(source_root)
    if actual_hash != manifest.get("patched_tree_sha256"):
        raise IntegrityError("Patched QDFL source-tree SHA-256 mismatch.")
    if actual_count != manifest.get("patched_file_count"):
        raise IntegrityError("Patched QDFL source-tree file count mismatch.")
    if Path(manifest["destination"]).resolve() != source_root.resolve():
        raise IntegrityError("Patch manifest destination does not match --source-root.")
    return manifest


def training_class_inventory(train_root: Path, expected_classes: int = 701) -> dict[str, Any]:
    train_root = train_root.resolve(strict=True)
    required_views = ("satellite", "street", "drone")
    class_lists: dict[str, list[str]] = {}
    image_counts: dict[str, int] = {}
    for view in required_views:
        view_root = train_root / view
        if not view_root.is_dir():
            raise IntegrityError(f"Missing University-1652 training view: {view_root}")
        classes = sorted(path.name for path in view_root.iterdir() if path.is_dir())
        class_lists[view] = classes
        image_counts[view] = sum(
            1 for class_name in classes for path in (view_root / class_name).iterdir() if path.is_file()
        )
    reference = class_lists["satellite"]
    if len(reference) != expected_classes:
        raise IntegrityError(
            f"Expected {expected_classes} University-1652 training identities, got {len(reference)}."
        )
    for view in required_views[1:]:
        if class_lists[view] != reference:
            raise IntegrityError(f"Training identity order differs between satellite and {view}.")
    ids_payload = "".join(f"{class_name}\n" for class_name in reference).encode("utf-8")
    return {
        "train_root": str(train_root),
        "class_count": len(reference),
        "class_ids_sha256": hashlib.sha256(ids_payload).hexdigest(),
        "image_counts": image_counts,
        "views": list(required_views),
    }


def training_content_inventory(
    train_root: Path,
    expected: dict[str, Any] | None = UNIVERSITY1652_TRAIN_CONTENT_INVENTORY,
) -> dict[str, Any]:
    """Hash the three official fitting views using the formal path convention."""

    train_root = train_root.resolve(strict=True)
    digest = hashlib.sha256()
    file_count = 0
    total_bytes = 0
    fitting_views = ("satellite", "street", "drone")
    candidates = [
        candidate
        for view in fitting_views
        for candidate in (train_root / view).rglob("*")
        if candidate.is_file()
    ]
    for path in sorted(
        candidates,
        key=lambda candidate: candidate.relative_to(train_root).as_posix(),
    ):
        relative = (
            Path("train") / path.relative_to(train_root)
        ).as_posix()
        size = path.stat().st_size
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        digest.update(sha256_file(path).encode("ascii"))
        digest.update(b"\n")
        file_count += 1
        total_bytes += size
    inventory = {
        "mode": "content",
        "sha256": digest.hexdigest(),
        "file_count": file_count,
        "total_bytes": total_bytes,
        "relative_path_prefix": "train",
    }
    if expected is not None and inventory != expected:
        raise IntegrityError(
            "University-1652 fitting content differs from the frozen inventory: "
            f"expected {expected}, got {inventory}"
        )
    return inventory


def validate_resource_adaptation(spec: QDFLConfigSpec, micro_batch_size: int) -> int:
    if micro_batch_size <= 0:
        raise IntegrityError("Micro-batch size must be positive.")
    if spec.nominal_batch_size % micro_batch_size:
        raise IntegrityError(
            f"{spec.nominal_batch_size} is not divisible by micro-batch size {micro_batch_size}."
        )
    return spec.nominal_batch_size // micro_batch_size


def verify_weight(
    path: Path | None,
    expected_sha256: str,
    expected_bytes: int,
    label: str,
) -> dict[str, Any]:
    if path is None:
        raise IntegrityError(f"{label} requires an explicit local path.")
    if not path.is_file():
        raise IntegrityError(f"{label} does not exist: {path}")
    if path.stat().st_size != expected_bytes:
        raise IntegrityError(
            f"{label} byte-count mismatch: expected {expected_bytes}, "
            f"got {path.stat().st_size}"
        )
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise IntegrityError(f"{label} SHA-256 mismatch: expected {expected_sha256}, got {actual}")
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": actual,
    }


def load_weight_registry(path: Path) -> tuple[dict[str, dict[str, Any]], str]:
    if not path.is_file():
        raise IntegrityError(f"Initialization-weight registry is absent: {path}")
    raw = path.read_bytes()
    registry = json.loads(raw.decode("utf-8"))
    if registry.get("schema_version") != WEIGHT_REGISTRY_SCHEMA:
        raise IntegrityError("Initialization-weight registry schema mismatch.")
    rows = registry.get("weights")
    if not isinstance(rows, list) or not rows:
        raise IntegrityError("Initialization-weight registry has no entries.")
    by_id = {row.get("id"): row for row in rows}
    if len(by_id) != len(rows) or None in by_id:
        raise IntegrityError("Initialization-weight registry IDs are absent or duplicated.")
    required_ids = {spec.initialization for spec in CONFIG_SPECS.values()}
    if not required_ids.issubset(set(by_id)):
        raise IntegrityError(
            "Initialization-weight registry omits QDFL configurations: "
            f"required {sorted(required_ids)}, got {sorted(by_id)}"
        )
    for weight_id, row in by_id.items():
        if len(str(row.get("sha256", ""))) != 64:
            raise IntegrityError(f"{weight_id} registry SHA-256 is invalid.")
        if int(row.get("bytes", 0)) <= 0:
            raise IntegrityError(f"{weight_id} registry byte count is invalid.")
        if not str(row.get("source_url", "")).startswith("https://"):
            raise IntegrityError(f"{weight_id} registry source URL is invalid.")
    return by_id, hashlib.sha256(raw).hexdigest()


def assert_fit_environment_has_no_test_roots() -> None:
    forbidden = [
        name
        for name in ("LGM_QDFL_U1652_TEST_ROOT", "LGM_QDFL_SUES_TEST_ROOT")
        if os.environ.get(name)
    ]
    if forbidden:
        raise IntegrityError(f"Official-test environment variables are forbidden during fitting: {forbidden}")


def dependency_versions() -> dict[str, str]:
    modules = {
        "albumentations": "albumentations",
        "cv2": "cv2",
        "numpy": "numpy",
        "torch": "torch",
        "torchvision": "torchvision",
        "pytorch_lightning": "pytorch_lightning",
        "timm": "timm",
        "transformers": "transformers",
        "pytorch_metric_learning": "pytorch_metric_learning",
        "skimage": "skimage",
        "yaml": "yaml",
    }
    versions: dict[str, str] = {}
    for label, module_name in modules.items():
        module = __import__(module_name)
        versions[label] = str(getattr(module, "__version__", "unknown"))
    return versions


def installed_distribution_fingerprint() -> dict[str, Any]:
    rows = sorted(
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
        "distribution_count": len(rows),
        "sha256": canonical_object_sha256(rows),
    }


def runtime_environment(device_index: int) -> dict[str, Any]:
    import torch

    if not torch.cuda.is_available():
        raise IntegrityError("QDFL fitting requires CUDA, but torch.cuda.is_available() is false.")
    if device_index < 0 or device_index >= torch.cuda.device_count():
        raise IntegrityError(
            f"CUDA device index {device_index} is outside [0, {torch.cuda.device_count()})."
        )
    properties = torch.cuda.get_device_properties(device_index)
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "dependencies": dependency_versions(),
        "installed_distributions": installed_distribution_fingerprint(),
        "cuda": {
            "device_index": device_index,
            "device_name": properties.name,
            "device_total_memory_bytes": int(properties.total_memory),
            "compute_capability": f"{properties.major}.{properties.minor}",
            "torch_cuda_runtime": torch.version.cuda,
            "cudnn": torch.backends.cudnn.version(),
        },
    }


def load_patch_manifest_hash(path: Path) -> str:
    return sha256_file(path)


def adapter_file_hash() -> str:
    return sha256_file(Path(__file__))


def _weight_payload(
    args: argparse.Namespace,
    spec: QDFLConfigSpec,
    registry: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    argument_and_label = {
        "dinov2_vitb14": (
            args.dinov2_weight,
            "DINOv2 ViT-B/14 initialization",
        ),
        "fsra_vit_base": (
            args.fsra_weight,
            "FSRA ViT initialization",
        ),
        "swin_v2_b_imagenet1k_v1": (
            args.swinv2_weight,
            "Swin V2-B ImageNet-1K initialization",
        ),
        "convnext_base_22k_1k_224": (
            args.convnext_weight,
            "ConvNeXt-B ImageNet-22K/1K initialization",
        ),
    }
    if spec.initialization not in argument_and_label:
        raise IntegrityError(
            f"Unsupported initialization specification: {spec.initialization}"
        )
    path, label = argument_and_label[spec.initialization]
    registered = registry[spec.initialization]
    verified = verify_weight(
        path,
        str(registered["sha256"]),
        int(registered["bytes"]),
        label,
    )
    return {
        spec.initialization: {
            **verified,
            "source_url": registered["source_url"],
            "load_contract": registered["load_contract"],
        }
    }


def build_run_config(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    spec = CONFIG_SPECS[args.config_id]
    if args.seed < 0:
        raise IntegrityError("QDFL seed must be non-negative.")
    patch_manifest = verify_patched_source(args.source_root, args.patch_manifest)
    config_path, official_config = validate_official_config(args.source_root, spec)
    inventory = training_class_inventory(args.train_root)
    inventory["content_inventory"] = training_content_inventory(args.train_root)
    accumulate = validate_resource_adaptation(spec, args.micro_batch_size)
    if args.workers < 0:
        raise IntegrityError("Worker count cannot be negative.")
    assert_fit_environment_has_no_test_roots()
    weight_registry_path = Path(__file__).with_name(
        "transactions_weight_registry.json"
    )
    weight_registry, weight_registry_sha = load_weight_registry(
        weight_registry_path
    )
    weights = _weight_payload(args, spec, weight_registry)
    run_config = {
        "schema_version": RUN_CONFIG_SCHEMA,
        "method": spec.method,
        "config_id": spec.config_id,
        "seed": args.seed,
        "source_root": str(args.source_root.resolve()),
        "source_tree_sha256": patch_manifest["patched_tree_sha256"],
        "patch_manifest_path": str(args.patch_manifest.resolve()),
        "patch_manifest_sha256": load_patch_manifest_hash(args.patch_manifest),
        "official_config_path": str(config_path.resolve()),
        "official_config_sha256": spec.sha256,
        "epochs": spec.epochs,
        "checkpoint_selection": "pre-specified final epoch",
        "official_test_access_during_fit": False,
        "resume_policy": (
            "resume only from an adapter-audited full Lightning checkpoint "
            "containing model, optimizer, scheduler, mixed-precision scaler, "
            "loop, epoch-history callback, and Python/NumPy/Torch RNG states"
        ),
        "nominal_batch_size": spec.nominal_batch_size,
        "micro_batch_size": args.micro_batch_size,
        "accumulate_grad_batches": accumulate,
        "effective_optimizer_batch_size": args.micro_batch_size * accumulate,
        "resource_adapted": args.micro_batch_size != spec.nominal_batch_size,
        "runtime_compatibility": {
            "xformers_disabled": True,
            "attention_backend": (
                "upstream DINOv2 standard-PyTorch attention fallback"
            ),
            "reason": (
                "the upstream pinned xFormers build targets torch 2.1 and is "
                "not ABI-compatible with the frozen Windows torch runtime"
            ),
        },
        "image_size": list(spec.image_size),
        "workers": args.workers,
        "precision": "16-mixed",
        "device_index": args.device_index,
        "dataset": inventory,
        "initializations": weights,
        "initialization_registry_path": str(weight_registry_path.resolve()),
        "initialization_registry_sha256": weight_registry_sha,
        "adapter_path": str(Path(__file__).resolve()),
        "adapter_sha256": adapter_file_hash(),
        "environment": runtime_environment(args.device_index),
    }
    return run_config, official_config


def _load_qdfl_runtime(source_root: Path) -> tuple[Any, Any]:
    # The patched source tree is hash-pinned. Runtime imports must not add
    # __pycache__ files and thereby mutate that tree between registered fits.
    sys.dont_write_bytecode = True
    source_string = str(source_root.resolve())
    if source_string not in sys.path:
        sys.path.insert(0, source_string)
    from datasets.train.U1652_dataloader import U1652DataModule

    module_path = source_root / "plModules" / "U1652_baseline.py"
    module_spec = importlib.util.spec_from_file_location("lgm_qdfl_u1652_baseline", module_path)
    if module_spec is None or module_spec.loader is None:
        raise IntegrityError(f"Cannot load QDFL model module: {module_path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return U1652DataModule, module.U1652_model


def _capture_rng_state() -> dict[str, Any]:
    import numpy as np
    import torch

    return {
        "schema_version": RNG_STATE_SCHEMA,
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch_cpu": torch.get_rng_state(),
        "torch_cuda": torch.cuda.get_rng_state_all(),
    }


def _validate_rng_state(state: Any) -> None:
    import torch

    if not isinstance(state, dict) or state.get("schema_version") != RNG_STATE_SCHEMA:
        raise IntegrityError("QDFL checkpoint RNG-state schema mismatch.")
    python_state = state.get("python")
    numpy_state = state.get("numpy")
    torch_cpu = state.get("torch_cpu")
    torch_cuda = state.get("torch_cuda")
    if not isinstance(python_state, tuple) or len(python_state) != 3:
        raise IntegrityError("QDFL checkpoint omits a valid Python RNG state.")
    if not isinstance(numpy_state, tuple) or len(numpy_state) != 5:
        raise IntegrityError("QDFL checkpoint omits a valid NumPy RNG state.")
    if not isinstance(torch_cpu, torch.Tensor) or torch_cpu.dtype != torch.uint8:
        raise IntegrityError("QDFL checkpoint omits a valid Torch CPU RNG state.")
    if (
        not isinstance(torch_cuda, list)
        or not torch_cuda
        or not all(
            isinstance(value, torch.Tensor) and value.dtype == torch.uint8
            for value in torch_cuda
        )
    ):
        raise IntegrityError("QDFL checkpoint omits valid Torch CUDA RNG states.")


def _restore_rng_state(state: dict[str, Any]) -> None:
    import numpy as np
    import torch

    _validate_rng_state(state)
    if len(state["torch_cuda"]) != torch.cuda.device_count():
        raise IntegrityError(
            "QDFL checkpoint CUDA RNG-state count differs from the current device count."
        )
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.set_rng_state(state["torch_cpu"])
    torch.cuda.set_rng_state_all(state["torch_cuda"])


def _make_epoch_audit_callback(pl: Any, history_path: Path, expected_epochs: int) -> Any:
    class EpochAuditCallback(pl.Callback):
        def __init__(self) -> None:
            super().__init__()
            self.records: list[dict[str, Any]] = []
            self.restored_rng_state: dict[str, Any] | None = None

        @property
        def state_key(self) -> str:
            return EPOCH_AUDIT_STATE_KEY

        def state_dict(self) -> dict[str, Any]:
            return {
                "schema_version": EPOCH_AUDIT_STATE_KEY,
                "records": self.records,
                "rng_state": _capture_rng_state(),
            }

        def load_state_dict(self, state_dict: dict[str, Any]) -> None:
            if state_dict.get("schema_version") != EPOCH_AUDIT_STATE_KEY:
                raise IntegrityError("QDFL epoch-audit callback-state schema mismatch.")
            self.records = list(state_dict.get("records", []))
            _validate_rng_state(state_dict.get("rng_state"))
            self.restored_rng_state = state_dict["rng_state"]

        def on_fit_start(self, trainer: Any, pl_module: Any) -> None:
            if history_path.exists():
                disk = json.loads(history_path.read_text(encoding="utf-8"))
                if disk.get("records") != self.records:
                    raise IntegrityError("Epoch history differs from callback state restored by checkpoint.")
            elif self.records:
                raise IntegrityError("Checkpoint contains epoch history but history.json is absent.")
            if self.records:
                if self.restored_rng_state is None:
                    raise IntegrityError("Resumed QDFL fit has no restorable RNG state.")
                _restore_rng_state(self.restored_rng_state)
            elif self.restored_rng_state is not None:
                raise IntegrityError(
                    "QDFL checkpoint RNG state exists without completed epoch history."
                )

        def on_train_epoch_end(self, trainer: Any, pl_module: Any) -> None:
            metrics: dict[str, float] = {}
            for name, value in trainer.callback_metrics.items():
                if hasattr(value, "numel") and value.numel() == 1:
                    metrics[name] = float(value.detach().cpu().item())
            record = {
                "epoch_index": int(trainer.current_epoch),
                "completed_epochs": int(trainer.current_epoch) + 1,
                "global_step": int(trainer.global_step),
                "metrics": metrics,
            }
            if self.records and record["epoch_index"] != self.records[-1]["epoch_index"] + 1:
                raise IntegrityError("Epoch audit sequence is not contiguous.")
            if not self.records and record["epoch_index"] != 0:
                raise IntegrityError("Epoch audit does not start at epoch zero.")
            self.records.append(record)
            atomic_write_json(
                history_path,
                {
                    "schema_version": HISTORY_SCHEMA,
                    "expected_epochs": expected_epochs,
                    "records": self.records,
                },
            )

    return EpochAuditCallback()


def audit_full_checkpoint(path: Path) -> dict[str, Any]:
    import torch

    payload = torch.load(
        path,
        map_location="cpu",
        weights_only=False,
        mmap=True,
    )
    try:
        if not isinstance(payload, dict):
            raise IntegrityError("QDFL checkpoint is not a mapping.")
        required = (
            "epoch",
            "global_step",
            "pytorch-lightning_version",
            "state_dict",
            "loops",
            "callbacks",
            "optimizer_states",
            "lr_schedulers",
            "MixedPrecision",
        )
        missing = [name for name in required if name not in payload]
        if missing:
            raise IntegrityError(
                f"QDFL checkpoint is not full-state; missing fields: {missing}"
            )
        if not isinstance(payload["state_dict"], dict) or not payload["state_dict"]:
            raise IntegrityError("QDFL checkpoint model state is empty.")
        if not isinstance(payload["loops"], dict) or not payload["loops"]:
            raise IntegrityError("QDFL checkpoint loop state is empty.")
        if (
            not isinstance(payload["optimizer_states"], list)
            or len(payload["optimizer_states"]) != 1
            or not isinstance(payload["optimizer_states"][0], dict)
            or not payload["optimizer_states"][0]
        ):
            raise IntegrityError("QDFL checkpoint optimizer state is absent or ambiguous.")
        if (
            not isinstance(payload["lr_schedulers"], list)
            or len(payload["lr_schedulers"]) != 1
            or not isinstance(payload["lr_schedulers"][0], dict)
            or not payload["lr_schedulers"][0]
        ):
            raise IntegrityError("QDFL checkpoint scheduler state is absent or ambiguous.")
        if not isinstance(payload["MixedPrecision"], dict) or not payload["MixedPrecision"]:
            raise IntegrityError("QDFL checkpoint mixed-precision scaler state is empty.")
        callbacks = payload["callbacks"]
        if not isinstance(callbacks, dict) or EPOCH_AUDIT_STATE_KEY not in callbacks:
            raise IntegrityError("QDFL checkpoint omits the epoch-audit callback state.")
        callback_state = callbacks[EPOCH_AUDIT_STATE_KEY]
        if (
            not isinstance(callback_state, dict)
            or callback_state.get("schema_version") != EPOCH_AUDIT_STATE_KEY
        ):
            raise IntegrityError("QDFL checkpoint epoch-audit state is invalid.")
        records = callback_state.get("records")
        if not isinstance(records, list) or not records:
            raise IntegrityError("QDFL checkpoint epoch-audit history is empty.")
        epoch = int(payload["epoch"])
        global_step = int(payload["global_step"])
        if len(records) != epoch + 1:
            raise IntegrityError(
                "QDFL checkpoint epoch and callback-history length are inconsistent."
            )
        if int(records[-1].get("epoch_index", -1)) != epoch:
            raise IntegrityError(
                "QDFL checkpoint epoch and callback-history index are inconsistent."
            )
        if int(records[-1].get("global_step", -1)) != global_step:
            raise IntegrityError(
                "QDFL checkpoint global step and callback history are inconsistent."
            )
        _validate_rng_state(callback_state.get("rng_state"))
        return {
            "epoch": epoch,
            "global_step": global_step,
            "model_state_tensor_count": len(payload["state_dict"]),
            "optimizer_state_count": len(payload["optimizer_states"]),
            "scheduler_state_count": len(payload["lr_schedulers"]),
            "precision_state_key": "MixedPrecision",
            "epoch_audit_state_key": EPOCH_AUDIT_STATE_KEY,
            "rng_state_schema": RNG_STATE_SCHEMA,
        }
    finally:
        del payload


def _checkpoint_epoch(path: Path) -> tuple[int, int]:
    audit = audit_full_checkpoint(path)
    return int(audit["epoch"]), int(audit["global_step"])


def validate_epoch_history(path: Path, expected_epochs: int) -> dict[str, Any]:
    if not path.is_file():
        raise IntegrityError(f"Epoch history is absent: {path}")
    history = json.loads(path.read_text(encoding="utf-8"))
    if history.get("schema_version") != HISTORY_SCHEMA:
        raise IntegrityError("Epoch history schema mismatch.")
    if int(history.get("expected_epochs", -1)) != expected_epochs:
        raise IntegrityError("Epoch history expected-epoch count mismatch.")
    records = history.get("records")
    if not isinstance(records, list) or len(records) != expected_epochs:
        raise IntegrityError("Epoch history does not contain one row per epoch.")
    previous_global_step = -1
    for index, record in enumerate(records):
        if int(record.get("epoch_index", -1)) != index:
            raise IntegrityError("Epoch history indices are not contiguous.")
        if int(record.get("completed_epochs", -1)) != index + 1:
            raise IntegrityError("Epoch history completed-epoch count is inconsistent.")
        global_step = int(record.get("global_step", -1))
        if global_step <= previous_global_step:
            raise IntegrityError("Epoch history global steps are not strictly increasing.")
        previous_global_step = global_step
    return history


def validate_completed_fit(
    *,
    manifest_path: Path,
    output_dir: Path,
    spec: QDFLConfigSpec,
    seed: int,
    run_config_sha: str,
) -> dict[str, Any]:
    if not manifest_path.is_file():
        raise IntegrityError(f"Completed fit manifest is absent: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != FIT_MANIFEST_SCHEMA:
        raise IntegrityError("Completed fit manifest schema mismatch.")
    payload = dict(manifest)
    declared_payload_sha = payload.pop("payload_sha256", None)
    if declared_payload_sha != canonical_object_sha256(payload):
        raise IntegrityError("Completed fit manifest payload hash mismatch.")
    expected_scalars = {
        "status": "completed",
        "method": spec.method,
        "config_id": spec.config_id,
        "seed": seed,
        "run_config_sha256": run_config_sha,
        "checkpoint_epoch_index": spec.epochs - 1,
        "completed_epochs": spec.epochs,
        "official_test_access_during_fit": False,
        "checkpoint_selection": "pre-specified final epoch",
    }
    for name, expected in expected_scalars.items():
        if manifest.get(name) != expected:
            raise IntegrityError(
                f"Completed fit manifest {name} mismatch: "
                f"expected {expected!r}, got {manifest.get(name)!r}"
            )

    expected_config = (output_dir / "run_config.json").resolve()
    expected_checkpoint = (output_dir / "checkpoints" / "last.ckpt").resolve()
    expected_history = (output_dir / "history.json").resolve()
    if Path(manifest.get("run_config_path", "")).resolve() != expected_config:
        raise IntegrityError("Completed fit manifest run-config path mismatch.")
    if Path(manifest.get("checkpoint_path", "")).resolve() != expected_checkpoint:
        raise IntegrityError("Completed fit manifest checkpoint path mismatch.")
    if Path(manifest.get("history_path", "")).resolve() != expected_history:
        raise IntegrityError("Completed fit manifest history path mismatch.")
    for label, path, hash_field in (
        ("run configuration", expected_config, "run_config_sha256"),
        ("checkpoint", expected_checkpoint, "checkpoint_sha256"),
        ("epoch history", expected_history, "history_sha256"),
    ):
        if not path.is_file():
            raise IntegrityError(f"Completed fit {label} is absent: {path}")
        if sha256_file(path) != manifest.get(hash_field):
            raise IntegrityError(f"Completed fit {label} SHA-256 mismatch.")

    history = validate_epoch_history(expected_history, spec.epochs)
    checkpoint_epoch, checkpoint_step = _checkpoint_epoch(expected_checkpoint)
    if checkpoint_epoch != spec.epochs - 1:
        raise IntegrityError("Completed fit checkpoint epoch mismatch.")
    if checkpoint_step != int(manifest.get("global_step", -1)):
        raise IntegrityError("Completed fit checkpoint global-step mismatch.")
    if checkpoint_step != int(history["records"][-1]["global_step"]):
        raise IntegrityError("Checkpoint and epoch-history global steps differ.")
    return manifest


def run_fit(args: argparse.Namespace, run_config: dict[str, Any], official_config: dict[str, Any]) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    spec = CONFIG_SPECS[args.config_id]
    run_config_path = output_dir / "run_config.json"
    run_config_sha = write_immutable_json(run_config_path, run_config)
    complete_path = output_dir / "fit_manifest.json"
    if complete_path.exists():
        return validate_completed_fit(
            manifest_path=complete_path,
            output_dir=output_dir,
            spec=spec,
            seed=args.seed,
            run_config_sha=run_config_sha,
        )

    checkpoints = output_dir / "checkpoints"
    history_path = output_dir / "history.json"
    last_checkpoint = checkpoints / "last.ckpt"
    if args.resume == "auto" and last_checkpoint.exists():
        resume_path: str | None = str(last_checkpoint)
    elif args.resume == "none" and last_checkpoint.exists():
        raise IntegrityError("Checkpoint exists but --resume=none was requested.")
    else:
        resume_path = None

    if resume_path is None:
        retained = [
            path
            for path in (history_path, output_dir / "status.json")
            if path.exists()
        ]
        if checkpoints.exists() and any(checkpoints.iterdir()):
            retained.append(checkpoints)
        if retained:
            names = ", ".join(path.name for path in retained)
            raise IntegrityError(
                "A failed fit left non-resumable artifacts but no last.ckpt "
                f"({names}); archive the complete attempt before restarting."
            )

    status_path = output_dir / "status.json"
    attempt_started_utc = utc_now()
    atomic_write_json(
        status_path,
        {
            "schema_version": STATUS_SCHEMA,
            "status": "running",
            "run_config_sha256": run_config_sha,
            "attempt_started_utc": attempt_started_utc,
            "resume_checkpoint": resume_path,
            "resume_checkpoint_sha256": (
                sha256_file(last_checkpoint) if resume_path is not None else None
            ),
        },
    )
    started = time.perf_counter()
    try:
        import pytorch_lightning as pl
        import torch
        from pytorch_lightning.callbacks import ModelCheckpoint

        assert_fit_environment_has_no_test_roots()
        os.environ["XFORMERS_DISABLED"] = "1"
        os.environ["LGM_QDFL_U1652_TRAIN_ROOT"] = str(args.train_root.resolve())
        weight_environment = (
            ("dinov2_weight", "LGM_QDFL_DINOV2_VITB14_WEIGHTS"),
            ("fsra_weight", "LGM_QDFL_FSRA_WEIGHTS"),
            ("swinv2_weight", "LGM_QDFL_SWINV2_B_WEIGHTS"),
            ("convnext_weight", "LGM_QDFL_CONVNEXT_B_22K_WEIGHTS"),
        )
        for attribute, environment_name in weight_environment:
            value = getattr(args, attribute)
            if value is not None:
                os.environ[environment_name] = str(value.resolve())

        pl.seed_everything(args.seed, workers=True)
        torch.cuda.set_device(args.device_index)
        torch.cuda.reset_peak_memory_stats(args.device_index)
        U1652DataModule, U1652Model = _load_qdfl_runtime(args.source_root)
        model_options = dict(official_config["model_configs"])
        model = U1652Model(**model_options)
        data_module = U1652DataModule(
            batch_size=args.micro_batch_size,
            image_size=official_config["image_size"],
            sample_num=official_config["sample_num"],
            num_workers=args.workers,
            DAC_sampling=official_config["DAC_sampling"],
            drop_last=official_config.get("drop_last", True),
            show_data_stats=True,
            sources=["satellite", "street", "drone"],
        )
        verify_patched_source(args.source_root, args.patch_manifest)

        checkpoint_callback = ModelCheckpoint(
            dirpath=checkpoints,
            save_last=True,
            save_top_k=0,
            every_n_epochs=1,
            save_on_train_epoch_end=True,
            save_weights_only=False,
        )
        audit_callback = _make_epoch_audit_callback(pl, history_path, spec.epochs)
        trainer = pl.Trainer(
            accelerator="gpu",
            devices=[args.device_index],
            default_root_dir=output_dir,
            enable_checkpointing=True,
            max_epochs=spec.epochs,
            precision="16-mixed",
            callbacks=[audit_callback, checkpoint_callback],
            deterministic="warn",
            benchmark=False,
            logger=False,
            log_every_n_steps=10,
            accumulate_grad_batches=run_config["accumulate_grad_batches"],
            num_sanity_val_steps=0,
            limit_val_batches=0,
            enable_progress_bar=True,
        )
        trainer.fit(model=model, datamodule=data_module, ckpt_path=resume_path)
        duration = time.perf_counter() - started

        if not last_checkpoint.is_file():
            raise IntegrityError("Final last.ckpt was not produced.")
        checkpoint_epoch, global_step = _checkpoint_epoch(last_checkpoint)
        if checkpoint_epoch != spec.epochs - 1:
            raise IntegrityError(
                f"Final checkpoint epoch mismatch: expected {spec.epochs - 1}, "
                f"got {checkpoint_epoch}"
            )
        history = validate_epoch_history(history_path, spec.epochs)
        if int(history["records"][-1]["global_step"]) != global_step:
            raise IntegrityError("Final checkpoint and epoch-history global steps differ.")

        manifest_payload = {
            "schema_version": FIT_MANIFEST_SCHEMA,
            "status": "completed",
            "method": spec.method,
            "config_id": spec.config_id,
            "seed": args.seed,
            "run_config_path": str(run_config_path),
            "run_config_sha256": run_config_sha,
            "checkpoint_path": str(last_checkpoint.resolve()),
            "checkpoint_sha256": sha256_file(last_checkpoint),
            "checkpoint_epoch_index": checkpoint_epoch,
            "completed_epochs": spec.epochs,
            "global_step": global_step,
            "history_path": str(history_path.resolve()),
            "history_sha256": sha256_file(history_path),
            "final_invocation_duration_seconds": duration,
            "resumed_from_checkpoint": resume_path is not None,
            "peak_gpu_memory_bytes": int(
                torch.cuda.max_memory_allocated(args.device_index)
            ),
            "official_test_access_during_fit": False,
            "checkpoint_selection": "pre-specified final epoch",
            "completed_utc": utc_now(),
            "dependencies": dependency_versions(),
        }
        manifest = {
            **manifest_payload,
            "payload_sha256": canonical_object_sha256(manifest_payload),
        }
        write_immutable_json(complete_path, manifest)
        manifest = validate_completed_fit(
            manifest_path=complete_path,
            output_dir=output_dir,
            spec=spec,
            seed=args.seed,
            run_config_sha=run_config_sha,
        )
        atomic_write_json(
            status_path,
            {
                "schema_version": STATUS_SCHEMA,
                "status": "completed",
                "run_config_sha256": run_config_sha,
                "fit_manifest_sha256": sha256_file(complete_path),
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
                "attempt_started_utc": attempt_started_utc,
                "failed_utc": utc_now(),
                "attempt_duration_seconds": time.perf_counter() - started,
                "resume_checkpoint": resume_path,
                "error_type": type(error).__name__,
                "error": str(error),
            },
        )
        raise


def add_fit_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config-id", choices=sorted(CONFIG_SPECS), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--patch-manifest", type=Path, required=True)
    parser.add_argument("--train-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--micro-batch-size", type=int, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--device-index", type=int, default=0)
    parser.add_argument("--resume", choices=("none", "auto"), default="auto")
    parser.add_argument("--dinov2-weight", type=Path)
    parser.add_argument("--fsra-weight", type=Path)
    parser.add_argument("--swinv2-weight", type=Path)
    parser.add_argument("--convnext-weight", type=Path)
    parser.add_argument("--preflight-only", action="store_true")
