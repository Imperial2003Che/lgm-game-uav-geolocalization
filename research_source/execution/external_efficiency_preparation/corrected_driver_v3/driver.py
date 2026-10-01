"""Separate primary T6 runner. No registration and no implicit/automatic release.

prepare requires completed predecessor evidence and binds existing checkpoints.
run requires a separately authored allow_run release bound to the exact plan.
worker is the only entry into scientific code and checks its live parent lease.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import secrets
import subprocess
import sys
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract as k

# If a worker's exit cannot be confirmed, retain the private lease and the
# shared handle while this parent survives. OS byte locks end on parent death;
# every future runner must still reject a live foreign Python/GPU owner.
_RETAINED_SHARED_LOCKS = []

def clean_environment():
    env = dict(os.environ)
    for name in ('PYTHONPATH', 'PYTHONHOME'):
        env.pop(name, None)
    env.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_DATASETS_OFFLINE='1',
        HF_HUB_DISABLE_TELEMETRY='1', PYTHONDONTWRITEBYTECODE='1',
        PYTHONHASHSEED='20260730', CUBLAS_WORKSPACE_CONFIG=':4096:8')
    # Device 0 means physical CUDA index 0, not a remapped inherited visibility.
    env.pop('CUDA_VISIBLE_DEVICES', None)
    return env

def assert_no_science_loaded():
    forbidden = ('torch', 'numpy', 'PIL', 'matplotlib', 'transformers', 'torchvision', 'scipy')
    k.require(not [name for name in forbidden if name in sys.modules], 'Parent/preflight imported science')

def verify_release(path, plan_path):
    release, release_record = k.read_bound_json(path)
    _, plan_record = k.read_bound_json(plan_path)
    k.require(release.get('allow_run') is True, 'A separate explicit active release is required')
    k.require(release.get('plan') == plan_record, 'Release is not bound to this exact plan')
    k.verify_record(release_record)
    k.verify_record(plan_record)
    return release, release_record, plan_record

def acquire_shared_lock(path=None):
    """Frozen DAC/CAMP first-byte protocol; never unlink the persistent file."""
    k.require(os.name == 'nt', 'Windows byte-range lock required')
    import msvcrt
    path = k.E / 'latest_baseline_gpu.lock' if path is None else Path(path)
    stream = path.open('a+b')
    try:
        stream.seek(0, os.SEEK_END)
        if not stream.tell():
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        return stream, {'path': str(path.resolve()), 'protocol': 'Windows msvcrt first-byte nonblocking exclusive lock',
                        'persistent_file_not_deleted': True}
    except BaseException:
        stream.close()
        raise

def release_shared_lock(stream):
    import msvcrt
    try:
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
    finally:
        stream.close()

def acquire_lock(path, payload):
    # Exclusive creation, never overwrite stale or foreign leases.
    return k.write_new(path, payload)

def release_own_lock(item):
    path = Path(item['path']).resolve()
    k.require(path == (k.HERE / 'corrected_primary_gpu.lock').resolve(), 'Unexpected private lock target')
    k.verify_record(item)
    path.unlink()


def exited_process_artifacts(case_dir):
    """Called by the parent after child wait and redirected file contexts close."""
    return [k.record(Path(case_dir) / name)
            for name in ('stdout.log', 'stderr.log', 'launch.json', 'launcher.json')]

def fail(output, error, stage):
    proof = {'status': 'failed', 'stage': stage, 'utc': k.now(),
        'exception': type(error).__name__, 'message': str(error),
        'traceback': traceback.format_exc(), 'full_t6_complete': False, 'manuscript_result': False}
    if hasattr(error, 'evidence'):
        proof['actual_scientific_failure_evidence'] = error.evidence
    path = Path(output) / 'failure.json'
    if not path.exists():
        k.write_new(path, proof)

def worker(lease_path, index, expected_lease_sha):
    assert_no_science_loaded()
    lease_path = Path(lease_path).resolve(strict=True)
    lease, lease_record = k.read_bound_json(lease_path)
    k.require(lease_record['sha256'] == expected_lease_sha, 'Worker lease differs from parent launch bytes')
    out = Path(lease['output_root']) / ('case_' + str(index))
    k.require(out.parent == lease_path.parent and out.parent.parent == (k.HERE / 'runs').resolve(),
              'Worker output is not owned by this driver')
    k.require(type(index) is int and 0 <= index < 4 and out.is_dir(), 'Invalid worker case directory')
    stage = 'worker_preflight'
    try:
        k.require(Path(sys.executable).resolve() == k.PYTHON.resolve(), 'Worker is not in the frozen baseline environment')
        rows = k.process_snapshot()
        ancestors = k.self_and_verified_ancestors(rows)
        owner = lease['parent_identity']
        k.require(owner['ProcessId'] in ancestors and owner['ProcessId'] != os.getpid(), 'Live parent is not this worker ancestor')
        k.require(k.process_identity(owner['ProcessId'], rows) == owner, 'Parent process identity changed')
        k.require(lease['schema'] == 'corrected-primary-t6-lease.v2', 'Wrong lease protocol')
        k.require(len(lease['locks']) == 1 and Path(lease['locks'][0]['path']).resolve() ==
                  (k.HERE / 'corrected_primary_gpu.lock').resolve(), 'Worker requires exactly one private lease lock')
        private, private_record = k.read_bound_json(lease['locks'][0]['path'])
        k.require(private_record == lease['locks'][0], 'Private lock bytes changed')
        for key in ('token', 'parent_identity', 'output_root', 'plan', 'release'):
            k.require(private[key] == lease[key], 'Private lease binding differs: ' + key)
        shared = lease['shared_gpu_lock']
        k.require(shared['path'] == str((k.E / 'latest_baseline_gpu.lock').resolve()) and
                  shared['protocol'] == 'Windows msvcrt first-byte nonblocking exclusive lock' and
                  shared['owner'] == owner, 'Shared-lock declaration differs from actual live parent')
        parent_allowlist = ancestors
        k.no_foreign_python(rows, parent_allowlist)
        k.gpu_idle()
        manifest = k.frozen_sources()
        plan_path = Path(lease['plan']['path'])
        k.verify_record(lease['plan'])
        k.verify_record(lease['release'])
        _, release_record, plan_record = verify_release(lease['release']['path'], plan_path)
        k.require(release_record == lease['release'] and plan_record == lease['plan'], 'Plan/release differ from captured lease')
        plan = k.verify_plan(plan_path, manifest, expected_record=plan_record)
        memory = k.resource_gate(plan, index)
        k.predecessors(manifest, k.process_snapshot())
        identity = k.process_identity(os.getpid(), k.process_snapshot())
        k.write_new(out / 'actual_worker_identity.json', {'identity': identity,
            'parent_identity': owner, 'verified_ancestor_pids': sorted(ancestors),
            'memory_at_gate': memory, 'scientific_modules_loaded_before_gate': [],
            'lease': lease_record, 'private_lease': private_record, 'shared_lock_is_held_by_verified_live_parent': True,
            'case_index': index})
        assert_no_science_loaded()
        for captured in (lease_record, private_record, plan_record, release_record):
            k.verify_record(captured)
        stage = 'scientific_case'
        # Exact, reviewed source is imported only after every preceding gate.
        from science import run_case
        result = run_case(plan, index, out)
        stage = 'worker_post_science_control_revalidation'
        k.require(k.process_identity(owner['ProcessId'], k.process_snapshot()) == owner, 'Parent exited or identity changed during science')
        for captured in (lease_record, private_record, plan_record, release_record):
            k.verify_record(captured)
        k.write_new(out / 'case_result.json', result)
        return 0
    except BaseException as error:
        fail(out, error, stage)
        return 1

def run(plan_path, release_path, name):
    assert_no_science_loaded()
    plan_path = Path(plan_path).resolve(strict=True)
    release_path = Path(release_path).resolve(strict=True)
    _, release_record, plan_record = verify_release(release_path, plan_path)
    manifest = k.frozen_sources()
    plan = k.verify_plan(plan_path, manifest, expected_record=plan_record)
    rows = k.process_snapshot()
    predecessor = k.predecessors(manifest, rows)
    k.no_foreign_python(rows, k.self_and_verified_ancestors(rows))
    k.gpu_idle()
    memory = k.resource_gate(plan, 0)
    output = k.scoped_new(k.HERE / 'runs', name)
    locks, active_child = [], None
    shared_stream = None
    children_confirmed_exited = True
    stage = 'exclusive_locks'
    try:
        owner = k.process_identity(os.getpid(), rows)
        lease_base = {'schema': 'corrected-primary-t6-lease.v2', 'token': secrets.token_hex(32),
            'created_utc': k.now(), 'parent_identity': owner, 'output_root': str(output),
            'plan': plan_record, 'release': release_record}
        for path in (k.HERE / 'corrected_primary_gpu.lock',):
            locks.append(acquire_lock(path, lease_base))
        shared_stream, shared_evidence = acquire_shared_lock()
        shared_evidence['owner'] = owner
        lease = {**lease_base, 'locks': locks, 'predecessor_evidence': predecessor,
                 'memory_before_children': memory, 'shared_gpu_lock': shared_evidence}
        k.write_new(output / 'lease.json', lease)
        stored_lease, lease_record = k.read_bound_json(output / 'lease.json')
        k.require(stored_lease == lease, 'Lease file differs from the intended parent payload')
        case_results, case_exit_records = [], []
        for index, case in enumerate(plan['cases']):
            stage = 'case_' + str(index)
            rows = k.process_snapshot()
            k.no_foreign_python(rows, k.self_and_verified_ancestors(rows))
            k.predecessors(manifest, rows)
            k.gpu_idle()
            k.resource_gate(plan, index)
            for captured in (lease_record, plan_record, release_record, *locks):
                k.verify_record(captured)
            case_dir = output / stage
            case_dir.mkdir(exist_ok=False)
            command = [str(k.PYTHON), '-B', str(k.HERE / 'driver.py'), 'worker',
                       '--lease', str(output / 'lease.json'), '--lease-sha256', lease_record['sha256'], '--case-index', str(index)]
            k.write_new(case_dir / 'launch.json', {'command': command, 'cwd': str(k.HERE),
                'created_utc': k.now(), 'case': case, 'driver': k.record(k.HERE / 'driver.py')})
            with (case_dir / 'stdout.log').open('xb') as stdout, (case_dir / 'stderr.log').open('xb') as stderr:
                children_confirmed_exited = False
                active_child = subprocess.Popen(command, cwd=str(k.HERE), env=clean_environment(),
                    stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                launcher_pid = active_child.pid
                k.write_new(case_dir / 'launcher.json', {'pid': launcher_pid, 'started_utc': k.now()})
                exit_code = active_child.wait()
                active_child = None
            rows = k.process_snapshot()
            receipt_path = case_dir / 'actual_worker_identity.json'
            receipt = k.read(receipt_path) if receipt_path.is_file() else None
            if receipt:
                identity = receipt['identity']
                k.require(k.exited(identity['ProcessId'], identity['CreatedUtc'], rows), 'Actual worker is still alive')
            k.no_foreign_python(rows, k.self_and_verified_ancestors(rows))
            k.gpu_idle()
            children_confirmed_exited = True
            exit_record = k.write_new(case_dir / 'process_exit.json', {'launcher_pid': launcher_pid, 'exit_code': exit_code,
                'actual_worker': receipt, 'observed_utc': k.now(), 'foreign_python_and_gpu_owners_absent': True,
                'closed_process_artifacts': exited_process_artifacts(case_dir),
                'log_seal_boundary': 'parent after child wait and stdout/stderr context exit'})
            k.require(exit_code == 0 and receipt is not None, 'Scientific worker failed; original failure/logs retained')
            for captured in (lease_record, plan_record, release_record, *locks):
                k.verify_record(captured)
            result = k.read(case_dir / 'case_result.json')
            k.require(result.get('status') == 'completed_primary_case_only' and result['full_t6_complete'] is False,
                      'Case result is incomplete or mislabelled')
            k.require((result['dataset'], result['variant']) == k.CASES[index], 'Actual case differs from registry')
            for item in result['output_artifacts']:
                k.verify_record(item)
            case_results.append(k.record(case_dir / 'case_result.json'))
            case_exit_records.append(exit_record)
        k.require(len(case_results) == 4, 'Four primary cases have not completed')
        total_tasks = sum(k.read(x['path'])['task_count'] for x in case_results)
        k.require(total_tasks == 22, 'Expected 22 official primary task checks')
        result = {'status': 'completed_corrected_primary_efficiency_only', 'completed_utc': k.now(),
            'cases': case_results, 'process_exits': case_exit_records,
            'official_cached_protocol_task_checks': total_tasks,
            'full_t6_complete': False, 'manuscript_result': False,
            'external_t1_efficiency_fits_measured': 0,
            'missing': ['seven matched external T1 efficiency fits', 'newer external comparator efficiency',
                        'dataset-wide online CLIP accuracy (not claimed by this selected-query driver)']}
        for captured in (lease_record, plan_record, release_record, *locks):
            k.verify_record(captured)
        k.write_new(output / 'result.json', result)
        return output
    except BaseException as error:
        fail(output, error, stage)
        raise
    finally:
        # Never release exclusivity while an interrupted worker may still run.
        if children_confirmed_exited and (active_child is None or active_child.poll() is not None):
            try:
                if shared_stream is not None:
                    release_shared_lock(shared_stream)
            finally:
                for item in reversed(locks):
                    release_own_lock(item)
        elif shared_stream is not None:
            _RETAINED_SHARED_LOCKS.append(shared_stream)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    prepare = sub.add_parser('prepare')
    prepare.add_argument('--name', required=True)
    launch = sub.add_parser('run')
    launch.add_argument('--plan', required=True)
    launch.add_argument('--release', required=True)
    launch.add_argument('--name', required=True)
    child = sub.add_parser('worker')
    child.add_argument('--lease', required=True)
    child.add_argument('--case-index', type=int, required=True)
    child.add_argument('--lease-sha256', required=True)
    args = parser.parse_args(argv)
    if args.mode == 'prepare':
        print(k.prepare(args.name))
    elif args.mode == 'run':
        print(run(args.plan, args.release, args.name))
    else:
        return worker(args.lease, args.case_index, args.lease_sha256)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
