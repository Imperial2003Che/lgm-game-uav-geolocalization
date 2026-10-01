"""Narrow file/AST review. Does not import or execute any producer source."""
import ast
import difflib
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone

EX = Path(r"C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution")
PREP = EX / "external_efficiency_preparation"
OUT = EX / "b1_worker_body_delta_review_20260930_0930"
OLD = PREP / "newer_native_b1_worker_v1" / "reference_worker.py"
NEW = PREP / "newer_native_b1_worker_v2" / "reference_worker.py"
AUTHOR_DIFF = PREP / "newer_native_b1_lifecycle_v1" / "COMPLETE_WORKER_V1_TO_V2.patch"
SCOPE_DIR = EX / "b1_integration_scope_20260930_0912"
EXPECTED = {
    OLD: (17414, "eed9b25b1204edbcf5172ea2fb24e272b7ff39103f98448e554a3dae779b7f46"),
    NEW: (21756, "313da5932a3b5c9f77eeeceb810fc741642a390b9672ca0d0f5726c2aa8ef2d7"),
    AUTHOR_DIFF: (None, "26940e8ce9be1a6becd68afc0c059defd7e58cb7169a28aa407c39b1b2d51678"),
}
bindings = []
checks = []

def check(name, result, detail=None):
    item = {"name": name, "passed": bool(result)}
    if detail is not None:
        item["detail"] = detail
    checks.append(item)
    if not result:
        raise AssertionError(name)

def read_bound(path, limit=100000):
    before = path.stat()
    check("bounded-size:" + path.name, 0 < before.st_size <= limit)
    with path.open("rb") as handle:
        raw = handle.read(limit + 1)
    after = path.stat()
    check("stable-read:" + str(path), (before.st_size, before.st_mtime_ns) ==
          (after.st_size, after.st_mtime_ns) and len(raw) == before.st_size)
    value = {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    if path in EXPECTED:
        expected_size, expected_sha = EXPECTED[path]
        check("adopted-source-sha:" + str(path), value["sha256"] == expected_sha)
        if expected_size is not None:
            check("adopted-source-size:" + str(path), value["bytes"] == expected_size)
    bindings.append(value)
    return raw

def write_new(name, raw):
    path = OUT / name
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}

def write_json(name, value):
    return write_new(name, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))

def dump(node):
    return ast.dump(node, annotate_fields=True, include_attributes=False)

def section(raw, node):
    return b"".join(raw.splitlines(keepends=True)[node.lineno-1:node.end_lineno])

def first_action(node):
    body = node.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]
    return body[0]

def is_closed_call(action):
    value = action.value if isinstance(action, (ast.Assign, ast.Expr)) else None
    return (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
            and value.func.id == "_closed_execution_admission")

def assign(tree, name):
    return next(n for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))

old_raw = read_bound(OLD)
new_raw = read_bound(NEW)
author_diff_raw = read_bound(AUTHOR_DIFF)
self_raw = read_bound(Path(__file__))
scope_report_raw = read_bound(SCOPE_DIR / "INTEGRATION_SCOPE.json")
check("saved-scope-report-expected-sha", hashlib.sha256(scope_report_raw).hexdigest() ==
      "cfe0c2a2e8f28ef0fea84645654d6ab6c68b38d842025ac00258f8ff06993fb9")
scope_source_raw = read_bound(SCOPE_DIR / "seal_scope_analysis.py")
old_tree = ast.parse(old_raw.decode("utf-8-sig"), filename=str(OLD))
new_tree = ast.parse(new_raw.decode("utf-8-sig"), filename=str(NEW))
old_functions = {n.name: n for n in old_tree.body if isinstance(n, ast.FunctionDef)}
new_functions = {n.name: n for n in new_tree.body if isinstance(n, ast.FunctionDef)}
added = sorted(set(new_functions) - set(old_functions))
check("no-removed-functions", set(old_functions) <= set(new_functions))
check("exact-three-added-functions", added == ["_load_lifecycle_module", "_native_worker_main", "_require_ack_before_original_import"])

