#!/usr/bin/env python3
"""Run one SUES-200 leave-one-altitude-out fit without editing the frozen core."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Callable, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lgm_game_pytorch import formal_retrieval as core


ADAPTER_CONFIG_SCHEMA = "lgm-game.sues-heldout-adapter-config.v1"
MEMBERSHIP_SCHEMA = "lgm-game.sues-heldout-membership.v1"
FIT_MANIFEST_SCHEMA = "lgm-game.sues-heldout-fit.v1"
STATUS_SCHEMA = "lgm-game.sues-heldout-fit-status.v1"
EXPECTED_CORE_SHA256 = (
    "081f327f8f83d79ab078adc61e76070c140f13e0ac9a0d8f423bfad15df59862"
)
EXPECTED_SUES_EVIDENCE_SHA256 = (
    "6c3a82fdcf59e401f5da4ed0f3d9dca99fdcbab0a46aa66fb47a055c832cdabd"
)
EXPECTED_SUES_EVIDENCE_META_SHA256 = (
    "3dc42892bbff9339d058fc0d6abaf2fd9e92cc94f9f9b7fd58ed0ae725b57dca"
)
EXPECTED_SUES_MANIFEST_SHA256 = (
    "c1386d5c746aca48bbb2793ed1ee19d6cd7330a7f5f1b27a5ec43727317ec226"
)
ALLOWED_VARIANTS = ("visual", "full")


class HeldoutIntegrityError(RuntimeError):
    """Raised when a leave-one-altitude-out artifact fails closed."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_sha256(payload: Any) -> str:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def canonical_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: Any) -> None:
    serialized = canonical_bytes(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    if temporary.exists():
        raise HeldoutIntegrityError(
            f"Refusing to overwrite stale temporary file: {temporary}"
        )
    temporary.write_bytes(serialized)
    temporary.replace(path)


def immutable_json(path: Path, payload: Any) -> str:
    serialized = canonical_bytes(payload)
    digest = hashlib.sha256(serialized).hexdigest()
    if path.exists():
        if path.read_bytes() != serialized:
            raise HeldoutIntegrityError(f"Existing immutable JSON differs: {path}")
        return digest
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(serialized)
    return digest


def adapter_sha256() -> str:
    return sha256_file(Path(__file__).resolve())


def validate_frozen_core() -> str:
    path = Path(core.__file__).resolve()
    actual = sha256_file(path)
    if actual != EXPECTED_CORE_SHA256:
        raise HeldoutIntegrityError(
            f"Frozen formal core changed: expected {EXPECTED_CORE_SHA256}, got {actual}"
        )
    return actual


def filter_heldout_records(
    records: Sequence[core.EvidenceRecord],
    heldout_altitude: str,
) -> list[core.EvidenceRecord]:
    if heldout_altitude not in core.SUES_ALTITUDES:
        raise HeldoutIntegrityError(
            f"Unsupported SUES-200 held-out altitude: {heldout_altitude}"
        )
    return [
        record
        for record in records
        if record.view != "drone" or record.altitude != heldout_altitude
    ]


def membership_payload(
    records: Sequence[core.EvidenceRecord],
    filtered_records: Sequence[core.EvidenceRecord],
    heldout_altitude: str,
    sues_train_ids: Sequence[str],
) -> dict[str, Any]:
    train_ids = set(sues_train_ids)
    excluded = [
        record
        for record in records
        if record.view == "drone" and record.altitude == heldout_altitude
    ]
    excluded_train = [record for record in excluded if record.label in train_ids]
    included_train_drone = [
        record
        for record in filtered_records
        if record.view == "drone" and record.label in train_ids
    ]
    included_train_satellite = [
        record
        for record in filtered_records
        if record.view == "satellite" and record.label in train_ids
    ]
    seen_altitudes = [
        altitude for altitude in core.SUES_ALTITUDES if altitude != heldout_altitude
    ]
    payload = {
        "schema_version": MEMBERSHIP_SCHEMA,
        "dataset": "sues200",
        "heldout_altitude_m": heldout_altitude,
        "seen_altitudes_m": seen_altitudes,
        "official_train_identity_count": len(train_ids),
        "input_protocol_record_count": len(records),
        "filtered_protocol_record_count": len(filtered_records),
        "excluded_heldout_drone_record_count_all_identities": len(excluded),
        "excluded_heldout_drone_record_count_official_train_ids": len(
            excluded_train
        ),
        "included_seen_altitude_drone_record_count_official_train_ids": len(
            included_train_drone
        ),
        "included_satellite_record_count_official_train_ids": len(
            included_train_satellite
        ),
        "excluded_heldout_train_paths_sha256": canonical_sha256(
            sorted(record.relative_path for record in excluded_train)
        ),
        "included_train_drone_paths_sha256": canonical_sha256(
            sorted(record.relative_path for record in included_train_drone)
        ),
        "included_train_satellite_paths_sha256": canonical_sha256(
            sorted(record.relative_path for record in included_train_satellite)
        ),
        "official_test_metric_access": False,
    }
    payload["payload_sha256"] = canonical_sha256(payload)
    return payload


def make_protocol_builder(
    original: Callable[..., core.TrainingProtocol],
    heldout_altitude: str,
    membership_path: Path,
) -> Callable[..., core.TrainingProtocol]:
    def build(
        records: Sequence[core.EvidenceRecord],
        dataset: str,
        val_fraction: float,
        seed: int,
        sues_train_ids: Sequence[str],
    ) -> core.TrainingProtocol:
        if dataset != "sues200":
            raise HeldoutIntegrityError(
                "The held-out-altitude adapter can only fit SUES-200."
            )
        filtered = filter_heldout_records(records, heldout_altitude)
        membership = membership_payload(
            records,
            filtered,
            heldout_altitude,
            sues_train_ids,
        )
        immutable_json(membership_path, membership)
        protocol = original(
            filtered,
            dataset,
            val_fraction,
            seed,
            sues_train_ids,
        )
        if any(
            record.altitude == heldout_altitude
            for record in protocol.train_queries
            if record.view == "drone"
        ):
            raise HeldoutIntegrityError("Held-out altitude leaked into fit queries.")
        protocol.protocol_summary = {
            **protocol.protocol_summary,
            "altitude_generalization_design": "leave_one_altitude_out",
            "heldout_altitude_m": heldout_altitude,
            "seen_altitudes_m": [
                altitude
                for altitude in core.SUES_ALTITUDES
                if altitude != heldout_altitude
            ],
            "heldout_altitude_fit_query_image_count": 0,
            "excluded_heldout_train_query_image_count": membership[
                "excluded_heldout_drone_record_count_official_train_ids"
            ],
            "heldout_membership_path": str(membership_path.resolve()),
            "heldout_membership_sha256": sha256_file(membership_path),
            "official_test_metric_access": False,
        }
        return protocol

    return build


def normalized_training_contract(args: argparse.Namespace) -> dict[str, Any]:
    excluded_runtime_fields = {"resume"}
    return {
        key: value
        for key, value in core.args_to_json(args).items()
        if key not in excluded_runtime_fields
    }


def validate_core_args(args: argparse.Namespace, heldout_altitude: str) -> None:
    core.validate_cli(args)
    if args.command != "train":
        raise HeldoutIntegrityError("Held-out adapter accepts only the train command.")
    if args.dataset != "sues200":
        raise HeldoutIntegrityError("Held-out adapter requires --dataset sues200.")
    if args.variant not in ALLOWED_VARIANTS:
        raise HeldoutIntegrityError(
            f"T2 permits only variants {ALLOWED_VARIANTS}, got {args.variant!r}."
        )
    expected = {
        "epochs": 80,
        "warmup_epochs": 5,
        "learning_rate": 0.0003,
        "backbone_lr_multiplier": 0.1,
        "weight_decay": 0.0001,
        "gradient_clip_norm": 5.0,
        "identities_per_batch": 16,
        "instances_per_identity": 4,
        "samples_per_class_per_epoch": 0,
        "steps_per_epoch": 0,
        "val_fraction": 0.0,
        "patience": 0,
        "data_hash_mode": "content",
        "pretrained": True,
        "backbone": "resnet18",
        "image_size": 224,
        "resize_size": 256,
        "embed_dim": 512,
        "dropout": 0.2,
        "amp": True,
        "workers": 8,
        "eval_batch_size": 128,
        "eval_chunk_size": 128,
    }
    for name, value in expected.items():
        if getattr(args, name) != value:
            raise HeldoutIntegrityError(
                f"T2 frozen setting {name} mismatch: expected {value!r}, "
                f"got {getattr(args, name)!r}"
            )
    if args.resume not in {"none", "last"}:
        raise HeldoutIntegrityError("T2 resume must be either none or last.")
    if heldout_altitude not in core.SUES_ALTITUDES:
        raise HeldoutIntegrityError("T2 held-out altitude is invalid.")


def evidence_artifacts(args: argparse.Namespace) -> list[dict[str, Any]]:
    rows = []
    for value in args.evidence:
        path = Path(value).expanduser().resolve(strict=True)
        meta_path = core.find_meta_path(path).resolve(strict=True)
        rows.append(
            {
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "meta_path": str(meta_path),
                "meta_bytes": meta_path.stat().st_size,
                "meta_sha256": sha256_file(meta_path),
            }
        )
    if (
        len(rows) != 1
        or rows[0]["sha256"] != EXPECTED_SUES_EVIDENCE_SHA256
        or rows[0]["meta_sha256"] != EXPECTED_SUES_EVIDENCE_META_SHA256
    ):
        raise HeldoutIntegrityError(
            "T2 must use the single frozen SUES-200 evidence cache and metadata."
        )
    return rows


def build_adapter_config(
    args: argparse.Namespace,
    heldout_altitude: str,
) -> dict[str, Any]:
    sues_manifest = Path(args.sues_manifest).expanduser().resolve(strict=True)
    if sha256_file(sues_manifest) != EXPECTED_SUES_MANIFEST_SHA256:
        raise HeldoutIntegrityError("T2 SUES-200 official train-ID manifest changed.")
    return {
        "schema_version": ADAPTER_CONFIG_SCHEMA,
        "dataset": "sues200",
        "design": "leave_one_altitude_out",
        "heldout_altitude_m": heldout_altitude,
        "seen_altitudes_m": [
            altitude
            for altitude in core.SUES_ALTITUDES
            if altitude != heldout_altitude
        ],
        "variant": args.variant,
        "seed": args.seed,
        "checkpoint_selection": "pre-specified final epoch",
        "official_test_metric_access_during_fit": False,
        "resume_policy": (
            "none for a fresh fit; last only after explicit authorization and "
            "the frozen core's full model/optimizer/scheduler/scaler/RNG audit"
        ),
        "training_contract": normalized_training_contract(args),
        "evidence_artifacts": evidence_artifacts(args),
        "sues_manifest": {
            "path": str(sues_manifest),
            "bytes": sues_manifest.stat().st_size,
            "sha256": sha256_file(sues_manifest),
        },
        "frozen_core": {
            "path": str(Path(core.__file__).resolve()),
            "sha256": validate_frozen_core(),
        },
        "adapter": {
            "path": str(Path(__file__).resolve()),
            "sha256": adapter_sha256(),
        },
    }


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise HeldoutIntegrityError(f"Required JSON artifact is absent: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise HeldoutIntegrityError(f"JSON artifact is not a mapping: {path}")
    return value


def validate_payload_hash(payload: dict[str, Any], label: str) -> None:
    body = dict(payload)
    declared = body.pop("payload_sha256", None)
    if declared != canonical_sha256(body):
        raise HeldoutIntegrityError(f"{label} payload hash mismatch.")


def inspect_checkpoint(path: Path) -> dict[str, Any]:
    import torch

    payload = torch.load(
        path,
        map_location="cpu",
        weights_only=False,
        mmap=True,
    )
    try:
        required = {
            "epoch",
            "model_state",
            "optimizer_state",
            "scheduler_state",
            "scaler_state",
            "history",
            "rng_state",
            "immutable_config",
            "run_config_sha256",
        }
        if not isinstance(payload, dict) or not required.issubset(payload):
            raise HeldoutIntegrityError("T2 checkpoint is not a full formal checkpoint.")
        protocol = payload["immutable_config"].get("protocol", {})
        return {
            "epoch": int(payload["epoch"]),
            "history_rows": len(payload["history"]),
            "run_config_sha256": payload["run_config_sha256"],
            "heldout_altitude_m": protocol.get("heldout_altitude_m"),
            "heldout_altitude_fit_query_image_count": protocol.get(
                "heldout_altitude_fit_query_image_count"
            ),
            "heldout_membership_sha256": protocol.get(
                "heldout_membership_sha256"
            ),
        }
    finally:
        del payload


def validate_completed_fit(
    output_dir: Path,
    adapter_config_sha: str,
    heldout_altitude: str,
    variant: str,
    seed: int,
) -> dict[str, Any]:
    fit_manifest_path = output_dir / "heldout_fit_manifest.json"
    fit = load_json(fit_manifest_path)
    if fit.get("schema_version") != FIT_MANIFEST_SCHEMA:
        raise HeldoutIntegrityError("T2 fit-manifest schema mismatch.")
    validate_payload_hash(fit, "T2 fit manifest")
    expected = {
        "status": "completed",
        "heldout_altitude_m": heldout_altitude,
        "variant": variant,
        "seed": seed,
        "adapter_config_sha256": adapter_config_sha,
        "epochs_completed": 80,
        "final_epoch_index": 79,
        "official_test_metric_access_during_fit": False,
        "checkpoint_selection": "pre-specified final epoch",
    }
    for name, value in expected.items():
        if fit.get(name) != value:
            raise HeldoutIntegrityError(f"T2 fit-manifest {name} mismatch.")
    config_path = output_dir / "heldout_adapter_config.json"
    if (
        Path(fit.get("adapter_config_path", "")).resolve() != config_path.resolve()
        or not config_path.is_file()
        or sha256_file(config_path) != adapter_config_sha
    ):
        raise HeldoutIntegrityError("T2 adapter-config path or hash mismatch.")
    artifacts = {
        "core_run_config": output_dir / "run_config.json",
        "core_history": output_dir / "history.json",
        "core_run_manifest": output_dir / "run_manifest.json",
        "last_checkpoint": output_dir / "last.pt",
        "best_checkpoint": output_dir / "best.pt",
        "membership": output_dir / "heldout_membership.json",
    }
    for name, path in artifacts.items():
        if Path(fit[f"{name}_path"]).resolve() != path.resolve():
            raise HeldoutIntegrityError(f"T2 {name} path mismatch.")
        if not path.is_file() or sha256_file(path) != fit[f"{name}_sha256"]:
            raise HeldoutIntegrityError(f"T2 {name} artifact hash mismatch.")
    if fit["last_checkpoint_sha256"] != fit["best_checkpoint_sha256"]:
        raise HeldoutIntegrityError(
            "T2 fixed-schedule final checkpoints best.pt and last.pt differ."
        )
    core_manifest = load_json(artifacts["core_run_manifest"])
    validate_payload_hash(core_manifest, "Frozen-core T2 run manifest")
    if (
        core_manifest.get("status") != "completed"
        or core_manifest.get("epochs_completed") != 80
        or core_manifest.get("test_protocol_was_evaluated") is not False
        or core_manifest.get("sample_scale", {}).get("heldout_altitude_m")
        != heldout_altitude
        or core_manifest.get("sample_scale", {}).get(
            "heldout_altitude_fit_query_image_count"
        )
        != 0
    ):
        raise HeldoutIntegrityError("Frozen-core T2 completion audit failed.")
    history = json.loads(artifacts["core_history"].read_text(encoding="utf-8"))
    if (
        not isinstance(history, list)
        or len(history) != 80
        or [int(row.get("epoch", -1)) for row in history] != list(range(80))
    ):
        raise HeldoutIntegrityError("T2 epoch history is incomplete or noncontiguous.")
    membership = load_json(artifacts["membership"])
    validate_payload_hash(membership, "T2 membership")
    checkpoint = inspect_checkpoint(artifacts["last_checkpoint"])
    if (
        checkpoint["epoch"] != 79
        or checkpoint["history_rows"] != 80
        or checkpoint["heldout_altitude_m"] != heldout_altitude
        or checkpoint["heldout_altitude_fit_query_image_count"] != 0
        or checkpoint["heldout_membership_sha256"]
        != sha256_file(artifacts["membership"])
        or checkpoint["run_config_sha256"] != fit["core_run_config_payload_sha256"]
    ):
        raise HeldoutIntegrityError("T2 final checkpoint audit failed.")
    return fit


def run_fit(
    args: argparse.Namespace,
    heldout_altitude: str,
    adapter_config: dict[str, Any],
) -> dict[str, Any]:
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    config_path = output_dir / "heldout_adapter_config.json"
    config_sha = immutable_json(config_path, adapter_config)
    fit_manifest_path = output_dir / "heldout_fit_manifest.json"
    if fit_manifest_path.exists():
        return validate_completed_fit(
            output_dir,
            config_sha,
            heldout_altitude,
            args.variant,
            args.seed,
        )

    membership_path = output_dir / "heldout_membership.json"
    retained_training = [
        path
        for path in (
            output_dir / "last.pt",
            output_dir / "best.pt",
            output_dir / "history.json",
            output_dir / "run_manifest.json",
            membership_path,
            output_dir / "heldout_fit_status.json",
        )
        if path.exists()
    ]
    if args.resume == "none" and retained_training:
        raise HeldoutIntegrityError(
            "T2 output contains a retained attempt; archive it before a "
            f"fresh epoch-zero fit: {[path.name for path in retained_training]}"
        )
    if args.resume == "last" and not (output_dir / "last.pt").is_file():
        raise HeldoutIntegrityError("T2 --resume last requires last.pt.")

    status_path = output_dir / "heldout_fit_status.json"
    started_utc = utc_now()
    resume_checkpoint_sha = (
        sha256_file(output_dir / "last.pt") if args.resume == "last" else None
    )
    atomic_json(
        status_path,
        {
            "schema_version": STATUS_SCHEMA,
            "status": "running",
            "adapter_config_sha256": config_sha,
            "attempt_started_utc": started_utc,
            "resume": args.resume,
            "resume_checkpoint_sha256": resume_checkpoint_sha,
        },
    )
    started = time.perf_counter()
    original_builder = core.build_training_protocol
    core.build_training_protocol = make_protocol_builder(
        original_builder,
        heldout_altitude,
        membership_path,
    )
    try:
        core.run_train(args)
        duration = time.perf_counter() - started
        core_manifest = load_json(output_dir / "run_manifest.json")
        validate_payload_hash(core_manifest, "Frozen-core T2 run manifest")
        if (
            core_manifest.get("status") != "completed"
            or core_manifest.get("epochs_completed") != 80
            or core_manifest.get("test_protocol_was_evaluated") is not False
        ):
            raise HeldoutIntegrityError("Frozen core did not complete the fixed T2 fit.")
        core_run_config = load_json(output_dir / "run_config.json")
        run_config_payload_sha = core_run_config.get("run_config_sha256")
        if not isinstance(run_config_payload_sha, str):
            raise HeldoutIntegrityError("Frozen-core run-config payload hash is absent.")
        artifacts = {
            "core_run_config": output_dir / "run_config.json",
            "core_history": output_dir / "history.json",
            "core_run_manifest": output_dir / "run_manifest.json",
            "last_checkpoint": output_dir / "last.pt",
            "best_checkpoint": output_dir / "best.pt",
            "membership": membership_path,
        }
        fit_payload: dict[str, Any] = {
            "schema_version": FIT_MANIFEST_SCHEMA,
            "status": "completed",
            "heldout_altitude_m": heldout_altitude,
            "variant": args.variant,
            "seed": args.seed,
            "adapter_config_path": str(config_path),
            "adapter_config_sha256": config_sha,
            "epochs_completed": 80,
            "final_epoch_index": 79,
            "core_run_config_payload_sha256": run_config_payload_sha,
            "final_invocation_duration_seconds": duration,
            "resumed_from_checkpoint": args.resume == "last",
            "resume_checkpoint_sha256_before_fit": resume_checkpoint_sha,
            "official_test_metric_access_during_fit": False,
            "checkpoint_selection": "pre-specified final epoch",
            "completed_utc": utc_now(),
        }
        for name, path in artifacts.items():
            fit_payload[f"{name}_path"] = str(path.resolve())
            fit_payload[f"{name}_sha256"] = sha256_file(path)
        fit = {
            **fit_payload,
            "payload_sha256": canonical_sha256(fit_payload),
        }
        immutable_json(fit_manifest_path, fit)
        fit = validate_completed_fit(
            output_dir,
            config_sha,
            heldout_altitude,
            args.variant,
            args.seed,
        )
        atomic_json(
            status_path,
            {
                "schema_version": STATUS_SCHEMA,
                "status": "completed",
                "adapter_config_sha256": config_sha,
                "fit_manifest_sha256": sha256_file(fit_manifest_path),
                "completed_utc": fit["completed_utc"],
            },
        )
        return fit
    except BaseException as error:
        atomic_json(
            status_path,
            {
                "schema_version": STATUS_SCHEMA,
                "status": "failed",
                "adapter_config_sha256": config_sha,
                "attempt_started_utc": started_utc,
                "failed_utc": utc_now(),
                "attempt_duration_seconds": time.perf_counter() - started,
                "resume": args.resume,
                "resume_checkpoint_sha256": resume_checkpoint_sha,
                "error_type": type(error).__name__,
                "error": str(error),
            },
        )
        raise
    finally:
        core.build_training_protocol = original_builder


def run_preflight(
    args: argparse.Namespace,
    heldout_altitude: str,
    adapter_config: dict[str, Any],
) -> dict[str, Any]:
    data_root = Path(args.data_root).expanduser().resolve(strict=True)
    store = core.EvidenceStore.load([Path(path) for path in args.evidence])
    records = core.derive_all_records(store, data_root, "sues200")
    sues_train_ids, sues_manifest = core.parse_sues_manifest(
        Path(args.sues_manifest).expanduser()
    )
    filtered = filter_heldout_records(records, heldout_altitude)
    membership = membership_payload(
        records,
        filtered,
        heldout_altitude,
        sues_train_ids,
    )
    protocol = core.build_training_protocol(
        filtered,
        "sues200",
        args.val_fraction,
        args.seed,
        sues_train_ids,
    )
    if any(
        row.view == "drone" and row.altitude == heldout_altitude
        for row in protocol.train_queries
    ):
        raise HeldoutIntegrityError("T2 preflight detected held-out-altitude leakage.")
    inventory = core.inventory_hash(
        core.records_for_training_inventory(protocol),
        args.data_hash_mode,
    )
    return {
        "schema_version": "lgm-game.sues-heldout-preflight.v1",
        "status": "completed",
        "manuscript_result": False,
        "dataset": "sues200",
        "heldout_altitude_m": heldout_altitude,
        "seen_altitudes_m": [
            altitude
            for altitude in core.SUES_ALTITUDES
            if altitude != heldout_altitude
        ],
        "variant": args.variant,
        "seed": args.seed,
        "fit_identity_count": len(protocol.train_ids),
        "fit_query_image_count": len(protocol.train_queries),
        "fit_gallery_image_count": sum(
            len(rows) for rows in protocol.train_gallery_by_label.values()
        ),
        "heldout_altitude_fit_query_image_count": 0,
        "membership": membership,
        "training_image_inventory": inventory,
        "sues_manifest": sues_manifest,
        "adapter_config_payload_sha256": canonical_sha256(adapter_config),
        "official_test_metric_access": False,
        "model_constructed": False,
        "optimizer_step_executed": False,
    }


def parse_args(
    argv: Sequence[str] | None = None,
) -> tuple[str, bool, argparse.Namespace]:
    wrapper = argparse.ArgumentParser(description=__doc__)
    wrapper.add_argument(
        "--heldout-altitude",
        choices=core.SUES_ALTITUDES,
        required=True,
    )
    wrapper.add_argument("--preflight-only", action="store_true")
    wrapper.add_argument(
        "core_arguments",
        nargs=argparse.REMAINDER,
        help="Frozen formal train command and arguments.",
    )
    wrapper_args = wrapper.parse_args(argv)
    remaining = list(wrapper_args.core_arguments)
    if remaining and remaining[0] == "--":
        remaining = remaining[1:]
    if not remaining:
        wrapper.error("the frozen core train command is required")
    core_args = core.build_parser().parse_args(remaining)
    setattr(core_args, "heldout_altitude", wrapper_args.heldout_altitude)
    return (
        wrapper_args.heldout_altitude,
        wrapper_args.preflight_only,
        core_args,
    )


def main(argv: Sequence[str] | None = None) -> int:
    heldout_altitude, preflight_only, args = parse_args(argv)
    try:
        validate_frozen_core()
        validate_core_args(args, heldout_altitude)
        adapter_config = build_adapter_config(args, heldout_altitude)
        if preflight_only:
            fit = run_preflight(args, heldout_altitude, adapter_config)
        else:
            fit = run_fit(args, heldout_altitude, adapter_config)
    except (HeldoutIntegrityError, OSError, ValueError, RuntimeError) as error:
        raise SystemExit(f"ERROR: {error}") from error
    print(json.dumps(fit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
