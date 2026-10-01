"""Seal only the new read-only snapshots; no process control or admission."""
from pathlib import Path
import datetime as dt
import hashlib
import json

HERE = Path(__file__).absolute().parent
EX = HERE.parent
bindings = {}
checks = 0

def require(ok, message):
    global checks
    checks += 1
    if not ok:
        raise RuntimeError(message)

def bind(path, expected=None):
    path = Path(path)
    require(path.stat().st_size < 2**20, 'Small-file bound')
    data = path.read_bytes()
    got = {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    if expected is not None:
        require(all(got[k] == expected[k] for k in got), 'Changed snapshot/input: '+str(path))
    bindings[str(path)] = got
    return got

def read(path, sha):
    pin = bind(path)
    require(pin['sha256'] == sha, 'Unexpected report bytes')
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

broad = read(HERE/'OBSERVATION_WRAPPER_INCLUDED.json', 'eec7f7e2c906a63420bed6bf1305c08825d78d1b3c4aa37e97487470e1b27f44')
stopped_path = EX/'efficiency_incident_20260929_1448/observation_20260930_010228007/OBSERVATION.json'
stopped = read(stopped_path, '93c3e43fa78a98beca64e23ea9feb34a5c5cc3e8fd0a2ee8a720a9ea89392674')
for row in broad['files']:
    bind(row['path'], row)
for row in stopped['states']:
    bind(row['source']['path'], row['source'])
    bind(row['snapshot']['path'], row['snapshot'])
    require(row['unchanged_since_incident'] is True, 'State changed')
for row in (broad['source'], stopped['source'], stopped['gpu_query'], broad['prior_reference'], broad['contract'], broad['old_pipeline_launch']):
    bind(row['path'], row)
carrier = broad['carrier']
bind(carrier['path'], carrier)
require(Path(carrier['path']).read_bytes() == b'0', 'Carrier differs')
require(carrier['creation_utc_ticks'] == '639262940518466959', 'Carrier observation changed')
require(broad['contract_boot_matches_current'] is False, 'Old boot contract unexpectedly applies')
for name in ('first', 'second'):
    snap = broad[name]
    require(snap['boot_utc_ticks'] == '639263179115000000', 'Unexpected boot')
    require(len(snap['matches']) == 2, 'Unexpected matched process set')
    rows = {r['name']: r for r in snap['matches']}
    require(set(rows) == {'AppActions.exe', 'VISIO.EXE'}, 'Unexpected matched names')
    app, visio = rows['AppActions.exe'], rows['VISIO.EXE']
    require((app['pid'], app['parent_pid'], app['creation_utc_ticks']) == (14420, 2232, '639263185295777970'), 'AppActions identity differs')
    require(app['command_line'] == '"C:\\Windows\\SystemApps\\MicrosoftWindows.Client.CBS_cw5n1h2txyewy\\AppActions.exe" -Embedding', 'AppActions command differs')
    require((visio['pid'], visio['parent_pid'], visio['creation_utc_ticks']) == (14932, 2232, '639263209854724070'), 'Visio identity differs')
    require(visio['command_line'] == '"C:\\Program Files\\Microsoft Office\\Root\\Office16\\VISIO.EXE" /Automation /Invisible -Embedding', 'Visio command differs')
    for row in (app, visio):
        parent = row['parent_current_observation']
        require(len(parent) == 1 and parent[0]['pid'] == 2232 and parent[0]['creation_utc_ticks'] == '639263179238930240' and parent[0]['command_line'] is None, 'Parent snapshot differs')
require(stopped['gpu_query_exit_code'] == 0 and stopped['gpu_process_rows'] == 26 and stopped['original_gpu_exclusive_gate_would_be_satisfied'] is False, 'Unexpected GPU snapshot')
require(broad['runtime_attempt_absent'] is True and broad['t6_output_absent'] is True and stopped['t6_output_exists'] is False, 'Unexpected runtime/output')
bind(__file__)
report = {
    'schema': 'root-current-stopped-observation-seal.v1',
    'utc': dt.datetime.now(dt.timezone.utc).isoformat(),
    'accepted_observation_only': True,
    'source': bindings[str(Path(__file__).absolute())],
    'checks': checks,
    'bindings': list(bindings.values()),
    'decision': 'Same stopped science and unresolved Visio process; no new completion/failure or user action.',
    'scientific_execution': False, 'COM_execution': False, 'execution_released': False,
    'limits': [
        'Read-only snapshots at 00:02 UTC are not future admission or process ownership.',
        'Numeric 14420 is AppActions, not the historical pipeline. Parent command is unavailable.',
        'VISIO 14932 remains unconfirmed; no attach, Quit, Kill or retry is authorized by this observation.',
        'Old boot-bound T6 contract is inapplicable; GPU remains nonempty. No release/native/intent/lock/state change.',
        'No old scientific checks, model weights, data arrays or partner archive revalidation.'
    ]
}
output = HERE/'ROOT_OBSERVATION_SEAL.json'
with output.open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(bind(output), ensure_ascii=False))
