"""Deterministically materialize compatibility-patched external source trees."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any, Sequence

from external_baselines.fetch_and_verify_sources import (
    IntegrityError,
    canonical_tree_hash,
    load_registry,
    verify_source_tree,
)


PATCH_SCHEMA = "lgm-game.external-source-patch.v1"


@dataclass(frozen=True)
class PatchSpec:
    relative_path: str
    old: str
    new: str
    expected_count: int = 1
    rationale: str = ""


QDFL_PATCHES: tuple[PatchSpec, ...] = (
    PatchSpec(
        "utils/__init__.py",
        "from .commons import print_nb_params,get_model_complexity_info,load_config\n"
        "from .metrics import *\n"
        "from .evaluation_utils import *\n"
        "from .loss_func import *",
        "from .commons import print_nb_params,get_model_complexity_info,load_config\n"
        "from .loss_func import *",
        rationale=(
            "Keep the fitting process from importing evaluation-only metrics and dataset code; "
            "the training losses remain unchanged."
        ),
    ),
    PatchSpec(
        "datasets/train/__init__.py",
        "from .U1652_dataloader import U1652DataModule\n"
        "from .DenseUAV_dataloader import DenseUAVDataModule\n"
        "from .SUES_200_dataloader import SUES_200_DataModule",
        "from .U1652_dataloader import U1652DataModule",
        rationale=(
            "Limit the fitting process to the registered University-1652 data module; "
            "this prevents unrelated hardcoded dataset roots from being imported."
        ),
    ),
    PatchSpec(
        "datasets/train/U1652_dataset.py",
        "BASE_PATH = '/media/whu/Largedisk/datasets/U1652/University-Release/train/'",
        "BASE_PATH = os.environ['LGM_QDFL_U1652_TRAIN_ROOT']",
        rationale="Parameterize the official University-1652 fitting path.",
    ),
    PatchSpec(
        "datasets/train/U1652_dataset_DAC.py",
        "BASE_PATH = '/media/whu/Largedisk/datasets/U1652/University-Release/train/'",
        "BASE_PATH = os.environ['LGM_QDFL_U1652_TRAIN_ROOT']",
        rationale="Parameterize the alternate official University-1652 fitting path.",
    ),
    PatchSpec(
        "datasets/test/U1652_test.py",
        "BASE_PATH = '/media/whu/Largedisk/datasets/U1652/University-Release/test/'",
        "BASE_PATH = os.environ['LGM_QDFL_U1652_TEST_ROOT']",
        rationale="Parameterize the official University-1652 evaluation path.",
    ),
    PatchSpec(
        "datasets/train/SUES_200_dataset.py",
        "BASE_PATH = '/media/whu/Largedisk/datasets/SUES-200-512x512/Training'",
        "BASE_PATH = os.environ['LGM_QDFL_SUES_TRAIN_ROOT']",
        rationale="Parameterize the optional SUES-200 fitting path.",
    ),
    PatchSpec(
        "datasets/test/SUES_200_test.py",
        "BASE_PATH = '/media/whu/Largedisk/datasets/SUES-200-512x512/Testing'",
        "BASE_PATH = os.environ['LGM_QDFL_SUES_TEST_ROOT']",
        rationale="Parameterize the optional SUES-200 evaluation path.",
    ),
    PatchSpec(
        "model/backbones/dinov2.py",
        "import time\n",
        "import time\nimport os\n",
        rationale="Read the pinned DINOv2 weight path from the adapter environment.",
    ),
    PatchSpec(
        "model/backbones/dinov2.py",
        "'dinov2_vitb14': 'your_own_path/pretrained_weights/dinov2_vitb14_pretrain.pth'",
        "'dinov2_vitb14': os.environ['LGM_QDFL_DINOV2_VITB14_WEIGHTS']",
        rationale="Replace the non-portable DINOv2 placeholder with an explicit pinned path.",
    ),
    PatchSpec(
        "model/get_backbone_components.py",
        "import torch\n",
        "import torch\nimport os\n",
        rationale="Read the pinned FSRA initialization path from the adapter environment.",
    ),
    PatchSpec(
        "model/get_backbone_components.py",
        "m.load_param('/media/whu/Filesystem2/jx_vit_base_p16_224-80ecf9dd.pth')",
        "m.load_param(os.environ['LGM_QDFL_FSRA_WEIGHTS'])",
        rationale="Replace the non-portable FSRA initialization path.",
    ),
    PatchSpec(
        "model/backbones/swinv2.py",
        "import time\n",
        "import time\nimport os\n",
        rationale="Read the hash-pinned Swin V2-B initialization from an explicit path.",
    ),
    PatchSpec(
        "model/backbones/swinv2.py",
        "            model = swin_v2_b(weights='IMAGENET1K_V1')",
        "            model = swin_v2_b(weights=None)\n"
        "            state_dict = torch.load(\n"
        "                os.environ['LGM_QDFL_SWINV2_B_WEIGHTS'],\n"
        "                map_location='cpu',\n"
        "                weights_only=True,\n"
        "            )\n"
        "            model.load_state_dict(state_dict)",
        rationale=(
            "Replace implicit torchvision cache/network resolution with the same "
            "explicitly hash-pinned Swin V2-B state dictionary."
        ),
    ),
    PatchSpec(
        "model/backbones/convnext_backbone/ConvNext_backbone.py",
        "import torch\n",
        "import os\nimport torch\n",
        rationale="Read the hash-pinned ConvNeXt-B initialization from an explicit path.",
    ),
    PatchSpec(
        "model/backbones/convnext_backbone/ConvNext_backbone.py",
        "        url = model_urls['convnext_base_22k'] if in_22k else model_urls['convnext_base_1k']\n"
        "        checkpoint = torch.hub.load_state_dict_from_url(url=url, map_location=\"cpu\")\n"
        "        print(url)\n"
        "        model.load_state_dict(checkpoint[\"model\"], strict=False)",
        "        url = model_urls['convnext_base_22k'] if in_22k else model_urls['convnext_base_1k']\n"
        "        checkpoint = torch.load(\n"
        "            os.environ['LGM_QDFL_CONVNEXT_B_22K_WEIGHTS'],\n"
        "            map_location='cpu',\n"
        "            weights_only=False,\n"
        "        )\n"
        "        print(url)\n"
        "        model.load_state_dict(checkpoint[\"model\"], strict=False)",
        rationale=(
            "Replace implicit URL/cache resolution with the same explicitly "
            "hash-pinned ConvNeXt-B 22K/1K checkpoint."
        ),
    ),
)

MCCG_PATCHES: tuple[PatchSpec, ...] = (
    PatchSpec(
        "models/ConvNext/backbones/model_convnext.py",
        "import torch\r\n",
        "import os\r\nimport torch\r\n",
        rationale="Read the hash-pinned ConvNeXt-T initialization from an explicit path.",
    ),
    PatchSpec(
        "models/ConvNext/backbones/model_convnext.py",
        "        url = model_urls['convnext_tiny_22k'] if in_22k else model_urls['convnext_tiny_1k']\r\n"
        "        checkpoint = torch.hub.load_state_dict_from_url(url=url, map_location=\"cpu\", check_hash=True)\r\n"
        "        print(url)\r\n"
        "        model.load_state_dict(checkpoint[\"model\"], strict=False)",
        "        url = model_urls['convnext_tiny_22k'] if in_22k else model_urls['convnext_tiny_1k']\r\n"
        "        checkpoint = torch.load(\r\n"
        "            os.environ['LGM_MCCG_CONVNEXT_T_22K_WEIGHTS'],\r\n"
        "            map_location='cpu',\r\n"
        "            weights_only=False,\r\n"
        "        )\r\n"
        "        print(url)\r\n"
        "        model.load_state_dict(checkpoint[\"model\"], strict=False)",
        rationale=(
            "Replace implicit URL/cache resolution with the same explicitly "
            "hash-pinned ConvNeXt-T 22K/1K checkpoint."
        ),
    ),
    PatchSpec(
        "train.py",
        "import argparse\n",
        "import argparse\nimport json\nimport random\n",
        rationale="Expose a caller-pinned random seed for the published training loop.",
    ),
    PatchSpec(
        "train.py",
        "parser.add_argument('--gpu_ids',default='0', type=str,help='gpu_ids: e.g. 0  0,1,2  0,2')",
        "parser.add_argument('--seed', default=1, type=int, help='registered random seed')\n"
        "parser.add_argument('--gpu_ids',default='0', type=str,help='gpu_ids: e.g. 0  0,1,2  0,2')",
        rationale="Add the registered seed without changing published defaults.",
    ),
    PatchSpec(
        "train.py",
        "dir_name = os.path.join('./model',opt.name)",
        "dir_name = os.path.join(os.environ['LGM_MCCG_OUTPUT_ROOT'], opt.name)",
        rationale="Keep generated artifacts outside the hash-pinned source tree.",
    ),
    PatchSpec(
        "train.py",
        "str_ids = opt.gpu_ids.split(',')",
        "random.seed(opt.seed)\n"
        "np.random.seed(opt.seed)\n"
        "torch.manual_seed(opt.seed)\n"
        "torch.cuda.manual_seed_all(opt.seed)\n"
        "str_ids = opt.gpu_ids.split(',')",
        rationale="Seed Python, NumPy, CPU torch, and CUDA before data/model construction.",
    ),
    PatchSpec(
        "train.py",
        "    cudnn.benchmark = True",
        "    cudnn.benchmark = False\n"
        "    cudnn.deterministic = True\n"
        "    torch.use_deterministic_algorithms(True, warn_only=True)\n"
        "    torch.cuda.reset_peak_memory_stats(gpu_ids[0])",
        rationale=(
            "Use deterministic kernels where supported and reset the device-memory "
            "counter before model construction."
        ),
    ),
    PatchSpec(
        "train.py",
        "os.path.join('model',opt.name,opt.fname)",
        "os.path.join(dir_name,opt.fname)",
        expected_count=4,
        rationale="Write the training log only under the registered output root.",
    ),
    PatchSpec(
        "train.py",
        "os.path.join('model', opt.name, opt.fname)",
        "os.path.join(dir_name, opt.fname)",
        expected_count=2,
        rationale="Write the training log only under the registered output root.",
    ),
    PatchSpec(
        "train.py",
        "            if epoch >= 90 and epoch_loss < min_loss:\n"
        "                save_network(model, opt.name, epoch)\n"
        "                min_loss = epoch_loss",
        "            if epoch == num_epochs - 1:\n"
        "                save_network(model, opt.name, 'last')",
        rationale=(
            "Replace training-loss checkpoint selection with the pre-specified "
            "final epoch required by the extension protocol."
        ),
    ),
    PatchSpec(
        "train.py",
        "model = train_model(model, opt, model_test, optimizer_ft, exp_lr_scheduler,\n"
        "                       num_epochs=num_epochs)",
        "model = train_model(model, opt, model_test, optimizer_ft, exp_lr_scheduler,\n"
        "                       num_epochs=num_epochs)\n"
        "runtime_metrics = {\n"
        "    'peak_gpu_memory_bytes': int(torch.cuda.max_memory_allocated(gpu_ids[0])),\n"
        "    'completed_epochs': int(num_epochs),\n"
        "    'final_epoch_index': int(num_epochs - 1),\n"
        "}\n"
        "with open(os.path.join(dir_name, 'runtime_metrics.json'), 'x', encoding='utf-8') as stream:\n"
        "    json.dump(runtime_metrics, stream, indent=2, sort_keys=True)\n"
        "    stream.write('\\n')",
        rationale="Record completion and peak allocated GPU memory without evaluating test data.",
    ),
    PatchSpec(
        "utils.py",
        "    if not os.path.isdir('./model/'+dirname):\n"
        "        os.mkdir('./model/'+dirname)\n"
        "    if isinstance(epoch_label, int):\n"
        "        save_filename = 'net_%03d.pth'% epoch_label\n"
        "    else:\n"
        "        save_filename = 'net_%s.pth'% epoch_label\n"
        "    save_path = os.path.join('./model',dirname,save_filename)\n"
        "    torch.save(network.cpu().state_dict(), save_path)\n"
        "    if torch.cuda.is_available:\n"
        "        network.cuda()",
        "    directory = os.path.join(os.environ['LGM_MCCG_OUTPUT_ROOT'], dirname)\n"
        "    os.makedirs(directory, exist_ok=True)\n"
        "    if isinstance(epoch_label, int):\n"
        "        save_filename = 'net_%03d.pth'% epoch_label\n"
        "    else:\n"
        "        save_filename = 'net_%s.pth'% epoch_label\n"
        "    save_path = os.path.join(directory, save_filename)\n"
        "    temporary = save_path + '.tmp'\n"
        "    if os.path.exists(save_path) or os.path.exists(temporary):\n"
        "        raise RuntimeError('Refusing to overwrite an MCCG checkpoint')\n"
        "    torch.save(network.cpu().state_dict(), temporary)\n"
        "    os.replace(temporary, save_path)\n"
        "    if torch.cuda.is_available():\n"
        "        network.cuda()",
        rationale="Write one non-overwriting final checkpoint under the registered output root.",
    ),
    PatchSpec(
        "utils.py",
        "    dirname = os.path.join('./model',name)",
        "    dirname = os.path.join(os.environ['LGM_MCCG_OUTPUT_ROOT'], name)",
        rationale="Resolve any explicit resume path under the registered output root.",
    ),
    PatchSpec(
        "utils.py",
        "    save_path = os.path.join('./model',name,save_filename)",
        "    save_path = os.path.join(os.environ['LGM_MCCG_OUTPUT_ROOT'], name, save_filename)",
        rationale="Resolve any explicit resume checkpoint under the registered output root.",
    ),
    PatchSpec(
        "utils.py",
        "    network.load_state_dict(torch.load(save_path))",
        "    network.load_state_dict(torch.load(save_path, map_location='cpu', weights_only=True))",
        rationale="Load an explicit model-only state dictionary without arbitrary object execution.",
    ),
)


def patch_plan_hash(source_id: str, patches: Sequence[PatchSpec]) -> str:
    payload = {
        "source_id": source_id,
        "patches": [asdict(patch) for patch in patches],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _source_entry(registry: dict[str, Any], source_id: str) -> dict[str, Any]:
    matches = [source for source in registry["sources"] if source["id"] == source_id]
    if len(matches) != 1:
        raise IntegrityError(f"Expected one registry entry for {source_id!r}.")
    return matches[0]


def _apply_patches(root: Path, patches: Sequence[PatchSpec]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for patch in patches:
        path = root / Path(patch.relative_path)
        if not path.is_file():
            raise IntegrityError(f"Patch target does not exist: {patch.relative_path}")
        raw_before = path.read_bytes()
        try:
            text = raw_before.decode("utf-8")
        except UnicodeDecodeError as error:
            raise IntegrityError(f"Patch target is not UTF-8: {patch.relative_path}") from error
        actual_count = text.count(patch.old)
        if actual_count != patch.expected_count:
            raise IntegrityError(
                f"{patch.relative_path}: expected {patch.expected_count} exact matches, "
                f"found {actual_count}"
            )
        updated = text.replace(patch.old, patch.new)
        raw_after = updated.encode("utf-8")
        path.write_bytes(raw_after)
        records.append(
            {
                "relative_path": patch.relative_path,
                "rationale": patch.rationale,
                "replacement_count": actual_count,
                "before_sha256": hashlib.sha256(raw_before).hexdigest(),
                "after_sha256": hashlib.sha256(raw_after).hexdigest(),
            }
        )
    return records


def _verify_existing_destination(
    destination: Path,
    manifest_path: Path,
    expected_plan_hash: str,
    expected_upstream_hash: str,
) -> dict[str, Any]:
    if not manifest_path.is_file():
        raise IntegrityError(
            f"Patched destination exists without its manifest; refusing reuse: {destination}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != PATCH_SCHEMA:
        raise IntegrityError(f"Unsupported patch manifest schema: {manifest.get('schema_version')!r}")
    if manifest.get("patch_plan_sha256") != expected_plan_hash:
        raise IntegrityError("Existing patched tree was produced by a different patch plan.")
    if manifest.get("upstream_tree_sha256") != expected_upstream_hash:
        raise IntegrityError("Existing patched tree was produced from a different upstream tree.")
    actual_hash, actual_count = canonical_tree_hash(destination)
    if actual_hash != manifest.get("patched_tree_sha256"):
        raise IntegrityError("Existing patched source-tree hash does not match its manifest.")
    if actual_count != manifest.get("patched_file_count"):
        raise IntegrityError("Existing patched source-tree file count does not match its manifest.")
    return manifest


def prepare_patched_source(
    *,
    source_id: str,
    upstream_root: Path,
    destination: Path,
    registry_path: Path,
    patches: Sequence[PatchSpec],
) -> dict[str, Any]:
    registry, registry_sha = load_registry(registry_path)
    source = _source_entry(registry, source_id)
    upstream_verification = verify_source_tree(upstream_root, source)
    plan_hash = patch_plan_hash(source_id, patches)
    manifest_path = destination.parent / f"{destination.name}.patch_manifest.json"

    if destination.exists():
        return _verify_existing_destination(
            destination,
            manifest_path,
            plan_hash,
            source["source_tree_sha256"],
        )
    if manifest_path.exists():
        raise IntegrityError(f"Patch manifest exists without its destination: {manifest_path}")
    destination.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix=f".{source_id}-patch-",
        dir=destination.parent,
    ) as temporary_name:
        temporary = Path(temporary_name) / "source"
        shutil.copytree(upstream_root, temporary)
        patch_records = _apply_patches(temporary, patches)
        patched_hash, patched_count = canonical_tree_hash(temporary)
        manifest = {
            "schema_version": PATCH_SCHEMA,
            "source_id": source_id,
            "upstream_root": str(upstream_root.resolve()),
            "upstream_tree_sha256": upstream_verification["source_tree_sha256"],
            "upstream_file_count": upstream_verification["source_file_count"],
            "registry_path": str(registry_path.resolve()),
            "registry_sha256": registry_sha,
            "patch_plan_sha256": plan_hash,
            "patches": patch_records,
            "patched_tree_sha256": patched_hash,
            "patched_file_count": patched_count,
            "destination": str(destination.resolve()),
        }
        shutil.move(str(temporary), str(destination))

    serialized = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    with manifest_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(serialized)
    return manifest


def prepare_qdfl_source(
    upstream_root: Path,
    destination: Path,
    registry_path: Path,
) -> dict[str, Any]:
    return prepare_patched_source(
        source_id="qdfl",
        upstream_root=upstream_root,
        destination=destination,
        registry_path=registry_path,
        patches=QDFL_PATCHES,
    )


def prepare_mccg_source(
    upstream_root: Path,
    destination: Path,
    registry_path: Path,
) -> dict[str, Any]:
    return prepare_patched_source(
        source_id="mccg",
        upstream_root=upstream_root,
        destination=destination,
        registry_path=registry_path,
        patches=MCCG_PATCHES,
    )
