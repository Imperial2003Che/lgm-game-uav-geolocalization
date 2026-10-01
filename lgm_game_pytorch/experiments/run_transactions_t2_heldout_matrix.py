#!/usr/bin/env python3
"""Audit or execute the 24 registered SUES-200 held-out-altitude T2 fits."""

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
from typing import Any, Sequence

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DELIVERY_ROOT_DEFAULT = PACKAGE_ROOT.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from lgm_game_pytorch import formal_retrieval as core
from experiments import run_frozen_formal_matrix as primary_runner
from experiments.run_sues_heldout_fit import (
    EXPECTED_CORE_SHA256,
    EXPECTED_SUES_EVIDENCE_META_SHA256,
    EXPECTED_SUES_EVIDENCE_SHA256,
    EXPECTED_SUES_MANIFEST_SHA256,
    filter_heldout_records,
    membership_payload,
    validate_completed_fit,
    validate_frozen_core,
)


MATRIX_SCHEMA = "lgm-game.transactions-t2-heldout-matrix.v1"
AUDIT_SCHEMA = "lgm-game.transactions-t2-static-audit.v1"
LEDGER_SCHEMA = "lgm-game.transactions-t2-ledger.v1"
EXPECTED_RUNS = tuple(
    (
        f"heldout_{altitude}m/{variant}/seed_{seed}",
        altitude,
        variant,
        seed,
    )
    for altitude in core.SUES_ALTITUDES
    for variant in ("visual", "full")
    for seed in (1, 2, 3)
)


