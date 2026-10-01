"""Read-only validation of the project's own stopped, SHA-preserved checkpoint."""
import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import zipfile

for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
assert Path(sys.executable).resolve() == Path(r'C:\项目\.venvs\lgm-baselines\Scripts\python.exe').resolve()
versions = {key: importlib.metadata.version(key) for key in ('torch', 'torchvision', 'numpy', 'Pillow')}
assert versions == {'torch': '2.11.0+cu126', 'torchvision': '0.26.0+cu126', 'numpy': '2.4.4', 'Pillow': '12.2.0'}
root = Path(__file__).resolve().parent / 'memory_recovery_20260914_1544'
run = root / 'run'
report_path = root / 'checkpoint_verification.json'
assert not report_path.exists(), 'Do not overwrite a verification record.'
read = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()
preserved = read(root / 'backup_manifest.json')
for item in preserved:
    assert sha(Path(item['backup'])) == item['sha256']
history = read(run / 'history.json')
manifest = read(run / 'run_manifest.json')
config = read(run / 'run_config.json')
assert len(history) == 35 and [row['epoch'] for row in history] == list(range(35))
assert manifest['last_completed_epoch'] == 34 and manifest['history_rows'] == 35
assert config['immutable_config']['seed'] == 2

import torch
torch.set_num_threads(1)
assert not torch.cuda.is_initialized()
reports = []
for name in ('last.pt', 'best.pt'):
    path = run / name
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
    # Trusted, locally generated training artifact. Python and NumPy RNG objects
    # are required for exact resume and were preserved before this read.
    state = torch.load(path, map_location='cpu', weights_only=False, mmap=True)
    required = {'model_state', 'optimizer_state', 'scheduler_state', 'scaler_state', 'rng_state', 'immutable_config', 'run_config_sha256', 'history', 'epoch'}
    assert required <= state.keys()
    assert state['epoch'] == 34 and state['history'] == history
    assert state['run_config_sha256'] == manifest['run_config_sha256'] == config['run_config_sha256']
    assert state['immutable_config'] == config['immutable_config']
    assert {'python', 'numpy', 'torch_cpu', 'torch_cuda'} <= state['rng_state'].keys()
    assert len(state['rng_state']['torch_cuda']) == 1
    assert state['rng_state']['torch_cpu'].dtype == torch.uint8
    assert all(tensor.dtype == torch.uint8 for tensor in state['rng_state']['torch_cuda'])
    tensors = []
    def check(value):
        if isinstance(value, torch.Tensor):
            tensors.append(value)
            if value.is_floating_point():
                assert bool(torch.isfinite(value).all())
        elif isinstance(value, dict):
            for item in value.values():
                check(item)
        elif isinstance(value, (tuple, list)):
            for item in value:
                check(item)
    check(state['model_state'])
    check(state['optimizer_state'])
    assert len(state['optimizer_state']['state']) > 0 and state['scaler_state']
    assert state['scheduler_state']['last_epoch'] == 35 * 652
    reports.append({'file': str(path), 'sha256': sha(path), 'epoch_zero_based': 34, 'completed_epochs': 35, 'finite_model_and_optimizer_tensors': len(tensors), 'optimizer_parameter_states': len(state['optimizer_state']['state']), 'scaler_state': state['scaler_state'], 'scheduler_state': state['scheduler_state'], 'config_sha256': state['run_config_sha256'], 'rng_state_fields': list(state['rng_state'])})
    del tensors, state
assert reports[0]['sha256'] == reports[1]['sha256']
assert not torch.cuda.is_initialized()
report = {'status': 'verified_complete_epoch_35', 'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'executable': sys.executable, 'versions': versions, 'cuda_initialized': False, 'reports': reports, 'scope': 'Checkpoint integrity and resume-state presence; no new training or test results.'}
with report_path.open('x', encoding='utf-8') as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
print(json.dumps({'status': report['status'], 'files': len(reports), 'cuda_initialized': False}))
