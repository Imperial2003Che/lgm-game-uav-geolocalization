"""Bounded CPU validation: no torch import, images, checkpoint loading or CUDA."""
import argparse
import ast
import dataclasses
from datetime import datetime, timezone
import importlib.abc
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

class BlockHeavyImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname.split('.')[0] in {'torch','torchvision','cv2','timm','numpy','albumentations','sample4geo'}:
            raise AssertionError('CPU preparation attempted heavy/model import: ' + fullname)
        return None

sys.meta_path.insert(0, BlockHeavyImports())
from camp_train_runtime import HERE, CountedLoader, TrainRun, sha_file, write_json
import prepare_or_train as entry
import serial_release as serial

def canonical(node):
    return ast.dump(node, include_attributes=False)

def main():
    checks = {}
    pin = json.loads((HERE / 'SOURCE_PIN.json').read_text(encoding='utf-8'))
    source = Path(pin['source_directory'])
    original = ast.parse((source / 'train_university.py').read_text(encoding='utf-8'))
    adapted = ast.parse((HERE / 'train_university_train_only.py').read_text(encoding='utf-8'))
    checks['official_files_byte_identical'] = len(entry.code_manifest()['official'])
    original_calls = [canonical(n) for n in ast.walk(original) if isinstance(n, ast.Call)
                      and isinstance(n.func, ast.Name) and n.func.id == 'train']
    new_calls = [canonical(n) for n in ast.walk(adapted) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == 'train']
    assert original_calls == new_calls and len(new_calls) == 1
    checks['official_train_call_ast_identical'] = True
    for name in ('loss_fn','loss_fn1','loss_fn2','loss_fn3','loss_fn4','loss_fn5',
                 'loss_fn6','loss_fn7','loss_fn8','loss_functions',
                 'scaler','train_dataset','train_steps_per','train_steps','warmup_steps'):
        def assignments(tree):
            return [canonical(n) for n in ast.walk(tree) if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
        before, after = assignments(original), assignments(adapted)
        assert before and before == after, name
        if before:
            checks['ast_identical_' + name] = len(before)
    # Every active optimizer/scheduler construction remains byte-equivalent as AST.
    for constructor in ('DataLoader','get_transforms','AdamW','get_cosine_schedule_with_warmup',
                        'get_polynomial_decay_schedule_with_warmup','get_constant_schedule_with_warmup'):
        def calls(tree):
            return [canonical(n) for n in ast.walk(tree) if isinstance(n, ast.Call)
                    and ast.unparse(n.func).split('.')[-1] == constructor]
        if constructor == 'DataLoader':
            # Original entry has two additional test loaders, intentionally removed.
            assert len(calls(adapted)) == 1 and calls(adapted)[0] in calls(original)
        else:
            assert calls(original) == calls(adapted), constructor
        checks['ast_identical_' + constructor] = len(calls(adapted))
    names = {n.id for n in ast.walk(adapted) if isinstance(n, ast.Name)}
    attrs = {n.attr for n in ast.walk(adapted) if isinstance(n, ast.Attribute)}
    forbidden = {'evaluate','U1652DatasetEval','query_dataset_test','query_dataloader_test',
                 'gallery_dataset_test','gallery_dataloader_test','best_score','zero_shot',
                 'checkpoint_start','only_test','TimmModel','Logger'}
    assert not forbidden.intersection(names | attrs), forbidden.intersection(names | attrs)
    checks['test_and_best_selection_nodes_removed'] = True
    cls = next(n for n in adapted.body if isinstance(n, ast.ClassDef) and n.name == 'Configuration')
    mini = ast.Module(body=[cls], type_ignores=[])
    scope = {'argparse': argparse, 'dataclass': dataclasses.dataclass, 'os': os}
    exec(compile(mini, '<configuration-only>', 'exec'), scope)
    cfg = scope['Configuration']()
    values = json.loads(json.dumps(vars(cfg)))
    assert values == entry.configuration_defaults()
    for name, value in {'epochs':1, 'batch_size':24, 'img_size':384, 'lr':0.001,
                        'warmup_epochs':0.1, 'mixed_precision':True, 'num_workers':0,
                        'custom_sampling':True, 'if_learn_ECE_weights':True,
                        'if_use_multiply_1':True, 'only_fine':True}.items():
        assert values[name] == value, name
    checks['configuration_constructed_without_torch'] = values
    class Loader:
        dataset = SimpleNamespace()
        def __len__(self): return 3
        def __iter__(self): return iter(('a','b','c'))
    wrapper = CountedLoader(Loader())
    assert list(wrapper) == ['a','b','c'] and wrapper.completed_batches == 3 and len(wrapper) == 3
    interrupted = CountedLoader(Loader())
    cursor = iter(interrupted)
    assert next(cursor) == 'a' and interrupted.completed_batches == 0
    assert next(cursor) == 'b' and interrupted.completed_batches == 1
    checks['loader_instrumentation_retains_order_and_counts_only_consumed_batches'] = True
    # Fail a deliberately invalid gate before ANY torch/model import; retain failure files.
    with tempfile.TemporaryDirectory(prefix='camp_cpu_gate_', dir=HERE) as directory:
        temp = Path(directory)
        plan_path, profile_path = temp/'plan.json', temp/'profile.json'
        write_json(plan_path, {'output_directory': str(temp/'failed_run')})
        write_json(profile_path, {'status':'unmeasured'})
        try:
            entry.train(SimpleNamespace(plan=str(plan_path), profile=str(profile_path),
                                        profile_sha256=sha_file(profile_path)))
        except RuntimeError as error:
            assert 'Resource gate failed: status' in str(error)
        else:
            raise AssertionError('Missing resource gate unexpectedly passed')
        failed = temp/'failed_run'
        assert all((failed/n).is_file() for n in ('failure.log','stdout.log','stderr.log','status.json'))
        assert json.loads((failed/'status.json').read_text(encoding='utf-8'))['status'] == 'failed'
    checks['invalid_resource_gate_fails_closed_with_logs_before_torch_import'] = True
    with tempfile.TemporaryDirectory(prefix='camp_cpu_observer_', dir=HERE) as directory:
        temp = Path(directory)
        run = TrainRun({'output_directory':str(temp), 'train_root':str(temp/'train'),
                        'source_directory':str(source), 'pretrained':{'path':str(temp/'init.pth')}},
                       temp/'plan.json', temp/'profile.json')
        run.epoch = 1
        run.scaler = SimpleNamespace(get_scale=lambda:512.0)
        run.optimizer = SimpleNamespace(param_groups=[{'lr':0.001}])
        run.observe_loss(2.5)
        run.after_batch(1)  # model the permitted first-batch AMP skip
        run.actual_optimizer_steps = 1
        run.observe_loss(2.0)
        run.after_batch(2)
        events = [json.loads(s) for s in (temp/'batch_progress.jsonl').read_text().splitlines()]
        assert events[0]['amp_skips']==1 and not events[0]['optimizer_updated_this_batch']
        assert events[1]['actual_optimizer_steps']==1 and events[1]['optimizer_updated_this_batch']
        try:
            run.observe_loss(float('nan'))
        except RuntimeError:
            assert (temp/'nonfinite_loss.json').is_file()
        else:
            raise AssertionError('Non-finite loss was accepted')
    checks['batch_observer_separates_amp_skip_from_update_and_rejects_nonfinite_loss'] = True
    runtime_ast = ast.parse((HERE/'camp_train_runtime.py').read_text(encoding='utf-8'))
    hook_calls = [n for n in ast.walk(runtime_ast) if isinstance(n,ast.Call)
                  and isinstance(n.func,ast.Attribute) and n.func.attr=='register_step_post_hook']
    assert len(hook_calls)==1
    save = next(n for n in ast.walk(runtime_ast) if isinstance(n,ast.FunctionDef) and n.name=='save_complete')
    saved_text = ast.unparse(save)
    assert 'self.actual_optimizer_steps <= 0' in saved_text
    assert 'torch.isfinite(value).all().item()' in saved_text
    assert 'final_parameter_sha256 == self.initial_parameter_sha256' in saved_text
    checks['save_requires_actual_update_finite_model_and_changed_representative_parameter'] = True
    with tempfile.TemporaryDirectory(prefix='camp_cpu_release_', dir=HERE) as directory:
        temp=Path(directory)
        write_json(temp/'plan.json', {'fixture':'CPU test only'})
        write_json(temp/'extension_plan.json', {'fixture':'CPU test only'})
        write_json(temp/'release.json', {'schema':'camp-university-training-release.v1','allow_cuda':True,
            'training_plan_sha256':sha_file(temp/'plan.json'),
            'preceding_extension_plan_sha256':sha_file(temp/'extension_plan.json')})
        write_json(temp/'status.json', {'status':'running','controller_pid':1001})
        write_json(temp/'pipeline_status.json', {'status':'ready_for_extension_preparation',
            'jobs':[{'id':i,'status':'completed','exit_code':0} for i in serial.PIPELINE_IDS]})
        write_json(temp/'extension_status.json', {'status':'registered_extensions_finished_review_pending',
            'plan_sha256':sha_file(temp/'extension_plan.json'),
            'jobs':[{'id':i,'status':'completed','exit_code':0} for i in serial.EXTENSION_IDS]})
        with patch.object(serial,'EXECUTION',temp), patch.object(serial,'alive',return_value=False), \
             patch.object(serial.subprocess,'run',side_effect=AssertionError('nvidia-smi must not run before predecessor completion')):
            try:
                serial.serial_release_gate(temp/'plan.json',temp/'release.json')
            except RuntimeError as error:
                assert 'Primary matrix has not completed' in str(error)
            else:
                raise AssertionError('Running primary matrix passed release')
        write_json(temp/'status.json', {'status':'completed','controller_pid':1001,
                                      'last_command':{'pid':1002,'started_utc':'2026-09-14T00:00:00+00:00'}})
        with patch.object(serial,'EXECUTION',temp), patch.object(serial,'alive',return_value=True):
            try:
                serial.serial_release_gate(temp/'plan.json',temp/'release.json')
            except RuntimeError as error:
                assert 'still running' in str(error)
            else:
                raise AssertionError('Active recorded owner passed release')
        with patch.object(serial,'EXECUTION',temp), patch.object(serial,'alive',return_value=False), \
             patch.object(serial.subprocess,'run',return_value=SimpleNamespace(stdout='9999, python.exe\n')):
            try:
                serial.serial_release_gate(temp/'plan.json',temp/'release.json')
            except RuntimeError as error:
                assert 'Another Python GPU' in str(error)
            else:
                raise AssertionError('Other Python compute process passed release')
        assert set(serial.owners({'controller_pid':1,'commands':[{'pid':2,'started_utc':'s'}]}))=={(1,None),(2,'s')}
    checks['serial_release_rejects_incomplete_predecessor_active_nested_owner_and_python_compute'] = True
    checks['resource_and_release_tests_use_mocks_not_nvidia_smi_or_cuda'] = True
    checks['torch_imported'] = 'torch' in sys.modules
    assert not checks['torch_imported']
    checks['gpu_execution'] = False
    checks['limitations'] = ['No model construction, pretrained loading, training sample decode or optimizer step executed.',
                             'Checkpoint tensor round-trip / RNG continuation remains a later registered runtime check.',
                             'Real full-batch24 resource profile and pinned environment required before training.']
    checks['checked_utc'] = datetime.now(timezone.utc).isoformat()
    write_json(HERE/'CPU_VALIDATION.json', checks)
    print(json.dumps({'checks': len(checks), 'passed': True, 'gpu_execution': False, 'torch_imported': False}))

if __name__ == '__main__':
    main()
