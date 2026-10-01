"""DAC-only scientific binding over explicitly inherited generic training bookkeeping.

All scientific imports are deferred. No model, tensor, image or GPU is loaded by
importing this module. The entry requires a separately admitted session.
"""
from contextlib import contextmanager
import json
import math
from pathlib import Path
import sys
from common_runtime import HERE, TrainRun, sha_file, write_json

SCIENTIFIC_SOURCE = HERE / 'scientific_source'
REQUIRED = {'views': 2, 'nclasses': 701, 'block': 2, 'triplet_loss': 0.3,
    'resnet': False, 'handcraft_model': True, 'epochs': 1, 'batch_size': 24,
    'img_size': 384, 'mixed_precision': True, 'custom_sampling': True,
    'weight_infonce': 1.0, 'weight_cls': 0.1, 'weight_dsa': 0.6,
    'lr': 0.001, 'warmup_epochs': 0.1, 'scheduler': 'cosine',
    'clip_grad': 100.0, 'label_smoothing': 0.1, 'grad_checkpointing': False}

def validate_model_schema(state):
    expected = json.loads((HERE / 'DAC_EXPECTED_MODEL_SCHEMA.json').read_text(encoding='utf-8'))['tensors']
    if len(state) != 402 or set(state) != set(expected):
        raise RuntimeError('DAC requires its exact 402-key model; CAMP state or altered classifier heads are not admissible')
    bad = [key for key, tensor in state.items() if list(tensor.shape) != expected[key]['shape'] or str(tensor.dtype) != expected[key]['dtype']]
    if bad:
        raise RuntimeError('DAC model shape/dtype mismatch: ' + repr(bad))
    return {'tensor_count': 402, 'key_shape_dtype_match': True, 'schema_sha256': sha_file(HERE / 'DAC_EXPECTED_MODEL_SCHEMA.json')}

