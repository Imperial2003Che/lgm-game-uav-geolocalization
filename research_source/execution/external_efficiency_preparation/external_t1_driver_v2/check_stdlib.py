"""Bounded stdlib/AST/mock checks; no scientific import or runtime admission."""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import driver_contract as d
import scientific_worker as s
import driver

checks = []
def check(name, value):
    checks.append({'name': name, 'passed': bool(value)})

def rejected(operation):
    try:
        operation()
    except Exception:
        return True
    return False

def named(tree, name):
    return next(n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)

def source(tree, name):
    return ast.unparse(named(tree, name))

def assignment_value(node, target):
    class QuerySliceAsSingleDescriptor(ast.NodeTransformer):
        def visit_Subscript(self, child):
            if isinstance(child.value, ast.Name) and child.value.id == 'query':
                return ast.Name(id='descriptor', ctx=ast.Load())
            return self.generic_visit(child)
    found = []
    for item in ast.walk(node):
        if isinstance(item, ast.Assign) and any(isinstance(x, ast.Name) and x.id == target for x in item.targets):
            clone = ast.parse(ast.unparse(item.value), mode='eval')
            found.append(ast.dump(QuerySliceAsSingleDescriptor().visit(clone).body, include_attributes=False))
    if not found:
        raise AssertionError(target)
    return sorted(found)

