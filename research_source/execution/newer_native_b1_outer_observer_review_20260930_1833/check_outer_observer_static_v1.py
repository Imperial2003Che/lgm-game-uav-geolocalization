"""One finite independent stdlib source/byte/JSON relation check, no candidate import.
Seven fixed new small inputs only; one new source AST. No author FIRST/None mirror
suite, candidate function calls, API/PowerShell/science/controls or old source hash.
"""
import ast
import hashlib
import json
import os
from pathlib import Path

HERE = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\external_efficiency_preparation\newer_native_b1_outer_observer_v1')
OUT = HERE.parent.parent / 'newer_native_b1_outer_observer_review_20260930_1833'
EXPECTED = {
    'outer_observer.py': (47752, '8dea1234eea9364480dcde0108b3263d38a2cbb6b842bcda775df085a0211aaa'),
    'README.md': (6803, 'f95b8b535896b6f220146c5d0f25ace67ce4b96661d1ec82670ac9f878060ffd'),
    'publish_source_metadata.py': (12052, '6b49a098a28db1379f0196fd40e64bbb281ddc4a1e35c8d9ab89c56b086400e0'),
    'SOURCE_MANIFEST.json': (3140, '33a9e89826828e9a53e706411c84c29dd5d3a2683870bbfb5ecd0920cf45c5a0'),
    'INTERFACE_CONTRACT.json': (4930, 'ea70d6097acec03f79949814e59dbdd4b54f3f0442a24165fdbd723f0c0b3d3c'),
    'AUTHOR_DELIVERY.json': (7808, 'e9eeca613fac5ea9226a164a2dca500441461abf10d285b6f76c91fafb8a0c4c'),
    'ACTUAL_AUTHOR_PUBLICATION_TOOL_RETURN.json': (2641, 'ed8604c6d7d8de691aa2b807fee9628594c7f78f015f2ef0aaa1814664e5332a'),
}
raws, bindings, checks = {}, {}, []

def check(label, condition):
    if not condition:
        raise ValueError(label)
    checks.append(label)

def parse_saved(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate metadata key')
            result[key] = value
        return result
    def reject(value):
        raise ValueError('Nonfinite metadata: ' + value)
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=reject)

for name, expected in EXPECTED.items():
    path = HERE / name
    before = path.stat()
    if not 0 < before.st_size <= 131072:
        raise ValueError('New small input exceeds bound')
    with path.open('rb') as stream:
        raw = stream.read(before.st_size + 1)
        after = os.fstat(stream.fileno())
    if len(raw) != before.st_size or (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise ValueError('Input changed during read')
    raws[name] = raw
    bindings[name] = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    check('fixed_new_bytes_' + name, (len(raw), bindings[name]['sha256']) == expected)

manifest, interface, author, receipt = [parse_saved(raws[name]) for name in ('SOURCE_MANIFEST.json', 'INTERFACE_CONTRACT.json', 'AUTHOR_DELIVERY.json', 'ACTUAL_AUTHOR_PUBLICATION_TOOL_RETURN.json')]
check('new_source_manifest_interface_author_exact_binding', manifest['new_source_bindings'] == [bindings[name] for name in ('outer_observer.py', 'README.md', 'publish_source_metadata.py')] and interface['selected_source'] == bindings['outer_observer.py'] and author['source_manifest'] == bindings['SOURCE_MANIFEST.json'] and author['interface'] == manifest['interface'] == bindings['INTERFACE_CONTRACT.json'] and author['source_bindings'][:3] == manifest['new_source_bindings'])
author_tool = receipt['actual_tool_result']['tool_return']
author_stdout = parse_saved(author_tool['output'].encode('utf-8'))
check('author_actual_publication_receipt_outputs', author_tool['chunk_id'] == 'b106a0' and author_tool['exit_code'] == 0 and all(author_stdout[key] == bindings[name] for key, name in [('source', 'outer_observer.py'), ('source_manifest', 'SOURCE_MANIFEST.json'), ('interface', 'INTERFACE_CONTRACT.json'), ('author_delivery', 'AUTHOR_DELIVERY.json')]))
check('metadata_source_only_no_operative_producers_or_runtime', interface['description_only_not_runtime_plan'] is True and interface['original_guardian_v3_supports_this_bootstrap_READY_ACK'] is False and interface['future_guardian_runtime_derivative_created_or_installed'] is False and interface['schemas_have_actual_immutable_producers_here'] is False and interface['operative_six_role_adjudication'] is None and interface['current_startup_release_or_request'] is None and manifest['execution_released'] is False and author['candidate_imported_or_called'] is False and receipt['external_held_actor_exit_proven'] is False)

source = raws['outer_observer.py'].decode('utf-8')
tree = ast.parse(source, filename=str(HERE / 'outer_observer.py'))
functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}

