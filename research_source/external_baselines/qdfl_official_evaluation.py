"""Official full-query University-1652 evaluation for QDFL-framework fits.

The adapter is deliberately fail-closed.  It verifies the immutable source,
all seven completed T1 fits, the selected final-epoch fit, and every local
initialization file before it reads the official test split.
"""

from __future__ import annotations

import argparse
import gc
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import random
import sys
import time
from typing import Any, Mapping

import numpy as np

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from external_baselines.fetch_and_verify_sources import IntegrityError
from external_baselines.official_descriptor_evaluation import (
    DescriptorEvaluationError,
    DescriptorTask,
    EVALUATION_CONFIG_SCHEMA,
    FrozenImageView,
    SUES200_ALTITUDES,
    begin_evaluation_output,
    complete_evaluation_output,
    descriptor_sha256,
    evaluate_descriptor_task,
    mark_evaluation_failed,
    scan_sues200_official_test,
    scan_university1652_official_test,
    sha256_file,
    validate_all_fits_gate,
    validate_completed_evaluation,
    validate_sues200_test_inventory,
    validate_test_inventory_gate,
    validate_university1652_test_inventory,
)
from external_baselines.qdfl_adapter import (
    CONFIG_SPECS,
    canonical_object_sha256,
    load_weight_registry,
    validate_completed_fit,
    validate_official_config,
    verify_patched_source,
    verify_weight,
)


ADAPTER_SCHEMA = "lgm-game.qdfl-official-evaluation.v1"
EXPECTED_TEST_SIZE = {
    "qdfl_dinov2_b14": (280, 280),
    "fsra_vit": (256, 256),
    "sdpl_swinv2_b": (256, 256),
    "ccr_convnext_b": (384, 384),
}
WEIGHT_ARGUMENTS = {
    "dinov2_vitb14": (
        "dinov2_weight",
        "LGM_QDFL_DINOV2_VITB14_WEIGHTS",
        "DINOv2 ViT-B/14 initialization",
    ),
    "fsra_vit_base": (
        "fsra_weight",
        "LGM_QDFL_FSRA_WEIGHTS",
        "FSRA ViT initialization",
    ),
    "swin_v2_b_imagenet1k_v1": (
        "swinv2_weight",
        "LGM_QDFL_SWINV2_B_WEIGHTS",
        "Swin V2-B ImageNet-1K initialization",
    ),
    "convnext_base_22k_1k_224": (
        "convnext_weight",
        "LGM_QDFL_CONVNEXT_B_22K_WEIGHTS",
        "ConvNeXt-B ImageNet-22K/1K initialization",
    ),
}


class FrozenPathDataset:
    """Minimal deterministic dataset over a previously audited image order."""

    def __init__(self, view: FrozenImageView, transform: Any):
        self.view = view
        self.transform = transform

    def __len__(self) -> int:
        return len(self.view.paths)

    def __getitem__(self, index: int) -> tuple[Any, int]:
        from PIL import Image

        path = self.view.paths[index]
        with Image.open(path) as source:
            image = source.convert("RGB")
        return self.transform(image), index


def verify_registered_weights(args: argparse.Namespace) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, str],
    str,
]:
    registry_path = Path(__file__).with_name(
        "transactions_weight_registry.json"
    )
    registry, registry_sha = load_weight_registry(registry_path)
    verified: dict[str, dict[str, Any]] = {}
    environment: dict[str, str] = {}
    for weight_id, (argument, variable, label) in WEIGHT_ARGUMENTS.items():
        row = registry[weight_id]
        path = getattr(args, argument)
        evidence = verify_weight(
            path,
            str(row["sha256"]),
            int(row["bytes"]),
            label,
        )
        verified[weight_id] = {
            **evidence,
            "source_url": row["source_url"],
            "load_contract": row["load_contract"],
        }
        environment[variable] = str(path.resolve())
    return verified, environment, registry_sha


