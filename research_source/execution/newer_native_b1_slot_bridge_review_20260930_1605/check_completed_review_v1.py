"""One bounded offline AST/byte/diff inspection; never imports candidate modules.

No scientific source execution, OS process probe, COM/CIM, lock, native worker,
runtime attempt, release, legacy suite, or artifact admission occurs here.
Only the fixed small source/metadata/patch/old-partial files listed below are read.
This script prints JSON; its ordinary Python process exit is not scientific proof.
"""
import ast
import difflib
import hashlib
import json
from pathlib import Path

EX = Path(r"C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution")
PREP = EX / "external_efficiency_preparation"
BRIDGE = PREP / "newer_native_b1_slot_bridge_v1"
REVIEW = EX / "newer_native_b1_slot_bridge_review_20260930_1605"
GUARDIAN = PREP / "newer_native_b1_guardian_v1" / "guardian_v3.py"
BOUND = 256 * 1024
checks = []
bindings = []
raw_cache = {}


def check(name, condition, detail=None):
    checks.append({"name": name, "pass": bool(condition), "detail": detail})


def read_small(path, expected_bytes=None, expected_sha=None):
    path = Path(path)
    if path in raw_cache:
        return raw_cache[path]
    before = path.stat()
    if before.st_size > BOUND:
        raise ValueError("Fixed small input exceeds bound: " + str(path))
    with path.open("rb") as stream:
        raw = stream.read(BOUND + 1)
    after = path.stat()
    stable = (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
    actual = {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    bindings.append(actual)
    check("bounded_stable_read:" + path.name, stable and len(raw) == before.st_size and len(raw) <= BOUND)
    if expected_bytes is not None:
        check("exact_declared_bytes:" + path.name, len(raw) == expected_bytes)
    if expected_sha is not None:
        check("exact_declared_sha256:" + path.name, actual["sha256"] == expected_sha)
    raw_cache[path] = raw
    return raw


def body_after_docstring(node):
    body = node.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        return body[1:]
    return body


def function_map(tree):
    return {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}


def called_gate(statement, gate):
    value = statement.value if isinstance(statement, (ast.Expr, ast.Assign, ast.AnnAssign)) else None
    return isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == gate


def set_contract(function, variable):
    for node in ast.walk(function):
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Call) and isinstance(node.left.func, ast.Name) and node.left.func.id == "set" and len(node.left.args) == 1 and isinstance(node.left.args[0], ast.Name) and node.left.args[0].id == variable:
            for value in node.comparators:
                if isinstance(value, ast.Set) and all(isinstance(x, ast.Constant) and isinstance(x.value, str) for x in value.elts):
                    return {x.value for x in value.elts}, node.lineno
    raise ValueError("No literal exact key set: " + function.name)


def assigned_dict(function, variable):
    for node in ast.walk(function):
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == variable for target in node.targets) and isinstance(node.value, ast.Dict):
            return {key.value: value for key, value in zip(node.value.keys, node.value.values) if isinstance(key, ast.Constant)}, node.lineno
    raise ValueError("No assigned dict: " + function.name + "/" + variable)


def scope_equalities(function, variable):
    found = []
    for node in ast.walk(function):
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Subscript) and isinstance(node.left.value, ast.Name) and node.left.value.id == variable and isinstance(node.left.slice, ast.Constant) and node.left.slice.value == "scope":
            for op, rhs in zip(node.ops, node.comparators):
                if isinstance(op, ast.Eq) and isinstance(rhs, ast.Constant):
                    found.append({"line": node.lineno, "value": rhs.value})
    return found


def constant_assignment(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(x, ast.Name) and x.id == name for x in node.targets):
            return node.value, node.lineno
    raise ValueError("Missing fixed assignment: " + name)


def named_call_lines(function, name):
    return sorted(node.lineno for node in ast.walk(function) if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute)) and (node.func.id if isinstance(node.func, ast.Name) else node.func.attr) == name)


