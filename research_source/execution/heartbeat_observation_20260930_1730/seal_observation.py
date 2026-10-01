"""Seal saved current OS/GPU observations; never a future execution admission."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os

HERE = Path(__file__).resolve().parent
EX = HERE.parent
MAX = 262144
def bind(path):
    path = Path(path)
    before = path.stat()
    assert 0 <= before.st_size <= MAX, str(path)
    raw = path.read_bytes()
    after = path.stat()
    assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
def read(path):
    bind(path)
    return json.loads(Path(path).read_bytes())
def verify(record):
    assert bind(record['path']) == record, record['path']

broad_path = HERE / 'OBSERVATION_WRAPPER_INCLUDED.json'
narrow_path = EX / 'efficiency_incident_20260929_1448/observation_20260930_172839956/OBSERVATION.json'
prior_path = EX / 'heartbeat_observation_20260930_162819876/OBSERVATION_WRAPPER_INCLUDED.json'
contract_path = EX / 't6_recovery_preparation_20260930_0405/RECOVERY_CONTRACT.json'
root_path = contract_path.parent / 'ROOT_SOURCE_ADOPTION.json'
broad, narrow, prior, contract = map(read, (broad_path, narrow_path, prior_path, contract_path))
assert bind(broad_path)['sha256'] == '61354f21a6a30a3dea65051503d9211660288a83d3167e4b5ba6058dcc1af6b6'
assert bind(narrow_path)['sha256'] == '17d8533810ca064c41376c1ccc9ce3dd4f96da3fac09d3d8a99c87e9ea4aaa88'
assert bind(contract_path)['sha256'] == '7e10d045a396c53a9ffb7ec0996e38f2a88101413cbf5655548a6f80edcb44ff'
assert bind(root_path)['sha256'] == 'bd39f17134c264f6637d578cb5521a780db011e8bc820e9d9e3436c182476f3e'
assert broad['files'] == prior['files'] and len(broad['files']) == 16
for record in broad['files']: verify(record)
for which in ('first', 'second'):
    assert broad[which]['boot_utc_ticks'] == contract['host_boot_utc_ticks'] == '639263337875000000'
assert broad['first']['matches'] == broad['second']['matches']
rows = broad['first']['matches']
assert len(rows) == 3 and rows == prior['first']['matches'][:3]
assert [(r['pid'], r['name'], r['parent_pid'], r['creation_utc_ticks']) for r in rows] == [
    (29480, 'VISIO.EXE', 13076, '639263338233256210'),
    (17896, 'WeChatAppEx.exe', 5000, '639263535469540740'),
    (14420, 'conhost.exe', 13212, '639263776238715890')]
console = rows[2]
assert console['command_line'] == r'\??\C:\Windows\system32\conhost.exe 0x4'
assert len(narrow['states']) == 5 and all(r['unchanged_since_incident'] is True for r in narrow['states'])
for row in narrow['states']:
    verify(row['source']); verify(row['snapshot'])
expected_narrow = [{'pid': 14420, 'parent': 13212,
    'creation_utc_ticks': '639263776238715890', 'command': console['command_line']}]
assert narrow['first_CIM']['records'] == narrow['second_CIM']['records'] == expected_narrow
assert narrow['gpu_query_exit_code'] == 0 and narrow['gpu_process_rows'] == 26
assert narrow['original_gpu_exclusive_gate_would_be_satisfied'] is False
verify(narrow['gpu_query'])
assert narrow['t6_output_exists'] is False and broad['t6_output_absent'] is True
assert broad['carrier'] == prior['carrier'] and Path(broad['carrier']['path']).read_bytes() == b'0'
assert broad['carrier']['creation_utc_ticks'] == '639262940518466959'
attempts = [EX / f't6_recovery_preparation_{s}/runtime_attempt'
    for s in ('20260929_1548', '20260930_0104', '20260930_0405')]
attempts.append(EX.parent / 'transfer_native_visio_candidate_20260930_0104/runtime_attempt_v1')
assert all(not p.exists() for p in attempts)
report = {
    'schema': 'root-readonly-heartbeat-observation-seal.v3',
    'utc': datetime.now(timezone.utc).isoformat(),
    'source': bind(__file__), 'observation': bind(broad_path),
    'stopped_observation': bind(narrow_path), 'prior_observation': bind(prior_path),
    'current_contract': bind(contract_path), 'current_source_adoption': bind(root_path),
    'boot_ticks': contract['host_boot_utc_ticks'],
    'same_current_visio_wechat_console_identities': True,
    'current_matched_processes': rows,
    'saved_narrow_records_not_empty': True,
    'no_original_scientific_owner_identified_in_saved_filtered_scans': True,
    'prior_service10292_absent_from_current_filtered_scans': True,
    'prior_service_absence_proves_exit_or_old_ownership': False,
    'no_old_process_exit_or_current_task_ownership_inferred': True,
    'unchanged_state_and_closed_log_files': broad['files'],
    'state_heartbeats': [dict(path=r['source']['path'], status=r['status'],
        heartbeat_utc=r['heartbeat_utc']) for r in narrow['states']],
    'carrier': broad['carrier'], 'attempts_absent_at_file_seal': [str(p) for p in attempts],
    'gpu_query': narrow['gpu_query'], 'gpu_rows': 26, 'gpu_exit_code': 0,
    'gpu_gate_satisfied': False, 'available_commit_measured': False,
    'execution_released': False, 'cleanup_authorized': False, 'new_scientific_result': False,
    'limits': [
        'Root AI read saved observer sources and snapshot text. File sealing is not another independent OS capture.',
        'Narrow records contain reused PID14420 conhost; they are not empty. The prior nullable-command service10292 is now absent within the saved filter, which does not prove its exit or historical ownership.',
        'The broad observer references historical Sep29 boot. Its false flag does not mean the current Sep30_0405 contract failed.',
        'Current parent-number observations are not historical ancestry, arbitrary process exclusion or task ownership.',
        'Unknown primary independent exit remains unknown. Numeric presence/absence cannot manufacture an exit code.',
        'Snapshot is not future admission. No release, intent, science import, native probe, COM, cleanup, lock acquisition, state mutation or recovery.',
        'No weights, NPZ, cache, image corpus or old large archives read.'
    ]}
target = HERE / 'ROOT_OBSERVATION_SEAL.json'
with target.open('x', encoding='utf-8', newline='\n') as f:
    json.dump(report, f, ensure_ascii=False, indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
print(json.dumps(bind(target), ensure_ascii=False))
