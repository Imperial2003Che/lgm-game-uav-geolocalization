"""First root small-file pre-execution binding; no candidate import or API."""
from pathlib import Path
import ast
import hashlib
import json
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
EX = HERE.parent
SRC = EX / 'external_efficiency_preparation/newer_native_process_evidence_v1'
REVIEW = EX / 'newer_native_process_evidence_review_20260930_0707'
BEFORE = EX / 'process_fixture_before_20260930_0810/OBSERVATION_WRAPPER_INCLUDED.json'
STOPPED = EX / 'efficiency_incident_20260929_1448/observation_20260930_080440874/OBSERVATION.json'
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

assert bind(SRC / 'windows_process_evidence.py')['sha256'] == 'b21c05e40ec721b343a376e95ba10ae590288ce3eecb33b7238fcf58a16ed023'
assert bind(SRC / 'benign_fixture.py')['sha256'] == '05379eda9addbac90faea33d73eb9a0faa4fc59450bf65e3e1f11de677fca50f'
assert bind(SRC / 'SOURCE_MANIFEST.json')['sha256'] == '0ca3e4acea597ceaad41eeb35285338d8a0a6f837c2480410faf857631ab9603'
manifest = read(SRC / 'SOURCE_MANIFEST.json')
assert manifest['execution_released'] is False and manifest['runtime_validated'] is False
for item in manifest['files']:
    verify(item)
assert bind(REVIEW / 'REVIEW.json')['sha256'] == '66ed055d14540d67b4403702ea6008c8a6ab8852eab6fae2777fcfd0a1a619e8'
review = read(REVIEW / 'REVIEW.json')
assert review['execution_released_by_review'] is False and review['runtime_validated'] is False
for item in review['inputs']:
    verify(item)
delivery = read(REVIEW / 'DELIVERY.json')
for key in ['review', 'explanation', 'review_sealer']:
    verify(delivery[key])
outer_review = read(EX / 'newer_native_process_runtime_review_20260930_0758/OUTER_SOURCE_REVIEW.json')
assert outer_review['execution_released'] is False and outer_review['runtime_validated'] is False
for item in outer_review['inputs']:
    verify(item)
read(SRC / 'DELIVERY.json')
obs = read(BEFORE)
stopped = read(STOPPED)
for item in obs['files']:
    verify(item)
assert len(obs['files']) == 16
for which in ['first', 'second']:
    assert obs[which]['boot_utc_ticks'] == '639263337875000000'
    assert len(obs[which]['matches']) == 1 and obs[which]['matches'][0]['name'] == 'VISIO.EXE'
assert obs['first']['matches'] == obs['second']['matches']
assert stopped['first_CIM']['records'] == stopped['second_CIM']['records'] == []
assert stopped['gpu_query_exit_code'] == 0 and stopped['gpu_process_rows'] == 26
assert stopped['original_gpu_exclusive_gate_would_be_satisfied'] is False
assert stopped['t6_output_exists'] is False
verify(stopped['gpu_query'])
assert all(item['unchanged_since_incident'] is True for item in stopped['states'])
verify({key: obs['carrier'][key] for key in ['path', 'bytes', 'sha256']})
assert Path(obs['carrier']['path']).read_bytes() == b'0'
assert obs['carrier']['creation_utc_ticks'] == '639262940518466959'
attempts = [EX / f't6_recovery_preparation_{stamp}/runtime_attempt'
            for stamp in ['20260929_1548', '20260930_0104', '20260930_0405']]
attempts += [EX.parent / 'transfer_native_visio_candidate_20260930_0104/runtime_attempt_v1',
             SRC / 'runtime_attempt_v1', HERE / 'outer_runtime_attempt_v1']
assert all(not path.exists() for path in attempts)
current_contract = read(EX / 't6_recovery_preparation_20260930_0405/RECOVERY_CONTRACT.json')
assert current_contract['host_boot_utc_ticks'] == obs['first']['boot_utc_ticks']
bind(EX / 't6_recovery_preparation_20260930_0405/ROOT_SOURCE_ADOPTION.json')
outer = bind(HERE / 'run_outer.py')
ast.parse((HERE / 'run_outer.py').read_text(encoding='utf-8'))
bind(__file__)
now = datetime.now(timezone.utc)
assert 0 <= (now - datetime.fromisoformat(obs['second']['observed_utc'])).total_seconds() < 900
decision = {
    'schema': 'root-one-benign-process-fixture-decision.v1', 'issued_utc': now.isoformat(),
    'execute': True, 'maximum_fixture_attempts': 1,
    'scope': 'One ordinary Python311 -I -S -B CPU two-case fixture and external controller observer only',
    'scientific_admission': False, 'scientific_release': False, 'cleanup_of_user_apps_authorized': False,
    'source_inspection': 'Root AI read the full helper, fixture, README, producer sealer/diff and independent review/sealer. Independent AI read full outer source separately before launch.',
    'small_inputs': list(records.values()), 'outer_source': outer,
    'observed_current_boot_utc_ticks': obs['second']['boot_utc_ticks'],
    'attempts_absent_at_decision': [str(path) for path in attempts],
    'predeclared_cases': [{'name': 'zero', 'child_exit': 0, 'launcher_exit': 0},
                          {'name': 'nonzero17', 'child_exit': 17, 'launcher_exit': 17}],
    'limits': [
        'No scientific environment, model, GPU, B1 body, COM or old suite is invoked. B1 public and private refusal gates stay unchanged.',
        'GPU query has 26 rows and scientific exclusive gate is false; this decision cannot authorize T6 or scientific waiting.',
        'Ordinary existing Visio remains untouched; neither attachment nor cleanup is allowed.',
        'Nt class60 is undocumented/experimental. Current-host test success does not establish general Windows compatibility.',
        'Each inner launcher/interpreter must have independent held identity and actual exit; fixture controller exit is separately held by outer.',
        'The outer record cannot prove its own exit. Actual shell/tool forwarded exit remains a separate limited observation.',
        'Any existing or partial fixture attempt rejects replay; failure preserves all evidence without delete, kill or automatic retry.',
        'This is a control fixture, not six scientific workers or fresh gallery/ranking/parity/timing/onlineCLIP/T6 acceptance.'
    ]}
path = HERE / 'ROOT_BENIGN_FIXTURE_DECISION.json'
with path.open('xb') as stream:
    stream.write((json.dumps(decision, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8'))
print(json.dumps({'decision': bind(path), 'small_bindings': len(decision['small_inputs'])}, ensure_ascii=False))
