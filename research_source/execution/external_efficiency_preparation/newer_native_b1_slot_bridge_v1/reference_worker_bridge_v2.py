"""Complete future original-encoder B1 body behind a permanently closed v1 gate.

Only stdlib is imported here. No caller token, dictionary, path or class grants
execution. The missing external lifecycle/admission controller must be reviewed
in a new version before either entry can reach original sources or science.
"""
from contextlib import nullcontext
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import traceback

HERE = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\external_efficiency_preparation\newer_native_b1_slot_bridge_v1')
PREPARATION = HERE.parent
EXECUTION = PREPARATION.parent
CONTRACT = PREPARATION / "newer_native_b1_contract_v1"
LOADER = PREPARATION / "newer_native_loader_v1"
PINS = {
    "contract_manifest": (CONTRACT / "SOURCE_MANIFEST.json", "35d7290f2f2f3189390bd45eddf2d6c4ac7378e313b14c9507de2536b997c1a4"),
    "contract_source": (CONTRACT / "b1_contract.py", "3947b52f48335adba748e797d79a89950006f28d073c362c8ded25258f0de486"),
    "root_adoption": (CONTRACT / "ROOT_SOURCE_ADOPTION.json", "dbe6e141cd6510daa7043273314bc9e155080d65f41c7367ed1e3b5a9e8dd3dc"),
    "loader_manifest": (LOADER / "SOURCE_MANIFEST.json", "1a5c34aac80187bda88eaffd24ba9756399d77b741d928047f40c5b3efe1d7c5"),
    "binder": (LOADER / "source_bindings.py", "2dcd4c6f1a38308a35f7a6426b4bfd164bef060af2c97dd0d0fecd381ae5c3f6"),
    "aliases": (LOADER / "path_aliases.py", "b15e12157a22c08f12c728187b74349b92157779c89a7886c6552becd0e1c3d6"),
}
ARTIFACT_NAMES = {
    "descriptors.npy", "image_content_sha256.jsonl",
    "strict_complete_final_load.json", "runtime_actual.json",
}
MISSING_ADMISSION = (
    "fresh single-method/seed worker and immutable controller request",
    "actual predecessor completion and distinct process exits",
    "current boot-bound plan/release and resource admission",
    "shared persistent first-byte GPU lock held through science",
    "external parent retaining actual launcher and interpreter handles",
    "parent acknowledgement before science and both real exits before log sealing",
)


class ClosedExecutionGate(RuntimeError):
    pass


def require(value, message):
    if not value:
        raise RuntimeError(message)


def _closed_execution_admission(*args, **kwargs):
    raise ClosedExecutionGate("B1 worker v2 has no execution admission issuer: " + "; ".join(MISSING_ADMISSION))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def parse(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, "Duplicate JSON key")
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(RuntimeError("Nonfinite JSON")))


def descriptor(path):
    _closed_execution_admission(path)
    path = Path(path).resolve(strict=True)
    before = path.stat()
    with path.open("rb") as stream:
        value = hashlib.file_digest(stream, "sha256").hexdigest()
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
            "Artifact changed during read")
    return {"path": str(path), "bytes": after.st_size, "sha256": value}


def read_control(record):
    _closed_execution_admission(record)
    require(type(record) is dict and set(record) == {"path", "bytes", "sha256"},
            "Exact immutable control descriptor required")
    require(type(record["bytes"]) is int and 0 <= record["bytes"] <= 8 * 1024 * 1024,
            "Bounded control JSON only")
    path = Path(record["path"])
    require(path.is_absolute() and path == path.resolve(strict=True), "Resolved absolute control path required")
    before = path.stat()
    require(before.st_size == record["bytes"] and before.st_size <= 8 * 1024 * 1024,
            "Actual control size differs or exceeds bound before any content read")
    with path.open("rb") as stream:
        raw = stream.read(record["bytes"] + 1)
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
            "Control changed during bounded read")
    require(len(raw) == record["bytes"] and digest(raw) == record["sha256"], "Control bytes differ")
    return raw, parse(raw)


