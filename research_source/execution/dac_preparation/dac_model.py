"""Construct the fixed official DAC model without any pretrained downloads.

No CAMP configuration or schema adaptation is used. The process-local backbone
factory calls DAC's own ConvNeXt class with the exact official Base arguments.
"""
from contextlib import contextmanager
import hashlib
import importlib
import json
from pathlib import Path
import socket
import sys
from types import SimpleNamespace
from unittest.mock import patch

SOURCE_ROOT = Path(__file__).resolve().parents[2] / 'literature/official_repos/snapshots/SummerpanKing__DAC__5612a79c3928'
SOURCE_MANIFEST = Path(__file__).resolve().parent / 'SOURCE_SHA256.json'
MODEL_CONFIG = dict(views=2, nclasses=701, block=2, triplet_loss=0.3, resnet=False)
BACKBONE_CONFIG = dict(depths=[3, 3, 27, 3], dims=[128, 256, 512, 1024])


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_source(source_root=SOURCE_ROOT):
    """Verify every audited source file before importing any official code."""
    source_root = Path(source_root).resolve()
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding='utf-8'))
    if source_root != Path(manifest['repository']).resolve():
        raise RuntimeError('DAC source must be the previously audited fixed snapshot')
    checked = {}
    for relative, expected in manifest['files'].items():
        path = (source_root / relative).resolve()
        if not path.is_relative_to(source_root) or not path.is_file() or _sha(path) != expected:
            raise RuntimeError(f'DAC fixed source changed: {relative}')
        checked[relative] = expected
    return checked


@contextmanager
def no_network():
    """Fail before a socket connection or a torch.hub download can start."""
    import torch
    attempts = []
    def blocked(*args, **kwargs):
        attempts.append('network_or_torch_hub_call_blocked')
        raise RuntimeError('DAC local model construction permits no network or pretrained download')
    with patch.object(socket.socket, 'connect', blocked), \
         patch.object(socket.socket, 'connect_ex', blocked), \
         patch.object(socket, 'create_connection', blocked), \
         patch.object(torch.hub, 'load_state_dict_from_url', blocked), \
         patch.object(torch.hub, 'download_url_to_file', blocked):
        yield attempts


