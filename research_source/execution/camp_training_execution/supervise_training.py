"""Prepare a new immutable plan, or explicitly supervise its six serial stages.

Preparation uses standard-library file/metadata operations only. No registration,
release or status is created by prepare. Supervise requires a later external release.
"""
import argparse
import copy
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from contracts import (EXECUTION, HERE, LATEST_IDS, FINAL_LATEST_STATUS, PREPARATION_SHA256,
    PredecessorBusy, check_latest_state, frozen_api, owner_records, read, sha,
    supervisor_lock, utc, validate_execution_plan, validate_preparation,
    validate_release, verify_profile, write)

def prepare(args):
    destination = Path(args.plan).resolve()
    if destination.exists():
        raise RuntimeError('Execution plans are immutable; choose a new path')
    validate_preparation()
    latest_path = EXECUTION / 'latest_baseline_plan.json'
    latest = read(latest_path)
    if [row['id'] for row in latest['jobs']] != LATEST_IDS:
        raise RuntimeError('Unexpected latest-author queue definition')
    seeds = []
    for seed in (1, 2, 3):
        path = Path(args.input_directory).resolve() / f'seed_{seed}_plan.json'
        original = read(path)
        if original['seed'] != seed:
            raise RuntimeError('Input plan seed mismatch')
        row = {'seed': seed, 'plan_path': str(path), 'plan_sha256': sha(path),
            'output_directory': original['output_directory'],
            'profile_directory': str(EXECUTION / 'camp_independent_profiles' / f'seed_{seed}'),
            'training_receipt_directory': str(HERE / 'receipts' / f'seed_{seed}')}
        if any(Path(row[key]).exists() for key in ('output_directory', 'profile_directory', 'training_receipt_directory')):
            raise RuntimeError('A future artifact directory already exists; do not reuse partial work')
        seeds.append(row)
    first = read(seeds[0]['plan_path'])
    prefix = Path(first['environment']['prefix'])
    records = {str(p.resolve()): sha(p) for p in (prefix / 'Lib' / 'site-packages').glob('*.dist-info/RECORD')}
    if not records:
        raise RuntimeError('No environment distribution RECORDs found')
    value = {'schema': 'camp-independent-training-plan.v1', 'status': 'prepared_not_registered',
        'created_utc': utc(), 'preparation_manifest_sha256': PREPARATION_SHA256,
        'python_executable': first['environment']['executable'],
        'preceding_latest_plan_path': str(latest_path), 'preceding_latest_plan_sha256': sha(latest_path),
        'preceding_extension_plan_sha256': sha(EXECUTION / 'extension_plan.json'),
        'execution_code_sha256': {p.name: sha(p) for p in HERE.glob('*.py')},
        'environment_records_sha256': records, 'seeds': seeds,
        'thread_environment': {'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
        'CUDA_VISIBLE_DEVICES': '0',
        'profile_policy': {'actual_adamw_steps_required': 2, 'max_batch_attempts': 32,
            'native_batch_pairs': 24, 'automatic_batch_reduction': False, 'per_seed_fresh_process': True},
        'stage_order': ['profile_seed_1', 'train_seed_1', 'profile_seed_2', 'train_seed_2', 'profile_seed_3', 'train_seed_3'],
        'checkpoint_selection': 'complete final epoch; no test-based selection',
        'profile_use': 'engineering resource evidence only; discard partial model and reinitialize every full run',
        'status_path': str(HERE / 'status.json')}
    destination.parent.mkdir(parents=True, exist_ok=True)
    write(destination, value)
    try:
        validate_execution_plan(destination)
    except BaseException:
        # Keep an invalid preparation for review, never silently overwrite it.
        write(destination.with_suffix('.validation_failure.json'), {'status': 'invalid_preparation', 'traceback': traceback.format_exc()})
        raise
    return {'plan_path': str(destination), 'sha256': sha(destination), 'registered': False, 'gpu_work_started': False}

def predecessor_ready(state, expected_plan_sha256, is_alive):
    if state.get('plan_sha256') != expected_plan_sha256:
        raise RuntimeError('Preceding author queue changed')
    if state.get('status') == FINAL_LATEST_STATUS:
        try:
            check_latest_state(state, expected_plan_sha256, is_alive)
            return True
        except PredecessorBusy:
            return False
    if state.get('status') not in ('waiting_for_registered_extensions', 'running_latest_baselines'):
        raise RuntimeError('Preceding author queue failed or was interrupted')
    if [row.get('id') for row in state.get('jobs', [])] != LATEST_IDS:
        raise RuntimeError('Wrong preceding author job identities')
    if any(row.get('status') == 'failed' or row.get('exit_code', 0) not in (0, None) for row in state['jobs']):
        raise RuntimeError('A preceding author job failed')
    pid, started = state.get('supervisor_pid'), state.get('supervisor_started_utc')
    if not pid or not started or not is_alive(pid, started):
        raise RuntimeError('Preceding author supervisor is missing; inspect any surviving child')
    return False

def command(plan, plan_path, release_path, seed, stage):
    return [plan['python_executable'], '-B', str(HERE / 'run_stage.py'), '--stage', stage,
        '--execution-plan', str(Path(plan_path).resolve()), '--release-file', str(Path(release_path).resolve()), '--seed', str(seed)]

def verify_training(row, execution_plan_path):
    output = Path(row['output_directory'])
    status = read(output / 'status.json')
    if status.get('status') != 'completed' or status.get('epoch_completed') != 1 or status.get('selection') != 'fixed final epoch' or status.get('test_data_read') is not False:
        raise RuntimeError('Frozen trainer did not produce a completed train-only final epoch')
    if sha(output / 'plan.json') != row['plan_sha256']:
        raise RuntimeError('Training output binds a different seed plan')
    original = read(row['plan_path'])
    if sha(output / 'data_manifest.json') != original['data_manifest_sha256']:
        raise RuntimeError('Final training data binding mismatch')
    if read(output / 'code_manifest.json') != original['code_manifest'] or read(output / 'environment_manifest.json') != original['environment']:
        raise RuntimeError('Final source/environment binding mismatch')
    profile_path = Path(row['profile_directory']) / 'profile.json'
    verify_profile(profile_path, row, execution_plan_path)
    if sha(output / 'resource_profile.json') != sha(profile_path):
        raise RuntimeError('Final trainer used a different resource profile')
    evidence = read(output / 'training_evidence.json')
    if evidence.get('actual_adamw_steps', 0) <= 0 or evidence.get('representative_parameter_changed') is not True or evidence.get('all_model_floating_state_finite') is not True:
        raise RuntimeError('No finite changed trained model was recorded')
    if status['actual_adamw_steps'] != evidence['actual_adamw_steps'] or status['optimizer_step_attempts'] != evidence['attempted_batches']:
        raise RuntimeError('Final update counter mismatch')
    if status['amp_skips'] != status['optimizer_step_attempts'] - status['actual_adamw_steps']:
        raise RuntimeError('Final AMP skip accounting mismatch')
    checkpoint_manifest = read(output / 'checkpoint_manifest.json')
    if set(checkpoint_manifest) != {'checkpoint_complete.pth', 'weights_end.pth'}:
        raise RuntimeError('Incomplete final checkpoint set')
    for name, value in checkpoint_manifest.items():
        path = output / name
        if path.stat().st_size != value['bytes'] or sha(path) != value['sha256']:
            raise RuntimeError('Final checkpoint bytes do not match their manifest')
    # Tensor-level complete-vs-weights equivalence is checked by the independent
    # evaluator. This supervisor uses streaming hashes, never imports tensors.
    return {'verified_utc': utc(), 'checkpoint_manifest_sha256': sha(output / 'checkpoint_manifest.json'),
        'training_evidence_sha256': sha(output / 'training_evidence.json'),
        'training_status_sha256': sha(output / 'status.json'), 'checkpoint_files': checkpoint_manifest}

def new_status(plan, plan_path, release_path):
    now = utc()
    return {'schema': 'camp-independent-training-status.v1', 'status': 'waiting_for_latest_baselines',
        'plan_path': str(Path(plan_path).resolve()), 'plan_sha256': sha(plan_path),
        'release_path': str(Path(release_path).resolve()), 'release_sha256': sha(release_path),
        'supervisor_pid': os.getpid(), 'supervisor_started_utc': now, 'started_utc': now,
        'seeds': [{**copy.deepcopy(row), 'status': 'pending', 'exit_code': None,
            'profile_record': {'status': 'pending'}, 'training_record': {'status': 'pending'}} for row in plan['seeds']]}

def supervise(args):
    plan = validate_release(args.plan, args.release_file)
    _, gate, _ = frozen_api()
    status_path = HERE / 'status.json'
    if status_path.exists():
        raise RuntimeError('Existing supervisor evidence must be reviewed; no automatic replay or overwrite')
    with supervisor_lock():
        if status_path.exists():
            raise RuntimeError('Another supervisor already created status')
        state = new_status(plan, args.plan, args.release_file)
        child, active_record, active_seed = None, None, None
        write(status_path, state)
        try:
            while True:
                validate_release(args.plan, args.release_file)
                previous = read(EXECUTION / 'latest_baseline_status.json')
                state.update(heartbeat_utc=utc(), preceding_status=previous.get('status'))
                write(status_path, state)
                if predecessor_ready(previous, plan['preceding_latest_plan_sha256'], gate.alive):
                    state['preceding_completion_sha256'] = sha(EXECUTION / 'latest_baseline_status.json')
                    break
                time.sleep(30)
            state['status'] = 'running'
            logs = HERE / 'logs'
            logs.mkdir(exist_ok=False)
            for row in state['seeds']:
                active_seed = row
                row['status'] = 'running'
                row['started_utc'] = utc()
                for stage in ('profile', 'train'):
                    validate_release(args.plan, args.release_file)
                    if not predecessor_ready(read(EXECUTION / 'latest_baseline_status.json'), plan['preceding_latest_plan_sha256'], gate.alive):
                        raise RuntimeError('Predecessor is no longer released')
                    record = row['profile_record' if stage == 'profile' else 'training_record']
                    active_record = record
                    child = None
                    stdout_path = logs / f'seed_{row["seed"]}_{stage}.stdout.log'
                    stderr_path = logs / f'seed_{row["seed"]}_{stage}.stderr.log'
                    record.update(status='launch_intent', started_utc=utc(),
                        command=command(plan, args.plan, args.release_file, row['seed'], stage),
                        stdout=str(stdout_path), stderr=str(stderr_path))
                    state['active_stage'] = f'{stage}_seed_{row["seed"]}'
                    # Persist launch intent before Popen; a crash never replays a pending fit.
                    write(status_path, state)
                    env = dict(os.environ)
                    env.update(CUDA_VISIBLE_DEVICES=plan['CUDA_VISIBLE_DEVICES'], PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8')
                    env.update(plan['thread_environment'])
                    with stdout_path.open('x', encoding='utf-8') as out, stderr_path.open('x', encoding='utf-8') as err:
                        child = subprocess.Popen(record['command'], cwd=HERE, env=env, stdin=subprocess.DEVNULL,
                            stdout=out, stderr=err, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                        record.update(pid=child.pid, status='running')
                        write(status_path, state)
                        while child.poll() is None:
                            state['heartbeat_utc'] = utc()
                            write(status_path, state)
                            time.sleep(30)
                        exit_code = child.wait()
                    record.update(exit_code=exit_code, finished_utc=utc(),
                        status='completed' if exit_code == 0 else 'failed',
                        stdout_sha256=sha(stdout_path), stderr_sha256=sha(stderr_path))
                    write(status_path, state)
                    if exit_code != 0:
                        raise RuntimeError('Stage failed; batch stays 24 and later seeds are not started')
                    if stage == 'profile':
                        profile_path = Path(row['profile_directory']) / 'profile.json'
                        verify_profile(profile_path, row, args.plan)
                        record.update(profile_path=str(profile_path), profile_sha256=sha(profile_path))
                    else:
                        record['artifact_verification'] = verify_training(row, args.plan)
                    write(status_path, state)
                row.update(status='completed', exit_code=0, finished_utc=utc())
                write(status_path, state)
            validate_release(args.plan, args.release_file)
            state.update(status='completed', exit_code=0, finished_utc=utc())
            state.pop('active_stage', None)
            write(status_path, state)
        except BaseException as error:
            state.update(status='failed', error=repr(error), traceback=traceback.format_exc(), stopped_utc=utc())
            if active_seed is not None:
                active_seed['status'] = 'failed'
                active_seed['exit_code'] = None if child is None else child.poll()
            if child is not None and child.poll() is None:
                state['surviving_child_pid'] = child.pid
                state['surviving_child_started_utc'] = active_record['started_utc']
                state['recovery_note'] = 'Child still runs. Retain its PID/logs; never relaunch until reviewed and exited.'
            write(status_path, state)
            raise

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    prepare_parser = sub.add_parser('prepare')
    prepare_parser.add_argument('--input-directory', type=Path, default=EXECUTION / 'camp_training_inputs')
    prepare_parser.add_argument('--plan', type=Path, default=HERE / 'execution_plan.json')
    run_parser = sub.add_parser('supervise')
    run_parser.add_argument('--plan', type=Path, required=True)
    run_parser.add_argument('--release-file', type=Path, required=True)
    args = parser.parse_args()
    if args.mode == 'prepare':
        import json
        print(json.dumps(prepare(args), ensure_ascii=False))
    else:
        supervise(args)

if __name__ == '__main__':
    main()
