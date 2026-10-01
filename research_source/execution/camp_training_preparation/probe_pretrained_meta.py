"""CPU/meta-only structure verification; no CUDA, image decode or forward pass.

Run with a suitable existing Python environment and -B. No environment changes.
"""
import importlib
import json
from pathlib import Path
import sys
from camp_train_runtime import HERE, WEIGHT_URL, no_network, sha_file, write_json

def main():
    sys.dont_write_bytecode = True
    pin = json.loads((HERE / 'SOURCE_PIN.json').read_text(encoding='utf-8'))
    source = Path(pin['source_directory'])
    weight = HERE.parent / 'baseline_preparation/compatibility_v3/work/weights/convnext_base_22k_1k_224.pth'
    expected_sha = '8afbd1fa254629e6db80df9822908a83c741bfe98778f58851a15c1639a80453'
    digest = sha_file(weight)
    if digest != expected_sha:
        raise RuntimeError('Fixed local pretrained checkpoint hash changed')
    sys.path.insert(0, str(source))
    import torch
    # All model and checkpoint tensors below are placed on the metadata device.
    with no_network():
        backbone = importlib.import_module('sample4geo.hand_convnext.ConvNext.backbones.model_convnext')
        old_torch = backbone.torch
        class MetaScheduleProxy:
            def __getattr__(self, name):
                return getattr(torch, name)
            def linspace(self, *args, **kwargs):
                kwargs['device'] = 'cpu'
                return torch.linspace(*args, **kwargs)
        backbone.torch = MetaScheduleProxy()
        try:
            with torch.device('meta'):
                model = backbone.ConvNeXt(depths=[3,3,27,3], dims=[128,256,512,1024])
        finally:
            backbone.torch = old_torch
        checkpoint = torch.load(weight, map_location='meta', weights_only=True, mmap=True)
    state, expected = checkpoint['model'], model.state_dict()
    missing = sorted(set(expected)-set(state))
    unexpected = sorted(set(state)-set(expected))
    differences = [{'key': k, 'expected_shape': list(expected[k].shape), 'actual_shape': list(state[k].shape),
                    'expected_dtype': str(expected[k].dtype), 'actual_dtype': str(state[k].dtype)}
                   for k in sorted(set(state)&set(expected))
                   if expected[k].shape != state[k].shape or expected[k].dtype != state[k].dtype]
    report = {'source_commit': pin['commit_sha'], 'python': sys.executable, 'torch': torch.__version__,
              'pretrained': {'path': str(weight), 'bytes': weight.stat().st_size,
                             'sha256': digest, 'source_url': WEIGHT_URL},
              'expected_tensors': len(expected), 'checkpoint_tensors': len(state),
              'missing_keys': missing, 'unexpected_keys': unexpected,
              'shape_or_dtype_mismatch': differences,
              'all_state_tensors_on_meta': all(v.device.type=='meta' for v in state.values()),
              'all_model_parameters_on_meta': all(p.device.type=='meta' for p in model.parameters()),
              'loaded_real_tensor_storage': False, 'forward_pass': False, 'gpu_execution': False,
              'head_keys': [k for k in expected if k.startswith('head.')],
              'full_camp_pos_scale_policy': 'Retain official learnable pos_scale; this probe covers backbone only.',
              'passed': not(missing or unexpected or differences)}
    write_json(HERE / 'PRETRAINED_META_VALIDATION.json', report)
    if not report['passed']:
        raise RuntimeError('Pretrained checkpoint does not strictly match official backbone')
    print(json.dumps({k:report[k] for k in ('expected_tensors','checkpoint_tensors','passed','gpu_execution')}))

if __name__ == '__main__':
    main()
