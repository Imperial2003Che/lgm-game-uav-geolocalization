"""One-shot offline JSON/source derivation only; never import or run a candidate."""
from pathlib import Path
import copy
import datetime as dt
import difflib
import hashlib
import json

HERE = Path(__file__).absolute().parent
EX = HERE.parent
OLD = EX / 't6_recovery_preparation_20260929_1548'
NEW = EX / 't6_recovery_preparation_20260930_0104'
OBS = EX / 'heartbeat_observation_20260930_0102'
STOP = EX / 'efficiency_incident_20260929_1448' / 'observation_20260930_010228007'
BOOT = '639263179115000000'
consumed = {}

def read(path):
    path = Path(path)
    assert path.suffix.lower() not in ('.pt', '.pth', '.npz', '.npy', '.png', '.jpg', '.zip')
    assert path.stat().st_size < 2 * 1024 * 1024
    data = path.read_bytes()
    consumed[str(path)] = {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    return data

def binding(path):
    read(path)
    return consumed[str(Path(path))]

def load(path):
    return json.loads(read(path).decode('utf-8-sig'))

def write(path, data):
    with Path(path).open('xb') as stream:
        stream.write(data)

def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')

def out_binding(path):
    data = Path(path).read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def semantic_diff(a, b, pointer=''):
    if type(a) is not type(b):
        return [{'pointer': pointer, 'operation': 'replace', 'old': a, 'new': b}]
    if isinstance(a, dict):
        result = []
        for key in sorted(a.keys() | b.keys()):
            p = pointer + '/' + key.replace('~', '~0').replace('/', '~1')
            if key not in a:
                result.append({'pointer': p, 'operation': 'add', 'new': b[key]})
            elif key not in b:
                result.append({'pointer': p, 'operation': 'remove', 'old': a[key]})
            else:
                result.extend(semantic_diff(a[key], b[key], p))
        return result
    if isinstance(a, list):
        result = []
        for index in range(max(len(a), len(b))):
            p = pointer + '/' + str(index)
            if index >= len(a):
                result.append({'pointer': p, 'operation': 'add', 'new': b[index]})
            elif index >= len(b):
                result.append({'pointer': p, 'operation': 'remove', 'old': a[index]})
            else:
                result.extend(semantic_diff(a[index], b[index], p))
        return result
    return [] if a == b else [{'pointer': pointer, 'operation': 'replace', 'old': a, 'new': b}]

assert not NEW.exists(), 'Never overwrite or replay an existing preparation directory'
assert not (HERE / 'DERIVATION.json').exists(), 'One-shot derivation already completed'
old_raw = read(OLD / 'RECOVERY_CONTRACT.json')
old = json.loads(old_raw)
old_manifest = load(OLD / 'SOURCE_MANIFEST.json')
old_adoption = load(OLD / 'ROOT_SOURCE_ADOPTION.json')
assert binding(OLD / 'RECOVERY_CONTRACT.json')['sha256'] == '01bf6d97793d0fbcda9936a85b7955b83e336d0c932531eec9f8f33b179b08a3'
assert old_adoption['source_manifest'] == binding(OLD / 'SOURCE_MANIFEST.json')
assert old_manifest['input_contract'] == binding(OLD / 'RECOVERY_CONTRACT.json')
assert old['host_boot_utc_ticks'] == '639262263395000000'
assert len(old['input_bindings']) == 96

observation = load(OBS / 'OBSERVATION_WRAPPER_INCLUDED.json')
seal = load(OBS / 'ROOT_OBSERVATION_SEAL.json')
assert binding(OBS / 'ROOT_OBSERVATION_SEAL.json')['sha256'] == 'a039ce8415a581cc92583ba6d9de476ed7b6b2e8143b42462c18d4b2a51ca103'
assert binding(OBS / 'OBSERVATION_WRAPPER_INCLUDED.json') in seal['bindings']
assert seal['accepted_observation_only'] and not seal['execution_released']
assert all(observation[key]['boot_utc_ticks'] == BOOT for key in ('first', 'second'))
assert observation['runtime_attempt_absent'] and observation['t6_output_absent']
assert all(item in observation['files'] for item in old['live_state_bindings'])
assert all(item in observation['files'] for item in old['append_log_prefixes'])
stopped = load(STOP / 'OBSERVATION.json')
assert binding(STOP / 'OBSERVATION.json') in seal['bindings']
assert stopped['gpu_query_exit_code'] == 0 and stopped['gpu_process_rows'] == 26
assert not stopped['original_gpu_exclusive_gate_would_be_satisfied']
assert all(row['unchanged_since_incident'] for row in stopped['states'])
init_path = EX / 'shared_lock_initialization_20260929_1652' / 'ROOT_INITIALIZATION_ADOPTION.json'
init = load(init_path)
assert init['lock'] == {key: observation['carrier'][key] for key in ('path', 'bytes', 'sha256')}
assert observation['carrier']['bytes'] == 1 and observation['carrier']['byte_values'] == [48]
assert init['replay_forbidden'] and not init['recovery_launched']
boot_root_path = EX / 'host_boot_change_20260930_0008' / 'ROOT_BOOT_OBSERVATION_ADOPTION.json'
boot_root = load(boot_root_path)
assert boot_root['new_boot_ticks'] == BOOT and boot_root['accepted_with_stated_limits']
assert not boot_root['execution_released']
boot_review_path = EX / 'host_boot_change_review_20260930_0008' / 'REVIEW.json'
boot_addendum_path = EX / 'host_boot_change_review_20260930_0008' / 'WRAPPER_ADDENDUM.json'
assert load(boot_review_path)['passed_with_stated_scope']
assert load(boot_addendum_path)['passed_with_stated_scope']

copy_names = ('pipeline_recovery_candidate.py', 'start_pipeline_recovery_candidate.ps1',
              'captured_pipeline_status.json', 'pipeline_seed.json')
source_bytes = {}
for name in copy_names:
    source_bytes[name] = read(OLD / name)
    assert binding(OLD / name) in old_manifest['candidate_files']
original = json.loads(source_bytes['captured_pipeline_status.json'])
seed = json.loads(source_bytes['pipeline_seed.json'])
spec = load(Path(old['recovery_spec']['path']))
assert binding(Path(old['recovery_spec']['path'])) == old['recovery_spec']
assert len(original['jobs']) == len(seed['jobs']) == 7
assert original['jobs'][:6] == seed['jobs'][:6]
assert all(job['status'] == 'completed' and type(job['exit_code']) is int and job['exit_code'] == 0 for job in original['jobs'][:6])
assert original['jobs'][6]['status'] == 'failed' and original['jobs'][6]['exit_code'] == 1
assert seed['jobs'][6]['status'] == 'pending' and seed['status'] == 'waiting_for_primary'
for before, after in zip(original['jobs'], seed['jobs']):
    assert all(before[key] == after[key] for key in ('id', 'command', 'entrypoint_sha256'))
assert original['jobs'][6]['command'] == spec['original_t6_command']
assert original['jobs'][6]['entrypoint_sha256'] == spec['original_t6_entrypoint_sha256']
assert seed['recovery_preparation']['incident_capture'] == old['incident_capture']

# No old 96-input traversal: retain their adopted values; runtime still verifies them.
added_paths = [OLD / 'RECOVERY_CONTRACT.json', OLD / 'SOURCE_MANIFEST.json', OLD / 'ROOT_SOURCE_ADOPTION.json',
               boot_root_path, boot_review_path, boot_addendum_path,
               OBS / 'OBSERVATION_WRAPPER_INCLUDED.json', STOP / 'OBSERVATION.json',
               OBS / 'ROOT_OBSERVATION_SEAL.json', init_path, Path(__file__).absolute()]
additions = [binding(path) for path in added_paths]
assert len({item['path'] for item in old['input_bindings'] + additions}) == 107
now = dt.datetime.now(dt.timezone.utc).isoformat()
new = copy.deepcopy(old)
new['prepared_utc'] = now
new['host_boot_utc'] = '2026-09-29T22:31:51.5000000+00:00'
new['host_boot_utc_ticks'] = BOOT
new['known_prerequisite'] = ('The existing one-byte shared carrier has adopted initialization and unchanged saved observation; '
    'do not initialize it again. Current saved GPU query has 26 rows, so no execution release is supported. '
    'New source adoption and fresh complete root readiness remain required before any separately gated release.')
new['input_bindings'] += additions
new['current_boot_authority'] = {
    'kind': 'post-stopped-host-reboot-separate-from-original-scientific-incident',
    'observation': binding(OBS / 'OBSERVATION_WRAPPER_INCLUDED.json'),
    'root_observation_seal': binding(OBS / 'ROOT_OBSERVATION_SEAL.json'),
    'boot_interpretation_adoption': binding(boot_root_path),
    'saved_samples_utc': [observation[key]['observed_utc'] for key in ('first', 'second')],
    'original_incident_boot_utc_ticks': old['host_boot_utc_ticks'],
    'original_incident_capture_and_recovery_spec_unchanged': True,
    'saved_observation_is_future_admission': False,
    'runtime_gate': 'Unchanged candidate reads host_boot_utc_ticks; provenance annex is bound via input_bindings, not parsed as independent live gates.'}
new['historical_source_provenance'] = {
    'previous_contract': binding(OLD / 'RECOVERY_CONTRACT.json'),
    'previous_manifest': binding(OLD / 'SOURCE_MANIFEST.json'),
    'previous_source_adoption': binding(OLD / 'ROOT_SOURCE_ADOPTION.json'),
    'previous_source_adoption_authorizes_this_manifest': False,
    'derivation_source': binding(Path(__file__).absolute()),
    'source_bytes_unchanged': list(copy_names),
    'copied_old_preparer_checker_sealer_or_tests': False}
new['limits'] += [
    'This new-boot derivative is source preparation pending root review, not adoption, release, native validation, intent or execution.',
    'Original incident CAPTURE/spec/seed are historical evidence; the new boot authority is separate and does not invent a new scientific failure or old process exit.',
    'Existing carrier is not held ownership. Fresh readiness must cover old and new attempt absence; unchanged candidate directly gates only its own HERE/runtime_attempt.',
    'The saved 26-row GPU query cannot authorize launch. No user-app exemption, closure, weakened guard, successor release or five-layer completion follows.'
]
assert new['input_bindings'][:96] == old['input_bindings']
assert new['live_state_bindings'] == old['live_state_bindings']
assert new['append_log_prefixes'] == old['append_log_prefixes']
assert new['incident_capture'] == old['incident_capture'] and new['recovery_spec'] == old['recovery_spec']

# Existence reads only; no locks, state writes, recovery imports or process queries.
assert not (OLD / 'runtime_attempt').exists()
assert not Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\analysis\transactions_t6_formal').exists()
NEW.mkdir()
assert NEW.parent == EX
for name, data in source_bytes.items():
    write(NEW / name, data)
    assert (NEW / name).read_bytes() == data
new_raw = json_bytes(new)
write(NEW / 'RECOVERY_CONTRACT.json', new_raw)
candidate_bindings = [out_binding(NEW / name) for name in copy_names] + [out_binding(NEW / 'RECOVERY_CONTRACT.json')]
manifest = {
    'schema': 't6-pipeline-recovery-source-manifest.v1', 'created_utc': now,
    'status': 'new_boot_preparation_only_pending_root_review_not_released_not_executed',
    'candidate_files': candidate_bindings,
    'input_contract': out_binding(NEW / 'RECOVERY_CONTRACT.json'),
    'scientific_sources_modified': False,
    'required_root_adoption_schema': 't6-pipeline-recovery-source-adoption.v1',
    'required_release_schema': 't6-pipeline-recovery-release.v1',
    'candidate_files_count_excluding_this_manifest': 5,
    'total_preparation_directory_files_including_this_manifest': 6,
    'previous_manifest_adoption_is_not_this_manifest_adoption': True}
write(NEW / 'SOURCE_MANIFEST.json', json_bytes(manifest))
diff = semantic_diff(old, new)
write(HERE / 'CONTRACT_SEMANTIC_DIFF.json', json_bytes({
    'schema': 'complete-json-value-diff.v1',
    'old': binding(OLD / 'RECOVERY_CONTRACT.json'), 'new': out_binding(NEW / 'RECOVERY_CONTRACT.json'),
    'method': 'Recursive union of every object key and list index, preserving scalar types; added objects contain their full values.',
    'changes': diff,
    'unchanged_top_level_fields': [key for key in old if key in new and old[key] == new[key]],
    'old_keys': list(old), 'new_keys': list(new), 'removals': [x for x in diff if x['operation'] == 'remove']}))
patch = b''.join(difflib.diff_bytes(difflib.unified_diff, old_raw.splitlines(keepends=True), new_raw.splitlines(keepends=True),
    fromfile=b'old/RECOVERY_CONTRACT.json', tofile=b'new/RECOVERY_CONTRACT.json'))
write(HERE / 'RECOVERY_CONTRACT.patch', patch)
for path in (OLD / 'prepare_contract.py', OLD / 'README.md',
             EX / 't6_release_contract_review_20260929_1750' / 'REVIEW.md',
             EX / 't6_release_contract_review_20260929_1750' / 'RELEASE_CONTRACT_REVIEW.json',
             EX / 'host_boot_change_review_20260930_0008' / 'REVIEW.md'):
    binding(path)
report = {
    'schema': 't6-new-boot-offline-derivation.v1', 'utc': now,
    'status': 'prepared_for_root_review_only', 'preparation_directory': str(NEW),
    'new_manifest': out_binding(NEW / 'SOURCE_MANIFEST.json'),
    'new_contract': out_binding(NEW / 'RECOVERY_CONTRACT.json'),
    'four_exact_copies': [{'old': binding(OLD / name), 'new': out_binding(NEW / name), 'byte_equal': True} for name in copy_names],
    'all_first_six_complete_job_objects_equal': True,
    'all_seven_id_command_entrypoint_sha256_equal': True,
    'original_seventh_failed_exit1_preserved_in_original': True,
    'original_seventh_command': spec['original_t6_command'],
    'original_seventh_entrypoint_sha256': spec['original_t6_entrypoint_sha256'],
    'seed_bytes_and_original_incident_annotation_unchanged': True,
    'original_96_contract_bindings_carried_without_rehash': True,
    'added_small_input_bindings': additions, 'new_input_count': 107,
    'candidate_manifest_bound_files': 5, 'directory_files_including_manifest': 6,
    'observed_five_states_and_log_prefixes_match_contract': True,
    'evidence_scope': 'Five state/log assertions use saved root-sealed observations; reviewer did not rehash live states or all historical inputs.',
    'new_boot_ticks': BOOT, 'saved_gpu_rows': 26,
    'old_runtime_attempt_absent_at_preparation': True,
    'new_runtime_attempt_absent': not (NEW / 'runtime_attempt').exists(),
    't6_output_absent_at_preparation': True,
    'carrier_content_not_opened_hashed_or_locked': True,
    'new_root_adoption_created': False, 'release_created': False, 'candidate_imported_or_executed': False,
    'native_or_science_or_synthetic_tests_executed': False,
    'live_state_old_source_logs_or_handoff_modified': False,
    'semantic_diff': out_binding(HERE / 'CONTRACT_SEMANTIC_DIFF.json'),
    'byte_line_diff': out_binding(HERE / 'RECOVERY_CONTRACT.patch'),
    'consumed_small_files': list(consumed.values()),
    'limitations': [
        'Only JSON comparison, byte copying, SHA256, and existence reads were executed. No old preparer/checker/runner or 75-test suite ran.',
        'Runtime behaviors, native imports, locks, GPU and memory admission, process identity, real child exits and scientific results remain untested here.',
        'Any later attempt/intent/state change or boot change requires fresh review; do not replay or overwrite retained entries.',
        'Root must review this new manifest/contract before a separate source adoption; current GPU evidence cannot support a release.'
    ]}
write(HERE / 'DERIVATION.json', json_bytes(report))
print(json.dumps({'status': report['status'], 'manifest': report['new_manifest'], 'contract': report['new_contract'],
    'derivation': out_binding(HERE / 'DERIVATION.json'), 'semantic_changes': len(diff)}, ensure_ascii=False))
