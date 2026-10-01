"""Root diagnosis adoption only; never rerun fixture or assume exit from absence."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
EX = HERE.parent
SRC = EX / 'external_efficiency_preparation/newer_native_process_evidence_v1'
INNER = SRC / 'runtime_attempt_v1'
OUTER = HERE / 'outer_runtime_attempt_v1'
REVIEW = EX / 'newer_native_process_runtime_review_20260930_0758'
records = {}

def bind(path):
    path = Path(path)
    assert path.stat().st_size < 100000
    raw = path.read_bytes()
    item = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    records[str(path)] = item
    return item

def read(path):
    bind(path)
    return json.loads(Path(path).read_bytes())

def check(item):
    assert bind(item['path']) == item, item['path']

decision = read(HERE / 'ROOT_BENIGN_FIXTURE_DECISION.json')
assert decision['scientific_admission'] is False and decision['execute'] is True
for item in decision['small_inputs']:
    check(item)
check(decision['outer_source'])
assert bind(HERE / 'ROOT_BENIGN_FIXTURE_DECISION.json')['sha256'] == 'e5c27646b1c5564f983599e5eacc767280a51678bae043f5af284b493391bbc4'
tool = read(HERE / 'TOOL_EXECUTION_RECEIPT.json')
assert tool['captured_tool_result']['exit_code'] == 92
failure = read(OUTER / 'OUTER_FAILURE.json')
assert failure['error'] == "EvidenceError('QueryFullProcessImageNameW: WinError 31')"
assert failure['held_exits'] == [None, None]
cleanup = read(OUTER / 'OUTER_RETURN_INTENT_AND_CLEANUP.json')
assert cleanup['return_intent'] == 92 and cleanup['cleanup_errors'] == []
assert cleanup['own_actual_exit_unknown'] is True
assert not (OUTER / 'CONTROLLER_EXIT_AND_CLOSED_LOGS.json').exists()
assert not (INNER / 'nonzero17').exists() and not (INNER / 'return_intent.json').exists()
assert not (INNER / 'zero/result.json').exists()
assert read(INNER / 'zero/child.task.json') == {'task': 'sum_squares_0_through_999', 'value': 332833500}
raw_run = []
for directory in [INNER, OUTER]:
    for path in sorted(directory.rglob('*')):
        if path.is_file():
            raw_run.append(bind(path))
events = [read(item['path']) for item in raw_run if item['path'].endswith('.json')
          and 'event' in json.loads(Path(item['path']).read_bytes())]
assert not any(event['event'] == 'exit_observed' for event in events)
signaled = [event for event in events if event['event'] == 'wait_result' and event['result'] == 0]
assert len(signaled) == 3
failed_review = read(REVIEW / 'FAILED_RUNTIME_REVIEW.json')
assert failed_review['fixture_passed'] is False
for item in failed_review['inputs']:
    check(item)
failed_delivery = read(REVIEW / 'FAILED_RUNTIME_DELIVERY.json')
for key in ['review', 'observer_filter_diff', 'source']:
    check(failed_delivery[key])
bind(REVIEW / 'REVIEW_SEALER_V1_FAILURE.json')
bind(REVIEW / 'seal_failed_runtime_review.py')
after_path = EX / 'process_fixture_after_failure_20260930_0814/OBSERVATION_WRAPPER_INCLUDED.json'
after = read(after_path)
for which in ['first', 'second']:
    assert after[which]['boot_utc_ticks'] == '639263337875000000'
    assert len(after[which]['matches']) == 1 and after[which]['matches'][0]['name'] == 'VISIO.EXE'
for item in after['files']:
    check(item)
check({key: after['carrier'][key] for key in ['path', 'bytes', 'sha256']})
assert Path(after['carrier']['path']).read_bytes() == b'0'
bind(__file__)
report = {
    'schema': 'root-failed-benign-process-control-adoption.v1',
    'adopted_utc': datetime.now(timezone.utc).isoformat(),
    'diagnosis_adopted': True, 'fixture_passed': False, 'runtime_validated': False,
    'scientific_admission': False, 'scientific_result_count': 0, 'new_figures': 0,
    'reviewer': 'Root AI; independent AI saved-runtime review separately bound',
    'source': bind(__file__), 'inputs': list(records.values()),
    'runtime_file_count': len(raw_run), 'signaled_records': signaled,
    'partial_benign_task': {'case': 'zero', 'after_bound_ack': True, 'sum_squares': 332833500},
    'failure': failure, 'cleanup_record': cleanup,
    'preserved_attempts': [str(INNER), str(OUTER)], 'replay_authorized': False,
    'limits': [
        'Three retained waits returned WAIT_OBJECT_0 but all failed at post-exit image query. No saved actual DWORD exit or actual exit FILETIME exists in v1.',
        'No complete case result or controller closed-log seal exists. Cleanup records do not replace dual held exit evidence.',
        'The zero child task and identity ACK were actually written. The planned nonzero17 branch was never started.',
        'Tool exit92 forwards the outer caller only; it is not a saved child, launcher or fixture-controller exit code.',
        'Saved after-failure double CIM has no fixture owner matches; absence cannot recover missing exit values.',
        'All runtime file digests here are preserved diagnostic bytes, not the rejected held-exit/closed-writer log seal.',
        'Future repaired source requires a new directory, independent review and separate root execution decision; v1 is never replayed.',
        'No scientific imports, GPU, original venv, B1 body, COM, locks, scientific release/intent/state mutation or scientific result occurred.'
    ]}
target = HERE / 'ROOT_FAILED_CONTROL_ADOPTION.json'
with target.open('xb') as stream:
    stream.write((json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8'))
print(json.dumps({'adoption': bind(target), 'unique_small_bindings': len(records)}, ensure_ascii=False))
