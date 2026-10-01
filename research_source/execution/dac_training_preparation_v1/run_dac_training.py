"""Future DAC training launch API. No plan/release/profile is generated here.

--help and import use stdlib only. Training requires a separately prepared exact
plan, a genuine DAC-native profile, CPU compatibility proof and serial release.
"""
import argparse
from contextlib import redirect_stdout, redirect_stderr
import json
import math
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from common_runtime import HERE, no_network, sha_file, write_json
from dac_train_runtime import DACTrainRun, SCIENTIFIC_SOURCE, verify_scientific_source
from input_contract import configuration_defaults, references
import input_audit
from gate_helpers import EXECUTION, alive, owners, exclusive_latest_baseline_lock

def utc():
    return datetime.now(timezone.utc).isoformat()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

PROCESS_ENVIRONMENT_KEYS = ('CUDA_VISIBLE_DEVICES', 'OMP_NUM_THREADS',
    'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS')

def process_environment(plan):
    actual = {name: os.environ.get(name) for name in PROCESS_ENVIRONMENT_KEYS}
    if actual != plan.get('process_environment'):
        raise RuntimeError('Explicitly recorded child process environment changed')
    return actual

def cpu_source_bindings():
    names = ('common_runtime.py', 'dac_train_runtime.py', 'input_contract.py',
        'train_university_train_only.py', 'SCIENTIFIC_SOURCE_MANIFEST.json',
        'SOURCE_PIN.json', 'DAC_EXPECTED_MODEL_SCHEMA.json', 'INPUT_REFERENCES.json')
    return {name: sha_file(HERE / name) for name in names}

def validate_cpu_proof(plan):
    cpu = plan['cpu_compatibility_proof']
    if sha_file(cpu['path']) != cpu['sha256']:
        raise RuntimeError('CPU model/real-pair compatibility report changed')
    proof = read(cpu['path'])
    expected = {'schema': 'dac-real-cpu-compatibility.v1', 'status': 'passed',
        'method': 'DAC', 'model_state_count': 402, 'pretrained_strict_tensor_count': 344,
        'real_pair_original_transforms_passed': True, 'cuda_initialized': False,
        'author_trained_weights_loaded': False, 'all_model_floating_state_finite': True,
        'all_pair_floating_values_finite': True, 'source_files_sha256': cpu_source_bindings(),
        'environment': plan['environment']}
    for key, value in expected.items():
        if proof.get(key) != value:
            raise RuntimeError('The genuine DAC CPU/model/real-pair proof is missing or stale: ' + key)
    return proof

def preparation_code_manifest():
    seal_path = HERE / 'PREPARATION_MANIFEST.json'
    seal = read(seal_path)
    for row in seal['files']:
        path = (HERE / row['path']).resolve()
        if not path.is_relative_to(HERE) or sha_file(path) != row['sha256']:
            raise RuntimeError('DAC preparation changed: ' + row['path'])
    verify_scientific_source()
    return {'method': 'DAC', 'preparation_manifest_sha256': sha_file(seal_path),
        'official_commit': '5612a79c3928d8a71939e4e761bb352f805cb51b', 'files': seal['files']}