def verify_scientific_source():
    pin = json.loads((HERE / 'SOURCE_PIN.json').read_text(encoding='utf-8'))
    official = Path(pin['official_source_directory'])
    for row in pin['files']:
        if sha_file(official / row['path']) != row['sha256']:
            raise RuntimeError('Official DAC source changed: ' + row['path'])
    manifest = json.loads((HERE / 'SCIENTIFIC_SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    for row in manifest['files']:
        if sha_file(SCIENTIFIC_SOURCE / row['path']) != row['derived_sha256']:
            raise RuntimeError('DAC private training source changed: ' + row['path'])
    for name, module in list(sys.modules.items()):
        if name == 'sample4geo' or name.startswith('sample4geo.'):
            paths = ([module.__file__] if getattr(module, '__file__', None) else []) + list(getattr(module, '__path__', []))
            if not paths or any(not Path(path).resolve().is_relative_to(SCIENTIFIC_SOURCE) for path in paths):
                raise RuntimeError('Another model family is already imported under sample4geo: ' + name)
    return manifest

class DACTrainRun(TrainRun):
    def __init__(self, plan, plan_path, profile_path):
        if plan.get('method') != 'DAC' or Path(plan['source_directory']).resolve() != SCIENTIFIC_SOURCE.resolve():
            raise RuntimeError('This adapter only constructs the fixed private DAC source')
        if plan.get('seed') not in (1, 2, 3):
            raise RuntimeError('Only the three declared University seeds are supported')
        super().__init__(plan, plan_path, profile_path)

    def configure(self, config):
        super().configure(config)
        for key, expected in REQUIRED.items():
            if getattr(config, key) != expected:
                raise RuntimeError('Official DAC University configuration changed: ' + key)
        if config.num_workers != 0 or config.device != 'cuda:0' or config.gpu_ids != (0,):
            raise RuntimeError('Only original Windows workers0 and the complete single-GPU AMP loss branch are admitted')

    def make_model(self, config):
        verify_scientific_source()
        # The inherited constructor is generic: it imports model.py, make_model.py
        # and ConvNeXt from self.source, which is required above to be DAC's private
        # source. It strictly loads all 344 original Meta backbone keys. No CAMP
        # scientific model, learned weight or 395-key schema enters this call.
        model = super().make_model(config)
        proof = validate_model_schema(model.state_dict())
        import torch
        proof.update(method='DAC', model_source=str(SCIENTIFIC_SOURCE),
            initialization='Original Meta IN22k-to-IN1k backbone; DAC heads use original constructor initialization',
            author_trained_weights_loaded=False,
            cudnn_actual={'benchmark': bool(torch.backends.cudnn.benchmark),
                'torch_backends_cudnn_benchmark_enabled_original_attribute': getattr(torch.backends, 'cudnn_benchmark_enabled', None),
                'deterministic': bool(torch.backends.cudnn.deterministic),
                'requested_benchmark': config.cudnn_benchmark,
                'adapter_corrected_original_spelling': False})
        write_json(self.output / 'dac_model_binding.json', proof)
        return model

    def observe_optimizer(self, optimizer, model, scaler):
        super().observe_optimizer(optimizer, model, scaler)
        if optimizer.__class__.__name__ != 'AdamW' or scaler is None:
            raise RuntimeError('Expected original AdamW and AMP scaler')
        write_json(self.output / 'dac_optimizer_initialization.json', {
            'class': optimizer.__class__.__module__ + '.' + optimizer.__class__.__name__,
            'resolved_defaults': optimizer.defaults, 'initial_scaler_state': scaler.state_dict(),
            'weight_infonce': 1.0, 'weight_cls': 0.1, 'weight_dsa': 0.6,
            'classification_cross_entropy_label_smoothing': 0.0,
            'infonce_cross_entropy_label_smoothing': 0.1,
            'DSA_definition': 'Official DSA_loss; 1 minus mean cosine similarity after its original concatenation/flattening. No MSE substitution.'})

    def before_epoch(self, epoch, loader):
        if len(loader.dataset.pairs) != 37854:
            raise RuntimeError('Expected all 37854 official University UAV-satellite pairs')
        super().before_epoch(epoch, loader)

    def save_complete(self, namespace):
        import torch
        model, optimizer = namespace['model'], namespace['optimizer']
        validate_model_schema(model.state_dict())
        state = optimizer.state_dict()
        if not state.get('state') or not state.get('param_groups'):
            raise RuntimeError('No actual AdamW state was created')
        steps = []
        for item in state['state'].values():
            if not {'step', 'exp_avg', 'exp_avg_sq'}.issubset(item):
                raise RuntimeError('Incomplete AdamW state')
            step = float(item['step'])
            if not math.isfinite(step) or step <= 0 or step != int(step):
                raise RuntimeError('AdamW state has no positive real updates')
            steps.append(int(step))
            if any(not torch.isfinite(item[key]).all().item() for key in ('exp_avg', 'exp_avg_sq')):
                raise RuntimeError('Nonfinite AdamW moments')
        if max(steps) != self.actual_optimizer_steps:
            raise RuntimeError('Real optimizer hook count differs from saved AdamW step counters')
        scheduler = namespace['scheduler'].state_dict()
        attempts = namespace['train_dataloader'].completed_batches
        if scheduler.get('last_epoch') != attempts:
            raise RuntimeError('Scheduler attempts differ from original consumed batches')
        write_json(self.output / 'dac_training_protocol_evidence.json', {
            'method': 'DAC', 'model_state_count': 402, 'epoch': 1,
            'scheduler_steps_planned_before_shuffle': namespace['train_steps'],
            'warmup_steps_planned_before_shuffle': namespace['warmup_steps'],
            'actual_loader_batches': attempts, 'scheduler_attempts': scheduler['last_epoch'],
            'actual_adamw_steps': self.actual_optimizer_steps, 'amp_skips': attempts - self.actual_optimizer_steps,
            'optimizer_step_min': min(steps), 'optimizer_step_max': max(steps),
            'all_optimizer_moments_finite': True,
            'test_set_read_or_model_selection': False})
        # Saves model/optimizer/scheduler/scaler, Python/NumPy/Torch CPU+CUDA RNG,
        # current/next sample order, original pair order, manifests and actual steps.
        super().save_complete(namespace)