class T2IntegrityError(RuntimeError):
    """Raised when the registered T2 matrix fails closed."""


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
        raise T2IntegrityError(f"Refusing to overwrite stale temporary: {temporary}")
    temporary.write_bytes(serialized)
    temporary.replace(path)


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise T2IntegrityError(f"Required JSON file is absent: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise T2IntegrityError(f"JSON root must be a mapping: {path}")
    return value


def validate_payload_hash(payload: dict[str, Any], label: str) -> None:
    body = dict(payload)
    declared = body.pop("payload_sha256", None)
    if declared != canonical_sha256(body):
        raise T2IntegrityError(f"{label} payload hash mismatch.")


def validate_matrix(path: Path) -> dict[str, Any]:
    matrix = load_json(path)
    expected_header = {
        "schema_version": MATRIX_SCHEMA,
        "status": "registered_not_executed",
        "registered_run_count": 24,
        "dataset": "sues200",
        "design": "leave_one_altitude_out",
        "altitudes_m": list(core.SUES_ALTITUDES),
        "variants": ["visual", "full"],
        "seeds": [1, 2, 3],
        "epochs": 80,
        "checkpoint_selection": "pre-specified final epoch",
        "official_test_gate": (
            "after all 24 registered held-out-altitude fits pass completion audit"
        ),
    }
    for name, expected in expected_header.items():
        if matrix.get(name) != expected:
            raise T2IntegrityError(f"T2 matrix header {name} changed.")
    rows = matrix.get("runs")
    if not isinstance(rows, list) or len(rows) != 24:
        raise T2IntegrityError("T2 matrix does not contain exactly 24 rows.")
    observed = []
    for ordinal, row in enumerate(rows, start=1):
        if row.get("ordinal") != ordinal:
            raise T2IntegrityError("T2 matrix ordinals are not contiguous.")
        observed.append(
            (
                row.get("run_id"),
                row.get("heldout_altitude_m"),
                row.get("variant"),
                row.get("seed"),
            )
        )
    if tuple(observed) != EXPECTED_RUNS:
        raise T2IntegrityError("T2 registered run semantics changed.")
    return matrix


def catalog_training_files(
    records: Sequence[core.EvidenceRecord],
    train_ids: Sequence[str],
) -> dict[str, dict[str, Any]]:
    train_id_set = set(train_ids)
    selected = {
        record.relative_path: record
        for record in records
        if record.label in train_id_set
        and record.view in {"satellite", "drone"}
    }
    catalog = {}
    for relative_path, record in sorted(selected.items()):
        stat = record.absolute_path.stat()
        catalog[relative_path] = {
            "record": record,
            "bytes": stat.st_size,
            "sha256": sha256_file(record.absolute_path),
        }
    return catalog


def inventory_from_catalog(
    catalog: dict[str, dict[str, Any]],
    heldout_altitude: str,
) -> dict[str, Any]:
    digest = hashlib.sha256()
    total_bytes = 0
    file_count = 0
    for relative_path, row in sorted(catalog.items()):
        record = row["record"]
        if record.view == "drone" and record.altitude == heldout_altitude:
            continue
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(row["bytes"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(row["sha256"].encode("ascii"))
        digest.update(b"\n")
        total_bytes += int(row["bytes"])
        file_count += 1
    return {
        "mode": "content",
        "sha256": digest.hexdigest(),
        "file_count": file_count,
        "total_bytes": total_bytes,
    }


def audit_primary_completion(
    delivery_root: Path,
    university_root: Path,
    sues_root: Path,
) -> dict[str, Any]:
    data = primary_runner.dataset_specs(
        delivery_root,
        university_root,
        sues_root,
    )
    specs = primary_runner.main_run_specs(
        delivery_root,
        ("university1652", "sues200"),
        primary_runner.MAIN_VARIANTS,
        primary_runner.MAIN_SEEDS,
    )
    specs += primary_runner.sensitivity_run_specs(
        delivery_root,
        ("university1652", "sues200"),
    )
    formal_path = (
        delivery_root
        / "lgm_game_pytorch"
        / "lgm_game_pytorch"
        / "formal_retrieval.py"
    ).resolve(strict=True)
    formal_sha = sha256_file(formal_path)
    if formal_sha != EXPECTED_CORE_SHA256:
        raise T2IntegrityError("Primary frozen core hash changed.")
    incomplete: dict[str, list[str]] = {}
    for spec in specs:
        issues = primary_runner.training_completion_issues(
            spec,
            data[spec.dataset],
            formal_sha,
        )
        if issues:
            incomplete[spec.identifier] = issues
    if incomplete:
        first = list(incomplete.items())[:3]
        raise T2IntegrityError(
            "T2 fitting is gated until all 42 primary fits pass completion "
            f"audit; first incomplete rows: {first}"
        )
    return {
        "registered_primary_fit_count": len(specs),
        "all_primary_fits_complete": True,
        "formal_core_sha256": formal_sha,
    }


def static_audit(args: argparse.Namespace, require_primary: bool) -> dict[str, Any]:
    delivery = args.delivery_root.resolve(strict=True)
    experiments = delivery / "lgm_game_pytorch" / "experiments"
    matrix_path = experiments / "transactions_t2_heldout_matrix.json"
    matrix = validate_matrix(matrix_path)
    wrapper_path = experiments / "run_sues_heldout_fit.py"
    protocol_path = delivery / "TRANSACTIONS_EXTENSION_PROTOCOL.md"
    evidence_path = (
        delivery
        / "lgm_game_pytorch"
        / "evidence_cache"
        / "sues200_clip_image_evidence.npz"
    ).resolve(strict=True)
    meta_path = core.find_meta_path(evidence_path).resolve(strict=True)
    manifest_path = (
        delivery
        / "lgm_game_pytorch"
        / "manifests"
        / "sues200_official_train_ids.yaml"
    ).resolve(strict=True)
    if sha256_file(evidence_path) != EXPECTED_SUES_EVIDENCE_SHA256:
        raise T2IntegrityError("Frozen SUES evidence cache hash changed.")
    if sha256_file(meta_path) != EXPECTED_SUES_EVIDENCE_META_SHA256:
        raise T2IntegrityError("Frozen SUES evidence metadata hash changed.")
    if sha256_file(manifest_path) != EXPECTED_SUES_MANIFEST_SHA256:
        raise T2IntegrityError("Frozen SUES train-ID manifest hash changed.")
    validate_frozen_core()
    if Path(sys.executable).resolve(strict=True) != args.python.resolve(strict=True):
        raise T2IntegrityError("T2 runner must use the declared primary interpreter.")

    data_root = args.sues_root.resolve(strict=True)
    store = core.EvidenceStore.load([evidence_path])
    records = core.derive_all_records(store, data_root, "sues200")
    train_ids, manifest_info = core.parse_sues_manifest(manifest_path)
    catalog = catalog_training_files(records, train_ids)
    altitude_rows = {}
    for altitude in core.SUES_ALTITUDES:
        filtered = filter_heldout_records(records, altitude)
        membership = membership_payload(
            records,
            filtered,
            altitude,
            train_ids,
        )
        inventory = inventory_from_catalog(catalog, altitude)
        protocol = core.build_training_protocol(
            filtered,
            "sues200",
            0.0,
            1,
            train_ids,
        )
        gallery_count = sum(
            len(rows) for rows in protocol.train_gallery_by_label.values()
        )
        if len(protocol.train_queries) + gallery_count != inventory["file_count"]:
            raise T2IntegrityError(
                f"T2 {altitude}m catalog and protocol image counts differ."
            )
        if any(row.altitude == altitude for row in protocol.train_queries):
            raise T2IntegrityError(f"T2 {altitude}m leaked into fitting.")
        altitude_rows[altitude] = {
            "membership": membership,
            "training_image_inventory": inventory,
            "fit_identity_count": len(protocol.train_ids),
            "fit_query_image_count": len(protocol.train_queries),
            "fit_gallery_image_count": sum(
                len(rows) for rows in protocol.train_gallery_by_label.values()
            ),
            "heldout_altitude_fit_query_image_count": 0,
        }
    primary = (
        audit_primary_completion(
            delivery,
            args.university_root,
            args.sues_root,
        )
        if require_primary
        else {
            "registered_primary_fit_count": 42,
            "all_primary_fits_complete": False,
            "gate_status": "not_checked_in_static_design_audit",
        }
    )
    payload = {
        "schema_version": AUDIT_SCHEMA,
        "status": (
            "ready_for_training"
            if primary["all_primary_fits_complete"]
            else "static_design_verified_primary_gate_pending"
        ),
        "manuscript_result": False,
        "registered_t2_fit_count": len(matrix["runs"]),
        "matrix_path": str(matrix_path.resolve()),
        "matrix_sha256": sha256_file(matrix_path),
        "runner_path": str(Path(__file__).resolve()),
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "heldout_adapter_path": str(wrapper_path.resolve()),
        "heldout_adapter_sha256": sha256_file(wrapper_path),
        "formal_core_path": str(Path(core.__file__).resolve()),
        "formal_core_sha256": EXPECTED_CORE_SHA256,
        "protocol_path": str(protocol_path.resolve()),
        "protocol_sha256": sha256_file(protocol_path),
        "python": str(args.python.resolve()),
        "dataset_root": str(data_root),
        "evidence": {
            "path": str(evidence_path),
            "bytes": evidence_path.stat().st_size,
            "sha256": EXPECTED_SUES_EVIDENCE_SHA256,
            "meta_path": str(meta_path),
            "meta_bytes": meta_path.stat().st_size,
            "meta_sha256": EXPECTED_SUES_EVIDENCE_META_SHA256,
        },
        "sues_manifest": {
            **manifest_info,
            "path": str(manifest_path),
            "file_sha256": EXPECTED_SUES_MANIFEST_SHA256,
        },
        "catalog": {
            "official_train_file_count": len(catalog),
            "path_size_content_rows_sha256": canonical_sha256(
                [
                    [path, row["bytes"], row["sha256"]]
                    for path, row in sorted(catalog.items())
                ]
            ),
        },
        "heldout_altitudes": altitude_rows,
        "primary_gate": primary,
        "official_test_metric_access": False,
        "model_constructed": False,
        "optimizer_step_executed": False,
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
        raise T2IntegrityError(f"nvidia-smi process audit failed: {completed.stderr}")
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
        raise T2IntegrityError(
            f"Another Python GPU process is active; T2 must be serialized: {conflicts}"
        )


def fit_command(
    args: argparse.Namespace,
    row: dict[str, Any],
    output_dir: Path,
    resume: str = "none",
) -> list[str]:
    delivery = args.delivery_root.resolve()
    wrapper = (
        delivery
        / "lgm_game_pytorch"
        / "experiments"
        / "run_sues_heldout_fit.py"
    )
    evidence = (
        delivery
        / "lgm_game_pytorch"
        / "evidence_cache"
        / "sues200_clip_image_evidence.npz"
    )
    manifest = (
        delivery
        / "lgm_game_pytorch"
        / "manifests"
        / "sues200_official_train_ids.yaml"
    )
    return [
        str(args.python.resolve()),
        "-B",
        str(wrapper.resolve()),
        "--heldout-altitude",
        row["heldout_altitude_m"],
        "--",
        "train",
        "--dataset",
        "sues200",
        "--data-root",
        str(args.sues_root.resolve()),
        "--evidence",
        str(evidence.resolve()),
        "--sues-manifest",
        str(manifest.resolve()),
        "--output-dir",
        str(output_dir.resolve()),
        "--device",
        f"cuda:{args.device_index}",
        "--workers",
        "8",
        "--seed",
        str(row["seed"]),
        "--data-hash-mode",
        "content",
        "--amp",
        "--eval-batch-size",
        "128",
        "--eval-chunk-size",
        "128",
        "--variant",
        row["variant"],
        "--backbone",
        "resnet18",
        "--embed-dim",
        "512",
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
            raise T2IntegrityError("T2 ledger schema mismatch.")
        if ledger.get("frozen_inputs") != frozen:
            raise T2IntegrityError("T2 frozen ledger inputs changed.")
        return ledger
    ledger = {
        "schema_version": LEDGER_SCHEMA,
        "created_utc": utc_now(),
        "updated_utc": utc_now(),
        "status": "registered",
        "registered_run_count": len(matrix["runs"]),
        "frozen_inputs": frozen,
        "runs": {
            row["run_id"]: {
                "ordinal": row["ordinal"],
                "heldout_altitude_m": row["heldout_altitude_m"],
                "variant": row["variant"],
                "seed": row["seed"],
                "status": "pending",
                "events": [],
            }
            for row in matrix["runs"]
        },
        "invocations": [],
    }
    atomic_json(path, ledger)
    return ledger


def record_event(
    ledger_path: Path,
    ledger: dict[str, Any],
    run_id: str,
    event: dict[str, Any],
) -> None:
    ledger_row = ledger["runs"][run_id]
    ledger_row["events"].append(event)
    ledger_row.update({key: value for key, value in event.items() if key != "command"})
    ledger["updated_utc"] = utc_now()
    atomic_json(ledger_path, ledger)


def run_training(args: argparse.Namespace) -> dict[str, Any]:
    audit = static_audit(args, require_primary=True)
    validate_payload_hash(audit, "T2 static audit")
    delivery = args.delivery_root.resolve()
    matrix = validate_matrix(
        delivery
        / "lgm_game_pytorch"
        / "experiments"
        / "transactions_t2_heldout_matrix.json"
    )
    runs_root = (
        delivery / "lgm_game_pytorch" / "runs" / "transactions_t2_heldout"
    )
    ledger_path = runs_root / "transactions_t2_ledger.json"
    ledger = initialize_or_verify_ledger(ledger_path, audit, matrix)
    invocation = {
        "started_utc": utc_now(),
        "status": "running",
        "stage": "train",
    }
    ledger["invocations"].append(invocation)
    ledger["status"] = "training"
    atomic_json(ledger_path, ledger)
    try:
        for row in matrix["runs"]:
            run_id = row["run_id"]
            output_dir = runs_root / "fits" / Path(run_id)
            ledger_row = ledger["runs"][run_id]
            if ledger_row["status"] == "completed":
                manifest = validate_completed_fit(
                    output_dir,
                    sha256_file(output_dir / "heldout_adapter_config.json"),
                    row["heldout_altitude_m"],
                    row["variant"],
                    int(row["seed"]),
                )
                record_event(
                    ledger_path,
                    ledger,
                    run_id,
                    {
                        "status": "completed",
                        "event_type": "skipped_already_complete",
                        "updated_utc": utc_now(),
                        "fit_manifest_sha256": sha256_file(
                            output_dir / "heldout_fit_manifest.json"
                        ),
                        "checkpoint_sha256": manifest["last_checkpoint_sha256"],
                    },
                )
                continue
            if ledger_row["status"] in {"running", "failed"}:
                raise T2IntegrityError(
                    f"{run_id} is {ledger_row['status']!r}; diagnose and preserve "
                    "the attempt before an explicitly authorized continuation."
                )
            if (output_dir / "heldout_fit_manifest.json").exists():
                manifest = validate_completed_fit(
                    output_dir,
                    sha256_file(output_dir / "heldout_adapter_config.json"),
                    row["heldout_altitude_m"],
                    row["variant"],
                    int(row["seed"]),
                )
                record_event(
                    ledger_path,
                    ledger,
                    run_id,
                    {
                        "status": "completed",
                        "event_type": "recovered_from_complete_artifacts",
                        "updated_utc": utc_now(),
                        "fit_manifest_sha256": sha256_file(
                            output_dir / "heldout_fit_manifest.json"
                        ),
                        "checkpoint_sha256": manifest["last_checkpoint_sha256"],
                    },
                )
                continue
            assert_no_other_python_gpu_process()
            command = fit_command(args, row, output_dir, resume="none")
            log_dir = (
                runs_root
                / "process_logs"
                / f"heldout_{row['heldout_altitude_m']}m"
                / row["variant"]
                / f"seed_{row['seed']}"
            )
            log_dir.mkdir(parents=True, exist_ok=True)
            stdout_path = log_dir / "attempt_1_stdout.log"
            stderr_path = log_dir / "attempt_1_stderr.log"
            if stdout_path.exists() or stderr_path.exists():
                raise T2IntegrityError(f"Refusing to overwrite T2 logs for {run_id}.")
            record_event(
                ledger_path,
                ledger,
                run_id,
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
                    run_id,
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
                raise T2IntegrityError(
                    f"T2 fit failed for {run_id}; return code "
                    f"{completed.returncode}. No retry was attempted."
                )
            manifest = validate_completed_fit(
                output_dir,
                sha256_file(output_dir / "heldout_adapter_config.json"),
                row["heldout_altitude_m"],
                row["variant"],
                int(row["seed"]),
            )
            record_event(
                ledger_path,
                ledger,
                run_id,
                {
                    "status": "completed",
                    "attempt": 1,
                    "finished_utc": utc_now(),
                    "elapsed_seconds": elapsed,
                    "return_code": 0,
                    "stdout_sha256": sha256_file(stdout_path),
                    "stderr_sha256": sha256_file(stderr_path),
                    "fit_manifest_sha256": sha256_file(
                        output_dir / "heldout_fit_manifest.json"
                    ),
                    "checkpoint_sha256": manifest["last_checkpoint_sha256"],
                },
            )
        incomplete = [
            run_id
            for run_id, row in ledger["runs"].items()
            if row["status"] != "completed"
        ]
        if incomplete:
            raise T2IntegrityError(f"T2 fits remain incomplete: {incomplete}")
        invocation["status"] = "completed"
        invocation["finished_utc"] = utc_now()
        ledger["status"] = "all_fits_complete_official_evaluation_not_started"
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
    parser.add_argument("--stage", choices=("audit", "train"), default="audit")
    args = parser.parse_args()
    if args.device_index < 0:
        raise SystemExit("ERROR: --device-index must be non-negative.")
    try:
        payload = (
            static_audit(args, require_primary=False)
            if args.stage == "audit"
            else run_training(args)
        )
    except (T2IntegrityError, OSError, ValueError, RuntimeError) as error:
        raise SystemExit(f"ERROR: {error}") from error
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