def validate_profile(plan_path, profile_path):
    profile = read(profile_path)
    expected = {'schema': 'dac-native-resource-profile.v1', 'method': 'DAC', 'status': 'passed',
        'plan_sha256': sha_file(plan_path), 'nominal_batch_pairs': 24, 'microbatch_pairs': 24,
        'gradient_accumulation': 1, 'img_size': 384, 'model_state_count': 402,
        'mixed_precision': True, 'all_official_losses': True, 'oom': False,
        'all_observed_losses_finite': True, 'all_model_floating_state_finite': True,
        'all_optimizer_floating_state_finite': True, 'representative_parameter_changed': True,
        'research_result': False}
    for key, value in expected.items():
        if profile.get(key) != value:
            raise RuntimeError('A genuine, matching DAC native profile is required: ' + key)
    actual, attempts = profile.get('actual_adamw_steps', 0), profile.get('completed_optimizer_amp_steps', 0)
    if type(actual) is not int or type(attempts) is not int or not 2 <= actual <= attempts <= 32 or profile.get('amp_skips') != attempts - actual:
        raise RuntimeError('Profile lacks two actual AdamW updates or correct AMP accounting')
    if profile.get('peak_allocated_bytes', 0) <= 0 or profile.get('peak_reserved_bytes', 0) < profile['peak_allocated_bytes']:
        raise RuntimeError('Missing genuine memory measurement')
    evidence = profile.get('evidence_sha256', {})
    if not {'batch_progress.jsonl', 'resource_batches.jsonl'}.issubset(evidence):
        raise RuntimeError('Missing per-batch profile measurements')
    for name, expected_sha in evidence.items():
        path = (Path(profile_path).resolve().parent / name).resolve()
        if path.parent != Path(profile_path).resolve().parent or sha_file(path) != expected_sha:
            raise RuntimeError('Profile measurement evidence changed')
    parent = Path(profile_path).resolve().parent
    batch = [json.loads(line) for line in (parent / 'batch_progress.jsonl').read_text(encoding='utf-8').splitlines()]
    resource = [json.loads(line) for line in (parent / 'resource_batches.jsonl').read_text(encoding='utf-8').splitlines()]
    if len(batch) != attempts or len(resource) != attempts:
        raise RuntimeError('Profile traces do not cover every completed attempt')
    previous = 0
    for index, (observed, measured) in enumerate(zip(batch, resource), 1):
        steps = observed.get('actual_optimizer_steps')
        if type(steps) is not int or steps - previous not in (0, 1):
            raise RuntimeError('Invalid actual optimizer step progression in profile trace')
        if observed.get('batch_attempt') != index or observed.get('loss_finite') is not True or not math.isfinite(float(observed['loss'])):
            raise RuntimeError('Invalid or nonfinite original loss measurement')
        if observed.get('optimizer_updated_this_batch') is not bool(steps - previous) or observed.get('amp_skips') != index - steps:
            raise RuntimeError('Profile trace AMP accounting mismatch')
        if measured.get('batch_attempt') != index or measured.get('actual_adamw_steps') != steps or measured.get('amp_skips') != index - steps:
            raise RuntimeError('Resource trace differs from original optimizer hook')
        if not (0 < measured.get('peak_allocated_bytes', 0) <= measured.get('peak_reserved_bytes', 0)):
            raise RuntimeError('Resource trace lacks genuine peak memory measurements')
        previous = steps
    if previous != actual:
        raise RuntimeError('Profile summary differs from real per-batch update records')
    return profile

def validate_inputs(plan_path, profile_path):
    plan = read(plan_path)
    if plan.get('schema') != 'dac-university-training-plan.v1' or plan.get('method') != 'DAC':
        raise RuntimeError('No registered DAC University training plan')
    refs = references()
    for key in ('train_root', 'data_manifest_path', 'data_manifest_sha256', 'pretrained'):
        if plan.get(key) != refs[key]:
            raise RuntimeError('DAC training input differs from the prepared existing reference: ' + key)
    if plan['code_manifest'] != preparation_code_manifest() or plan['official_configuration_defaults'] != configuration_defaults():
        raise RuntimeError('DAC source or original defaults changed')
    if Path(plan['source_directory']).resolve() != SCIENTIFIC_SOURCE.resolve() or plan['seed'] not in (1, 2, 3):
        raise RuntimeError('Invalid source or seed')
    if input_audit.environment() != plan['environment']:
        raise RuntimeError('Use the exact independently reviewed runtime environment')
    process_environment(plan)
    if sha_file(plan['pretrained']['path']) != plan['pretrained']['sha256']:
        raise RuntimeError('Original Meta initialization changed')
    if sha_file(plan['data_manifest_path']) != plan['data_manifest_sha256'] or input_audit.data_manifest(plan['train_root']) != read(plan['data_manifest_path']):
        raise RuntimeError('University train content or official traversal order changed')
    validate_cpu_proof(plan)
    validate_profile(plan_path, profile_path)
    return plan