def write_new_json(path, value):
    _closed_execution_admission(path, value)
    raw = canonical(value) + b"\n"
    with Path(path).open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return descriptor(path)


def verify_original_seal(prepared):
    require(type(prepared) is dict, "Original prepared mapping required")
    body = dict(prepared)
    seal = body.pop("payload_sha256", None)
    require(type(seal) is str and digest(canonical(body)) == seal, "Original prepared payload seal mismatch")
    return seal


def derivation_envelope(prepared, derived, declared):
    """Pure packaging; preserve the exact adopted derivative INCLUDING old seal."""
    original_seal = verify_original_seal(prepared)
    require(type(prepared["settings"]["batch_size"]) is int and prepared["settings"]["batch_size"] == 16,
            "Original batch16 required")
    require(type(derived["settings"]["batch_size"]) is int and derived["settings"]["batch_size"] == 1,
            "Derived batch1 required")
    reverse = copy.deepcopy(derived)
    reverse["settings"]["batch_size"] = 16
    require(canonical(reverse) == canonical(prepared), "Only /settings/batch_size may differ, including JSON value types")
    require(derived["payload_sha256"] == original_seal, "Historical original seal field must remain unchanged")
    require(declared["json_pointer"] == "/settings/batch_size" and
            type(declared["original"]) is int and declared["original"] == 16 and
            type(declared["derived"]) is int and declared["derived"] == 1 and
            declared["original_canonical_sha256"] == digest(canonical(prepared)) and
            declared["derived_canonical_sha256"] == digest(canonical(derived)) and
            declared["original_prepared_file_modified"] is False,
            "Adopted derivation record does not match exact objects")
    return {
        "schema": "newer-native-b1-derived-envelope.v1",
        "original_payload_seal_verified": original_seal,
        "original_canonical_sha256": digest(canonical(prepared)),
        "derived_canonical_sha256": digest(canonical(derived)),
        "derivation": copy.deepcopy(declared),
        "derived_prepared": copy.deepcopy(derived),
        "copied_payload_sha256_is_historical_metadata_only": True,
        "original_seal_not_valid_for_derived": True,
        "derived_passed_to_read_prepared_or_verify_seal": False,
        "new_scientific_protocol": False,
    }


def require_request_bytes(raw, rebuilt):
    require(raw == canonical(rebuilt) + b"\n",
            "Request file must byte-match the canonical request rebuilt from actual CompletedInputs")
    return digest(raw)


def candidate_envelope(request, artifacts):
    require(set(artifacts) == ARTIFACT_NAMES, "Exactly four original encoder artifacts required")
    return {
        "schema": "newer-native-b1-candidate.v1",
        "method": request["method"], "seed": request["seed"],
        "request_canonical_sha256": digest(canonical(request)),
        "source_recipe": copy.deepcopy(request["source_recipe"]),
        "derivation": copy.deepcopy(request["derivation"]),
        "artifacts": copy.deepcopy(artifacts),
        "independent_execution_proven": False,
        "measurement_admitted": False, "fresh_gallery_proven": False,
        "full_t6_complete": False, "manuscript_result": False,
    }


def _import_pinned(name, path):
    _closed_execution_admission(name, path)
    require(name not in sys.modules, "Fresh original namespace required: " + name)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    require(Path(module.__file__).resolve() == Path(path).resolve(), "Imported module path differs")
    return module


def _load_sources_after_admission():
    """Never used by stdlib checks; only reachable after the closed gate changes."""
    _closed_execution_admission()
    evidence = {}
    for name, (path, expected) in PINS.items():
        item = descriptor(path)
        require(item["sha256"] == expected, "Pinned predecessor source differs: " + name)
        evidence[name] = item
    require(not any(n.split(".")[0] in {"numpy", "torch", "torchvision", "cv2", "timm", "albumentations", "PIL"}
                    for n in sys.modules), "No scientific imports allowed before native admission")
    c = _import_pinned("_native_b1_original_contract", CONTRACT / "b1_contract.py")
    _import_pinned("path_aliases", LOADER / "path_aliases.py")
    b = _import_pinned("source_bindings", LOADER / "source_bindings.py")
    return c, b, evidence


