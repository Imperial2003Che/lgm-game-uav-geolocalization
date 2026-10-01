"""Root source adoption only. No candidate imports, controls, locks or launches."""
from pathlib import Path
import datetime as dt
import difflib
import hashlib
import json

HERE = Path(__file__).absolute().parent
EX = HERE.parent
REVIEW = EX / 't6_recovery_review_20260929_1548'
OBS = EX / 'efficiency_incident_20260929_1448/observation_20260929_161142806/OBSERVATION.json'
verified = {}
checks = 0

def require(value, label):
    global checks
    checks += 1
    if not value:
        raise AssertionError(label)

def binding(path):
    path = Path(path)
    require(path.suffix.lower() not in {'.pt', '.pth', '.npz', '.npy'}, 'No scientific binary reads')
    require(path.stat().st_size <= 3000000, 'Small files only')
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def verify(item):
    actual = binding(item['path'])
    require(actual == {key: item[key] for key in actual}, 'Binding: ' + actual['path'])
    verified[actual['path']] = actual
    return actual

def read(path, expected=None):
    actual = binding(path)
    if expected:
        require(actual['sha256'] == expected, 'Pinned root input')
    verified[actual['path']] = actual
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def walk(value):
    if isinstance(value, dict):
        if {'path', 'bytes', 'sha256'} <= value.keys():
            verify(value)
        else:
            for child in value.values():
                walk(child)
    elif isinstance(value, list):
        for child in value:
            walk(child)

def diff_values(before, after, path=''):
    if isinstance(before, dict) and isinstance(after, dict):
        result = []
        for key in sorted(before.keys() | after.keys()):
            p = path + '/' + key
            if key not in before:
                result.append({'path': p, 'operation': 'add', 'after': after[key]})
            elif key not in after:
                result.append({'path': p, 'operation': 'remove', 'before': before[key]})
            else:
                result.extend(diff_values(before[key], after[key], p))
        return result
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        return [r for i, (a, b) in enumerate(zip(before, after)) for r in diff_values(a, b, path + '/' + str(i))]
    return [] if before == after else [{'path': path, 'operation': 'replace', 'before': before, 'after': after}]

manifest = read(HERE / 'SOURCE_MANIFEST.json', '8cf084500ae398685ab79d629edb1f9ebffd808e28e605c104d8a93a39c52c41')
prep = read(HERE / 'PREPARATION_REPORT.json', '9ae3709b19ca2e3f96ad0acd8efeeeaa17c09cbab5201fcf2efd2e8ffb6896d4')
delivery = read(HERE / 'DELIVERY.json', '44bdc4ec10cd0b73228ba82ba28bf606069dbc43306e262a2ff8ac652acd6097')
independent = read(REVIEW / 'CANDIDATE_STATIC_REVIEW.json', '17431b2268c7aa920ad32e8a94683e39b51011dc08a2ccbdf6b225b47a0da52b')
contract = read(HERE / 'RECOVERY_CONTRACT.json', '01bf6d97793d0fbcda9936a85b7955b83e336d0c932531eec9f8f33b179b08a3')
controls = read(HERE / 'synthetic_control_a1/REPORT.json', '08ca502a82db4a2e465a72cb627920f4bf2115dcef318004b6ddfcbe1e32b2b2')
observation = read(OBS, '93c69549098ff28976e3ba150934c2b85869799118f9174bb5e798a13be971f3')
for obj in [manifest, prep, delivery, independent, contract, controls, observation]:
    walk(obj)
require(len(manifest['candidate_files']) == 14, 'Fourteen candidate files')
require(len(contract['input_bindings']) == 96, 'Ninety-six bounded input bindings')
require(controls['status'] == 'passed' and controls['checks'] == len(controls['check_names']) == 75, 'New synthetic checks')
require(independent['status'] == 'static_review_no_remaining_definite_blocker_for_source_preparation', 'Independent source finding')
require(independent['actual_execution'] is False and independent['independent_test_execution'] is False, 'Review scope')
require(independent['source_manifest'] == binding(HERE / 'SOURCE_MANIFEST.json'), 'Independent exact manifest')
original = read(HERE / 'captured_pipeline_status.json')
seed = read(HERE / 'pipeline_seed.json')
semantic = read(HERE / 'PIPELINE_STATE_SEMANTIC_DIFF.json')
require((HERE / 'captured_pipeline_status.json').read_bytes() == (EX / 'pipeline_status.json').read_bytes(), 'Original live bytes unchanged')
require(len(original['jobs']) == len(seed['jobs']) == 7, 'Exact seven jobs')
require(original['jobs'][:6] == seed['jobs'][:6], 'Whole first six records unchanged')
require(all(j['status'] == 'completed' and j['exit_code'] == 0 for j in seed['jobs'][:6]), 'First six parent completions only')
require(original['status'] == 'failed' and seed['status'] == 'waiting_for_primary', 'Exact state transition')
require(seed['jobs'][6]['status'] == 'pending', 'Only last stage pending')
require([j['id'] for j in original['jobs']] == [j['id'] for j in seed['jobs']], 'IDs/order unchanged')
for old, new in zip(original['jobs'], seed['jobs']):
    require(old['command'] == new['command'] and old['entrypoint_sha256'] == new['entrypoint_sha256'], 'Command/source unchanged')
    require(binding(old['command'][1])['sha256'] == old['entrypoint_sha256'], 'Current frozen source')
