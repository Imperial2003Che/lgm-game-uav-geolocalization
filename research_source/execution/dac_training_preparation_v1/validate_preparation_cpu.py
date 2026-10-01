"""Standard-library source/contract fixtures only; never a model or resource test."""
import ast
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.abc
import json
import math
from pathlib import Path
import runpy
import sys
import tempfile
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
BLOCKED = {'torch', 'numpy', 'PIL', 'timm', 'cv2', 'albumentations', 'scipy',
    'torchvision', 'transformers', 'tensorboard', 'sklearn'}
IMPORT_ATTEMPTS = []

class NoScientificImport(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in BLOCKED:
            IMPORT_ATTEMPTS.append(fullname)
            raise RuntimeError('Scientific import prohibited in stdlib fixture: ' + fullname)

sys.meta_path.insert(0, NoScientificImport())
import common_runtime as common
import dac_train_runtime as runtime
import input_contract as inputs
import run_dac_training as launch
import gate_helpers as gate

RESULTS = []
def check(name, function):
    try:
        function()
        RESULTS.append({'name': name, 'passed': True})
    except BaseException as error:
        RESULTS.append({'name': name, 'passed': False, 'error': repr(error)})

def require(condition, message='Fixture assertion failed'):
    if not condition:
        raise AssertionError(message)

def rejects(function):
    try:
        function()
    except (RuntimeError, KeyError, ValueError, TypeError):
        return
    raise AssertionError('Expected rejection did not occur')

def tree(path):
    return ast.parse(Path(path).read_text(encoding='utf-8'))

def dump(node):
    return ast.dump(node, include_attributes=False)

def named(path, name):
    return next(node for node in tree(path).body if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name == name)

def calls(path, name):
    return [dump(node) for node in ast.walk(tree(path)) if isinstance(node, ast.Call) and ast.unparse(node.func) == name]

def assignment(path, name):
    return [dump(node) for node in ast.walk(tree(path)) if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)]

def json_write(path, value):
    Path(path).write_text(json.dumps(value, indent=2), encoding='utf-8')

def fake_state():
    schema = json.loads((HERE / 'DAC_EXPECTED_MODEL_SCHEMA.json').read_text(encoding='utf-8'))['tensors']
    return {key: SimpleNamespace(shape=tuple(row['shape']), dtype=row['dtype']) for key, row in schema.items()}

def make_run(directory):
    plan = {'method': 'DAC', 'seed': 1, 'source_directory': str(runtime.SCIENTIFIC_SOURCE),
        'output_directory': str(directory), 'train_root': str(directory / 'train'),
        'pretrained': {'path': str(directory / 'mock_initialization')},
        'official_configuration_defaults': inputs.configuration_defaults()}
    return runtime.DACTrainRun(plan, directory / 'fixture_plan', directory / 'fixture_profile')

def profile_fixture(directory):
    plan_path = directory / 'fixture_plan'
    plan_path.write_text('strictly a stdlib fixture; not an execution plan', encoding='utf-8')
    batch, resource = [], []
    for index, steps in enumerate((0, 1, 2), 1):
        batch.append({'batch_attempt': index, 'loss': 1.0 / index, 'loss_finite': True,
            'actual_optimizer_steps': steps, 'optimizer_updated_this_batch': index != 1,
            'amp_skips': index - steps})
        resource.append({'batch_attempt': index, 'actual_adamw_steps': steps,
            'amp_skips': index - steps, 'peak_allocated_bytes': 100, 'peak_reserved_bytes': 200})
    for name, rows in [('batch_progress.jsonl', batch), ('resource_batches.jsonl', resource)]:
        (directory / name).write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
    report = {'schema': 'dac-native-resource-profile.v1', 'method': 'DAC', 'status': 'passed',
        'plan_sha256': common.sha_file(plan_path), 'nominal_batch_pairs': 24, 'microbatch_pairs': 24,
        'gradient_accumulation': 1, 'img_size': 384, 'model_state_count': 402,
        'mixed_precision': True, 'all_official_losses': True, 'oom': False,
        'all_observed_losses_finite': True, 'all_model_floating_state_finite': True,
        'all_optimizer_floating_state_finite': True, 'representative_parameter_changed': True,
        'research_result': False, 'actual_adamw_steps': 2, 'completed_optimizer_amp_steps': 3,
        'amp_skips': 1, 'peak_allocated_bytes': 100, 'peak_reserved_bytes': 200,
        'fixture_only': True,
        'evidence_sha256': {name: common.sha_file(directory / name) for name in ('batch_progress.jsonl', 'resource_batches.jsonl')}}
    profile_path = directory / 'fixture_profile.json'
    json_write(profile_path, report)
    return plan_path, profile_path, report