function_review = []
for name, old_fn in old_functions.items():
    new_fn = new_functions[name]
    old_section = section(old_raw, old_fn)
    new_section = section(new_raw, new_fn)
    if name not in {"_closed_execution_admission", "_execute_original_reference"}:
        check("unchanged-function-AST:" + name, dump(old_fn) == dump(new_fn))
        check("unchanged-function-bytes:" + name, old_section == new_section)
        outcome = "exact raw function bytes and AST unchanged"
    elif name == "_closed_execution_admission":
        check("closed-raise-remains-first", isinstance(first_action(new_fn), ast.Raise))
        check("closed-gate-only-message-version-delta", new_section.replace(b"B1 worker v2", b"B1 worker v1") == old_section)
        outcome = "only rejection message v1 to v2; unconditional first raise preserved"
    else:
        ack_calls = [n for n in new_fn.body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                     and isinstance(n.value.func, ast.Name) and n.value.func.id == "_require_ack_before_original_import"]
        check("exactly-one-added-body-ACK-call", len(ack_calls) == 1)
        ack_stmt = ack_calls[0]
        check("added-body-ACK-exact-arguments", dump(ack_stmt.value) == dump(ast.parse("_require_ack_before_original_import(request_record, handshake_record)").body[0].value))
        restored_body = [n for n in new_fn.body if n is not ack_stmt]
        check("original-entire-body-AST-preserved-after-one-insertion", [dump(n) for n in restored_body] == [dump(n) for n in old_fn.body])
        check("signature-only-adds-optional-handshake", [a.arg for a in new_fn.args.args] == [a.arg for a in old_fn.args.args] + ["handshake_record"]
              and len(new_fn.args.defaults) == len(old_fn.args.defaults) + 1
              and isinstance(new_fn.args.defaults[-1], ast.Constant) and new_fn.args.defaults[-1].value is None
              and new_fn.args.vararg is None and new_fn.args.kwarg is None)
        # Check the complete args AST after removing only the appended positional arg/default.
        restored_args = ast.arguments(posonlyargs=new_fn.args.posonlyargs, args=new_fn.args.args[:-1],
            vararg=new_fn.args.vararg, kwonlyargs=new_fn.args.kwonlyargs,
            kw_defaults=new_fn.args.kw_defaults, kwarg=new_fn.args.kwarg, defaults=new_fn.args.defaults[:-1])
        check("original-args-AST-exact-after-one-added-default", dump(restored_args) == dump(old_fn.args))
        new_lines = new_section.splitlines(keepends=True)
        old_lines = old_section.splitlines(keepends=True)
        new_lines[0] = old_lines[0]
        ack_line = ack_stmt.lineno - new_fn.lineno
        del new_lines[ack_line]
        check("original-entire-function-bytes-preserved-after-two-declared-lines", b"".join(new_lines) == old_section)
        load_stmt = next(n for n in new_fn.body if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)
                         and isinstance(n.value.func, ast.Name) and n.value.func.id == "_load_sources_after_admission")
        check("ACK-before-first-original-load", ack_stmt.lineno < load_stmt.lineno)
        check("original-FIRST-closed-action-preserved", is_closed_call(first_action(new_fn)))
        outcome = "optional handshake parameter and one ACK check inserted; every original body statement and remaining raw function byte unchanged"
    function_review.append({"name": name, "old_lines": [old_fn.lineno, old_fn.end_lineno],
        "new_lines": [new_fn.lineno, new_fn.end_lineno], "result": outcome})

constant_review = []
for name in ("PINS", "ARTIFACT_NAMES", "MISSING_ADMISSION"):
    a, b = assign(old_tree, name), assign(new_tree, name)
    check("constant-AST-identical:" + name, dump(a) == dump(b))
    check("constant-source-bytes-identical:" + name, section(old_raw, a) == section(new_raw, b))
    constant_review.append({"name": name, "old_lines": [a.lineno, a.end_lineno], "new_lines": [b.lineno, b.end_lineno],
                          "source": section(new_raw, b).decode("utf-8")})

def encode_calls(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "encode_seed"]

old_encode, new_encode = encode_calls(old_tree), encode_calls(new_tree)
check("unique-original-encode-seed-call", len(old_encode) == len(new_encode) == 1)
check("encode-call-AST-and-arguments-identical", dump(old_encode[0]) == dump(new_encode[0]))
check("encode-call-source-bytes-identical", section(old_raw, old_encode[0]) == section(new_raw, new_encode[0]))

closed_functions = ("_import_pinned", "_load_sources_after_admission", "_execute_original_reference",
                    "run_reference", "admit_reference", "_load_lifecycle_module",
                    "_require_ack_before_original_import", "_native_worker_main")