require(diff_values(original, seed) == semantic['changes'], 'Complete semantic diff independently reproduced')
allowed = {'/active_stage','/error','/heartbeat_utc','/jobs/6/exit_code','/jobs/6/finished_utc','/jobs/6/pid','/jobs/6/started_utc','/jobs/6/status','/recovery_preparation','/status','/stopped_utc','/supervisor_pid','/supervisor_started_utc'}
require({r['path'] for r in semantic['changes']} == allowed, 'Exact permitted mutation set in preparation only')
for old, new, patch in [
    (HERE/'rejected_pre_review_v1/pipeline_recovery_candidate.py', HERE/'pipeline_recovery_candidate.py', HERE/'PRE_REVIEW_TO_FINAL_SOURCE_DIFF.patch'),
    (HERE/'rejected_pre_review_v1/prepare_contract_failed_path.py', HERE/'prepare_contract.py', HERE/'PREPARE_CONTRACT_PATH_CORRECTION.patch')]:
    rebuilt = ''.join(difflib.unified_diff(old.read_text(encoding='utf-8').splitlines(True), new.read_text(encoding='utf-8').splitlines(True), fromfile=str(old), tofile=str(new)))
    require(patch.read_text(encoding='utf-8') == rebuilt, 'Complete source diff reproduced')
    verified[str(old)] = binding(old)
state_diff = ''.join(difflib.unified_diff((HERE/'captured_pipeline_status.json').read_bytes().decode('utf-8-sig').splitlines(True), (HERE/'pipeline_seed.json').read_bytes().decode('utf-8').splitlines(True), fromfile='captured original failed pipeline_status.json', tofile='preparation-only pipeline_seed.json'))
require((HERE/'PIPELINE_STATE_DERIVATION.patch').read_bytes() == state_diff.encode('utf-8'), 'Exact state serialization diff')
syntax = read(HERE / 'POWERSHELL_SYNTAX.json')
require(syntax['errors'] == 0 and syntax['real_launch'] is False, 'Syntax parse only')
require(observation['first_CIM']['records'] == observation['second_CIM']['records'] == [], 'Latest two observed absence scans')
require(observation['gpu_process_rows'] == 21 and observation['original_gpu_exclusive_gate_would_be_satisfied'] is False, 'Existing gate not satisfied')
require(observation['t6_output_exists'] is False, 'No measured T6 output')
require(not (EX/'latest_baseline_gpu.lock').exists(), 'Missing shared lock remains explicit')
require(not (HERE/'runtime_attempt').exists(), 'No actual one-use attempt created')
require(not (HERE/'release.json').exists(), 'No real root release')
report = {
    'schema': 't6-pipeline-recovery-source-adoption.v1',
    'created_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
    'status': 'source_preparation_adopted_no_execution_release',
    'source_manifest': binding(HERE/'SOURCE_MANIFEST.json'),
    'approved_for_future_gated_execution': True,
    'execution_released': False,
    'scope': 'Only original pipeline stage7; first six complete records preserved; primary/successors untouched',
    'independent_review': binding(REVIEW/'CANDIDATE_STATIC_REVIEW.json'),
    'preparation_report': binding(HERE/'PREPARATION_REPORT.json'),
    'author_delivery': binding(HERE/'DELIVERY.json'),
    'new_synthetic_controls': binding(HERE/'synthetic_control_a1/REPORT.json'),
    'root_source': binding(Path(__file__).absolute()),
    'latest_actual_readonly_observation': binding(OBS),
    'root_checks': checks,
    'unique_bound_files': len(verified),
    'bindings': list(verified.values()),
    'root_read_scope': ['Entire final candidate and original supervisor/native/gate/lock contracts', 'Complete source changes, PowerShell/preparation/checker/sealer/readme/independent source/report', 'Independent exact source/state diff reconstruction and final artifact input bindings'],
    'actual_execution_this_review': False,
    'independent_controls_rerun': False,
    'scientific_artifacts_or_weights_rehashed': False,
    'remaining_execution_prerequisites': ['Separately reviewed shared persistent lock initialization; currently absent', 'Fresh root execution release bound to this adoption and actual incident/state', 'Unchanged original GPU gate, 26 GiB admission, owner absence, locks, native imports and final CAS/source/release/boot gates'],
    'limits': independent['candidate_specific_limitations'] + contract['limits'] + ['Seventy-five author synthetic checks are bound, not rerun and not actual Windows execution evidence', 'Source acceptance permits only a future separately released and gated action, not launch now or scientific acceptance', 'Old primary exit unknown and old failed attempt/logs retained; no successor release or all-five completion claim']
}
with (HERE/'ROOT_SOURCE_ADOPTION.json').open('x', encoding='utf-8', newline='\n') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
    f.write('\n')
print(json.dumps({'report': binding(HERE/'ROOT_SOURCE_ADOPTION.json'), 'checks': checks, 'unique_files':len(verified)}, ensure_ascii=False))
