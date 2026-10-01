"""Sequential, resumable orchestrator for the four formal robustness runs.

The orchestrator launches no work until all four corresponding seed-1,
80-epoch formal checkpoints pass the frozen training runner's completion
audit.  It then executes the existing image-level evaluator one run at a time.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


EXPERIMENTS_DIR = Path(__file__).resolve().parent
if str(EXPERIMENTS_DIR) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS_DIR))

import formal_robustness_common as common  # noqa: E402
import run_frozen_formal_matrix as formal_matrix  # noqa: E402
import run_image_level_robustness as evaluator  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    delivery_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description=(
            "Wait for all four frozen seed-1 checkpoints, then run University/SUES "
            "x visual/full image-level robustness sequentially and resumably."
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
        "--stage",
        choices=("status", "run"),
        default="run",
        help="status performs only read-only readiness/completion checks.",
    )
    parser.add_argument(
        "--wait",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Wait until all four checkpoints are complete before launching any evaluator.",
    )
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument(
        "--wait-timeout-seconds",
        type=int,
        default=0,
        help="0 waits indefinitely; positive values fail after the bound.",
    )
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--eval-batch-size", type=int, default=128)
    parser.add_argument("--eval-chunk-size", type=int, default=128)
    parser.add_argument("--image-workers", type=int, default=8)
    parser.add_argument(
        "--amp",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--clip-precision",
        choices=("match-cache", "fp32", "fp16", "bf16"),
        default="match-cache",
    )
    parser.add_argument(
        "--clip-local-files-only",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--clip-clean-audit-samples", type=int, default=64)
    parser.add_argument(
        "--ledger",
        type=Path,
        default=None,
        help="Defaults to lgm_game_pytorch/runs/frozen_robustness_matrix_ledger.json.",
    )
    args = parser.parse_args(argv)
    if args.poll_seconds <= 0:
        parser.error("--poll-seconds must be positive.")
    if args.wait_timeout_seconds < 0:
        parser.error("--wait-timeout-seconds cannot be negative.")
    if args.eval_batch_size <= 0 or args.eval_chunk_size <= 0:
        parser.error("Evaluation batch and ranking chunk sizes must be positive.")
    if args.image_workers < 0:
        parser.error("--image-workers cannot be negative.")
    if args.clip_clean_audit_samples <= 0:
        parser.error("--clip-clean-audit-samples must be positive.")
    return args


def robustness_command(
    args: argparse.Namespace,
    spec: common.RobustnessRunSpec,
    evaluator_path: Path,
    sues_manifest: Path,
) -> list[str]:
    command = [
        str(args.python.expanduser().resolve()),
        str(evaluator_path.resolve()),
        "--dataset",
        spec.dataset,
        "--data-root",
        str(spec.data_root),
        "--evidence",
        str(spec.evidence),
        "--checkpoint",
        str(spec.checkpoint),
        "--output-dir",
        str(spec.output_dir),
        "--sues-manifest",
        str(sues_manifest),
        "--device",
        str(args.device),
        "--eval-batch-size",
        str(args.eval_batch_size),
        "--eval-chunk-size",
        str(args.eval_chunk_size),
        "--image-workers",
        str(args.image_workers),
        "--corruption-seed",
        str(evaluator.DEFAULT_CORRUPTION_SEED),
        "--clip-precision",
        str(args.clip_precision),
        "--clip-clean-audit-samples",
        str(args.clip_clean_audit_samples),
        "--amp" if args.amp else "--no-amp",
        (
            "--clip-local-files-only"
            if args.clip_local_files_only
            else "--no-clip-local-files-only"
        ),
    ]
    return command


def training_readiness(
    specs: Sequence[common.RobustnessRunSpec],
    frozen_specs: MappingKey,
    datasets: dict[str, formal_matrix.DatasetSpec],
    formal_script_sha256: str,
) -> dict[str, list[str]]:
    readiness: dict[str, list[str]] = {}
    for spec in specs:
        key = (spec.dataset, spec.variant)
        frozen = frozen_specs[key]
        issues = formal_matrix.training_completion_issues(
            frozen,
            datasets[spec.dataset],
            formal_script_sha256,
        )
        if not issues:
            issues.extend(
                formal_matrix.checkpoint_artifact_hash_issues(
                    frozen, names=("best.pt", "last.pt")
                )
            )
        readiness[spec.identifier] = issues
    return readiness


# A small alias keeps the runtime annotation readable without importing typing
# constructs that add no behavior.
MappingKey = dict[tuple[str, str], formal_matrix.RunSpec]


def ledger_run_record(
    ledger: dict[str, Any],
    identifier: str,
) -> dict[str, Any]:
    runs = ledger.setdefault("runs", {})
    record = runs.setdefault(
        identifier,
        {
            "status": "pending_checkpoint",
            "attempts": [],
        },
    )
    return record


def write_ledger(path: Path, ledger: dict[str, Any]) -> None:
    ledger["updated_utc"] = utc_now()
    common.atomic_json(path, ledger)


def base_environment(delivery_root: Path) -> dict[str, str]:
    environment = dict(os.environ)
    package_root = delivery_root / "lgm_game_pytorch"
    existing = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = (
        str(package_root)
        if not existing
        else str(package_root) + os.pathsep + existing
    )
    environment["PYTHONHASHSEED"] = "1"
    environment["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    return environment


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    delivery_root = args.delivery_root.expanduser().resolve(strict=True)
    package_root = delivery_root / "lgm_game_pytorch"
    evaluator_path = Path(evaluator.__file__).resolve()
    formal_script = package_root / "lgm_game_pytorch" / "formal_retrieval.py"
    protocol_path = delivery_root / "FORMAL_EXPERIMENT_PROTOCOL.md"
    sues_manifest = (
        package_root / "manifests" / "sues200_official_train_ids.yaml"
    ).resolve(strict=True)
    python_path = args.python.expanduser().resolve(strict=True)
    args.python = python_path

    specs = common.build_run_specs(
        delivery_root, args.university_root, args.sues_root
    )
    datasets = formal_matrix.dataset_specs(
        delivery_root, args.university_root, args.sues_root
    )
    frozen_list = formal_matrix.main_run_specs(
        delivery_root,
        common.DATASETS,
        common.VARIANTS,
        (1,),
    )
    frozen_specs: MappingKey = {
        (spec.dataset, spec.variant): spec for spec in frozen_list
    }
    if set(frozen_specs) != {
        (dataset, variant)
        for dataset in common.DATASETS
        for variant in common.VARIANTS
    }:
        raise RuntimeError("Frozen checkpoint registry is not exactly 2x2.")

    ledger_path = (
        args.ledger.expanduser().resolve()
        if args.ledger is not None
        else package_root / "runs" / "frozen_robustness_matrix_ledger.json"
    )
    source_hashes = {
        "orchestrator": common.sha256_file(Path(__file__).resolve()),
        "evaluator": common.sha256_file(evaluator_path),
        "common_validator": common.sha256_file(Path(common.__file__).resolve()),
        "formal_matrix_runner": common.sha256_file(Path(formal_matrix.__file__).resolve()),
        "formal_retrieval": common.sha256_file(formal_script),
        "frozen_protocol": common.sha256_file(protocol_path),
    }
    commands = {
        spec.identifier: robustness_command(
            args, spec, evaluator_path, sues_manifest
        )
        for spec in specs
    }
    immutable_config = {
        "schema_version": common.SCHEMA_VERSION,
        "registered_runs": [
            {
                "identifier": spec.identifier,
                "dataset": spec.dataset,
                "variant": spec.variant,
                "seed": 1,
                "data_root": str(spec.data_root),
                "evidence": str(spec.evidence),
                "evidence_sha256": common.sha256_file(spec.evidence),
                "checkpoint": str(spec.checkpoint),
                "output_dir": str(spec.output_dir),
                "command": commands[spec.identifier],
            }
            for spec in specs
        ],
        "source_hashes": source_hashes,
        "sues_manifest": {
            "path": str(sues_manifest),
            "sha256": common.sha256_file(sues_manifest),
        },
        "execution": {
            "sequential": True,
            "all_four_checkpoints_complete_before_first_launch": True,
            "device": args.device,
            "eval_batch_size": args.eval_batch_size,
            "eval_chunk_size": args.eval_chunk_size,
            "image_workers": args.image_workers,
            "amp": args.amp,
            "clip_precision": args.clip_precision,
            "clip_local_files_only": args.clip_local_files_only,
            "clip_clean_audit_samples": args.clip_clean_audit_samples,
            "corruption_seed": evaluator.DEFAULT_CORRUPTION_SEED,
        },
    }
    config_sha = common.canonical_sha256(immutable_config)
    if ledger_path.is_file():
        ledger = common.load_json(ledger_path)
        if (
            ledger.get("schema_version") != common.SCHEMA_VERSION
            or ledger.get("config_sha256") != config_sha
            or ledger.get("immutable_config") != immutable_config
        ):
            raise RuntimeError(
                "Existing robustness ledger belongs to a different immutable "
                "registry/source/configuration. Use a new ledger path."
            )
    else:
        ledger = {
            "schema_version": common.SCHEMA_VERSION,
            "created_utc": utc_now(),
            "status": "initialized",
            "config_sha256": config_sha,
            "immutable_config": immutable_config,
            "runs": {},
        }
        for spec in specs:
            ledger_run_record(ledger, spec.identifier)
        write_ledger(ledger_path, ledger)

    formal_script_sha = source_hashes["formal_retrieval"]
    readiness = training_readiness(
        specs, frozen_specs, datasets, formal_script_sha
    )
    for spec in specs:
        record = ledger_run_record(ledger, spec.identifier)
        record["checkpoint_issues"] = readiness[spec.identifier]
        record["checkpoint_status"] = (
            "completed_and_verified"
            if not readiness[spec.identifier]
            else "waiting"
        )

    if args.stage == "status":
        completed_robustness = 0
        for spec in specs:
            record = ledger_run_record(ledger, spec.identifier)
            if spec.robustness_manifest.is_file():
                validation = common.validate_completed_robustness(
                    spec,
                    evaluator,
                    verify_artifacts=True,
                    verify_per_query=True,
                    expected_evaluator_sha256=source_hashes["evaluator"],
                )
                record["robustness_status"] = (
                    "completed_and_verified"
                    if validation.complete
                    else "invalid_completed_tree"
                )
                record["robustness_issues"] = validation.issues
                if validation.complete:
                    completed_robustness += 1
            else:
                record["robustness_status"] = "not_completed"
        ledger["status"] = "status_only"
        ledger["checkpoint_ready_count"] = sum(
            not value for value in readiness.values()
        )
        ledger["robustness_complete_count"] = completed_robustness
        write_ledger(ledger_path, ledger)
        print(
            json.dumps(
                {
                    "checkpoint_readiness": readiness,
                    "robustness_complete_count": completed_robustness,
                    "ledger": str(ledger_path),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if completed_robustness == 4 else 2

    waiting_started = time.monotonic()
    while any(readiness.values()):
        ledger["status"] = "waiting_for_all_four_checkpoints"
        ledger["checkpoint_ready_count"] = sum(
            not value for value in readiness.values()
        )
        write_ledger(ledger_path, ledger)
        if not args.wait:
            raise RuntimeError(
                "Not all four frozen checkpoints are complete; --no-wait forbids polling."
            )
        elapsed = time.monotonic() - waiting_started
        if args.wait_timeout_seconds and elapsed >= args.wait_timeout_seconds:
            raise TimeoutError(
                "Timed out waiting for all four seed-1 formal checkpoints."
            )
        print(
            f"{utc_now()} | waiting: "
            f"{sum(not value for value in readiness.values())}/4 checkpoints ready",
            flush=True,
        )
        time.sleep(args.poll_seconds)
        readiness = training_readiness(
            specs, frozen_specs, datasets, formal_script_sha
        )
        for spec in specs:
            record = ledger_run_record(ledger, spec.identifier)
            record["checkpoint_issues"] = readiness[spec.identifier]
            record["checkpoint_status"] = (
                "completed_and_verified"
                if not readiness[spec.identifier]
                else "waiting"
            )

    ledger["status"] = "running_sequential_robustness"
    ledger["all_four_checkpoints_verified_utc"] = utc_now()
    write_ledger(ledger_path, ledger)
    environment = base_environment(delivery_root)

    for spec in specs:
        record = ledger_run_record(ledger, spec.identifier)
        if spec.robustness_manifest.is_file():
            existing = common.validate_completed_robustness(
                spec,
                evaluator,
                verify_artifacts=True,
                verify_per_query=True,
                expected_evaluator_sha256=source_hashes["evaluator"],
            )
            if existing.complete:
                record["status"] = "completed_and_verified"
                record["robustness_manifest_sha256"] = common.sha256_file(
                    spec.robustness_manifest
                )
                write_ledger(ledger_path, ledger)
                continue
            record["status"] = "invalid_completed_tree"
            record["validation_issues"] = existing.issues
            ledger["status"] = "failed_integrity_gate"
            write_ledger(ledger_path, ledger)
            raise RuntimeError(
                f"{spec.identifier} has a completed-looking but invalid robustness "
                "tree; refusing to overwrite or silently resume it."
            )

        # Revalidate immediately before each launch. A checkpoint or its manifest
        # must not change between the global readiness gate and execution.
        fresh = training_readiness(
            [spec], frozen_specs, datasets, formal_script_sha
        )[spec.identifier]
        if fresh:
            record["status"] = "checkpoint_became_invalid"
            record["checkpoint_issues"] = fresh
            ledger["status"] = "failed_integrity_gate"
            write_ledger(ledger_path, ledger)
            raise RuntimeError(
                f"{spec.identifier} checkpoint failed revalidation: {fresh}"
            )

        command = commands[spec.identifier]
        attempt = {
            "started_utc": utc_now(),
            "command": command,
            "evaluator_sha256": source_hashes["evaluator"],
        }
        record.setdefault("attempts", []).append(attempt)
        record["status"] = "running"
        write_ledger(ledger_path, ledger)
        spec.output_dir.mkdir(parents=True, exist_ok=True)
        # Keep wrapper logs outside the evaluator output tree. Otherwise the
        # evaluator could hash a still-open stdout file and its final log line
        # would correctly invalidate that artifact hash.
        wrapper_log_dir = (
            ledger_path.parent / "frozen_robustness_orchestrator_logs"
        )
        wrapper_log_dir.mkdir(parents=True, exist_ok=True)
        log_stem = spec.identifier.replace("/", "__")
        stdout_path = wrapper_log_dir / f"{log_stem}.stdout.log"
        stderr_path = wrapper_log_dir / f"{log_stem}.stderr.log"
        with stdout_path.open("a", encoding="utf-8", newline="\n") as stdout, stderr_path.open(
            "a", encoding="utf-8", newline="\n"
        ) as stderr:
            completed = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                env=environment,
                check=False,
            )
        attempt["completed_utc"] = utc_now()
        attempt["returncode"] = completed.returncode
        attempt["stdout"] = {
            "path": str(stdout_path),
            "sha256": common.sha256_file(stdout_path),
            "bytes": stdout_path.stat().st_size,
        }
        attempt["stderr"] = {
            "path": str(stderr_path),
            "sha256": common.sha256_file(stderr_path),
            "bytes": stderr_path.stat().st_size,
        }
        if completed.returncode != 0:
            record["status"] = "evaluator_failed_retained_for_resume"
            ledger["status"] = "failed_evaluator"
            write_ledger(ledger_path, ledger)
            raise RuntimeError(
                f"{spec.identifier} evaluator exited {completed.returncode}; "
                "artifacts are retained and the same command can resume."
            )

        validation = common.validate_completed_robustness(
            spec,
            evaluator,
            verify_artifacts=True,
            verify_per_query=True,
            expected_evaluator_sha256=source_hashes["evaluator"],
        )
        if not validation.complete:
            record["status"] = "evaluator_output_failed_integrity"
            record["validation_issues"] = validation.issues
            ledger["status"] = "failed_integrity_gate"
            write_ledger(ledger_path, ledger)
            raise RuntimeError(
                f"{spec.identifier} output failed strict validation: "
                f"{validation.issues[:10]}"
            )
        record["status"] = "completed_and_verified"
        record["robustness_manifest_sha256"] = common.sha256_file(
            spec.robustness_manifest
        )
        record["run_config_sha256"] = validation.manifest.get(
            "run_config_sha256"
        )
        write_ledger(ledger_path, ledger)

    ledger["status"] = "completed"
    ledger["completed_utc"] = utc_now()
    ledger["completed_run_count"] = sum(
        ledger_run_record(ledger, spec.identifier).get("status")
        == "completed_and_verified"
        for spec in specs
    )
    if ledger["completed_run_count"] != common.EXPECTED_RUN_COUNT:
        raise AssertionError("Ledger cannot complete without all four verified runs.")
    write_ledger(ledger_path, ledger)
    print(f"Completed four formal robustness runs; ledger: {ledger_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
