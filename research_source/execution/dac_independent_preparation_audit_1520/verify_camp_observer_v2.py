"""Test actual source-extracted parent signature and production context manager.

Scientific imports are intercepted. Only scalar AverageMeter source is executed;
fake sample4geo modules stand in for imports in the observation context manager.
"""
import ast
from contextlib import redirect_stdout
from datetime import datetime, timezone
import hashlib
import importlib.abc
import importlib.util
import io
import json
import math
from pathlib import Path
import sys
import tempfile
from types import ModuleType
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parent
NEW = EXECUTION / 'camp_training_preparation_v2'
OLD = EXECUTION / 'camp_training_preparation'
SOURCE = EXECUTION.parent / 'literature/official_repos/snapshots/Mabel0403__CAMP__b04a9c856711'
blocked = {'torch','torchvision','numpy','scipy','matplotlib','PIL','cv2','timm','albumentations','sample4geo'}

class DenyScientific(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname.split('.')[0] in blocked:
            raise AssertionError('Scientific import attempted: ' + fullname)

sys.meta_path.insert(0, DenyScientific())

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def canon(n):
    return ast.dump(n, include_attributes=False)

def main():
    checks = {}
    before_tree = ast.parse((OLD / 'camp_train_runtime.py').read_text(encoding='utf-8'))
    after_tree = ast.parse((NEW / 'camp_train_runtime.py').read_text(encoding='utf-8'))
    calls = [n for n in ast.walk(before_tree) if isinstance(n, ast.Call) and ast.unparse(n.func) == 'super().update']
    assert len(calls) == 1 and [ast.unparse(x) for x in calls[0].args] == ['val','n']
    calls[0].args.pop()
    assert canon(before_tree) == canon(after_tree)
    checks['entire_runtime_ast_equal_except_one_removed_forward_argument'] = True
    base_tree = ast.parse((SOURCE / 'sample4geo/utils.py').read_text(encoding='utf-8'))
    base_node = next(n for n in base_tree.body if isinstance(n, ast.ClassDef) and n.name == 'AverageMeter')
    base_namespace = {}
    exec(compile(ast.Module(body=[base_node], type_ignores=[]), 'exact-official-AverageMeter', 'exec'), base_namespace)
    Base = base_namespace['AverageMeter']
    base_update = next(n for n in base_node.body if isinstance(n, ast.FunctionDef) and n.name == 'update')
    assert [a.arg for a in base_update.args.args] == ['self','val']
    checks['official_parent_signature_extracted_without_module_import'] = True
    runtime = load(NEW / 'camp_train_runtime.py', 'camp_train_runtime')
    original_runtime = load(OLD / 'camp_train_runtime.py', 'original_camp_observer_runtime_for_test')
    assert runtime.HERE == NEW
    checks['v2_runtime_resolves_own_directory'] = True
    root = ModuleType('sample4geo')
    root.__path__ = []
    trainer = ModuleType('sample4geo.trainer')
    trainer.AverageMeter = Base
    root.trainer = trainer
    with tempfile.TemporaryDirectory(prefix='scalar_observer_', dir=HERE) as temp:
        def new_run(cls):
            value = cls.__new__(cls)
            value.output = Path(temp)
            value.loss_observations = []
            return value
        with patch.dict(sys.modules, {'sample4geo': root, 'sample4geo.trainer': trainer}):
            bad_run = new_run(original_runtime.TrainRun)
            with bad_run.training_observers():
                bad = trainer.AverageMeter()
                try:
                    bad.update(2.5)
                except TypeError as error:
                    checks['v1_actual_context_manager_counterexample'] = str(error)
                else:
                    raise AssertionError('The v1 production observer should fail')
                assert bad.count == 0
            assert trainer.AverageMeter is Base
            checks['v1_restores_original_class_after_error'] = True
            run = new_run(runtime.TrainRun)
            original_meter = Base()
            with run.training_observers():
                observed = trainer.AverageMeter()
                for val in (2.5, 1.0, -0.25, 0.0):
                    original_meter.update(val)
                    observed.update(val)
                    assert vars(observed) == vars(original_meter)
                assert run.loss_observations == [2.5, 1.0, -0.25, 0.0]
            assert trainer.AverageMeter is Base
            checks['v2_actual_context_manager_preserves_every_parent_field_four_updates'] = True
            checks['v2_observes_original_scalar_once_per_update'] = True
            checks['v2_restores_original_class_after_success'] = True
            for label, val in [('nan', float('nan')), ('inf', float('inf')), ('minus_inf', -float('inf'))]:
                run = new_run(runtime.TrainRun)
                try:
                    with run.training_observers():
                        observed = trainer.AverageMeter()
                        observed.update(val)
                except RuntimeError as error:
                    assert 'non-finite' in str(error)
                else:
                    raise AssertionError('Non-finite loss must be rejected')
                assert observed.count == 0 and run.loss_observations == []
                assert trainer.AverageMeter is Base
                checks['nonfinite_' + label + '_rejected_before_parent_update_and_class_restored'] = True
    for label, path in [('profile', EXECUTION / 'camp_training_execution/run_stage.py'),
                        ('train', NEW / 'prepare_or_train.py')]:
        tree = ast.parse(path.read_text(encoding='utf-8'))
        contexts = [n for n in ast.walk(tree) if isinstance(n, ast.With)
                    and any(isinstance(i.context_expr, ast.Call)
                        and ast.unparse(i.context_expr.func) == 'run.training_observers' for i in n.items)]
        assert len(contexts) == 1
        assert any(isinstance(n, ast.Call) and ast.unparse(n.func) == 'runpy.run_path' for n in ast.walk(contexts[0]))
        checks[label + '_production_run_path_enclosed_by_tested_observer'] = {'path': str(path),
            'sha256': sha(path), 'line': contexts[0].lineno}
    # Rerun existing lightweight validation while routing only its final report
    # out of the immutable 18-file copy. All original scientific-import blockers
    # stay enabled, and original temporary failed-run fixture directories vanish.
    sys.path.insert(0, str(NEW))
    for name in ('prepare_or_train','serial_release'):
        sys.modules.pop(name, None)
    validation = load(NEW / 'validate_cpu.py', 'camp_v2_existing_cpu_validation')
    original_write = validation.write_json
    target = HERE / 'CAMP_V2_BASE_CPU_VALIDATION.json'
    def routed_write(path, value):
        if Path(path).resolve() == (NEW / 'CPU_VALIDATION.json').resolve():
            return original_write(target, value)
        return original_write(path, value)
    with patch.object(validation, 'write_json', routed_write), redirect_stdout(io.StringIO()):
        validation.main()
    existing = json.loads(target.read_text(encoding='utf-8'))
    assert not existing['torch_imported'] and not existing['gpu_execution']
    checks['original_lightweight_validation_rerun_on_v2'] = {'path': str(target), 'sha256': sha(target)}
    legacy_manifest = json.loads((OLD/'PREPARATION_MANIFEST.json').read_text(encoding='utf-8'))
    changes = [r['path'] for r in legacy_manifest['files'] if sha(NEW/r['path']) != r['sha256']]
    assert changes == ['camp_train_runtime.py']
    checks['only_one_of_18_payload_files_changed_after_checks'] = changes
    checks['no_original_payload_modified'] = all(sha(OLD/r['path']) == r['sha256'] for r in legacy_manifest['files'])
    assert checks['no_original_payload_modified']
    assert not blocked.intersection(sys.modules)
    checks['scientific_modules_not_imported'] = True
    record = {'status':'passed', 'created_utc':datetime.now(timezone.utc).isoformat(),
        'runtime_sha256':sha(NEW/'camp_train_runtime.py'),
        'official_utils_sha256':sha(SOURCE/'sample4geo/utils.py'),
        'checks':checks, 'check_count':len(checks),
        'scientific_imports':[], 'training':False, 'profile':False,
        'cuda':False, 'queue_registration':False,
        'limits':'Actual model training/profile and tensor round-trip still require serial runtime validation.'}
    (HERE/'CAMP_V2_OBSERVER_REVIEW.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(json.dumps({'status':'passed','checks':len(checks), 'report':str(HERE/'CAMP_V2_OBSERVER_REVIEW.json')}))

if __name__ == '__main__':
    main()
