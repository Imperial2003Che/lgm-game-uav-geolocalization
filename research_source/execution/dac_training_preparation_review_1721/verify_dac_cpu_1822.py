"""Root-owned real CPU compatibility probe; no training, GPU, or model forward."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import sys
import traceback

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'dac_training_preparation_v1'
OUTPUT = HERE / 'real_cpu_probe_1822'
MODEL_OUTPUT = OUTPUT / 'model_and_pair'
EXPECTED_PREPARATION = '169a6eb7c351acc7e291b4ceefdecebda2c80ad70b46a20eeed6d42d14e72bc9'

def sha(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def now():
    return datetime.now(timezone.utc).isoformat()

def write(path, value):
    with open(path, 'x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)

def main():
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise RuntimeError('CPU visibility must be set before interpreter startup')
    if Path(sys.executable).resolve() != Path(r'C:\项目\.venvs\lgm-camp\Scripts\python.exe').resolve():
        raise RuntimeError('Wrong independent CAMP/DAC environment')
    if any(name in sys.modules for name in ('torch', 'numpy', 'cv2', 'PIL')):
        raise RuntimeError('Expected a fresh interpreter')
    OUTPUT.mkdir(exist_ok=False)
    report = {'schema': 'dac-real-cpu-compatibility.v1', 'status': 'running',
              'method': 'DAC', 'started_utc': now(), 'pid': os.getpid(),
              'script_sha256': sha(__file__), 'model_forward_executed': False,
              'optimizer_steps_executed': 0, 'gpu_profile_executed': False,
              'research_result': False, 'seed': 1}
    write(OUTPUT / 'started.json', report)
    try:
        assert sha(SOURCE / 'PREPARATION_MANIFEST.json') == EXPECTED_PREPARATION
        sys.path.insert(0, str(SOURCE))
        from run_dac_training import cpu_source_bindings, preparation_code_manifest
        from input_contract import construct_model_cpu, normal_dataset_cpu, references
        from input_audit import environment, runtime_environment
        from common_runtime import no_network
        from dac_train_runtime import validate_model_schema, verify_scientific_source
        report['source_files_sha256'] = cpu_source_bindings()
        report['preparation'] = preparation_code_manifest()
        report['environment'] = environment()
        report['process_environment'] = {key: os.environ.get(key) for key in (
            'CUDA_VISIBLE_DEVICES', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
            'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'NO_ALBUMENTATIONS_UPDATE')}
        with no_network():
            model, config, run = construct_model_cpu(MODEL_OUTPUT, seed=1)
            import torch
            assert not torch.cuda.is_initialized()
            state = model.state_dict()
            report['model_schema'] = validate_model_schema(state)
            report['model_state_count'] = len(state)
            report['all_model_state_cpu'] = all(value.device.type == 'cpu' for value in state.values())
            report['all_model_floating_state_finite'] = all(
                bool(torch.isfinite(value).all().item()) for value in state.values() if value.is_floating_point())
            assert report['all_model_state_cpu'] and report['all_model_floating_state_finite']
            report['model_parameter_count'] = sum(value.numel() for value in model.parameters())
            pretrained = json.loads((MODEL_OUTPUT / 'pretrained_binding.json').read_text(encoding='utf-8'))
            assert pretrained['expected_tensor_count'] == pretrained['loaded_tensor_count'] == 344
            assert pretrained['load_policy'] == 'strict=True'
            assert not any(pretrained[key] for key in ('missing_keys', 'unexpected_keys', 'shape_dtype_mismatch', 'ignored_keys'))
            ref = references()
            assert pretrained['sha256'] == sha(ref['pretrained']['path']) == ref['pretrained']['sha256']
            report['pretrained_strict_tensor_count'] = 344
            report['pretrained_binding'] = pretrained
            binding = json.loads((MODEL_OUTPUT / 'dac_model_binding.json').read_text(encoding='utf-8'))
            report['author_trained_weights_loaded'] = binding['author_trained_weights_loaded']
            assert report['author_trained_weights_loaded'] is False
            report['cudnn_actual'] = binding['cudnn_actual']
            report['native_model_data_config'] = run.cpu_data_config
            with run.image_boundary():
                dataset = normal_dataset_cpu(config, run)
                sample = dataset.samples[0]
                pair = dataset[0]
            assert len(dataset.ids) == 701 and len(dataset.pairs) == len(dataset) == 37854
            assert pair[2] == sample[0] and pair[3] == sample[1]
            reference_manifest = json.loads(Path(ref['data_manifest_path']).read_text(encoding='utf-8'))
            rows = {row['path']: row for row in reference_manifest['files']}
            report['real_images'] = []
            for path_text in sample[2:]:
                path = Path(path_text).resolve()
                relative = path.relative_to(Path(ref['train_root']).resolve()).as_posix()
                expected = rows[relative]
                actual_sha = sha(path)
                assert actual_sha == expected['sha256'] and path.stat().st_size == expected['bytes']
                report['real_images'].append({'path': str(path), 'relative_path': relative,
                    'sha256': actual_sha, 'bytes': path.stat().st_size, 'matches_full_training_inventory': True})
            report['pair_tensors'] = []
            for value in pair[:2]:
                assert isinstance(value, torch.Tensor)
                assert tuple(value.shape) == (3, 384, 384) and value.dtype == torch.float32
                assert value.device.type == 'cpu' and bool(torch.isfinite(value).all().item())
                report['pair_tensors'].append({'shape': list(value.shape), 'dtype': str(value.dtype),
                    'device': str(value.device), 'finite': True,
                    'sha256': hashlib.sha256(value.detach().contiguous().numpy().tobytes()).hexdigest()})
            report.update(real_pair_original_transforms_passed=True, all_pair_floating_values_finite=True,
                identity_count=len(dataset.ids), training_pair_count=len(dataset.pairs),
                sampled_identity=str(pair[2]), sampled_label=int(pair[3]),
                pair_position=0, shuffle_executed=False, full_image_inventory_rescanned=False)
            report['runtime_environment'] = runtime_environment(OUTPUT)
            report['module_origins'] = {
                name: str(Path(module.__file__).resolve())
                for name, module in list(sys.modules.items())
                if name.startswith('sample4geo.') and getattr(module, '__file__', None)}
            verify_scientific_source()
            assert report['source_files_sha256'] == cpu_source_bindings()
            assert sha(SOURCE / 'PREPARATION_MANIFEST.json') == EXPECTED_PREPARATION
            report['cuda_initialized'] = torch.cuda.is_initialized()
            assert report['cuda_initialized'] is False
        report.update(status='passed', finished_utc=now(), network='socket connects blocked during scientific work')
        report['artifact_sha256'] = {str(path.relative_to(OUTPUT)): sha(path)
            for path in OUTPUT.rglob('*') if path.is_file()}
        write(OUTPUT / 'result.json', report)
        print(json.dumps({'status': report['status'], 'result': str(OUTPUT / 'result.json'),
            'sha256': sha(OUTPUT / 'result.json'), 'states': len(state),
            'pretrained': 344, 'real_pair': True, 'cuda_initialized': False}))
    except BaseException:
        report.update(status='failed', finished_utc=now(), traceback=traceback.format_exc())
        write(OUTPUT / 'failure.json', report)
        raise

if __name__ == '__main__':
    main()
