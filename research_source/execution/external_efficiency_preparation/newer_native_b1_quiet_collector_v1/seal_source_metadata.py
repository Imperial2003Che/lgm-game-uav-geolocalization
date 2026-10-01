"""One-shot author source/metadata seal only; does not import the candidate."""
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

HERE = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\external_efficiency_preparation\newer_native_b1_quiet_collector_v1')
PREP = HERE.parent
EX = PREP.parent
MAX = 128 * 1024


def read_bound(path):
    stat = path.stat()
    if not 0 <= stat.st_size <= MAX:
        raise ValueError('Author source byte bound exceeded: ' + str(path))
    with path.open('rb') as stream:
        raw = stream.read(stat.st_size + 1)
        after = os.fstat(stream.fileno())
    if len(raw) != stat.st_size or (stat.st_size, stat.st_mtime_ns, stat.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise ValueError('Author bytes changed: ' + str(path))
    return raw, {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def write_new(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    for name in ('INTERFACE_CONTRACT.json', 'SOURCE_MANIFEST.json', 'AUTHOR_DELIVERY.json'):
        if (HERE / name).exists():
            raise ValueError('Any author artifact refuses seal replay: ' + name)
    selected_paths = [HERE / 'quiet_collector.py', HERE / 'README.md', Path(__file__).resolve(),
        PREP / 'newer_native_b1_guardian_v1' / 'guardian_v3.py',
        PREP / 'newer_native_b1_slot_bridge_v1' / 'guardian_exchange_v2.py',
        PREP / 'newer_native_b1_slot_bridge_v1' / 'INTERFACE_CONTRACT.json',
        PREP / 'newer_native_process_evidence_v2' / 'windows_process_evidence.py',
        EX / 'b1_slot_bridge_root_adoption_20260930_1647' / 'ROOT_CLOSED_SOURCE_ADOPTION.json']
    raws, bindings = {}, []
    for path in selected_paths:
        raw, binding = read_bound(path)
        raws[path.name if path.parent == HERE else str(path)] = raw
        bindings.append(binding)
    tree = ast.parse(raws['quiet_collector.py'].decode('utf-8'), filename=str(HERE / 'quiet_collector.py'))
    effect_names = ['_read_bound', '_new_record', '_fixed_helper', '_authority', '_query_full_inventory',
                    '_wait_ready', '_read_declared_actual_evidence', '_collect_snapshot', 'collect_snapshot',
                    'collect_boundary', 'main']
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    first_rejections = []
    for name in effect_names:
        node = functions[name]
        if not isinstance(node.body[0], ast.Raise):
            raise ValueError('Effect entry does not reject FIRST: ' + name)
        first_rejections.append({'function': name, 'first_statement': 'raise', 'lineno': node.lineno})
    pins = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.startswith('REVIEWED_') and target.id.endswith('_PIN'):
                    if not isinstance(node.value, ast.Constant) or node.value.value is not None:
                        raise ValueError('A quiet source pin is installed')
                    pins[target.id] = None
    if len(pins) != 3:
        raise ValueError('Exactly three explicit uninstalled quiet pins required')
    module_guard = tree.body[-1]
    if not isinstance(module_guard, ast.If) or not isinstance(module_guard.body[0], ast.Raise):
        raise ValueError('Module CLI does not reject first')
    query_node = next(node for node in tree.body if isinstance(node, ast.Assign) and any(
        isinstance(target, ast.Name) and target.id == 'CIM_QUERY_PS' for target in node.targets))
    query_text = ast.literal_eval(query_node.value)
    if not isinstance(query_text, str):
        raise ValueError('Fixed query source is not literal text')
    interface = {
        'schema': 'newer-native-b1-quiet-collector-source-interface-description.v1',
        'description_only_not_runtime_plan': True,
        'selected_collector_source': bindings[0],
        'guardian_source_integration_installed': False,
        'effect_entries_first_reject': effect_names,
        'current_reviewed_pins': pins,
        'public_interfaces': ['collect_snapshot(context)', 'collect_boundary(context)'],
        'guardian_required_result_keys': ['unknown_or_live_descendants', 'foreign_scientific_processes'],
        'current_query_scope': 'Complete unfiltered Win32_Process rows returned by actual query; bounded raw bytes and actual query exits required',
        'query_source_utf8_bytes': len(query_text.encode('utf-8')),
        'query_source_utf8_sha256': hashlib.sha256(query_text.encode('utf-8')).hexdigest(),
        'query_only_READY_ACK_is_scientific_release': False,
        'query_READY_schema': 'newer-native-b1-full-cim-read-ready-proposal.v1',
        'query_ACK_schema': 'newer-native-b1-full-cim-read-ack-proposal.v1',
        'independent_execution_root_schema': 'newer-native-b1-quiet-execution-authority-proposal.v1',
        'finite_slot_evidence_schema': 'newer-native-b1-finite-slot-quiet-evidence-proposal.v1',
        'schemas_are_new_unproduced_proposals': True,
        'original_guardian_consumes_new_schema': False,
        'sample_raw_stdout_maximum_bytes': 16 * 1024 * 1024,
        'sample_raw_stderr_maximum_bytes': 2 * 1024 * 1024,
        'full_inventory_maximum_rows': 65536,
        'control_log_maximum_bytes': 64 * 1024 * 1024,
        'two_full_query_intervals_minimum_seconds': 15,
        'current_parent_relation_is_complete_historical_parentage': False,
        'CIM_API_birth_comparison': 'exact integer ticks // 10; raw original ticks preserved',
        'nullable_fields': ['name', 'executable_path', 'command_line', 'creation_utc_ticks', 'creation_utc'],
        'unknown_actual_command_replaced_with_config_or_basename': False,
        'caller_arrays_callbacks_context_booleans_are_authority': False,
        'uncaptured_short_lived_child_exit_proven': False,
        'finite_actual_slot_history_resolution_supplied': False,
        'unbounded_arbitrary_past_process_proof_required': False,
        'guardian_unobserved_descendants_cleared': False,
        'shared_byte_lock_ownership_or_release_proven': False,
        'independent_runtime_query_topology_validated': False,
        'measurement_admitted': False,
        'execution_released': False,
        'remaining_interfaces': ['independently adopted finite actual-slot lineage method/role policy and real raw evidence producer',
            'source-integrated guardian-owned query actor/stream registration and retention on failures',
            'independently captured current live observer identities/commands and raw IPC authority bindings',
            'actual held query exits and closed raw streams after runtime execution',
            'external guardian actual exit observer and independent immutable scientific evidence gate']}
    interface_binding = write_new(HERE / 'INTERFACE_CONTRACT.json', interface)
    manifest = {
        'schema': 'newer-native-b1-quiet-collector-source-only-manifest.v1',
        'utc': datetime.now(timezone.utc).isoformat(),
        'new_source_bindings': bindings[:3],
        'necessary_original_small_source_bindings': bindings[3:],
        'interface': interface_binding,
        'execution_released': False, 'runnable_collector_validated': False,
        'guardian_or_old_sources_modified': False, 'scientific_measurement_admitted': False}
    manifest_binding = write_new(HERE / 'SOURCE_MANIFEST.json', manifest)
    report = {
        'schema': 'newer-native-b1-quiet-collector-author-source-method.v1',
        'utc': datetime.now(timezone.utc).isoformat(),
        'source_manifest': manifest_binding, 'source_bindings': bindings, 'interface': interface_binding,
        'syntax_AST_only': True, 'candidate_imported_or_executed': False,
        'local_AST_function_FIRST_inspection': first_rejections,
        'uninstalled_source_pins': pins, 'CLI_FIRST_rejected_by_AST': True,
        'pure_candidate_metadata_functions_not_invoked': True,
        'embedded_PowerShell_not_parsed_or_executed': True,
        'Popen_CIM_WinAPI_or_actual_clock_queries_by_candidate': False,
        'ordinary_sealer_timestamp_not_independent_process_exit': True,
        'no_synthetic_controls_tests_or_old_suite': True,
        'no_scientific_import_or_model_GPU_measurement': True,
        'no_shared_lock_state_release_intent_native_probe_COM_cleanup_changes': True,
        'old_scientific_or_control_suite_replayed': False,
        'weights_NPZ_cache_image_largeZIP_rehashed': False,
        'source_method': 'AI source construction and selected original source text inspection; bounded bytes/AST only by this sealer. Not human review or independent acceptance.',
        'original_source_read_scope': {'guardian': 'RuntimeContext/_quiet_snapshot, actual slot exit/stream closure, terminal boundary, retention, source constants and saved identity/exit relations',
            'helper': 'Ledger and actual HeldProcess/snapshot/confirm_twice/wait/close/seal_closed_log blocks',
            'slot_bridge': 'matching source-interface contract and related source searches; not a whole-program repeated review',
            'root': 'latest adoption scope and remaining quiet-interface limitation; no old checks rerun'},
        'filename_lookup_note': 'One rg lookup used nonexistent process_evidence.py filename; actual windows_process_evidence.py then read. Lookup was source research only, no candidate/API/scientific failure.',
        'specific_remaining_gap': 'Finite actual slot/query spawn-window uncaptured lineage/short-lived child exit stays unresolved; current inventory, captured held exits and nullable actual commands remain separate.',
        'source_constructed': True, 'independently_adopted': False, 'runtime_query_validated': False,
        'execution_released': False, 'B1_execution_admitted': False, 'scientific_measurement_admitted': False,
        'T6_complete': False, 'new_scientific_or_figure_result': False}
    report_binding = write_new(HERE / 'AUTHOR_DELIVERY.json', report)
    print(json.dumps({'source_manifest': manifest_binding, 'interface': interface_binding, 'author_delivery': report_binding,
                      'source': bindings[0], 'actual_work': 'ordinary source/metadata/AST sealing only; candidate and APIs not invoked'},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