def serial_release_gate(plan_path, release_path):
    release = read(release_path)
    if release.get('schema') != 'dac-university-training-release.v1' or release.get('allow_cuda') is not True or release.get('training_plan_sha256') != sha_file(plan_path):
        raise RuntimeError('No explicit serial release for this exact DAC plan')
    definitions = [
        ('status.json', 'completed', None),
        ('pipeline_status.json', 'ready_for_extension_preparation', ['formal_aggregate', 'formal_figures', 'cross_dataset_transfer', 'robustness', 'robustness_aggregate', 'query_analysis', 'formal_efficiency_component']),
        ('extension_status.json', 'registered_extensions_finished_review_pending', None),
        ('latest_baseline_status.json', 'latest_baselines_finished_review_pending', None)]
    checked = {}
    for name, status, expected_ids in definitions:
        state = read(EXECUTION / name)
        if state.get('status') != status:
            raise RuntimeError('A preceding registered queue is not complete: ' + name)
        if name == 'status.json' and state.get('stage') != 'all':
            raise RuntimeError('Only completion of the entire primary matrix can release DAC')
        if name in ('extension_status.json', 'latest_baseline_status.json'):
            plan_name = 'extension_plan.json' if name == 'extension_status.json' else 'latest_baseline_plan.json'
            expected_sha = sha_file(EXECUTION / plan_name)
            if release.get('preceding_plan_sha256', {}).get(plan_name) != expected_sha or state.get('plan_sha256') != expected_sha:
                raise RuntimeError('Predecessor plan binding mismatch')
            expected_ids = [row['id'] for row in read(EXECUTION / plan_name)['jobs']]
        if expected_ids is not None:
            if [row.get('id') for row in state.get('jobs', [])] != expected_ids or any(row.get('status') != 'completed' or row.get('exit_code') != 0 for row in state['jobs']):
                raise RuntimeError('A preceding job is missing or unsuccessful')
        process_owners = list(owners(state))
        if not process_owners:
            raise RuntimeError('Missing preceding process ownership evidence')
        for pid, started in process_owners:
            if not started or alive(pid, started):
                raise RuntimeError('Preceding process has not demonstrably exited')
        checked[name] = sha_file(EXECUTION / name)
    # Additional later queues can be explicitly bound by the future serial owner.
    for row in release.get('additional_predecessors', []):
        path = Path(row['path']).resolve()
        if not path.is_relative_to(EXECUTION) or sha_file(path) != row['sha256']:
            raise RuntimeError('Additional predecessor evidence changed')
        state = read(path)
        additional_owners = list(owners(state))
        if not additional_owners or state.get('status') != row['required_status'] or any(not started or alive(pid, started) for pid, started in additional_owners):
            raise RuntimeError('Additional serial predecessor not released')
        if state.get('jobs') and any(job.get('status') != 'completed' or job.get('exit_code') != 0 for job in state['jobs']):
            raise RuntimeError('Additional predecessor contains an unsuccessful job')
        checked[str(path)] = row['sha256']
    gpu = subprocess.run(['nvidia-smi', '--query-compute-apps=pid,process_name', '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=30, check=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    if any('python' in line.lower() for line in gpu.stdout.splitlines()):
        raise RuntimeError('Another Python compute process is active')
    return {'method': 'DAC', 'verified_utc': utc(), 'release_sha256': sha_file(release_path),
        'plan_sha256': sha_file(plan_path), 'preceding_status_sha256': checked,
        'nvidia_compute_rows': gpu.stdout.splitlines(), 'shared_gpu_lock_held': True}

def train(plan_path, profile_path, release_path):
    plan_path, profile_path, release_path = map(lambda p: Path(p).resolve(), (plan_path, profile_path, release_path))
    plan = read(plan_path)
    output = Path(plan['output_directory']).resolve()
    if not output.is_relative_to(EXECUTION) or output.is_relative_to(HERE):
        raise RuntimeError('Future output must be a new execution directory outside preparation source')
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'status.json', {'method': 'DAC', 'status': 'starting', 'started_utc': utc()})
    try:
        with (output / 'stdout.log').open('x', encoding='utf-8') as out, (output / 'stderr.log').open('x', encoding='utf-8') as err:
            with redirect_stdout(out), redirect_stderr(err), no_network():
                plan = validate_inputs(plan_path, profile_path)
                for source, name in ((plan_path, 'plan.json'), (profile_path, 'resource_profile.json'), (Path(plan['data_manifest_path']), 'data_manifest.json'), (release_path, 'serial_release.json')):
                    shutil.copy2(source, output / name)
                write_json(output / 'code_manifest.json', plan['code_manifest'])
                write_json(output / 'environment_manifest.json', input_audit.environment())
                run = DACTrainRun(plan, plan_path, profile_path)
                sys.path.insert(0, str(SCIENTIFIC_SOURCE))
                sys.dont_write_bytecode = True
                with exclusive_latest_baseline_lock():
                    # Refresh lightweight bindings after the potentially lengthy image audit.
                    if plan != read(plan_path) or plan['code_manifest'] != preparation_code_manifest() or input_audit.environment() != plan['environment']:
                        raise RuntimeError('Plan, source or environment changed before serial allocation')
                    process_environment(plan)
                    validate_cpu_proof(plan)
                    validate_profile(plan_path, profile_path)
                    write_json(output / 'serial_release_gate.json', serial_release_gate(plan_path, release_path))
                    input_audit.runtime_environment(output)
                    import torch
                    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
                        raise RuntimeError('One visible GPU is required for the complete official DAC loss branch')
                    with run.image_boundary(), run.training_observers():
                        runpy.run_path(str(HERE / 'train_university_train_only.py'), run_name='__main__', init_globals={'DAC_RUN': run})
                if read(output / 'status.json').get('status') != 'completed':
                    raise RuntimeError('No complete final-epoch checkpoint was produced')
    except BaseException as error:
        (output / 'failure.log').write_text(traceback.format_exc(), encoding='utf-8')
        write_json(output / 'status.json', {'method': 'DAC', 'status': 'failed', 'error': repr(error),
            'failed_utc': utc(), 'recovery': 'Retain failed directory. No automatic batch change or partial-epoch completion claim.'})
        raise

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--release-file', required=True)
    args = parser.parse_args()
    train(args.plan, args.profile, args.release_file)

if __name__ == '__main__':
    main()
