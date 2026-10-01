"""AST and meaningful operation-order/guard mocks, without scientific imports."""
from __future__ import annotations
import ast
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bindings as b
import native_ops as n
import native_load as loader

checks = []
def ok(name, value):
    if not value:
        raise AssertionError(name)
    checks.append({'check': name, 'passed': True})

def refuses(name, fn):
    try:
        fn()
    except (b.common().GateError, ValueError, FileNotFoundError):
        ok(name, True)
    else:
        raise AssertionError('Did not refuse: ' + name)

def literal_assignment(tree, name):
    return ast.literal_eval(next(x.value for x in tree.body if isinstance(x, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == name for t in x.targets)))

class Tensor:
    def __init__(self, tag, log):
        self.tag, self.log, self.requires_grad = tag, log, False
        self.shape, self.ndim = (1, 2), 2
    def __add__(self, other):
        self.log.append(('raw_sum', self.tag, other.tag))
        return Tensor('sum', self.log)
    def cpu(self):
        self.log.append(('cpu', self.tag))
        return self
    def numpy(self):
        self.log.append(('numpy', self.tag))
        return self

class FakeNumpy:
    float32 = 'float32'
    def ascontiguousarray(self, value, dtype):
        value.dtype = dtype
        return value
    def isfinite(self, value):
        return SimpleNamespace(all=lambda: True)

def operation_fixture(family, role):
    log = []
    class Model:
        def __call__(self, images):
            log.append(('forward', images.tag))
            return Tensor(images.tag + '_features', log)
    model = Model()
    def flip(images, dims):
        log.append(('flip', dims))
        return Tensor('mirror', log)
    def view_output(owner, images, actual_role):
        log.append(('route', actual_role, id(owner)))
        return owner(images)
    def qpost(original, mirrored):
        log.append(('official_qdfl_post', original.tag, mirrored.tag))
        return Tensor('qdfl_cpu_normalized', log)
    def mpost(value):
        log.append(('official_mccg_post', value.tag))
        return Tensor('mccg_gpu_normalized', log)
    torch = SimpleNamespace(Tensor=Tensor, flip=flip)
    context = SimpleNamespace(runtime=SimpleNamespace(torch=torch, numpy=FakeNumpy()), family=family, model=model,
        official=SimpleNamespace(_view_output=view_output, qdfl_postprocess=qpost, mccg_postprocess=mpost))
    with patch.object(n, 'require_native', return_value=None):
        result = n.native_descriptor(context, Tensor('original', log), role)
    return context, result, log

