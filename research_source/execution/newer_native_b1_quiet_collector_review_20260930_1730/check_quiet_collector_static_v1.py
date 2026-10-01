"""One bounded independent AI source/metadata relation check; no candidate import.
Only the seven named new small inputs are read/hash once. Only quiet_collector.py
is parsed with ast. No functions from the candidate or author sealer are called,
no PowerShell parser/runtime/API is started, and no old suite/source is hashed.
This is static source preparation review, never admission or physical evidence.
"""
import ast
import hashlib
import json
import os
from pathlib import Path

SOURCE_DIR = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\external_efficiency_preparation\newer_native_b1_quiet_collector_v1')
REVIEW_DIR = SOURCE_DIR.parent.parent / 'newer_native_b1_quiet_collector_review_20260930_1730'
EXPECTED = {
    'quiet_collector.py': (38671, '852fc0e925ea54922e87ecfeaa82e97db776bd04e00497440f6083214999cbd9'),
    'INTERFACE_CONTRACT.json': (3513, '66fe2f9131bdfd93296488fe5cb82fe7ddd25527c40d9aedf43f5925541dbca4'),
    'SOURCE_MANIFEST.json': (3123, 'f0fa5366ae6576fa2834e5d4ec63ef1cb0f9e250fe540453ec2adc5a4a503605'),
    'AUTHOR_DELIVERY.json': (6649, '251d286ea7e08328a6801954f998144148d5d65508846964c47be4e8dcaa6726'),
    'README.md': (5314, 'd5ac6bf837e2008439348dc4ce42d6eef8136269e302a0c76b3e1cafbe852969'),
    'seal_source_metadata.py': (10767, 'b59726d31719548d5f7d085664f753b794fc099bed8336ad44593afb137fb288'),
    'ACTUAL_AUTHOR_SEAL_TOOL_RETURN.json': None,
}
raws, bindings, checks = {}, {}, []

def check(label, condition):
    if not condition:
        raise ValueError(label)
    checks.append(label)

def pairs(items):
    value = {}
    for key, item in items:
        if key in value:
            raise ValueError('Duplicate saved metadata key')
        value[key] = item
    return value

def parse_saved(raw):
    def reject(value):
        raise ValueError('Nonfinite saved metadata: ' + value)
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=reject)

def binding(path, raw):
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

