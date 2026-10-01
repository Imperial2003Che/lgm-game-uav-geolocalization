"""One-shot offline contract derivation; never import or execute a recovery entry."""
from pathlib import Path
import copy
import datetime as dt
import difflib
import hashlib
import json
import sys

HERE = Path(__file__).absolute().parent
EX = HERE.parent
ORIGINAL = EX / 't6_recovery_preparation_20260929_1548'
PREVIOUS = EX / 't6_recovery_preparation_20260930_0104'
NEW = EX / 't6_recovery_preparation_20260930_0405'
OBS = EX / 'heartbeat_observation_20260930_040510057'
STOP = EX / 'efficiency_incident_20260929_1448' / 'observation_20260930_040511476'
BOOT = '639263337875000000'
ROOT_PATH = OBS / 'ROOT_BOOT_OBSERVATION_ADOPTION.json'
PINS = {
    PREVIOUS / 'RECOVERY_CONTRACT.json': 'd0aa27edfc5391689a947dc7a572d38a9a150186672c7d10965715f12e36d136',
    PREVIOUS / 'SOURCE_MANIFEST.json': '40b6ae257c53d77a024979d84bae71b85320a13e08a7a8c58a07f24bfacaa141',
    PREVIOUS / 'ROOT_SOURCE_ADOPTION.json': 'fff6965e4d794902105f578cadb4680f363c7d6d31dcfd0a29bd3e636ea09343',
    OBS / 'OBSERVATION_WRAPPER_INCLUDED.json': '46543c4e92245872f50aa1016ff09afb20d4197a05b872abe3c454837956615b',
    STOP / 'OBSERVATION.json': '42422ac8b18e948b857478668c53c885847eb59be91f8dea08fce47ea25ec586',
}
COPY_PINS = {
    'pipeline_recovery_candidate.py': 'b95ee9ff8c90b9323b89eb3a9228c36e40576b16830eb07dbd78e38cef1f833e',
    'start_pipeline_recovery_candidate.ps1': '3c9e1ec672f6ef7b2a33060495c26d4a766add0b74e2780cc7dc4db732d4eb37',
    'captured_pipeline_status.json': '47fd31336b8e742da91891a87c28a0767989cb45c375aeb000854f50e37acf12',
    'pipeline_seed.json': '20973168dee96357397f27d103db79eec8f71375272fd3d1e9d240487f1d4360',
}
consumed = {}


