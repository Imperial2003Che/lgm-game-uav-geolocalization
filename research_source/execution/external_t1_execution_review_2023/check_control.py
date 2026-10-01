"""Independent stdlib control checks for the seven-slot parent; no science."""
from __future__ import annotations
import ast
import copy
from contextlib import ExitStack
import importlib.abc
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

OUT = Path(__file__).resolve().parent
SRC = OUT.parent / 'external_efficiency_preparation/external_t1_execution_v1'
FORBIDDEN = {'torch', 'numpy', 'PIL', 'torchvision', 'transformers', 'scipy', 'matplotlib'}
class NoScience(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in FORBIDDEN:
            raise AssertionError('Scientific import forbidden: ' + fullname)
sys.meta_path.insert(0, NoScience())
sys.path.insert(0, str(SRC))
import execution_contract as c
import run_seven_slots as runner
import aggregate_results as aggregate
native, k, bindings, life = c.runtime_helpers()

def child(code):
    parent = int(sys.argv[3])
    started = sys.argv[4]
    me = {'schema': 'external-t1-slot-identity.v1', 'request': {'fixture_only': True},
          'pid': os.getpid(), 'started_utc': life.process_started(os.getpid()),
          'lineage': life.worker_lineage(os.getpid(), parent, started),
          'cim_identity': k.process_identity(os.getpid(), k.process_snapshot())}
    print(json.dumps(me), flush=True)
    assert sys.stdin.readline().strip() == 'exit'
    raise SystemExit(code)
if len(sys.argv) > 1 and sys.argv[1] == '--identity-child':
    child(int(sys.argv[2]))

checks = []
def check(name, value):
    checks.append({'name': name, 'passed': bool(value)})
    if not value: raise AssertionError(name)
def rejects(name, fn, cls=Exception):
    try: fn()
    except cls: check(name, True)
    else: check(name, False)

def main():
    registry = bindings.slots()
    ids = [x['run_id'] for x in registry]
    check('seven unique frozen native slots', len(registry) == len(set(ids)) == 7)
    check('ten original official tasks', len(bindings.EXPECTED_TASKS) == 10)
    check('original 213 native source records unchanged', len(native.verify_sources()['files']) == 213)
    for name in ('execution_contract.py', 'run_seven_slots.py', 'slot_entry.py', 'aggregate_results.py'):
        tree = ast.parse((SRC / name).read_text(encoding='utf-8-sig'))
        compile(tree, str(SRC / name), 'exec')
        check('stdlib control syntax: ' + name, True)
    check('no actual output or source seal created during candidate review', not (SRC / 'runs').exists() and not (SRC / 'SOURCE_MANIFEST.json').exists())
    for values in ((1, 0), (0, 7), (0, 259), (None, 0), (False, 0), (0, 0.0)):
        rejects('exit gate rejects ' + repr(values), lambda v=values: runner.require_exited_zero(*v))
    runner.require_exited_zero(0, 0)
    check('both actual integer exit0 accepted', True)
    actual_process_tests = []
    for code in (0, 7):
        parent = {'pid': os.getpid(), 'started_utc': life.process_started(os.getpid())}
        command = [str(k.PYTHON), '-B', str(Path(__file__).resolve()), '--identity-child', str(code), str(parent['pid']), parent['started_utc']]
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, encoding='utf-8', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        launcher_handle = life.ProcessObservation(process.pid, existing_handle=process._handle)
        worker_handle = None
        try:
            line = process.stdout.readline()
            if not line:
                raise AssertionError(process.stderr.read())
            identity = json.loads(line)
            launcher = {'pid': process.pid, 'started_utc': launcher_handle.started_utc}
            c.validate_identity(identity, {'fixture_only': True}, parent, launcher)
            worker_handle = life.ProcessObservation(identity['pid'])
            check('actual native worker/launcher handles live for exit' + str(code), worker_handle.exit_code() == launcher_handle.exit_code() == 259)
            check('Windows venv launcher distinguished from actual worker ' + str(code), identity['pid'] != process.pid)
            process.stdin.write('exit\n'); process.stdin.flush()
            stdout, stderr = process.communicate(timeout=20)
            check('actual retained launcher/worker exit matches ' + str(code), process.returncode == launcher_handle.exit_code() == worker_handle.exit_code() == code and not stderr)
            if code:
                rejects('real controlled exit7 cannot pass completed gate', lambda: runner.require_exited_zero(process.returncode, worker_handle.exit_code()))
            actual_process_tests.append({'launcher': launcher, 'worker': identity, 'exit_code': code})
        finally:
            if worker_handle: worker_handle.close()
            launcher_handle.close()
            if process.poll() is None:
                process.stdin.write('exit\n'); process.stdin.flush(); process.wait(timeout=20)
    with tempfile.TemporaryDirectory(prefix='lgm_t1_control_review_') as temp:
        root = Path(temp).resolve()
        check('all synthetic fixtures in OS temp root', root.parent == Path(tempfile.gettempdir()).resolve())
        # Persistent controller lock is separate from actual native shared GPU lock.
        with patch.object(runner, 'HERE', root):
            with runner.controller_lock():
                rejects('real competing controller byte lock refused', lambda: runner.controller_lock().__enter__(), OSError)
            before = (root / 'controller.lock').read_bytes()
            with runner.controller_lock(): pass
            check('controller byte file persists unchanged across reacquisition', (root / 'controller.lock').read_bytes() == before)
        p = root / 'atomic.json'
        value = {'fixture_only': True, '中文': 'complete publication'}
        artifact = c.atomic_new_json(p, value)
        check('closed atomic JSON publication exact', c.bound(p) == (value, artifact) and not p.with_name(p.name + '.pending').exists())
        rejects('atomic publish refuses overwriting prior evidence', lambda: c.atomic_new_json(p, {'changed': True}))
        check('refused overwrite leaves prior bytes', c.bound(p) == (value, artifact))
        plan_path, release_path = root / 'plan.json', root / 'release.json'
        plan = {'fixture_only': True, 'predecessors': []}
        pr = k.write_new(plan_path, plan)
        release = {'fixture_only': True, 'allow_run': True, 'plan': pr, 'allowed_run_ids': ids}
        rr = k.write_new(release_path, release)
        bind = [{'row': row, 'checkpoint': {'fixture_only': True}} for row in registry]
        with ExitStack() as stack:
            stack.enter_context(patch.object(c, 'source_manifest', return_value={'fixture_only': True}))
            stack.enter_context(patch.object(native, 'verify_plan', side_effect=lambda path, run_id, expected_record: (plan, bind[ids.index(run_id)])))
            stack.enter_context(patch.object(native, 'admitted_predecessors', return_value=([], {'fixture_only': True})))
            check('same raw seven-slot plan/release admitted', c.admit(plan_path, release_path, pr, rr)[-1] == bind)
            for title, wrong in [('missing', ids[:-1]), ('reordered', list(reversed(ids))), ('duplicate', ids[:-1] + ids[:1])]:
                altered = dict(release, allowed_run_ids=wrong)
                release_path.write_text(json.dumps(altered), encoding='utf-8')
                rejects('seven-slot release rejects ' + title, lambda: c.admit(plan_path, release_path))
            release_path.write_text(json.dumps(release), encoding='utf-8')
            _, rr = c.bound(release_path)
            def mutate_plan(*args, **kwargs):
                plan_path.write_text('{"changed":true}', encoding='utf-8')
                return plan, bind[ids.index(args[1])]
            with patch.object(native, 'verify_plan', side_effect=mutate_plan):
                rejects('admission rejects control mutation before returning', lambda: c.admit(plan_path, release_path, pr, rr))
        # Measurement serialization checked with marked synthetic samples only.
        summarize = aggregate.summary_function()
        samples = [float(i) for i in range(1, 101)]
        measurement = {'clock': 'cuda_event', 'warmup_repetitions': 20, 'inference_mode': True,
            'timing': summarize(samples), 'runtime_flags': {'native_amp': False, 'cuda_autocast_enabled': False,
                'cpu_autocast_enabled': False, 'explicit_device_index': 0, 'current_cuda_device_index': 0},
            'memory': {'baseline_allocated': 1, 'baseline_reserved': 2, 'peak_allocated': 4, 'peak_reserved': 6,
                       'peak_allocated_minus_baseline': 3, 'peak_reserved_minus_baseline': 4}}
        check('native hundred-sample schema accepted', aggregate.verify_measurement(measurement, 'gpu_forward_pair', summarize) == summarize(samples))
        for field, value in [('clock', 'cpu_wall'), ('warmup_repetitions', 0), ('inference_mode', False)]:
            wrong = copy.deepcopy(measurement); wrong[field] = value
            rejects('timing rejects changed ' + field, lambda w=wrong: aggregate.verify_measurement(w, 'gpu_forward_pair', summarize))
        wrong = copy.deepcopy(measurement); wrong['timing']['median'] += 1
        rejects('timing summary drift refused', lambda: aggregate.verify_measurement(wrong, 'gpu_forward_pair', summarize))
        wrong = copy.deepcopy(measurement); wrong['memory']['peak_allocated_minus_baseline'] = 0
        rejects('allocator arithmetic drift refused', lambda: aggregate.verify_measurement(wrong, 'gpu_forward_pair', summarize))
        # Exercise actual aggregate cardinality/CSV/three-seed logic; slot records
        # are explicit stubs here, never advertised as real measurement outputs.
        source_record = k.write_new(root / 'source.json', {'fixture_only': True})
        pr = k.record(plan_path)
        rr = k.record(release_path)
        slots = [{'run_id': x} for x in ids]
        def stub_slot(slot, binding, *_):
            row = binding['row']
            return [{'run_id': row['run_id'], 'method': row['method'], 'seed': row['seed'], 'task': task,
                **{field: 0.5 for field in aggregate.METRICS},
                **{scope + '_median_ms': float(row['seed']) for scope in aggregate.SCOPES}}
                for task in bindings.EXPECTED_TASKS]
        with patch.object(aggregate, 'verify_slot', side_effect=stub_slot):
            destination = root / 'aggregate'; destination.mkdir()
            result = aggregate.aggregate(plan, pr, rr, bind, slots, destination, {'fixture_only': True}, source_record)
            final, _ = c.bound(result['path'])
            check('aggregate actual control enforces 7 slots and70 distinct tasks', final['slot_count'] == 7 and final['task_count'] == 70)
            check('aggregate requires external actual parent exit verification', final['parent_exit_not_observed'] and final['parent_exit0_required_by_final_T6_acceptor'])
            check('aggregate does not claim full T6 or CAMP/DAC', final['full_t6_complete'] is False and final['CAMP_DAC_efficiency_included'] is False)
            seeds = k.read(final['qdfl_seed_summary']['path'])
            check('three-seed sample SD actually calculated', len(seeds['tasks']) == 10 and seeds['tasks'][0]['values']['gpu_forward_pair_median_ms']['sample_sd'] == 1.0)
            for name, rows, values in [('six_slots', slots[:-1], bind), ('duplicate_slots', slots[:-1] + slots[:1], bind), ('six_bindings', slots, bind[:-1])]:
                missing = root / name; missing.mkdir()
                rejects('aggregate rejects ' + name, lambda r=rows, v=values, o=missing: aggregate.aggregate(plan, pr, rr, v, r, o, {}, source_record))
                check('rejected aggregate has no success file ' + name, not (missing / 'aggregate.json').exists())
    check('no scientific imports during all fixtures/Win32 smoke', not FORBIDDEN.intersection(sys.modules))
    report = {'schema': 'external-t1-seven-slot-independent-control-review.v1', 'status': 'passed',
        'checks': checks, 'actual_standard_library_process_tests': actual_process_tests,
        'source_files': {str(p): k.sha(p) for p in sorted(SRC.glob('*.py'))},
        'original_native_driver_sources_verified': 213, 'scientific_execution_performed': False,
        'actual_training_or_measurement_performed': False, 'active_plan_or_release_created': False,
        'scope': 'source contract review, exact seven-slot admission, real Windows0/7 identities and byte lock, synthetic serialization/cardinality tests',
        'not_tested': ['real full launch_slot orchestration', 'real model loading', 'GPU timing', 'actual seven checkpoint bindings'], 'utc': k.now()}
    rec = k.write_new(OUT / 'CONTROL_REVIEW.json', report)
    print(json.dumps({'checks_passed': len(checks), 'report': rec}, ensure_ascii=True))
if __name__ == '__main__': main()
