"""One-time stdlib-only byte derivation; no imports of the candidate or science."""
import ast
import difflib
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREP = HERE.parent
OLD = PREP / 'newer_native_b1_worker_v1' / 'reference_worker.py'
NEW = PREP / 'newer_native_b1_worker_v2' / 'reference_worker.py'
EXPECTED = 'eed9b25b1204edbcf5172ea2fb24e272b7ff39103f98448e554a3dae779b7f46'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def put(path, raw):
    with path.open('xb') as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())


def main():
    raw = OLD.read_bytes()
    if sha(raw) != EXPECTED or NEW.exists():
        raise RuntimeError('Exact prior source or fresh new target required')
    put(HERE / 'PRIOR_WORKER_V1.py.txt', raw)
    old = raw.decode('utf-8')
    newline = '\r\n' if '\r\n' in old else '\n'
    additions = '''

def _load_lifecycle_module():
    _closed_execution_admission()
    path = PREPARATION / "newer_native_b1_lifecycle_v1" / "native_lifecycle.py"
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
    require(ack["schema"] == "newer-native-b1-external-ack.v1" and
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
'''.replace('\n', newline)
    before = 'def _execute_original_reference(request_record, control_directory, native_directory):'
    after = 'def _execute_original_reference(request_record, control_directory, native_directory, handshake_record=None):'
    if old.count(before) != 1:
        raise RuntimeError('Unique prior scientific entry required')
    new = old.replace(before, after)
    marker = '    # Future admitted body is complete below. It is not an alternate entry path.' + newline
    if new.count(marker) != 1:
        raise RuntimeError('Unique exact import-boundary marker required')
    new = new.replace(marker, marker + '    _require_ack_before_original_import(request_record, handshake_record)' + newline)
    cli = 'if __name__ == "__main__":' + newline
    if new.count(cli) != 1:
        raise RuntimeError('Unique prior CLI guard required')
    new = new.replace(cli, additions + newline + cli)
    new = new.replace('Source-only B1 worker v1: no CLI execution or admission is available',
                      'Source-only native B1 worker v2: no CLI execution or admission is available')
    new = new.replace('B1 worker v1 has no execution admission issuer:', 'B1 worker v2 has no execution admission issuer:')
    new += '    raise SystemExit(_native_worker_main())' + newline
    put(NEW, new.encode('utf-8'))
    patch = ''.join(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                    fromfile=str(OLD), tofile=str(NEW))).encode('utf-8')
    put(HERE / 'COMPLETE_WORKER_V1_TO_V2.patch', patch)
    # Static packaging metadata only: no candidate import, API or test executed.
    before_tree, after_tree = ast.parse(old), ast.parse(new)
    a = next(n for n in before_tree.body if isinstance(n, ast.FunctionDef) and n.name == '_execute_original_reference')
    b = next(n for n in after_tree.body if isinstance(n, ast.FunctionDef) and n.name == '_execute_original_reference')
    old_body, new_body = old.splitlines()[a.lineno - 1:a.end_lineno], new.splitlines()[b.lineno - 1:b.end_lineno]
    ack_calls = [i for i, node in enumerate(b.body) if isinstance(node, ast.Expr) and
                 isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and
                 node.value.func.id == '_require_ack_before_original_import']
    if len(ack_calls) != 1:
        raise RuntimeError('Exactly one new ACK statement in scientific function required')
    restored_body = [node for i, node in enumerate(b.body) if i != ack_calls[0]]
    change = {'schema': 'newer-native-b1-worker-byte-derivation.v1',
              'prior': {'path': str(OLD), 'bytes': len(raw), 'sha256': sha(raw)},
              'new': {'path': str(NEW), 'bytes': len(new.encode('utf-8')), 'sha256': sha(new.encode('utf-8'))},
              'changes': ['signature adds handshake_record', 'one guarded ACK check before _load_sources_after_admission',
                          'three new guarded lifecycle/ACK/native worker functions', 'closed gate/CLI version wording only'],
              'scientific_function_after_new_ack_ast_matches_prior':
                  ast.dump(ast.Module(body=restored_body, type_ignores=[])) ==
                  ast.dump(ast.Module(body=a.body, type_ignores=[])),
              'scientific_function_prior_lines': [a.lineno, a.end_lineno],
              'scientific_function_new_lines': [b.lineno, b.end_lineno],
              'old_body_text': '\n'.join(old_body), 'new_body_text': '\n'.join(new_body),
              'source_derivation_only': True, 'candidate_or_scientific_imported': False,
              'native_execution_or_api_called': False, 'synthetic_controls_executed': False}
    put(HERE / 'WORKER_BODY_DERIVATION.json', json.dumps(change, ensure_ascii=False, indent=2).encode('utf-8') + b'\n')
    print(json.dumps({'new': change['new'], 'scientific_body_ast_preserved': change['scientific_function_after_new_ack_ast_matches_prior'],
                      'diff_sha256': sha(patch)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