def main():
    b, n, loader = d.adapters()
    k = d.common()
    check('imported helpers without scientific modules', not any(x in sys.modules for x in
        ('torch', 'numpy', 'PIL', 'torchvision', 'transformers', 'scipy', 'matplotlib')))
    check('v2 adapter source pin', k.sha(d.ADAPTER / 'SOURCE_MANIFEST.json') == d.ADAPTER_SHA)
    prior = HERE.parent / 'external_t1_driver_v1'
    check('v1 driver seal remains unchanged', k.sha(prior / 'SOURCE_MANIFEST.json') == '7100d5f1eb93f4b2803fbc1cf4ef01f64ac75b92ff67539932547de23bec4762')
    for record in k.read(prior / 'SOURCE_MANIFEST.json')['files']:
        k.verify_record(record)
    check('all198 prior v1 sealed sources preserved', len(k.read(prior / 'SOURCE_MANIFEST.json')['files']) == 198)
    manifest = b.source_manifest()
    check('all immutable v2 source records still verify', len(manifest['files']) == 188)
    check('seven registered actual fit slots', len(b.slots()) == 7)
    check('ten official tasks per fit, seventy total', len(b.EXPECTED_TASKS) == 10 and len(b.slots()) * len(b.EXPECTED_TASKS) == 70)
    trees = {}
    for path in HERE.glob('*.py'):
        text = path.read_text(encoding='utf-8-sig')
        trees[path.stem] = ast.parse(text)
        compile(text, str(path), 'exec', dont_inherit=True)
        check('AST syntax ' + path.name, True)
        imports = [x for x in trees[path.stem].body if isinstance(x, (ast.Import, ast.ImportFrom))]
        names = [v.name.split('.')[0] for x in imports for v in x.names] + [x.module.split('.')[0]
                 for x in imports if isinstance(x, ast.ImportFrom) and x.module]
        check('no top-level science imports ' + path.name, not set(names) & {'torch', 'numpy', 'PIL', 'torchvision', 'transformers'})
    worker, contract, cli = trees['scientific_worker'], trees['driver_contract'], trees['driver']
    original_tree = ast.parse((b.EXT / 'official_descriptor_evaluation.py').read_text(encoding='utf-8'))
    official_eval = named(original_tree, 'evaluate_descriptor_task')
    new_rank = named(worker, 'native_full_ranking')
    for value in ('dot_products', 'query_squared_norm', 'squared_distance', 'scores'):
        check('native ranking exact original AST ' + value,
              assignment_value(new_rank, value) == assignment_value(official_eval, value))
    order_value = next(x.value for x in ast.walk(new_rank) if isinstance(x, ast.Return))
    check('native complete stable argsort exact original AST',
          [ast.dump(order_value, include_attributes=False)] == assignment_value(official_eval, 'order'))
    check('four measured scopes without GPU ranking substitution', 'raw_file_to_complete_native_ranking' in source(worker, 'measure_task_sample') and
          "clock='synchronized_wall'" in source(worker, 'measure_task_sample') and 'native_full_ranking' in source(worker, 'measure_task_sample'))
    check('all full tasks before first B1 measurement loop', source(worker, 'run_slot').index('all_ten_full_gallery_metrics.json') < source(worker, 'run_slot').index('measure_task_sample('))
    check('exact nine-view descriptor fingerprint check', 'observed == declared[key]' in source(worker, 'extract_views') and len(s.VIEW_ORDER) == 9)
    check('actual full descriptor saved before fingerprint comparison', source(worker, 'extract_views').index('save_array(') < source(worker, 'extract_views').index('observed ='))
    check('original full-view extractor reused unchanged', 'n.encode_official_view(ctx, view, role)' in source(worker, 'extract_views'))
    check('original full evaluator chunk128', 'original.evaluate_descriptor_task(task, chunk_size=128)' in source(worker, 'run_slot'))
    check('independent original B1 exact parity retained in immutable adapter', 'new B=1 adapter against original B=1 official extractor' in (d.ADAPTER / 'native_ops.py').read_text())
    check('worker does not impose bitwise cross-batch gate', 'expected_official_descriptor=' not in source(worker, 'measure_task_sample'))
    check('actual cross-batch arrays and differences are saved', all(x in source(worker, 'measure_task_sample') for x in
        ('actual_native_batch_reference.npy', 'actual_b1_descriptor.npy', 'actual_b1_vs_native_batch_difference.json', 'max_abs_difference', 'different_element_count')))
    check('shared path removed from exclusive-create and unlink registry', 'latest_baseline_gpu.lock' not in source(cli, 'allowed_locks'))
    check('shared lock uses original first byte nonblocking protocol', all(x in source(cli, 'shared_gpu_lock') for x in
        ("open('a+b')", 'msvcrt.LK_NBLCK, 1', 'msvcrt.LK_UNLCK, 1', 'stream.seek(0)')))
    check('shared lock never removes persistent file', 'unlink' not in source(cli, 'shared_gpu_lock') and 'write_new' not in source(cli, 'shared_gpu_lock'))
    check('SUES galleries remain unmasked', 'gallery_descriptors=gmap' in source(worker, 'make_task') and 'query_descriptors=qmap[subset]' in source(worker, 'make_task'))
    check('workers0 selected by immutable adapter', 'num_workers=0' in (d.ADAPTER / 'native_ops.py').read_text())
    check('mmap read only and no full-gallery concatenation', "mmap_mode='r'" in source(worker, 'make_task') and 'concatenate' not in ast.unparse(worker))
    check('failure arrays persisted before outer rethrow', 'd.failure_artifacts(sample, error)' in source(worker, 'run_slot'))
    check('before/after actual content inventories checked', 'inventory_after == inventory' in source(worker, 'run_slot'))
    check('only science subtree artifacts are sealed', 'output.rglob' in source(worker, 'run_slot') and 'scientific_worker.run_slot(plan, binding, science)' in source(cli, 'run_one'))
    check('driver does not claim it sealed parent logs', 'external_parent_stdout_stderr_not_sealed_by_worker' in source(cli, 'run_one'))
    check('no child process runner in this bounded worker', not any(isinstance(x, ast.Name) and x.id == 'subprocess' for x in ast.walk(cli)))
    check('frozen five-layer helpers reused', 'k.predecessors(primary, rows)' in source(contract, 'admitted_predecessors'))
    check('new parent PID ancestry helper reused', 'k.self_and_verified_ancestors(rows)' in source(contract, 'admitted_predecessors'))
    check('actual per-slot native environment checked before scientific worker import',
          source(cli, 'run_one').index('b.verify_current_environment') < source(cli, 'run_one').index('import scientific_worker'))
    check('exact release and plan checked before native admission', source(cli, 'run_one').index('d.verify_release') < source(cli, 'run_one').index('d.verify_plan'))
    check('post-lock predecessor revalidation before science', source(cli, 'run_one').index('d.admitted_predecessors()[0]') < source(cli, 'run_one').index('import scientific_worker'))
    check('new output uses exclusive scoped directory', 'k.scoped_new(HERE / \'runs\', name)' in source(cli, 'run_one'))
    check('inactive release template only in prepare', "'allow_run': False" in source(contract, 'prepare') and "'allow_run': True" not in source(contract, 'prepare'))
    check('resource gate avoids impossible fixed26GiB', '26 *' not in source(contract, 'resource_gate') and 'derive_slot_budget(binding)' in source(contract, 'resource_gate'))
    check('host estimate labels unprofiled allocations explicitly', 'estimate_is_not_measured_peak' in source(contract, 'derive_slot_budget'))
    metric = {name: 0.5 for name in s.METRICS}
    metric.update({name: 10 for name in s.COUNTS})
    check('actual six-field metrics accept equal fixture', s.compare_metrics(metric, metric, rtol=2e-6, atol=2e-7)['passed'])
    for field in s.METRICS:
        changed = dict(metric, **{field: 0.6})
        check('actual metric mismatch rejected ' + field, not s.compare_metrics(changed, metric, rtol=2e-6, atol=2e-7)['passed'])
    check('nonfinite actual metric rejected', not s.compare_metrics(dict(metric, MRR=float('nan')), metric, rtol=2e-6, atol=2e-7)['passed'])
    check('actual full gallery count mismatch rejected', not s.compare_metrics(dict(metric, gallery=9), metric, rtol=2e-6, atol=2e-7)['passed'])
    # Real exception arrays are opaque to stdlib. This fixture tests the exact
    # persistence control flow with tiny independent bytes, not numerical science.
    class FakeNP:
        @staticmethod
        def save(stream, array, *, allow_pickle):
            assert allow_pickle is False
            stream.write(b'STDLIB_FIXTURE_ONLY:' + array)
    error = RuntimeError('injected first-parity failure')
    error.actual_descriptor_array = b'actual'
    error.expected_descriptor_array = b'expected'
    error.evidence = {'passed': False, 'scope': 'stdlib failure fixture only'}
    with tempfile.TemporaryDirectory(prefix='t1_driver_stdlib_') as temporary:
        root = Path(temporary)
        with patch.dict(sys.modules, {'numpy': FakeNP}):
            result = d.failure_artifacts(root / 'failure', error)
        proof = k.read(result['path'])
        check('failure evidence remains JSON serializable', json.loads(json.dumps(proof)) == proof)
        check('both first-failure opaque arrays saved', len(proof['descriptor_arrays']) == 2 and not proof['array_persistence_errors'])
        check('failure actual bytes independent', (root / 'failure' / 'failure_descriptor_actual.npy').read_bytes().endswith(b'actual'))
        check('failure expected bytes independent', (root / 'failure' / 'failure_descriptor_expected.npy').read_bytes().endswith(b'expected'))
        check('failure arrays metadata external to JSON evidence', set(proof['evidence']) == {'passed', 'scope'})
        with patch.object(d, 'HERE', root):
            target = root / 'release_TEMPLATE.json'
            k.write_new(target, {'allow_run': False, 'plan': {}, 'allowed_run_ids': []})
            check('inactive release rejected without touching future checkpoint', rejected(lambda: d.verify_release(target, root / 'absent_plan', b.slots()[0]['run_id'])))
        check('exclusive output prevents collisions', rejected(lambda: k.scoped_new(root, 'failure')))
        check('unsafe output traversal rejected', rejected(lambda: k.scoped_new(root, '../outside')))
        metrics_path = root / 'metrics.json'
        k.write_new(metrics_path, {'descriptor_fingerprints': {'view': {'shape': [51355, 2048]}}, 'tasks': [{'gallery': 51355}]})
        budget = d.derive_slot_budget({'evaluation_dir': str(root), 'checkpoint': {'bytes': 100_000_000}})
        check('resource formula uses real declared dimensions', budget['descriptor_output_bytes'] == 51355 * 2048 * 4)
        check('source estimate under16GiB for concrete stdlib shape fixture', budget['host_required_available_bytes'] < 16 * 1024**3)
        # Execute the real CLI failure control flow, with all admission inputs
        # replaced by stdlib fixtures. No scientific entrance is reached.
        with patch.object(driver, 'HERE', root), patch.object(d, 'verify_release', side_effect=RuntimeError('inactive fixture release')):
            exit_code = driver.run_one(root / 'no_plan', root / 'no_release', b.slots()[0]['run_id'], 'denied_fixture')
        denied = root / 'runs' / 'denied_fixture'
        check('real run_one rejected release exits1', exit_code == 1)
        check('real run_one writes pre-admission failure evidence', (denied / 'failure.json').is_file() and (denied / 'failure_phase.json').is_file())
        plan_path = root / 'fixture_plan.json'
        release_path = root / 'fixture_release.json'
        k.write_new(plan_path, {'fixture_only': True})
        k.write_new(release_path, {'fixture_only': True})
        lock_paths = {root / 'fixture_global_gpu.lock', root / 'fixture_local_gpu.lock'}
        fake_binding = {'row': {'framework': 'fixture', 'run_id': 'fixture'}}
        original_shared_lock = driver.shared_gpu_lock
        with patch.object(driver, 'HERE', root), patch.object(driver, 'allowed_locks', return_value=lock_paths), \
             patch.object(driver, 'shared_gpu_lock', side_effect=lambda: original_shared_lock(root / 'fixture_shared_gpu.lock')), \
             patch.object(d, 'verify_release', return_value=(k.record(release_path), k.record(plan_path))), \
             patch.object(d, 'verify_plan', return_value=({'predecessors': []}, fake_binding)), \
             patch.object(d, 'admitted_predecessors', side_effect=[([], {'fixture_owner': True}), RuntimeError('post-lock fixture failure')]), \
             patch.object(b, 'verify_current_environment', return_value={'fixture_environment': True}), \
             patch.object(d, 'resource_gate', return_value={'fixture_resources': True}):
            locked_exit = driver.run_one(plan_path, release_path, 'fixture', 'post_lock_fixture')
        check('post-lock gate failure exits1 before science entrance', locked_exit == 1)
        check('post-lock failure removes only its actual exclusive fixture locks', not any(p.exists() for p in lock_paths))
        check('post-lock failure records exact phase', k.read(root / 'runs' / 'post_lock_fixture' / 'failure_phase.json')['phase'] == 'post_lock_revalidation')
        check('post-lock failure leaves persistent shared lock file present', (root / 'fixture_shared_gpu.lock').is_file())
        persistent = root / 'persistent_fixture.lock'
        persistent.write_bytes(b'existing protocol fixture bytes')
        before = k.record(persistent)
        with driver.shared_gpu_lock(persistent):
            check('real Windows first-byte lock rejects competing handle', rejected(lambda: driver.shared_gpu_lock(persistent).__enter__()))
            check('existing persistent file length unchanged while held', persistent.stat().st_size == before['bytes'])
        with driver.shared_gpu_lock(persistent):
            check('real Windows first-byte lock can reacquire after release', True)
        check('persistent file remains same bytes after release', k.record(persistent) == before)
        raw_path = root / 'single_read_fixture.json'
        raw_path.write_text('{"version":1}', encoding='utf-8')
        parsed, bound = d.read_bound_json(raw_path)
        check('single raw read parsed value and SHA correspond', parsed == {'version': 1} and bound == k.record(raw_path))
        original_loads = json.loads
        def mutate_after_parse(value, *args, **kwargs):
            parsed_value = original_loads(value, *args, **kwargs)
            raw_path.write_text('{"version":2}', encoding='utf-8')
            return parsed_value
        with patch.object(d.json, 'loads', side_effect=mutate_after_parse):
            check('read-bound JSON rejects modification during parse before receipt', rejected(lambda: d.read_bound_json(raw_path)))
        for kind in ('plan', 'release'):
            for stage in ('read_to_receipt', 'post_science'):
                case = root / (kind + '_' + stage)
                case.mkdir()
                cp, cr = case / 'plan.json', case / 'release.json'
                k.write_new(cp, {'fixture': 'plan'})
                k.write_new(cr, {'fixture': 'release'})
                captured = k.record(cr), k.record(cp)
                target = cp if kind == 'plan' else cr
                def verify_fixture(*args, **kwargs):
                    if stage == 'read_to_receipt':
                        target.write_text('{"modified_after_bound_read":true}', encoding='utf-8')
                    return {'predecessors': []}, fake_binding
                def science_fixture(*args, **kwargs):
                    target.write_text('{"modified_during_science_fixture":true}', encoding='utf-8')
                    return {'closed_scientific_artifacts': [], 'fixture_only': True}
                with patch.object(driver, 'HERE', case), \
                     patch.object(driver, 'allowed_locks', return_value={case / 'private.lock'}), \
                     patch.object(driver, 'shared_gpu_lock', side_effect=lambda: original_shared_lock(case / 'persistent.lock')), \
                     patch.object(d, 'verify_release', return_value=captured), \
                     patch.object(d, 'verify_plan', side_effect=verify_fixture), \
                     patch.object(d, 'admitted_predecessors', return_value=([], {'fixture_owner': True})), \
                     patch.object(b, 'verify_current_environment', return_value={'fixture_environment': True}), \
                     patch.object(d, 'resource_gate', return_value={'fixture_resources': True}), \
                     patch.object(s, 'run_slot', side_effect=science_fixture) as scientific_entry:
                    code = driver.run_one(cp, cr, 'fixture', 'run')
                out = case / 'runs' / 'run'
                check(kind + ' modification at ' + stage + ' rejects stale-object/new-SHA receipt', code == 1 and not (out / 'result.json').exists())
                check(kind + ' modification at ' + stage + ' leaves captured old artifact', k.read(out / 'admission.json')[kind] == captured[1 if kind == 'plan' else 0])
                check(kind + ' modification at ' + stage + ' science entrance count', scientific_entry.call_count == int(stage == 'post_science'))
    check('no runtime plan/release or result outputs created', not (HERE / 'preparations').exists() and not (HERE / 'runs').exists())
    check('all scientific imports absent at exit', not any(x in sys.modules for x in
        ('torch', 'numpy', 'PIL', 'torchvision', 'transformers', 'scipy', 'matplotlib')))
    report = {'schema': 'external-t1-driver-stdlib-checks.v1', 'checks': checks,
        'passed': sum(x['passed'] for x in checks), 'failed': sum(not x['passed'] for x in checks),
        'scientific_execution_performed': False, 'scientific_imports': [], 'actual_checkpoint_bindings_created': 0,
        'fixture_outputs_are_not_scientific_arrays_or_measurements': True}
    k.write_new(HERE / 'STDLIB_REVIEW.json', report)
    print(json.dumps({name: report[name] for name in ('passed', 'failed', 'scientific_execution_performed')}))
    return int(report['failed'] != 0)

if __name__ == '__main__':
    raise SystemExit(main())