guard_review = []
for name in closed_functions:
    action = first_action(new_functions[name])
    check("FIRST-unconditional-closed-call:" + name, is_closed_call(action))
    guard_review.append({"function": name, "first_action_line": action.lineno,
                         "first_action_source": section(new_raw, action).decode("utf-8")})
main_guard = next(n for n in new_tree.body if isinstance(n, ast.If)
                  and dump(n.test) == dump(ast.parse('__name__ == "__main__"', mode="eval").body))
check("module-main-FIRST-raise", isinstance(main_guard.body[0], ast.Raise)
      and isinstance(main_guard.body[0].exc, ast.Call)
      and isinstance(main_guard.body[0].exc.func, ast.Name)
      and main_guard.body[0].exc.func.id == "ClosedExecutionGate")
check("module-main-extra-call-unreachable-after-raise", len(main_guard.body) == 2 and isinstance(main_guard.body[1], ast.Raise))
check("new-module-top-level-node-kinds-unchanged", [type(n).__name__ for n in old_tree.body] ==
      [type(n).__name__ for n in new_tree.body if not isinstance(n, ast.FunctionDef) or n.name not in added])
check("top-level-original-imports-identical", [dump(n) for n in old_tree.body if isinstance(n, (ast.Import, ast.ImportFrom))] ==
      [dump(n) for n in new_tree.body if isinstance(n, (ast.Import, ast.ImportFrom))])

main_fn = new_functions["_native_worker_main"]
handshake_stmt = next(n for n in main_fn.body if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)
                      and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == "_worker_pre_science_handshake")
body_stmt = next(n for n in main_fn.body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                 and isinstance(n.value.func, ast.Name) and n.value.func.id == "_execute_original_reference")
check("native-entry-handshake-before-original-body", handshake_stmt.lineno < body_stmt.lineno)
check("native-entry-explicit-handshake-argument", len(body_stmt.value.args) == 4
      and isinstance(body_stmt.value.args[-1], ast.Name) and body_stmt.value.args[-1].id == "handshake")
added_ack = new_functions["_require_ack_before_original_import"]
ack_source = section(new_raw, added_ack).decode("utf-8")
ack_checks = {
    "raw request SHA compared against handshake, ACK, ready": 'handshake_record["request_raw_sha256"] == ack["request_raw_sha256"] == ready["request_raw_sha256"]',
    "request binding descriptor compared": 'handshake_record["request"] == ack["request"] == ready["request"]',
    "ready own actual PID checked": 'ready["pid"] == os.getpid()',
    "ready self held identity compared to handshake and ACK": 'handshake_record["interpreter_identity"] == ack["interpreter_identity"]',
    "no pre-ACK original science import assertion checked": 'ready["original_source_or_science_imported"] is False',
    "six bootstrap source/image byte bindings read before original imports": '("launcher_image", "interpreter_image", "controller_image", "worker_source", "controller_source", "process_helper_source")',
    "actual worker source descriptor compared": 'bootstrap["worker_source"] == descriptor(__file__)',
    "directory identities checked": 'handshake_record["native_directory"] == spec["native_directory"]',
}
for name, marker in ack_checks.items():
    check("new-ACK-structural-edge:" + name, marker in ack_source)

delta = b"".join(difflib.diff_bytes(difflib.unified_diff,
    old_raw.splitlines(keepends=True), new_raw.splitlines(keepends=True),
    fromfile=str(OLD).encode("utf-8"), tofile=str(NEW).encode("utf-8"), n=3))
