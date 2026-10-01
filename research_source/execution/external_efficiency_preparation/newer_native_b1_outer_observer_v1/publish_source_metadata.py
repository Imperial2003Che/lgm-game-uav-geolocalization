"""One-shot stdlib source/metadata publication; never imports the candidate."""
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

HERE = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\external_efficiency_preparation\newer_native_b1_outer_observer_v1')
PREP, EX = HERE.parent, HERE.parent.parent
MAX = 128 * 1024


def read_small(path):
    before = path.stat()
    if not 0 <= before.st_size <= MAX:
        raise ValueError('Publication byte bound exceeded: ' + str(path))
    with path.open('rb') as stream:
        raw = stream.read(before.st_size + 1)
        after = os.fstat(stream.fileno())
    if len(raw) != before.st_size or (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise ValueError('Publication bytes changed: ' + str(path))
    return raw, {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def new_json(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    for name in ('INTERFACE_CONTRACT.json', 'SOURCE_MANIFEST.json', 'AUTHOR_DELIVERY.json'):
        if (HERE / name).exists():
            raise ValueError('Any publication artifact refuses replay: ' + name)
    paths = [HERE / 'outer_observer.py', HERE / 'README.md', Path(__file__).resolve(),
        PREP / 'newer_native_b1_guardian_v1' / 'guardian_v3.py',
        PREP / 'newer_native_process_evidence_v2' / 'windows_process_evidence.py',
        PREP / 'newer_native_b1_slot_bridge_v1' / 'INTERFACE_CONTRACT.json',
        EX / 'b1_preparation_delivery_20260930_1750' / 'ROOT_QUIET_SOURCE_PREPARATION_ADOPTION.json',
        EX / 'b1_preparation_delivery_20260930_1750' / 'ROOT_ROLE_POLICY_PREPARATION_ADOPTION.json']
    bindings, raw_source = [], None
    for path in paths:
        raw, binding = read_small(path)
        bindings.append(binding)
        if path == paths[0]:
            raw_source = raw
    tree = ast.parse(raw_source.decode('utf-8'), filename=str(paths[0]))
    effect_names = ['_read_bound', '_new_record', '_discover_control', '_load_bound_module', '_execution_authority', '_verify_six_predecessors',
        '_read_spec', '_fresh_physical_admission', '_capture_interpreter', '_actual_finite_quiet', '_remember',
        '_retain_failure', '_run_observer', '_guardian_actor', 'run_observer', 'run_guardian_actor', 'main']
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    first = []
    for name in effect_names:
        node = functions[name]
        if not isinstance(node.body[0], ast.Raise):
            raise ValueError('Effect entry does not reject FIRST: ' + name)
        first.append({'name': name, 'first_statement': 'raise', 'lineno': node.lineno})
    pins = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.startswith('REVIEWED_') and target.id.endswith('_PIN'):
                    if not isinstance(node.value, ast.Constant) or node.value.value is not None:
                        raise ValueError('Installed execution pin is forbidden')
                    pins[target.id] = None
    if len(pins) != 4 or not isinstance(tree.body[-1], ast.If) or not isinstance(tree.body[-1].body[0], ast.Raise):
        raise ValueError('Four None pins and FIRST module rejection required')
    interface = {
        'schema': 'newer-native-b1-outer-observer-source-interface-description.v1',
        'description_only_not_runtime_plan': True,
        'selected_source': bindings[0], 'source_modes': ['external observer', 'blocked guardian actor'],
        'source_cli_modes': ['--observer-spec PATH SHA256', '--guardian-actor --spec-binding PATH'],
        'all_modes_are_closed': True, 'effect_FIRST_functions': effect_names, 'current_reviewed_pins': pins,
        'original_guardian_v3_supports_this_bootstrap_READY_ACK': False,
        'future_guardian_runtime_derivative_created_or_installed': False,
        'original_guardian_or_primitive_called_or_bypassed': False,
        'schemas': {
            'operative_six_role_policy': 'newer-native-b1-operative-six-role-policy-proposal.v1',
            'execution_root': 'newer-native-b1-external-observer-execution-root-proposal.v1',
            'spec': 'newer-native-b1-external-guardian-observer-spec-proposal.v1',
            'bootstrap': 'newer-native-b1-external-guardian-bootstrap-proposal.v1',
            'request': 'newer-native-b1-external-guardian-start-request-proposal.v1',
            'release': 'newer-native-b1-external-guardian-observer-release-proposal.v1',
            'READY': 'newer-native-b1-external-guardian-ready-proposal.v1',
            'ACK': 'newer-native-b1-external-guardian-ack-proposal.v1',
            'physical_admission': 'newer-native-b1-external-observer-physical-admission-proposal.v1',
            'finite_quiet_boundary': 'newer-native-b1-external-guardian-finite-quiet-boundary-proposal.v1',
            'terminal_candidate': 'newer-native-b1-external-guardian-held-exit-candidate.v1'},
        'acyclic_byte_graph': ['common source/request/bootstrap/guardian-plan inputs',
            'early fixed execution root binds common descriptors/boot/nonce/directories',
            'later startup release binds root and common inputs; no spec descriptor',
            'final spec binds root and release', 'later READY and ACK bind raw final spec/request SHA'],
        'schemas_have_actual_immutable_producers_here': False,
        'future_physical_producer_interface': 'collect_actual_outer_guardian_admission(execution_root_descriptor, spec_descriptor, phase)',
        'future_finite_quiet_interface': 'collect_actual_outer_guardian_boundary(execution_root_descriptor, spec_descriptor)',
        'future_producer_source_interfaces_are_not_current_operational': True,
        'prospective_Popen': 'exact declared launcher executable, -B same-module actor source, fixed spec-binding path; shell=False/CREATE_NO_WINDOW',
        'distinct_external_held_guardian_actors': ['actual launcher', 'actual interpreter'],
        'live_double_confirmation_before_ACK': ['full command', 'same-file image', 'actual held birth', 'both current parent births'],
        'ACK_raw_bindings': ['exact canonical+LF keyset', 'spec raw SHA', 'request raw SHA', 'nonce',
            'READY descriptor', 'fixed execution root/source/release', 'independent actual observer/launcher/interpreter identities',
            'actual fixed-producer resource descriptors'],
        'exit_rule': 'same continuously held handles; adopted helper actual DWORD candidate first, then PID/birth/exit times; retained live image only',
        'Popen_is_separate_from_both_actual_held_exits': True,
        'closed_logs': ['guardian.stdout.log', 'guardian.stderr.log'],
        'log_shared_read_excludes_write_delete_only_at_saved_seal': True,
        'global_arbitrary_writer_history_exclusion': False,
        'two_actual_full_query_end_to_start_min_seconds': 15,
        'finite_unknowns_from_current_quiet_candidate_can_be_cleared_by_setting_pin': False,
        'uncaptured_historical_short_lived_exit_inferred': False,
        'shared_byte_lock_owned_or_released_by_outer_observer': False,
        'guardian_return_intent_is_actual_exit': False,
        'external_observer_self_exit_proven': False,
        'new_recursive_observer_layer_created': False,
        'source_runtime_topology_API_and_physical_resource_validated': False,
        'operative_six_role_adjudication': None,
        'current_startup_release_or_request': None,
        'scientific_measurement_or_T6_admitted': False,
        'execution_released': False}
    interface_record = new_json(HERE / 'INTERFACE_CONTRACT.json', interface)
    manifest_record = new_json(HERE / 'SOURCE_MANIFEST.json', {
        'schema': 'newer-native-b1-outer-observer-source-only-manifest.v1', 'utc': datetime.now(timezone.utc).isoformat(),
        'new_source_bindings': bindings[:3], 'necessary_original_small_bindings': bindings[3:], 'interface': interface_record,
        'execution_released': False, 'actual_guardian_or_observer_executed': False,
        'old_guardian_quiet_bridge_OR_scientific_sources_modified': False, 'B1_or_T6_scientific_admitted': False})
    author_record = new_json(HERE / 'AUTHOR_DELIVERY.json', {
        'schema': 'newer-native-b1-outer-observer-author-source-method.v1', 'utc': datetime.now(timezone.utc).isoformat(),
        'source_manifest': manifest_record, 'interface': interface_record, 'source_bindings': bindings,
        'local_AST_FIRST_inspection': first, 'uninstalled_reviewed_pins': pins, 'module_FIRST_reject_by_AST': True,
        'method': 'AI source construction and necessary original text reading; this one stdlib publisher bounds/hash eight small files and parses one new source AST. Not human review, API evidence or scientific/control tests.',
        'original_read_scope': ['HANDOFF latest17:22UTC and latest quiet/role preparation scope roots',
            'guardian_v3 release/plan/pins/return-intent and missing original READY/ACK CLI',
            'process helper Ledger/live HeldProcess/confirm_twice/wait/DWORD-first/signaled-exit/close/seal_closed_log blocks',
            'bridge native lifecycle READY/rawSHA ACK/dual external held exit blocks and source interface'],
        'candidate_imported_or_called': False, 'pure_candidate_relations_executed': False,
        'effect_modes_Popen_WinAPI_CIM_PS_native_science_or_controls_executed': False,
        'physical_resource_or_lock_state_release_intent_attempt_created': False,
        'guardian_runtime_derivative_or_producers_prepared_here': False,
        'old_passed_suites_replayed': False, 'old_large_weights_NPZ_cache_images_ZIP_read_or_hash': False,
        'source_method_exit0_is_not_actual_held_process_or_own_exit': True,
        'independent_review_or_root_adoption_performed_here': False,
        'execution_released': False, 'scientific_measurement_admitted': False, 'B1_or_T6_complete': False,
        'remaining_limitations': ['No operative six-role adjudication/issuer/execution root or actual resource/quiet producer exists.',
            'The original guardian_v3 and current quiet candidate remain closed and cannot be made operational by adding these source pins.',
            'The proposed aggregate resource/quiet schemas and live observer/raw IPC provenance require a new independently reviewed immutable producer integration.',
            'Current finite quiet consumer binds raw full inventory/held query exit and lineage records, but does not itself create/capture or fully reconstruct historical lineage.',
            'Native venv redirector/base-image/full-command topology and both external mode handshakes are dormant/unvalidated.',
            'Self return intent and self reference release cannot prove self exit; a real external parent is still needed without creating an infinite hierarchy.',
            'Evidence-handle retention is not guardian OS byte-lock ownership. Hard interruption/residual children remain a fresh incident.',
            'Pre-context setup can leave directory/self-only records; no prospective guardian Popen has yet been called there.',
            'This source does not perform original scientific artifact admission, fresh full gallery/ranking/parity/full timing/onlineCLIP or T6.']})
    print(json.dumps({'source': bindings[0], 'source_manifest': manifest_record, 'interface': interface_record,
        'author_delivery': author_record, 'actual_scope': 'one stdlib metadata/AST publication only; no candidate/APIs'},
        ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
