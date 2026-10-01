"""Candidate fixture only. Future single explicit CPU execution after root review.

All roles use isolated -I -S -B Python311. Nothing imports B1/scientific code.
An attempt directory, even empty/partial, prevents replay. Never kill/terminate.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
PYTHON = Path(r'C:\Users\17703\AppData\Local\Programs\Python\Python311\python.exe')
ATTEMPT = HERE / 'runtime_attempt_v1'
ACK_SECONDS = 45
WAIT_MS = 60000
CASES = ({'name': 'zero', 'child_exit': 0, 'launcher_exit': 0},
         {'name': 'nonzero17', 'child_exit': 17, 'launcher_exit': 17})


def helper():
    path = HERE / 'windows_process_evidence.py'
    spec = importlib.util.spec_from_file_location('_reviewed_benign_held_helper', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_json(path):
    with Path(path).open('rb') as f:
        raw = f.read(128 * 1024 + 1)
    if len(raw) > 128 * 1024:
        raise RuntimeError('Oversize fixture control file')
    return json.loads(raw)


def wait_file(path, seconds):
    end = time.monotonic() + seconds
    while not path.exists():
        if time.monotonic() >= end:
            raise TimeoutError('Fixture control wait expired: ' + path.name)
        time.sleep(0.05)
    # Malformed/partially written files are a preserved failure, never a retry.
    return read_json(path)


def command(role, case):
    return [str(PYTHON), '-I', '-S', '-B', str(Path(__file__).resolve()),
            '--role', role, '--case', str(case), '--execute-benign-fixture']


def identity_ack(h, case, role, self_held):
    record = wait_file(case / f'{role}.ack.json', ACK_SECONDS)
    request = (case / 'request.json').read_bytes()
    h.require(record['request_sha256'] == hashlib.sha256(request).hexdigest(), 'ACK request binding differs')
    h.require(record['role'] == role and record['identity'] == self_held.identity, 'ACK held identity differs')
    return record


def close_all(held, streams, ledger):
    """All cleanup branches run; closure is never termination or exit proof."""
    errors = []
    for f in streams:
        try:
            if not f.closed:
                f.close()
        except BaseException as error:
            errors.append({'stream_close_error': repr(error)})
    for p in reversed(held):
        try:
            p.close()
        except BaseException as error:
            errors.append({'handle_close_error': repr(error)})
    ledger.emit('cleanup_complete', errors=errors,
                own_stream_closed=[f.closed for f in streams],
                exits=[p.exit_observation for p in held], no_termination=True)
    return errors


def child(h, case):
    api = h.WinAPI(); ledger = h.Ledger(case, 'child')
    held = []; streams = []; code = 92
    try:
        me = h.HeldProcess(api, os.getpid(), ledger, 'child_self'); held.append(me)
        h.create_json(case / 'child.ready.json', {'pid': os.getpid(), 'identity': me.identity})
        identity_ack(h, case, 'child', me)
        ledger.emit('ack_received_before_fixture_task')
        # A small, deterministic CPU task begins only after the identity ACK.
        total = sum(i * i for i in range(1000))
        h.create_json(case / 'child.task.json', {'task': 'sum_squares_0_through_999', 'value': total})
        request = read_json(case / 'request.json')
        code = request['child_exit']
        h.require(type(code) is int and code in (0, 17), 'Only predeclared benign exit codes allowed')
        print('benign child completed after ACK; intended exit', code, flush=True)
        print('benign child stderr record', file=sys.stderr, flush=True)
    except BaseException as error:
        ledger.emit('failure', error=repr(error), traceback=traceback.format_exc(), actual_self_exit_unknown=True)
    finally:
        errors = close_all(held, streams, ledger)
        if errors:
            code = 94
    return code


def launcher(h, case):
    api = h.WinAPI(); ledger = h.Ledger(case, 'launcher')
    held = []; streams = []; code = 93; proc = None
    try:
        me = h.HeldProcess(api, os.getpid(), ledger, 'launcher_self'); held.append(me)
        h.create_json(case / 'launcher.ready.json', {'pid': os.getpid(), 'identity': me.identity})
        identity_ack(h, case, 'launcher', me)
        argv = command('child', case)
        out = (case / 'child.stdout.log').open('xb'); streams.append(out)
        err = (case / 'child.stderr.log').open('xb'); streams.append(err)
        ledger.emit('spawn_declaration', argv=argv, full_command=subprocess.list2cmdline(argv),
                    popen_creation_handle='Separate standard-library creation handle; not claimed minimal-rights evidence')
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                close_fds=True, creationflags=subprocess.CREATE_NO_WINDOW, cwd=str(HERE))
        h.create_json(case / 'child.spawn.json', {'pid': proc.pid, 'argv': argv})
        child_held = h.HeldProcess(api, proc.pid, ledger, 'child_launcher_observer'); held.append(child_held)
        result = child_held.wait(WAIT_MS)
        h.require(result is not None, 'Launcher child wait timed out; actual exit remains unproven')
        popen_code = proc.wait(timeout=0)
        ledger.emit('popen_exit_separate', exit_code=popen_code, evidence_handle_exit=result)
        code = result['exit_code_unsigned_dword']
        h.require(code in (0, 17, 92, 94), 'Unexpected child exit status')
        print('benign launcher observed child exit', code, flush=True)
    except BaseException as error:
        ledger.emit('failure', error=repr(error), traceback=traceback.format_exc(),
                    child_pid=proc.pid if proc else None, unobserved_exit_not_assumed=True)
    finally:
        errors = close_all(held, streams, ledger)
        if errors:
            code = 94
    return code


def run_case(h, api, controller, case_record):
    case = ATTEMPT / case_record['name']; case.mkdir()
    ledger = h.Ledger(case, 'controller')
    held = []; streams = []; completed = None; proc = None
    try:
        h.create_json(case / 'request.json', {**case_record, 'controller_identity': controller.identity,
                      'ack_timeout_seconds': ACK_SECONDS, 'wait_ms': WAIT_MS,
                      'scientific_execution': False})
        argv = command('launcher', case)
        out = (case / 'launcher.stdout.log').open('xb'); streams.append(out)
        err = (case / 'launcher.stderr.log').open('xb'); streams.append(err)
        ledger.emit('spawn_declaration', argv=argv, full_command=subprocess.list2cmdline(argv),
                    popen_creation_handle='Separate Popen internal creation handle; evidence below uses independently opened limited-query/synchronize handle')
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                close_fds=True, creationflags=subprocess.CREATE_NO_WINDOW, cwd=str(HERE))
        launcher_held = h.HeldProcess(api, proc.pid, ledger, 'launcher_external'); held.append(launcher_held)
        launcher_held.confirm_twice(subprocess.list2cmdline(argv), PYTHON, controller)
        ready = wait_file(case / 'launcher.ready.json', ACK_SECONDS)
        h.require(ready['pid'] == proc.pid and ready['identity'] == launcher_held.identity, 'Launcher self-report disagrees with external held identity')
        request_sha = hashlib.sha256((case / 'request.json').read_bytes()).hexdigest()
        h.create_json(case / 'launcher.ack.json', {'role': 'launcher', 'identity': launcher_held.identity,
                                                'request_sha256': request_sha})
        candidate = wait_file(case / 'child.spawn.json', ACK_SECONDS)
        child_argv = command('child', case)
        h.require(candidate['argv'] == child_argv, 'Child command declaration differs')
        child_held = h.HeldProcess(api, candidate['pid'], ledger, 'child_external'); held.append(child_held)
        child_held.confirm_twice(subprocess.list2cmdline(child_argv), PYTHON, launcher_held)
        ready = wait_file(case / 'child.ready.json', ACK_SECONDS)
        h.require(ready['pid'] == child_held.identity['pid'] and ready['identity'] == child_held.identity,
                  'Child self-report disagrees with external held identity')
        h.create_json(case / 'child.ack.json', {'role': 'child', 'identity': child_held.identity,
                                             'request_sha256': request_sha})
        lexit = launcher_held.wait(WAIT_MS)
        cexit = child_held.wait(WAIT_MS)
        h.require(lexit is not None and cexit is not None, 'Timeout; both actual exits not proven')
        h.require(lexit['exit_code_unsigned_dword'] == case_record['launcher_exit'] and
                  cexit['exit_code_unsigned_dword'] == case_record['child_exit'], 'Predeclared exit branch differs')
        popen_code = proc.wait(timeout=0)
        ledger.emit('popen_exit_separate', code=popen_code)
        for f in streams:
            f.close()
        logs = [h.seal_closed_log(api, case / name, held, streams) for name in
                ('launcher.stdout.log', 'launcher.stderr.log', 'child.stdout.log', 'child.stderr.log')]
        task = read_json(case / 'child.task.json')
        h.require(task == {'task': 'sum_squares_0_through_999', 'value': 332833500}, 'Benign task result differs')
        completed = {'case': case_record, 'launcher_exit': lexit, 'interpreter_exit': cexit,
                     'closed_logs': logs, 'benign_task': task,
                     'scientific_execution_or_admission': False, 'controller_self_exit_proven': False}
        h.create_json(case / 'result.json', completed)
    except BaseException as error:
        ledger.emit('failure', error=repr(error), traceback=traceback.format_exc(),
                    actual_exit_evidence=[p.exit_observation for p in held],
                    partial_files_preserved=True, automatic_retry=False, no_termination=True)
        raise
    finally:
        errors = close_all(held, streams, ledger)
        if errors:
            raise RuntimeError('Fixture cleanup incomplete; preserved logs record details')
    return completed


def parent(h):
    # Any existing attempt, including an empty one, is consumed and rejects replay.
    ATTEMPT.mkdir(exist_ok=False)
    ledger = h.Ledger(ATTEMPT, 'parent')
    held = []; results = []
    try:
        h.create_json(ATTEMPT / 'predeclared_cases.json', {'cases': list(CASES),
                      'python': str(PYTHON), 'flags': ['-I', '-S', '-B'],
                      'child_task_requires_ack': True, 'retries': 0,
                      'scientific_imports_or_execution': False})
        api = h.WinAPI()
        me = h.HeldProcess(api, os.getpid(), ledger, 'controller_self'); held.append(me)
        me.snapshot()
        for case in CASES:
            results.append(run_case(h, api, me, case))
        h.create_json(ATTEMPT / 'return_intent.json', {'completed_cases': results,
                      'controller_return_intent': 0, 'controller_actual_exit_unknown_here': True,
                      'helper_is_not_scientific_admission': True})
    except BaseException as error:
        ledger.emit('failure', error=repr(error), traceback=traceback.format_exc(),
                    preserved_completed_case_count=len(results), retry=False, no_termination=True)
        raise
    finally:
        errors = close_all(held, [], ledger)
        if errors:
            raise RuntimeError('Controller evidence-handle cleanup incomplete')
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute-benign-fixture', action='store_true')
    parser.add_argument('--role', choices=('parent', 'launcher', 'child'), default='parent')
    parser.add_argument('--case')
    args = parser.parse_args()
    if not args.execute_benign_fixture:
        raise SystemExit('Source-only candidate; root review and explicit benign execution required')
    if os.name != 'nt' or not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        raise SystemExit('Only Windows isolated -I -S -B execution is permitted')
    if not os.path.samefile(sys.executable, PYTHON):
        raise SystemExit('Exact ordinary Python311 interpreter required; no original scientific environment')
    h = helper()
    if args.role == 'parent':
        h.require(args.case is None, 'Parent does not accept arbitrary case directories')
        return parent(h)
    case = Path(args.case).resolve(strict=True)
    h.require(case.parent == ATTEMPT and case.name in {c['name'] for c in CASES}, 'Exact fixture case path required')
    h.require(read_json(case / 'request.json')['name'] == case.name, 'Case request differs')
    return launcher(h, case) if args.role == 'launcher' else child(h, case)


if __name__ == '__main__':
    raise SystemExit(main())
