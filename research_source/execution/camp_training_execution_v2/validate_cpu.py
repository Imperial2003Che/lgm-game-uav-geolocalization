"""Pure-stdlib/AST fixtures. Never performs resource profiling or training."""
import ast
import copy
import importlib.abc
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

BLOCKED = {'torch', 'torchvision', 'numpy', 'scipy', 'PIL', 'cv2', 'timm', 'albumentations',
           'sklearn', 'transformers', 'tensorboard', 'pptx', 'sample4geo'}
class NoScience(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in BLOCKED:
            raise RuntimeError('CPU validation forbids scientific import: ' + fullname)
        return None

sys.meta_path.insert(0, NoScience())
sys.dont_write_bytecode = True
import contracts as c
import run_stage as stage
import supervise_training as supervisor

def expect_error(action, kind=RuntimeError):
    try:
        action()
    except kind:
        return
    raise AssertionError('Expected failure was not raised')

def completed_predecessor():
    started = '2026-09-14T00:00:00+00:00'
    return {'status': c.FINAL_LATEST_STATUS, 'plan_sha256': 'latest-plan',
        'supervisor_pid': 100, 'supervisor_started_utc': started,
        'jobs': [{'id': name, 'status': 'completed', 'exit_code': 0, 'pid': 101 + i,
                  'started_utc': started} for i, name in enumerate(c.LATEST_IDS)]}

def fixtures():
    checks = []
    def passed(name):
        checks.append({'check': name, 'passed': True})
    preparation_proof = c.validate_preparation()
    api, gate, runtime = c.frozen_api()
    official_code = api.code_manifest()
    input_plans = {}
    for seed in (1, 2, 3):
        path = c.EXECUTION / 'camp_training_inputs_v2' / f'seed_{seed}_plan.json'
        value = c.read(path)
        assert value['code_manifest'] == official_code and value['seed'] == seed
        input_plans[str(seed)] = {'path': str(path), 'sha256': c.sha(path)}
    assert not BLOCKED.intersection(sys.modules)
    passed('All 18 frozen preparation files verified; stdlib imports load no science modules')
    passed('All 37 official source hashes match each of the three actual root-created seed plans')
    environment_plan = {'thread_environment': {'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'}, 'CUDA_VISIBLE_DEVICES': '0'}
    with patch.dict(c.os.environ, {**environment_plan['thread_environment'], 'CUDA_VISIBLE_DEVICES': '0'}):
        assert c.validate_stage_environment(environment_plan)['CUDA_VISIBLE_DEVICES'] == '0'
        with patch.dict(c.os.environ, {'OMP_NUM_THREADS': '8'}):
            expect_error(lambda: c.validate_stage_environment(environment_plan))
    passed('Exact child CUDA/thread environment is required and mismatches fail')
    for path in c.HERE.glob('*.py'):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in tree.body:
            if isinstance(node, ast.Import):
                assert all(alias.name.split('.')[0] not in BLOCKED for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                assert (node.module or '').split('.')[0] not in BLOCKED
    passed('All execution source parses; no top-level scientific imports')
    original = ast.parse((c.PREPARATION / 'train_university_train_only.py').read_text(encoding='utf-8'))
    assert any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'observe_optimizer' for node in ast.walk(original))
    assert 'register_step_post_hook' in (c.PREPARATION / 'camp_train_runtime.py').read_text(encoding='utf-8')
    assert 'runpy.run_path' in (c.HERE / 'run_stage.py').read_text(encoding='utf-8')
    passed('Profiler invokes frozen official entry and retains real optimizer post-step hook')

    previous = completed_predecessor()
    assert len(c.check_latest_state(previous, 'latest-plan', lambda *args: False)) == 3
    passed('Both author jobs completed with all original owners exited are accepted')
    for name, mutate in (
        ('wrong plan', lambda s: s.update(plan_sha256='different')),
        ('wrong IDs', lambda s: s['jobs'][0].update(id='wrong')),
        ('missing job', lambda s: s['jobs'].pop()),
        ('failed job', lambda s: s['jobs'][0].update(status='failed', exit_code=1)),
        ('nonzero exit', lambda s: s['jobs'][0].update(exit_code=1)),
        ('missing PID', lambda s: s['jobs'][0].pop('pid')),
        ('missing timestamp', lambda s: s['jobs'][0].pop('started_utc')),
    ):
        value = copy.deepcopy(previous)
        mutate(value)
        expect_error(lambda: c.check_latest_state(value, 'latest-plan', lambda *args: False))
        passed('Predecessor rejects ' + name)
    expect_error(lambda: c.check_latest_state(previous, 'latest-plan', lambda pid, started: pid == 102), c.PredecessorBusy)
    assert supervisor.predecessor_ready(previous, 'latest-plan', lambda pid, started: pid == 100) is False
    passed('Live completed predecessor/child remains waiting, not CUDA-ready')
    running = copy.deepcopy(previous)
    running.update(status='running_latest_baselines')
    assert supervisor.predecessor_ready(running, 'latest-plan', lambda *args: True) is False
    expect_error(lambda: supervisor.predecessor_ready(running, 'latest-plan', lambda *args: False))
    passed('Running predecessor waits; missing live supervisor fails instead of bypassing')
    def inaccessible(*args):
        raise RuntimeError('Win32 access denied')
    expect_error(lambda: c.check_latest_state(previous, 'latest-plan', inaccessible))
    passed('Unknown process state fails closed')

    with tempfile.TemporaryDirectory(prefix='camp_stdlib_validation_') as temporary:
        temp = Path(temporary)
        plan_path = temp / 'seed_plan.json'
        plan_path.write_text('{}', encoding='utf-8')
        plan = {'output_directory': str(temp / 'unused_full_run'), 'train_root': str(temp / 'train'),
                'source_directory': str(temp / 'source'), 'pretrained': {'path': str(temp / 'weight')}}
        class Parameter:
            requires_grad = True
            shape = (1,)
            dtype = 'synthetic-float'
        parameter = Parameter()
        class Model:
            def named_parameters(self):
                return [('model_1.convnext.downsample_layers.0.0.weight', parameter)]
        class Optimizer:
            param_groups = [{'lr': 0.001}]
            def register_step_post_hook(self, callback):
                self.callback = callback
                return SimpleNamespace(remove=lambda: None)
            def step(self):
                self.callback(self, (), {})
        class Loader:
            batch_size, num_workers, drop_last = 24, 0, False
            def __init__(self, number):
                self.number = number
                self.dataset = SimpleNamespace(ids=list(range(701)), samples=[(j, 's', 'd') for _ in range(number) for j in range(24)], pairs=list(range(number * 24)))
            def __len__(self):
                return self.number
            def __iter__(self):
                yield from range(self.number)
        cuda = SimpleNamespace(synchronize=lambda: None, max_memory_allocated=lambda: 100,
            max_memory_reserved=lambda: 200, memory_allocated=lambda: 80, memory_reserved=lambda: 200)
        fake_torch = SimpleNamespace(cuda=cuda)
        for name, updates, expected_exception in (
            ('amp_skip_then_two_real_steps', [False, True, True, True], stage.ProfileComplete),
            ('all_amp_skips_bound', [False] * 32, stage.ProfileLimit),
        ):
            output = temp / name
            output.mkdir()
            run = stage.make_profile_run(runtime, plan, plan_path, output / 'profile.json', output, fake_torch)
            optimizer = Optimizer()
            with patch.object(runtime.TrainRun, 'parameter_digest', return_value='initial-fixture-digest'):
                run.observe_optimizer(optimizer, Model(), SimpleNamespace(get_scale=lambda: 1024))
            wrapped = run.wrap_loader(Loader(len(updates)))
            run.before_epoch(1, wrapped)
            def simulate_original_batches():
                for index in wrapped:
                    run.observe_loss(2.0 - index / 100)
                    if updates[index]:
                        optimizer.step()
            expect_error(simulate_original_batches, expected_exception)
            rows = [json.loads(line) for line in (output / 'batch_progress.jsonl').read_text(encoding='utf-8').splitlines()]
            if name.startswith('amp_skip'):
                assert wrapped.completed_batches == 3 and run.actual_optimizer_steps == 2 and run.amp_skips == 1
                assert [row['actual_optimizer_steps'] for row in rows] == [0, 1, 2]
            else:
                assert wrapped.completed_batches == 32 and run.actual_optimizer_steps == 0 and run.amp_skips == 32
            assert not (output / 'weights_end.pth').exists()
            passed('Instrumented frozen batch observer: ' + name)
        # Build an explicitly synthetic profile from the mock observer's JSONL.
        # It lives only in the temporary fixture tree and is never a runtime receipt.
        fixture_dir = temp / 'amp_skip_then_two_real_steps'
        fixture_path = fixture_dir / 'profile.json'
        synthetic = {'schema': 'camp-native-resource-profile.v1', 'status': 'passed',
            'plan_sha256': c.sha(plan_path), 'execution_plan_sha256': c.sha(plan_path),
            'nominal_batch_pairs': 24, 'microbatch_pairs': 24, 'gradient_accumulation': 1,
            'img_size': 384, 'all_official_losses': True, 'mixed_precision': True, 'oom': False,
            'exclusive_gpu_allocation': True, 'research_result': False,
            'all_model_floating_state_finite': True, 'all_optimizer_floating_state_finite': True,
            'representative_parameter_changed': True, 'all_observed_losses_finite': True,
            'research_checkpoint_written': False, 'actual_adamw_steps': 2,
            'completed_optimizer_amp_steps': 3, 'amp_skips': 1, 'losses': [2.0, 1.99, 1.98],
            'initial_parameter_sha256': 'fixture-before', 'final_parameter_sha256': 'fixture-after',
            'peak_allocated_bytes': 100, 'peak_reserved_bytes': 200,
            'evidence_sha256': {name: c.sha(fixture_dir / name) for name in ('batch_progress.jsonl', 'resource_batches.jsonl')},
            'synthetic_fixture_only': True}
        binding = {'plan_sha256': c.sha(plan_path)}
        c.write(fixture_path, synthetic)
        assert c.verify_profile(fixture_path, binding, plan_path)['actual_adamw_steps'] == 2
        passed('Profile verifier reconciles actual-step, AMP-skip, finite-loss and resource JSONL records')
        for name, values in (
            ('only one actual step', {'actual_adamw_steps': 1}),
            ('wrong seed plan', {'plan_sha256': 'wrong'}),
            ('missing loss observation', {'losses': [2.0]}),
            ('unchanged parameters', {'final_parameter_sha256': 'fixture-before'}),
            ('missing CUDA measurement', {'peak_allocated_bytes': 0}),
        ):
            c.write(fixture_path, {**synthetic, **values})
            expect_error(lambda: c.verify_profile(fixture_path, binding, plan_path))
            passed('Resource evidence rejects ' + name)
        nonfinite_output = temp / 'nonfinite'
        nonfinite_output.mkdir()
        nonfinite_run = stage.make_profile_run(runtime, plan, plan_path, temp / 'none', nonfinite_output, fake_torch)
        expect_error(lambda: nonfinite_run.observe_loss(float('nan')))
        assert (nonfinite_output / 'nonfinite_loss.json').exists()
        passed('Original non-finite loss observation fails before backward')

        # Exercise the actual failure-report path, failing before any scientific import.
        failed_output = temp / 'profile_preflight_failure'
        row = {'seed': 1, 'plan_path': str(plan_path), 'plan_sha256': c.sha(plan_path), 'profile_directory': str(failed_output)}
        args = SimpleNamespace(execution_plan=plan_path, release_file=temp / 'not-created')
        with patch.object(stage, 'validate_inputs', side_effect=MemoryError('synthetic host allocation failure')):
            expect_error(lambda: stage.resource_profile(args, {}, row, api, gate, runtime), MemoryError)
        failure = c.read(failed_output / 'profile.json')
        assert failure['status'] == 'failed' and failure['oom'] is True and failure['research_result'] is False
        assert (failed_output / 'failure.log').exists()
        passed('Preflight host OOM retains failed profile/traceback without science import or batch change')

        # End-to-end supervisor fixtures, using fake Popen only. No child is launched.
        for scenario in ('all_six_success', 'first_profile_failure', 'surviving_child'):
            folder = temp / scenario
            folder.mkdir()
            execution_path = folder / 'execution_plan.json'
            release_path = folder / 'release.json'
            execution_path.write_text('{}', encoding='utf-8')
            release_path.write_text('{}', encoding='utf-8')
            c.write(folder / 'latest_baseline_status.json', completed_predecessor())
            execution_plan = {'python_executable': 'synthetic-python-never-executed', 'preceding_latest_plan_sha256': 'latest-plan',
                'thread_environment': {'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'}, 'CUDA_VISIBLE_DEVICES': '0',
                'seeds': [{'seed': i, 'plan_path': str(plan_path), 'plan_sha256': c.sha(plan_path),
                    'output_directory': str(folder / f'train_{i}'), 'profile_directory': str(folder / f'profile_{i}'),
                    'training_receipt_directory': str(folder / f'receipt_{i}')} for i in (1, 2, 3)]}
            calls = []
            class Child:
                pid = 900
                def __init__(self, fail=False):
                    self.returncode = None
                    self.fail = fail
                def poll(self):
                    if scenario == 'surviving_child':
                        return None
                    self.returncode = 1 if self.fail else 0
                    return self.returncode
                def wait(self):
                    return self.poll()
            def spawn(argv, **kwargs):
                state = c.read(folder / 'status.json')
                active = state['active_stage']
                assert active.endswith('_seed_' + argv[-1])
                index = int(argv[-1]) - 1
                record = state['seeds'][index]['profile_record' if 'profile_seed' in active else 'training_record']
                assert record['status'] == 'launch_intent' and record['command'] == argv
                assert kwargs['env']['CUDA_VISIBLE_DEVICES'] == '0'
                calls.append(active)
                if 'profile_seed' in active:
                    profile_dir = Path(execution_plan['seeds'][index]['profile_directory'])
                    profile_dir.mkdir()
                    c.write(profile_dir / 'profile.json', {'synthetic_fixture_only': True})
                return Child(fail=scenario == 'first_profile_failure')
            from contextlib import nullcontext
            def interrupted_sleep(seconds):
                if scenario == 'surviving_child':
                    raise KeyboardInterrupt('synthetic supervisor interruption')
            patches = (
                patch.object(supervisor, 'HERE', folder), patch.object(supervisor, 'EXECUTION', folder),
                patch.object(supervisor, 'validate_release', return_value=execution_plan),
                patch.object(supervisor, 'frozen_api', return_value=(None, SimpleNamespace(alive=lambda *args: False), None)),
                patch.object(supervisor, 'supervisor_lock', side_effect=lambda: nullcontext()),
                patch.object(supervisor.subprocess, 'Popen', side_effect=spawn),
                patch.object(supervisor.time, 'sleep', side_effect=interrupted_sleep),
                patch.object(supervisor, 'verify_profile', return_value={'synthetic_fixture_only': True}),
                patch.object(supervisor, 'verify_training', return_value={'synthetic_fixture_only': True}),
            )
            from contextlib import ExitStack
            with ExitStack() as stack:
                for item in patches:
                    stack.enter_context(item)
                action = lambda: supervisor.supervise(SimpleNamespace(plan=execution_path, release_file=release_path))
                if scenario == 'all_six_success':
                    action()
                else:
                    expect_error(action, KeyboardInterrupt if scenario == 'surviving_child' else RuntimeError)
            status = c.read(folder / 'status.json')
            if scenario == 'all_six_success':
                assert calls == ['profile_seed_1', 'train_seed_1', 'profile_seed_2', 'train_seed_2', 'profile_seed_3', 'train_seed_3']
                assert status['status'] == 'completed' and all(row['status'] == 'completed' and row['exit_code'] == 0 for row in status['seeds'])
                assert all(row['training_record']['pid'] == 900 and row['training_record']['exit_code'] == 0 for row in status['seeds'])
            elif scenario == 'first_profile_failure':
                assert len(calls) == 1 and status['status'] == 'failed' and status['seeds'][1]['status'] == 'pending'
                assert status['seeds'][0]['profile_record']['exit_code'] == 1
            else:
                assert len(calls) == 1 and status['surviving_child_pid'] == 900 and status['status'] == 'failed'
                assert status['seeds'][0]['profile_record']['status'] == 'running'
            passed('Standard-library supervisor fixture: ' + scenario)

    assert not BLOCKED.intersection(sys.modules)
    validate_now = c.validate_preparation()
    assert validate_now == preparation_proof
    passed('Frozen preparation unchanged after all fixtures; no scientific modules loaded')
    result = {'schema': 'camp-independent-training-cpu-validation.v1', 'status': 'passed', 'verified_utc': c.utc(),
        'scientific_libraries_imported': False, 'gpu_calls': False, 'real_children_started': 0,
        'resource_profile_executed': False, 'formal_training_executed': False, 'registered': False,
        'fixture_scope': 'Synthetic standard-library mocks validate control flow; these are not resource or scientific results',
        'preparation': preparation_proof, 'checks': checks,
        'actual_seed_plan_bindings': input_plans,
        'execution_code_sha256': {p.name: c.sha(p) for p in c.HERE.glob('*.py')}}
    c.write(c.HERE / 'CPU_VALIDATION.json', result)
    print(json.dumps({'status': result['status'], 'checks': len(checks), 'science_imports': False, 'gpu_calls': False}))

if __name__ == '__main__':
    fixtures()