def main():
    pin = json.loads((HERE / 'SOURCE_PIN.json').read_text(encoding='utf-8'))
    official = Path(pin['official_source_directory'])
    entry = HERE / 'train_university_train_only.py'
    original_entry = official / 'train_university.py'
    if not original_entry.exists():
        original_entry = official / 'train_university_1652.py'
    # Exact source path is taken from the builder's immutable entry metadata.
    if not original_entry.exists():
        candidates = [official / row['path'] for row in pin['files'] if row['path'].endswith('.py') and common.sha_file(official / row['path']) == '2345a2b8ffe8722cbfeff8c607fc737a95aa55377ab75eb429ef397fa52209a8']
        require(len(candidates) == 1)
        original_entry = candidates[0]
    check('all adapter/scientific Python files parse without importing them', lambda: [tree(path) for path in HERE.rglob('*.py')])
    check('all 36 official and 19 private file hashes match', lambda: (require(len(pin['files']) == 36), require(len(runtime.verify_scientific_source()['files']) == 19)))
    check('generic runtime byte-identical to reviewed CAMP v2 plumbing', lambda: require(common.sha_file(HERE / 'common_runtime.py') == '3cbf41ddef34fba1bb1a57f5eca287129748708abb21941f63ff9a5ac40d9b26'))
    for helper in ('environment', 'runtime_environment', 'data_manifest'):
        check('inherited input helper exact AST: '+helper, lambda helper=helper: require(dump(named(HERE/'input_audit.py',helper))==dump(named(HERE.parent/'camp_training_preparation_v2/prepare_or_train.py',helper))))
    for helper in ('alive', 'owners', 'exclusive_latest_baseline_lock'):
        check('inherited PID/lock helper exact AST including decorators: '+helper, lambda helper=helper: require(dump(named(HERE/'gate_helpers.py',helper))==dump(named(HERE.parent/'camp_training_preparation_v2/serial_release.py',helper))))
    check('original DAC train function exact AST', lambda: require(dump(named(official / 'sample4geo/trainer.py', 'train')) == dump(named(runtime.SCIENTIFIC_SOURCE / 'sample4geo/trainer.py', 'train'))))
    for definition in ('get_data', 'U1652DatasetTrain', 'get_transforms'):
        check('original normal dataset AST: ' + definition, lambda definition=definition: require(dump(named(official / 'sample4geo/dataset/university.py', definition)) == dump(named(runtime.SCIENTIFIC_SOURCE / 'sample4geo/dataset/university.py', definition))))
    for function in ('torch.optim.AdamW', 'get_cosine_schedule_with_warmup', 'get_polynomial_decay_schedule_with_warmup', 'get_constant_schedule_with_warmup', 'DataLoader', 'train', 'DSA_loss', 'InfoNCE', 'GradScaler'):
        check('official constructor/call retained: ' + function, lambda function=function: require(calls(original_entry, function) == calls(entry, function) if function != 'DataLoader' else all(call in calls(original_entry, function) for call in calls(entry, function))))
    for name in ('train_steps_per', 'train_steps', 'warmup_steps', 'loss_functions'):
        check('official assignment retained: ' + name, lambda name=name: require(assignment(entry, name) == assignment(original_entry, name)))
    def scheduler_order():
        nodes = list(ast.walk(tree(entry)))
        assigned = next(node.lineno for node in nodes if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'train_steps' for target in node.targets))
        shuffled = [node.lineno for node in nodes if isinstance(node, ast.Call) and ast.unparse(node.func) == 'train_dataloader.dataset.shuffle']
        require(len(shuffled) == 2 and assigned < min(shuffled))
    check('scheduler total computed before first shuffle, post-epoch shuffle retained', scheduler_order)
    def no_tests():
        forbidden = {'evaluate', 'evaluate_trs', 'predict', 'U1652DatasetEval', 'query_dataloader_test', 'reference_dataloader', 'best_score', 'checkpoint_start', 'only_test', 'zero_shot'}
        names = {node.id for node in ast.walk(tree(entry)) if isinstance(node, ast.Name)}
        attrs = {node.attr for node in ast.walk(tree(entry)) if isinstance(node, ast.Attribute)}
        require(not forbidden.intersection(names | attrs))
        require(not any(isinstance(node, ast.Constant) and isinstance(node.value, str) and '/test/' in node.value for node in ast.walk(tree(entry))))
    check('training entry has no test objects, paths or test-based selection', no_tests)
    def direct_guard():
        try:
            runpy.run_path(str(entry), run_name='fixture_unadmitted')
        except RuntimeError as error:
            require('separately admitted' in str(error))
        else:
            raise AssertionError('Unadmitted entry ran')
        require(not IMPORT_ATTEMPTS)
    check('unadmitted entry stops before first scientific import', direct_guard)
    check('all DAC scientific defaults preserved', lambda: require(all(getattr(inputs.make_configuration(), key) == value for key, value in runtime.REQUIRED.items())))
    check('402 exact fake key/shape/dtype fixture accepted', lambda: runtime.validate_model_schema(fake_state()))
    def altered_schema(kind):
        state = fake_state()
        if kind == '395':
            for key in list(state)[-7:]:
                del state[key]
        elif kind == 'shape':
            state[next(iter(state))].shape = (999,)
        else:
            state[next(iter(state))].dtype = 'torch.float16'
        rejects(lambda: runtime.validate_model_schema(state))
    for kind in ('395', 'shape', 'dtype'):
        check('reject CAMP/altered DAC schema: ' + kind, lambda kind=kind: altered_schema(kind))
    with tempfile.TemporaryDirectory(prefix='stdlib_fixtures_', dir=HERE) as temp_name:
        temporary = Path(temp_name).resolve()
        require(temporary.is_relative_to(HERE))  # bounds checked before automatic recursive fixture cleanup
        def original_average_meter():
            namespace = {}
            node = named(official / 'sample4geo/utils.py', 'AverageMeter')
            exec(compile(ast.Module(body=[node], type_ignores=[]), 'original-DAC-AverageMeter-only', 'exec'), namespace)
            package, trainer = ModuleType('sample4geo'), ModuleType('sample4geo.trainer')
            package.trainer = trainer
            trainer.AverageMeter = namespace['AverageMeter']
            run = make_run(temporary)
            with patch.dict(sys.modules, {'sample4geo': package, 'sample4geo.trainer': trainer}):
                with run.training_observers():
                    meter = trainer.AverageMeter()
                    meter.update(2.0)
                    meter.update(4.0)
                    require(meter.avg == 3.0 and meter.count == 2 and run.loss_observations == [2.0, 4.0])
                    rejects(lambda: meter.update(float('nan')))
                    rejects(lambda: meter.update(float('inf')))
                require(trainer.AverageMeter is namespace['AverageMeter'])
        check('real original AverageMeter.update(val) signature; finite/NaN/inf/context restore', original_average_meter)
        def counted_after_batch():
            seen = []
            class Loader:
                dataset = SimpleNamespace()
                def __len__(self): return 2
                def __iter__(self): return iter([1, 2])
            wrapped = common.CountedLoader(Loader(), seen.append)
            iterator = iter(wrapped)
            require(next(iterator) == 1 and seen == [])
            require(next(iterator) == 2 and seen == [1])
            require(list(iterator) == [] and seen == [1, 2] and wrapped.completed_batches == 2)
        check('loader records only after official batch consumer returns', counted_after_batch)
        def real_update_counter():
            run = make_run(temporary)
            model = SimpleNamespace(named_parameters=lambda: [('model.convnext.downsample_layers.0.0.weight', SimpleNamespace(requires_grad=True, shape=(128,3,4,4), dtype='float32'))])
            hooks = []
            optimizer = SimpleNamespace(register_step_post_hook=lambda hook: hooks.append(hook) or object(), param_groups=[{'lr':0.001}])
            with patch.object(common.TrainRun, 'parameter_digest', return_value='fixture_digest'):
                common.TrainRun.observe_optimizer(run, optimizer, model, SimpleNamespace(get_scale=lambda:1024))
            run.epoch = 1
            run.observe_loss(1); run.after_batch(1)  # deliberate AMP skipped step, no optimizer hook
            hooks[0](optimizer, (), {}); run.observe_loss(0.9); run.after_batch(2)
            hooks[0](optimizer, (), {}); run.observe_loss(0.8); run.after_batch(3)
            require(run.actual_optimizer_steps == 2 and run.amp_skips == 1)
        check('actual optimizer hook distinguishes one AMP skip from two real updates', real_update_counter)
        def adam_state(kind):
            run = make_run(temporary)
            run.actual_optimizer_steps = 2
            row = {'step':2, 'exp_avg':True, 'exp_avg_sq':True}
            optimizer_state = {'state': {0:row}, 'param_groups':[{'lr':0.001}]}
            attempts = 3
            if kind == 'empty': optimizer_state['state'] = {}
            elif kind == 'zero': row['step'] = 0
            elif kind == 'missing': del row['exp_avg']
            elif kind == 'nonfinite': row['exp_avg'] = False
            elif kind == 'hook_mismatch': row['step'] = 1
            elif kind == 'scheduler_mismatch': attempts = 1578
            fake_torch = ModuleType('torch')
            fake_torch.isfinite = lambda value: SimpleNamespace(all=lambda:SimpleNamespace(item=lambda:bool(value)))
            namespace = {'model':SimpleNamespace(state_dict=fake_state),
                'optimizer':SimpleNamespace(state_dict=lambda:optimizer_state),
                'scheduler':SimpleNamespace(state_dict=lambda:{'last_epoch':attempts}),
                'train_dataloader':SimpleNamespace(completed_batches=3), 'train_steps':1578, 'warmup_steps':157.8}
            with patch.dict(sys.modules, {'torch':fake_torch}), patch.object(common.TrainRun, 'save_complete') as parent:
                if kind == 'valid':
                    run.save_complete(namespace)
                    require(parent.call_count == 1)
                else:
                    rejects(lambda:run.save_complete(namespace))
                    require(parent.call_count == 0)
        for kind in ('valid', 'empty', 'zero', 'missing', 'nonfinite', 'hook_mismatch', 'scheduler_mismatch'):
            check('saved AdamW/scheduler pure fake-state fixture: ' + kind, lambda kind=kind: adam_state(kind))
        for kind in ('valid', 'wrong_method', 'wrong_count', 'all_skipped', 'oom', 'no_memory', 'tampered_trace', 'lying_steps'):
            def profile_case(kind=kind):
                directory = temporary / ('profile_' + kind); directory.mkdir()
                plan, profile, report = profile_fixture(directory)
                if kind == 'wrong_method': report['method'] = 'CAMP'
                elif kind == 'wrong_count': report['model_state_count'] = 395
                elif kind == 'all_skipped': report['actual_adamw_steps'] = 0
                elif kind == 'oom': report['oom'] = True
                elif kind == 'no_memory': report['peak_allocated_bytes'] = 0
                elif kind == 'tampered_trace': (directory / 'batch_progress.jsonl').write_text('{}\n', encoding='utf-8')
                elif kind == 'lying_steps':
                    report['actual_adamw_steps'] = 3; report['amp_skips'] = 0
                json_write(profile, report)
                if kind == 'valid': launch.validate_profile(plan, profile)
                else: rejects(lambda:launch.validate_profile(plan, profile))
            check('bounded native profile contract fixture: ' + kind, profile_case)
        def lock_context():
            fake = ModuleType('msvcrt'); fake.LK_NBLCK=1; fake.LK_UNLCK=2
            observed=[]; fake.locking=lambda fd, mode, size: observed.append((mode,size))
            with patch.dict(sys.modules, {'msvcrt':fake}), patch.object(gate, 'EXECUTION', temporary):
                with gate.exclusive_latest_baseline_lock(): require(observed == [(1,1)])
            require(observed == [(1,1),(2,1)])
        check('shared Windows lock is a usable context manager and releases same byte', lock_context)
        def predecessor(kind):
            start='2026-09-14T00:00:00+00:00'
            job=lambda ident:{'id':ident,'status':'completed','exit_code':0,'pid':101,'started_utc':start}
            states={
                'status.json':{'status':'completed','stage':'all','controller_pid':101,'started_utc':start},
                'pipeline_status.json':{'status':'ready_for_extension_preparation','supervisor_pid':102,'supervisor_started_utc':start,'jobs':[job(ident) for ident in ['formal_aggregate','formal_figures','cross_dataset_transfer','robustness','robustness_aggregate','query_analysis','formal_efficiency_component']]},
                'extension_plan.json':{'jobs':[job('ext1'),job('ext2'),job('ext3'),job('ext4')]},
                'latest_baseline_plan.json':{'jobs':[job('CAMP-author'),job('DAC-author')]}}
            for name,status,plan in [('extension_status.json','registered_extensions_finished_review_pending','extension_plan.json'),('latest_baseline_status.json','latest_baselines_finished_review_pending','latest_baseline_plan.json')]:
                states[name]={'status':status,'plan_sha256':'fixture-'+plan,'supervisor_pid':103,'supervisor_started_utc':start,'jobs':deepcopy(states[plan]['jobs'])}
            release={'schema':'dac-university-training-release.v1','allow_cuda':True,'training_plan_sha256':'fixture-plan',
                'preceding_plan_sha256':{name:'fixture-'+name for name in ('extension_plan.json','latest_baseline_plan.json')}}
            if kind == 'running': states['status.json']['status']='running'
            if kind == 'wrong_ids': states['extension_status.json']['jobs'][0]['id']='other'
            if kind == 'failed_exit': states['latest_baseline_status.json']['jobs'][0]['exit_code']=1
            if kind == 'missing_started': del states['pipeline_status.json']['supervisor_started_utc']
            if kind == 'no_owners': states['status.json'].pop('controller_pid')
            if kind == 'wrong_plan': states['extension_status.json']['plan_sha256']='other'
            if kind == 'missing_status': del states['extension_status.json']
            def read_mock(path): return deepcopy(release if Path(path).name=='fixture-release' else states[Path(path).name])
            def hash_mock(path): return 'fixture-plan' if Path(path).name=='fixture-plan' else 'fixture-'+Path(path).name
            with patch.object(launch,'read',read_mock), patch.object(launch,'sha_file',hash_mock), patch.object(launch,'alive',return_value=kind=='live_pid'), patch.object(launch.subprocess,'run',return_value=SimpleNamespace(stdout='123, python.exe' if kind=='gpu_busy' else '')):
                action=lambda:launch.serial_release_gate(Path('fixture-plan'),Path('fixture-release'))
                if kind=='valid': require(action()['shared_gpu_lock_held'] is True)
                else: rejects(action)
        for kind in ('valid','running','wrong_ids','failed_exit','missing_started','no_owners','wrong_plan','missing_status','live_pid','gpu_busy'):
            check('fresh serial release pure mocked process/GPU fixture: '+kind,lambda kind=kind:predecessor(kind))
        for kind in ('valid', 'old_source', 'wrong_environment', 'wrong_model', 'cuda_used', 'bad_pair'):
            def cpu_case(kind=kind):
                proof = {'schema':'dac-real-cpu-compatibility.v1', 'status':'passed', 'method':'DAC',
                    'model_state_count':402, 'pretrained_strict_tensor_count':344,
                    'real_pair_original_transforms_passed':True, 'cuda_initialized':False,
                    'author_trained_weights_loaded':False, 'all_model_floating_state_finite':True,
                    'all_pair_floating_values_finite':True, 'source_files_sha256':launch.cpu_source_bindings(),
                    'environment':{'fixture':'no real scientific environment used'}}
                plan={'environment':deepcopy(proof['environment'])}
                if kind=='old_source': proof['source_files_sha256']['dac_train_runtime.py']='stale'
                elif kind=='wrong_environment': proof['environment']={'fixture':'different'}
                elif kind=='wrong_model': proof['model_state_count']=395
                elif kind=='cuda_used': proof['cuda_initialized']=True
                elif kind=='bad_pair': proof['all_pair_floating_values_finite']=False
                path=temporary/('cpu_proof_'+kind+'.json'); json_write(path,proof)
                plan['cpu_compatibility_proof']={'path':str(path),'sha256':common.sha_file(path)}
                if kind=='valid': launch.validate_cpu_proof(plan)
                else: rejects(lambda:launch.validate_cpu_proof(plan))
            check('real CPU evidence contract mocked only: '+kind,cpu_case)
        def process_environment_case():
            actual={name:launch.os.environ.get(name) for name in launch.PROCESS_ENVIRONMENT_KEYS}
            require(launch.process_environment({'process_environment':actual})==actual)
            rejects(lambda:launch.process_environment({'process_environment':{}}))
        check('future process environment is explicitly bound and never silently set',process_environment_case)
    check('CPU helper seeds original setup before model and uses real model normalization', lambda: require('setup_system(' in (HERE/'input_contract.py').read_text(encoding='utf-8') and "data_config['mean']" in (HERE/'input_contract.py').read_text(encoding='utf-8')))
    check('official misspelled cuDNN attribute observed at exact original object', lambda: require("getattr(torch.backends, 'cudnn_benchmark_enabled', None)" in (HERE/'dac_train_runtime.py').read_text(encoding='utf-8')))
    check('no scientific import attempted/executed by fixture process', lambda: require(not IMPORT_ATTEMPTS and not BLOCKED.intersection(sys.modules)))
    files = {path.relative_to(HERE).as_posix():common.sha_file(path) for path in HERE.rglob('*.py')}
    report={'schema':'dac-preparation-stdlib-validation.v1','status':'passed' if all(row['passed'] for row in RESULTS) else 'failed',
        'generated_utc':datetime.now(timezone.utc).isoformat(),'checks':RESULTS,'passed':sum(row['passed'] for row in RESULTS),'total':len(RESULTS),
        'source_files_sha256':files,'scientific_import_attempts':IMPORT_ATTEMPTS,'real_model_or_images_loaded':False,'cuda_used':False,
        'resource_measurement_executed':False,'fixture_numbers_are_not_measurements':True}
    json_write(HERE/'CPU_VALIDATION.json',report)
    print(json.dumps({'status':report['status'],'passed':report['passed'],'total':report['total'],'failures':[row for row in RESULTS if not row['passed']]}))
    if report['status']!='passed': raise SystemExit(1)

if __name__ == '__main__': main()