diff_binding = write_new("COMPLETE_INDEPENDENT_BYTE_DIFF.patch", delta)
source_binding = write_json("INPUT_BINDINGS.json", {"schema": "b1-worker-body-static-input-bindings.v1", "inputs": bindings})
report = {
    "schema": "b1-worker-body-delta-static-review.v1",
    "reviewed_utc": datetime.now(timezone.utc).isoformat(),
    "review_method": "Independent AI static reading plus this saved stdlib bounded-byte/AST checker; no human review or producer import/execution.",
    "scope": "Exact frozen worker-v1 to source-only worker-v2 delta only. No controller full validation, original authority re-audit, runtime/API/venv/fixture/science execution or evidence admission.",
    "result": "passed narrow source correspondence and first closed guards",
    "source_adopted": False,
    "execution_released": False,
    "native_worker_validated": False,
    "scientific_result_admitted": False,
    "controller_fully_validated": False,
    "checks": checks,
    "check_count": len(checks),
    "old_function_count": len(old_functions),
    "new_function_count": len(new_functions),
    "added_functions": added,
    "function_review": function_review,
    "constant_review": constant_review,
    "encode_seed": {"old_lines": [old_encode[0].lineno, old_encode[0].end_lineno],
                    "new_lines": [new_encode[0].lineno, new_encode[0].end_lineno],
                    "actual_source": section(new_raw, new_encode[0]).decode("utf-8"),
                    "claim": "Only original encode_seed call and exact arguments preserved; not invoked."},
    "first_closed_guards": guard_review,
    "new_handshake_edge": {"native_handshake_line": handshake_stmt.lineno,
        "body_invocation_line": body_stmt.lineno,
        "body_ACK_line": ack_stmt.lineno,
        "first_original_load_line": load_stmt.lineno,
        "added_ACK_function_lines": [added_ack.lineno, added_ack.end_lineno],
        "claim": "Dormant native entry performs lifecycle handshake before original body; body then rechecks bound ACK before _load_sources_after_admission. All these paths first unconditionally reject today."},
    "preserved_scientific_scope": [
        "All original complete-request bind/rebuild, original prepared seal validation, unique in-memory batch16 to batch1 derivation and stale original metadata handling are byte/AST unchanged.",
        "Pinned original contract/binder/aliases/loader bindings and original evaluator entry, DAC before/after scope, runtime/environment and frozen source guards remain unchanged.",
        "No loader replacement or numeric/math/protocol change. CAMP/DAC strict original evaluator behavior remains inherited, not newly executed or independently runtime validated here.",
        "Fresh native output topology, four exact original native artifacts, candidate-only consistency, return-intent unknown exits/streams, scientific false flags and partial failure preservation remain unchanged.",
        "Current-venv launcher/interpreter identities, external held exits and closed logs, issuer boot/resources/predecessor/release/locks, six workers, fresh full gallery/ranking/parity/timing/fullonlineCLIP still require separate actual completed execution and evidence adoption.",
    ],
    "limits": [
        "AST/byte chronology is dormant source evidence, not actual ACK or runtime handoff success.",
        "Lifecycle helper, controller, evidence-contract and bootstrap graph are the other independent reviewer's scope. This report does not validate their full protocol.",
        "PINS hashes are checked for unchanged literal values only; no re-read or rehash of the six original authority targets, checkpoint/cache/NPZ/image/big ZIP.",
        "Pure consistency helpers are not independent execution evidence. No original public B1/ranking gate was changed or opened.",
        "Inherited old v1 docstring/comment wording remains unchanged in the copied original body; the added v2 guards and CLI explicitly say v2.",
    ],
    "complete_byte_diff": diff_binding,
    "input_bindings": source_binding,
}
report_binding = write_json("DELTA_REVIEW.json", report)
readme = """# Narrow worker body source delta review

The independently checked old and new worker sources preserve all original function bodies except the declared optional handshake parameter and one bound-ACK check before the first original-source import. The original PINS, encode_seed arguments, derivation/science guards, DAC scope, native artifact set, consistency and return-intent logic are unchanged. Every science/entry path still first unconditionally rejects.

This is a byte/AST review of dormant source only. It neither adopts source nor validates the native Windows science environment, complete lifecycle/controller, actual ACK/exits/closed logs, predecessor/resource/release/shared-lock issuer, or scientific results. The report lists exact line edges and inherited limits. No producer modules, APIs, controls, fixtures or science were run; old files were not edited.
"""
readme_binding = write_new("SCOPE.md", readme.encode("utf-8"))
delivery = write_json("DELIVERY.json", {"schema": "b1-worker-body-delta-review-delivery.v1",
    "issued_utc": datetime.now(timezone.utc).isoformat(), "scope": report["scope"],
    "check_count": len(checks), "source_adopted": False, "execution_released": False,
    "inputs": bindings, "outputs": [diff_binding, source_binding, report_binding, readme_binding]})
print(json.dumps({"result": "passed narrow static delta only", "check_count": len(checks),
    "report": report_binding, "delivery": delivery}, ensure_ascii=False))
