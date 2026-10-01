"""New limited binding/count/observer-scope edges; never rerun runtime checks."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EX = HERE.parent
RUN = EX / 'newer_native_process_execution_v2_20260930_0820'
POST = EX / 'process_fixture_after_v2_20260930_0840'
inputs = {}
checks = []

def check(condition, description):
    checks.append({'check': description, 'passed': bool(condition)})
    assert condition, description

def bind(path, limit=100000):
    path = Path(path)
    check(path.stat().st_size < limit, 'Bounded new scope/binding file ' + path.name)
    with path.open('rb') as stream:
        raw = stream.read(limit)
    check(len(raw) < limit, 'Bounded read ' + path.name)
    item = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    inputs[str(path)] = item
    return item, raw

def load(path):
    return json.loads(bind(path)[1])

report = load(HERE / 'RUNTIME_REVIEW.json')
delivery = load(HERE / 'DELIVERY.json')
input_table = load(HERE / 'INPUT_BINDINGS.json')
check(report['check_count'] == 1877 and report['unique_input_count'] == 198,
      'Core report contains 1877 sealed diagnostics and 198 input records')
check(len(input_table['files']) == 198, 'Actual input table has 198 unique records')
check(len({item['path'] for item in input_table['files']}) == 198, 'Input table paths unique')
check(bind(delivery['source']['path'])[0] == delivery['source'], 'Separate delivery source binding is exact')
check(delivery['source']['path'] not in {item['path'] for item in input_table['files']},
      'Final delivery source is one additional bound input, giving console 199')
old = bind(HERE / 'REVIEW_PREPARED_BEFORE_FILENAME_FIX.py.txt')[1]
new = bind(HERE / 'review_runtime.py')[1]
patch = bind(HERE / 'REVIEW_PREEXEC_FIX.patch')[1]
expected = b''.join(difflib.diff_bytes(difflib.unified_diff, old.splitlines(keepends=True), new.splitlines(keepends=True),
                                   fromfile=b'prepared/review_runtime.py', tofile=b'first_runtime/review_runtime.py'))
check(patch == expected, 'Complete byte diff preserves preparation-to-first-execution source changes')
bind(HERE / 'PLAN.md')
decision, raw_decision = bind(RUN / 'ROOT_BENIGN_FIXTURE_DECISION.json')
entry = load(RUN / 'outer_runtime_attempt_v1/entry.json')
outer_report = load(RUN / 'outer_runtime_attempt_v1/CONTROLLER_EXIT_AND_CLOSED_LOGS.json')
check(entry['decision'] == decision == outer_report['decision'], 'Runtime entry and completed controller report bind exact actual root decision bytes')
check(bind(entry['source']['path'])[0] == entry['source'], 'Actual runtime outer entry source binding agrees with current reviewed exact bytes')
check(entry['scientific_admission'] is False and entry['self_exit_unknown'] is True,
      'Actual entry is benign-only and does not prove outer own exit')
obs = load(POST / 'OBSERVATION_WRAPPER_INCLUDED.json')
observer, observer_raw = bind(POST / 'observe_after_v2.ps1')
check(obs['source'] == observer, 'Actual post observation binds exact observer source')
observer_text = observer_raw.decode('utf-8')
for pid in [17896, 13180, 19432, 10068, 3816, 17112]:
    check(str(pid) in observer_text, 'Actual post filter includes new CPU actor numeric PID ' + str(pid))
check('benign_fixture|run_outer' in observer_text and "Get-CimInstance Win32_Process" in observer_text,
      'Actual saved post source independently includes broad fixture/outer command matches')
actual_exit_ns = (report['fixture_controller_actual_held_exit_captured_by_outer']['exit_filetime_100ns'] - 116444736000000000) * 100
for which in ['first', 'second']:
    # ISO at microsecond precision suffices for this separated ~109 second observation.
    observed = datetime.fromisoformat(obs[which]['observed_utc'].replace('Z', '+00:00'))
    check(int(observed.timestamp() * 1000000000) > actual_exit_ns,
          'Saved root double OS observation actually occurred after fixture controller exit ' + which)
    check(not any(row['pid'] in [17896, 13180, 19432, 10068, 3816, 17112] for row in obs[which]['matches']),
          'Saved post scan contains none of actual new actor numeric PIDs ' + which)
check(obs['contract_boot_matches_current'] is False and obs['contract_boot_utc_ticks'] == '639262263395000000',
      'Observer false boot comparison remains historical Sep29 contract, not current 0405 authority failure')
bind(__file__)
value = {
    'schema': 'independent-v2-runtime-scope-and-binding-addendum.v1',
    'reviewed_utc': datetime.now(timezone.utc).isoformat(),
    'joins_without_modifying': [bind(HERE / 'RUNTIME_REVIEW.json')[0], bind(HERE / 'DELIVERY.json')[0]],
    'scope': 'Additional new root-decision/entry/source/observer edges and count explanation only; completed 1877 runtime diagnostics never rerun',
    'report_diagnostic_count': 1877, 'console_total_checks_including_later_source_binding': 1879,
    'report_input_binding_count': 198, 'console_unique_bound_paths_including_delivery_source': 199,
    'actual_additional_checks': checks, 'inputs': list(inputs.values()),
    'reviewer_executed_producer_or_winapi_or_os_query': False,
    'runtime_fixture_replayed': False, 'scientific_execution_or_admission': False,
    'limits': [
        'Saved root double CIM observation is absence evidence in its actual source filter, not actual historical exit proof or a reviewer reobservation.',
        'Root observer kept historical Sep29 contract comparison. Both actual post snapshots match current boot 639263337875000000.',
        'Outer tool forwarded exit0 remains separate from independently held fixture-controller exit0; no independent held outer own exit is supplied.',
        'The count difference occurs when delivery separately checks and binds reviewer source after sealing diagnostic/input tables; no extra runtime case ran.',
        'The original prepared reviewer source and complete two-change byte diff remain. First actual runtime review succeeded; no failed runtime checker or review suite replay occurred.'
    ]}
target = HERE / 'RUNTIME_SCOPE_AND_BINDING_ADDENDUM.json'
raw = (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode('utf-8')
with target.open('xb') as stream:
    stream.write(raw)
print(json.dumps({'path': str(target), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                  'checks': len(checks), 'inputs': len(inputs)}, ensure_ascii=False))
