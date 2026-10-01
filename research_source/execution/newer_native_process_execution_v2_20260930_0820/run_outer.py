"""One root-authorized ordinary-Python CPU fixture; not scientific admission."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

HERE = Path(__file__).resolve().parent
EX = HERE.parent
SRC = EX / 'external_efficiency_preparation' / 'newer_native_process_evidence_v2'
PYTHON = Path(r'C:\Users\17703\AppData\Local\Programs\Python\Python311\python.exe')
ATTEMPT = HERE / 'outer_runtime_attempt_v1'
DECISION = HERE / 'ROOT_BENIGN_FIXTURE_DECISION.json'

def binding(path):
    path = Path(path)
    raw = path.read_bytes()
    if len(raw) >= 100000:
        raise RuntimeError('Only bounded small control/source files are permitted')
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def create(path, value):
    with Path(path).open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, sort_keys=True,
                                allow_nan=False, indent=2) + '\n').encode('utf-8'))
        stream.flush()
        os.fsync(stream.fileno())

def main():
    if sys.argv[1:] != ['--execute-one-benign-fixture']:
        raise RuntimeError('Explicit single benign-fixture argument required')
    if os.name != 'nt' or not os.path.samefile(sys.executable, PYTHON):
        raise RuntimeError('Exact installed Windows Python311 required')
    if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        raise RuntimeError('Isolated -I -S -B invocation required')
    decision = json.loads(DECISION.read_bytes())
    if decision['schema'] != 'root-one-benign-process-fixture-decision.v1' or decision['execute'] is not True:
        raise RuntimeError('No benign execution decision')
    if decision['scientific_admission'] is not False or decision['maximum_fixture_attempts'] != 1:
        raise RuntimeError('Wrong execution scope')
    for item in decision['small_inputs']:
        if binding(item['path']) != item:
            raise RuntimeError('Changed pinned source/review/observation: ' + item['path'])
    if binding(__file__) != decision['outer_source']:
        raise RuntimeError('Outer caller source differs')
    if (SRC / 'runtime_attempt_v1').exists() or ATTEMPT.exists():
        raise RuntimeError('Any existing fixture or outer attempt refuses replay')
    ATTEMPT.mkdir(exist_ok=False)
    create(ATTEMPT / 'entry.json', {'decision': binding(DECISION), 'source': binding(__file__),
                                  'scope': 'ordinary Python311 CPU two-case fixture only',
                                  'scientific_admission': False, 'self_exit_unknown': True})
    held = []
    streams = []
    proc = None
    ledger = None
    code = 91
    try:
        spec = importlib.util.spec_from_file_location('root_benign_evidence', SRC / 'windows_process_evidence.py')
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        ledger = helper.Ledger(ATTEMPT, 'outer')
        api = helper.WinAPI()
        parent = helper.HeldProcess(api, os.getpid(), ledger, 'outer_self')
        held.append(parent)
        parent.snapshot()
        argv = [str(PYTHON), '-I', '-S', '-B', str(SRC / 'benign_fixture.py'), '--execute-benign-fixture']
        expected_command = subprocess.list2cmdline(argv)
        stdout = (ATTEMPT / 'controller.stdout.log').open('xb')
        streams.append(stdout)
        stderr = (ATTEMPT / 'controller.stderr.log').open('xb')
        streams.append(stderr)
        proc = subprocess.Popen(argv, cwd=str(SRC), stdin=subprocess.DEVNULL,
                                stdout=stdout, stderr=stderr, close_fds=True,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        ledger.emit('controller_spawned', actual_popen_pid=proc.pid, argv=argv,
                    declared_command_line=expected_command,
                    popen_creation_handle_rights_unspecified=True)
        controller = helper.HeldProcess(api, proc.pid, ledger, 'fixture_controller_external')
        held.append(controller)
        controller.confirm_twice(expected_command, PYTHON, parent)
        observed = controller.wait(60000)
        helper.require(observed is not None, 'Controller actual exit not observed in bounded wait')
        helper.require(observed['exit_code_unsigned_dword'] == 0, 'Actual fixture controller failed')
        popen_code = proc.wait(timeout=0)
        helper.require(popen_code == 0, 'Separate Popen controller exit differs')
        for stream in streams:
            stream.close()
        ledger.emit('controller_streams_closed', stream_count=len(streams), all_closed=all(f.closed for f in streams))
        logs = [helper.seal_closed_log(api, path, [controller], streams)
                for path in [ATTEMPT / 'controller.stdout.log', ATTEMPT / 'controller.stderr.log']]
        create(ATTEMPT / 'CONTROLLER_EXIT_AND_CLOSED_LOGS.json', {
            'schema': 'root-benign-fixture-controller-exit.v1', 'decision': binding(DECISION),
            'controller_actual_held_exit': observed, 'controller_popen_exit': popen_code,
            'closed_logs': logs, 'fixture_attempt': str(SRC / 'runtime_attempt_v1'),
            'scope': 'Fixture controller real exit only; inner actors and whole fixture require separate review',
            'outer_self_actual_exit_unknown_in_this_record': True, 'scientific_admission': False})
        code = 0
    except BaseException as error:
        code = 92
        create(ATTEMPT / 'OUTER_FAILURE.json', {
            'error': repr(error), 'traceback': traceback.format_exc(),
            'controller_pid_if_spawned': proc.pid if proc else None,
            'held_exits': [p.exit_observation for p in held],
            'partial_attempt_preserved': True, 'replay_or_kill_authorized': False,
            'absence_is_not_exit_evidence': True, 'scientific_admission': False})
    finally:
        errors = []
        for stream in streams:
            try:
                stream.close()
            except BaseException as error:
                errors.append({'resource': 'stream', 'error': repr(error)})
        for process in reversed(held):
            try:
                process.close()
            except BaseException as error:
                errors.append({'resource': process.label, 'error': repr(error)})
        if errors:
            code = 94
        create(ATTEMPT / 'OUTER_RETURN_INTENT_AND_CLEANUP.json', {
            'return_intent': code, 'cleanup_errors': errors,
            'own_redirect_streams_closed': all(f.closed for f in streams),
            'evidence_handles_closed': all(p.handle is None for p in held),
            'own_actual_exit_unknown': True, 'does_not_terminate_processes': True,
            'scientific_admission': False})
    print(json.dumps({'return_intent': code, 'outer_attempt': str(ATTEMPT),
                      'fixture_attempt': str(SRC / 'runtime_attempt_v1')}, ensure_ascii=False))
    return code

if __name__ == '__main__':
    raise SystemExit(main())
