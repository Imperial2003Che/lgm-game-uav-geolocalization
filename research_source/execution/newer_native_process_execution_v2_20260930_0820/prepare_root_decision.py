"""Root decision for separately reviewed repaired CPU control; no candidate import."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
EX = HERE.parent
SRC = EX / 'external_efficiency_preparation/newer_native_process_evidence_v2'
OLD = SRC.parent / 'newer_native_process_evidence_v1'
REVIEW = EX / 'newer_native_process_runtime_review_20260930_0758'
records = {}

def bind(path):
    path = Path(path)
    assert path.stat().st_size < 100000
    raw = path.read_bytes()
    item = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    records[str(path)] = item
    return item

def verify(item):
    assert bind(item['path']) == item, item['path']

def read(path):
    bind(path)
    return json.loads(Path(path).read_bytes())

assert bind(SRC / 'windows_process_evidence.py')['sha256'] == 'cc090bec1429ab429b556200597acedfa13c33e878627155b0cc9f8098c9f5d2'
assert bind(SRC / 'benign_fixture.py')['sha256'] == '05379eda9addbac90faea33d73eb9a0faa4fc59450bf65e3e1f11de677fca50f'
assert (SRC / 'benign_fixture.py').read_bytes() == (OLD / 'benign_fixture.py').read_bytes()
manifest = read(SRC / 'SOURCE_MANIFEST.json')
assert bind(SRC / 'SOURCE_MANIFEST.json')['sha256'] == 'a733c63322aefd299ec6d603ece6a769c466e7e61191780a5580a2b1340132aa'
assert manifest['execution_released'] is False and manifest['runtime_validated'] is False
for item in manifest['files'] + manifest['parent_source_bindings']:
    verify(item)
delivery = read(SRC / 'DELIVERY.json')
verify(delivery['source_manifest'])
for item in read(SRC / 'FAILURE_INPUT_BINDINGS.json')['files']:
    verify(item)
static = read(REVIEW / 'V2_PREEXEC_SOURCE_REVIEW.json')
assert static['execution_released'] is False and static['runtime_validated'] is False
for item in static['inputs']:
    verify(item)
failure_root = read(EX / 'newer_native_process_execution_20260930_0810/ROOT_FAILED_CONTROL_ADOPTION.json')
assert failure_root['diagnosis_adopted'] is True and failure_root['fixture_passed'] is False
assert failure_root['replay_authorized'] is False
bind(EX / 'newer_native_process_execution_20260930_0810/ROOT_EXIT_REPAIR_PRIMARY_SOURCES.json')
obs = read(EX / 'process_fixture_before_v2_20260930_0830/OBSERVATION_WRAPPER_INCLUDED.json')
for which in ['first', 'second']:
    assert obs[which]['boot_utc_ticks'] == '639263337875000000'
    assert len(obs[which]['matches']) == 1 and obs[which]['matches'][0]['name'] == 'VISIO.EXE'
assert obs['first']['matches'] == obs['second']['matches']
assert len(obs['files']) == 16
for item in obs['files']:
    verify(item)
verify({key: obs['carrier'][key] for key in ['path', 'bytes', 'sha256']})
assert Path(obs['carrier']['path']).read_bytes() == b'0'
assert obs['carrier']['creation_utc_ticks'] == '639262940518466959'
contract = read(EX / 't6_recovery_preparation_20260930_0405/RECOVERY_CONTRACT.json')
assert contract['host_boot_utc_ticks'] == obs['second']['boot_utc_ticks']
bind(EX / 't6_recovery_preparation_20260930_0405/ROOT_SOURCE_ADOPTION.json')
b1 = EX / 'external_efficiency_preparation/newer_native_b1_worker_v1/reference_worker.py'
assert bind(b1)['sha256'] == 'eed9b25b1204edbcf5172ea2fb24e272b7ff39103f98448e554a3dae779b7f46'
attempts = [EX / f't6_recovery_preparation_{stamp}/runtime_attempt'
            for stamp in ['20260929_1548', '20260930_0104', '20260930_0405']]
attempts += [EX.parent / 'transfer_native_visio_candidate_20260930_0104/runtime_attempt_v1',
             SRC / 'runtime_attempt_v1', HERE / 'outer_runtime_attempt_v1']
assert all(not path.exists() for path in attempts)
assert (OLD / 'runtime_attempt_v1').exists()
assert (EX / 'newer_native_process_execution_20260930_0810/outer_runtime_attempt_v1').exists()
outer = bind(HERE / 'run_outer.py')
assert outer['sha256'] == '7f06502ca666cffcd2f06b4b3c0242e8deb816ab077bb16d28de6153221a233d'
assert (HERE / 'OUTER_V1_SOURCE.py.txt').read_bytes().replace(
    b'newer_native_process_evidence_v1', b'newer_native_process_evidence_v2') == (HERE / 'run_outer.py').read_bytes()
diff = b''.join(difflib.diff_bytes(difflib.unified_diff,
    (HERE / 'OUTER_V1_SOURCE.py.txt').read_bytes().splitlines(keepends=True),
    (HERE / 'run_outer.py').read_bytes().splitlines(keepends=True),
    fromfile=b'v1/run_outer.py', tofile=b'v2/run_outer.py'))
with (HERE / 'OUTER_PATH_ONLY.patch').open('xb') as stream:
    stream.write(diff)
bind(HERE / 'OUTER_PATH_ONLY.patch')
ast.parse((HERE / 'run_outer.py').read_text(encoding='utf-8'))
bind(__file__)
now = datetime.now(timezone.utc)
assert 0 <= (now - datetime.fromisoformat(obs['second']['observed_utc'])).total_seconds() < 900
decision = {
    'schema': 'root-one-benign-process-fixture-decision.v1', 'issued_utc': now.isoformat(),
    'execute': True, 'maximum_fixture_attempts': 1,
    'scope': 'Separate repaired-v2 ordinary Python311 -I -S -B CPU two-case fixture; never replay v1',
    'scientific_admission': False, 'scientific_release': False, 'cleanup_of_user_apps_authorized': False,
    'source_inspection': 'Root AI read full v2 helper, producer derivation source, complete diff/README, unchanged v1 fixture, and independent v1 failure/v2 pre-execution reviews. No old checker or runtime was replayed.',
    'small_inputs': list(records.values()), 'outer_source': outer,
    'observed_current_boot_utc_ticks': obs['second']['boot_utc_ticks'],
    'attempts_absent_at_decision': [str(path) for path in attempts],
    'preserved_consumed_v1_attempts': [str(OLD / 'runtime_attempt_v1'), str(EX / 'newer_native_process_execution_20260930_0810/outer_runtime_attempt_v1')],
    'predeclared_cases': [{'name': 'zero', 'child_exit': 0, 'launcher_exit': 0},
                          {'name': 'nonzero17', 'child_exit': 17, 'launcher_exit': 17}],
    'limits': [
        'This new reviewed version is one explicit root control decision, not an automatic replay of consumed v1.',
        'No scientific environment/model/GPU/B1 body/COM/old suite/locks/scientific release or intent is invoked.',
        'GPU remained nonempty in the saved original query; no scientific resource admission is asserted by this CPU decision.',
        'Existing ordinary Visio remains untouched; current observations confer no application ownership or cleanup rights.',
        'Nt class60 stays undocumented and experimental; current-host success cannot validate all Windows or the original scientific venv launcher.',
        'Live image/full command/two contemporaneous parentage observations remain. After signaled wait, same held PID/creation and actual exit code/time are required.',
        'Incomplete exit candidates cannot replace complete exits or allow a closed-log seal; all cleanup records require later review.',
        'Outer own actual exit is unknown in its return record; forwarded shell/tool exit is separate limited evidence.',
        'This supplies no six native scientific workers, real predecessor exits/resource-release/shared locks, fresh gallery/ranking/parity/timing/onlineCLIP or T6 acceptance.'
    ]}
target = HERE / 'ROOT_BENIGN_FIXTURE_DECISION.json'
with target.open('xb') as stream:
    stream.write((json.dumps(decision, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8'))
print(json.dumps({'decision': bind(target), 'small_bindings': len(decision['small_inputs'])}, ensure_ascii=False))