def validate_fit_gate(args: argparse.Namespace) -> dict[str, Any]:
    if args.config_id not in CONFIG_SPECS:
        raise IntegrityError(f"Unknown QDFL configuration: {args.config_id}")
    spec = CONFIG_SPECS[args.config_id]
    if args.seed < 0:
        raise IntegrityError("Evaluation seed must be non-negative.")
    patch = verify_patched_source(args.source_root, args.patch_manifest)
    config_path, official_config = validate_official_config(
        args.source_root,
        spec,
    )
    observed_test_size = tuple(official_config.get("test_size", ()))
    expected_test_size = EXPECTED_TEST_SIZE[args.config_id]
    if observed_test_size != expected_test_size:
        raise IntegrityError(
            f"{args.config_id} official test size changed: "
            f"expected {expected_test_size}, got {observed_test_size}."
        )

    fit_dir = args.fit_dir.resolve(strict=True)
    run_config_path = fit_dir / "run_config.json"
    fit_manifest_path = fit_dir / "fit_manifest.json"
    run_config_sha = sha256_file(run_config_path)
    fit_manifest = validate_completed_fit(
        manifest_path=fit_manifest_path,
        output_dir=fit_dir,
        spec=spec,
        seed=args.seed,
        run_config_sha=run_config_sha,
    )
    run_config = json.loads(run_config_path.read_text(encoding="utf-8"))
    expected_run_config = {
        "method": spec.method,
        "config_id": args.config_id,
        "seed": args.seed,
        "source_tree_sha256": patch["patched_tree_sha256"],
        "official_config_sha256": spec.sha256,
        "official_test_access_during_fit": False,
        "checkpoint_selection": "pre-specified final epoch",
    }
    for field, expected in expected_run_config.items():
        if run_config.get(field) != expected:
            raise IntegrityError(
                f"QDFL fit run configuration {field} changed: "
                f"expected {expected!r}, got {run_config.get(field)!r}."
            )
    if (
        Path(str(run_config.get("source_root", ""))).resolve()
        != args.source_root.resolve()
        or Path(str(run_config.get("official_config_path", ""))).resolve()
        != config_path.resolve()
        or run_config.get("patch_manifest_sha256")
        != sha256_file(args.patch_manifest)
    ):
        raise IntegrityError("QDFL fit source/configuration path evidence changed.")

    checkpoint_path = fit_dir / "checkpoints" / "last.ckpt"
    run_id = f"{args.config_id}/seed_{args.seed}"
    all_fits_gate, gate_row = validate_all_fits_gate(
        args.all_fits_gate,
        run_id=run_id,
        fit_manifest_path=fit_manifest_path,
        checkpoint_path=checkpoint_path,
    )
    weights, weight_environment, weight_registry_sha = (
        verify_registered_weights(args)
    )
    return {
        "spec": spec,
        "patch": patch,
        "config_path": config_path,
        "official_config": official_config,
        "fit_dir": fit_dir,
        "run_config_path": run_config_path,
        "run_config_sha256": run_config_sha,
        "run_config": run_config,
        "fit_manifest_path": fit_manifest_path,
        "fit_manifest": fit_manifest,
        "checkpoint_path": checkpoint_path,
        "all_fits_gate": all_fits_gate,
        "all_fits_gate_row": gate_row,
        "weights": weights,
        "weight_environment": weight_environment,
        "weight_registry_sha256": weight_registry_sha,
        "test_size": expected_test_size,
        "run_id": run_id,
    }


def qdfl_postprocess(
    output: Any,
    mirrored_output: Any | None = None,
) -> Any:
    """Reproduce the upstream QDFL descriptor normalization exactly."""

    import torch

    if not isinstance(output, torch.Tensor) or output.ndim < 2:
        raise DescriptorEvaluationError(
            "QDFL model output is not a descriptor tensor."
        )
    value = output.detach().to(device="cpu", dtype=torch.float32)
    norm = torch.linalg.vector_norm(value, ord=2, dim=1, keepdim=True)
    if not torch.isfinite(norm).all() or torch.any(norm <= 0):
        raise DescriptorEvaluationError("QDFL descriptor norm is invalid.")
    value = value / norm.expand_as(value)
    if mirrored_output is not None:
        if (
            not isinstance(mirrored_output, torch.Tensor)
            or mirrored_output.shape != output.shape
        ):
            raise DescriptorEvaluationError(
                "QDFL mirrored descriptor shape changed."
            )
        # The public extractor adds the raw mirrored output to the normalized
        # original output, then normalizes the sum along descriptor dimension.
        value = value + mirrored_output.detach().to(
            device="cpu",
            dtype=torch.float32,
        )
        norm = torch.linalg.vector_norm(value, ord=2, dim=1, keepdim=True)
        if not torch.isfinite(norm).all() or torch.any(norm <= 0):
            raise DescriptorEvaluationError(
                "QDFL flip-augmented descriptor norm is invalid."
            )
        value = value / norm.expand_as(value)
    return value.reshape(value.shape[0], -1).contiguous()


