"""Standard-library contracts; importing this module never imports science libraries."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parent
PREPARATION = EXECUTION / 'camp_training_preparation_v2'
PREPARATION_SHA256 = '12747158ce2647474c6d24688ba3ebb872ac137118fab7aefd1c1e0ecfad40ec'
LATEST_IDS = ['camp_author_checkpoint_full_gallery_10tasks', 'dac_author_checkpoint_full_gallery_10tasks']
FINAL_LATEST_STATUS = 'latest_baselines_finished_review_pending'

class PredecessorBusy(RuntimeError):
    pass

def utc():
    return datetime.now(timezone.utc).isoformat()

def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.partial')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    os.replace(temporary, path)

def validate_preparation():
    manifest = PREPARATION / 'PREPARATION_MANIFEST.json'
    if sha(manifest) != PREPARATION_SHA256:
        raise RuntimeError('Frozen training preparation manifest changed')
    rows = read(manifest)['files']
    for row in rows:
        path = (PREPARATION / row['path']).resolve()
        if not path.is_relative_to(PREPARATION) or sha(path) != row['sha256']:
            raise RuntimeError('Frozen preparation payload changed: ' + row['path'])
    return {'manifest_sha256': PREPARATION_SHA256, 'verified_payload_count': len(rows)}

def frozen_api():
    validate_preparation()
    sys.dont_write_bytecode = True
    if str(PREPARATION) not in sys.path:
        sys.path.insert(0, str(PREPARATION))
    api = importlib.import_module('prepare_or_train')
    gate = importlib.import_module('serial_release')
    runtime = importlib.import_module('camp_train_runtime')
    for module in (api, gate, runtime):
        if Path(module.__file__).resolve().parent != PREPARATION:
            raise RuntimeError('Unexpected training adapter import origin')
    return api, gate, runtime

def owner_records(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if (key == 'pid' or key.endswith('_pid')) and isinstance(item, int) and item > 0:
                started = value.get('supervisor_started_utc', value.get('started_utc')) if key == 'supervisor_pid' else value.get('started_utc')
                if not isinstance(started, str):
                    raise RuntimeError('Predecessor PID lacks creation-time evidence: ' + key)
                datetime.fromisoformat(started)
                yield item, started
            elif isinstance(item, (dict, list)):
                yield from owner_records(item)
    elif isinstance(value, list):
        for item in value:
            yield from owner_records(item)

def check_latest_state(state, expected_plan_sha256, is_alive):
    if state.get('plan_sha256') != expected_plan_sha256:
        raise RuntimeError('Latest-author queue status has a different plan')
    if state.get('status') != FINAL_LATEST_STATUS:
        raise RuntimeError('Latest-author queue has not completed')
    jobs = state.get('jobs', [])
    if [job.get('id') for job in jobs] != LATEST_IDS:
        raise RuntimeError('Expected exactly the two registered author-checkpoint jobs')
    if any(job.get('status') != 'completed' or job.get('exit_code') != 0 for job in jobs):
        raise RuntimeError('An author-checkpoint job is incomplete or failed')
    if not state.get('supervisor_pid') or any(not job.get('pid') for job in jobs):
        raise RuntimeError('Completed predecessor lacks recorded process identities')
    checked = []
    for pid, started in sorted(set(owner_records(state))):
        if is_alive(pid, started):
            raise PredecessorBusy(f'Predecessor owner remains alive: PID {pid}')
        checked.append({'pid': pid, 'started_utc': started, 'original_owner_alive': False})
    return checked

def latest_gate(execution_plan, gate_module):
    path = Path(execution_plan['preceding_latest_plan_path'])
    expected = execution_plan['preceding_latest_plan_sha256']
    if sha(path) != expected:
        raise RuntimeError('Preceding latest-author registration changed')
    status_path = EXECUTION / 'latest_baseline_status.json'
    checked = check_latest_state(read(status_path), expected, gate_module.alive)
    return {'verified_utc': utc(), 'status_sha256': sha(status_path), 'plan_sha256': expected, 'owners': checked}

def validate_execution_plan(plan_path):
    plan = read(plan_path)
    if plan.get('schema') != 'camp-independent-training-plan.v1':
        raise RuntimeError('Wrong execution plan schema')
    if plan.get('preparation_manifest_sha256') != PREPARATION_SHA256:
        raise RuntimeError('Execution plan binds a different frozen training preparation')
    if plan.get('thread_environment') != {'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'} or plan.get('CUDA_VISIBLE_DEVICES') != '0':
        raise RuntimeError('Registered single-GPU/thread environment changed')
    if [row.get('seed') for row in plan.get('seeds', [])] != [1, 2, 3]:
        raise RuntimeError('Every seed 1, 2, 3 must be registered exactly once in order')
    if plan.get('stage_order') != ['profile_seed_1', 'train_seed_1', 'profile_seed_2', 'train_seed_2', 'profile_seed_3', 'train_seed_3']:
        raise RuntimeError('The fixed independent profile/full-training order changed')
    if plan.get('profile_policy') != {'actual_adamw_steps_required': 2, 'max_batch_attempts': 32, 'native_batch_pairs': 24, 'automatic_batch_reduction': False, 'per_seed_fresh_process': True}:
        raise RuntimeError('Native two-update profile policy changed')
    validate_preparation()
    for filename, expected in plan['execution_code_sha256'].items():
        path = (HERE / filename).resolve()
        if path.parent != HERE or path.suffix != '.py' or sha(path) != expected:
            raise RuntimeError('Execution code changed: ' + filename)
    if set(plan['execution_code_sha256']) != {p.name for p in HERE.glob('*.py')}:
        raise RuntimeError('Execution source inventory changed')
    outputs = set()
    reference = None
    for row in plan['seeds']:
        if sha(row['plan_path']) != row['plan_sha256']:
            raise RuntimeError('Per-seed training plan changed')
        seed_plan = read(row['plan_path'])
        if plan['python_executable'] != seed_plan['environment']['executable']:
            raise RuntimeError('Execution interpreter differs from the original seed plan')
        if seed_plan['seed'] != row['seed'] or seed_plan['output_directory'] != row['output_directory']:
            raise RuntimeError('Seed/output binding mismatch')
        for key, expected in {'epochs': 1, 'nominal_batch_pairs': 24, 'microbatch_pairs': 24,
                              'gradient_accumulation': 1, 'img_size': 384, 'mixed_precision': True,
                              'num_workers': 0, 'training_test_access': False}.items():
            if seed_plan['protocol'].get(key) != expected:
                raise RuntimeError('Scientific training protocol changed: ' + key)
        if Path(row['output_directory']).resolve() in outputs:
            raise RuntimeError('Duplicate final training directory')
        outputs.add(Path(row['output_directory']).resolve())
        same = {k: v for k, v in seed_plan.items() if k not in ('created_utc', 'seed', 'output_directory')}
        if reference is None:
            reference = same
        elif same != reference:
            raise RuntimeError('The three seeds differ in their scientific configuration or inputs')
    for path, expected in plan['environment_records_sha256'].items():
        if sha(path) != expected:
            raise RuntimeError('Registered environment RECORD changed: ' + path)
    return plan

def validate_stage_environment(plan):
    expected = {**plan['thread_environment'], 'CUDA_VISIBLE_DEVICES': plan['CUDA_VISIBLE_DEVICES']}
    actual = {name: os.environ.get(name) for name in expected}
    if actual != expected:
        raise RuntimeError('Child process thread/GPU environment differs from registration')
    return actual

def validate_release(plan_path, release_path):
    release = read(release_path)
    plan = validate_execution_plan(plan_path)
    if release.get('schema') != 'camp-independent-training-execution-release.v1' or release.get('allow_cuda') is not True:
        raise RuntimeError('No active external serial execution release')
    if release.get('execution_plan_sha256') != sha(plan_path) or release.get('preceding_latest_plan_sha256') != plan['preceding_latest_plan_sha256']:
        raise RuntimeError('Execution release does not bind the exact plans')
    return plan

def write_seed_release(seed_row, destination, outer_release_path, execution_plan):
    # Derived only at runtime after validation of the explicit outer release.
    write(destination, {'schema': 'camp-university-training-release.v1', 'allow_cuda': True,
        'training_plan_sha256': seed_row['plan_sha256'],
        'preceding_extension_plan_sha256': execution_plan['preceding_extension_plan_sha256'],
        'outer_execution_release_sha256': sha(outer_release_path), 'derived_utc': utc()})

def verify_profile(profile_path, seed_row, execution_plan_path):
    profile = read(profile_path)
    expected = {'schema': 'camp-native-resource-profile.v1', 'status': 'passed',
        'plan_sha256': seed_row['plan_sha256'], 'execution_plan_sha256': sha(execution_plan_path),
        'nominal_batch_pairs': 24, 'microbatch_pairs': 24, 'gradient_accumulation': 1,
        'img_size': 384, 'all_official_losses': True, 'mixed_precision': True,
        'oom': False, 'exclusive_gpu_allocation': True, 'research_result': False,
        'all_model_floating_state_finite': True, 'all_optimizer_floating_state_finite': True,
        'representative_parameter_changed': True, 'all_observed_losses_finite': True,
        'research_checkpoint_written': False}
    for key, value in expected.items():
        if profile.get(key) != value:
            raise RuntimeError('Invalid genuine profile evidence: ' + key)
    actual, attempts = profile.get('actual_adamw_steps', 0), profile.get('completed_optimizer_amp_steps', 0)
    if actual < 2 or not actual <= attempts <= 32 or profile.get('amp_skips') != attempts - actual:
        raise RuntimeError('Two actual AdamW updates, separately from AMP skips, are required')
    losses = profile.get('losses', [])
    if len(losses) != attempts or any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in losses):
        raise RuntimeError('Missing finite original loss evidence for every attempted batch')
    if profile.get('initial_parameter_sha256') == profile.get('final_parameter_sha256') or not profile.get('initial_parameter_sha256') or not profile.get('final_parameter_sha256'):
        raise RuntimeError('Missing independently hashed changed parameter evidence')
    if profile.get('peak_allocated_bytes', 0) <= 0 or profile.get('peak_reserved_bytes', 0) < profile['peak_allocated_bytes']:
        raise RuntimeError('Missing measured CUDA memory peaks')
    for name, expected_hash in profile.get('evidence_sha256', {}).items():
        path = (Path(profile_path).parent / name).resolve()
        if path.parent != Path(profile_path).resolve().parent or sha(path) != expected_hash:
            raise RuntimeError('Profile evidence changed')
    if 'batch_progress.jsonl' not in profile.get('evidence_sha256', {}) or 'resource_batches.jsonl' not in profile['evidence_sha256']:
        raise RuntimeError('Missing genuine per-batch evidence')
    batch_rows = [json.loads(line) for line in (Path(profile_path).parent / 'batch_progress.jsonl').read_text(encoding='utf-8').splitlines()]
    resource_rows = [json.loads(line) for line in (Path(profile_path).parent / 'resource_batches.jsonl').read_text(encoding='utf-8').splitlines()]
    if len(batch_rows) != attempts or len(resource_rows) != attempts:
        raise RuntimeError('Per-batch evidence count mismatch')
    previous = 0
    for number, (batch, resource, loss) in enumerate(zip(batch_rows, resource_rows, losses), 1):
        count = batch.get('actual_optimizer_steps', -1)
        delta = count - previous
        if delta not in (0, 1) or batch.get('batch_attempt') != number or resource.get('batch_attempt') != number or batch.get('loss') != loss or batch.get('loss_finite') is not True or batch.get('optimizer_updated_this_batch') != bool(delta):
            raise RuntimeError('Per-batch optimizer/loss evidence is inconsistent')
        if batch.get('amp_skips') != number - count or resource.get('actual_adamw_steps') != count or resource.get('amp_skips') != number - count:
            raise RuntimeError('Per-batch AMP skip evidence is inconsistent')
        previous = count
    if previous != actual:
        raise RuntimeError('Last actual-update counter differs from profile summary')
    return profile

@contextmanager
def supervisor_lock():
    if os.name != 'nt':
        raise RuntimeError('This preparation targets Windows')
    import msvcrt
    with (HERE / 'supervisor.lock').open('a+b') as stream:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
