"""CreateNew author metadata only; no candidate imports, API calls or tests."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIMIT = 128 * 1024
SELECTED = ('native_lifecycle_bridge_v2.py', 'reference_worker_bridge_v2.py', 'guardian_exchange_v2.py')
EXPECTED = ('a7758c1724c14161718a7a7e436d08ca4bfe74f93ee34c782ae37efdcbfd1310',
            '82b7018c3cb8ffd8923f1e8a3fa7d04eddd2df9e62ab9ab0493fb1a01013f94c',
            '9c03423e679b91bedf855edf51dbcdd82dc4019dcb5b63056aac82994aa311c2')


def describe(path):
    path = Path(path)
    before = path.stat()
    if before.st_size > LIMIT:
        raise ValueError('Author source bound exceeded')
    raw = path.read_bytes()
    after = path.stat()
    if before.st_size != len(raw) or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError('Author file changed during read')
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def create(name, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    with (HERE / name).open('xb') as stream:
        stream.write(raw)
        stream.flush()
    return describe(HERE / name)


def main():
    selected = [describe(HERE / name) for name in SELECTED]
    if [r['sha256'] for r in selected] != list(EXPECTED):
        raise ValueError('Selected author source differs')
    inherited = [
        {'path': str(HERE.parent / 'newer_native_b1_lifecycle_v1' / 'native_lifecycle.py'), 'bytes': 33642,
         'sha256': '407eb2163451877e03578a91a3e496126d49be1141607855eb279d1641469d59'},
        {'path': str(HERE.parent / 'newer_native_b1_worker_v2' / 'reference_worker.py'), 'bytes': 21756,
         'sha256': '313da5932a3b5c9f77eeeceb810fc741642a390b9672ca0d0f5726c2aa8ef2d7'},
        {'path': str(HERE.parent / 'newer_native_b1_guardian_v1' / 'guardian_v3.py'), 'bytes': 43486,
         'sha256': 'f2b355c93d1d3660edecece06304403dd64b06873fcf878be1cffb9f5e9a52fc'},
        {'path': str(HERE.parent / 'newer_native_process_evidence_v2' / 'windows_process_evidence.py'), 'bytes': 16238,
         'sha256': 'cc090bec1429ab429b556200597acedfa13c33e878627155b0cc9f8098c9f5d2'}]
    interface = create('INTERFACE_CONTRACT.json', {
        'schema': 'newer-native-b1-slot-bridge-source-interface-description.v1',
        'description_only_not_runtime_plan': True, 'selected_sources': selected,
        'guardian_cli': ['--guardian-slot-spec', 'EXACT_SPEC_PATH', '--guardian-control-directory', 'EXACT_SLOT_CONTROL_PATH'],
        'schemas': {'spec': 'newer-native-b1-guardian-slot-candidate.v1',
                    'bootstrap': 'newer-native-b1-guardian-bootstrap-candidate.v1',
                    'static_exchange': 'newer-native-b1-slot-exchange-declaration-proposal.v1',
                    'preack_request': 'newer-native-b1-guardian-preack-request-proposal.v1',
                    'grant': 'newer-native-b1-guardian-preack-grant-proposal.v1',
                    'ACK': 'newer-native-b1-guardian-external-ack-proposal.v1'},
        'preack_request_fields': ['schema', 'spec', 'request', 'bootstrap', 'nonce', 'launcher', 'interpreter'],
        'grant_fields': ['schema', 'spec', 'request', 'bootstrap', 'nonce', 'release', 'authority_root',
                         'guardian_identity', 'controller_identity', 'launcher_identity', 'interpreter_identity',
                         'resource', 'actual_retained_lock_identity', 'execute_original_reference', 'measurement_admitted', 'scope'],
        'IPC_names': ['preack_request.json', 'preack_grant.json', 'slot_candidate.json'],
        'guardian_writes': ['preack_grant.json'], 'controller_writes': ['preack_request.json', 'slot_candidate.json'],
        'caller_context_supplies_execution_authority': False,
        'current_reviewed_execution_authority': None,
        'new_runtime_plan': None, 'six_completed_inputs': None,
        'actual_predecessor_adjudication': None, 'native_topology_validation': None,
        'quiet_collector': None, 'external_guardian_exit_observer': None,
        'resource_or_lock_proven_here': False, 'measurement_admitted': False,
        'old_eight_field_candidate_accepted_as_grant': False,
        'new_B1_TTL_max_seconds': 900, 'TTL_is_new_proposal_not_inherited_release': True,
        'raw_GPU_rule': 'Initial/before-spawn/preACK completely empty successful query; no PID exemptions',
        'normal_partial_rule': 'Preserve partial and retain guardian ownership; reference/stream close is not exit or lock release',
        'hard_interruption_rule': 'OS locks may release; a fresh residual-child incident audit remains mandatory',
        'runtime_or_scientific_execution_released': False})
    receipts = create('ACTUAL_SOURCE_AUTHOR_TOOL_RECEIPTS.json', {
        'schema': 'newer-native-b1-source-author-tool-receipts.v1',
        'scope': 'Exact tool result transcription for ordinary Python source text derivation only',
        'initial_derivation': {'tool_chunk': '4562cb', 'exit_code': 0, 'wall_time_seconds': 0.1832967,
                               'source': describe(HERE / 'derive_bridge_source.py')},
        'v2_derivation': {'tool_chunk': '8572a6', 'exit_code': 0, 'wall_time_seconds': 0.1790826,
                          'source': describe(HERE / 'derive_bridge_source_v2.py')},
        'candidate_module_imported': False, 'controls_tests_or_API_called': False,
        'native_or_scientific_venv_started': False, 'held_launcher_interpreter_exit_evidence': False,
        'scientific_result': False})
    names = ['README.md', 'guardian_exchange.py', 'native_lifecycle_bridge.py', 'reference_worker_bridge.py',
             *SELECTED, 'lifecycle_original_to_bridge.patch', 'worker_original_to_bridge.patch',
             'native_lifecycle_bridge_v1_to_v2.patch', 'reference_worker_bridge_v1_to_v2.patch',
             'guardian_exchange_v1_to_v2.patch', 'SOURCE_DERIVATION.json', 'SOURCE_DERIVATION_V2.json',
             'derive_bridge_source.py', 'derive_bridge_source_v2.py', 'seal_author_delivery.py',
             'INTERFACE_CONTRACT.json', 'ACTUAL_SOURCE_AUTHOR_TOOL_RECEIPTS.json']
    bindings = [describe(HERE / name) for name in names]
    manifest = create('SOURCE_MANIFEST.json', {
        'schema': 'newer-native-b1-slot-bridge-author-source-manifest.v1',
        'selected_sources': selected, 'bindings': bindings,
        'original_source_descriptors_inherited_not_rehashed_by_sealer': inherited,
        'old_source_bytes_mutated': False, 'independent_source_review_passed': False,
        'root_source_adopted': False, 'execution_released': False,
        'native_environment_validated': False, 'scientific_execution_or_measurement_admitted': False})
    delivery = create('AUTHOR_DELIVERY.json', {
        'schema': 'newer-native-b1-slot-bridge-author-delivery.v1',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'Closed author source candidate; independent and root review pending',
        'manifest': manifest, 'interface_description': interface, 'source_derivation_tool_receipts': receipts,
        'selected_sources': selected, 'all_new_source_bindings': bindings,
        'work_completed': 'Actual new dormant guardian IPC connection to the preserved one-slot lifecycle and minimally derived worker, with complete source deltas',
        'minimal_v2_scope': 'Only selected filename bindings, exact proposed release scope/source/predecessor and raw-resource associations, and immediate original-import grant/TTL reread',
        'missing_interfaces': ['Actual predecessor/root/release/resource/retained-lock authority',
                               'Reviewed guardian/bridge issuer integration; old guardian pins remain None',
                               'Prepared-native-venv complete-command/image/parent topology validation',
                               'Complete quiet-descendant/scientific-process collector',
                               'Actual external guardian-held exit and closed-stream observer',
                               'Integrated immutable new-schema execution and scientific artifact admission',
                               'Six actual completed inputs and fresh gallery/ranking/parity/full timing/online CLIP'],
        'source_import_or_execution': False, 'static_review_or_controls_passed': False,
        'syntax_compile_or_test_run': False, 'old_suite_replayed': False,
        'WinAPI_OS_probe_or_COM_called': False, 'runtime_attempt_or_intent_created': False,
        'release_or_grant_created': False, 'lock_or_scientific_state_modified': False,
        'root_source_adopted': False, 'execution_released': False,
        'native_environment_validated': False, 'independent_B1_execution_proven': False,
        'scientific_measurement_admitted': False, 'T6_complete': False,
        'handoff_or_user_notification_written': False})
    print(json.dumps({'manifest': manifest, 'delivery': delivery, 'bindings': len(bindings)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