def extract_qdfl_descriptors(
    model: Any,
    dataloader: Any,
    device: Any,
    *,
    horizontal_flip: bool = True,
) -> np.ndarray:
    import torch

    descriptors: list[Any] = []
    expected_index = 0
    model.eval()
    with torch.inference_mode():
        for images, indices in dataloader:
            observed = [int(value) for value in indices.tolist()]
            expected = list(
                range(expected_index, expected_index + len(observed))
            )
            if observed != expected:
                raise DescriptorEvaluationError(
                    "QDFL dataloader order differs from the frozen path order."
                )
            expected_index += len(observed)
            images = images.to(device=device, non_blocking=True)
            output = model(images)
            mirrored = model(torch.flip(images, dims=(3,))) if horizontal_flip else None
            descriptors.append(qdfl_postprocess(output, mirrored))
            del images, output, mirrored
    if expected_index != len(dataloader.dataset):
        raise DescriptorEvaluationError(
            "QDFL descriptor extraction omitted official images."
        )
    result = torch.cat(descriptors, dim=0)
    if result.shape[0] != expected_index or not torch.isfinite(result).all():
        raise DescriptorEvaluationError(
            "QDFL descriptor matrix is incomplete or non-finite."
        )
    return np.ascontiguousarray(result.numpy(), dtype=np.float32)


def build_transform(test_size: tuple[int, int]) -> Any:
    from torchvision import transforms

    return transforms.Compose(
        [
            transforms.Resize(
                test_size,
                interpolation=transforms.InterpolationMode.BICUBIC,
            ),
            transforms.ToTensor(),
            transforms.Normalize(
                [0.485, 0.456, 0.406],
                [0.229, 0.224, 0.225],
            ),
        ]
    )


def load_model(gate: Mapping[str, Any], device: Any) -> Any:
    import torch

    source_root = Path(gate["patch"]["destination"]).resolve()
    source_text = str(source_root)
    if source_text in sys.path:
        raise IntegrityError("Pinned QDFL source is already present on sys.path.")
    sys.path.insert(0, source_text)
    try:
        module = importlib.import_module("plModules.U1652_baseline")
        model_class = getattr(module, "U1652_model")
        model = model_class(**gate["official_config"]["model_configs"])
    finally:
        if sys.path[0] == source_text:
            sys.path.pop(0)
    checkpoint = torch.load(
        gate["checkpoint_path"],
        map_location="cpu",
        weights_only=True,
        mmap=True,
    )
    try:
        if not isinstance(checkpoint, Mapping):
            raise IntegrityError("QDFL checkpoint is not a mapping.")
        state = checkpoint.get("state_dict")
        if not isinstance(state, Mapping) or not state:
            raise IntegrityError("QDFL checkpoint model state is absent.")
        model.load_state_dict(state, strict=True)
    finally:
        del checkpoint
    return model.eval().to(device)


def set_determinism(seed: int, device_index: int) -> Any:
    import torch

    if not torch.cuda.is_available():
        raise IntegrityError("QDFL official evaluation requires CUDA.")
    if device_index < 0 or device_index >= torch.cuda.device_count():
        raise IntegrityError(f"Invalid CUDA device index: {device_index}")
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.cuda.set_device(device_index)
    return torch.device(f"cuda:{device_index}")


def runtime_environment(device: Any) -> dict[str, Any]:
    import torch
    import torchvision

    properties = torch.cuda.get_device_properties(device)
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "torch": torch.__version__,
        "torchvision": torchvision.__version__,
        "pillow": importlib.metadata.version("pillow"),
        "cuda": {
            "device_index": device.index,
            "device_name": properties.name,
            "device_total_memory_bytes": int(properties.total_memory),
            "compute_capability": f"{properties.major}.{properties.minor}",
            "torch_cuda_runtime": torch.version.cuda,
            "cudnn": torch.backends.cudnn.version(),
        },
    }


