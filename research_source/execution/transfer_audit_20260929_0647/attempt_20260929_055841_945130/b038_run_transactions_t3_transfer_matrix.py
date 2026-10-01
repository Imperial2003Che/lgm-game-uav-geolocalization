#!/usr/bin/env python3
"""Audit or execute the 12 registered bidirectional zero-shot T3 evaluations."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DELIVERY_ROOT_DEFAULT = PACKAGE_ROOT.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from lgm_game_pytorch import formal_retrieval as core
from experiments import run_frozen_formal_matrix as primary_runner
from experiments.run_cross_dataset_evaluation import (
    EXPECTED_CORE_SHA256,
    EXPECTED_EVIDENCE,
    EXPECTED_SUES_MANIFEST_SHA256,
    EXPECTED_TASKS,
    validate_completed,
)


MATRIX_SCHEMA = "lgm-game.transactions-t3-transfer-matrix.v1"
AUDIT_SCHEMA = "lgm-game.transactions-t3-static-audit.v1"
LEDGER_SCHEMA = "lgm-game.transactions-t3-ledger.v1"
EXPECTED_ROWS = tuple(
    (
        f"{source}_to_{target}/{variant}/seed_{seed}",
        source,
        target,
        variant,
        seed,
        len(EXPECTED_TASKS[target]),
    )
    for source, target in (
        ("university1652", "sues200"),
        ("sues200", "university1652"),
    )
    for variant in ("visual", "full")
    for seed in (1, 2, 3)
)


class T3IntegrityError(RuntimeError):
    """Raised when the registered T3 transfer matrix fails closed."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(payload: Any) -> str:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def atomic_json(path: Path, payload: Any) -> None:
    serialized = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    if temporary.exists():
        raise T3IntegrityError(f"Refusing to overwrite stale temporary: {temporary}")
    temporary.write_bytes(serialized)
    temporary.replace(path)


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise T3IntegrityError(f"Required JSON file is absent: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise T3IntegrityError(f"JSON root must be a mapping: {path}")
    return value


def validate_payload_hash(payload: dict[str, Any], label: str) -> None:
    body = dict(payload)
    declared = body.pop("payload_sha256", None)
    if declared != canonical_sha256(body):
        raise T3IntegrityError(f"{label} payload hash mismatch.")


def validate_matrix(path: Path) -> dict[str, Any]:
    matrix = load_json(path)
    expected_header = {
        "schema_version": MATRIX_SCHEMA,
        "status": "registered_not_executed",
        "registered_evaluation_count": 12,
        "design": "bidirectional_zero_shot_cross_dataset_transfer",
        "source_variants": ["visual", "full"],
        "seeds": [1, 2, 3],
        "checkpoint_selection": "pre-specified final epoch",
        "target_dataset_training_or_calibration": False,
    }
    for name, expected in expected_header.items():
        if matrix.get(name) != expected:
            raise T3IntegrityError(f"T3 matrix header {name} changed.")
    rows = matrix.get("evaluations")
    if not isinstance(rows, list) or len(rows) != 12:
        raise T3IntegrityError("T3 matrix does not contain exactly 12 rows.")
    observed = []
    for ordinal, row in enumerate(rows, start=1):
        if row.get("ordinal") != ordinal:
            raise T3IntegrityError("T3 matrix ordinals are not contiguous.")
        observed.append(
            (
                row.get("evaluation_id"),
                row.get("source_dataset"),
                row.get("target_dataset"),
                row.get("variant"),
                row.get("seed"),
                row.get("expected_target_task_count"),
            )
        )
    if tuple(observed) != EXPECTED_ROWS:
        raise T3IntegrityError("T3 registered transfer semantics changed.")
    return matrix


def primary_source_gate(
    delivery_root: Path,
    university_root: Path,
    sues_root: Path,
    require_complete: bool,
) -> dict[str, Any]:
    data = primary_runner.dataset_specs(
        delivery_root,
        university_root,
        sues_root,
    )
    specs = primary_runner.main_run_specs(
        delivery_root,
        ("university1652", "sues200"),
        ("visual", "full"),
        (1, 2, 3),
    )
    formal_path = (
        delivery_root
        / "lgm_game_pytorch"
        / "lgm_game_pytorch"
        / "formal_retrieval.py"
    ).resolve(strict=True)
    formal_sha = sha256_file(formal_path)
    if formal_sha != EXPECTED_CORE_SHA256:
        raise T3IntegrityError("T3 frozen formal core hash changed.")
    incomplete = {}
    if require_complete:
        for spec in specs:
            issues = primary_runner.training_completion_issues(
                spec,
                data[spec.dataset],
                formal_sha,
            )
            if issues:
                incomplete[spec.identifier] = issues
        if incomplete:
            raise T3IntegrityError(
                "T3 is gated until all 12 registered source checkpoints pass "
                f"the primary completion audit: {list(incomplete.items())[:3]}"
            )
    return {
        "registered_source_checkpoint_count": len(specs),
        "all_source_checkpoints_complete": require_complete and not incomplete,
        "gate_status": (
            "complete"
            if require_complete and not incomplete
            else "not_checked_in_static_design_audit"
        ),
        "formal_core_sha256": formal_sha,
    }


def target_protocol_audit(
    dataset: str,
    data_root: Path,
    evidence_path: Path,
    sues_manifest: Path,
) -> dict[str, Any]:
    store = core.EvidenceStore.load([evidence_path])
    records = core.derive_all_records(store, data_root, dataset)
    train_ids, manifest_info = core.parse_sues_manifest(
        sues_manifest if dataset == "sues200" else None
    )
    tasks = core.build_official_evaluation_tasks(records, dataset, train_ids)
    if tuple(task.name for task in tasks) != EXPECTED_TASKS[dataset]:
        raise T3IntegrityError(f"T3 {dataset} official task set changed.")
    return {
        "task_count": len(tasks),
        "task_names": [task.name for task in tasks],
        "protocol_membership_sha256": core.protocol_membership_hash(tasks),
        "task_scale": {
            task.name: {
                "queries": len(task.query),
                "gallery_images": len(task.gallery),
                "query_identities": len({row.label for row in task.query}),
                "gallery_identities": len({row.label for row in task.gallery}),
            }
            for task in tasks
        },
        "sues_manifest": manifest_info if dataset == "sues200" else None,
    }


def static_audit(args: argparse.Namespace, require_primary: bool) -> dict[str, Any]:
    delivery = args.delivery_root.resolve(strict=True)
    experiments = delivery / "lgm_game_pytorch" / "experiments"
    matrix_path = experiments / "transactions_t3_transfer_matrix.json"
    adapter_path = experiments / "run_cross_dataset_evaluation.py"
    protocol_path = delivery / "TRANSACTIONS_EXTENSION_PROTOCOL.md"
    matrix = validate_matrix(matrix_path)
    if Path(sys.executable).resolve(strict=True) != args.python.resolve(strict=True):
        raise T3IntegrityError("T3 runner must use the declared primary interpreter.")
    if sha256_file(Path(core.__file__).resolve()) != EXPECTED_CORE_SHA256:
        raise T3IntegrityError("T3 frozen formal core hash changed.")
    sues_manifest = (
        delivery
        / "lgm_game_pytorch"
        / "manifests"
        / "sues200_official_train_ids.yaml"
    ).resolve(strict=True)
    if sha256_file(sues_manifest) != EXPECTED_SUES_MANIFEST_SHA256:
        raise T3IntegrityError("T3 SUES manifest changed.")
    roots = {
        "university1652": args.university_root.resolve(strict=True),
        "sues200": args.sues_root.resolve(strict=True),
    }
    evidence_paths = {
        "university1652": (
            delivery
            / "lgm_game_pytorch"
            / "evidence_cache"
            / "university1652_clip_image_evidence.npz"
        ).resolve(strict=True),
        "sues200": (
            delivery
            / "lgm_game_pytorch"
            / "evidence_cache"
            / "sues200_clip_image_evidence.npz"
        ).resolve(strict=True),
    }
    targets = {}
    for dataset in ("university1652", "sues200"):
        evidence_path = evidence_paths[dataset]
        meta_path = core.find_meta_path(evidence_path).resolve(strict=True)
        if (
            sha256_file(evidence_path) != EXPECTED_EVIDENCE[dataset]["sha256"]
            or sha256_file(meta_path)
            != EXPECTED_EVIDENCE[dataset]["meta_sha256"]
        ):
            raise T3IntegrityError(f"T3 frozen {dataset} evidence changed.")
        targets[dataset] = {
            "data_root": str(roots[dataset]),
            "evidence_path": str(evidence_path),
            "evidence_sha256": EXPECTED_EVIDENCE[dataset]["sha256"],
            "evidence_meta_path": str(meta_path),
            "evidence_meta_sha256": EXPECTED_EVIDENCE[dataset][
                "meta_sha256"
            ],
            "protocol": target_protocol_audit(
                dataset,
                roots[dataset],
                evidence_path,
                sues_manifest,
            ),
        }
    source_gate = primary_source_gate(
        delivery,
        args.university_root,
        args.sues_root,
        require_complete=require_primary,
    )
    payload = {
        "schema_version": AUDIT_SCHEMA,
        "status": (
            "ready_for_evaluation"
            if source_gate["all_source_checkpoints_complete"]
            else "static_design_verified_source_gate_pending"
        ),
        "manuscript_result": False,
        "registered_evaluation_count": len(matrix["evaluations"]),
        "matrix_path": str(matrix_path.resolve()),
        "matrix_sha256": sha256_file(matrix_path),
        "runner_path": str(Path(__file__).resolve()),
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "adapter_path": str(adapter_path.resolve()),
        "adapter_sha256": sha256_file(adapter_path),
        "formal_core_path": str(Path(core.__file__).resolve()),
        "formal_core_sha256": EXPECTED_CORE_SHA256,
        "protocol_path": str(protocol_path.resolve()),
        "protocol_sha256": sha256_file(protocol_path),
        "python": str(args.python.resolve()),
        "targets": targets,
        "source_gate": source_gate,
        "target_dataset_training_or_calibration": False,
        "model_constructed": False,
        "evaluation_executed": False,
    }
    payload["payload_sha256"] = canonical_sha256(payload)
    return payload


def assert_no_other_python_gpu_process() -> None:
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-compute-apps=pid,process_name",
            "--format=csv,noheader,nounits",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise T3IntegrityError(f"nvidia-smi process audit failed: {completed.stderr}")
    conflicts = []
    for line in completed.stdout.splitlines():
        fields = [field.strip() for field in line.split(",", 1)]
        if len(fields) != 2 or "python" not in fields[1].lower():
            continue
        try:
            pid = int(fields[0])
        except ValueError:
            continue
        if pid != os.getpid():
            conflicts.append({"pid": pid, "process_name": fields[1]})
    if conflicts:
        raise T3IntegrityError(
            f"Another Python GPU process is active; T3 must be serialized: {conflicts}"
        )


def evaluation_paths(
    args: argparse.Namespace,
    row: dict[str, Any],
) -> tuple[Path, Path, Path]:
    delivery = args.delivery_root.resolve()
    checkpoint = (
        delivery
        / "lgm_game_pytorch"
        / "runs"
        / "formal_main"
        / row["source_dataset"]
        / row["variant"]
        / f"seed_{row['seed']}"
        / "best.pt"
    )
    output = (
        delivery
        / "lgm_game_pytorch"
        / "evaluations"
        / "transactions_t3_transfer"
        / f"{row['source_dataset']}_to_{row['target_dataset']}"
        / row["variant"]
        / f"seed_{row['seed']}"
    )
    evidence = (
        delivery
        / "lgm_game_pytorch"
        / "evidence_cache"
        / (
            "university1652_clip_image_evidence.npz"
            if row["target_dataset"] == "university1652"
            else "sues200_clip_image_evidence.npz"
        )
    )
    return checkpoint, output, evidence


def evaluation_command(
    args: argparse.Namespace,
    row: dict[str, Any],
    checkpoint: Path,
    output: Path,
    evidence: Path,
) -> list[str]:
    delivery = args.delivery_root.resolve()
    adapter = (
        delivery
        / "lgm_game_pytorch"
        / "experiments"
        / "run_cross_dataset_evaluation.py"
    )
    target_root = (
        args.university_root
        if row["target_dataset"] == "university1652"
        else args.sues_root
    )
    sues_manifest = (
        delivery
        / "lgm_game_pytorch"
        / "manifests"
        / "sues200_official_train_ids.yaml"
    )
    return [
        str(args.python.resolve()),
        "-B",
        str(adapter.resolve()),
        "--source-dataset",
        row["source_dataset"],
        "--target-dataset",
        row["target_dataset"],
        "--variant",
        row["variant"],
        "--seed",
        str(row["seed"]),
        "--checkpoint",
        str(checkpoint.resolve()),
        "--data-root",
        str(target_root.resolve()),
        "--evidence",
        str(evidence.resolve()),
        "--sues-manifest",
        str(sues_manifest.resolve()),
        "--output-dir",
        str(output.resolve()),
        "--device",
        f"cuda:{args.device_index}",
        "--workers",
        "8",
        "--data-hash-mode",
        "content",
        "--amp",
        "--eval-batch-size",
        "128",
        "--eval-chunk-size",
        "128",
    ]


def initialize_or_verify_ledger(
    path: Path,
    audit: dict[str, Any],
    matrix: dict[str, Any],
) -> dict[str, Any]:
    frozen = {
        "static_audit": audit,
        "static_audit_payload_sha256": audit["payload_sha256"],
    }
    if path.exists():
        ledger = load_json(path)
        if ledger.get("schema_version") != LEDGER_SCHEMA:
            raise T3IntegrityError("T3 ledger schema mismatch.")
        if ledger.get("frozen_inputs") != frozen:
            raise T3IntegrityError("T3 frozen ledger inputs changed.")
        return ledger
    ledger = {
        "schema_version": LEDGER_SCHEMA,
        "created_utc": utc_now(),
        "updated_utc": utc_now(),
        "status": "registered",
        "registered_evaluation_count": len(matrix["evaluations"]),
        "frozen_inputs": frozen,
        "evaluations": {
            row["evaluation_id"]: {
                "ordinal": row["ordinal"],
                "source_dataset": row["source_dataset"],
                "target_dataset": row["target_dataset"],
                "variant": row["variant"],
                "seed": row["seed"],
                "status": "pending",
                "events": [],
            }
            for row in matrix["evaluations"]
        },
        "invocations": [],
    }
    atomic_json(path, ledger)
    return ledger


def record_event(
    ledger_path: Path,
    ledger: dict[str, Any],
    evaluation_id: str,
    event: dict[str, Any],
) -> None:
    row = ledger["evaluations"][evaluation_id]
    row["events"].append(event)
    row.update({key: value for key, value in event.items() if key != "command"})
    ledger["updated_utc"] = utc_now()
    atomic_json(ledger_path, ledger)


def run_evaluations(args: argparse.Namespace) -> dict[str, Any]:
    audit = static_audit(args, require_primary=True)
    validate_payload_hash(audit, "T3 static audit")
    delivery = args.delivery_root.resolve()
    matrix = validate_matrix(
        delivery
        / "lgm_game_pytorch"
        / "experiments"
        / "transactions_t3_transfer_matrix.json"
    )
    evaluations_root = (
        delivery
        / "lgm_game_pytorch"
        / "evaluations"
        / "transactions_t3_transfer"
    )
    ledger_path = evaluations_root / "transactions_t3_ledger.json"
    ledger = initialize_or_verify_ledger(ledger_path, audit, matrix)
    invocation = {
        "started_utc": utc_now(),
        "status": "running",
        "stage": "evaluate",
    }
    ledger["invocations"].append(invocation)
    ledger["status"] = "evaluating"
    atomic_json(ledger_path, ledger)
    try:
        for row in matrix["evaluations"]:
            evaluation_id = row["evaluation_id"]
            checkpoint, output, evidence = evaluation_paths(args, row)
            ledger_row = ledger["evaluations"][evaluation_id]
            config_path = output / "transfer_evaluation_config.json"
            if ledger_row["status"] == "completed":
                manifest = validate_completed(
                    output,
                    sha256_file(config_path),
                    row["source_dataset"],
                    row["target_dataset"],
                    row["variant"],
                    int(row["seed"]),
                )
                record_event(
                    ledger_path,
                    ledger,
                    evaluation_id,
                    {
                        "status": "completed",
                        "event_type": "skipped_already_complete",
                        "updated_utc": utc_now(),
                        "manifest_sha256": sha256_file(
                            output / "transfer_evaluation_manifest.json"
                        ),
                        "checkpoint_sha256": manifest["checkpoint_sha256"],
                    },
                )
                continue
            if ledger_row["status"] in {"running", "failed"}:
                raise T3IntegrityError(
                    f"{evaluation_id} is {ledger_row['status']!r}; diagnose and "
                    "archive the attempt before an explicitly authorized restart."
                )
            if (output / "transfer_evaluation_manifest.json").exists():
                manifest = validate_completed(
                    output,
                    sha256_file(config_path),
                    row["source_dataset"],
                    row["target_dataset"],
                    row["variant"],
                    int(row["seed"]),
                )
                record_event(
                    ledger_path,
                    ledger,
                    evaluation_id,
                    {
                        "status": "completed",
                        "event_type": "recovered_from_complete_artifacts",
                        "updated_utc": utc_now(),
                        "manifest_sha256": sha256_file(
                            output / "transfer_evaluation_manifest.json"
                        ),
                        "checkpoint_sha256": manifest["checkpoint_sha256"],
                    },
                )
                continue
            assert_no_other_python_gpu_process()
            command = evaluation_command(
                args,
                row,
                checkpoint,
                output,
                evidence,
            )
            log_dir = (
                evaluations_root
                / "process_logs"
                / f"{row['source_dataset']}_to_{row['target_dataset']}"
                / row["variant"]
                / f"seed_{row['seed']}"
            )
            log_dir.mkdir(parents=True, exist_ok=True)
            stdout_path = log_dir / "attempt_1_stdout.log"
            stderr_path = log_dir / "attempt_1_stderr.log"
            if stdout_path.exists() or stderr_path.exists():
                raise T3IntegrityError(
                    f"Refusing to overwrite T3 logs for {evaluation_id}."
                )
            record_event(
                ledger_path,
                ledger,
                evaluation_id,
                {
                    "status": "running",
                    "attempt": 1,
                    "started_utc": utc_now(),
                    "command": command,
                    "stdout_path": str(stdout_path.resolve()),
                    "stderr_path": str(stderr_path.resolve()),
                },
            )
            started = time.perf_counter()
            environment = dict(os.environ)
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            with stdout_path.open("x", encoding="utf-8", newline="\n") as stdout, (
                stderr_path.open("x", encoding="utf-8", newline="\n")
            ) as stderr:
                completed = subprocess.run(
                    command,
                    cwd=delivery / "lgm_game_pytorch",
                    env=environment,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout,
                    stderr=stderr,
                    check=False,
                )
            elapsed = time.perf_counter() - started
            if completed.returncode != 0:
                record_event(
                    ledger_path,
                    ledger,
                    evaluation_id,
                    {
                        "status": "failed",
                        "attempt": 1,
                        "finished_utc": utc_now(),
                        "elapsed_seconds": elapsed,
                        "return_code": completed.returncode,
                        "stdout_sha256": sha256_file(stdout_path),
                        "stderr_sha256": sha256_file(stderr_path),
                    },
                )
                raise T3IntegrityError(
                    f"T3 evaluation failed for {evaluation_id}; return code "
                    f"{completed.returncode}. No retry was attempted."
                )
            manifest = validate_completed(
                output,
                sha256_file(config_path),
                row["source_dataset"],
                row["target_dataset"],
                row["variant"],
                int(row["seed"]),
            )
            record_event(
                ledger_path,
                ledger,
                evaluation_id,
                {
                    "status": "completed",
                    "attempt": 1,
                    "finished_utc": utc_now(),
                    "elapsed_seconds": elapsed,
                    "return_code": 0,
                    "stdout_sha256": sha256_file(stdout_path),
                    "stderr_sha256": sha256_file(stderr_path),
                    "manifest_sha256": sha256_file(
                        output / "transfer_evaluation_manifest.json"
                    ),
                    "checkpoint_sha256": manifest["checkpoint_sha256"],
                },
            )
        incomplete = [
            evaluation_id
            for evaluation_id, row in ledger["evaluations"].items()
            if row["status"] != "completed"
        ]
        if incomplete:
            raise T3IntegrityError(f"T3 evaluations remain incomplete: {incomplete}")
        invocation["status"] = "completed"
        invocation["finished_utc"] = utc_now()
        ledger["status"] = "all_evaluations_complete"
        ledger["updated_utc"] = utc_now()
        atomic_json(ledger_path, ledger)
        return ledger
    except BaseException as error:
        invocation["status"] = "failed_or_interrupted"
        invocation["finished_utc"] = utc_now()
        invocation["error_type"] = type(error).__name__
        invocation["error"] = str(error)
        ledger["status"] = "failed_or_interrupted"
        ledger["updated_utc"] = utc_now()
        atomic_json(ledger_path, ledger)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--delivery-root",
        type=Path,
        default=DELIVERY_ROOT_DEFAULT,
    )
    parser.add_argument("--university-root", type=Path, required=True)
    parser.add_argument("--sues-root", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--device-index", type=int, default=0)
    parser.add_argument("--stage", choices=("audit", "evaluate"), default="audit")
    parser.add_argument(
        "--audit-output",
        type=Path,
        help=(
            "Optional JSON path for the non-result static audit. "
            "Valid only with --stage audit."
        ),
    )
    args = parser.parse_args()
    if args.device_index < 0:
        raise SystemExit("ERROR: --device-index must be non-negative.")
    if args.audit_output is not None and args.stage != "audit":
        raise SystemExit("ERROR: --audit-output is valid only with --stage audit.")
    try:
        payload = (
            static_audit(args, require_primary=False)
            if args.stage == "audit"
            else run_evaluations(args)
        )
        if args.audit_output is not None:
            atomic_json(args.audit_output.expanduser().resolve(), payload)
    except (T3IntegrityError, OSError, ValueError, RuntimeError) as error:
        raise SystemExit(f"ERROR: {error}") from error
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