def read(path):
    path = Path(path)
    assert path.suffix.lower() not in ('.pt', '.pth', '.npz', '.npy', '.png', '.jpg', '.zip')
    assert path.stat().st_size < 2 * 1024 * 1024
    data = path.read_bytes()
    item = {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    assert path not in PINS or item['sha256'] == PINS[path], 'Pinned source changed: ' + str(path)
    consumed[str(path)] = item
    return data


def binding(path):
    read(path)
    return consumed[str(Path(path))]


def load(path):
    return json.loads(read(path).decode('utf-8-sig'))


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def write(path, data):
    with Path(path).open('xb') as stream:
        stream.write(data)


def output_binding(path):
    data = Path(path).read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def semantic_diff(a, b, pointer=''):
    if type(a) is not type(b):
        return [{'pointer': pointer, 'operation': 'replace', 'old': a, 'new': b}]
    if isinstance(a, dict):
        changes = []
        for key in sorted(a.keys() | b.keys()):
            child = pointer + '/' + key.replace('~', '~0').replace('/', '~1')
            if key not in a:
                changes.append({'pointer': child, 'operation': 'add', 'new': b[key]})
            elif key not in b:
                changes.append({'pointer': child, 'operation': 'remove', 'old': a[key]})
            else:
                changes.extend(semantic_diff(a[key], b[key], child))
        return changes
    if isinstance(a, list):
        changes = []
        for index in range(max(len(a), len(b))):
            child = pointer + '/' + str(index)
            if index >= len(a):
                changes.append({'pointer': child, 'operation': 'add', 'new': b[index]})
            elif index >= len(b):
                changes.append({'pointer': child, 'operation': 'remove', 'old': a[index]})
            else:
                changes.extend(semantic_diff(a[index], b[index], child))
        return changes
    return [] if a == b else [{'pointer': pointer, 'operation': 'replace', 'old': a, 'new': b}]


assert len(sys.argv) == 2 and len(sys.argv[1]) == 64 and all(c in '0123456789abcdef' for c in sys.argv[1])
PINS[ROOT_PATH] = sys.argv[1]
assert not NEW.exists(), 'Never overwrite or replay an existing preparation directory'
assert not (HERE / 'DERIVATION.json').exists(), 'Derivation already completed'
previous_raw = read(PREVIOUS / 'RECOVERY_CONTRACT.json')
previous = json.loads(previous_raw)
previous_manifest = load(PREVIOUS / 'SOURCE_MANIFEST.json')
previous_adoption = load(PREVIOUS / 'ROOT_SOURCE_ADOPTION.json')
assert previous_adoption['source_manifest'] == binding(PREVIOUS / 'SOURCE_MANIFEST.json')
assert previous_adoption['approved_for_future_gated_execution'] is True
assert previous_adoption['execution_released'] is False
assert previous_manifest['input_contract'] == binding(PREVIOUS / 'RECOVERY_CONTRACT.json')
assert previous['host_boot_utc_ticks'] == '639263179115000000'
assert len(previous['input_bindings']) == 107
assert previous['current_boot_authority']['original_incident_boot_utc_ticks'] == '639262263395000000'

observation = load(OBS / 'OBSERVATION_WRAPPER_INCLUDED.json')
stopped = load(STOP / 'OBSERVATION.json')
root = load(ROOT_PATH)
assert root['new_boot_ticks'] == BOOT
assert root['execution_released'] is False
assert root['accepted_with_stated_limits'] is True
assert binding(OBS / 'OBSERVATION_WRAPPER_INCLUDED.json') in root['bindings']
assert binding(STOP / 'OBSERVATION.json') in root['bindings']
assert all(observation[key]['boot_utc_ticks'] == BOOT for key in ('first', 'second'))
assert observation['runtime_attempt_absent'] and observation['t6_output_absent']
assert all(item in observation['files'] for item in previous['live_state_bindings'])
assert all(item in observation['files'] for item in previous['append_log_prefixes'])
assert len(observation['files']) == 16
assert stopped['host_boot_utc'] == '2026-09-30T02:56:27.5000000+00:00'
assert stopped['gpu_query_exit_code'] == 0 and stopped['gpu_process_rows'] == 23
assert stopped['original_gpu_exclusive_gate_would_be_satisfied'] is False
assert all(row['unchanged_since_incident'] for row in stopped['states'])
assert observation['carrier']['bytes'] == 1 and observation['carrier']['byte_values'] == [48]
assert observation['carrier']['sha256'] == '5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9'
assert observation['carrier']['creation_utc_ticks'] == '639262940518466959'

sources = {}
for name, sha in COPY_PINS.items():
    sources[name] = read(PREVIOUS / name)
    assert binding(PREVIOUS / name)['sha256'] == sha
    assert binding(PREVIOUS / name) in previous_manifest['candidate_files']
captured = json.loads(sources['captured_pipeline_status.json'])
seed = json.loads(sources['pipeline_seed.json'])
spec = load(previous['recovery_spec']['path'])
assert binding(previous['recovery_spec']['path']) == previous['recovery_spec']
assert len(captured['jobs']) == len(seed['jobs']) == 7
assert captured['jobs'][:6] == seed['jobs'][:6]
assert all(j['status'] == 'completed' and type(j['exit_code']) is int and j['exit_code'] == 0 for j in captured['jobs'][:6])
assert captured['jobs'][6]['status'] == 'failed' and captured['jobs'][6]['exit_code'] == 1
assert seed['jobs'][6]['status'] == 'pending' and seed['status'] == 'waiting_for_primary'
for before, after in zip(captured['jobs'], seed['jobs']):
    assert all(before[key] == after[key] for key in ('id', 'command', 'entrypoint_sha256'))
assert captured['jobs'][6]['command'] == spec['original_t6_command']
assert captured['jobs'][6]['entrypoint_sha256'] == spec['original_t6_entrypoint_sha256']
assert seed['recovery_preparation']['incident_capture'] == previous['incident_capture']

# These seven provenance files are newly bound; the 107 inherited files are not traversed.
added_paths = [PREVIOUS / 'RECOVERY_CONTRACT.json', PREVIOUS / 'SOURCE_MANIFEST.json',
               PREVIOUS / 'ROOT_SOURCE_ADOPTION.json', OBS / 'OBSERVATION_WRAPPER_INCLUDED.json',
               STOP / 'OBSERVATION.json', ROOT_PATH, Path(__file__).absolute()]
additions = [binding(path) for path in added_paths]
assert len({item['path'] for item in previous['input_bindings'] + additions}) == 114
now = dt.datetime.now(dt.timezone.utc).isoformat()
new = copy.deepcopy(previous)
new['prepared_utc'] = now
new['host_boot_utc'] = '2026-09-30T02:56:27.5000000+00:00'
new['host_boot_utc_ticks'] = BOOT
new['known_prerequisite'] = (
    'The existing one-byte shared carrier has adopted initialization and unchanged saved observation; '
    'do not initialize it again. Current saved GPU query has 23 rows, so no execution release is supported. '
    'New source adoption and fresh complete root readiness remain required before any separately gated release.')
new['input_bindings'] += additions
authority = new['current_boot_authority']
authority['observation'] = binding(OBS / 'OBSERVATION_WRAPPER_INCLUDED.json')
authority['root_observation_seal'] = binding(ROOT_PATH)
authority['boot_interpretation_adoption'] = binding(ROOT_PATH)
authority['root_authority_note'] = 'The current root jointly adopts the observation and boot interpretation; these two fields reference that same immutable report.'
authority['saved_samples_utc'] = [observation[key]['observed_utc'] for key in ('first', 'second')]
authority['previous_contract_boot_utc_ticks'] = previous['host_boot_utc_ticks']
new['historical_source_provenance'] = {
    'previous_contract': binding(PREVIOUS / 'RECOVERY_CONTRACT.json'),
    'previous_manifest': binding(PREVIOUS / 'SOURCE_MANIFEST.json'),
    'previous_source_adoption': binding(PREVIOUS / 'ROOT_SOURCE_ADOPTION.json'),
    'previous_source_adoption_authorizes_this_manifest': False,
    'derivation_source': binding(Path(__file__).absolute()),
    'source_bytes_unchanged': list(COPY_PINS),
    'copied_old_preparer_checker_sealer_or_tests': False,
}
assert new['limits'][5] == 'Existing carrier is not held ownership. Fresh readiness must cover old and new attempt absence; unchanged candidate directly gates only its own HERE/runtime_attempt.'
assert new['limits'][6].startswith('The saved 26-row GPU query')
attempts = [str(folder / 'runtime_attempt') for folder in (ORIGINAL, PREVIOUS, NEW)]
new['limits'][5] = ('Existing carrier is not held ownership. Fresh root readiness must cover absence of runtime_attempt in all three '
    'preparation directories: t6_recovery_preparation_20260929_1548, t6_recovery_preparation_20260930_0104, '
    't6_recovery_preparation_20260930_0405. The unchanged candidate directly gates only its own HERE/runtime_attempt.')
new['limits'][6] = 'The saved 23-row GPU query cannot authorize launch. No user-app exemption, closure, weakened guard, successor release or five-layer completion follows.'
new['limits'].append('The prior two boot-bound contract adoptions remain historical and cannot authorize this manifest. Current observation does not establish any uncaptured process exit or task ownership of the observed Visio application.')
new['future_root_runtime_attempt_absence_paths'] = attempts
for key in previous:
    if key not in {'prepared_utc', 'host_boot_utc', 'host_boot_utc_ticks', 'known_prerequisite',
                   'input_bindings', 'current_boot_authority', 'historical_source_provenance', 'limits'}:
        assert new[key] == previous[key], 'Unexpected field mutation: ' + key
assert new['input_bindings'][:107] == previous['input_bindings']
assert new['current_boot_authority']['original_incident_boot_utc_ticks'] == '639262263395000000'

# Existence reads only, no lock opening, state mutation, process queries or scientific imports.
assert all(not Path(path).exists() for path in attempts)
assert not Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\analysis\transactions_t6_formal').exists()
NEW.mkdir()
assert NEW.parent == EX
for name, data in sources.items():
    write(NEW / name, data)
    assert (NEW / name).read_bytes() == data
new_raw = encoded(new)
write(NEW / 'RECOVERY_CONTRACT.json', new_raw)
members = [output_binding(NEW / name) for name in COPY_PINS] + [output_binding(NEW / 'RECOVERY_CONTRACT.json')]
manifest = {
    'schema': 't6-pipeline-recovery-source-manifest.v1', 'created_utc': now,
    'status': 'new_boot_preparation_only_pending_root_review_not_released_not_executed',
    'candidate_files': members, 'input_contract': output_binding(NEW / 'RECOVERY_CONTRACT.json'),
    'scientific_sources_modified': False,
    'required_root_adoption_schema': 't6-pipeline-recovery-source-adoption.v1',
    'required_release_schema': 't6-pipeline-recovery-release.v1',
    'candidate_files_count_excluding_this_manifest': 5,
    'total_preparation_directory_files_including_this_manifest': 6,
    'previous_manifest_adoption_is_not_this_manifest_adoption': True,
}
write(NEW / 'SOURCE_MANIFEST.json', encoded(manifest))
changes = semantic_diff(previous, new)
write(HERE / 'CONTRACT_SEMANTIC_DIFF.json', encoded({
    'schema': 'complete-json-value-diff.v1', 'old': binding(PREVIOUS / 'RECOVERY_CONTRACT.json'),
    'new': output_binding(NEW / 'RECOVERY_CONTRACT.json'),
    'method': 'Complete recursive key/index union; strict scalar types; full values for additions.',
    'changes': changes, 'unchanged_top_level_fields': [k for k in previous if previous[k] == new[k]],
    'old_keys': list(previous), 'new_keys': list(new), 'removals': [x for x in changes if x['operation'] == 'remove'],
}))
patch = b''.join(difflib.diff_bytes(difflib.unified_diff, previous_raw.splitlines(keepends=True),
    new_raw.splitlines(keepends=True), fromfile=b'previous/RECOVERY_CONTRACT.json', tofile=b'new/RECOVERY_CONTRACT.json'))
write(HERE / 'RECOVERY_CONTRACT.patch', patch)
report = {
    'schema': 't6-new-boot-offline-derivation.v1', 'utc': now,
    'status': 'prepared_for_independent_and_root_source_review_only',
    'preparation_directory': str(NEW), 'source': binding(Path(__file__).absolute()),
    'new_manifest': output_binding(NEW / 'SOURCE_MANIFEST.json'),
    'new_contract': output_binding(NEW / 'RECOVERY_CONTRACT.json'),
    'four_exact_copies': [{'old': binding(PREVIOUS / name), 'new': output_binding(NEW / name), 'byte_equal': True} for name in COPY_PINS],
    'all_first_six_complete_job_objects_equal': True,
    'all_seven_id_command_entrypoint_sha256_equal': True,
    'original_seventh_failed_exit1_preserved_in_original': True,
    'original_seventh_command': spec['original_t6_command'],
    'original_seventh_entrypoint_sha256': spec['original_t6_entrypoint_sha256'],
    'seed_bytes_and_original_incident_annotation_unchanged': True,
    'inherited_107_contract_bindings_carried_without_full_rehash': True,
    'added_small_input_bindings': additions, 'new_input_count': 114,
    'candidate_manifest_bound_files': 5, 'directory_files_including_manifest': 6,
    'observed_five_states_and_log_prefixes_match_contract': True,
    'evidence_scope': 'State/log/carrier assertions use saved root-adopted observations; this derivation did not rehash live states or all historical input files.',
    'new_boot_ticks': BOOT, 'previous_boot_ticks': previous['host_boot_utc_ticks'], 'saved_gpu_rows': 23,
    'root_boot_authority': binding(ROOT_PATH),
    'three_runtime_attempt_paths_absent_at_preparation': attempts,
    't6_output_absent_at_preparation': True,
    'carrier_content_not_opened_hashed_or_locked': True,
    'execution_released': False, 'new_root_source_adoption_created': False,
    'release_created': False, 'candidate_imported_or_executed': False,
    'native_or_science_or_synthetic_tests_executed': False,
    'live_state_old_source_logs_or_handoff_modified': False,
    'semantic_diff': output_binding(HERE / 'CONTRACT_SEMANTIC_DIFF.json'),
    'byte_line_diff': output_binding(HERE / 'RECOVERY_CONTRACT.patch'),
    'consumed_small_files': list(consumed.values()),
    'limitations': [
        'Only JSON comparison, exact byte copying, SHA256 of small consumed files and existence reads were executed; no prior generator, runner, native probe or suite ran.',
        'No resource gate, lock, actual child identity/exit, T6 measurement or successor release is established.',
        'Current boot authority and three-attempt list are provenance/root-review fields, not new runtime parsers in the unchanged guardian.',
        'The new source manifest still needs independent/root adoption. The saved nonempty GPU query cannot support an execution release.',
    ],
}
write(HERE / 'DERIVATION.json', encoded(report))
print(json.dumps({'manifest': report['new_manifest'], 'contract': report['new_contract'],
    'derivation': output_binding(HERE / 'DERIVATION.json'), 'semantic_changes': len(changes),
    'execution_released': False}, ensure_ascii=False))