def segment(name):
    return ast.get_source_segment(source, functions[name])

order_ranges = {}
def source_order(name, tokens):
    text = segment(name)
    offsets = [text.index(token) for token in tokens]
    order_ranges[name] = [{'token': token, 'line': functions[name].lineno + text[:offset].count('\n')} for token, offset in zip(tokens, offsets)]
    return offsets == sorted(offsets)

check('observer_capture_double_confirm_before_ack_exit_close_seal', source_order('_run_observer', ['context.streams.extend', 'context.finite_unobserved_descendants = True', 'subprocess.Popen', 'context.popen_processes.append', "launcher = helper.HeldProcess", 'context.processes.append', 'launcher.confirm_twice', '_discover_control', '_capture_interpreter', "_fresh_physical_admission(context, 'before_guardian_ACK')", "ack_record = _new_record", 'actor.wait(60000)', 'saved_exit_relation', 'proc.wait(timeout=0)', 'stream.close()', 'helper.seal_closed_log', '_actual_finite_quiet(context)', 'context.finite_unobserved_descendants = False']))
check('actor_independent_live_parent_chain_before_runtime_import', source_order('_guardian_actor', ["control / 'guardian.ready.json'", "control / 'observer.ack.json'", "launcher = helper.HeldProcess", "observer = helper.HeldProcess", "outer_parent = helper.HeldProcess", 'observer.confirm_twice', 'launcher.confirm_twice', 'me.confirm_twice', "_fresh_physical_admission(actor_context, 'actor_before_guardian_runtime_import')", '_load_bound_module(REVIEWED_GUARDIAN_RUNTIME_SOURCE_PIN', "runtime.run_guardian(spec['guardian_plan'])"]))
observer, actor, capture = segment('_run_observer'), segment('_guardian_actor'), segment('_capture_interpreter')
check('raw_ready_ack_distinct_held_identity_relationships', "ready['spec_raw_sha256'] == digest(spec_raw)" in observer and "ready['request_raw_sha256'] == digest(request_raw)" in observer and "ready['guardian_runtime_imported'] is False" in observer and "ready['interpreter_identity']['pid'] != launcher.identity['pid']" in capture and "interpreter.identity == ready['interpreter_identity']" in capture and "ack['interpreter_identity'] == me.identity" in actor and "launcher.identity == ack['launcher_identity'] and observer.identity == ack['observer_identity']" in actor and "set(ack) ==" in actor)
check('canonical_raw_control_and_spec_rereads', "raw == canonical(value) + b'\\n'" in segment('_discover_control') and "_read_bound(record) == raw" in segment('_discover_control') and "_read_bound(spec_record) == spec_raw" in observer and "_read_bound(spec['request']) == request_raw" in actor and "_read_bound(spec['bootstrap']) == bootstrap_raw" in actor)
check('real_nonzero_terminal_not_science_or_own_exit', "'all_designated_actual_exits_zero':" in observer and "'actual_launcher_exit': launcher.exit_observation" in observer and "'actual_interpreter_exit': interpreter.exit_observation" in observer and "'separate_popen_exit_code': popen_code" in observer and "'guardian_return_intent_is_exit_proof': False" in observer and "'observer_self_exit_proven': False" in observer and "'actual_own_exit_unknown_here': True" in observer and "'actual_guardian_exit_requires_external_held_observer': True" in actor and "'measurement_admitted': True" not in source)
quiet = segment('_actual_finite_quiet')
check('finite_quiet_raw_dependencies_with_known_consumer_limits', "producer.collect_actual_outer_guardian_boundary" in quiet and "sample['finite_actual_spawn_window_adjudicated'] is True" in quiet and "sample['absence_is_exit_proof'] is False" in quiet and "_read_bound(sample['raw_full_inventory_stdout'])" in quiet and "_read_bound(sample['actual_query_exit'])" in quiet and "_read_bound(sample['actual_lineage_records'])" in quiet and ">= 15 * 10000000" in quiet and interface['finite_unknowns_from_current_quiet_candidate_can_be_cleared_by_setting_pin'] is False)
retention = segment('_retain_failure')
check('failure_retention_requires_exits_streams_quiet_before_reference_close', source_order('_retain_failure', ['actor.wait(1000)', "all(actor.exit_observation is not None", 'proc.wait(timeout=0)', 'stream.close()', '_actual_finite_quiet(context)', 'context.finite_unobserved_descendants = False', 'actor.close()']) and 'while True:' in retention and 'except BaseException as retention_error:' in retention and 'continue' in retention)

