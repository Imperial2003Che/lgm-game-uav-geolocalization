"""Independent AI saved-record audit only: no producer import/API/fixture replay.

Run only after the root notifies that its separate single v2 invocation ended.
This reviewer has never held those process handles and does not reobserve OS.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
EX = HERE.parent
SRC = EX / 'external_efficiency_preparation/newer_native_process_evidence_v2'
RUN = EX / 'newer_native_process_execution_v2_20260930_0820'
PYTHON = r'C:\Users\17703\AppData\Local\Programs\Python\Python311\python.exe'
OFFSET = 504911232000000000
UNIX_OFFSET = 116444736000000000
records = {}
checks = []
events_read = {}

def check(condition, description, actual=None):
    entry = {'index': len(checks) + 1, 'check': description, 'passed': bool(condition)}
    if actual is not None:
        entry['actual'] = actual
    checks.append(entry)
    if not condition:
        raise AssertionError(description)

def binding(path, limit=100000):
    path = Path(path)
    check(path.is_file() and path.stat().st_size < limit, 'Bounded actual small file: ' + str(path))
    with path.open('rb') as stream:
        raw = stream.read(limit)
    check(len(raw) < limit, 'Bounded read: ' + str(path))
    value = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    records[str(path)] = value
    return value, raw

def load(path):
    return json.loads(binding(path)[1])

def verify(item):
    check(binding(item['path'])[0] == item, 'Exact saved byte/size/SHA binding: ' + item['path'])

def write(path, value):
    raw = (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode('utf-8')
    with Path(path).open('xb') as stream:
        stream.write(raw)
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def identity(value, context):
    check(type(value['pid']) is int and value['pid'] > 0, context + ': positive integer PID')
    check(type(value['creation_filetime_100ns']) is int and value['creation_filetime_100ns'] > 0,
          context + ': positive exact FILETIME integer')
    check(value['creation_utc_ticks'] == value['creation_filetime_100ns'] + OFFSET,
          context + ': exact integer 1601-to-.NET UTC conversion')
    check(value['image'].casefold() == PYTHON.casefold(), context + ': retained live expected Python image path')

def ledger(directory, actor):
    result = []
    # Windows glob is case-insensitive: OUTER_RETURN_INTENT... is metadata,
    # not an indexed outer ledger. Filter names before any ledger read.
    indexed_paths = []
    for path in Path(directory).iterdir():
        match = re.fullmatch(re.escape(actor) + r'_(\d{4})_(.+)\.json', path.name)
        if path.is_file() and match is not None:
            indexed_paths.append((path, match))
    for path, match in sorted(indexed_paths, key=lambda item: item[0].name):
        row = load(path)
        row['_index'] = int(match.group(1))
        row['_path'] = str(path)
        check(row['event'] == match.group(2) and row['actor'] == actor, 'Ledger actor/event agrees with filename ' + path.name)
        check(type(row['utc_ns']) is int and row['utc_ns'] > 0, 'Actual UTC nanosecond integer ' + path.name)
        result.append(row)
    check(result and [r['_index'] for r in result] == list(range(1, len(result) + 1)),
          'Complete consecutive ' + actor + ' ledger indices in ' + str(directory))
    check(all(a['utc_ns'] <= b['utc_ns'] for a, b in zip(result, result[1:])), 'Ledger chronological order ' + actor)
    check(len({r['pid'] for r in result}) == 1, 'One actual emitting actor PID ' + actor)
    check(not any(r['event'] == 'failure' for r in result), 'No actual failure events in completed actor ' + actor)
    for row in result:
        if row['event'] == 'nt_command_size':
            check(row['status'] in (0xC0000004, 0xC0000023, 0x80000005) and 16 <= row['required_bytes'] <= 1048576,
                  'Actual bounded experimental Nt command size query ' + row['_path'])
        if row['event'] == 'nt_command_result':
            check(row['status'] == 0 and 16 <= row['returned_bytes'] <= row['capacity'] <= 1048576,
                  'Actual successful bounded experimental Nt command value query ' + row['_path'])
    events_read[str(directory) + '/' + actor] = result
    return result

def find(rows, event, label=None):
    result = [r for r in rows if r['event'] == event and (label is None or r.get('label') == label)]
    check(len(result) == 1, 'Exactly one ' + event + ('/' + label if label else ''))
    return result[0]

def held(rows, label):
    row = find(rows, 'held_open', label)
    identity(row['identity'], label)
    check(row['access_mask'] == 0x101000, label + ': independent limited-query/synchronize rights')
    if label.endswith('_self'):
        check(row['identity']['pid'] == row['pid'], label + ': actual self held PID equals emitting actor')
    return row['identity']

def snapshot(value, expected_identity, command, parent_pid, context):
    keys = ('pid', 'creation_filetime_100ns', 'creation_utc_ticks', 'image')
    check({k: value[k] for k in keys} == expected_identity, context + ': actual current identity equals original retained identity')
    check(value['held_now'] == value['fresh_after'] == expected_identity, context + ': held/fresh-before/fresh-after identity agrees')
    check(value['command_line'] == command, context + ': complete actual command line matches exact declaration')
    check(value['parent_pid'] == parent_pid, context + ': current Toolhelp parent PID agrees')

def confirmed(rows, label, expected_identity, parent_identity, command):
    row = find(rows, 'confirmed', label)
    gates = [r for r in rows if r['event'] == 'confirmation_gate' and r.get('label') == label]
    check(len(gates) == 2 and [r['index'] for r in gates] == [0, 1], label + ': exactly two contemporaneous complete confirmation gates')
    check(row['observations'][0] == row['observations'][1], label + ': two saved observations identical')
    for i, gate in enumerate(gates):
        check(gate['expected_parent'] == parent_identity, label + ': retained actual parent creation identity')
        check(gate['expected_command'] == command and gate['expected_image'].casefold() == PYTHON.casefold(), label + ': exact expected command/image declaration')
        check(gate['observed'] == row['observations'][i], label + ': confirmed observation sourced from corresponding gate')
        snapshot(gate['observed'], expected_identity, command, parent_identity['pid'], label)
        candidates = [r for r in rows if r['event'] == 'candidate_snapshot' and r.get('label') == label and r['_index'] < gate['_index']]
        check(candidates and candidates[-1]['value'] == gate['observed'], label + ': gate agrees with independently queried candidate')
    check(gates[0]['utc_ns'] + 200000000 <= gates[1]['utc_ns'] <= row['utc_ns'], label + ': separated confirmations precede confirmation publication')
    check(expected_identity['creation_utc_ticks'] >= parent_identity['creation_utc_ticks'] and expected_identity['pid'] != parent_identity['pid'], label + ': child creation follows held parent')
    return row

def actual_exit(rows, label, expected_identity, code):
    wait = find(rows, 'wait_result', label)
    candidate = find(rows, 'exit_candidate', label)
    pid_candidate = find(rows, 'signaled_pid_candidate', label)
    times_candidate = find(rows, 'signaled_identity_times_candidate', label)
    complete = find(rows, 'exit_observed', label)
    check(wait['result'] == 0 and wait['milliseconds'] == 60000, label + ': actual WAIT_OBJECT_0 before exit query')
    check(wait['_index'] < candidate['_index'] < pid_candidate['_index'] < times_candidate['_index'] < complete['_index'], label + ': WAIT→DWORD candidate→same-handle PID/times→complete exit ordering')
    check(candidate['value']['complete_exit_evidence'] is False and pid_candidate['complete_exit_evidence'] is False and times_candidate['complete_exit_evidence'] is False, label + ': incomplete candidates clearly distinguished')
    check(candidate['value']['exit_code_unsigned_dword'] == code and candidate['value']['wait_result'] == 0 and candidate['value']['retained_live_identity'] == expected_identity, label + ': actual DWORD candidate equals retained identity and predeclared branch')
    check(pid_candidate['pid_from_held_handle'] == expected_identity['pid'], label + ': same retained handle actual PID')
    times = times_candidate['value']
    check(times['pid'] == expected_identity['pid'] and times['creation_filetime_100ns'] == expected_identity['creation_filetime_100ns'] and times['creation_utc_ticks'] == expected_identity['creation_utc_ticks'], label + ': positive exact same-handle creation identity after exit')
    check(type(times['exit_filetime_100ns']) is int and times['exit_filetime_100ns'] > expected_identity['creation_filetime_100ns'], label + ': positive actual exit FILETIME after creation')
    check(times['exit_utc_ticks'] == times['exit_filetime_100ns'] + OFFSET, label + ': exact exit UTC conversion')
    value = complete['value']
    check(value['identity'] == expected_identity and value['same_retained_handle_pid_creation_verified'] is True and value['exit_code_unsigned_dword'] == code and value['wait_result'] == 0, label + ': complete same retained handle exit evidence')
    check(all(value[key] == val for key, val in times.items()), label + ': complete actual exit inherits exact candidate times')
    check(value['image_scope'] == 'Retained live image; not requeried after exit', label + ': image scope is retained live evidence only')
    exit_ns = (times['exit_filetime_100ns'] - UNIX_OFFSET) * 100
    check(exit_ns <= wait['utc_ns'] <= candidate['utc_ns'] <= times_candidate['utc_ns'] <= complete['utc_ns'], label + ': actual exit precedes signaled saved observation')
    check(wait['utc_ns'] - exit_ns < 10000000000, label + ': same host observation within 10 seconds of actual exit')
    closed = find(rows, 'held_closed', label)
    check(closed['_index'] > complete['_index'] and closed['exit_observed'] is True and closed['process_not_terminated'] is True, label + ': retained evidence handle closed after complete exit')
    return value, complete

def cleanup(rows, required_closed_count):
    row = find(rows, 'cleanup_complete')
    check(row['errors'] == [] and row['no_termination'] is True, 'Actual cleanup completes without errors/termination')
    check(len(row['own_stream_closed']) == required_closed_count and all(row['own_stream_closed']), 'All designated own redirect streams actually reported closed')
    check(not any(r['event'] == 'failure' for r in rows), 'No hidden actor failure')
    return row

def audit_case(name, code, parent_identity):
    directory = SRC / 'runtime_attempt_v1' / name
    request_path = directory / 'request.json'
    request = load(request_path)
    request_binding = binding(request_path)[0]
    check(request == {'name': name, 'child_exit': code, 'launcher_exit': code, 'controller_identity': parent_identity,
                      'ack_timeout_seconds': 45, 'wait_ms': 60000, 'scientific_execution': False}, name + ': exact predeclared request including actual controller')
    c = ledger(directory, 'controller'); l = ledger(directory, 'launcher'); k = ledger(directory, 'child')
    li = held(c, 'launcher_external'); ki = held(c, 'child_external')
    check(held(l, 'launcher_self') == li and held(l, 'child_launcher_observer') == ki and held(k, 'child_self') == ki,
          name + ': independently held external/self/launcher observer identities agree')
    for role, ident in [('launcher', li), ('child', ki)]:
        ready = load(directory / (role + '.ready.json'))
        ack = load(directory / (role + '.ack.json'))
        check(ready == {'pid': ident['pid'], 'identity': ident}, name + ': ' + role + ' actual self report agrees with external held evidence')
        check(ack == {'role': role, 'identity': ident, 'request_sha256': request_binding['sha256']}, name + ': ' + role + ' ACK binds exact request raw bytes and actual identity')
    launcher_argv = [PYTHON, '-I', '-S', '-B', str(SRC / 'benign_fixture.py'), '--role', 'launcher', '--case', str(directory), '--execute-benign-fixture']
    child_argv = [PYTHON, '-I', '-S', '-B', str(SRC / 'benign_fixture.py'), '--role', 'child', '--case', str(directory), '--execute-benign-fixture']
    lconfirmed = confirmed(c, 'launcher_external', li, parent_identity, subprocess.list2cmdline(launcher_argv))
    kconfirmed = confirmed(c, 'child_external', ki, li, subprocess.list2cmdline(child_argv))
    check(find(c, 'spawn_declaration')['argv'] == launcher_argv and find(l, 'spawn_declaration')['argv'] == child_argv, name + ': exact actually declared isolated CPU commands')
    spawn = load(directory / 'child.spawn.json')
    check(spawn == {'pid': ki['pid'], 'argv': child_argv}, name + ': actual launcher child spawn declaration matches external held identity')
    ack_event = find(k, 'ack_received_before_fixture_task')
    task = load(directory / 'child.task.json')
    check(task == {'task': 'sum_squares_0_through_999', 'value': 332833500}, name + ': actual saved benign CPU sum')
    task_mtime_ns = (directory / 'child.task.json').stat().st_mtime_ns
    check(kconfirmed['utc_ns'] <= ack_event['utc_ns'] <= task_mtime_ns, name + ': complete child confirmation and bound ACK receipt before actual task file last-write',
          {'confirmation_utc_ns': kconfirmed['utc_ns'], 'ack_event_utc_ns': ack_event['utc_ns'], 'task_current_last_write_ns': task_mtime_ns})
    launcher_spawn = find(l, 'spawn_declaration')
    check(lconfirmed['utc_ns'] <= launcher_spawn['utc_ns'] < ack_event['utc_ns'], name + ': launcher external confirmation precedes ACK-gated child spawn')
    le, levent = actual_exit(c, 'launcher_external', li, code)
    ke, kevent = actual_exit(c, 'child_external', ki, code)
    inner_exit, inner_event = actual_exit(l, 'child_launcher_observer', ki, code)
    check({key: inner_exit[key] for key in ['pid', 'creation_filetime_100ns', 'creation_utc_ticks', 'exit_filetime_100ns', 'exit_utc_ticks', 'exit_code_unsigned_dword']} ==
          {key: ke[key] for key in ['pid', 'creation_filetime_100ns', 'creation_utc_ticks', 'exit_filetime_100ns', 'exit_utc_ticks', 'exit_code_unsigned_dword']}, name + ': two independently opened actual child exit observations agree')
    check(ke['exit_filetime_100ns'] <= le['exit_filetime_100ns'], name + ': child exits before launcher propagates branch')
    check(find(c, 'popen_exit_separate')['code'] == code, name + ': controller separate Popen launcher observation agrees')
    pl = find(l, 'popen_exit_separate')
    check(pl['exit_code'] == code and pl['evidence_handle_exit'] == inner_exit, name + ': launcher separate Popen child observation agrees')
    cleanup(c, 2); cleanup(l, 2); cleanup(k, 0)
    result = load(directory / 'result.json')
    check(result['case'] == {'name': name, 'child_exit': code, 'launcher_exit': code} and result['launcher_exit'] == le and result['interpreter_exit'] == ke,
          name + ': saved complete result agrees with independently read event evidence')
    check(result['scientific_execution_or_admission'] is False and result['controller_self_exit_proven'] is False, name + ': benign result scope keeps parent exit unknown')
    expected_logs = {'launcher.stdout.log': f'benign launcher observed child exit {code}\r\n'.encode(), 'launcher.stderr.log': b'',
                     'child.stdout.log': f'benign child completed after ACK; intended exit {code}\r\n'.encode(),
                     'child.stderr.log': b'benign child stderr record\r\n'}
    check(len(result['closed_logs']) == 4, name + ': exactly four actual closed logs')
    for item in result['closed_logs']:
        path = Path(item['path'])
        check(path.parent == directory and path.name in expected_logs, name + ': closed log allowlist')
        actual, raw = binding(path)
        check({key: item[key] for key in ('path', 'bytes', 'sha256')} == actual, name + ': closed saved log seal matches actual small bytes')
        check(raw == expected_logs[path.name], name + ': actual log bytes match benign branch')
        check(item['read_lock_denied_write_delete'] is True and item['controller_streams_closed'] is True, name + ': saved compatible read-lock and stream closure facts')
        check(path.stat().st_mtime_ns <= levent['utc_ns'], name + ': last actual log write precedes externally saved launcher exit')
    return {'name': name, 'launcher_identity': li, 'interpreter_identity': ki,
            'launcher_actual_held_exit': le, 'interpreter_actual_held_exit': ke,
            'launcher_also_observed_interpreter_exit': inner_exit,
            'ack_before_saved_task_verified': True, 'closed_logs': result['closed_logs']}, result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--actual-invocation-confirmed-by-root', action='store_true')
    parser.add_argument('--after-observation', required=True)
    parser.add_argument('--tool-receipt', required=True)
    args = parser.parse_args()
    check(args.actual_invocation_confirmed_by_root, 'Root notification of completed actual v2 invocation required')
    decision = load(RUN / 'ROOT_BENIGN_FIXTURE_DECISION.json')
    check(decision['execute'] is True and decision['maximum_fixture_attempts'] == 1 and decision['scientific_admission'] is False,
          'One separate root v2 benign-only execution decision')
    verify(decision['outer_source'])
    for path, sha in [(SRC / 'windows_process_evidence.py', 'cc090bec1429ab429b556200597acedfa13c33e878627155b0cc9f8098c9f5d2'),
                      (SRC / 'benign_fixture.py', '05379eda9addbac90faea33d73eb9a0faa4fc59450bf65e3e1f11de677fca50f')]:
        check(binding(path)[0]['sha256'] == sha, 'Exact source actually reviewed and invoked ' + path.name)
    outerdir = RUN / 'outer_runtime_attempt_v1'
    fixturedir = SRC / 'runtime_attempt_v1'
    check(outerdir.is_dir() and fixturedir.is_dir(), 'Actual distinct v2 attempts exist; no replay')
    # Only the newly completed small runtime bytes are inventoried here.
    for directory in [outerdir, fixturedir]:
        paths = sorted(path for path in directory.rglob('*') if path.is_file())
        check(0 < len(paths) < 400, 'Bounded new runtime inventory')
        for path in paths:
            check(path.suffix in ('.json', '.log'), 'Only small runtime JSON/log allowlist ' + path.name)
            binding(path)
        check(not any('failure' in path.name.casefold() for path in paths), 'No actual failure files in completed new runtime')
    outer = ledger(outerdir, 'outer'); parent = ledger(fixturedir, 'parent')
    outeridentity = held(outer, 'outer_self')
    controlleridentity = held(outer, 'fixture_controller_external')
    check(held(parent, 'controller_self') == controlleridentity, 'Fixture self identity equals independent outer held actual identity')
    outerspawn = find(outer, 'controller_spawned')
    argv = [PYTHON, '-I', '-S', '-B', str(SRC / 'benign_fixture.py'), '--execute-benign-fixture']
    check(outerspawn['argv'] == argv and outerspawn['actual_popen_pid'] == controlleridentity['pid'], 'Actual outer spawn and isolated exact controller command')
    confirmed(outer, 'fixture_controller_external', controlleridentity, outeridentity, subprocess.list2cmdline(argv))
    for row in [r for r in parent if r['event'] == 'candidate_snapshot']:
        snapshot(row['value'], controlleridentity, subprocess.list2cmdline(argv), outeridentity['pid'], 'Actual fixture parent snapshot')
    predeclared = load(fixturedir / 'predeclared_cases.json')
    check(predeclared == {'cases': [{'name': 'zero', 'child_exit': 0, 'launcher_exit': 0}, {'name': 'nonzero17', 'child_exit': 17, 'launcher_exit': 17}],
                         'python': PYTHON, 'flags': ['-I', '-S', '-B'], 'child_task_requires_ack': True, 'retries': 0, 'scientific_imports_or_execution': False}, 'Actual predeclared zero/nonzero CPU cases')
    cases = []; result_values = []
    for name, code in [('zero', 0), ('nonzero17', 17)]:
        value, result = audit_case(name, code, controlleridentity)
        cases.append(value); result_values.append(result)
    check(cases[0]['launcher_actual_held_exit']['exit_filetime_100ns'] < cases[1]['launcher_identity']['creation_filetime_100ns'], 'Actual cases executed serially after preceding launcher exit')
    intent = load(fixturedir / 'return_intent.json')
    check(intent['completed_cases'] == result_values and intent['controller_return_intent'] == 0 and intent['controller_actual_exit_unknown_here'] is True,
          'Fixture return intention is consistent and keeps own actual exit unknown')
    cleanup(parent, 0)
    controller_exit, controller_event = actual_exit(outer, 'fixture_controller_external', controlleridentity, 0)
    check(all(case['launcher_actual_held_exit']['exit_filetime_100ns'] <= controller_exit['exit_filetime_100ns'] for case in cases), 'Inner actual exits precede outer-held fixture controller exit')
    controller_report = load(outerdir / 'CONTROLLER_EXIT_AND_CLOSED_LOGS.json')
    check(controller_report['controller_actual_held_exit'] == controller_exit and controller_report['controller_popen_exit'] == 0,
          'Outer actual controller held exit plus separately saved Popen exit agree')
    check(controller_report['outer_self_actual_exit_unknown_in_this_record'] is True and controller_report['scientific_admission'] is False,
          'Outer report keeps own actual exit scope distinct')
    for item in controller_report['closed_logs']:
        actual, raw = binding(item['path'])
        check({key: item[key] for key in ('path', 'bytes', 'sha256')} == actual and Path(item['path']).parent == outerdir,
              'Actual outer controller log size/SHA matches saved seal')
        check(raw == b'', 'Actual fixture parent stdout/stderr are empty after success')
        check(item['read_lock_denied_write_delete'] is True and item['controller_streams_closed'] is True, 'Saved outer post-exit closed-stream/read-lock evidence')
    check(len(controller_report['closed_logs']) == 2, 'Two actual outer controller logs')
    streams_event = find(outer, 'controller_streams_closed')
    check(streams_event['all_closed'] is True and streams_event['_index'] > controller_event['_index'], 'Outer own streams close only after actual controller held exit')
    clean = load(outerdir / 'OUTER_RETURN_INTENT_AND_CLEANUP.json')
    check(clean['return_intent'] == 0 and clean['cleanup_errors'] == [] and clean['own_redirect_streams_closed'] is True and clean['evidence_handles_closed'] is True,
          'Actual outer cleanup records no errors and closes all own streams/evidence handles')
    check(clean['own_actual_exit_unknown'] is True and clean['does_not_terminate_processes'] is True, 'Outer cleanup is not own exit or termination evidence')
    receipt = load(args.tool_receipt)
    check(receipt['schema'] == 'post-execution-tool-transcription.v1' and receipt['tool_result']['exit_code'] == 0,
          'Actual root forwarded outer shell/tool receipt has exit zero; not independently held outer exit')
    observation = load(args.after_observation)
    for which in ['first', 'second']:
        row = observation[which]
        check(row['boot_utc_ticks'] == decision['observed_current_boot_utc_ticks'], 'Root post-fixture current boot stable ' + which)
        check(len(row['matches']) == 1 and row['matches'][0]['name'] == 'VISIO.EXE', 'Root saved broad post-fixture scan has ordinary Visio only ' + which)
    check(observation['first']['matches'] == observation['second']['matches'], 'Root saved broad double OS ordinary Visio identity unchanged')
    report = {
        'schema': 'independent-saved-v2-benign-runtime-review.v1', 'reviewed_utc': datetime.now(timezone.utc).isoformat(),
        'reviewer': 'Independent AI agent; read saved records and actual bounded small file bytes only',
        'fixture_passed_saved_record_audit': True, 'case_count': 2, 'expected_nonzero17_is_control_success': True,
        'actual_cases': cases, 'fixture_controller_actual_held_exit_captured_by_outer': controller_exit,
        'outer_cleanup': clean, 'root_tool_receipt': receipt,
        'root_after_observation': binding(args.after_observation)[0],
        'root_decision': binding(RUN / 'ROOT_BENIGN_FIXTURE_DECISION.json')[0],
        'check_count': len(checks), 'unique_input_count': len(records),
        'windows_api_or_producer_executed_by_reviewer': False, 'live_handles_held_or_os_reobserved_by_reviewer': False,
        'source_only_planning_used_as_runtime_proof': False, 'scientific_execution_or_admission': False,
        'limits': [
            'Independent AI saved-record validation, not human review or independent live API capture.',
            'Process handles were held by actual producer actors; this reviewer read their persisted API values and corresponding small logs.',
            'Root tool receipt is forwarded outer invocation evidence. It does not give an independently held outer PID/creation/exit observation.',
            'Two current Toolhelp parent observations with held creation identities are not full historical ancestry.',
            'Nt class60 current-host success remains undocumented/experimental; no original scientific venv launcher or all-Windows compatibility validation.',
            'Recomputed actual closed-log bytes validate saved seals. Cooperative read-sharing/closure records do not prove global historical malicious-writer exclusion.',
            'Task last-write time is contemporaneous filesystem metadata, not an immutable publication or full syscall transcript.',
            'CreateNew/flush publication is cooperative and may expose partial files; the frozen v1 failure remains and is never replayed.',
            'No B1, original scientific environment, boot/resource/release/shared locks/predecessor exits, six scientific workers, gallery/ranking/parity/timing/onlineCLIP or T6 validation.'
        ]}
    inputs = write(HERE / 'INPUT_BINDINGS.json', {'files': list(records.values())})
    diagnostics = write(HERE / 'CHECKS.json', {'checks': checks})
    report['inputs'] = inputs; report['diagnostics'] = diagnostics
    review = write(HERE / 'RUNTIME_REVIEW.json', report)
    delivery = write(HERE / 'DELIVERY.json', {'schema': 'independent-v2-benign-runtime-delivery.v1', 'review': review,
        'inputs': inputs, 'diagnostics': diagnostics, 'source': binding(__file__)[0],
        'scientific_execution_or_admission': False, 'fixture_replayed': False,
        'reviewer_held_original_process_handles': False, 'scope': 'Saved two-case benign runtime evidence, actual bounded log-byte and root double OS observation checks only'})
    print(json.dumps({'review': review, 'delivery': delivery, 'checks': len(checks), 'inputs': len(records)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
