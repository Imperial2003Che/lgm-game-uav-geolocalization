"""Runtime hooks. Import is lightweight; training functions run only after the gate.

No training loss, tensor transformation, sampling, optimizer, or schedule is defined
here. Those computations remain in the pinned official CAMP modules and entry.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import random
import socket
import sys
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
WEIGHT_URL = 'https://dl.fbaipublicfiles.com/convnext/convnext_base_22k_1k_224.pth'

def sha_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.partial')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temporary, path)

@contextmanager
def no_network():
    def blocked(*args, **kwargs):
        raise RuntimeError('Training uses declared local files; network access is disabled')
    with patch.object(socket.socket, 'connect', blocked), patch.object(socket.socket, 'connect_ex', blocked), patch.object(socket, 'create_connection', blocked):
        yield

class CountedLoader:
    """Observe the original loader; do not create another sampler or generator."""
    def __init__(self, loader, after_batch=None):
        self.loader = loader
        self.dataset = loader.dataset
        self.completed_batches = 0
        self.after_batch = after_batch
    def __len__(self):
        return len(self.loader)
    def __iter__(self):
        for batch in self.loader:
            yield batch
            # A batch is counted only after the official trainer consumed it.
            self.completed_batches += 1
            if self.after_batch is not None:
                self.after_batch(self.completed_batches)

class TrainRun:
    def __init__(self, plan, plan_path, profile_path):
        self.plan = plan
        self.plan_path = Path(plan_path)
        self.profile_path = Path(profile_path)
        self.output = Path(plan['output_directory']).resolve()
        self.train_root = Path(plan['train_root']).resolve()
        self.source = Path(plan['source_directory']).resolve()
        self.weight = Path(plan['pretrained']['path']).resolve()
        self.expected_batches = None
        self.epoch = None
        self.make_model_calls = 0
        self.actual_optimizer_steps = 0
        self.loss_observations = []
        self.previous_actual_steps = 0
        self.amp_skips = 0
        self.optimizer_hook = None
    def configure(self, config):
        # All scientific defaults remain from the pinned official Configuration.
        for key, expected in self.plan['official_configuration_defaults'].items():
            actual = getattr(config, key)
            if isinstance(actual, tuple):
                actual = list(actual)
            if actual != expected:
                raise RuntimeError(f'Official default changed: {key}: {actual!r} != {expected!r}')
        config.seed = self.plan['seed']
        config.device = 'cuda:0'
        config.gpu_ids = (0,)
        config.num_workers = 0  # official Windows default; also keeps access guard/RNG in this process
        config.query_folder_train = str(self.train_root / 'satellite')
        config.gallery_folder_train = str(self.train_root / 'drone')
        config.model_path = str(self.output)
        config.data_folder = str(self.train_root)
        write_json(self.output / 'effective_configuration.json', vars(config))
    def make_model(self, config):
        import torch
        self.make_model_calls += 1
        if self.make_model_calls != 1:
            raise RuntimeError('Exactly one CAMP model construction is allowed')
        module = importlib.import_module('sample4geo.hand_convnext.model')
        factory = importlib.import_module('sample4geo.hand_convnext.ConvNext.make_model')
        backbone = importlib.import_module('sample4geo.hand_convnext.ConvNext.backbones.model_convnext')
        for item in (module, factory, backbone):
            if not Path(item.__file__).resolve().is_relative_to(self.source):
                raise RuntimeError('CAMP import escaped the pinned source')
        def local_factory(name, pretrained=True, **kwargs):
            if name != 'convnext_base' or pretrained is not True or kwargs:
                raise RuntimeError('Unexpected official backbone factory request')
            # Same constructor and initialization order as official convnext_base.
            model = backbone.ConvNeXt(depths=[3, 3, 27, 3], dims=[128, 256, 512, 1024])
            checkpoint = torch.load(self.weight, map_location='cpu', weights_only=True, mmap=True)
            if not isinstance(checkpoint, dict) or 'model' not in checkpoint:
                raise RuntimeError('Expected original Facebook checkpoint with model mapping')
            state = checkpoint['model']
            expected = model.state_dict()
            missing = sorted(set(expected) - set(state))
            extra = sorted(set(state) - set(expected))
            mismatch = [k for k in set(expected) & set(state)
                        if expected[k].shape != state[k].shape or expected[k].dtype != state[k].dtype]
            proof = {'source_url': WEIGHT_URL, 'sha256': self.plan['pretrained']['sha256'],
                     'expected_tensor_count': len(expected), 'loaded_tensor_count': len(state),
                     'missing_keys': missing, 'unexpected_keys': extra, 'shape_dtype_mismatch': mismatch,
                     'key_renaming': 'none', 'ignored_keys': [], 'load_policy': 'strict=True'}
            write_json(self.output / 'pretrained_binding.json', proof)
            if missing or extra or mismatch:
                raise RuntimeError('Pretrained coverage mismatch; no keys may be silently skipped')
            model.load_state_dict(state, strict=True)
            return model
        with patch.object(factory, 'create_model', local_factory):
            model = module.make_model(config)
        return model
    def wrap_loader(self, loader):
        if loader.batch_size != 24 or loader.num_workers != 0 or loader.drop_last:
            raise RuntimeError('Original University DataLoader contract changed')
        if len(loader.dataset.ids) != 701:
            raise RuntimeError('Expected all 701 University training identities')
        self.loader = CountedLoader(loader, self.after_batch)
        return self.loader
    def observe_optimizer(self, optimizer, model, scaler):
        """Observe the real AdamW.step reached by GradScaler; do not replace it."""
        if self.optimizer_hook is not None or scaler is None:
            raise RuntimeError('Expected exactly one original optimizer and enabled AMP scaler')
        self.scaler = scaler
        self.optimizer = optimizer
        def stepped(optimizer, args, kwargs):
            self.actual_optimizer_steps += 1
        self.optimizer_hook = optimizer.register_step_post_hook(stepped)
        candidates = [(name, value) for name, value in model.named_parameters()
                      if name.endswith('convnext.downsample_layers.0.0.weight') and value.requires_grad]
        if len(candidates) != 1:
            raise RuntimeError('Unable to identify the original shared backbone stem weight')
        self.representative_name, self.representative_parameter = candidates[0]
        self.initial_parameter_sha256 = self.parameter_digest(self.representative_parameter)
        write_json(self.output / 'initial_parameter_evidence.json', {
            'name': self.representative_name, 'shape': list(self.representative_parameter.shape),
            'dtype': str(self.representative_parameter.dtype),
            'sha256': self.initial_parameter_sha256,
            'scope': 'representative trainable shared ConvNeXt stem tensor, not whole model'})
    @staticmethod
    def parameter_digest(parameter):
        return hashlib.sha256(parameter.detach().cpu().contiguous().numpy().tobytes()).hexdigest()
    def observe_loss(self, value, n=1):
        value = float(value)
        if not math.isfinite(value):
            # This observes the original loss.item() at its existing AverageMeter
            # call, before its backward pass; no extra loss calculation is added.
            write_json(self.output / 'nonfinite_loss.json', {
                'batch_attempt': len(self.loss_observations) + 1, 'value': repr(value)})
            raise RuntimeError('Official training loss became non-finite')
        self.loss_observations.append(value)
    def after_batch(self, completed_batches):
        if len(self.loss_observations) != completed_batches:
            raise RuntimeError('Expected exactly one official scalar loss observation per batch')
        delta = self.actual_optimizer_steps - self.previous_actual_steps
        if delta not in (0, 1):
            raise RuntimeError('Expected zero or one actual AdamW update per official batch')
        self.amp_skips += int(delta == 0)
        self.previous_actual_steps = self.actual_optimizer_steps
        row = {'epoch': self.epoch, 'batch_attempt': completed_batches,
               'loss': self.loss_observations[-1], 'loss_finite': True,
               'actual_optimizer_steps': self.actual_optimizer_steps,
               'optimizer_updated_this_batch': bool(delta), 'amp_skips': self.amp_skips,
               'scale_after_update': self.scaler.get_scale(),
               'lr_after_scheduler': self.optimizer.param_groups[0]['lr']}
        with open(self.output / 'batch_progress.jsonl', 'a', encoding='utf-8') as stream:
            stream.write(json.dumps(row) + '\n')
    def before_epoch(self, epoch, loader):
        if epoch != 1 or self.epoch is not None:
            raise RuntimeError('This registration permits exactly one complete epoch')
        self.epoch = epoch
        self.expected_batches = len(loader)
        samples = loader.dataset.samples
        if not samples or len(samples) % 24:
            raise RuntimeError('Official custom sampler did not produce complete 24-pair batches')
        for start in range(0, len(samples), 24):
            if len({row[0] for row in samples[start:start + 24]}) != 24:
                raise RuntimeError('Official unique-place batch invariant failed')
        self.epoch_sample_order = [list(row) for row in samples]
        write_json(self.output / 'epoch01_sample_order.json', self.epoch_sample_order)
        write_json(self.output / 'epoch01_sampling.json', {
            'official_pair_count': len(loader.dataset.pairs), 'sample_count': len(samples),
            'excluded_tail_pairs': len(loader.dataset.pairs) - len(samples),
            'expected_batches': self.expected_batches, 'nominal_pairs_per_batch': 24,
            'sample_order_sha256': sha_file(self.output / 'epoch01_sample_order.json')})
    @contextmanager
    def image_boundary(self):
        """Guard Python dataset directory scans and native OpenCV image reads."""
        import cv2
        import numpy as np
        import sample4geo.dataset.university as dataset
        original_get_data, original_imread = dataset.get_data, cv2.imread
        def train_path(path):
            resolved = Path(path).resolve()
            if not resolved.is_relative_to(self.train_root):
                raise RuntimeError(f'Dataset access outside declared train root: {resolved}')
            return resolved
        def guarded_get_data(path):
            train_path(path)
            return original_get_data(path)
        def guarded_imread(filename, *args, **kwargs):
            resolved = train_path(filename)
            # Measured Windows Unicode failure in original cv2.imread; only the
            # byte-reading path changes. OpenCV performs the same encoded-image decode.
            if len(args) > 1 or set(kwargs) - {'flags'} or (args and 'flags' in kwargs):
                raise RuntimeError('Unexpected official cv2.imread signature')
            flags = args[0] if args else kwargs.get('flags', cv2.IMREAD_COLOR)
            encoded = np.frombuffer(resolved.read_bytes(), dtype=np.uint8)
            decoded = cv2.imdecode(encoded, flags)
            if decoded is None:
                raise RuntimeError(f'OpenCV failed to decode declared training image: {resolved}')
            return decoded
        with patch.object(dataset, 'get_data', guarded_get_data), patch.object(cv2, 'imread', guarded_imread):
            yield
    @contextmanager
    def training_observers(self):
        """Observe the existing AverageMeter.update(loss.item()), preserving it."""
        import sample4geo.trainer as trainer
        original = trainer.AverageMeter
        run = self
        class ObservedAverageMeter(original):
            def update(self, val, n=1):
                run.observe_loss(val, n)
                return super().update(val)
        with patch.object(trainer, 'AverageMeter', ObservedAverageMeter):
            yield
    def save_complete(self, namespace):
        import numpy as np
        import torch
        loader = namespace['train_dataloader']
        if self.epoch != 1 or loader.completed_batches != self.expected_batches:
            raise RuntimeError('Cannot mark an incomplete epoch complete')
        if self.actual_optimizer_steps <= 0:
            raise RuntimeError('AMP skipped every AdamW update; this is not a trained checkpoint')
        if not math.isfinite(float(namespace['train_loss'])):
            raise RuntimeError('Non-finite epoch training loss')
        model = namespace['model']
        if hasattr(model, 'module'):
            raise RuntimeError('This resource registration permits one GPU only')
        nonfinite = [name for name, value in model.state_dict().items()
                     if value.is_floating_point() and not torch.isfinite(value).all().item()]
        if nonfinite:
            write_json(self.output / 'nonfinite_model_state.json', {'keys': nonfinite})
            raise RuntimeError('Final model has non-finite floating state')
        final_parameter_sha256 = self.parameter_digest(self.representative_parameter)
        if final_parameter_sha256 == self.initial_parameter_sha256:
            raise RuntimeError('The representative shared stem weight did not change')
        step_evidence = {'attempted_batches': loader.completed_batches,
                         'actual_adamw_steps': self.actual_optimizer_steps, 'amp_skips': self.amp_skips,
                         'epoch_loss': float(namespace['train_loss']),
                         'all_model_floating_state_finite': True,
                         'representative_parameter': self.representative_name,
                         'initial_parameter_sha256': self.initial_parameter_sha256,
                         'final_parameter_sha256': final_parameter_sha256,
                         'representative_parameter_changed': True,
                         'final_scaler_state': self.scaler.state_dict()}
        write_json(self.output / 'training_evidence.json', step_evidence)
        numpy_rng = np.random.get_state()
        numpy_state = {'bit_generator': numpy_rng[0], 'keys': numpy_rng[1].tolist(),
                       'pos': numpy_rng[2], 'has_gauss': numpy_rng[3], 'cached_gaussian': numpy_rng[4]}
        checkpoint = {
            'schema_version': 1, 'epoch_completed': 1, 'next_epoch': 2,
            'global_step': self.actual_optimizer_steps,
            'attempted_batches': loader.completed_batches,
            'training_evidence': step_evidence,
            'model': model.state_dict(), 'optimizer': namespace['optimizer'].state_dict(),
            'scheduler': namespace['scheduler'].state_dict() if namespace['scheduler'] else None,
            'scaler': namespace['scaler'].state_dict() if namespace['scaler'] else None,
            'rng': {'python': random.getstate(), 'numpy': numpy_state,
                    'torch_cpu': torch.get_rng_state(), 'torch_cuda': torch.cuda.get_rng_state_all()},
            'sampler': {'samples_for_next_epoch': [list(row) for row in loader.dataset.samples],
                        'pairs': [list(row) for row in loader.dataset.pairs],
                        'shuffle_batch_size': loader.dataset.shuffle_batch_size},
            'configuration': vars(namespace['config']),
            'scheduler_total_steps_before_initial_shuffle': namespace['train_steps'],
            'warmup_steps': namespace['warmup_steps'],
            'plan_sha256': sha_file(self.plan_path),
            'profile_sha256': sha_file(self.profile_path),
            'manifests': {name: sha_file(self.output / name) for name in
                          ('code_manifest.json','data_manifest.json','environment_manifest.json',
                           'runtime_environment.json','serial_release_gate.json')},
            'recovery_scope': 'epoch boundary; fixed one-epoch run is finished; no partial-epoch claim',
        }
        for name, content in [('checkpoint_complete.pth', checkpoint), ('weights_end.pth', model.state_dict())]:
            temporary = self.output / (name + '.partial')
            torch.save(content, temporary)
            os.replace(temporary, self.output / name)
        write_json(self.output / 'checkpoint_manifest.json', {
            name: {'sha256': sha_file(self.output / name), 'bytes': (self.output / name).stat().st_size}
            for name in ('checkpoint_complete.pth','weights_end.pth')})
        write_json(self.output / 'status.json', {'status': 'completed', 'epoch_completed': 1,
            'optimizer_step_attempts': loader.completed_batches, 'actual_adamw_steps': self.actual_optimizer_steps,
            'amp_skips': self.amp_skips, 'selection': 'fixed final epoch',
            'test_data_read': False, 'ended_utc': datetime.now(timezone.utc).isoformat()})

def restore_epoch_boundary(checkpoint, model, optimizer, scheduler, scaler, dataset):
    """Restore complete state into identically constructed objects; not a launch API.

    The declared one-epoch experiment has already ended. This helper supports state
    verification/future separately registered continuation, never a second epoch
    silently added to the current experiment.
    """
    import numpy as np
    import torch
    if checkpoint['epoch_completed'] != 1 or checkpoint['next_epoch'] != 2:
        raise RuntimeError('Unsupported recovery boundary')
    if [list(row) for row in dataset.pairs] != checkpoint['sampler']['pairs']:
        raise RuntimeError('Dataset pair order changed')
    model.load_state_dict(checkpoint['model'], strict=True)
    optimizer.load_state_dict(checkpoint['optimizer'])
    if (scheduler is None) != (checkpoint['scheduler'] is None) or (scaler is None) != (checkpoint['scaler'] is None):
        raise RuntimeError('Scheduler / scaler identity changed')
    if scheduler is not None:
        scheduler.load_state_dict(checkpoint['scheduler'])
    if scaler is not None:
        scaler.load_state_dict(checkpoint['scaler'])
    dataset.samples = [tuple(row) for row in checkpoint['sampler']['samples_for_next_epoch']]
    random.setstate(checkpoint['rng']['python'])
    nr = checkpoint['rng']['numpy']
    np.random.set_state((nr['bit_generator'], np.array(nr['keys'], dtype=np.uint32), nr['pos'], nr['has_gauss'], nr['cached_gaussian']))
    torch.set_rng_state(checkpoint['rng']['torch_cpu'])
    torch.cuda.set_rng_state_all(checkpoint['rng']['torch_cuda'])
