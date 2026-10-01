"""One finite stdlib inspection of five new role-policy files only.

Never imports or executes the publisher, guardian, candidates or science.
No old source/quote suite, process/API/COM/CIM/lock/state/attempt/release action.
"""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(r"C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\b1_predecessor_role_policy_20260930_1730")
NAMES = ("ROLE_POLICY.json", "POLICY_PREPARATION_REPORT.json", "README.md", "prepare_role_policy.py", "ACTUAL_POLICY_PUBLICATION_TOOL_RETURN.json")
CAP = 64 * 1024
EXPECTED_ORDER = ["primary", "pipeline7", "extension4", "authors20", "independent9fit42eval", "extra_DAC3fit30eval"]


def main():
    raw, bindings, stable = {}, [], []
    for name in NAMES:
        path = HERE / name
        before = path.stat()
        if not 0 < before.st_size <= CAP:
            raise ValueError("Only fixed bounded new inputs allowed")
        with path.open("rb") as stream:
            body = stream.read(CAP + 1)
        after = path.stat()
        stable.append((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns) and len(body) == before.st_size)
        raw[name] = body
        bindings.append({"path": str(path), "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()})
    policy = json.loads(raw["ROLE_POLICY.json"])
    report = json.loads(raw["POLICY_PREPARATION_REPORT.json"])
    receipt = json.loads(raw["ACTUAL_POLICY_PUBLICATION_TOOL_RETURN.json"])
    published = json.loads(receipt["actual_return"]["output"])
    rows = policy["roles"]
    publisher = raw["prepare_role_policy.py"].decode("utf-8-sig")
    tree = ast.parse(publisher, filename=str(HERE / "prepare_role_policy.py"))
    checks = []

    def check(name, condition):
        checks.append({"name": name, "pass": bool(condition)})

    check("five_fixed_small_input_reads_stable", len(bindings) == 5 and all(stable))
    check("exact_known_new_policy_bytes_sha", bindings[0]["bytes"] == 18011 and bindings[0]["sha256"] == "a8f038875bd27e2bd393f6c30ae2cf198b5a0d78b690f9aace149ba576538609")
    check("actual_publication_three_output_bindings_match", published["outputs"] == bindings[:3] and receipt["actual_return"]["exit_code"] == 0 and receipt["receipt_created_after_execution"] is True)
    source_record = next(record for record in report["new_saved_inputs_bound"] if record["path"] == str(HERE / "prepare_role_policy.py"))
    check("publisher_actual_saved_source_binding_matches", source_record == bindings[3])
    check("six_roles_exact_order_and_ordinal", [row["role"] for row in rows] == EXPECTED_ORDER and [row["order"] for row in rows] == list(range(1, 7)) and report["roles_proposed"] == EXPECTED_ORDER)
    check("all_six_exit_and_adjudication_fields_remain_null", all(row["required_actual_exits_current"] is None and row["adjudication_current"] is None and row["execution_ready_current"] is False for row in rows))
    check("inactive_policy_cannot_be_live_guardian_adjudication", policy["schema"] == "b1-predecessor-role-exit-policy-proposal.v1" and policy["not_schema"] == "b1-predecessor-adjudication.v1" and all(policy[key] is False for key in ("policy_adopted", "execution_adjudication_adopted", "release_allowed", "B1_scientific_execution_authorized")))
    future = policy["future_root_adjudication_required_fields"]
    check("future_field_description_is_not_an_actual_adjudication", all(type(future[key]) is str for key in ("science_adopted", "scope_complete", "exit_requirement_adjudicated", "status", "original_spec", "original_plan", "source_authority", "required_actual_exits")) and future["absence_is_exit_proof"] is False)
    primary = rows[0]
    check("primary_unknown_preserved_without_present_empty_waiver", primary["historical_primary_independent_own_exit"] == "unknown" and primary["empty_exit_list_currently_published"] is False and policy["empty_list_policy"]["propagation_to_other_roles"] is False)
    check("pending_five_roles_have_no_empty_waiver", all(row["empty_exit_list_allowed_for_this_pending_role"] is False and row["scope_complete_current"] is False for row in rows[1:]))
    check("pipeline_first6_gap_requires_separate_disposition", any("first6 historical independent-exit gaps" in text and "no automatic primary exception" in text for text in rows[1]["missing"]))
    check("primary_future_new_actors_cannot_use_historical_exception", "cannot waive new primary/resume actors" in primary["future_empty_list_condition"] and "actual external controller/launcher/interpreter" in primary["actual_new_actor_coverage_required"])
    extra = rows[-1]
    check("extra_DAC_registration_unknown_remains_null", extra["original_status_path"] is None and extra["required_completed_status"] is None and any("Registration and exact state/spec/plan source mapping" in text for text in extra["missing"]))
    global_rule = "\n".join(policy["global_exit_record_generation"])
    check("actual_new_exit_rules_keep_applicable_contract_and_missing_provenance", "actual applicable original/recovery/execution contract" in global_rule and "relevant completed job contract" in global_rule and "no missing values or handle provenance may be filled" in global_rule and "preserve the old actual receipt and the missing-field limitation" in global_rule)
    constraints = "\n".join(policy["nonbypass_dependencies"])
    check("frozen_order_resource_native_and_result_limits_remain", all(text in constraints for text in ("Original five layers in order", "extraDAC3fit30eval", "originalT6 not replaced", "complete emptyGPU", ">=26GiB", "initial/pre-spawn/preACK", "byte locks", "actual native environment", "TTL/release", "negative results", "No completed science rerun")))
    input_records = report["new_saved_inputs_bound"]
    check("six_author_input_bindings_have_explicit_separate_uses", len(input_records) == report["input_binding_count"] == 6 and policy["research_authority"] == input_records[0] and policy["base_note"] == input_records[1] and input_records[-1] == bindings[3])
    imports = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module)
    check("publisher_imports_only_declared_stdlib", set(imports) == {"pathlib", "datetime", "hashlib", "json", "os"})
    write_names = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "outputs" for target in node.targets):
            for call in node.value.elts:
                target = call.args[0]
                if isinstance(call.func, ast.Name) and call.func.id == "write_new" and isinstance(target, ast.BinOp) and isinstance(target.left, ast.Name) and target.left.id == "HERE" and isinstance(target.right, ast.Constant):
                    write_names.append(target.right.value)
    check("publisher_top_level_outputs_are_only_three_inactive_files", write_names == list(NAMES[:3]))
    forbidden = {"exec", "eval", "compile", "__import__", "Popen", "WinAPI", "HeldProcess", "acquire", "CIM", "Dispatch"}
    called = {node.func.id if isinstance(node.func, ast.Name) else node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute))}
    check("publisher_has_no_candidate_import_spawn_or_probe_call", not (called & forbidden))
    quote_specs = [("guardian_v3.py", 132, 149), ("guardian_v3.py", 309, 326), ("contracts.py", 80, 106), ("run_dac_stage.py", 268, 282)]
    source_quote_specs = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "quote" and len(node.args) == 4 and isinstance(node.args[1], ast.Name) and isinstance(node.args[2], ast.Constant) and isinstance(node.args[3], ast.Constant):
            source_quote_specs.append((node.args[1].id, node.args[2].value, node.args[3].value))
    expected_variables = [("guardian_path", 132, 149), ("guardian_path", 309, 326), ("camp_path", 80, 106), ("dac_path", 268, 282)]
    saved_quotes = [(Path(q["path"]).name, q["start_line"], q["end_line"]) for q in report["new_necessary_source_quotes"]]
    check("four_saved_new_quote_specs_match_publisher_declarations_only", source_quote_specs == expected_variables and saved_quotes == quote_specs)
    result = {"schema": "b1-predecessor-role-policy-limited-static-check.v1", "inspection_kind": "Five new saved files only; JSON/byte and one publisher AST, no source module import", "static_checks_complete": True, "all_checks_pass": all(row["pass"] for row in checks), "check_count": len(checks), "checks": checks, "new_input_byte_bindings": bindings, "physical_input_read_and_sha_count": 5, "publisher_AST_parse_count": 1, "existing_source_quote_checks_replayed": False, "quote_matching_scope": "Saved report quote ranges/path names versus publisher AST declarations, not fresh original-source quote validation", "publisher_reexecuted": False, "source_policy_preparation_only": True, "operative_policy_adopted": False, "execution_adjudication_adopted": False, "actual_exit_record_generated": False, "release_or_scientific_permission": False}
    print(json.dumps(result, ensure_ascii=True, indent=2))
    raise SystemExit(0 if result["all_checks_pass"] else 1)


if __name__ == "__main__":
    main()
