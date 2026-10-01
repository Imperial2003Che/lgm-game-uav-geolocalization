"""One stdlib parent; seven native isolated workers; no automatic replay."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import execution_contract as c
import aggregate_results as a

@contextmanager
def controller_lock():
    _, k, _, _ = c.runtime_helpers()
    k.require(os.name == 'nt', 'Windows execution controller required')
    import msvcrt
    with (HERE / 'controller.lock').open('a+b') as stream:
        stream.seek(0, os.SEEK_END)
        if not stream.tell():
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)

def require_exited_zero(launcher_code, worker_code):
    _, k, _, _ = c.runtime_helpers()
    k.require(type(launcher_code) is int and type(worker_code) is int and launcher_code == worker_code == 0,
              'Launcher or actual native worker failed or is still active; stop without aggregate')

def launch_slot(index, binding, plan, plan_record, release_record, parent, root, batch_name, execution_source):
    native, k, b, life = c.runtime_helpers()
    control = root / ('slot_' + str(index))
    control.mkdir(exist_ok=False)
    native_name = batch_name + '_slot_' + str(index)
    native_output = (c.NATIVE / 'runs' / native_name).resolve()
    k.require(not native_output.exists(), 'Native output already exists; retain and review instead of replay')
    before = c.before_slot(plan, binding, (plan_record, release_record, execution_source))
    request = {'schema': 'external-t1-slot-request.v1', 'slot_index': index, 'run_id': binding['row']['run_id'],
        'plan': plan_record, 'release': release_record, 'parent': parent, 'control_directory': str(control),
        'native_name': native_name, 'native_output': str(native_output),
        'execution_source': execution_source, 'before_slot': before}
    request_record = c.atomic_new_json(control / 'request.json', request)
    executable = b.native_environment(binding['row']['framework'])['executable']
    command = [executable, '-B', str(HERE / 'slot_entry.py'), '--request', str(control / 'request.json'),
        '--request-sha256', request_record['sha256']]
    process = launcher_handle = worker_handle = None
    identity = None
    phase = 'spawn_native_identity_shim'
    launcher_code = worker_code = None
    try:
        for item in (request_record, plan_record, release_record):
            k.verify_record(item)
        with (control / 'stdout.log').open('xb') as out, (control / 'stderr.log').open('xb') as err:
            process = subprocess.Popen(command, cwd=str(HERE), env=c.process_environment(binding['row']['seed']),
                stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            launcher_handle = life.ProcessObservation(process.pid, existing_handle=process._handle)
            launcher = {'pid': process.pid, 'started_utc': launcher_handle.started_utc}
            launcher_record = c.atomic_new_json(control / 'launcher.json', {'launcher': launcher, 'command': command,
                'request': request_record, 'environment': {key: c.process_environment(binding['row']['seed']).get(key)
                    for key in ('PYTHONHASHSEED', 'CUBLAS_WORKSPACE_CONFIG', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'CUDA_VISIBLE_DEVICES')}})
            deadline = time.monotonic() + 60
            while not (control / 'worker_identity.json').exists():
                k.require(process.poll() is None, 'Launcher exited before actual worker handshake')
                k.require(time.monotonic() < deadline, 'Actual native worker handshake timeout')
                time.sleep(0.05)
            phase = 'retain_actual_worker_handle'
            identity, identity_record = c.bound(control / 'worker_identity.json')
            c.validate_identity(identity, request_record, parent, launcher)
            worker_handle = life.ProcessObservation(identity['pid'])
            k.require(worker_handle.started_utc == identity['started_utc'], 'Retained worker handle does not match handshake')
            for item in (request_record, identity_record, plan_record, release_record):
                k.verify_record(item)
            c.atomic_new_json(control / 'parent_observed.json', {'request': request_record, 'identity': identity_record, 'parent': parent})
            phase = 'wait_for_real_launcher_and_worker_exit'
            launcher_code = process.wait()
            # Still inside stdout/stderr contexts. Do not hash/close while an
            # actual redirected writer is live even if the launcher returned.
            worker_code = worker_handle.exit_code()
            until = time.monotonic() + 5
            while worker_code == 259 and time.monotonic() < until:
                time.sleep(0.05)
                worker_code = worker_handle.exit_code()
            require_exited_zero(launcher_code, worker_code)
            k.require(launcher_handle.exit_code() == launcher_code, 'Popen/retained launcher exit code differ')
        phase = 'closed_logs_and_native_result_verification'
        intent, intent_record = c.bound(control / 'return_intent.json')
        k.require(intent['request'] == request_record and intent['identity'] == identity_record and intent['return_intent'] == 0, 'Shim return intent belongs to another launch')
        result, result_record = c.bound(native_output / 'result.json', intent['native_result'])
        k.require(result['status'] == 'completed_external_t1_slot_only' and result['owner'] == identity['cim_identity'] and
                  result['run_id'] == binding['row']['run_id'] and result['task_count'] == 10 and result['checkpoint'] == binding['checkpoint'],
                  'Native result does not belong to actual completed worker/checkpoint')
        for item in (request_record, identity_record, launcher_record, intent_record, plan_record, release_record, request['execution_source']):
            k.verify_record(item)
        rows = k.process_snapshot()
        k.no_foreign_python(rows, k.self_and_verified_ancestors(rows))
        k.gpu_idle()
        lifecycle = {'schema': 'external-t1-slot-lifecycle.v1', 'status': 'completed', 'request': request_record,
            'launcher': launcher, 'actual_worker': identity, 'launcher_exit_code': launcher_code,
            'actual_worker_exit_code': worker_code, 'native_result': result_record, 'finished_utc': k.now(),
            'retained_actual_handles_used': True, 'closed_log_boundary': 'both actual processes exit0 then parent redirected contexts closed',
            'no_foreign_python_or_gpu_owners': True}
        lifecycle_record = c.atomic_new_json(control / 'lifecycle.json', lifecycle)
        closed = [k.record(control / name) for name in ('request.json', 'launcher.json', 'worker_identity.json',
            'parent_observed.json', 'return_intent.json', 'stdout.log', 'stderr.log', 'lifecycle.json')]
        return {'slot_index': index, 'run_id': binding['row']['run_id'], 'status': 'completed',
            'launcher_exit_code': launcher_code, 'worker_exit_code': worker_code, 'worker_identity': identity,
            'native_output': str(native_output), 'native_result': result_record, 'lifecycle': lifecycle_record,
            'control_directory': str(control), 'closed_control_artifacts': closed}
    except BaseException as error:
        proof = {'phase': phase, 'run_id': binding['row']['run_id'], 'request': request_record, 'type': type(error).__name__,
            'error': str(error), 'traceback': traceback.format_exc(), 'utc': k.now(), 'launcher_exit_code': launcher_code,
            'worker_exit_code': worker_code, 'actual_worker_identity': identity,
            'failed_logs_not_sealed_as_closed': True, 'full_t6_complete': False}
        if process is not None:
            proof['launcher_still_alive'] = process.poll() is None
        if worker_handle is not None:
            proof['actual_worker_exit_code_at_failure'] = worker_handle.exit_code()
        c.atomic_new_json(control / 'controller_failure.json', proof)
        raise
    finally:
        if worker_handle is not None:
            worker_handle.close()
        if launcher_handle is not None:
            launcher_handle.close()

def run(plan_path, release_path, name, plan_sha256, release_sha256):
    c.no_science()
    c.source_manifest()
    native, k, b, life = c.runtime_helpers()
    with controller_lock():
        root = k.scoped_new(HERE / 'runs', name)
        phase = 'actual_seven_slot_plan_release_admission'
        slots = []
        try:
            _, requested_plan = c.bound(plan_path)
            _, requested_release = c.bound(release_path)
            k.require(requested_plan['sha256'] == plan_sha256 and requested_release['sha256'] == release_sha256, 'Caller exact plan/release SHA differs')
            plan, release, plan_record, release_record, bindings = c.admit(plan_path, release_path, requested_plan, requested_release)
            execution_source = k.record(HERE / 'SOURCE_MANIFEST.json')
            parent = {'pid': os.getpid(), 'started_utc': life.process_started(os.getpid())}
            k.require(parent['started_utc'] is not None, 'Actual controller identity unavailable')
            admission_record = c.atomic_new_json(root / 'admission.json', {'schema': 'external-t1-seven-slot-admission.v1',
                'plan': plan_record, 'release': release_record, 'parent': parent,
                'execution_source': execution_source, 'ordered_run_ids': [x['row']['run_id'] for x in bindings]})
            for index, binding in enumerate(bindings):
                phase = 'slot_' + str(index)
                for earlier in slots:
                    k.verify_record(earlier['native_result'])
                    k.verify_record(earlier['lifecycle'])
                k.verify_record(admission_record)
                slots.append(launch_slot(index, binding, plan, plan_record, release_record, parent, root, name, execution_source))
            phase = 'verify_all_seven_slots_and_seventy_tasks'
            for artifact in (admission_record, plan_record, release_record, execution_source):
                k.verify_record(artifact)
            # Recheck all seven actual checkpoint/finished-evaluation bindings.
            _, _, _, _, current_bindings = c.admit(plan_path, release_path, plan_record, release_record)
            k.require(current_bindings == bindings, 'Completed source bindings changed during serial execution')
            result = a.aggregate(plan, plan_record, release_record, bindings, slots, root, parent, execution_source)
            return result
        except BaseException as error:
            c.atomic_new_json(root / 'failure.json', {'phase': phase, 'type': type(error).__name__, 'error': str(error),
                'traceback': traceback.format_exc(), 'utc': k.now(), 'completed_slot_records': slots,
                'automatic_retry_or_replay': False, 'full_t6_complete': False})
            raise

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--release-sha256', required=True)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    print(run(args.plan, args.release, args.name, args.plan_sha256, args.release_sha256))

if __name__ == '__main__':
    main()