for name, expected in EXPECTED.items():
    path = SOURCE_DIR / name
    before = path.stat()
    if not 0 < before.st_size <= 131072:
        raise ValueError('New small-file bound exceeded: ' + name)
    with path.open('rb') as stream:
        raw = stream.read(before.st_size + 1)
        after = os.fstat(stream.fileno())
    if len(raw) != before.st_size or (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise ValueError('New input changed during read: ' + name)
    raws[name], bindings[name] = raw, binding(path, raw)
    if expected is not None:
        check('fixed_new_bytes_' + name, (len(raw), bindings[name]['sha256']) == expected)

interface = parse_saved(raws['INTERFACE_CONTRACT.json'])
manifest = parse_saved(raws['SOURCE_MANIFEST.json'])
author = parse_saved(raws['AUTHOR_DELIVERY.json'])
receipt = parse_saved(raws['ACTUAL_AUTHOR_SEAL_TOOL_RETURN.json'])
check('manifest_three_new_source_bindings_exact', manifest['new_source_bindings'] == [bindings[name] for name in ('quiet_collector.py', 'README.md', 'seal_source_metadata.py')])
check('interface_manifest_author_bindings_exact', interface['selected_collector_source'] == bindings['quiet_collector.py'] and manifest['interface'] == bindings['INTERFACE_CONTRACT.json'] and author['interface'] == bindings['INTERFACE_CONTRACT.json'] and author['source_manifest'] == bindings['SOURCE_MANIFEST.json'] and author['source_bindings'][:3] == manifest['new_source_bindings'])
check('source_preparation_only_metadata', manifest['execution_released'] is False and manifest['runnable_collector_validated'] is False and manifest['guardian_or_old_sources_modified'] is False and interface['guardian_source_integration_installed'] is False and author['runtime_query_validated'] is False and author['execution_released'] is False and author['B1_execution_admitted'] is False and author['scientific_measurement_admitted'] is False and author['T6_complete'] is False)
actual_author = receipt['actual_return']
author_receipt_output = parse_saved(actual_author['output'].encode('utf-8'))
check('saved_author_actual_receipt_binds_outputs', actual_author['chunk_id'] == '3b0ea2' and actual_author['exit_code'] == 0 and all(author_receipt_output[key] == bindings[name] for key, name in [('source_manifest', 'SOURCE_MANIFEST.json'), ('interface', 'INTERFACE_CONTRACT.json'), ('author_delivery', 'AUTHOR_DELIVERY.json'), ('source', 'quiet_collector.py')]))
check('author_receipt_not_query_exit', receipt['candidate_and_embedded_query_not_executed'] is True and receipt['tool_exit_is_not_held_scientific_or_query_process_exit'] is True and 'seal_source_metadata.py' in receipt['submitted_args']['cmd'])

source = raws['quiet_collector.py'].decode('utf-8')
tree = ast.parse(source, filename=str(SOURCE_DIR / 'quiet_collector.py'))
functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
query_assignment = next(node for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'CIM_QUERY_PS' for target in node.targets))
query = ast.literal_eval(query_assignment.value)
query_binding = {'bytes': len(query.encode('utf-8')), 'sha256': hashlib.sha256(query.encode('utf-8')).hexdigest(), 'source_assignment_line': query_assignment.lineno}
check('embedded_fixed_query_descriptor', query_binding['bytes'] == interface['query_source_utf8_bytes'] and query_binding['sha256'] == interface['query_source_utf8_sha256'])
check('query_ready_ack_before_full_cim', query.index("'query_ready.json'") < query.index("'query_ack.json'") < query.index("throw 'Wrong read-only query ACK'") < query.index('Get-CimInstance -ClassName Win32_OperatingSystem') < query.index('Get-CimInstance -ClassName Win32_Process'))
check('query_raw_request_sha_nonce_pid_readonly_binding', all(token in query for token in ('$requestHasher.ComputeHash($requestRaw)', '$ack.nonce -cne $request.nonce', '$ack.request_sha256 -cne $requestSha', '$ack.actual_held_query_identity.pid -ne $PID', '$ack.execution_or_science_authority -ne $false', '[IO.FileMode]::CreateNew')))
check('query_full_null_rows_remain_current_only', all(token in query for token in ('@(Get-CimInstance -ClassName Win32_Process -ErrorAction Stop)', 'command_line = $_.CommandLine', 'executable_path = $_.ExecutablePath', 'if ($null -eq $_.CreationDate) { $null }', 'filtered = $false', 'row_count = [long]$rows.Count', 'not atomic enumeration or complete historical ancestry')) and '-Filter' not in query)

def segment(name):
    return ast.get_source_segment(source, functions[name])

query_body = segment('_query_full_inventory')
tokens = ['context.streams.extend', 'context.unobserved_descendants = True', 'subprocess.Popen', 'context.popen_processes.append', 'helper.HeldProcess', 'context.processes.append', 'held.confirm_twice', '_wait_ready', "directory / 'query_ack.json'", 'held.wait', 'held_exit_relation', 'proc.wait', 'stdout.close()', 'stderr.close()', 'helper.seal_closed_log', 'inventory_relation']
offsets = [query_body.index(token) for token in tokens]
check('dormant_query_capture_ack_exit_close_raw_order', offsets == sorted(offsets))
check('distinct_held_and_popen_exit0_no_synthesis', "type(actual_exit) is int and actual_exit == 0 and observed_exit['exit_code_unsigned_dword'] == 0" in query_body and "observed_exit['exit_utc_ticks'] >= relation['inventory']['sample_end_utc_ticks']" in query_body)
check('ready_exact_external_held_request_relation', all(token in query_body for token in ("set(ready) == {'schema', 'nonce', 'request_sha256', 'self_pid', 'execution_or_science_authority'}", "ready['request_sha256'] == request_record['sha256']", "ready['self_pid'] == held.identity['pid']", "ready['execution_or_science_authority'] is False")))
collect_body = functions['_collect_snapshot']
classify_call = next(node for node in ast.walk(collect_body) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'classify_candidate_inventory')
check('finite_actual_slot_unknown_hardcoded_true', any(keyword.arg == 'actual_slot_history_unresolved' and isinstance(keyword.value, ast.Constant) and keyword.value.value is True for keyword in classify_call.keywords))
classify_text = segment('classify_candidate_inventory')
check('current_parent_not_history_or_absence_exit', all(token in classify_text for token in ("'historical_parentage_proven': False", "'numeric_pid_alone_is_ancestor_proof': False", "'absence_is_exit_proof': False", "'full_current_inventory_is_historical_capture': False", "'finite_actual_slot_lineage_unresolved'", "'non_observer_actual_command_unknown'")) and 'while remaining:' in classify_text)
check('no_false_unobserved_assignment_or_release_true', not any(isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and node.value.value is False and any(isinstance(target, ast.Attribute) and target.attr == 'unobserved_descendants' for target in node.targets) for node in ast.walk(tree)) and "'release_authorized': True" not in source and "'measurement_admitted': True" not in source)
evidence_text = segment('_read_declared_actual_evidence')
check('new_evidence_producer_not_existing_guardian_claim', interface['schemas_are_new_unproduced_proposals'] is True and interface['original_guardian_consumes_new_schema'] is False and "value['producer_source'] == REVIEWED_FINITE_SLOT_LINEAGE_METHOD_PIN" in evidence_text and 'terminal[\'value\']' in evidence_text and 'closed[\'read_lock_denied_write_delete\'] is True' in evidence_text)
check('caller_relations_only_and_finite_scope_not_arbitrary_history', "'caller_candidate_relation_only': True" in classify_text and "'unbounded_arbitrary_history_required': False" in classify_text and interface['caller_arrays_callbacks_context_booleans_are_authority'] is False and interface['uncaptured_short_lived_child_exit_proven'] is False and interface['finite_actual_slot_history_resolution_supplied'] is False and interface['guardian_unobserved_descendants_cleared'] is False)

