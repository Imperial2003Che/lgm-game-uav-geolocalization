"""Bounded saved observation adoption, not another OS or future admission."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os

HERE = Path(__file__).resolve().parent
EX = HERE.parent
MAX = 262144
records = {}

def read(path):
    path = Path(path)
    before = path.stat()
    assert 0 <= before.st_size <= MAX, str(path)
    with path.open('rb') as stream:
        raw = stream.read(MAX + 1)
    after = path.stat()
    assert len(raw) == before.st_size <= MAX
    assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
    record = dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    records[str(path)] = record
    return raw, record

def obj(path):
    raw, record = read(path)
    return json.loads(raw), record

def verify(record):
    _, actual = read(record['path'])
    assert actual == record, record['path']

broad, broad_d = obj(HERE / 'OBSERVATION_WRAPPER_INCLUDED.json')
narrow, narrow_d = obj(EX / 'efficiency_incident_20260929_1448/observation_20260930_203112314/OBSERVATION.json')
prior, prior_d = obj(EX / 'heartbeat_observation_20260930_1936/OBSERVATION_WRAPPER_INCLUDED.json')
contract, contract_d = obj(EX / 't6_recovery_preparation_20260930_0405/RECOVERY_CONTRACT.json')
root, root_d = obj(EX / 't6_recovery_preparation_20260930_0405/ROOT_SOURCE_ADOPTION.json')
assert broad_d['sha256'] == 'bc1b2d9fdd7b747d920962df378b4e39b6a1d9a7fbcc091f02b0de5dceaef526'
assert narrow_d['sha256'] == 'eafd8b84ecef3a8cba6f227678398c925ad71e51cff72789ed57b19dfacf3213'
assert contract_d['sha256'] == '7e10d045a396c53a9ffb7ec0996e38f2a88101413cbf5655548a6f80edcb44ff'
assert root_d['sha256'] == 'bd39f17134c264f6637d578cb5521a780db011e8bc820e9d9e3436c182476f3e'
assert broad['files'] == prior['files'] and len(broad['files']) == 16
for record in broad['files']:
    verify(record)
for label in ('first', 'second'):
    assert broad[label]['boot_utc_ticks'] == contract['host_boot_utc_ticks'] == '639263337875000000'
assert broad['first']['matches'] == broad['second']['matches'] == prior['first']['matches']
rows = broad['first']['matches']
assert len(rows) == 3
expected_narrow = [{'pid': 14420, 'parent': 13212,
    'creation_utc_ticks': '639263776238715890',
    'command': rows[2]['command_line']}]
assert narrow['first_CIM']['records'] == narrow['second_CIM']['records'] == expected_narrow
assert len(narrow['states']) == 5 and all(x['unchanged_since_incident'] is True for x in narrow['states'])
for state in narrow['states']:
    verify(state['source'])
    verify(state['snapshot'])
assert narrow['gpu_query_exit_code'] == 0 and narrow['gpu_process_rows'] == 26
assert narrow['original_gpu_exclusive_gate_would_be_satisfied'] is False
verify(narrow['gpu_query'])
assert narrow['t6_output_exists'] is False and broad['t6_output_absent'] is True
assert broad['carrier'] == prior['carrier']
carrier_raw, carrier_d = read(broad['carrier']['path'])
assert carrier_raw == b'0'
assert broad['carrier']['creation_utc_ticks'] == '639262940518466959'
attempts = [EX / f't6_recovery_preparation_{s}/runtime_attempt'
    for s in ('20260929_1548', '20260930_0104', '20260930_0405')]
attempts.append(EX.parent / 'transfer_native_visio_candidate_20260930_0104/runtime_attempt_v1')
assert all(not p.exists() for p in attempts)
_, source_d = read(__file__)
report = dict(
    schema='root-readonly-heartbeat-observation-seal.v4',
    utc=datetime.now(timezone.utc).isoformat(), source=source_d,
    observation=broad_d, stopped_observation=narrow_d, prior_observation=prior_d,
    current_contract=contract_d, current_source_adoption=root_d,
    current_boot_matches_0405_contract=True,
    boot_ticks=contract['host_boot_utc_ticks'],
    current_matched_processes=rows,
    same_current_visio_wechat_console_identities=True,
    narrow_records_not_empty=True,
    no_original_scientific_owner_identified_in_saved_filtered_scans=True,
    primary_independent_own_exit='unknown',
    state_heartbeats=[dict(path=x['source']['path'], status=x['status'],
        heartbeat_utc=x['heartbeat_utc']) for x in narrow['states']],
    unchanged_state_and_closed_log_files=broad['files'],
    carrier=broad['carrier'], attempts_absent_at_file_seal=[str(p) for p in attempts],
    gpu_query=narrow['gpu_query'], gpu_exit_code=0, gpu_rows=26,
    gpu_gate_satisfied=False, available_commit_measured=False,
    execution_released=False, cleanup_authorized=False, new_scientific_result=False,
    local_bindings=list(records.values()),
    methods='Root AI read saved broad/narrow snapshots and prior sealer text; bounded local file bytes and saved relationships only. No repeat of scientific or control suites.',
    limits=[
        'Snapshot sealing is not another independent OS/GPU capture or future admission.',
        'Narrow records contain reused PID14420 conhost; they are not empty. Same numeric identifiers never prove old actor ownership or historical exits.',
        'Current parent-number observations are not historical complete ancestry or arbitrary process exclusion.',
        'Historical Sep29 boot mismatch flag is not a failure of current Sep30_0405 contract.',
        'Current ordinary user Visio is not attached, closed or used to bypass the empty Visio gate.',
        'No release, intent, scientific import, native probe, COM, cleanup, lock acquisition, recovery or live scientific state modification.',
        'No weight, NPZ, cache, image corpus, old large ZIP, old scientific or control suite read/run.'
    ])
target = HERE / 'ROOT_OBSERVATION_SEAL.json'
with target.open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
    stream.flush()
    os.fsync(stream.fileno())
_, result = read(target)
print(json.dumps(result, ensure_ascii=False))