def build_dac_model(source_root=SOURCE_ROOT, device='cpu'):
    """Build DAC's exact University model schema, without a weight download.

    The default CPU mode is for a later authorized loader. This task validates
    only device='meta'. No parameter is removed, renamed, invented or converted
    to a plain constant. The factory does not itself load any checkpoint.
    """
    import torch
    source_root = Path(source_root).resolve()
    checked = verify_source(source_root)
    target_device = torch.device(device)
    if target_device.type not in ('cpu', 'meta'):
        raise ValueError('Build on CPU or meta; GPU execution is a separate caller responsibility')
    for name, module in list(sys.modules.items()):
        if name != 'sample4geo' and not name.startswith('sample4geo.'):
            continue
        module_file = getattr(module, '__file__', None)
        module_paths = list(getattr(module, '__path__', []))
        paths = ([module_file] if module_file else []) + module_paths
        if not paths or not all(Path(item).resolve().is_relative_to(source_root) for item in paths):
            raise RuntimeError(f'Another sample4geo source is already imported: {name}')
    old_path = list(sys.path)
    old_bytecode = sys.dont_write_bytecode
    module_provenance = {}
    factory_requests = []
    schedule_constants = []
    try:
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(source_root))
        with no_network() as network_attempts:
            module = importlib.import_module('sample4geo.hand_convnext.model')
            factory = importlib.import_module('sample4geo.hand_convnext.ConvNext.make_model')
            backbone = importlib.import_module('sample4geo.hand_convnext.ConvNext.backbones.model_convnext')
            for name, imported in list(sys.modules.items()):
                if not name.startswith('sample4geo.'):
                    continue
                imported_file = getattr(imported, '__file__', None)
                if imported_file:
                    path = Path(imported_file).resolve()
                    if not path.is_relative_to(source_root):
                        raise RuntimeError(f'DAC module resolved outside fixed snapshot: {name}')
                    relative = path.relative_to(source_root).as_posix()
                    if relative not in checked or _sha(path) != checked[relative]:
                        raise RuntimeError(f'Unaudited imported DAC module: {name}')
                    module_provenance[name] = dict(path=str(path), sha256=checked[relative])
            class ScheduleTorchProxy:
                def __getattr__(self, name):
                    return getattr(torch, name)
                def linspace(self, *args, **kwargs):
                    # DAC's ConvNeXt constructor calls .item() for 36 drop-path
                    # constants. These are not parameters or checkpoint state.
                    if args != (0, 0.0, 36) or kwargs:
                        raise RuntimeError('Unexpected official DAC drop-path schedule request')
                    values = torch.linspace(*args, device='cpu')
                    schedule_constants.extend(values.tolist())
                    return values
            def checkpoint_only_factory(name, pretrained=True, **kwargs):
                if name != 'convnext_base' or pretrained is not True or kwargs:
                    raise RuntimeError('Unexpected DAC backbone factory request')
                factory_requests.append({'name':name, 'original_pretrained_argument':pretrained,
                                         'construction':'official DAC ConvNeXt class, no checkpoint loading',
                                         'config':BACKBONE_CONFIG})
                return backbone.ConvNeXt(**BACKBONE_CONFIG)
            original_factory = factory.create_model
            original_torch = backbone.torch
            factory.create_model = checkpoint_only_factory
            if target_device.type == 'meta':
                backbone.torch = ScheduleTorchProxy()
            try:
                with torch.device(target_device):
                    model = module.make_model(SimpleNamespace(**MODEL_CONFIG))
                model.eval()
            finally:
                factory.create_model = original_factory
                backbone.torch = original_torch
            if len(factory_requests) != 1 or network_attempts:
                raise RuntimeError('Unexpected model construction or network attempt')
    finally:
        sys.path[:] = old_path
        sys.dont_write_bytecode = old_bytecode
    config = model.get_config()
    if tuple(config['mean']) != (0.485, 0.456, 0.406) or tuple(config['std']) != (0.229, 0.224, 0.225):
        raise RuntimeError('Official DAC model normalization changed')
    state = model.state_dict()
    if any(value.device.type != target_device.type for value in state.values()):
        raise RuntimeError('A model state tensor was created on the wrong device')
    model._dac_construction_proof = {
        'source_root': str(source_root), 'source_sha256': checked,
        'model_config': dict(MODEL_CONFIG), 'backbone_config': BACKBONE_CONFIG,
        'factory_requests': factory_requests, 'imported_modules': module_provenance,
        'device':str(target_device), 'network_attempts': network_attempts,
        'meta_schedule_cpu_constants': schedule_constants,
        'original_factory_restored':factory.create_model is original_factory,
        'original_backbone_torch_restored':backbone.torch is original_torch,
        'schema_adaptation':'none', 'dropped_keys':[], 'renamed_keys':[], 'invented_state_tensors':[],
        'normalization':config,
    }
    return model


def validate_checkpoint_state(model, state):
    """Compare every key, shape and dtype before any strict state assignment."""
    import torch
    if not isinstance(state, dict) or not state or not all(isinstance(k,str) and isinstance(v,torch.Tensor) for k,v in state.items()):
        raise RuntimeError('Expected the official plain tensor state dictionary')
    expected = model.state_dict()
    missing = sorted(set(expected) - set(state))
    unexpected = sorted(set(state) - set(expected))
    differences = [dict(key=key, expected_shape=list(expected[key].shape), actual_shape=list(state[key].shape),
                        expected_dtype=str(expected[key].dtype), actual_dtype=str(state[key].dtype))
                   for key in sorted(set(expected) & set(state))
                   if expected[key].shape != state[key].shape or expected[key].dtype != state[key].dtype]
    if missing or unexpected or differences:
        detail = dict(missing_keys=missing, unexpected_keys=unexpected, shape_or_dtype_mismatches=differences)
        raise RuntimeError('Strict DAC author checkpoint mismatch: ' + json.dumps(detail, ensure_ascii=False))
    return dict(tensor_count=len(state), total_stored_numel=sum(v.numel() for v in state.values()),
                missing_keys=missing, unexpected_keys=unexpected, shape_or_dtype_mismatches=differences,
                key_normalization='none', schema_adaptation='none', model_config=dict(MODEL_CONFIG))
