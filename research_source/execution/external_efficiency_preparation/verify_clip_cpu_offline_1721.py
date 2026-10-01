"""Isolated CPU compatibility check; no GPU benchmark or cache-parity claim."""
import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import sys
import traceback
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
OUT = HERE / 'clip_cpu_offline_validation_1721'
EXPECTED_PYTHON = Path(r'C:\项目\.venvs\lgm-baselines\Scripts\python.exe')
def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()
def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def refuse_network(*args, **kwargs):
    raise RuntimeError('CPU compatibility check is offline only')

assert Path(sys.executable).resolve() == EXPECTED_PYTHON.resolve()
assert not OUT.exists(), 'Preserve an earlier attempt; use a reviewed new probe version.'
OUT.mkdir()
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'
os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1')
manifest_path = HERE / 'CLIP_OFFLINE_SNAPSHOT_MANIFEST_1721.json'
assert sha(manifest_path) == 'ae8d97c54f262adda48e94e0b7a4694e364bbe167eae761e490c02d5c5104226'
manifest = read(manifest_path)
assert manifest['revision'] == '3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268'
for row in manifest['files']:
    assert Path(row['path']).stat().st_size == row['bytes'] and sha(row['path']) == row['sha256']
report = {'status': 'started_cpu_compatibility_check', 'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'python': sys.executable, 'pid': os.getpid(), 'script_sha256': sha(__file__),
          'snapshot_manifest_sha256': sha(manifest_path), 'gpu_benchmark_executed': False,
          'cache_probability_parity_tested': False, 'manuscript_result': False}
(OUT/'started.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
try:
    with patch.object(socket.socket, 'connect', refuse_network), patch.object(socket.socket, 'connect_ex', refuse_network), patch.object(socket, 'create_connection', refuse_network):
        import torch
        import numpy
        import PIL
        import transformers
        from PIL import Image
        from transformers import CLIPModel, CLIPProcessor
        torch.set_num_threads(1)
        assert not torch.cuda.is_initialized()
        expected = {'torch': '2.11.0+cu126', 'numpy': '2.4.4', 'Pillow': '12.2.0', 'transformers': '4.57.6'}
        versions = {name: importlib.metadata.version(name) for name in expected}
        assert versions == expected
        for module in (torch, numpy, PIL, transformers):
            assert Path(module.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
        snapshot = Path(manifest['local_snapshot'])
        model, loading = CLIPModel.from_pretrained(str(snapshot), local_files_only=True, use_safetensors=False, output_loading_info=True)
        model.eval()
        allowed_old_buffers = {'text_model.embeddings.position_ids', 'vision_model.embeddings.position_ids'}
        assert not loading.get('missing_keys') and not loading.get('mismatched_keys') and not loading.get('error_msgs')
        assert set(loading.get('unexpected_keys', [])) <= allowed_old_buffers
        raw = torch.load(snapshot/'pytorch_model.bin', map_location='cpu', weights_only=True, mmap=True)
        current = model.state_dict()
        assert len(raw) == 400 and len(current) == 398
        assert set(raw)-set(current) == allowed_old_buffers and not set(current)-set(raw)
        for name, tensor in current.items():
            assert tensor.device.type == 'cpu' and tensor.dtype == torch.float32
            assert torch.equal(tensor, raw[name]), name
            assert bool(torch.isfinite(tensor).all()), name
        for name, width in (('text_model.embeddings.position_ids',77), ('vision_model.embeddings.position_ids',50)):
            actual = dict(model.named_buffers())[name]
            assert torch.equal(raw[name], torch.arange(width,dtype=torch.int64).reshape(1,width))
            assert torch.equal(actual,raw[name])
        del raw
        processor = CLIPProcessor.from_pretrained(str(snapshot), local_files_only=True)
        assert type(processor.image_processor).__name__ == 'CLIPImageProcessor'
        assert processor.tokenizer.is_fast is True
        inventory_path = HERE.parent/'camp_training_inputs'/'university_train_content_manifest.json'
        assert sha(inventory_path) == 'c6620e548072d5a9b795018133442986b344820f0fe87af76f362870e4b02da4'
        inventory = read(inventory_path)
        selected = next(row for row in inventory['files'] if row['path'].startswith('drone/'))
        image_path = Path(inventory['train_root'])/selected['path']
        assert sha(image_path) == selected['sha256']
        with Image.open(image_path) as encoded:
            image = encoded.convert('RGB')
        try:
            batch = processor(images=[image], return_tensors='pt')
        finally:
            image.close()
        assert tuple(batch['pixel_values'].shape) == (1,3,224,224)
        assert batch['pixel_values'].device.type == 'cpu'
        with torch.inference_mode():
            features = model.get_image_features(**batch)
        assert tuple(features.shape) == (1,512) and bool(torch.isfinite(features).all())
        assert not features.requires_grad and not torch.cuda.is_initialized()
        report.update(status='passed_real_cpu_load_and_one_training_image_forward', finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            versions=versions, loading_info=loading, source_state_entries=400, learned_model_state_entries=398,
            all_learned_state_values_exact_and_finite=True, validated_nonpersistent_old_buffers=sorted(allowed_old_buffers),
            model_dtype='torch.float32', model_device='cpu', image_processor_class=type(processor.image_processor).__name__,
            tokenizer_class=type(processor.tokenizer).__name__, tokenizer_is_fast=processor.tokenizer.is_fast,
            original_image={'path':str(image_path),'sha256':selected['sha256']}, input_shape=list(batch['pixel_values'].shape),
            feature_shape=list(features.shape), feature_all_finite=True, cuda_initialized=False,
            scope='CPU compatibility and real image plumbing only. No CUDA autocast, native GPU timing, online-cache parity or retrieval metric was tested.')
except BaseException as error:
    report.update(status='failed_cpu_compatibility_check', error=f'{type(error).__name__}: {error}', traceback=traceback.format_exc())
    (OUT/'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    raise
(OUT/'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'status':report['status'],'result':str(OUT/'result.json'),'cuda_initialized':False}))
