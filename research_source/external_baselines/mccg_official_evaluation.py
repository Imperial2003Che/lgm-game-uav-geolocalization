"""Official full-query University-1652 evaluation for the MCCG fit.

The public MCCG test program defines two directions, two-pass horizontal-flip
augmentation, view-aware forward branches, and inner-product ranking.  This
adapter preserves those semantics while adding immutable fit/test evidence and
recomputable per-query outputs.
"""

from __future__ import annotations

import argparse
import gc
import importlib
import importlib.metadata
import json
import math
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
from external_baselines.mccg_adapter import (
    PUBLISHED_RECIPE,
    WEIGHT_ID,
    validate_completed_fit,
    validate_options,
    validate_published_recipe,
)
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
    canonical_object_sha256,
    load_weight_registry,
    verify_patched_source,
    verify_weight,
)


ADAPTER_SCHEMA = "lgm-game.mccg-official-evaluation.v1"
CONFIG_ID = "mccg_convnext_tiny"
METHOD = "MCCG"


class FrozenPathDataset:
    def __init__(self, view: FrozenImageView, transform: Any):
        self.view = view
        self.transform = transform

    def __len__(self) -> int:
        return len(self.view.paths)

    def __getitem__(self, index: int) -> tuple[Any, int]:
        from PIL import Image

        with Image.open(self.view.paths[index]) as source:
            image = source.convert("RGB")
        return self.transform(image), index


def validate_fit_gate(args: argparse.Namespace) -> dict[str, Any]:
    if args.seed < 0:
        raise IntegrityError("Evaluation seed must be non-negative.")
    patch = verify_patched_source(
        args.source_root,
        args.patch_manifest,
        expected_source_id="mccg",
    )
    validate_published_recipe(args.source_root)

    fit_dir = args.fit_dir.resolve(strict=True)
    run_config_path = fit_dir / "run_config.json"
    fit_manifest_path = fit_dir / "fit_manifest.json"
    checkpoint_path = fit_dir / "net_last.pth"
    run_config_sha = sha256_file(run_config_path)
    fit_manifest = validate_completed_fit(
        fit_manifest_path,
        fit_dir,
        run_config_sha,
        args.seed,
    )
    run_config = json.loads(run_config_path.read_text(encoding="utf-8"))
    expected_fields = {
        "method": METHOD,
        "config_id": CONFIG_ID,
        "seed": args.seed,
        "source_tree_sha256": patch["patched_tree_sha256"],
        "published_recipe": PUBLISHED_RECIPE,
        "checkpoint_selection": "pre-specified final epoch",
        "official_test_access_during_fit": False,
    }
    for field, expected in expected_fields.items():
        if run_config.get(field) != expected:
            raise IntegrityError(
                f"MCCG fit run configuration {field} changed."
            )
    if (
        Path(str(run_config.get("source_root", ""))).resolve()
        != args.source_root.resolve()
        or run_config.get("patch_manifest_sha256")
        != sha256_file(args.patch_manifest)
    ):
        raise IntegrityError("MCCG fit source evidence changed.")

    dataset = run_config.get("dataset", {})
    environment = run_config.get("environment", {})
    training_device_index = int(
        environment.get("cuda", {}).get("device_index", -1)
    )
    validate_options(
        fit_dir / "opts.yaml",
        fit_dir.name,
        args.seed,
        Path(str(dataset.get("train_root", ""))),
        training_device_index,
    )

    run_id = f"{CONFIG_ID}/seed_{args.seed}"
    all_fits_gate, gate_row = validate_all_fits_gate(
        args.all_fits_gate,
        run_id=run_id,
        fit_manifest_path=fit_manifest_path,
        checkpoint_path=checkpoint_path,
    )
    registry_path = Path(__file__).with_name(
        "transactions_weight_registry.json"
    )
    registry, registry_sha = load_weight_registry(registry_path)
    row = registry[WEIGHT_ID]
    weight = verify_weight(
        args.convnext_weight,
        str(row["sha256"]),
        int(row["bytes"]),
        "MCCG ConvNeXt-T ImageNet-22K/1K initialization",
    )
    return {
        "patch": patch,
        "fit_dir": fit_dir,
        "run_config_path": run_config_path,
        "run_config_sha256": run_config_sha,
        "run_config": run_config,
        "fit_manifest_path": fit_manifest_path,
        "fit_manifest": fit_manifest,
        "checkpoint_path": checkpoint_path,
        "run_id": run_id,
        "all_fits_gate": all_fits_gate,
        "all_fits_gate_row": gate_row,
        "weight": {
            **weight,
            "source_url": row["source_url"],
            "load_contract": row["load_contract"],
        },
        "weight_registry_sha256": registry_sha,
    }


def mccg_postprocess(output: Any) -> Any:
    """Reproduce MCCG's post-flip descriptor normalization."""

    import torch

    if not isinstance(output, torch.Tensor) or output.ndim not in {2, 3}:
        raise DescriptorEvaluationError(
            "MCCG model output is not a 2-D/3-D descriptor tensor."
        )
    value = output.to(dtype=torch.float32)
    norm = torch.linalg.vector_norm(value, ord=2, dim=1, keepdim=True)
    if value.ndim == 3:
        norm = norm * math.sqrt(value.shape[-1])
    if not torch.isfinite(norm).all() or torch.any(norm <= 0):
        raise DescriptorEvaluationError("MCCG descriptor norm is invalid.")
    value = value / norm.expand_as(value)
    return value.reshape(value.shape[0], -1).contiguous()


