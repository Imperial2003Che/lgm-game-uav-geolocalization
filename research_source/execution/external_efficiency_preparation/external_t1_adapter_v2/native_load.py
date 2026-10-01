"""Real native model loader for a future isolated, released T6 worker.

This module is not a launcher. The caller must enforce the reviewed whole-queue
completion/PID/resource/release contract before calling load_native_slot. This
adapter independently verifies completed T1 evidence, native environment,
source/model identity, strict checkpoint loading and actual precision flags.
"""
from __future__ import annotations
import importlib
import importlib.util
import inspect
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import bindings as b
from native_ops import NativeContext, precision_state

_LOADED_SLOT = None

def load_components():
    k = b.common()
    path = b.COMPONENTS / 'measurement_components.py'
    k.require(k.sha(path) == b.COMPONENT_SHA, 'Frozen measurement components changed')
    spec = importlib.util.spec_from_file_location('external_t1_corrected_components', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

def evaluator_arguments(binding, official):
    """Reconstruct original arguments from the completed evaluation's actual config."""
    cfg, row = binding['evaluation_config'], binding['row']
    args = SimpleNamespace(config_id=row['config_id'], seed=row['seed'],
        source_root=Path(cfg['source_root']), patch_manifest=Path(cfg['patch_manifest_path']),
        fit_dir=Path(binding['fit_dir']), all_fits_gate=Path(binding['all_fits_gate']),
        test_inventory_gate=Path(binding['test_inventory_gate']),
        test_root=Path(cfg['dataset_roots']['university1652_test']),
        sues_root=Path(cfg['dataset_roots']['sues200']), sues_manifest=Path(cfg['sues_manifest']['path']))
    if row['framework'] == 'qdfl':
        for weight_id, (argument, variable, label) in official.WEIGHT_ARGUMENTS.items():
            setattr(args, argument, Path(cfg['initialization_files'][weight_id]['path']))
    else:
        args.convnext_weight = Path(cfg['initialization_file']['path'])
    return args

def load_native_slot(binding, *, device_index=0):
    """Actually loads native model/weights; never called during this preparation.

    Separate fresh process per fit is mandatory, including QDFL seeds 1/2/3.
    No model or timing from one seed is copied to another slot.
    """
    global _LOADED_SLOT
    k = b.common()
    k.require(_LOADED_SLOT is None, 'Each fit requires a fresh isolated process')
    k.require(type(device_index) is int and device_index >= 0, 'Invalid explicit CUDA index')
    b.verify_binding(binding)
    row = binding['row']
    metadata = b.verify_current_environment(row['framework'])
    forbidden_prefixes = ('external_baselines', 'plModules', 'model', 'models', 'utils')
    k.require(not [name for name in sys.modules if name.split('.')[0] in forbidden_prefixes],
              'Native model namespace already exists; use a fresh worker')
    k.gpu_idle()
    # Reserve the process even if a later import/load fails; no in-process retry.
    _LOADED_SLOT = row['run_id']
    os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.environ['XFORMERS_DISABLED'] = '1'
    if str(b.DELIVERY) not in sys.path:
        sys.path.insert(0, str(b.DELIVERY))
    # Real scientific imports are confined to this explicit future entry point.
    import numpy as np
    import torch
    import torchvision
    from PIL import Image
    from external_baselines import run_transactions_t1_matrix as matrix
    family_module = 'qdfl_official_evaluation' if row['framework'] == 'qdfl' else 'mccg_official_evaluation'
    official = importlib.import_module('external_baselines.' + family_module)
    k.require(Path(matrix.__file__).resolve() == b.EXT / 'run_transactions_t1_matrix.py', 'Imported wrong frozen matrix')
    k.require(Path(official.__file__).resolve() == b.EXT / (family_module + '.py'), 'Imported wrong frozen evaluator')
    site = Path(sys.executable).parent.parent / 'Lib' / 'site-packages'
    for module in (np, torch, torchvision, Image):
        k.require(Path(module.__file__).resolve().is_relative_to(site.resolve()), 'Foreign scientific package imported')
    k.require(not torch.cuda.is_initialized(), 'CUDA initialized before native setup; use a fresh worker')
    k.require(not torch.is_autocast_enabled('cuda') and not torch.is_autocast_enabled('cpu'), 'Inherited AMP is forbidden')
    # This exact registered code recomputes completed per-query arrays and checks
    # the full official tasks before the selected model is loaded for efficiency.
    validated = []
    for registered in b.slots():
        fit = b.RUNS / 'fits' / registered['run_id']
        evaluation = b.RUNS / 'evaluations' / registered['run_id']
        fit_result = matrix.validate_existing_fit(registered, fit)
        evaluation_result = matrix.validate_existing_evaluation(registered, evaluation)
        validated.append({'run_id': registered['run_id'], 'checkpoint_sha256': fit_result['checkpoint_sha256'],
                          'evaluation_manifest': k.record(evaluation / 'evaluation_manifest.json'),
                          'task_names': evaluation_result['task_names']})
    args = evaluator_arguments(binding, official)
    source_lock = k.read(b.EXT / 'transactions_environment_lock.json')['compatibility_revision']['source_manifests'][row['framework']]
    k.require(args.source_root.resolve() == Path(source_lock['source_root']).resolve() and
              args.patch_manifest.resolve() == Path(source_lock['manifest_path']).resolve() and
              k.sha(args.patch_manifest) == source_lock['manifest_sha256'], 'Native model source differs from registered T1 source')
    gate = official.validate_fit_gate(args)
    k.require(k.record(gate['checkpoint_path']) == binding['checkpoint'], 'Actual validated selected checkpoint differs')
    cfg = binding['evaluation_config']
    k.require(cfg['execution']['amp'] is False and cfg['execution']['batch_size'] == b.BATCHES[row['config_id']],
              'Completed native evaluation precision/batch differs')
    k.require(tuple(cfg['protocol']['test_size']) == b.SIZES[row['config_id']] and
              cfg['protocol']['horizontal_flip_augmentation'] is True, 'Completed native image/flip protocol differs')
    device = official.set_determinism(row['seed'], device_index)
    k.require(device.index == device_index and torch.cuda.current_device() == device_index, 'CUDA device mismatch')
    before_precision = torch.get_float32_matmul_precision()
    k.require(before_precision == 'highest', 'Fresh native process default precision was altered')
    if row['framework'] == 'qdfl':
        for variable, value in gate['weight_environment'].items():
            os.environ[variable] = value
        model = official.load_model(gate, device)
        transform = official.build_transform(gate['test_size'])
        model_file = args.source_root / 'plModules' / 'U1652_baseline.py'
        expected_class = 'U1652_model'
        expected_precision = 'medium'
    else:
        os.environ['LGM_MCCG_CONVNEXT_T_22K_WEIGHTS'] = str(args.convnext_weight.resolve())
        model = official.load_model(args.source_root, gate['checkpoint_path'], device)
        transform = official.build_transform()
        model_file = args.source_root / 'models' / 'model.py'
        expected_class = 'two_view_net'
        expected_precision = 'highest'
        k.require(hasattr(model, 'model_1') and not hasattr(model, 'model_2'), 'MCCG shared-model structure differs')
    k.require(type(model).__name__ == expected_class and Path(inspect.getfile(type(model))).resolve() == model_file.resolve(),
              'Actual loaded model class/source identity differs')
    k.require(torch.get_float32_matmul_precision() == expected_precision, 'Native matmul precision side effect changed')
    k.require(not model.training and all(p.dtype == torch.float32 for p in model.parameters()),
              'Native model must remain eval with FP32 parameters')
    loaded_source = []
    for name, module in tuple(sys.modules.items()):
        if name.split('.')[0] in ('plModules', 'model', 'models', 'utils'):
            filename = getattr(module, '__file__', None)
            if filename:
                path = Path(filename).resolve()
                k.require(path.is_relative_to(args.source_root.resolve()), 'Native namespace resolved outside pinned source')
                loaded_source.append(k.record(path))
    components = load_components()
    runtime = components.Runtime(torch, np, None, None, device)
    identity = {'run_id': row['run_id'], 'actual_model_class': type(model).__module__ + '.' + type(model).__name__,
        'actual_model_object_id': id(model), 'actual_model_source': k.record(model_file),
        'actual_loaded_native_sources': loaded_source, 'native_environment_metadata': metadata,
        'actual_library_files': {x.__name__: str(Path(x.__file__).resolve()) for x in (np, torch, torchvision, Image)},
        'original_official_runtime': official.runtime_environment(device), 'strict_checkpoint_load': True,
        'checkpoint': binding['checkpoint'], 'whole_seven_fit_and_70_task_validation': validated,
        'float32_matmul_precision_before_model_import': before_precision,
        'float32_matmul_precision_after_model_import': torch.get_float32_matmul_precision(),
        'test_size': b.SIZES[row['config_id']], 'native_amp': False,
        'normalization': 'original evaluator function; no substituted uniform normalization',
        'model_setup_is_outside_online_timing': True,
        'caller_still_owns_release_pid_resource_and_output_contract': True, '_PIL_Image_module': Image}
    context = NativeContext(runtime, components, official, model, transform, binding, identity)
    identity['native_precision_after_load'] = precision_state(context)
    return context