def _execute_original_reference(request_record, control_directory, native_directory, handshake_record=None):
    # This first statement is unconditional rejection in v1, including private callers.
    admission = _closed_execution_admission(request_record, control_directory, native_directory)
    # Future admitted body is complete below. It is not an alternate entry path.
    _require_ack_before_original_import(request_record, handshake_record)
    c, b, sources = _load_sources_after_admission()
    raw, supplied = read_control(request_record)
    require(supplied["schema"] == "newer-native-b1-request.v1", "Unexpected B1 request schema")
    require(supplied["method"] in ("CAMP", "DAC") and type(supplied["seed"]) is int
            and supplied["seed"] in (1, 2, 3), "One registered method and seed per fresh worker")
    inputs = b.bind_completed(supplied["method"], supplied["binding"]["path"],
                              supplied["binding"]["sha256"], supplied["completion"]["path"],
                              supplied["completion"]["sha256"])
    rebuilt = c.request_from_completed(inputs, supplied["seed"])
    require_request_bytes(raw, rebuilt)
    require(inputs.prepared.artifact() == rebuilt["prepared"], "Actual prepared descriptor differs")
    prepared = inputs.prepared.value()
    verify_original_seal(prepared)
    package = b.open_original_package(inputs.method)
    # The original protocol independently verifies the ORIGINAL object only.
    package.protocol.verify_seal(prepared)
    derived, declared = c.derive_b1_prepared(prepared)
    require(declared == rebuilt["derivation"], "Rebuilt sole-difference derivation changed")
    envelope = derivation_envelope(prepared, derived, declared)
    require(Path(sys.executable).resolve() == Path(prepared["python"]).resolve(),
            "Actual registered native interpreter required")
    require(Path(sys.prefix).resolve() == Path(prepared["runtime"]["prefix"]).resolve(),
            "Actual registered native environment required")
    require(all(os.environ.get(k) == v for k, v in prepared["settings"]["thread_environment"].items()),
            "Native thread environment must be fixed by the external launcher")
    control = Path(control_directory).resolve()
    native = Path(native_directory).resolve()
    require(control.parent == HERE / "worker_runs" and control.name and not control.exists(),
            "Fresh exact worker control run directory required")
    require(native.parent == package.directory / "b1_reference_runs" and native.name == control.name
            and not native.exists(), "Fresh original-protocol native output root required")
    control.mkdir(parents=True, exist_ok=False)
    phase = "fresh_original_protocol_output"
    try:
        native.mkdir(parents=True, exist_ok=False)
        phase = "original_source_prepared_and_request_revalidation"
        write_new_json(control / "entry.json", {
            "schema": "newer-native-b1-worker-entry.v1",
            "request": request_record, "sources": sources, "admission": admission,
            "pid": os.getpid(), "python": sys.executable,
            "native_directory": str(native), "scientific_call_completed": False,
            "worker_identity_and_exit_are_not_proven_by_this_record": True,
        })
        write_new_json(control / "derived_prepared_envelope.json", envelope)
        scope = package.snapshots.snapshot_scope() if package.snapshots is not None else nullcontext()
        with scope:
            original = package.evaluator.read_prepared(inputs.prepared.path)
            require(original == prepared, "Original read_prepared differs from bound bytes")
            require(package.protocol.helpers().runtime_snapshot(sys.executable) == prepared["runtime"],
                    "Installed native runtime changed")
            b.no_scientific_modules()
            require(c.source_recipe(inputs.method) == rebuilt["source_recipe"], "Original encode_seed source/AST changed")
            inputs.unchanged()
            require(read_control(request_record)[0] == raw, "Request changed before encoding")
            if package.snapshots is not None:
                package.snapshots.unchanged_inputs()
            phase = "original_encode_seed_B1_query_subset"
            os.environ["CUDA_VISIBLE_DEVICES"] = "0"
            with (control / "encode.log").open("x", encoding="utf-8", newline="\n") as stream:
                def log(message):
                    stream.write(datetime.now(timezone.utc).isoformat() + " " + message + "\n")
                    stream.flush()
                    print(message, flush=True)
                # Exact original function; no AST editing, operation-side loader,
                # replacement transform, ranking helper, model copy or caller array.
                package.evaluator.encode_seed(
                    derived, inputs.seed_binding(rebuilt["seed"]),
                    rebuilt["selected_rows"], native, log)
                stream.flush()
                os.fsync(stream.fileno())
            phase = "closed_original_artifacts_and_candidate_consistency"
            require({p.name for p in native.iterdir()} == ARTIFACT_NAMES, "Unexpected native output set")
            artifacts = {name: descriptor(native / name) for name in sorted(ARTIFACT_NAMES)}
            candidate = candidate_envelope(rebuilt, artifacts)
            consistency = c.check_candidate_artifacts(rebuilt, candidate, native)
            require(consistency["candidate_artifact_consistency"] is True and
                    consistency["independent_execution_proven"] is False and
                    consistency["measurement_admitted"] is False,
                    "Candidate consistency must not imply execution admission")
            inputs.unchanged()
            require(read_control(request_record)[0] == raw, "Request changed after encoding")
            require(c.source_recipe(inputs.method) == rebuilt["source_recipe"], "Original source/AST changed")
            for name, item in sources.items():
                require(descriptor(item["path"]) == item, "Dependency source changed: " + name)
            if package.snapshots is not None:
                package.snapshots.unchanged_inputs()
        candidate_record = write_new_json(control / "candidate.json", candidate)
        consistency_record = write_new_json(control / "candidate_consistency.json", consistency)
        # This is return intent only. Parent must observe both retained handles
        # exit and close its stdout/stderr streams before sealing lifecycle evidence.
        return_record = write_new_json(control / "return_intent.json", {
            "request": request_record, "candidate": candidate_record,
            "consistency": consistency_record, "return_intent": 0,
            "actual_process_exit_not_yet_observed": True,
            "parent_stdout_stderr_not_sealed_by_worker": True,
            "independent_execution_proven": False, "measurement_admitted": False,
            "fresh_full_gallery_proven": False, "full_dataset_online_accuracy_proven": False,
            "full_t6_complete": False, "manuscript_result": False,
        })
        return return_record
    except BaseException as error:
        # Preserve partial native bytes. Do not hash a possibly open memmap as
        # closed evidence, delete outputs, terminate processes, or retry a seed.
        write_new_json(control / "failure.json", {
            "phase": phase, "type": type(error).__name__, "message": str(error),
            "traceback": traceback.format_exc(), "request": request_record,
            "native_directory": str(native),
            "partial_native_files": [{"name": p.name, "bytes": p.stat().st_size}
                                     for p in native.iterdir() if p.is_file()] if native.exists() else [],
            "partial_files_not_hashed_as_closed": True,
            "actual_process_exit_not_observed": True, "automatic_retry": False,
            "full_t6_complete": False, "manuscript_result": False,
        })
        raise


