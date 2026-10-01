"""Source/stdlib control fixtures only; no real scientific process or imports."""
from __future__ import annotations
import ast
from contextlib import ExitStack
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import contract as k
import driver as d

checks = []
def check(name, passed):
    checks.append({'name': name, 'passed': bool(passed)})

def rejected(operation):
    try:
        operation()
    except Exception:
        return True
    return False

def function_map(path):
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    return {node.name: ast.dump(node, include_attributes=False) for node in tree.body if isinstance(node, ast.FunctionDef)}

def fsource(path, name):
    return ast.unparse(next(node for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig')))
                           if isinstance(node, ast.FunctionDef) and node.name == name))

def identity(pid, parent=0, time='2026-09-14T01:00:00+00:00'):
    return {'ProcessId': pid, 'ParentProcessId': parent, 'CreatedUtc': time,
            'Name': 'python.exe', 'ExecutablePath': sys.executable}

def fixture_plan_release(root):
    plan_path, release_path = root / 'fixture_plan.json', root / 'fixture_release.json'
    plan = {'cases': [{'dataset': dataset, 'variant': variant} for dataset, variant in k.CASES],
            'fixture_only': True}
    plan_record = k.write_new(plan_path, plan)
    release_record = k.write_new(release_path, {'allow_run': True, 'plan': plan_record, 'fixture_only': True})
    return plan, plan_path, release_path, plan_record, release_record

def patch_gates(stack, root, rows, plan):
    stack.enter_context(patch.object(k, 'HERE', root))
    stack.enter_context(patch.object(k, 'E', root / 'execution'))
    stack.enter_context(patch.object(k, 'PYTHON', Path(sys.executable)))
    stack.enter_context(patch.object(k, 'process_snapshot', return_value=rows))
    stack.enter_context(patch.object(k, 'frozen_sources', return_value={}))
    stack.enter_context(patch.object(k, 'verify_plan', return_value=plan))
    stack.enter_context(patch.object(k, 'resource_gate', return_value={'fixture_only': True}))
    stack.enter_context(patch.object(k, 'predecessors', return_value=[]))
    stack.enter_context(patch.object(k, 'gpu_idle', return_value=[]))
    (root / 'execution').mkdir(exist_ok=True)
    (root / 'driver.py').write_text('# stdlib fixture only; not an executable child\n', encoding='utf-8')

def parent_fixture(root, mutate=None, phase=None):
    plan, plan_path, release_path, plan_record, release_record = fixture_plan_release(root)
    rows = [identity(os.getpid())]
    calls = []
    class Process:
        def __init__(self, command, **kwargs):
            self.index = int(command[-1])
            self.pid = 900000 + self.index
            calls.append(command)
            case = root / 'runs' / 'parent_fixture' / ('case_' + str(self.index))
            owner = identity(self.pid, os.getpid(), '2026-09-14T01:00:01+00:00')
            k.write_new(case / 'actual_worker_identity.json', {'identity': owner, 'fixture_only': True})
            k.write_new(case / 'case_result.json', {'status': 'completed_primary_case_only',
                'dataset': plan['cases'][self.index]['dataset'], 'variant': plan['cases'][self.index]['variant'],
                'task_count': 3 if self.index < 2 else 8, 'full_t6_complete': False,
                'output_artifacts': [], 'fixture_only': True})
            kwargs['stdout'].write(b'stdlib mock child, no science\n')
            kwargs['stderr'].write(b'')
        def wait(self):
            if phase == 'after_child' and mutate:
                (plan_path if mutate == 'plan' else release_path).write_text('{"mutated_fixture":true}', encoding='utf-8')
            return 0
        def poll(self):
            return 0
    with ExitStack() as stack:
        patch_gates(stack, root, rows, plan)
        stack.enter_context(patch.object(d.subprocess, 'Popen', Process))
        if phase == 'read_to_lease':
            def changed_plan(*args, **kwargs):
                (plan_path if mutate == 'plan' else release_path).write_text('{"mutated_fixture":true}', encoding='utf-8')
                return plan
            stack.enter_context(patch.object(k, 'verify_plan', side_effect=changed_plan))
        try:
            result = d.run(plan_path, release_path, 'parent_fixture')
            failed = False
        except Exception:
            failed = True
            result = root / 'runs' / 'parent_fixture'
        check('private lock cleared after known exited parent fixture ' + str(mutate) + str(phase), not (root / 'corrected_primary_gpu.lock').exists())
        check('persistent shared file retained after parent fixture ' + str(mutate) + str(phase), (root / 'execution' / 'latest_baseline_gpu.lock').is_file())
        lease = k.read(result / 'lease.json')
        check('parent lease uses captured old plan/release ' + str(mutate) + str(phase), lease['plan'] == plan_record and lease['release'] == release_record)
        if mutate:
            check('parent rejects changed ' + mutate + '/' + phase, failed and not (result / 'result.json').exists())
            check('parent rejects before next child ' + mutate + '/' + phase, len(calls) == int(phase == 'after_child'))
        else:
            final = k.read(result / 'result.json')
            check('four-case parent fixture preserves registry and22task sum', not failed and len(calls) == 4 and final['official_cached_protocol_task_checks'] == 22)
            check('four-case fixture parent does not claim fullT6', final['full_t6_complete'] is False)
            check('every child command pins the exact captured lease SHA', all(command[command.index('--lease-sha256') + 1] == k.record(result / 'lease.json')['sha256'] for command in calls))
            for index in range(4):
                proof = k.read(result / ('case_' + str(index)) / 'process_exit.json')
                check('parent seals closed process logs case' + str(index), all(k.verify_record(item) for item in proof['closed_process_artifacts']))

