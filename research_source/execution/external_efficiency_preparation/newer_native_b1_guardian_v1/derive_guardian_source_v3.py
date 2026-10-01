"""Offline minimal source retention repair; no guardian import/API/runtime."""
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED = 'c2dbebea631de5cf4cb4998408309effad019dd62a1f39c85d0be351db8a81fa'


def replace(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError('Expected unique source block missing')
    return text.replace(old, new, 1)


def main():
    raw = (HERE / 'guardian_v2.py').read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED:
        raise RuntimeError('Sealed v2 source differs')
    original = raw.decode('utf-8')
    value = replace(original, '    locked: bool = False\n',
                    '    locked: bool = False\n    acquisition_started: bool = False\n')
    value = replace(value, '        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)\n',
                    '        self.acquisition_started = True  # before API; error is not proof no lock acquired\n        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)\n')
    value = replace(value, '    unobserved_descendants: bool = False\n',
                    '    unobserved_descendants: bool = False\n    retention_failures: list = field(default_factory=list)\n    retention_failure_count: int = 0\n')
    start = value.index('def _failure_handoff(context, error):\n')
    finish = value.index('\n\ndef _run_guardian(plan_record):\n', start)
    old = value[start:finish]
    new = '''def _remember_retention_failure(context, phase, error):
    _closed(context, phase, error)
    context.retention_failure_count += 1
    record = {'phase': phase, 'error': str(error)[:4096],
              'count': context.retention_failure_count,
              'stored_detail_scope': 'first64 in-memory details; counter retains later failures',
              'exit_or_release_proven': False}
    if len(context.retention_failures) < 64:
        context.retention_failures.append(record)
    try:
        context.ledger.emit('retention_operation_failed', **record)
    except BaseException as log_error:
        context.retention_failure_count += 1
        if len(context.retention_failures) < 64:
            context.retention_failures.append({'phase': 'retention_ledger_write',
                'error': str(log_error)[:4096], 'count': context.retention_failure_count,
                'persistent_error_record_unavailable': True, 'exit_or_release_proven': False})


def _setup_failure_retention(initial_dir, lock, error):
    _closed(initial_dir, lock, error)
    # Even a lock API failure after acquisition_started is not proof that the
    # OS byte lock was never obtained. Preserve owner/stream; no default close.
    recording_error = None
    try:
        _new_record(initial_dir / 'guardian_setup_partial_failure.json', {
            'schema': 'newer-native-b1-guardian-setup-partial-failure.v1',
            'error': str(error), 'traceback': traceback.format_exc(),
            'scientific_spawn_reached': False, 'lock_acquisition_started': lock.acquisition_started,
            'lock_acquisition_returned': lock.locked,
            'retained_stream_created': lock.stream is not None,
            'shared_lock_release_authorized': False, 'actual_guardian_exit_unknown': True})
    except BaseException as record_error:
        recording_error = str(record_error)
    # In-memory error remains reachable if persistent writing failed. This is
    # not successful diagnostics/exit proof and does not unlock anything.
    retained_failure = {'initial_error': str(error), 'recording_error': recording_error,
                        'lock_stream': lock.stream, 'release_authorized': False}
    while True:
        try:
            time.sleep(1)
        except BaseException as wait_error:
            retained_failure['latest_wait_error'] = str(wait_error)


def _failure_handoff(context, error):
    _closed(context, error)
    try:
        _new_record(context.directory / 'failure_partial.json', {
            'schema': 'newer-native-b1-guardian-partial-failure.v1',
            'error': str(error), 'traceback': traceback.format_exc(),
            'captured_identities': [x.identity for x in context.processes],
            'captured_exits': [x.exit_observation for x in context.processes],
            'spawned_pids': [x.pid for x in context.popen_processes],
            'unobserved_descendants': context.unobserved_descendants,
            'shared_lock_release_authorized': False, 'measurement_admitted': False,
            'own_reference_or_stream_cleanup_is_not_child_exit': True})
    except BaseException as record_error:
        _remember_retention_failure(context, 'initial_partial_write', record_error)
    # Running incident retention only, never launch a native slot just to wait
    # for initial GPU admission. Never kill/delete/rollback/retry an attempt.
    # Own open streams and unobserved descendants remain blocking facts; this
    # repair does not close them or manufacture an empty quiet observation.
    while True:
        try:
            for actor in context.processes:
                if actor.exit_observation is None:
                    try:
                        actor.wait(1000)
                    except BaseException as observation_error:
                        _remember_retention_failure(context, 'held_exit_wait', observation_error)
            try:
                context.byte_lock.release_after_observation(context)
            except BaseException as boundary_error:
                _remember_retention_failure(context, 'actual_terminal_boundary_or_release', boundary_error)
                time.sleep(1)
                continue
            return
        except BaseException as retention_error:
            # An API, ledger, timestamp, sleep or record failure cannot escape
            # the owner-retention loop and thereby release locks by process exit.
            try:
                _remember_retention_failure(context, 'retention_loop', retention_error)
            except BaseException as second_error:
                # Persistent diagnostics can be unavailable; preserve actual
                # unknown state and retain the owner instead of claiming proof.
                context.retention_failure_count += 1
                context.last_unrecorded_retention_error = str(second_error)
            continue
'''
    value = replace(value, old, new)
    value = replace(value, '    lock = OwnedByteLock()\n    lock.acquire()\n    context = None\n    try:\n',
                    '    lock = OwnedByteLock()\n    context = None\n    try:\n        lock.acquire()\n')
    old_start = value.index('        if context is None:\n', value.index('def _run_guardian'))
    old_end = value.index('        _failure_handoff(context, error)\n', old_start)
    setup_old = value[old_start:old_end]
    value = replace(value, setup_old,
                    '        if context is None:\n            _setup_failure_retention(initial_dir, lock, error)\n            raise IncompleteIntegration(\'Setup retention unexpectedly returned; no execution may continue\')\n')
    output = value.encode('utf-8')
    delta = ''.join(difflib.unified_diff(original.splitlines(True), value.splitlines(True),
                    fromfile='guardian_v2.py', tofile='guardian_v3.py')).encode('utf-8')
    for path, body in ((HERE / 'guardian_v3.py', output), (HERE / 'guardian_v2_to_v3.patch', delta)):
        with path.open('xb') as stream:
            stream.write(body)
            stream.flush()
    result = {'schema': 'guardian-v3-offline-source-derivation.v1',
              'input': {'path': str(HERE / 'guardian_v2.py'), 'bytes': len(raw), 'sha256': EXPECTED},
              'outputs': [{'path': str(HERE / name), 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}
                         for name, body in (('guardian_v3.py', output), ('guardian_v2_to_v3.patch', delta))],
              'original_v2_and_manifest_unchanged': True,
              'guardian_imported_tested_or_executed': False,
              'runtime_API_native_or_scientific_calls': False}
    with (HERE / 'SOURCE_DERIVATION_V3.json').open('xb') as stream:
        stream.write((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