def main():
    manifest = json.loads(read_small(BRIDGE / "SOURCE_MANIFEST.json", 8528, "c88c720f6f0c14c64f02e4ea4b62bb13135c86a3d0a5723f9a7f674dc9adb99d"))
    delivery = json.loads(read_small(BRIDGE / "AUTHOR_DELIVERY.json", 9623, "e0ced0314fd4281e44e320673bd103985fce9951ca010911a119efb8fe676e71"))
    interface = json.loads(read_small(BRIDGE / "INTERFACE_CONTRACT.json", 3325, "e5a4644626390653c3453dad5c50b18bd2ffeca6b1031643d902bdcb95b4899b"))
    check("metadata_selected_source_equality", manifest["selected_sources"] == delivery["selected_sources"] == interface["selected_sources"])
    descriptors = {Path(record["path"]).name: record for record in manifest["bindings"]}
    selected = {}
    trees = {}
    ast_parsed = []
    for record in manifest["selected_sources"]:
        path = Path(record["path"])
        fixed_source = path.parent == BRIDGE and path.name in {"native_lifecycle_bridge_v2.py", "reference_worker_bridge_v2.py", "guardian_exchange_v2.py"}
        check("fixed_selected_source_root:" + path.name, fixed_source)
        if not fixed_source:
            raise ValueError("Manifest cannot widen the fixed source read scope")
        raw = read_small(path, record["bytes"], record["sha256"])
        selected[path.name] = raw.decode("utf-8")
        trees[path.name] = ast.parse(selected[path.name], filename=str(path))
        ast_parsed.append(str(path))
    guardian_text = read_small(GUARDIAN, 43486, "f2b355c93d1d3660edecece06304403dd64b06873fcf878be1cffb9f5e9a52fc").decode("utf-8")
    trees["guardian_v3.py"] = ast.parse(guardian_text, filename=str(GUARDIAN))
    ast_parsed.append(str(GUARDIAN))
    pure = {
        "native_lifecycle_bridge_v2.py": {"require", "canonical", "digest", "parse", "require_descriptor", "verify_original_prepared", "validate_spec_data", "worker_argv", "final_admission_relation", "_closed_execution_admission"},
        "reference_worker_bridge_v2.py": {"require", "canonical", "digest", "parse", "verify_original_seal", "derivation_envelope", "require_request_bytes", "candidate_envelope", "_closed_execution_admission"},
        "guardian_exchange_v2.py": {"require", "canonical", "digest", "parse", "descriptor", "identity", "timestamp", "exchange_relation", "grant_relation", "_closed"},
        "guardian_v3.py": {"require", "canonical", "digest", "parse", "integer", "descriptor", "utc", "saved_identity", "saved_exit_relation", "resource_relation", "release_relation", "plan_relation", "_closed"},
    }
    closed_entries = []
    for filename, tree in trees.items():
        gate = "_closed_execution_admission" if filename in {"native_lifecycle_bridge_v2.py", "reference_worker_bridge_v2.py"} else "_closed"
        functions = function_map(tree)
        gate_body = body_after_docstring(functions[gate])
        check("unconditional_gate_raise:" + filename, len(gate_body) == 1 and isinstance(gate_body[0], ast.Raise))
        for name, function in functions.items():
            if name not in pure[filename]:
                body = body_after_docstring(function)
                passed = bool(body) and called_gate(body[0], gate)
                check("FIRST_reject:" + filename + ":" + name, passed)
                closed_entries.append({"file": filename, "function": name, "line": function.lineno, "first_statement_line": body[0].lineno, "pass": passed})
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                for function in node.body:
                    if isinstance(function, ast.FunctionDef):
                        body = body_after_docstring(function)
                        passed = bool(body) and called_gate(body[0], gate)
                        check("FIRST_reject_method:" + filename + ":" + node.name + "." + function.name, passed)
                        closed_entries.append({"file": filename, "function": node.name + "." + function.name, "line": function.lineno, "first_statement_line": body[0].lineno, "pass": passed})
        main_guards = [node for node in tree.body if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__"]
        check("CLI_first_unconditional_raise:" + filename, len(main_guards) == 1 and isinstance(main_guards[0].body[0], ast.Raise))
    pin_rows = []
    for filename, names in (("guardian_exchange_v2.py", ["REVIEWED_EXECUTION_AUTHORITY_PIN"]), ("guardian_v3.py", ["REVIEWED_EXECUTION_ROOT_PIN", "REVIEWED_SLOT_BRIDGE_PIN", "REVIEWED_QUIET_COLLECTOR_PIN", "REVIEWED_OUTER_OBSERVER_PIN"])):
        for name in names:
            node, line = constant_assignment(trees[filename], name)
            passed = isinstance(node, ast.Constant) and node.value is None
            check("fixed_authority_None:" + filename + ":" + name, passed)
            pin_rows.append({"file": filename, "name": name, "line": line, "literal_none": passed})
    life = function_map(trees["native_lifecycle_bridge_v2.py"])
    worker = function_map(trees["reference_worker_bridge_v2.py"])
    exchange = function_map(trees["guardian_exchange_v2.py"])
    guardian = function_map(trees["guardian_v3.py"])
    request, request_line = assigned_dict(exchange["_controller_preack"], "request")
    request_consumer, request_consumer_line = set_contract(guardian["_preack_authority"], "ipc")
    grant, grant_line = assigned_dict(guardian["_preack_authority"], "grant")
    grant_consumer, grant_consumer_line = set_contract(exchange["grant_relation"], "value")
    final_consumer, final_consumer_line = set_contract(life["final_admission_relation"], "value")
    check("exact_seven_request_fields_match", set(request) == request_consumer == set(interface["preack_request_fields"]) and len(request) == 7)
    check("exact_sixteen_grant_fields_match", set(grant) == grant_consumer == final_consumer == set(interface["grant_fields"]) and len(grant) == 16)
    check("request_schema_matches_declared_interface", request["schema"].value == interface["schemas"]["preack_request"])
    check("grant_schema_matches_declared_interface", grant["schema"].value == interface["schemas"]["grant"])
    ack, ack_line = assigned_dict(life["_run_native_slot"], "ack")
    check("new_ACK_schema_matches_interface", ack["schema"].value == interface["schemas"]["ACK"])
    check("old_eight_field_final_candidate_is_not_grant", "actual_identities" not in grant_consumer and "release" in grant_consumer and "authority_root" in grant_consumer)
    release_scopes = scope_equalities(exchange["_check_authority"], "release")
    guardian_release_scopes = scope_equalities(guardian["release_relation"], "value")
    check("exact_proposed_release_scope_matches", release_scopes[0]["value"] == guardian_release_scopes[0]["value"] == "one_native_B1_slot_after_five_layers_and_extra_DAC")
    check("preACK_is_before_controller_ACK_write", named_call_lines(life["_run_native_slot"], "_final_admission_before_ack")[0] < ack_line)
    check("initial_authority_is_before_native_Popen", named_call_lines(life["_run_native_slot"], "_initial_controller_check")[0] < named_call_lines(life["_run_native_slot"], "Popen")[0])
    check("worker_ACK_hook_is_before_original_source_loader", named_call_lines(worker["_execute_original_reference"], "_require_ack_before_original_import")[0] < named_call_lines(worker["_execute_original_reference"], "_load_sources_after_admission")[0])
    check("immediate_original_import_hook_rechecks_authority", bool(named_call_lines(worker["_require_ack_before_original_import"], "_check_authority")))
    check("dual_held_waits_before_log_seal", len(named_call_lines(life["_run_native_slot"], "wait")) >= 3 and max(named_call_lines(life["_run_native_slot"], "wait")) < named_call_lines(life["_run_native_slot"], "seal_closed_log")[0])
    original_life = PREP / "newer_native_b1_lifecycle_v1" / "native_lifecycle.py"
    original_worker = PREP / "newer_native_b1_worker_v2" / "reference_worker.py"
    originals = {record["path"]: record for record in manifest["original_source_descriptors_inherited_not_rehashed_by_sealer"]}
    delta_pairs = [(original_life, BRIDGE / "native_lifecycle_bridge.py", "lifecycle_original_to_bridge.patch"), (original_worker, BRIDGE / "reference_worker_bridge.py", "worker_original_to_bridge.patch"), (BRIDGE / "native_lifecycle_bridge.py", BRIDGE / "native_lifecycle_bridge_v2.py", "native_lifecycle_bridge_v1_to_v2.patch"), (BRIDGE / "reference_worker_bridge.py", BRIDGE / "reference_worker_bridge_v2.py", "reference_worker_bridge_v1_to_v2.patch"), (BRIDGE / "guardian_exchange.py", BRIDGE / "guardian_exchange_v2.py", "guardian_exchange_v1_to_v2.patch")]
    delta_rows = []
    for old, new, patch_name in delta_pairs:
        old_descriptor = descriptors.get(old.name) if old.parent == BRIDGE else originals[str(old)]
        new_descriptor = descriptors[new.name]
        old_raw = read_small(old, old_descriptor["bytes"], old_descriptor["sha256"])
        new_raw = read_small(new, new_descriptor["bytes"], new_descriptor["sha256"])
        patch_descriptor = descriptors[patch_name]
        actual_patch = read_small(BRIDGE / patch_name, patch_descriptor["bytes"], patch_descriptor["sha256"])
        header = actual_patch.decode("utf-8").splitlines()
        expected_patch = "".join(difflib.unified_diff(old_raw.decode("utf-8").splitlines(True), new_raw.decode("utf-8").splitlines(True), fromfile=header[0][4:], tofile=header[1][4:])).encode("utf-8")
        exact = expected_patch == actual_patch
        check("complete_saved_delta_byte_match:" + patch_name, exact)
        delta_rows.append({"patch": patch_name, "old": str(old), "new": str(new), "exact_regenerated_delta": exact})
    original_worker_text = raw_cache[original_worker].decode("utf-8")
    original_worker_tree = ast.parse(original_worker_text, filename=str(original_worker))
    ast_parsed.append(str(original_worker))
    original_body = ast.get_source_segment(original_worker_text, function_map(original_worker_tree)["_execute_original_reference"])
    derived_body = ast.get_source_segment(selected["reference_worker_bridge_v2.py"], worker["_execute_original_reference"])
    check("original_encode_body_only_control_root_delta", original_body.replace('control.parent == HERE / "runs"', 'control.parent == HERE / "worker_runs"') == derived_body)
    for name, expected_bytes, expected_sha in [("PARTIAL_REVIEW.json", 4285, "1e119f10834297afa0c35dfe6f2d839f765d0e8df1e6d0103ec9c3d3fb328aa2"), ("PARTIAL_REVIEW.md", 3559, "726459529eac1834629b5f676b81d0d92d94633e011b8d3c3402615a46739d86"), ("CHECKER_EXECUTION_STATUS.json", 291, "bed82c6ade0bbefccb004a405453c2d29b65fb846af36dca354a0ac8957f52b1"), ("READ_TOOL_TRANSCRIPT.json", 164145, "757d2e0d9b11ea67e8ad207c3856c64363db21b0b918e87709a643970935241c")]:
        read_small(REVIEW / name, expected_bytes, expected_sha)
    protocol = {"request_producer_line": request_line, "request_consumer_line": request_consumer_line, "request_keys": sorted(request), "grant_producer_line": grant_line, "grant_consumer_line": grant_consumer_line, "final_relation_line": final_consumer_line, "grant_keys": sorted(grant), "grant_scope_producer_value": grant["scope"].value, "grant_scope_producer_value_line": grant["scope"].lineno, "grant_scope_equalities_in_bridge": scope_equalities(exchange["grant_relation"], "value"), "grant_scope_equalities_in_final_relation": scope_equalities(life["final_admission_relation"], "value"), "release_scope_checks": release_scopes, "ACK_producer_line": ack_line}
    report = {"schema": "native-b1-slot-bridge-bounded-static-inspection.v1", "inspection_kind": "Offline stdlib AST/byte/diff only; candidate source never imported/executed", "inspection_completed": True, "static_assertions_pass": all(row["pass"] for row in checks), "failed_checks": [row for row in checks if not row["pass"]], "checks": checks, "byte_bindings": bindings, "AST_parsed_source_paths": ast_parsed, "FIRST_closed_entries": closed_entries, "literal_None_pins": pin_rows, "protocol": protocol, "complete_delta_checks": delta_rows, "candidate_execution_or_import": False, "scientific_native_environment_validation": False, "resource_or_lock_or_actual_exit_observation": False, "old_suite_replayed": False, "root_source_adopted": False, "execution_released": False, "measurement_admitted": False, "T6_complete": False}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["static_assertions_pass"] else 1)


if __name__ == "__main__":
    main()