result = {
    'schema': 'newer-native-b1-outer-observer-independent-static-result.v1',
    'scope_complete': 'seven new small input bindings and bounded new source IPC/exit/closure relations only',
    'method': 'AI full text review plus one new stdlib source AST/byte/JSON check; no candidate functions invoked',
    'input_bindings': list(bindings.values()),
    'counts': {'new_small_files_read_and_hashed_once': 7, 'new_input_sha256_evaluations': 7, 'metadata_json_parse_calls': 4, 'saved_author_stdout_json_parse_calls': 1, 'new_source_ast_parse_calls': 1, 'local_relation_checks': len(checks), 'candidate_imports_or_calls': 0, 'author_publisher_executions_by_reviewer': 0, 'author_FIRST_None_mirror_suites': 0, 'old_source_hashes_or_suite_replays': 0, 'API_CIM_PowerShell_science_or_controls': 0, 'synthetic_candidate_fixtures': 0},
    'passed_static_relation_labels': checks, 'dormant_call_order_lines': order_ranges,
    'important_limits': ['AST/string order is not runtime or Windows/native topology validation.', 'Four None pins and closed FIRST entries were text read; author 17 FIRST/4 None enumeration was not replayed.', 'Current finite quiet consumer binds producer raw records but does not itself reconstruct full nullable row/time/history lineage.', 'Actor independently recollects fresh physical admission; it does not reread both admission descriptors carried in ACK.', 'Bounded/canonical bytes, caller identities and producer/source pins are associations, not immutable physical proof or scientific issuer authority.', 'Old guardian integration, operative six-role adjudication, immutable physical/finite quiet producers and actual runtime evidence remain absent.'],
    'closed_source_preparation_adoption_recommended': True, 'operative_integration_adopted': False,
    'runtime_or_scientific_admission': False, 'candidate_executed': False, 'actual_guardian_or_observer_exit_proven': False,
}
raw_result = (json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
with (OUT / 'CHECK_RESULT.json').open('xb') as stream:
    stream.write(raw_result)
    stream.flush()
    os.fsync(stream.fileno())
print(json.dumps({'result': {'path': str(OUT / 'CHECK_RESULT.json'), 'bytes': len(raw_result), 'sha256': hashlib.sha256(raw_result).hexdigest()}, 'counts': result['counts'], 'input_bindings': result['input_bindings'], 'passed_static_relation_labels': checks, 'dormant_call_order_lines': order_ranges, 'runtime_or_scientific_admission': False}, ensure_ascii=True, indent=2))

