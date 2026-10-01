"""Offline CLIP source inventory; no numerical package imports or model loading."""
from pathlib import Path
import ast
import collections
import datetime
import email.parser
import hashlib
import io
import json
import math
import pickle
import struct
import sys
import zipfile

HERE = Path(__file__).resolve().parent
REV = '3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268'
HF = Path(r'C:\Users\17703\.cache\huggingface\hub\models--openai--clip-vit-base-patch32')
SNAP = HF / 'snapshots' / REV
ORIGINAL = Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch')
SITE = Path(r'C:\项目\.venvs\lgm-baselines\Lib\site-packages')
GENERATOR = ORIGINAL / 'lgm_game_pytorch/generate_clip_image_evidence.py'
REQUIRED = ['config.json', 'merges.txt', 'preprocessor_config.json', 'pytorch_model.bin', 'special_tokens_map.json', 'tokenizer.json', 'tokenizer_config.json', 'vocab.json']

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def pin(path):
    return {'path': str(path.resolve()), 'bytes': path.stat().st_size, 'sha256': sha(path)}

def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()

files = [pin(SNAP / name) for name in REQUIRED]
snapshot_manifest = {'schema': 'clip-offline-snapshot-pins.v1', 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'repository': 'openai/clip-vit-base-patch32', 'revision': REV, 'local_snapshot': str(SNAP), 'files': files, 'no_model_load_performed': True}
manifest_path = HERE / 'CLIP_OFFLINE_SNAPSHOT_MANIFEST_1721.json'
if manifest_path.exists():
    existing_manifest = read_json(manifest_path)
    assert existing_manifest['files'] == snapshot_manifest['files'] and existing_manifest['revision'] == REV
    snapshot_manifest = existing_manifest