def worker_fixture(root, mutate=None, wrong_parent=False):
    plan, plan_path, release_path, plan_record, release_record = fixture_plan_release(root)
    parent = identity(800000)
    child = identity(os.getpid(), 800000, '2026-09-14T01:00:01+00:00')
    rows = [parent, child]
    output = root / 'runs' / 'worker_fixture'
    case = output / 'case_0'
    case.mkdir(parents=True)
    base = {'schema': 'corrected-primary-t6-lease.v2', 'token': 'stdlib-fixture-token',
        'created_utc': k.now(), 'parent_identity': parent, 'output_root': str(output),
        'plan': plan_record, 'release': release_record}
    calls = []
    with ExitStack() as stack:
        patch_gates(stack, root, rows, plan)
        private_record = k.write_new(root / 'corrected_primary_gpu.lock', base)
        stream, shared = d.acquire_shared_lock()
        shared['owner'] = parent
        lease = {**base, 'locks': [private_record], 'shared_gpu_lock': shared}
        lease_path = output / 'lease.json'
        lease_record = k.write_new(lease_path, lease)
        def fake_science(plan_value, index, out):
            calls.append(index)
            if mutate:
                path = {'plan': plan_path, 'release': release_path, 'lease': lease_path,
                        'private': root / 'corrected_primary_gpu.lock'}[mutate]
                path.write_text('{"changed_in_stdlib_stub":true}', encoding='utf-8')
            return {'fixture_only': True, 'full_t6_complete': False}
        stack.enter_context(patch.dict(sys.modules, {'science': SimpleNamespace(run_case=fake_science)}))
        if wrong_parent:
            stack.enter_context(patch.object(k, 'process_snapshot', return_value=[child]))
        try:
            code = d.worker(lease_path, 0, lease_record['sha256'])
        finally:
            d.release_shared_lock(stream)
        label = str(mutate) + str(wrong_parent)
        if mutate or wrong_parent:
            check('worker rejects changed control or lost parent ' + label, code == 1 and not (case / 'case_result.json').exists())
            check('worker actual failure evidence preserved ' + label, (case / 'failure.json').exists())
        else:
            check('worker accepts private lease while shared first byte is held', code == 0 and len(calls) == 1)
            receipt = k.read(case / 'actual_worker_identity.json')
            check('worker receipt retains original captured lease/private artifacts', receipt['lease'] == lease_record and receipt['private_lease'] == private_record)
        if wrong_parent:
            check('worker with no actual live parent never enters science stub', not calls)