line_order = [{'token': token, 'line': functions['_query_full_inventory'].lineno + query_body[:offset].count('\n')} for token, offset in zip(tokens, offsets)]
result = {
    'schema': 'newer-native-b1-quiet-collector-independent-static-result.v1',
    'review_scope_completed': 'seven new bounded small inputs and quiet source IPC/current-parent/finite-gap relations only',
    'method': 'AI full-text source review plus one stdlib AST/byte/JSON source-only checker; no candidate functions called',
    'input_bindings': list(bindings.values()),
    'counts': {'new_small_input_files_read_and_hashed_once': len(bindings), 'new_input_sha256_evaluations': len(bindings), 'new_saved_metadata_documents_parsed': 4, 'saved_author_tool_stdout_documents_parsed': 1, 'embedded_query_sha256_evaluations': 1, 'candidate_ast_parse_calls': 1, 'local_relation_assertions': len(checks), 'candidate_imports_or_calls': 0, 'author_sealer_executions_by_reviewer': 0, 'old_source_hashes_or_old_suite_replays': 0, 'synthetic_candidate_fixture_calls': 0, 'embedded_powershell_executions_or_parser_calls': 0},
    'passed_static_relation_labels': checks,
    'embedded_query_binding': query_binding,
    'dormant_query_body_order': line_order,
    'important_limits': [
        'String/AST relation inspection does not validate Windows/PowerShell execution or raw IPC topology.',
        'FIRST raises and three None pins were fully text read; reviewer does not rerun author FIRST/None mirror suite.',
        'Query ACK consumer compares nonce/raw request SHA/PID/read-only marker; it does not independently compare birth/image/parent fields or exact JSON key sets/canonical encoding.',
        'Full current rows/current-parent reachability do not prove uncaptured short-lived historical lineage or exits.',
        'New authority/finite-slot evidence schemas and guardian integration are unproduced/uninstalled proposals.',
        'Stable raw bytes and reviewed root pins do not supply immutable physical provenance, writer-history proof, byte-lock release, or scientific admission.',
    ],
    'static_source_preparation_review_complete': True,
    'source_preparation_adoption_recommended': True,
    'operative_collector_adopted': False,
    'execution_adjudication_adopted': False,
    'candidate_or_query_executed': False,
    'runtime_topology_validated': False,
    'scientific_measurement_admitted': False,
    'T6_complete': False,
}
raw_result = (json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
with (REVIEW_DIR / 'CHECK_RESULT.json').open('xb') as stream:
    stream.write(raw_result)
    stream.flush()
    os.fsync(stream.fileno())
print(json.dumps({'result': binding(REVIEW_DIR / 'CHECK_RESULT.json', raw_result), 'counts': result['counts'], 'passed_static_relation_labels': checks, 'input_bindings': result['input_bindings'], 'dormant_query_body_order': line_order, 'execution_or_scientific_admission': False}, ensure_ascii=True, indent=2, allow_nan=False))

