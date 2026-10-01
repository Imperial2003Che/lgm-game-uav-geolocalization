"""Inspect tensor metadata only; never load author pickle with weights_only=False."""
import hashlib
import importlib.metadata as metadata
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'

HERE = Path(__file__).resolve().parent
CHECKPOINT = HERE.parent / 'latest_author_checkpoints/CAMP_University_author_checkpoint.pth'
EXPECTED = '6bc5b21310c9698588567a52f54c423e9e8f9c7a4473e85e5e462fea1898869b'

def sha256(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()

def main():
    before = sha256(CHECKPOINT)
    if before != EXPECTED:
        raise RuntimeError('Author checkpoint digest differs from verified download')
    import torch
    if torch.cuda.is_initialized():
        raise RuntimeError('CUDA must remain uninitialized')
    torch.set_num_threads(1)
    # Meta and mmap: tensor dimensions and dtypes only, no parameter payload allocation.
    state = torch.load(CHECKPOINT, map_location='meta', weights_only=True, mmap=True)
    if not isinstance(state, dict):
        raise TypeError(f'Unexpected checkpoint container: {type(state).__name__}')
    if not all(isinstance(k, str) and isinstance(v, torch.Tensor) for k, v in state.items()):
        raise TypeError('Expected a direct string-to-tensor state dictionary')
    tensors = [dict(key=k, shape=list(v.shape), dtype=str(v.dtype),
                    device=str(v.device), numel=v.numel(), bytes=v.numel()*v.element_size())
               for k, v in state.items()]
    if not all(x['device'] == 'meta' for x in tensors):
        raise RuntimeError('A tensor was materialized unexpectedly')
    after = sha256(CHECKPOINT)
    if after != before:
        raise RuntimeError('Checkpoint changed while inspecting metadata')
    packages = {}
    for package in ['torch', 'torchvision', 'numpy', 'pillow', 'timm',
                    'opencv-python', 'opencv-python-headless', 'albumentations',
                    'scipy', 'scikit-learn', 'transformers', 'tensorboard']:
        try:
            packages[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            packages[package] = None
    report = dict(status='tensor_metadata_inspected_not_model_evaluated',
                  created_utc=datetime.now(timezone.utc).isoformat(),
                  checkpoint=str(CHECKPOINT), checkpoint_sha256=before,
                  checkpoint_bytes=CHECKPOINT.stat().st_size,
                  code_sha256=sha256(Path(__file__)), python=sys.executable,
                  torch_version=torch.__version__, packages=packages,
                  loader=dict(weights_only=True, map_location='meta', mmap=True),
                  cuda_initialized=torch.cuda.is_initialized(),
                  container=type(state).__name__, tensor_count=len(tensors),
                  total_stored_numel=sum(x['numel'] for x in tensors),
                  total_logical_tensor_bytes=sum(x['bytes'] for x in tensors),
                  dtype_counts=dict(Counter(x['dtype'] for x in tensors)),
                  tensors=tensors)
    target = HERE / 'author_checkpoint_metadata.json'
    if target.exists():
        raise FileExistsError('Preserve earlier inventory; do not overwrite')
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k,v in report.items() if k != 'tensors'}, ensure_ascii=False))

if __name__ == '__main__':
    main()