def main():
    old = HERE.parent / 'corrected_driver_v2'
    check('primary v2 seal unchanged', k.sha(old / 'SOURCE_MANIFEST.json') == '59f1c85e6e58541b50aec8054c37ac101b3cf58995e1c565c0abf4b51c0a760e')
    old_manifest = k.read(old / 'SOURCE_MANIFEST.json')
    for record in old_manifest['files']:
        k.verify_record(record)
    check('all old v2 source artifacts preserved', True)
    check('science.py exactly byte identical', (HERE / 'science.py').read_bytes() == (old / 'science.py').read_bytes())
    old_contract, new_contract = function_map(old / 'contract.py'), function_map(HERE / 'contract.py')
    changed = {name for name in old_contract.keys() | new_contract.keys() if old_contract.get(name) != new_contract.get(name)}
    check('contract changes only bound JSON and plan control', changed == {'read_bound_json', 'verify_plan'})
    for name in ('resource_budget', 'resource_gate', 'predecessors', 'verify_snapshot', 'actual_case_files', 'prepare', 'exited', 'self_and_verified_ancestors'):
        check('unchanged contract definition ' + name, old_contract[name] == new_contract[name])
    for path in HERE.glob('*.py'):
        tree = ast.parse(path.read_text(encoding='utf-8-sig'))
        compile(tree, str(path), 'exec')
        check('AST compile ' + path.name, True)
        top = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
        roots = [alias.name.split('.')[0] for node in top for alias in node.names] + [node.module.split('.')[0]
                 for node in top if isinstance(node, ast.ImportFrom) and node.module]
        check('no top-level scientific imports ' + path.name, not set(roots) & {'torch', 'numpy', 'PIL', 'transformers', 'torchvision'})
    worker = fsource(HERE / 'driver.py', 'worker')
    run = fsource(HERE / 'driver.py', 'run')
    check('shared path never goes into private unlink registry', 'latest_baseline_gpu.lock' not in fsource(HERE / 'driver.py', 'release_own_lock'))
    check('worker shared evidence checks parent and protocol without hashing shared', "k.verify_record(shared)" not in worker and "shared['owner'] == owner" in worker)
    check('worker command receives parent captured lease SHA', '--lease-sha256' in run and 'expected_lease_sha' in worker)
    check('parent receipt never recaptures plan or release SHA', 'k.record(plan_path)' not in run and 'k.record(release_path)' not in run)
    check('worker final control revalidation after scientific run', worker.index('worker_post_science_control_revalidation') > worker.index('result = run_case'))
    check('private lock retained for unconfirmed worker', '_RETAINED_SHARED_LOCKS.append(shared_stream)' in run and 'children_confirmed_exited' in run)
    check('no science imports before all fixtures', not any(x in sys.modules for x in ('torch', 'numpy', 'PIL', 'transformers', 'torchvision', 'scipy')))
    with tempfile.TemporaryDirectory(prefix='primary_v3_stdlib_') as temporary:
        root = Path(temporary)
        lock = root / 'persistent.lock'
        lock.write_bytes(b'existing lock protocol fixture')
        before = k.record(lock)
        stream, _ = d.acquire_shared_lock(lock)
        check('Windows shared first byte rejects competing handle', rejected(lambda: d.acquire_shared_lock(lock)))
        with patch.object(k, 'HERE', root), patch.object(k, 'verify_record', side_effect=AssertionError('must not hash shared file')) as hasher:
            check('private cleanup rejects shared path before any hash', rejected(lambda: d.release_own_lock(before)) and hasher.call_count == 0)
        d.release_shared_lock(stream)
        stream, _ = d.acquire_shared_lock(lock)
        d.release_shared_lock(stream)
        check('Windows shared file survives unlock and reacquire byte identical', k.record(lock) == before)
        path = root / 'raw.json'
        path.write_text('{"v":1}', encoding='utf-8')
        value, record = k.read_bound_json(path)
        check('bound JSON captures same object/raw SHA', value == {'v': 1} and record == k.record(path))
        original_loads = json.loads
        def mutate_parse(raw, *args, **kwargs):
            value = original_loads(raw, *args, **kwargs)
            path.write_text('{"v":2}', encoding='utf-8')
            return value
        with patch.object(k.json, 'loads', side_effect=mutate_parse):
            check('bound JSON rejects concurrent parse/read mutation', rejected(lambda: k.read_bound_json(path)))
        for kind in ('plan', 'release'):
            directory = root / ('actual_release_' + kind)
            directory.mkdir()
            _, pp, rp, _, _ = fixture_plan_release(directory)
            real_read = k.read_bound_json
            def changed_read(p):
                result = real_read(p)
                if Path(p) == pp:
                    (pp if kind == 'plan' else rp).write_text('{"changed_after_parse":true}', encoding='utf-8')
                return result
            with patch.object(k, 'read_bound_json', side_effect=changed_read):
                check('real verify_release rejects changed ' + kind + ' before return', rejected(lambda: d.verify_release(rp, pp)))
        for kind, phase in ((None, None), ('plan', 'read_to_lease'), ('release', 'read_to_lease'),
                            ('plan', 'after_child'), ('release', 'after_child')):
            directory = root / ('parent_' + str(kind) + str(phase))
            directory.mkdir()
            parent_fixture(directory, kind, phase)
        for kind, lost in ((None, False), ('plan', False), ('release', False), ('lease', False), ('private', False), (None, True)):
            directory = root / ('worker_' + str(kind) + str(lost))
            directory.mkdir()
            worker_fixture(directory, kind, lost)
    check('no actual prepare/run/active release directories', not (HERE / 'runs').exists() and not (HERE / 'preparations').exists())
    check('no scientific modules imported after fixtures', not any(x in sys.modules for x in ('torch', 'numpy', 'PIL', 'transformers', 'torchvision', 'scipy')))
    report = {'schema': 'primary-v3-stdlib-control-review.v1', 'checks': checks,
        'passed': sum(x['passed'] for x in checks), 'failed': sum(not x['passed'] for x in checks),
        'scientific_execution_performed': False, 'scientific_imports': [],
        'real_shared_gpu_lock_touched': False, 'fixtures_are_not_scientific_outputs': True,
        'model_load_or_gpu_run': False}
    k.write_new(HERE / 'STDLIB_REVIEW.json', report)
    print(json.dumps({name: report[name] for name in ('passed', 'failed', 'scientific_execution_performed')}))
    return int(report['failed'] != 0)

if __name__ == '__main__':
    raise SystemExit(main())