def run_reference(*args, **kwargs):
    _closed_execution_admission(*args, **kwargs)


def admit_reference(*args, **kwargs):
    _closed_execution_admission(*args, **kwargs)




def _load_lifecycle_module():
    _closed_execution_admission()
    path = HERE / "native_lifecycle_bridge_v2.py"
    spec = importlib.util.spec_from_file_location("_new_native_b1_lifecycle", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(Path(module.__file__).resolve() == path.resolve(strict=True), "Exact new lifecycle source required")
    return module


def _require_ack_before_original_import(request_record, handshake_record):
    _closed_execution_admission(request_record, handshake_record)
    lifecycle = _load_lifecycle_module()
    require(type(handshake_record) is dict, "Actual externally acknowledged native handshake required")
    spec_raw = lifecycle.read_bound(handshake_record["spec"])
    spec = lifecycle.parse(spec_raw)
    ack_raw = lifecycle.read_bound(handshake_record["ack"])
    ack = lifecycle.parse(ack_raw)
    ready_raw = lifecycle.read_bound(handshake_record["ready"])
    ready = lifecycle.parse(ready_raw)
    request_raw, request = read_control(request_record)
    require(request_record == spec["request"] == handshake_record["request"] == ack["request"] == ready["request"],
            "Original request must be the exact same independently captured native request")
    require(digest(request_raw) == handshake_record["request_raw_sha256"] == ack["request_raw_sha256"] == ready["request_raw_sha256"],
            "Original raw request bytes changed after native ACK")
    require(handshake_record["nonce"] == spec["nonce"] == ack["nonce"] == ready["nonce"] and
            ack["ready"] == handshake_record["ready"] and ack["spec"] == handshake_record["spec"] and
            ready["spec"] == handshake_record["spec"], "Native ACK/request/nonce/source association differs")
    require(handshake_record["spec_raw_sha256"] == digest(spec_raw) == ack["spec_raw_sha256"] == ready["spec_raw_sha256"],
            "Native specification raw bytes changed after ACK")
    require(ready["pid"] == os.getpid() and ready["identity"] == handshake_record["interpreter_identity"] == ack["interpreter_identity"],
            "Native ready/ACK interpreter differs from actual executing PID")
    require(ack["schema"] == "newer-native-b1-guardian-external-ack-proposal.v1" and
            ack["guardian_exchange"] == spec["guardian_exchange"] and
            ready["original_source_or_science_imported"] is False and
            ack["candidate_consistency_is_not_execution_authority"] is True,
            "Only pre-source external native ACK consistency is represented here")
    bootstrap_raw = lifecycle.read_bound(spec["bootstrap"])
    bootstrap = lifecycle.parse(bootstrap_raw)
    for name in ("launcher_image", "interpreter_image", "controller_image", "worker_source", "controller_source", "process_helper_source"):
        lifecycle.read_bound(bootstrap[name])
    require(ack["bootstrap"] == spec["bootstrap"] and bootstrap["worker_source"] == descriptor(__file__),
            "Actual new worker/source bytes changed after ACK")
    require(handshake_record["worker_control_directory"] == spec["worker_control_directory"] and
            handshake_record["native_directory"] == spec["native_directory"], "Native/body control path differs")
    exchange = lifecycle._load_guardian_exchange(spec)
    grant_raw = lifecycle.read_bound(ack["final_admission"])
    exchange._check_authority(handshake_record["spec"], spec, lifecycle.parse(grant_raw))
    require(lifecycle.read_bound(ack["final_admission"]) == grant_raw, "Guardian grant changed immediately before original imports")
    return {"ack": handshake_record["ack"], "raw_request_sha256": digest(request_raw),
            "candidate_consistency_only": True, "measurement_admitted": False}


def _native_worker_main(arguments=None):
    _closed_execution_admission(arguments)
    # -B only native bootstrapping, not the old isolated ordinary-Python fixture.
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-spec-binding", required=True)
    args = parser.parse_args(arguments)
    lifecycle = _load_lifecycle_module()
    handshake = lifecycle._worker_pre_science_handshake(args.native_spec_binding)
    # Ready/ACK directories belong to lifecycle, leaving both original body
    # roots absent for the unchanged CreateNew gates below.
    _execute_original_reference(handshake["request"], handshake["worker_control_directory"],
                                handshake["native_directory"], handshake)
    # Return intent only. Both actual exits remain the external parent's job.
    return 0

if __name__ == "__main__":
    raise ClosedExecutionGate("Source-only native B1 worker v2: no CLI execution or admission is available")
    raise SystemExit(_native_worker_main())