else:
    manifest_path.write_text(json.dumps(snapshot_manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('SNAPSHOT_MANIFEST_READY ' + str(manifest_path), flush=True)

# Read tensor reconstruction metadata with explicitly allowed symbolic handlers.
# Never import torch, instantiate a tensor, or execute an archive-supplied callable.
def symbolic_tensor(storage, offset, shape, stride, requires_grad=False, hooks=None, metadata=None):
    return {'storage': storage, 'offset': offset, 'shape': list(shape), 'stride': list(stride), 'requires_grad': requires_grad}

class MetadataOnlyUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if (module, name) == ('collections', 'OrderedDict'):
            return collections.OrderedDict
        if module == 'torch' and name in {'FloatStorage', 'LongStorage', 'HalfStorage'}:
            return name
        if (module, name) in {('torch._utils', '_rebuild_tensor_v2'), ('torch._utils', '_rebuild_tensor')}:
            return symbolic_tensor
        raise ValueError(f'Non-allowlisted pickle global: {module}.{name}')

    def persistent_load(self, pid):
        if not isinstance(pid, tuple) or len(pid) != 5 or pid[0] != 'storage':
            raise ValueError('Unexpected persistent storage descriptor')
        _, dtype, key, device, numel = pid
        if dtype not in {'FloatStorage', 'LongStorage', 'HalfStorage'} or not isinstance(numel, int) or numel < 0:
            raise ValueError('Unexpected storage metadata')
        return {'dtype': dtype, 'key': key, 'device': device, 'numel': numel}

with zipfile.ZipFile(SNAP / 'pytorch_model.bin') as archive:
    pickles = [n for n in archive.namelist() if n.endswith('/data.pkl')]
    assert len(pickles) == 1
    state = MetadataOnlyUnpickler(io.BytesIO(archive.read(pickles[0]))).load()
    assert isinstance(state, collections.OrderedDict)
    root = pickles[0].rsplit('/', 1)[0]
    crc_failure = archive.testzip()
    assert crc_failure is None
    logit = state['logit_scale']
    assert logit['storage']['dtype'] == 'FloatStorage' and logit['shape'] == []
    logit_bytes = archive.read(root + '/data/' + str(logit['storage']['key']))
    learned_logit = struct.unpack_from('<f', logit_bytes, logit['offset'] * 4)[0]
    tensor_metadata = []
    legacy_position_buffers = []
    for name, spec in state.items():
        info = archive.getinfo(root + '/data/' + str(spec['storage']['key']))
        itemsize = {'FloatStorage': 4, 'LongStorage': 8, 'HalfStorage': 2}[spec['storage']['dtype']]
        assert info.file_size == spec['storage']['numel'] * itemsize
        tensor_metadata.append({'name': name, **spec, 'storage_bytes': info.file_size})
        if spec['storage']['dtype'] == 'LongStorage':
            assert name in {'text_model.embeddings.position_ids', 'vision_model.embeddings.position_ids'}
            payload = archive.read(info)
            expected_count = 77 if name.startswith('text_') else 50
            values = struct.unpack('<' + 'q' * expected_count, payload)
            assert values == tuple(range(expected_count))
            legacy_position_buffers.append({'name': name, 'shape': spec['shape'], 'exact_int64_values_are_arange': True, 'count': expected_count})
    checkpoint = {'format': 'pytorch zip archive', 'zip_crc_verified': True, 'member_count': len(archive.infolist()), 'symbolic_state_entries': len(state), 'dtype_counts': dict(collections.Counter(v['storage']['dtype'] for v in state.values())), 'total_tensor_elements_in_state': sum(math.prod(v['shape']) for v in state.values()), 'learned_logit_scale_fp32': learned_logit, 'python_exp_unclamped_for_reference_only': math.exp(learned_logit), 'metadata_scale_after_original_torch_fp32_exp_and_max100': 100.0, 'tensor_metadata': tensor_metadata, 'legacy_position_buffers': legacy_position_buffers, 'current_model_source_position_ids_persistent': False, 'load_mismatch_caveat': 'Current modeling_clip.py registers both buffers persistent=False. Actual offline loading_info must be recorded; only these exact legacy arange buffers have a source-grounded potential unexpected-key explanation. No arbitrary missing or unexpected learned weights accepted.', 'model_not_loaded': True, 'all_tensor_finite_values_not_checked': True}

generator_ast = ast.parse(GENERATOR.read_text(encoding='utf-8-sig'))
constants = {}
for node in generator_ast.body:
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id in {'CONTENT_CANDIDATES', 'STYLE_CANDIDATES'}:
        constants[node.target.id] = ast.literal_eval(node.value)
content = [{'id': i, 'text': t} for i, t in constants['CONTENT_CANDIDATES']]
style = [{'id': i, 'text': t} for i, t in constants['STYLE_CANDIDATES']]
assert len(content) == 11 and len(style) == 10

def npy_header(stream):
    assert stream.read(6) == b'\x93NUMPY'
    version = stream.read(2)
    width = 2 if version[0] == 1 else 4
    length = int.from_bytes(stream.read(width), 'little')
    assert 0 < length < 100000
    return {'version': list(version), **ast.literal_eval(stream.read(length).decode('latin1').strip())}

caches = []
for dataset, rows in [('university1652', 146520), ('sues200', 40200)]:
    meta_path = ORIGINAL / f'evidence_cache/{dataset}_clip_image_evidence.meta.json'
    data_path = ORIGINAL / f'evidence_cache/{dataset}_clip_image_evidence.npz'
    meta = read_json(meta_path)
    assert meta['model']['revision_requested'] == REV == meta['model']['revision_resolved']
    assert meta['model']['name'] == 'openai/clip-vit-base-patch32'
    assert meta['content_candidates'] == content and meta['style_candidates'] == style
    assert meta['hashes']['content_candidates_sha256'] == canonical_sha(content)
    assert meta['hashes']['style_candidates_sha256'] == canonical_sha(style)
    assert meta['hashes']['combined_candidates_sha256'] == canonical_sha({'content': content, 'style': style})
    data_pin = pin(data_path)
    assert data_pin['sha256'] == meta['cache_sha256'] == meta['hashes']['cache_sha256']
    headers = {}
    with zipfile.ZipFile(data_path) as archive:
        assert archive.testzip() is None
        for member in archive.namelist():
            with archive.open(member) as stream:
                headers[member] = npy_header(stream)
    assert headers['content_probs.npy']['descr'] == '<f2' and tuple(headers['content_probs.npy']['shape']) == (rows, 11)
    assert headers['style_probs.npy']['descr'] == '<f2' and tuple(headers['style_probs.npy']['shape']) == (rows, 10)
    caches.append({'dataset': dataset, 'metadata': pin(meta_path), 'cache': data_pin, 'headers': headers, 'coverage': meta['coverage'], 'model': meta['model'], 'hardware': meta['hardware'], 'run_configuration': meta['run_configuration'], 'software': meta['software'], 'determinism': meta['determinism'], 'candidate_hashes': {k: v for k, v in meta['hashes'].items() if 'candidates' in k}, 'cache_crc_verified': True, 'numeric_probability_parity_not_executed': True})

packages = []
for pattern in ['transformers-*.dist-info', 'huggingface_hub-*.dist-info', 'tokenizers-*.dist-info', 'safetensors-*.dist-info', 'torch-*.dist-info', 'numpy-*.dist-info', 'pillow-*.dist-info']:
    found = list(SITE.glob(pattern))
    assert len(found) == 1, pattern
    dist = found[0]
    meta = email.parser.Parser().parsestr((dist / 'METADATA').read_text(encoding='utf-8'))
    packages.append({'name': meta['Name'], 'version': meta['Version'], 'directory': str(dist), 'metadata': pin(dist / 'METADATA'), 'record': pin(dist / 'RECORD')})

sources = [GENERATOR, ORIGINAL / 'lgm_game_pytorch/formal_retrieval.py', SITE / 'transformers/processing_utils.py', SITE / 'transformers/modeling_utils.py', SITE / 'transformers/models/clip/processing_clip.py', SITE / 'transformers/models/clip/image_processing_clip.py', SITE / 'transformers/models/clip/modeling_clip.py', SITE / 'transformers/models/auto/tokenization_auto.py', SITE / 'huggingface_hub/file_download.py']
config = read_json(SNAP / 'config.json')
other_snapshots = [{'revision': p.name, 'files': sorted(x.name for x in p.iterdir() if x.is_file())} for p in (HF / 'snapshots').iterdir() if p.name != REV]
no_exist = sorted(p.name for p in (HF / '.no_exist' / REV).iterdir())
assert not (SNAP / 'model.safetensors').exists() and 'model.safetensors' in no_exist
report = {
    'schema': 'clip-offline-source-audit.v1',
    'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status': 'required_offline_files_present_source_and_archive_checks_passed_model_load_not_executed',
    'snapshot_manifest': pin(manifest_path),
    'snapshot': snapshot_manifest,
    'checkpoint_archive': checkpoint,
    'snapshot_model_config': config,
    'snapshot_preprocessor_config': read_json(SNAP / 'preprocessor_config.json'),
    'snapshot_tokenizer_config': read_json(SNAP / 'tokenizer_config.json'),
    'vocabulary_entries': len(read_json(SNAP / 'vocab.json')),
    'cache_metadata_and_data': caches,
    'ordered_content_candidates': content,
    'ordered_style_candidates': style,
    'baseline_packages_read_only_metadata': packages,
    'source_pins': [pin(p) for p in sources],
    'hf_cache_provenance': {'repository_directory': str(HF), 'refs_main': (HF / 'refs/main').read_text().strip(), 'refs_pr66': (HF / 'refs/refs/pr/66').read_text().strip(), 'other_snapshots': other_snapshots, 'negative_cache_entries': no_exist, 'snapshot_files_are_regular_files_not_symlinks': all(not (SNAP/n).is_symlink() for n in REQUIRED), 'inherited_evidence': 'Original cache metadata pins requested/resolved commit and model-config canonical hash, and installed loader source resolves missing safetensors to bin for use_safetensors=None. Metadata does not contain the original weight-file SHA or download HTTP receipt. Present files are now explicitly hashed; no new remote provenance claim is made.'},
    'offline_driver_loading': {'interpreter': r'C:\项目\.venvs\lgm-baselines\Scripts\python.exe', 'model_class': 'transformers.CLIPModel', 'processor_class': 'transformers.CLIPProcessor', 'local_path': str(SNAP), 'model_kwargs': {'local_files_only': True, 'use_safetensors': False}, 'processor_kwargs': {'local_files_only': True}, 'precision': 'Do not call model.half(): original parameters/load default FP32 with fp16 autocast only for image/text feature forward. Feature normalization and logits/softmax occur outside autocast in FP32; final probabilities cast float16.', 'processor_selection': 'Keep original use_fast unset in fixed transformers4.57.6: slow CLIPImageProcessor is selected, AutoTokenizer defaults fast. Explicit global use_fast=False can also switch tokenizer and is not silently substituted.', 'processor_normalization': 'PIL RGB; bicubic shortest-edge224, center crop224; rescale1/255; provided CLIP mean/std; retain slow image processor.', 'model_commit_note': 'Local directory loading can omit config._commit_hash. Bind commit using directory path and manifest SHA; record original repository and commit separately. Do not overwrite checkpoint/model fields to fabricate a resolver result.', 'no_download_or_environment_change_needed_for_required_files': True, 'actual_offline_model_load_test_performed': False},
    'scientific_semantics': {'image_batch_size_in_original_caches': 128, 'image_load_threads_in_original_caches': 8, 'text_forward_calls': 'two separate candidate-family batches, 11 then 10; do not combine into one 21-token-family batch without numerical parity proof', 'candidate_order_equal_across_both_datasets_and_generator': True, 'features': 'get_image_features/get_text_features -> features.float() -> F.normalize(dim=-1)', 'scale': 'float(model.logit_scale.detach().float().exp().clamp(max=100).cpu())', 'separate_softmax': 'content11 and style10 separately, FP32 logits outside autocast, output NumPy float16', 'retrieval_cache_validation': 'Original EvidenceStore validation converts cached float16 probabilities to float32 with its original validation path; no extra renormalization added.', 'new_query_batch_caveat': 'Native cache was generated at image batch128. A B=1 timing path may differ after float16 quantization. Exact selected-query parity remains a runtime gate, not proven by this static audit; never relax tolerance after observing failure.'},
    'limitations': ['No tensor numerical forward, CUDA initialization, real timing, new experiment or model load.', 'ZIP CRC, symbolic tensor metadata and hashes prove current archive consistency, not weight accuracy or provenance beyond available retained records.', 'All tensor finiteness and strict live model state compatibility await isolated offline load when resource conditions allow.', 'Do not use safetensors from c237dc49 PR snapshot for fixed3d74 loading.'],
    'scientific_imports': [name for name in sys.modules if name.split('.')[0] in {'torch', 'numpy', 'PIL', 'transformers', 'safetensors'}],
}
assert report['scientific_imports'] == []
out = HERE / 'CLIP_OFFLINE_SOURCE_AUDIT_1721.json'
out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': report['status'], 'report': str(out), 'manifest_sha256': sha(manifest_path), 'weight': next(p for p in files if p['path'].endswith('pytorch_model.bin')), 'state_entries': len(state), 'logit_scale_raw': learned_logit, 'scientific_imports': report['scientific_imports']}, ensure_ascii=False), flush=True)
