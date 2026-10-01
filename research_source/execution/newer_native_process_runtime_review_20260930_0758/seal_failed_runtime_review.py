"""Independent saved-evidence failure review only; no candidate import/process/API/science calls."""
import datetime
import difflib
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
EX = HERE.parent
SRC = EX / 'external_efficiency_preparation' / 'newer_native_process_evidence_v1'
INNER = SRC / 'runtime_attempt_v1'
OUTER = EX / 'newer_native_process_execution_20260930_0810'
ATTEMPT = OUTER / 'outer_runtime_attempt_v1'
AFTER = EX / 'process_fixture_after_failure_20260930_0814'
PYTHON = r'C:\Users\17703\AppData\Local\Programs\Python\Python311\python.exe'
OFFSET = 504911232000000000
bindings = {}
raws = {}
checks = []

def check(value, text):
    if not value:
        raise AssertionError(text)
    checks.append(text)

def raw(path):
    path = Path(path)
    key = str(path)
    if key not in raws:
        before = path.stat()
        check(0 <= before.st_size < 100000, 'bounded small saved input ' + path.name)
        with path.open('rb') as stream:
            value = stream.read(100000)
        after = path.stat()
        check((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns) and len(value) == before.st_size,
              'saved input unchanged during read ' + path.name)
        raws[key] = value
        bindings[key] = {'path': key, 'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()}
    return raws[key]

def doc(path):
    return json.loads(raw(path))

def ledger(folder, actor):
    paths = sorted(folder.glob(actor + '_*.json'))
    records = [doc(path) for path in paths]
    check([int(path.name.split('_')[1]) for path in paths] == list(range(1, len(paths) + 1)), actor + ' saved ledger indices contiguous')
    check(all(record['actor'] == actor and type(record['utc_ns']) is int for record in records), actor + ' saved event actor/integer clock')
    check([record['utc_ns'] for record in records] == sorted(record['utc_ns'] for record in records), actor + ' saved event ordering')
    return records

def events(records, event, label=None):
    return [r for r in records if r['event'] == event and (label is None or r.get('label') == label)]

def unique(records, event, label=None):
    rows = events(records, event, label)
    check(len(rows) == 1, 'unique saved ' + event + '/' + str(label))
    return rows[0]

outer = ledger(ATTEMPT, 'outer')
parent = ledger(INNER, 'parent')
controller = ledger(INNER / 'zero', 'controller')
launcher = ledger(INNER / 'zero', 'launcher')
child = ledger(INNER / 'zero', 'child')
all_events = outer + parent + controller + launcher + child
holds = [r for r in all_events if r['event'] == 'held_open']
check(len(holds) == 8, 'eight recorded independently opened evidence handles across actors')
for hold in holds:
    ident = hold['identity']
    check(hold['access_mask'] == 0x101000, 'recorded limited-query/synchronize access ' + hold['label'])
    check(type(ident['pid']) is int and type(ident['creation_filetime_100ns']) is int and type(ident['creation_utc_ticks']) is int,
          'integer held PID/creation fields ' + hold['label'])
    check(ident['creation_utc_ticks'] == ident['creation_filetime_100ns'] + OFFSET and ident['image'] == PYTHON,
          'integer epoch and captured kernel image ' + hold['label'])

outer_id = unique(outer, 'held_open', 'outer_self')['identity']
controller_id = unique(outer, 'held_open', 'fixture_controller_external')['identity']
launcher_id = unique(controller, 'held_open', 'launcher_external')['identity']
child_id = unique(controller, 'held_open', 'child_external')['identity']
check(unique(parent, 'held_open', 'controller_self')['identity'] == controller_id, 'controller self and external creation identity agree')
check(unique(launcher, 'held_open', 'launcher_self')['identity'] == launcher_id, 'launcher self and external creation identity agree')
check(unique(child, 'held_open', 'child_self')['identity'] == child_id, 'child self and external creation identity agree')
check(unique(launcher, 'held_open', 'child_launcher_observer')['identity'] == child_id, 'supplementary launcher child identity agrees')
check(len({i['pid'] for i in (outer_id, controller_id, launcher_id, child_id)}) == 4, 'four distinct saved actor PID identities')

def confirm(records, label, ident, parent_ident, argv):
    confirmed = unique(records, 'confirmed', label)
    rows = confirmed['observations']
    check(len(rows) == 2 and rows[0] == rows[1], label + ' two identical complete saved observations')
    gates = events(records, 'confirmation_gate', label)
    check([g['index'] for g in gates] == [0, 1], label + ' two saved confirmation gates')
    check(len(events(records, 'candidate_snapshot', label)) >= 2, label + ' at least the two complete candidate snapshots retained; parent rechecks may add more')
    cmd = subprocess.list2cmdline(argv)  # Formatting only; no process is launched.
    for index, observation in enumerate(rows):
        got_id = {k: observation[k] for k in ('pid', 'creation_filetime_100ns', 'creation_utc_ticks', 'image')}
        check(got_id == observation['fresh_after'] == observation['held_now'] == ident, label + ' captured fresh/held creation agreement ' + str(index))
        check(observation['command_line'] == cmd and observation['parent_pid'] == parent_ident['pid'], label + ' complete captured command/current parent ' + str(index))
        check(observation['creation_utc_ticks'] >= parent_ident['creation_utc_ticks'], label + ' captured child does not predate held parent ' + str(index))
        check(gates[index]['observed'] == observation and gates[index]['expected_parent'] == parent_ident and gates[index]['expected_command'] == cmd,
              label + ' gate record agrees with complete observation ' + str(index))
    return confirmed

fixture = str(SRC / 'benign_fixture.py')
common = [PYTHON, '-I', '-S', '-B', fixture]
controller_confirmed = confirm(outer, 'fixture_controller_external', controller_id, outer_id, common + ['--execute-benign-fixture'])
launcher_confirmed = confirm(controller, 'launcher_external', launcher_id, controller_id,
                             common + ['--role', 'launcher', '--case', str(INNER / 'zero'), '--execute-benign-fixture'])
child_confirmed = confirm(controller, 'child_external', child_id, launcher_id,
                          common + ['--role', 'child', '--case', str(INNER / 'zero'), '--execute-benign-fixture'])
for record in events(all_events, 'nt_command_result'):
    check(record['status'] == 0 and 16 <= record['returned_bytes'] <= record['capacity'] <= 1048576,
          'actual saved Nt class60 success/bounded result ' + record['actor'] + '/' + record['label'])

request_path = INNER / 'zero' / 'request.json'
request = doc(request_path)
check(request['name'] == 'zero' and request['child_exit'] == request['launcher_exit'] == 0 and request['scientific_execution'] is False,
      'only zero branch request created with scientific false')
request_sha = hashlib.sha256(raw(request_path)).hexdigest()
for role, identity in (('launcher', launcher_id), ('child', child_id)):
    ack = doc(INNER / 'zero' / (role + '.ack.json'))
    ready = doc(INNER / 'zero' / (role + '.ready.json'))
    check(ack['role'] == role and ack['identity'] == identity and ack['request_sha256'] == request_sha,
          role + ' exact request SHA and held identity ACK')
    check(ready['pid'] == identity['pid'] and ready['identity'] == identity, role + ' self-ready agrees with external held identity')
task = doc(INNER / 'zero' / 'child.task.json')
ack_event = unique(child, 'ack_received_before_fixture_task')
check(task == {'task': 'sum_squares_0_through_999', 'value': 332833500}, 'saved benign CPU task exact result')
check(ack_event['utc_ns'] > child_confirmed['utc_ns'], 'child saved ACK event follows both captured complete confirmations')
check((INNER / 'zero' / 'child.task.json').stat().st_mtime_ns >= ack_event['utc_ns'], 'task file modification time corroborates ACK-before-task source order')
check('intended exit 0' in raw(INNER / 'zero' / 'child.stdout.log').decode('utf-8'), 'child stdout preserves intention zero only')

waits = events(all_events, 'wait_result')
check(len(waits) == 3 and all(r['result'] == 0 for r in waits), 'three saved WAIT_OBJECT_0 records')
check([(r['actor'], r['label']) for r in waits] == [('outer', 'fixture_controller_external'), ('controller', 'launcher_external'), ('launcher', 'child_launcher_observer')],
      'signaled waits concern controller, launcher, and supplementary child observer; external child wait not reached')
check(not events(all_events, 'exit_observed'), 'no complete held exit observation was recorded')
check(not (INNER / 'zero' / 'result.json').exists() and not (INNER / 'return_intent.json').exists(), 'zero result and parent completion return record absent')
check(not (INNER / 'nonzero17').exists(), 'nonzero17 directory never created')
check(not (ATTEMPT / 'CONTROLLER_EXIT_AND_CLOSED_LOGS.json').exists(), 'outer completed controller-exit/closed-log seal absent')
for records in (controller, launcher, parent):
    fail = unique(records, 'failure')
    check('QueryFullProcessImageNameW: WinError 31' in fail['error'] and 'kernel_identity' in fail['traceback'], 'saved failure reaches post-signaled kernel_identity image query ' + fail['actor'])
outer_failure = doc(ATTEMPT / 'OUTER_FAILURE.json')
check(outer_failure['error'] == "EvidenceError('QueryFullProcessImageNameW: WinError 31')" and outer_failure['held_exits'] == [None, None],
      'outer failure has no completed exit-code/time evidence')
check(unique(controller, 'failure')['actual_exit_evidence'] == [None, None] and unique(parent, 'failure')['preserved_completed_case_count'] == 0,
      'controller saved no pair of exit records and parent completed no case')
check(unique(launcher, 'failure')['utc_ns'] < unique(controller, 'failure')['utc_ns'] < unique(parent, 'failure')['utc_ns'] < waits[0]['utc_ns'],
      'saved causal failure order launcher then controller then parent then outer wait')
for records in (child, launcher, controller, parent):
    cleanup = unique(records, 'cleanup_complete')
    check(cleanup['errors'] == [] and all(cleanup['own_stream_closed']) and cleanup['no_termination'] is True,
          'saved cleanup record reports no error and own streams closed ' + cleanup['actor'])
    check(all(exit_record is None for exit_record in cleanup['exits']), 'cleanup does not manufacture actual exits ' + cleanup['actor'])
    check(all(row['exit_observed'] is False for row in events(records, 'held_closed')), 'recorded handle release has no completed exit proof ' + cleanup['actor'])
cleanup = doc(ATTEMPT / 'OUTER_RETURN_INTENT_AND_CLEANUP.json')
check(cleanup['return_intent'] == 92 and cleanup['cleanup_errors'] == [] and cleanup['own_redirect_streams_closed'] is True and cleanup['evidence_handles_closed'] is True,
      'outer saved return92/cleanup records true closure status without completed exit acceptance')
tool = doc(OUTER / 'TOOL_EXECUTION_RECEIPT.json')
check(tool['captured_tool_result']['exit_code'] == 92 and tool['scientific_execution'] is False and tool['replay_authorized'] is False,
      'forwarded tool result concerns failed outer exit92 only')
check(' -I -S -B -X utf8 ' in tool['executed_command'] and '--execute-one-benign-fixture' in tool['executed_command'],
      'saved tool transcript declares isolated ordinary Python one fixture')

observation = doc(AFTER / 'OBSERVATION_WRAPPER_INCLUDED.json')
observer_path = AFTER / 'observe_fixture_after.ps1'
prior_path = AFTER / 'OBSERVER_PRIOR.ps1.txt'
observer_raw = raw(observer_path)
prior_raw = raw(prior_path)
expected = prior_raw.replace(b'40968,23920)', b'40968,23920,10292,8528,17840,1396)').replace(b'run_independent|resume_formal)', b'run_independent|resume_formal|benign_fixture|run_outer)')
check(observer_raw == expected, 'after-observer source differs only by four fixture IDs and fixture/outer command filter')
check(bindings[str(observer_path)] == observation['source'], 'captured after-observer source binding agrees')
for phase in ('first', 'second'):
    snap = observation[phase]
    check(snap['boot_utc_ticks'] == '639263337875000000', 'saved after-observer same current boot ' + phase)
    check(len(snap['matches']) == 1 and snap['matches'][0]['pid'] == 29480 and snap['matches'][0]['name'] == 'VISIO.EXE',
          'saved after-observer finds only ordinary Visio ' + phase)
    check(snap['matches'][0]['creation_utc_ticks'] == '639263338233256210' and snap['matches'][0]['parent_pid'] == 13076,
          'saved ordinary Visio identity unchanged ' + phase)
check(len(observation['files']) == 16 and observation['carrier']['byte_values'] == [48], 'saved after-observer reports16 prior state/log bytes and persistent b0 carrier')
check(observation['contract_boot_matches_current'] is False and observation['contract_boot_utc_ticks'] == '639262263395000000',
      'observer false contract match refers old Sep29 boot, not current0405 source contract')
observer_diff = ''.join(difflib.unified_diff(prior_raw.decode('utf-8').splitlines(True), observer_raw.decode('utf-8').splitlines(True),
                                         fromfile='OBSERVER_PRIOR.ps1.txt', tofile='observe_fixture_after.ps1'))

# Bind only actual preserved small controls/logs after the failed outer completed.
# These reviewer snapshots are not the missing producer closed-log seals.
for folder in (ATTEMPT, INNER):
    for path in sorted(folder.rglob('*')):
        if path.is_file():
            raw(path)
source_pins = {'windows_process_evidence.py': 'b21c05e40ec721b343a376e95ba10ae590288ce3eecb33b7238fcf58a16ed023',
               'benign_fixture.py': '05379eda9addbac90faea33d73eb9a0faa4fc59450bf65e3e1f11de677fca50f'}
for name, expected_sha in source_pins.items():
    raw(SRC / name)
    check(bindings[str(SRC / name)]['sha256'] == expected_sha, 'frozen v1 source exact bytes remain ' + name)
for path in (OUTER / 'run_outer.py', OUTER / 'ROOT_BENIGN_FIXTURE_DECISION.json',
             HERE / 'OUTER_SOURCE_REVIEW.json', SRC / 'SOURCE_MANIFEST.json',
             EX / 'newer_native_process_evidence_review_20260930_0707' / 'REVIEW.json', Path(__file__)):
    raw(path)
report = {
    'schema': 'independent-benign-process-fixture-failed-runtime-review.v1',
    'reviewed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'reviewer': 'Independent AI agent /root/process_runtime_review_0758; no human review',
    'decision': 'FAILED runtime fixture. Saved partial evidence is accepted only as bounded failure diagnosis; neither branch has complete exit-and-closed-log acceptance.',
    'fixture_passed': False, 'scientific_admission': False, 'execution_released': False,
    'fixture_or_helper_executed_by_reviewer': False, 'windows_api_called_by_reviewer': False,
    'method': 'AI text inspection plus new saved-runtime JSON, exact command/creation/ACK/order and small-byte binding checks. No existing static checker or old control/scientific suite rerun.',
    'recorded_identities': {'outer': outer_id, 'controller': controller_id, 'launcher': launcher_id, 'child': child_id},
    'partial_accepted_scope': {
        'full_confirmations': 'Three actor identities were each captured twice with full command/image and current parent number plus held parent creation identity before failure. This is not complete historical parentage.',
        'nt_class60': 'Actual saved size/result/candidate records show current-host success for live captures only; no stable public API contract or other-host support inferred.',
        'ack': {'request_sha256': request_sha, 'launcher_ack_identity': launcher_id, 'child_ack_identity': child_id,
                'child_ack_event_utc_ns': ack_event['utc_ns'], 'task': task,
                'scope': 'Source gating, exact ACK records, child ACK event and task-file modification time corroborate ACK-before-task. Reviewer did not independently observe publication in real time.'},
        'signaled_waits': waits,
        'termination_scope': 'Three retained-handle signaled waits were saved: launcher observer waited for child, controller waited for launcher, and outer waited for controller. Direct external child wait was not reached. No unsigned exit codes or exit FILETIMEs were saved for any of those actors.',
        'failure': 'QueryFullProcessImageNameW WinError31 during kernel_identity requery after WAIT_OBJECT_0, first child observer, then launcher observer, then outer controller observer. This is an actual CPU evidence-component failure, not original T6/GPU/host/resource failure.',
        'cleanup': 'Actor records report empty cleanup errors and own streams closed. Held release records do not supply exit evidence. Review accepts the saved reports as reports, not independent OS closure recapture.',
        'after_observation': 'Root captured two later widened CIM scans with no fixture IDs/commands and only the same ordinary Visio. Absence is not an exit-code substitute; no new GPU/commit admission was performed.',
        'tool_exit': 'Root forwarded actual tool shell exit92 for outer only. This is separate from missing complete controller/launcher/interpreter held exits.',
    },
    'missing_evidence': ['zero result.json', 'parent return_intent completion', 'all complete exit_observed records',
                         'actual unsigned controller/launcher/interpreter exit codes', 'actual exit FILETIME fields',
                         'case and controller closed-log seals', 'nonzero17 case and its actual execution'],
    'log_hash_scope': 'Hashes below are current reviewer snapshots of preserved diagnostic bytes after failure; they cannot replace missing producer seal_closed_log evidence or prove historical global writer exclusion.',
    'minimum_new_source_recommendation': [
        'Preserve all v1 sources, attempt directories, logs, decision and failures; never replay/delete/rename them.',
        'In separately reviewed v2, retain pre-exit two complete image/command/current-parent captures and the continuously held identity handle.',
        'After WAIT_OBJECT_0, save GetExitCodeProcess unsigned DWORD immediately as a candidate, then query held GetProcessId and GetProcessTimes creation/exit using that same handle. Compare PID/raw creation exactly to retained identity; require positive actual exit FILETIME before completed exit_observation.',
        'Do not requery image/command of an exited process. Retained pre-exit image/command provenance must be explicit rather than presented as new post-exit capture.',
        'Persist candidate post-signaled values before gates, retain partial evidence on any error, and assign complete exit_observation only after all identity/time gates pass.',
        'Keep ACK, both branches, isolated Python, signaled-before-code, cleanup, read-sharing closed-log sealing and new-attempt refusal gates unchanged. New v2 execution requires a separate root decision, not automatic retry.',
        'Benign fixture evidence does not establish real scientific-venv redirection, six native B1 workers, predecessor exits, boot/resource/release/shared-lock admission, full ranking/parity/timing or T6 completion.'
    ],
    'inspection_note': 'One initial text request used the nonexistent observer filename observe_current.ps1; the saved observation source identified observe_fixture_after.ps1 and that exact source/prior were then read fully. No observer was executed by reviewer.',
    'diagnostic_check_count': len(checks), 'diagnostic_checks': checks,
    'bound_small_file_count': len(bindings), 'inputs': list(bindings.values()),
    'old_sources_or_attempts_modified': False, 'scientific_or_old_suite_run': False,
}
for name, value in [('FAILED_RUNTIME_REVIEW.json', report), ('AFTER_OBSERVER_FILTER_DIFF.patch', observer_diff)]:
    payload = ((json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
               if isinstance(value, dict) else value.encode('utf-8'))
    with (HERE / name).open('xb') as stream:
        stream.write(payload)
delivery = {'schema': 'independent-failed-benign-runtime-review-delivery.v1', 'fixture_passed': False,
            'execution_released': False, 'scientific_admission': False,
            'review': {'path': str(HERE / 'FAILED_RUNTIME_REVIEW.json'), 'bytes': (HERE / 'FAILED_RUNTIME_REVIEW.json').stat().st_size,
                       'sha256': hashlib.sha256((HERE / 'FAILED_RUNTIME_REVIEW.json').read_bytes()).hexdigest()},
            'observer_filter_diff': {'path': str(HERE / 'AFTER_OBSERVER_FILTER_DIFF.patch'), 'bytes': (HERE / 'AFTER_OBSERVER_FILTER_DIFF.patch').stat().st_size,
                                     'sha256': hashlib.sha256((HERE / 'AFTER_OBSERVER_FILTER_DIFF.patch').read_bytes()).hexdigest()},
            'source': bindings[str(Path(__file__))], 'diagnostic_check_count': len(checks), 'bound_small_file_count': len(bindings)}
with (HERE / 'FAILED_RUNTIME_DELIVERY.json').open('xb') as stream:
    stream.write((json.dumps(delivery, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
print(json.dumps(delivery, ensure_ascii=False))
