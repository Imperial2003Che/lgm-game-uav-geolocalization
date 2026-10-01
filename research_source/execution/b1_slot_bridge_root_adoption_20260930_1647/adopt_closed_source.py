"""New bounded root source adoption; never imports candidates or executes a suite."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os

EX = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution')
HERE = Path(__file__).resolve().parent
SOURCE = EX / 'external_efficiency_preparation' / 'newer_native_b1_slot_bridge_v1'
REVIEW = EX / 'newer_native_b1_slot_bridge_review_20260930_1605'
OBS = EX / 'heartbeat_observation_20260930_162819876'
CAP = 262144
CACHE = {}
BINDINGS = {}
CHECKS = []

def check(name, condition):
    if condition is not True:
        raise ValueError(name)
    CHECKS.append({'name': name, 'pass': True})

def read(path, declared=None):
    path = Path(path)
    resolved = path.resolve(strict=True)
    check('within_execution:' + path.name, resolved.is_relative_to(EX.resolve()))
    key = str(resolved).casefold()
    if key not in CACHE:
        before = path.stat()
        check('bounded_size:' + path.name, 0 <= before.st_size <= CAP)
        with path.open('rb') as stream:
            raw = stream.read(CAP + 1)
        after = path.stat()
        check('stable_saved_read:' + path.name,
              before.st_size == after.st_size == len(raw) and
              before.st_mtime_ns == after.st_mtime_ns and
              before.st_ino == after.st_ino)
        CACHE[key] = raw
        BINDINGS[key] = {'path': str(path), 'bytes': len(raw),
                         'sha256': hashlib.sha256(raw).hexdigest()}
    if declared is not None:
        check('descriptor_fields:' + path.name,
              set(declared) == {'path', 'bytes', 'sha256'})
        check('descriptor_path:' + path.name, Path(declared['path']) == path)
        current = BINDINGS[key]
        check('descriptor_bytes_sha:' + path.name,
              type(declared['bytes']) is int and declared['bytes'] == current['bytes'] and
              declared['sha256'] == current['sha256'])
    return CACHE[key]

def parsed(path, declared=None):
    return json.loads(read(path, declared))

def descriptor(path):
    read(path)
    return BINDINGS[str(Path(path).resolve()).casefold()]

def write_new(name, payload):
    path = HERE / name
    raw = (json.dumps(payload, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    check('bounded_new_report:' + name, len(raw) <= CAP)
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

manifest = parsed(SOURCE / 'SOURCE_MANIFEST.json', {
    'path': str(SOURCE / 'SOURCE_MANIFEST.json'), 'bytes': 8528,
    'sha256': 'c88c720f6f0c14c64f02e4ea4b62bb13135c86a3d0a5723f9a7f674dc9adb99d'})
author = parsed(SOURCE / 'AUTHOR_DELIVERY.json', {
    'path': str(SOURCE / 'AUTHOR_DELIVERY.json'), 'bytes': 9623,
    'sha256': 'e0ced0314fd4281e44e320673bd103985fce9951ca010911a119efb8fe676e71'})
check('nineteen_new_manifest_inputs', len(manifest['bindings']) == 19)
check('author_manifest_input_agreement', author['all_new_source_bindings'] == manifest['bindings'])
check('selected_source_agreement', author['selected_sources'] == manifest['selected_sources'])
check('manifest_author_byte_binding', author['manifest'] == descriptor(SOURCE / 'SOURCE_MANIFEST.json'))
for binding in manifest['bindings']:
    path = Path(binding['path'])
    check('fixed_candidate_input_directory:' + path.name, path.parent == SOURCE)
    read(path, binding)
check('original_author_execution_false', all(author[key] is False for key in (
    'source_import_or_execution', 'syntax_compile_or_test_run', 'old_suite_replayed',
    'WinAPI_OS_probe_or_COM_called', 'runtime_attempt_or_intent_created',
    'release_or_grant_created', 'lock_or_scientific_state_modified',
    'execution_released', 'native_environment_validated',
    'independent_B1_execution_proven', 'scientific_measurement_admitted', 'T6_complete')))

completed = parsed(REVIEW / 'COMPLETED_REVIEW.json')
read(REVIEW / 'COMPLETED_REVIEW.md')
result = parsed(REVIEW / 'COMPLETED_STATIC_CHECK_RESULT_V1.json')
actual = parsed(REVIEW / 'COMPLETED_STATIC_CHECK_ACTUAL_TOOL_RETURN_V1.json')
check('independent_source_scope_pass_only',
      completed['source_static_review_completed'] is True and
      completed['source_static_review_passed'] is True and
      completed['root_source_adopted'] is False and
      completed['SCI_release_allowed'] is False)
check('saved_actual_checker_return',
      actual['actual_tools_exec_command_return']['chunk_id'] == '7f1cdb' and
      actual['actual_tools_exec_command_return']['exit_code'] == 0 and
      actual['actual_tools_exec_command_return']['wall_time_seconds'] == 0.2146681)
check('saved_result_matches_actual_stdout',
      json.loads(actual['actual_tools_exec_command_return']['output']) == result)
check('independent_local_assertions_only',
      result['inspection_completed'] is True and result['static_assertions_pass'] is True and
      result['failed_checks'] == [] and len(result['checks']) == 162 and
      all(row['pass'] is True for row in result['checks']))
check('saved_closed_entry_and_pin_counts',
      len(result['FIRST_closed_entries']) == 64 and
      all(row['pass'] is True for row in result['FIRST_closed_entries']) and
      len(result['literal_None_pins']) == 5 and
      all(row['literal_none'] is True for row in result['literal_None_pins']) and
      len(result['complete_delta_checks']) == 5 and
      all(row['exact_regenerated_delta'] is True for row in result['complete_delta_checks']))
check('no_candidate_scientific_execution_in_static_result',
      all(result[key] is False for key in ('candidate_execution_or_import',
          'scientific_native_environment_validation', 'resource_or_lock_or_actual_exit_observation',
          'old_suite_replayed', 'root_source_adopted', 'execution_released',
          'measurement_admitted', 'T6_complete')))
check('scope_and_serialization_limits_preserved',
      completed['grant_scope_decision']['must_fix_for_current_source_interface'] is False and
      completed['grant_scope_decision']['consumer_scope_value_or_type_compared'] is False and
      completed['grant_serialization_limits']['consumer_explicit_canonical_equality'] is False)
check('normalized_index_count_only', len(completed['normalized_byte_bindings']) == 21)
allowed_other = {
    EX / 'external_efficiency_preparation' / 'newer_native_b1_lifecycle_v1' / 'native_lifecycle.py',
    EX / 'external_efficiency_preparation' / 'newer_native_b1_worker_v2' / 'reference_worker.py',
    EX / 'external_efficiency_preparation' / 'newer_native_b1_guardian_v1' / 'guardian_v3.py',
    REVIEW / 'PARTIAL_REVIEW.json', REVIEW / 'PARTIAL_REVIEW.md',
    REVIEW / 'CHECKER_EXECUTION_STATUS.json', REVIEW / 'READ_TOOL_TRANSCRIPT.json',
}
for indexed, displayed in zip(completed['normalized_byte_bindings'], result['byte_bindings']):
    path = Path(indexed['path'])
    check('allowlisted_index:' + path.name, path.parent == SOURCE or path in allowed_other)
    check('separate_path_index_matches_actual_ascii_descriptor:' + path.name,
          Path(displayed['path']).name == path.name and
          indexed['bytes'] == displayed['bytes'] and indexed['sha256'] == displayed['sha256'])
    read(path, {key: indexed[key] for key in ('path', 'bytes', 'sha256')})
# The checker descriptor has a provenance field; consume only the three byte fields.
read(REVIEW / 'check_completed_review_v1.py', {
    key: completed['static_tool']['checker_source'][key] for key in ('path', 'bytes', 'sha256')})

observation = parsed(OBS / 'ROOT_OBSERVATION_SEAL.json', {
    'path': str(OBS / 'ROOT_OBSERVATION_SEAL.json'), 'bytes': 15871,
    'sha256': '9dc9c7145421d2afea00198f8cd41f5832cfaffccb637b8e8e436ab067d31a25'})
read(OBS / 'OBSERVATION_WRAPPER_INCLUDED.json', {
    'path': str(OBS / 'OBSERVATION_WRAPPER_INCLUDED.json'), 'bytes': 16907,
    'sha256': '7caf167349e826245ac708e9338c0b39e5cedbbc96ed59cb8277a5ada9425947'})
read(OBS / 'ACTUAL_OBSERVATION_TOOLS.json')
read(OBS / 'seal_observation.py')
read(EX / 'efficiency_incident_20260929_1448' / 'observation_20260930_162821323' / 'OBSERVATION.json', {
    'path': str(EX / 'efficiency_incident_20260929_1448' / 'observation_20260930_162821323' / 'OBSERVATION.json'),
    'bytes': 5767, 'sha256': '2c8df67c071ea28d70f524062ddad428dcfa4f3b25d416ed3bf1d4407e269670'})
read(HERE / 'adopt_closed_source.py')

report = {
    'schema': 'native-b1-slot-bridge-root-closed-source-adoption.v1',
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'source_adopted': True,
    'scope': 'Three selected v2 bridge sources and saved complete deltas as closed source preparation only',
    'selected_sources': manifest['selected_sources'],
    'author_manifest': descriptor(SOURCE / 'SOURCE_MANIFEST.json'),
    'author_delivery': descriptor(SOURCE / 'AUTHOR_DELIVERY.json'),
    'independent_completed_review': descriptor(REVIEW / 'COMPLETED_REVIEW.json'),
    'independent_checker_actual_return': descriptor(REVIEW / 'COMPLETED_STATIC_CHECK_ACTUAL_TOOL_RETURN_V1.json'),
    'root_review_method': {
        'reviewer': 'Root AI reading tool text; no human review',
        'complete_read': 'Three selected v2 sources, all five saved patches, author derivation/sealing programs, interface and metadata, independent checker and completed explanations',
        'shared_guardian_read': 'Relevant authority/grant/interface sections plus inherited prior root v3 delta review; not a new full runtime or whole-program review',
        'root_binding': 'Fresh bounded file bytes below; no repeated AST/delta checker, candidate import, API or scientific suite',
    },
    'independent_method': completed['static_tool'],
    'independent_stdout_display_limitation': completed['tool_stdout_encoding_limitation'],
    'grant_scope_decision': completed['grant_scope_decision'],
    'grant_serialization_limits': completed['grant_serialization_limits'],
    'historical_partial_preserved': True,
    'historical_author_and_old_roots_not_rewritten': True,
    'bindings': list(BINDINGS.values()),
    'root_local_binding_and_consistency_checks': list(CHECKS),
    'local_checks_are_not_scientific_tests': True,
    'runtime_environment_validated': False,
    'runnable_controller_or_worker_validated': False,
    'guardian_pins_installed': False,
    'candidate_execution_or_import': False,
    'release_or_grant_or_attempt_created': False,
    'science_state_or_locks_modified': False,
    'old_scientific_or_control_suite_replayed': False,
    'weights_images_NPZ_cache_large_ZIP_rehashed': False,
    'current_independent_OS_or_GPU_admission': False,
    'execution_released': False,
    'B1_execution_admitted': False,
    'scientific_measurement_admitted': False,
    'T6_complete': False,
    'current_saved_observation': descriptor(OBS / 'ROOT_OBSERVATION_SEAL.json'),
    'saved_observation_interpretation': '26 GPU rows/gate false; current boot unchanged. Numeric14420 conhost and10292 svchost with actual command null are not historical science identities; ordinary user Visio remains. No commit measurement, future admission, exit or cleanup authority.',
    'remaining_work': completed['remaining_runtime_and_scientific_gaps'],
    'all_task_deliveries_complete': False,
    'automation_retained': True,
}
out = write_new('ROOT_CLOSED_SOURCE_ADOPTION.json', report)
print(json.dumps({'report': out, 'fresh_unique_small_bindings': len(BINDINGS),
                  'report_local_checks': len(report['root_local_binding_and_consistency_checks']),
                  'source_adopted': True, 'execution_released': False}, ensure_ascii=False))
