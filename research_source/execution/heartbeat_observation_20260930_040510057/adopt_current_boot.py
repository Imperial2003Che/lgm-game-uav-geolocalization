"""Adopt this turn's saved reboot observation; no launch or process control."""
from pathlib import Path
import datetime, hashlib, json

HERE = Path(__file__).parent
EX = HERE.parent
bindings = {}
checks = []

def bind(path, expected=None):
    path = Path(path)
    assert path.stat().st_size < 500000, str(path)
    data = path.read_bytes()
    rec = dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    if expected:
        assert all(rec[k] == expected[k] for k in ('bytes', 'sha256')), str(path)
    bindings[str(path)] = rec
    return rec

def read(path, sha):
    rec = bind(path)
    assert rec['sha256'] == sha, str(path)
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def check(ok, label):
    assert ok, label
    checks.append(label)

obs = read(HERE/'OBSERVATION_WRAPPER_INCLUDED.json', '46543c4e92245872f50aa1016ff09afb20d4197a05b872abe3c454837956615b')
stop = read(EX/'efficiency_incident_20260929_1448/observation_20260930_040511476/OBSERVATION.json', '42422ac8b18e948b857478668c53c885847eb59be91f8dea08fce47ea25ec586')
review = read(EX/'heartbeat_boot_review_20260930_0405/OBSERVATION_REVIEW.json', '45ebcb84a5ce522c1595f2857b28979a3f5b629dd68c61ee3216d00483867394')
prior = read(EX/'t6_recovery_preparation_20260930_0104/RECOVERY_CONTRACT.json', 'd0aa27edfc5391689a947dc7a572d38a9a150186672c7d10965715f12e36d136')
prior_root = read(EX/'t6_recovery_preparation_20260930_0104/ROOT_SOURCE_ADOPTION.json', 'fff6965e4d794902105f578cadb4680f363c7d6d31dcfd0a29bd3e636ea09343')
for b in review['bindings']:
    bind(b['path'], b)
check(review['accepted_observation_scope'] is True and len(review['checks']) == 42, 'Independent focused saved-observation review accepted')
check(prior_root['execution_released'] is False, 'Prior source adoption released no execution')
check(prior['host_boot_utc_ticks'] == '639263179115000000', 'Immediate prior contract boot retained as history')
check(obs['first']['boot_utc_ticks'] == obs['second']['boot_utc_ticks'] == review['new_boot_utc_ticks'] == '639263337875000000', 'Both saved broad scans agree with independently reviewed new boot')
check(stop['host_boot_utc'] == '2026-09-30T02:56:27.5000000+00:00', 'Narrow observer agrees on exact new boot time')
check(len(obs['files']) == 16 and all(s['unchanged_since_incident'] for s in stop['states']), 'Sixteen state/log bindings and five saved state heartbeats unchanged')
for b in obs['files']:
    bind(b['path'], b)
for phase in ('first', 'second'):
    matches = obs[phase]['matches']
    check(len(matches) == 1 and matches[0]['name'] == 'VISIO.EXE', phase + ': no science pattern match; one existing Visio')
    v = matches[0]
    check(v['pid'] == 29480 and v['creation_utc_ticks'] == '639263338233256210' and v['parent_pid'] == 13076, phase + ': exact saved Visio identity')
    check(v['command_line'] == '"C:\\Program Files\\Microsoft Office\\root\\Office16\\VISIO.EXE" ', phase + ': ordinary full Visio command retained')
    p = v['parent_current_observation']
    check(len(p) == 1 and p[0]['name'] == 'explorer.exe' and p[0]['creation_utc_ticks'] == '639263338065379830', phase + ': current parent-number observation retained without ownership inference')
check(stop['gpu_query_exit_code'] == 0 and stop['gpu_process_rows'] == 23 and stop['original_gpu_exclusive_gate_would_be_satisfied'] is False, 'Saved successful GPU query is nonempty; execution not admitted')
check(not stop['first_CIM']['records'] and not stop['second_CIM']['records'], 'Two narrower saved CIM scans empty, no exit code inferred')
carrier = obs['carrier']
bind(carrier['path'], carrier)
check(Path(carrier['path']).read_bytes() == b'0' and carrier['creation_utc_ticks'] == '639262940518466959', 'Persistent carrier unchanged; no held lock claimed')
attempts = []
for dirname in ('t6_recovery_preparation_20260929_1548', 't6_recovery_preparation_20260930_0104', 't6_recovery_preparation_20260930_0405'):
    path = EX/dirname/'runtime_attempt'
    check(not path.exists(), dirname + ': runtime attempt absent at root check')
    attempts.append(str(path))
visio_attempt = EX.parent/'transfer_native_visio_candidate_20260930_0104/runtime_attempt_v1'
check(not visio_attempt.exists(), 'Visio candidate runtime attempt absent')
t6 = Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\analysis\transactions_t6_formal')
check(not t6.exists(), 'T6 measurement output still absent')
bind(__file__)
report = {
    'schema': 'root-post-stopped-new-boot-observation-adoption.v1',
    'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'new_boot_ticks': '639263337875000000',
    'new_boot_utc': '2026-09-30T02:56:27.5000000Z',
    'previous_boot_ticks': '639263179115000000',
    'original_incident_boot_ticks': '639262263395000000',
    'old_boot_contract_valid_for_current_boot': False,
    'adopted_observation_only': True,
    'accepted_with_stated_limits': True,
    'execution_released': False,
    'cleanup_authorized': False,
    'new_scientific_failure_inferred': False,
    'independent_exit_code_inferred': False,
    'current_unowned_visio': obs['second']['matches'][0],
    't6_runtime_attempts_checked_absent': attempts,
    'visio_runtime_attempt_checked_absent': str(visio_attempt),
    'checks': checks,
    'bindings': list(bindings.values()),
    'method': 'Root AI read both observer sources, both complete saved observations and independent source/report; focused small-file byte bindings. No repeated science or historical control suites.',
    'limits': [
        'This saved snapshot is not future admission; resources remain unavailable under the frozen empty-GPU rule.',
        'A separate source contract bound to this boot must preserve the original stage-seven command, first six completed records, source and log prefixes, three admission checks, native probe, six byte locks, fifteen-minute release and captured child exits.',
        'Future root admission must check all three attempt directories; each unchanged guardian directly checks only its own directory.',
        'Current Visio is not task-owned; no attach, Quit, Kill or cleanup authority. Current parent-number observation is not historical parent identity proof.',
        'Previous AppActions 14420 and Visio 14932 absence is not captured exit evidence or retroactive ownership.',
        'Scientific work was already stopped before this reboot; unchanged state/log bytes do not supply missing independent process exits.',
        'No release, intent, native training probe, COM, recovery, byte-lock acquisition or live state mutation. No weights, model, cache, images, old large ZIP or scientific/control suites were read or executed.'
    ]
}
target = HERE/'ROOT_BOOT_OBSERVATION_ADOPTION.json'
with target.open('x', encoding='utf-8', newline='\n') as f:
    f.write(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'root': bind(target), 'checks': len(checks), 'bindings': len(report['bindings'])}, ensure_ascii=False))