def main():
    k = b.common()
    forbidden = {'torch', 'numpy', 'PIL', 'torchvision', 'matplotlib', 'transformers', 'scipy'}
    trees = {}
    for file in HERE.glob('*.py'):
        tree = ast.parse(file.read_text(encoding='utf-8'), filename=str(file))
        compile(tree, str(file), 'exec')
        trees[file.name] = tree
    ok('new source ASTs parse/compile without executing', True)
    ok('all adapter modules import without scientific libraries', not forbidden.intersection(sys.modules))
    for name, tree in trees.items():
        top_names = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                top_names |= {x.name.split('.')[0] for x in node.names}
            if isinstance(node, ast.ImportFrom) and node.module:
                top_names.add(node.module.split('.')[0])
        ok(name + ' has no module-scope science import', not top_names.intersection(forbidden))
    registry = b.slots()
    ok('seven original fit slots match including three independent QDFL seeds', len(registry) == 7 and
       [x['seed'] for x in registry if x['method'] == 'QDFL'] == [1, 2, 3])
    ok('ten external tasks differ honestly from primary eleven-task scope', len(b.EXPECTED_TASKS) == 10 and
       not any('street' in name for name in b.EXPECTED_TASKS))
    qtree = ast.parse((b.EXT / 'qdfl_official_evaluation.py').read_text(encoding='utf-8'))
    mtree = ast.parse((b.EXT / 'mccg_adapter.py').read_text(encoding='utf-8'))
    qsize = literal_assignment(qtree, 'EXPECTED_TEST_SIZE')
    for key, size in qsize.items():
        ok(key + ' native image size matches frozen evaluator', b.SIZES[key] == size)
    recipe = next(x.value for x in mtree.body if isinstance(x, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == 'PUBLISHED_RECIPE' for t in x.targets))
    msize = next(ast.literal_eval(value) for key, value in zip(recipe.keys, recipe.values)
                 if ast.literal_eval(key) == 'image_size')
    ok('MCCG is 256 not CCR 384', b.SIZES['mccg_convnext_tiny'] == tuple(msize) == (256, 256))
    matrix_tree = ast.parse((b.EXT / 'run_transactions_t1_matrix.py').read_text(encoding='utf-8'))
    ok('official extraction batches match frozen runner', b.BATCHES == literal_assignment(matrix_tree, 'EVALUATION_BATCH_SIZE'))
    for role in b.ROLE_NAMES:
        ok('explicit supported role ' + role, b.role_kind(role) in {'drone', 'satellite'})
    for role in ('satellite_drone', 'street', 'query_uav', '', None):
        refuses('reject ambiguous/unsupported role ' + str(role), lambda role=role: b.role_kind(role))
    _, _, log = operation_fixture('qdfl', 'query_drone')
    ok('QDFL original then GPU flip then mirrored forward', log[:3] == [('forward', 'original'), ('flip', (3,)), ('forward', 'mirror')])
    ok('QDFL delegates raw original+raw mirror to exact CPU postprocess without pre-normalizing mirror',
       log[3] == ('official_qdfl_post', 'original_features', 'mirror_features') and not any(x[0] == 'raw_sum' for x in log))
    for role in ('query_drone', 'query_satellite'):
        context, _, log = operation_fixture('mccg', role)
        routes = [entry for entry in log if entry[0] == 'route']
        ok('MCCG ' + role + ' sends two forwards through same actual model object',
           routes == [('route', role, id(context.model)), ('route', role, id(context.model))])
        kinds = [entry[0] for entry in log]
        ok('MCCG ' + role + ' sums raw outputs before GPU postprocess and D2H',
           kinds.index('raw_sum') < kinds.index('official_mccg_post') < kinds.index('cpu'))
    for family in ('qdfl', 'mccg'):
        expected = b.native_environment(family)
        ok(family + ' environment is source-specific, not primary baseline', 'lgm-baselines' not in expected['executable'])
    with patch.object(b, 'source_manifest', return_value={}), \
         patch.object(k, 'read', return_value={'status': 'official_evaluation_running'}), \
         patch.object(b, 'slots', return_value=registry), patch.object(b, 'checkpoint_path') as cp:
        refuses('unfinished T1 refuses binding before checkpoint resolution', lambda: b.bind_completed_slot(registry[0]['run_id']))
        ok('no future checkpoint lookup after incomplete T1 gate', not cp.called)
    load_fn = next(x for x in trees['native_load.py'].body if isinstance(x, ast.FunctionDef) and x.name == 'load_native_slot')
    first_science = min(x.lineno for x in ast.walk(load_fn) if isinstance(x, ast.Import)
                        and any(a.name in {'numpy', 'torch'} for a in x.names))
    for guard in ('verify_binding', 'verify_current_environment', 'gpu_idle'):
        guard_line = next(x.lineno for x in ast.walk(load_fn) if isinstance(x, ast.Call)
                          and isinstance(x.func, ast.Attribute) and x.func.attr == guard)
        ok(guard + ' occurs before native scientific imports', guard_line < first_science)
    for name in ('load_model', 'validate_fit_gate', 'validate_existing_fit', 'validate_existing_evaluation'):
        ok('real frozen loader invokes ' + name, any(isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute)
            and x.func.attr == name for x in ast.walk(load_fn)))
    with patch.object(n, 'precision_state', return_value={'native_amp': False}):
        corrected = n.clean_measurement_metadata(None, {'runtime_flags': {'native_formal_autocast': 'float16',
            'native_clip_autocast': 'float16', 'device': 'cuda:0'}, 'scope': 'fixture'})
    ok('T1 reports native AMP false and removes inherited primary FP16 labels', corrected['runtime_flags'] == {'device': 'cuda:0', 'native_amp': False})
    ok('no controller/launcher source exists', not any(x in (HERE / 'native_load.py').read_text(encoding='utf-8')
                                                    for x in ('subprocess.Popen(', 'subprocess.run(')))
    ok('no scientific library loaded by checks', not forbidden.intersection(sys.modules))
    report = {'schema': 'external-t1-adapter-stdlib-check.v1', 'created_utc': k.now(), 'passed': len(checks),
        'failed': 0, 'checks': checks, 'scientific_imports': [], 'scientific_execution_performed': False,
        'mock_operations_are_test_fixtures_not_measurements': True,
        'source_files': [k.record(p) for p in sorted(HERE.glob('*.py'))]}
    k.write_new(HERE / 'STDLIB_REVIEW.json', report)
    print(json.dumps({'passed': len(checks), 'failed': 0, 'scientific_execution': False}))

if __name__ == '__main__':
    main()