def build_evaluation_config(
    args: argparse.Namespace,
    gate: Mapping[str, Any],
    test_inventory: Mapping[str, Any],
    device: Any,
) -> dict[str, Any]:
    spec = gate["spec"]
    payload = {
        "schema_version": EVALUATION_CONFIG_SCHEMA,
        "adapter_schema": ADAPTER_SCHEMA,
        "method": spec.method,
        "config_id": args.config_id,
        "seed": args.seed,
        "run_id": gate["run_id"],
        "source_root": str(args.source_root.resolve()),
        "source_tree_sha256": gate["patch"]["patched_tree_sha256"],
        "patch_manifest_path": str(args.patch_manifest.resolve()),
        "patch_manifest_sha256": sha256_file(args.patch_manifest),
        "official_config_path": str(gate["config_path"].resolve()),
        "official_config_sha256": spec.sha256,
        "fit": {
            "fit_dir": str(gate["fit_dir"]),
            "run_config_path": str(gate["run_config_path"]),
            "run_config_sha256": gate["run_config_sha256"],
            "fit_manifest_path": str(gate["fit_manifest_path"]),
            "fit_manifest_sha256": sha256_file(gate["fit_manifest_path"]),
            "checkpoint_path": str(gate["checkpoint_path"]),
            "checkpoint_sha256": sha256_file(gate["checkpoint_path"]),
            "checkpoint_selection": "pre-specified final epoch",
            "official_test_access_during_fit": False,
        },
        "all_fits_gate": {
            "path": str(args.all_fits_gate.resolve()),
            "sha256": sha256_file(args.all_fits_gate),
            "payload_sha256": gate["all_fits_gate"]["payload_sha256"],
        },
        "test_inventory_gate": {
            "path": str(args.test_inventory_gate.resolve()),
            "sha256": sha256_file(args.test_inventory_gate),
        },
        "initialization_registry_sha256": gate[
            "weight_registry_sha256"
        ],
        "initialization_files": gate["weights"],
        "dataset_roots": {
            "university1652_test": str(args.test_root.resolve()),
            "sues200": str(args.sues_root.resolve()),
        },
        "test_inventories": dict(test_inventory),
        "sues_manifest": {
            "path": str(args.sues_manifest.resolve()),
            "sha256": sha256_file(args.sues_manifest),
        },
        "protocol": {
            "directions": [
                "official test/query_drone -> test/gallery_satellite",
                "official test/query_satellite -> test/gallery_drone",
                *[
                    (
                        f"SUES-200 official 80 test IDs at {altitude} m "
                        "UAV query -> all 200 satellite gallery"
                    )
                    for altitude in SUES200_ALTITUDES
                ],
                *[
                    (
                        "SUES-200 official 80 satellite test-ID query -> "
                        f"all 200 {altitude} m UAV gallery"
                    )
                    for altitude in SUES200_ALTITUDES
                ],
            ],
            "street_to_satellite_reported": False,
            "reason_street_excluded": (
                "The selected public QDFL-framework comparison entry points "
                "implement only Drone-to-Satellite and Satellite-to-Drone."
            ),
            "sues200_zero_shot": True,
            "sues200_target_fitting_or_selection": False,
            "all_queries": True,
            "all_gallery_images": True,
            "path_order": "lexicographic identity then filename",
            "horizontal_flip_augmentation": True,
            "test_size": list(gate["test_size"]),
            "resize_interpolation": "torchvision BICUBIC",
            "normalization": "ImageNet mean/std",
            "descriptor_normalization": (
                "upstream get_descriptors_supervised_with_label semantics"
            ),
            "ranking": (
                "float32 negative squared L2; stable descending path-order tie"
            ),
            "metric": "official trapezoidal AP and full-gallery recall",
        },
        "execution": {
            "batch_size": args.batch_size,
            "workers": args.workers,
            "ranking_chunk_size": args.ranking_chunk_size,
            "amp": False,
            "test_content_hash_computed": True,
        },
        "environment": runtime_environment(device),
        "code": {
            "adapter_path": str(Path(__file__).resolve()),
            "adapter_sha256": sha256_file(Path(__file__)),
            "common_evaluator_path": str(
                Path(__file__).with_name(
                    "official_descriptor_evaluation.py"
                ).resolve()
            ),
            "common_evaluator_sha256": sha256_file(
                Path(__file__).with_name(
                    "official_descriptor_evaluation.py"
                )
            ),
        },
    }
    payload["payload_sha256"] = canonical_object_sha256(payload)
    return payload


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    if args.batch_size <= 0 or args.workers < 0:
        raise IntegrityError("Evaluation batch/workers are invalid.")
    if args.ranking_chunk_size <= 0:
        raise IntegrityError("Ranking chunk size must be positive.")
    output_dir = args.output_dir.resolve()
    if (output_dir / "evaluation_manifest.json").is_file():
        manifest = validate_completed_evaluation(output_dir)
        if (
            manifest.get("config_id") != args.config_id
            or manifest.get("seed") != args.seed
        ):
            raise IntegrityError("Existing QDFL evaluation identity mismatch.")
        return manifest
    if output_dir.exists() and any(output_dir.iterdir()):
        raise IntegrityError(
            "Incomplete QDFL evaluation artifacts must be archived before retry."
        )

    # Everything above the scan is fit/source evidence only.  The official
    # test path is first resolved and read after this completed-fit gate.
    gate = validate_fit_gate(args)
    for name, value in gate["weight_environment"].items():
        os.environ[name] = value
    views, university_inventory = scan_university1652_official_test(
        args.test_root,
        hash_contents=True,
    )
    validate_university1652_test_inventory(university_inventory)
    sues_views, sues_inventory, sues_test_ids = (
        scan_sues200_official_test(
            args.sues_root,
            args.sues_manifest,
            hash_contents=True,
        )
    )
    validate_sues200_test_inventory(sues_inventory)
    inventory = {
        "university1652": university_inventory,
        "sues200": sues_inventory,
    }
    validate_test_inventory_gate(
        args.test_inventory_gate,
        test_root=args.test_root,
        sues_root=args.sues_root,
        sues_manifest=args.sues_manifest,
        all_fits_gate_path=args.all_fits_gate,
        inventory=inventory,
    )

    device = set_determinism(args.seed, args.device_index)
    evaluation_config = build_evaluation_config(
        args,
        gate,
        inventory,
        device,
    )
    output, evaluation_config_sha = begin_evaluation_output(
        output_dir,
        evaluation_config,
    )
    started = time.perf_counter()
    try:
        import torch
        from torch.utils.data import DataLoader

        transform = build_transform(gate["test_size"])
        model = load_model(gate, device)
        fingerprints: dict[str, dict[str, Any]] = {}
        results = {}

        def extract_registered_view(
            dataset: str,
            role: str,
            view: FrozenImageView,
        ) -> np.ndarray:
            loader = DataLoader(
                FrozenPathDataset(view, transform),
                batch_size=args.batch_size,
                shuffle=False,
                num_workers=args.workers,
                pin_memory=True,
                drop_last=False,
                persistent_workers=args.workers > 0,
            )
            matrix = extract_qdfl_descriptors(model, loader, device)
            fingerprints[f"{dataset}/{role}"] = {
                "shape": list(matrix.shape),
                "dtype": str(matrix.dtype),
                "sha256": descriptor_sha256(matrix),
            }
            del loader
            return matrix

        task_specs = (
            (
                "university1652_drone_to_satellite",
                "query_drone",
                "gallery_satellite",
                "official test/query_drone -> test/gallery_satellite",
            ),
            (
                "university1652_satellite_to_drone",
                "query_satellite",
                "gallery_drone",
                "official test/query_satellite -> test/gallery_drone",
            ),
        )
        for task_name, query_role, gallery_role, protocol in task_specs:
            query_view = views[query_role]
            gallery_view = views[gallery_role]
            query_descriptors = extract_registered_view(
                "university1652",
                query_role,
                query_view,
            )
            gallery_descriptors = extract_registered_view(
                "university1652",
                gallery_role,
                gallery_view,
            )
            results[task_name] = evaluate_descriptor_task(
                DescriptorTask(
                    name=task_name,
                    protocol=protocol,
                    query_descriptors=query_descriptors,
                    query_labels=query_view.labels,
                    query_paths=query_view.relative_paths,
                    gallery_descriptors=gallery_descriptors,
                    gallery_labels=gallery_view.labels,
                    gallery_paths=gallery_view.relative_paths,
                    score_type="squared_l2",
                ),
                chunk_size=args.ranking_chunk_size,
            )
            del query_descriptors, gallery_descriptors
            gc.collect()

        test_id_set = set(sues_test_ids)
        satellite_view = sues_views["satellite_all"]
        satellite_descriptors = extract_registered_view(
            "sues200",
            "satellite_all",
            satellite_view,
        )
        satellite_query_mask = np.asarray(
            [
                label in test_id_set
                for label in satellite_view.labels.tolist()
            ],
            dtype=np.bool_,
        )
        if int(satellite_query_mask.sum()) != 80:
            raise DescriptorEvaluationError(
                "SUES-200 satellite test-query count changed."
            )
        for altitude in SUES200_ALTITUDES:
            drone_role = f"drone_{altitude}_all"
            drone_view = sues_views[drone_role]
            drone_descriptors = extract_registered_view(
                "sues200",
                drone_role,
                drone_view,
            )
            drone_query_mask = np.asarray(
                [
                    label in test_id_set
                    for label in drone_view.labels.tolist()
                ],
                dtype=np.bool_,
            )
            if int(drone_query_mask.sum()) != 4000:
                raise DescriptorEvaluationError(
                    f"SUES-200 {altitude} m UAV test-query count changed."
                )
            uav_task = f"sues200_uav_{altitude}m_to_satellite"
            results[uav_task] = evaluate_descriptor_task(
                DescriptorTask(
                    name=uav_task,
                    protocol=(
                        "official 80 test IDs as query; all 200 satellite "
                        "IDs in gallery"
                    ),
                    query_descriptors=drone_descriptors[drone_query_mask],
                    query_labels=drone_view.labels[drone_query_mask],
                    query_paths=drone_view.relative_paths[drone_query_mask],
                    gallery_descriptors=satellite_descriptors,
                    gallery_labels=satellite_view.labels,
                    gallery_paths=satellite_view.relative_paths,
                    score_type="squared_l2",
                ),
                chunk_size=args.ranking_chunk_size,
            )
            satellite_task = (
                f"sues200_satellite_to_uav_{altitude}m"
            )
            results[satellite_task] = evaluate_descriptor_task(
                DescriptorTask(
                    name=satellite_task,
                    protocol=(
                        "official 80 test IDs as query; all 200 "
                        f"{altitude}m UAV IDs in gallery"
                    ),
                    query_descriptors=satellite_descriptors[
                        satellite_query_mask
                    ],
                    query_labels=satellite_view.labels[
                        satellite_query_mask
                    ],
                    query_paths=satellite_view.relative_paths[
                        satellite_query_mask
                    ],
                    gallery_descriptors=drone_descriptors,
                    gallery_labels=drone_view.labels,
                    gallery_paths=drone_view.relative_paths,
                    score_type="squared_l2",
                ),
                chunk_size=args.ranking_chunk_size,
            )
            del drone_descriptors
            gc.collect()
        manifest = complete_evaluation_output(
            output,
            evaluation_config_sha256=evaluation_config_sha,
            method=gate["spec"].method,
            config_id=args.config_id,
            seed=args.seed,
            results=results,
            descriptor_fingerprints=fingerprints,
            elapsed_seconds=time.perf_counter() - started,
        )
        del model, satellite_descriptors
        gc.collect()
        torch.cuda.empty_cache()
        return manifest
    except BaseException as error:
        mark_evaluation_failed(output, evaluation_config_sha, error)
        raise


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config-id",
        choices=tuple(CONFIG_SPECS),
        required=True,
    )
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--patch-manifest", type=Path, required=True)
    parser.add_argument("--fit-dir", type=Path, required=True)
    parser.add_argument("--all-fits-gate", type=Path, required=True)
    parser.add_argument("--test-inventory-gate", type=Path, required=True)
    parser.add_argument("--test-root", type=Path, required=True)
    parser.add_argument("--sues-root", type=Path, required=True)
    parser.add_argument("--sues-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dinov2-weight", type=Path, required=True)
    parser.add_argument("--fsra-weight", type=Path, required=True)
    parser.add_argument("--swinv2-weight", type=Path, required=True)
    parser.add_argument("--convnext-weight", type=Path, required=True)
    parser.add_argument("--device-index", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--ranking-chunk-size", type=int, default=128)


def main() -> int:
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    args = parser.parse_args()
    try:
        manifest = evaluate(args)
    except (
        DescriptorEvaluationError,
        IntegrityError,
        OSError,
        RuntimeError,
        ValueError,
    ) as error:
        raise SystemExit(f"ERROR: {error}") from error
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
