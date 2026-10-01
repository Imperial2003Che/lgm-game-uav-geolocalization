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
    release = k.read(path)
    k.require(release.get('allow_run') is True, 'A separate explicit active release is required')
    k.require(release.get('plan') == k.record(plan_path), 'Release is not bound to this exact plan')
    return release

def acquire_lock(path, payload):
    # Exclusive creation, never overwrite stale or foreign leases.
    return k.write_new(path, payload)

def release_own_lock(item):
    k.verify_record(item)
    path = Path(item['path']).resolve()
    k.require(path in {(k.E / 'latest_baseline_gpu.lock').resolve(),
                      (k.HERE / 'corrected_primary_gpu.lock').resolve()}, 'Unexpected lock target')
    path.unlink()

def fail(output, error, stage):
    proof = {'status': 'failed', 'stage': stage, 'utc': k.now(),
        'exception': type(error).__name__, 'message': str(error),
        'traceback': traceback.format_exc(), 'full_t6_complete': False, 'manuscript_result': False}
    if hasattr(error, 'evidence'):
        proof['actual_scientific_failure_evidence'] = error.evidence
    path = Path(output) / 'failure.json'
    if not path.exists():
        k.write_new(path, proof)

def worker(lease_path, index):
    assert_no_science_loaded()
    lease_path = Path(lease_path).resolve(strict=True)
    lease = k.read(lease_path)
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
        for item in lease['locks']:
            k.verify_record(item)
        parent_allowlist = ancestors
        k.no_foreign_python(rows, parent_allowlist)
        k.gpu_idle()
        manifest = k.frozen_sources()
        plan_path = Path(lease['plan']['path'])
        k.verify_record(lease['plan'])
        k.verify_record(lease['release'])
        verify_release(lease['release']['path'], plan_path)
        plan = k.verify_plan(plan_path, manifest)
        memory = k.resource_gate(plan, index)
        k.predecessors(manifest, k.process_snapshot())
        identity = k.process_identity(os.getpid(), k.process_snapshot())
        k.write_new(out / 'actual_worker_identity.json', {'identity': identity,
            'parent_identity': owner, 'verified_ancestor_pids': sorted(ancestors),
            'memory_at_gate': memory, 'scientific_modules_loaded_before_gate': [],
            'lease': k.record(lease_path), 'case_index': index})
        assert_no_science_loaded()
        stage = 'scientific_case'
        # Exact, reviewed source is imported only after every preceding gate.
        from science import run_case
        result = run_case(plan, index, out)
        k.write_new(out / 'case_result.json', result)
        return 0
    except BaseException as error:
        fail(out, error, stage)
        return 1

def run(plan_path, release_path, name):
    assert_no_science_loaded()
    plan_path = Path(plan_path).resolve(strict=True)
    release_path = Path(release_path).resolve(strict=True)
    verify_release(release_path, plan_path)
    manifest = k.frozen_sources()
    plan = k.verify_plan(plan_path, manifest)
    rows = k.process_snapshot()
    predecessor = k.predecessors(manifest, rows)
    k.no_foreign_python(rows, k.self_and_verified_ancestors(rows))
    k.gpu_idle()
    memory = k.resource_gate(plan, 0)
    output = k.scoped_new(k.HERE / 'runs', name)
    locks, active_child = [], None
    children_confirmed_exited = True
    stage = 'exclusive_locks'
    try:
        owner = k.process_identity(os.getpid(), rows)
        lease_base = {'schema': 'corrected-primary-t6-lease.v1', 'token': secrets.token_hex(32),
            'created_utc': k.now(), 'parent_identity': owner, 'output_root': str(output),
            'plan': k.record(plan_path), 'release': k.record(release_path)}
        for path in (k.E / 'latest_baseline_gpu.lock', k.HERE / 'corrected_primary_gpu.lock'):
            locks.append(acquire_lock(path, lease_base))
        lease = {**lease_base, 'locks': locks, 'predecessor_evidence': predecessor,
                 'memory_before_children': memory}
        k.write_new(output / 'lease.json', lease)
        case_results = []
        for index, case in enumerate(plan['cases']):
            stage = 'case_' + str(index)
            rows = k.process_snapshot()
            k.no_foreign_python(rows, k.self_and_verified_ancestors(rows))
            k.predecessors(manifest, rows)
            k.gpu_idle()
            k.resource_gate(plan, index)
            case_dir = output / stage
            case_dir.mkdir(exist_ok=False)
            command = [str(k.PYTHON), '-B', str(k.HERE / 'driver.py'), 'worker',
                       '--lease', str(output / 'lease.json'), '--case-index', str(index)]
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
            k.write_new(case_dir / 'process_exit.json', {'launcher_pid': launcher_pid, 'exit_code': exit_code,
                'actual_worker': receipt, 'observed_utc': k.now(), 'foreign_python_and_gpu_owners_absent': True})
            k.require(exit_code == 0 and receipt is not None, 'Scientific worker failed; original failure/logs retained')
            result = k.read(case_dir / 'case_result.json')
            k.require(result.get('status') == 'completed_primary_case_only' and result['full_t6_complete'] is False,
                      'Case result is incomplete or mislabelled')
            k.require((result['dataset'], result['variant']) == k.CASES[index], 'Actual case differs from registry')
            for item in result['output_artifacts']:
                k.verify_record(item)
            case_results.append(k.record(case_dir / 'case_result.json'))
        k.require(len(case_results) == 4, 'Four primary cases have not completed')
        total_tasks = sum(k.read(x['path'])['task_count'] for x in case_results)
        k.require(total_tasks == 22, 'Expected 22 official primary task checks')
        result = {'status': 'completed_corrected_primary_efficiency_only', 'completed_utc': k.now(),
            'cases': case_results, 'official_cached_protocol_task_checks': total_tasks,
            'full_t6_complete': False, 'manuscript_result': False,
            'external_t1_efficiency_fits_measured': 0,
            'missing': ['seven matched external T1 efficiency fits', 'newer external comparator efficiency',
                        'dataset-wide online CLIP accuracy (not claimed by this selected-query driver)']}
        k.write_new(output / 'result.json', result)
        return output
    except BaseException as error:
        fail(output, error, stage)
        raise
    finally:
        # Never release exclusivity while an interrupted worker may still run.
        if children_confirmed_exited and (active_child is None or active_child.poll() is not None):
            for item in reversed(locks):
                release_own_lock(item)

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
    args = parser.parse_args(argv)
    if args.mode == 'prepare':
        print(k.prepare(args.name))
    elif args.mode == 'run':
        print(run(args.plan, args.release, args.name))
    else:
        return worker(args.lease, args.case_index)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