def _view_output(model: Any, images: Any, role: str) -> Any:
    if "satellite" in role:
        output, _ = model(images, None)
        return output
    if "drone" in role:
        _, output = model(None, images)
        return output
    raise DescriptorEvaluationError(f"Unsupported MCCG view role: {role}")


def extract_mccg_descriptors(
    model: Any,
    dataloader: Any,
    device: Any,
    role: str,
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
                    "MCCG dataloader order differs from the frozen path order."
                )
            expected_index += len(observed)
            images = images.to(device=device, non_blocking=True)
            original = _view_output(model, images, role)
            mirrored = _view_output(
                model,
                torch.flip(images, dims=(3,)),
                role,
            )
            descriptors.append(
                mccg_postprocess(original + mirrored).cpu()
            )
            del images, original, mirrored
    if expected_index != len(dataloader.dataset):
        raise DescriptorEvaluationError(
            "MCCG descriptor extraction omitted official images."
        )
    matrix = torch.cat(descriptors, dim=0)
    if matrix.shape[0] != expected_index or not torch.isfinite(matrix).all():
        raise DescriptorEvaluationError(
            "MCCG descriptor matrix is incomplete or non-finite."
        )
    return np.ascontiguousarray(matrix.numpy(), dtype=np.float32)


def build_transform() -> Any:
    from torchvision import transforms

    size = tuple(PUBLISHED_RECIPE["image_size"])
    return transforms.Compose(
        [
            transforms.Resize(
                size,
                interpolation=transforms.InterpolationMode.BICUBIC,
            ),
            transforms.ToTensor(),
            transforms.Normalize(
                [0.485, 0.456, 0.406],
                [0.229, 0.224, 0.225],
            ),
        ]
    )


def load_model(
    source_root: Path,
    checkpoint_path: Path,
    device: Any,
) -> Any:
    import torch

    source_text = str(source_root.resolve())
    if source_text in sys.path:
        raise IntegrityError("Pinned MCCG source is already present on sys.path.")
    sys.path.insert(0, source_text)
    try:
        module = importlib.import_module("models.model")
        model_class = getattr(module, "two_view_net")
        model = model_class(
            701,
            block=PUBLISHED_RECIPE["classifier_blocks"],
            return_f=False,
            resnet=False,
        )
    finally:
        if sys.path[0] == source_text:
            sys.path.pop(0)
    state = torch.load(
        checkpoint_path,
        map_location="cpu",
        weights_only=True,
        mmap=True,
    )
    try:
        if not isinstance(state, Mapping) or not state:
            raise IntegrityError("MCCG checkpoint state is absent.")
        model.load_state_dict(state, strict=True)
    finally:
        del state
    return model.eval().to(device)


def set_determinism(seed: int, device_index: int) -> Any:
    import torch

    if not torch.cuda.is_available():
        raise IntegrityError("MCCG official evaluation requires CUDA.")
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
    inventory: Mapping[str, Any],
    device: Any,
) -> dict[str, Any]:
    payload = {
        "schema_version": EVALUATION_CONFIG_SCHEMA,
        "adapter_schema": ADAPTER_SCHEMA,
        "method": METHOD,
        "config_id": CONFIG_ID,
        "seed": args.seed,
        "run_id": gate["run_id"],
        "source_root": str(args.source_root.resolve()),
        "source_tree_sha256": gate["patch"]["patched_tree_sha256"],
        "patch_manifest_path": str(args.patch_manifest.resolve()),
        "patch_manifest_sha256": sha256_file(args.patch_manifest),
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
        "initialization_file": gate["weight"],
        "dataset_roots": {
            "university1652_test": str(args.test_root.resolve()),
            "sues200": str(args.sues_root.resolve()),
        },
        "test_inventories": dict(inventory),
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
                "The pinned public MCCG test entry point evaluates only "
                "Drone-to-Satellite and Satellite-to-Drone."
            ),
            "sues200_zero_shot": True,
            "sues200_target_fitting_or_selection": False,
            "all_queries": True,
            "all_gallery_images": True,
            "path_order": "lexicographic identity then filename",
            "horizontal_flip_augmentation": True,
            "multi_scale": [1.0],
            "view_branches": {"satellite": 1, "drone": 3},
            "test_size": PUBLISHED_RECIPE["image_size"],
            "query_padding": 0,
            "resize_interpolation": "torchvision BICUBIC",
            "normalization": "ImageNet mean/std",
            "descriptor_normalization": (
                "upstream MCCG extract_feature semantics, including sqrt(parts)"
            ),
            "ranking": "float32 inner product; stable descending path-order tie",
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
            manifest.get("config_id") != CONFIG_ID
            or manifest.get("seed") != args.seed
        ):
            raise IntegrityError("Existing MCCG evaluation identity mismatch.")
        return manifest
    if output_dir.exists() and any(output_dir.iterdir()):
        raise IntegrityError(
            "Incomplete MCCG evaluation artifacts must be archived before retry."
        )

    gate = validate_fit_gate(args)
    os.environ["LGM_MCCG_CONVNEXT_T_22K_WEIGHTS"] = str(
        args.convnext_weight.resolve()
    )
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

        transform = build_transform()
        model = load_model(
            args.source_root,
            gate["checkpoint_path"],
            device,
        )
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
            matrix = extract_mccg_descriptors(
                model,
                loader,
                device,
                role,
            )
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
                    score_type="inner_product",
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
                    score_type="inner_product",
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
                    score_type="inner_product",
                ),
                chunk_size=args.ranking_chunk_size,
            )
            del drone_descriptors
            gc.collect()
        manifest = complete_evaluation_output(
            output,
            evaluation_config_sha256=evaluation_config_sha,
            method=METHOD,
            config_id=CONFIG_ID,
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
