"""Stdlib identity handshake followed by the unmodified released native v2 worker."""
import argparse
import os
from pathlib import Path
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import execution_contract as c

def run(request_path, request_sha256):
    c.no_science()
    c.source_manifest()
    native, k, b, life = c.runtime_helpers()
    request, captured = c.bound(request_path)
    k.require(captured['sha256'] == request_sha256 and request['schema'] == 'external-t1-slot-request.v1', 'Wrong captured slot request')
    k.require(request['execution_source'] == k.record(HERE / 'SOURCE_MANIFEST.json'), 'Request binds another execution source')
    root = Path(request['control_directory']).resolve()
    k.require(Path(request_path).resolve().parent == root and root.parent.parent == (HERE / 'runs').resolve(), 'Control output escapes this execution')
    phase = 'actual_identity_handshake'
    try:
        parent = request['parent']
        identity = {'schema': 'external-t1-slot-identity.v1', 'request': captured,
            'pid': os.getpid(), 'started_utc': life.process_started(os.getpid()),
            'cim_identity': k.process_identity(os.getpid(), k.process_snapshot()),
            'lineage': life.worker_lineage(os.getpid(), parent['pid'], parent['started_utc'])}
        identity_record = c.atomic_new_json(root / 'worker_identity.json', identity)
        deadline = time.monotonic() + 60
        while not (root / 'parent_observed.json').exists():
            k.require(time.monotonic() < deadline, 'Parent did not retain actual worker handle in time')
            k.require(life.process_started(parent['pid']) == parent['started_utc'], 'Parent disappeared before acknowledgement')
            time.sleep(0.05)
        ack, ack_record = c.bound(root / 'parent_observed.json')
        k.require(ack == {'request': captured, 'identity': identity_record, 'parent': parent}, 'Wrong parent observation acknowledgement')
        phase = 'captured_native_admission'
        plan, _, plan_record, release_record, bindings = c.admit(request['plan']['path'], request['release']['path'], request['plan'], request['release'])
        index = request['slot_index']
        k.require(type(index) is int and 0 <= index < 7 and bindings[index]['row']['run_id'] == request['run_id'], 'Wrong frozen slot index')
        k.require(request['native_output'] == str((c.NATIVE / 'runs' / request['native_name']).resolve()), 'Wrong native output destination')
        b.verify_current_environment(bindings[index]['row']['framework'])
        for artifact in (captured, identity_record, ack_record, plan_record, release_record, request['execution_source']):
            k.verify_record(artifact)
        c.before_slot(plan, bindings[index], (captured, plan_record, release_record))
        phase = 'native_v2_run_one'
        # This is the existing, source-pinned implementation, not new science.
        exit_code = c.native_driver().run_one(plan_record['path'], release_record['path'], request['run_id'], request['native_name'])
        k.require(type(exit_code) is int and exit_code == 0, 'Native v2 worker failed; preserve its arrays/logs')
        phase = 'post_native_control_revalidation'
        for artifact in (captured, identity_record, ack_record, plan_record, release_record, request['execution_source']):
            k.verify_record(artifact)
        k.require(life.process_started(parent['pid']) == parent['started_utc'], 'Parent disappeared during native run')
        c.atomic_new_json(root / 'return_intent.json', {'request': captured, 'identity': identity_record,
            'native_result': k.record(Path(request['native_output']) / 'result.json'),
            'return_intent': 0, 'actual_process_exit_not_yet_observed': True})
        return 0
    except BaseException as error:
        c.atomic_new_json(root / 'shim_failure.json', {'phase': phase, 'type': type(error).__name__, 'error': str(error),
            'traceback': traceback.format_exc(), 'utc': k.now(), 'request': captured,
            'full_t6_complete': False, 'scientific_values_created_by_shim': False})
        return 1

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--request-sha256', required=True)
    args = parser.parse_args()
    return run(args.request, args.request_sha256)

if __name__ == '__main__':
    raise SystemExit(main())
