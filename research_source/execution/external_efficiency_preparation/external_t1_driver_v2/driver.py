"""Source-only prepared CLI: bind seven future slots, or execute one released slot.

Each run-one must use its registered original interpreter in a fresh process.
This CLI does not spawn subprocesses or create an active release.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import driver_contract as d

def allowed_locks():
    return {(HERE / 'external_t1_gpu.lock').resolve()}

@contextmanager
def shared_gpu_lock(path=None):
    """Same persistent first-byte lock protocol as frozen DAC/CAMP controls.

    The optional path exists for standard-library temporary-file tests only.
    Runtime calls never supply it and always share the registered common file.
    """
    k = d.common()
    k.require(os.name == 'nt', 'Windows byte-range lock required')
    import msvcrt
    path = k.E / 'latest_baseline_gpu.lock' if path is None else Path(path)
    with path.open('a+b') as stream:
        stream.seek(0, os.SEEK_END)
        if not stream.tell():
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            raise RuntimeError('Another serial baseline owns the GPU lock') from error
        try:
            yield {'path': str(path.resolve()), 'protocol': 'Windows msvcrt nonblocking first-byte lock',
                'persistent_file_is_not_deleted': True}
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)

def release_lock(record):
    k = d.common()
    k.require(Path(record['path']).resolve() in allowed_locks(), 'Unexpected lock target')
    k.verify_record(record)
    Path(record['path']).unlink()

def run_one(plan_path, release_path, run_id, name):
    d.no_science_loaded()
    k, b = d.common(), d.adapters()[0]
    output = k.scoped_new(HERE / 'runs', name)
    science = output / 'science'
    science.mkdir(exist_ok=False)
    locks = []
    shared = None
    shared_acquired = False
    phase = 'release_plan_predecessors_native_environment_resources'
    try:
        release, plan_record = d.verify_release(release_path, plan_path, run_id)
        plan, binding = d.verify_plan(plan_path, run_id, expected_record=plan_record)
        predecessors, owner = d.admitted_predecessors()
        k.require(predecessors == plan['predecessors'], 'Five predecessor proofs changed since plan preparation')
        environment = b.verify_current_environment(binding['row']['framework'])
        resource = d.resource_gate(binding)
        phase = 'exclusive_gpu_locks'
        receipt = {'schema': 'external-t1-single-slot-admission.v2', 'utc': k.now(), 'owner': owner,
            'run_id': run_id, 'plan': plan_record, 'release': release,
            'predecessors': predecessors, 'environment': environment, 'resource': resource,
            'output': str(output), 'full_t6_complete': False}
        for path in sorted(allowed_locks()):
            locks.append(k.write_new(path, receipt))
        receipt['locks'] = locks
        shared = shared_gpu_lock()
        receipt['shared_gpu_byte_lock'] = shared.__enter__()
        shared_acquired = True
        k.write_new(output / 'admission.json', receipt)
        phase = 'post_lock_revalidation'
        k.verify_record(receipt['plan'])
        k.verify_record(release)
        k.require(d.admitted_predecessors()[0] == predecessors, 'Predecessor state changed after locks')
        d.resource_gate(binding)
        d.no_science_loaded()
        k.verify_record(plan_record)
        k.verify_record(release)
        # The only entrance to real scientific imports/model loading.
        phase = 'actual_single_slot_science'
        import scientific_worker
        result = scientific_worker.run_slot(plan, binding, science)
        phase = 'post_science_exact_plan_release_revalidation'
        k.verify_record(plan_record)
        k.verify_record(release)
        result.update({'finished_utc': k.now(), 'owner': owner, 'admission': k.record(output / 'admission.json'),
            'external_parent_stdout_stderr_not_sealed_by_worker': True,
            'parent_must_wait_for_real_process_exit_before_sealing_logs_or_starting_next_slot': True})
        for item in result['closed_scientific_artifacts']:
            k.verify_record(item)
        phase = 'final_exact_plan_release_revalidation'
        k.verify_record(plan_record)
        k.verify_record(release)
        k.write_new(output / 'result.json', result)
        return 0
    except BaseException as error:
        k.write_new(output / 'failure_phase.json', {'phase': phase, 'run_id': run_id, 'utc': k.now()})
        d.failure_artifacts(output, error)
        return 1
    finally:
        # Only the exact files acquired by this process are removed. A following
        # process still has to prove this Python owner exited and GPU is idle.
        try:
            if shared_acquired:
                shared.__exit__(None, None, None)
        finally:
            for item in reversed(locks):
                release_lock(item)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prep = commands.add_parser('prepare', help='Bind seven actual completed slots after all five predecessor layers exit')
    prep.add_argument('--name', required=True)
    run = commands.add_parser('run-one', help='Execute one actual released slot in its registered fresh native interpreter')
    run.add_argument('--plan', type=Path, required=True)
    run.add_argument('--release', type=Path, required=True)
    run.add_argument('--run-id', required=True)
    run.add_argument('--name', required=True)
    args = parser.parse_args(argv)
    if args.command == 'prepare':
        print(json.dumps(d.prepare(args.name), ensure_ascii=False))
        return 0
    return run_one(args.plan, args.release, args.run_id, args.name)

if __name__ == '__main__':
    raise SystemExit(main())
