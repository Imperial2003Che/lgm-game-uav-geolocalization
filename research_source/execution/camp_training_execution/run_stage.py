"""Explicit GPU stages. Import and --help are standard-library only.

No stage runs without an external release, immutable plans, fresh predecessor
exit checks and the shared baseline GPU lock. This file is preparation only.
"""
import argparse
from contextlib import contextmanager, redirect_stderr, redirect_stdout
import json
import math
import os
from pathlib import Path
import runpy
import shutil
import sys
import time
import traceback
from types import SimpleNamespace
from unittest.mock import patch
from contracts import (HERE, PREPARATION, frozen_api, latest_gate, read, sha, utc,
                       validate_release, verify_profile, write, write_seed_release)
from contracts import validate_stage_environment

class ProfileComplete(Exception):
    """Only the post-batch observer raises this after two real optimizer steps."""

class ProfileLimit(RuntimeError):
    pass

def profile_decision(actual, attempts, max_attempts=32):
    if not (0 <= actual <= attempts <= max_attempts):
        raise RuntimeError('Invalid actual/attempt optimizer counters')
    if actual >= 2:
        return 'complete'
    if attempts >= max_attempts:
        raise ProfileLimit('Two actual AdamW updates were not reached within 32 original batches')
    return 'continue'

def make_profile_run(runtime, plan, plan_path, profile_path, output, torch_module):
    """Instrument the frozen run, with no altered loss/backward/optimizer math."""
    class ProfileRun(runtime.TrainRun):
        def __init__(self):
            super().__init__(plan, plan_path, profile_path)
            # Only the resource-probe artifact directory differs from a full run.
            self.output = Path(output)
            self.resource_started = time.perf_counter()
            self.previous_batch_time = None
            self.model = None

        def observe_optimizer(self, optimizer, model, scaler):
            self.model = model
            super().observe_optimizer(optimizer, model, scaler)

        def before_epoch(self, epoch, loader):
            super().before_epoch(epoch, loader)
            torch_module.cuda.synchronize()
            self.previous_batch_time = time.perf_counter()

        def after_batch(self, completed_batches):
            super().after_batch(completed_batches)
            # The original trainer has already run scaler.step/update and scheduler.
            torch_module.cuda.synchronize()
            now = time.perf_counter()
            row = {'batch_attempt': completed_batches, 'actual_adamw_steps': self.actual_optimizer_steps,
                'amp_skips': self.amp_skips, 'seconds_including_data_and_synchronization': now - self.previous_batch_time,
                'peak_allocated_bytes': torch_module.cuda.max_memory_allocated(),
                'peak_reserved_bytes': torch_module.cuda.max_memory_reserved(),
                'allocated_bytes': torch_module.cuda.memory_allocated(),
                'reserved_bytes': torch_module.cuda.memory_reserved()}
            self.previous_batch_time = now
            with (self.output / 'resource_batches.jsonl').open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(row, allow_nan=False) + '\n')
            decision = profile_decision(self.actual_optimizer_steps, completed_batches)
            if decision == 'complete':
                raise ProfileComplete()

        def save_complete(self, namespace):
            raise RuntimeError('A bounded resource profile must never save a research checkpoint')

    return ProfileRun()

@contextmanager
def tracked_writers():
    # Deferred import: only inside the allocated GPU stage. Calls/methods are unchanged.
    import torch.utils.tensorboard as tensorboard_module
    original = tensorboard_module.SummaryWriter
    writers = []
    def create(*args, **kwargs):
        writer = original(*args, **kwargs)
        writers.append(writer)
        return writer
    with patch.object(tensorboard_module, 'SummaryWriter', create):
        try:
            yield
        finally:
            for writer in writers:
                writer.close()

def validate_inputs(api, plan):
    # No science import; source, package metadata, original image bytes and order.
    if api.environment() != plan['environment'] or api.code_manifest() != plan['code_manifest']:
        raise RuntimeError('Training code or environment differs from the frozen seed plan')
    if sha(plan['pretrained']['path']) != plan['pretrained']['sha256']:
        raise RuntimeError('Original pretrained bytes changed')
    if sha(plan['data_manifest_path']) != plan['data_manifest_sha256']:
        raise RuntimeError('Original training manifest changed')
    if api.data_manifest(plan['train_root']) != read(plan['data_manifest_path']):
        raise RuntimeError('Training content or official traversal order changed')

def finite_state(torch_module, run):
    model_bad = [name for name, value in run.model.state_dict().items()
                 if value.is_floating_point() and not torch_module.isfinite(value).all().item()]
    optimizer_bad = []
    for index, state in enumerate(run.optimizer.state.values()):
        for name, value in state.items():
            if torch_module.is_tensor(value) and value.is_floating_point() and not torch_module.isfinite(value).all().item():
                optimizer_bad.append(f'{index}:{name}')
    final_digest = run.parameter_digest(run.representative_parameter)
    evidence = {'all_model_floating_state_finite': not model_bad,
        'all_optimizer_floating_state_finite': not optimizer_bad,
        'nonfinite_model_keys': model_bad, 'nonfinite_optimizer_keys': optimizer_bad,
        'representative_parameter': run.representative_name,
        'initial_parameter_sha256': run.initial_parameter_sha256, 'final_parameter_sha256': final_digest,
        'representative_parameter_changed': final_digest != run.initial_parameter_sha256}
    if model_bad or optimizer_bad or not evidence['representative_parameter_changed']:
        write(run.output / 'invalid_update_evidence.json', evidence)
        raise RuntimeError('Profile did not produce finite, changed model/optimizer state')
    return evidence

def resource_profile(args, execution_plan, row, api, gate, runtime):
    output = Path(row['profile_directory'])
    output.mkdir(parents=True, exist_ok=False)
    profile_path = output / 'profile.json'
    seed_plan = read(row['plan_path'])
    run = None
    torch_module = None
    started = utc()
    report = {'schema': 'camp-native-resource-profile.v1', 'status': 'starting',
        'started_utc': started, 'pid': os.getpid(), 'seed': row['seed'],
        'plan_sha256': row['plan_sha256'], 'execution_plan_sha256': sha(args.execution_plan),
        'research_result': False, 'scope': 'bounded native resource measurement only; model discarded',
        'nominal_batch_pairs': 24, 'microbatch_pairs': 24, 'gradient_accumulation': 1,
        'img_size': 384, 'all_official_losses': True, 'mixed_precision': True,
        'max_batch_attempts': 32, 'oom': False, 'exclusive_gpu_allocation': False}
    write(profile_path, report)
    try:
        with (output / 'stdout.log').open('x', encoding='utf-8', buffering=1) as out, (output / 'stderr.log').open('x', encoding='utf-8', buffering=1) as err:
            with redirect_stdout(out), redirect_stderr(err), runtime.no_network():
                validate_inputs(api, seed_plan)
                shutil.copy2(row['plan_path'], output / 'plan.json')
                shutil.copy2(seed_plan['data_manifest_path'], output / 'data_manifest.json')
                write(output / 'environment_manifest.json', api.environment())
                write(output / 'code_manifest.json', seed_plan['code_manifest'])
                release_path = output / 'serial_release.json'
                write_seed_release(row, release_path, args.release_file, execution_plan)
                sys.path.insert(0, seed_plan['source_directory'])
                with gate.exclusive_latest_baseline_lock():
                    # Revalidate after potentially lengthy content hashing and under the shared lock.
                    validate_release(args.execution_plan, args.release_file)
                    report['process_environment'] = validate_stage_environment(execution_plan)
                    outer_proof = latest_gate(execution_plan, gate)
                    original_proof = gate.serial_release_gate(row['plan_path'], release_path)
                    write(output / 'serial_release_gate.json', {'latest_author_queue': outer_proof, 'original_queues': original_proof})
                    report['exclusive_gpu_allocation'] = True
                    api.runtime_environment(output)
                    import torch as torch_module
                    if not torch_module.cuda.is_available() or torch_module.cuda.device_count() != 1:
                        raise RuntimeError('Exactly one visible CUDA device is required')
                    torch_module.cuda.synchronize()
                    torch_module.cuda.reset_peak_memory_stats()
                    free, total = torch_module.cuda.mem_get_info()
                    report['device'] = {'name': torch_module.cuda.get_device_name(), 'initial_free_bytes': free, 'total_bytes': total}
                    report['torch_cpu_threads'] = {'intraop': torch_module.get_num_threads(), 'interop': torch_module.get_num_interop_threads()}
                    run = make_profile_run(runtime, seed_plan, row['plan_path'], profile_path, output, torch_module)
                    reached = False
                    with run.image_boundary(), run.training_observers(), tracked_writers():
                        try:
                            runpy.run_path(str(PREPARATION / 'train_university_train_only.py'), run_name='__main__', init_globals={'CAMP_RUN': run})
                        except ProfileComplete:
                            reached = True
                    if not reached or run.actual_optimizer_steps < 2:
                        raise RuntimeError('Official trainer ended without the required two actual updates')
                    report.update(finite_state(torch_module, run))
                    torch_module.cuda.synchronize()
                    report.update(status='passed', completed_optimizer_amp_steps=run.loader.completed_batches,
                        actual_adamw_steps=run.actual_optimizer_steps, amp_skips=run.amp_skips,
                        losses=run.loss_observations, all_observed_losses_finite=all(math.isfinite(x) for x in run.loss_observations),
                        final_scaler_state=run.scaler.state_dict(),
                        peak_allocated_bytes=torch_module.cuda.max_memory_allocated(),
                        peak_reserved_bytes=torch_module.cuda.max_memory_reserved(),
                        seconds_including_initialization=time.perf_counter() - run.resource_started,
                        research_checkpoint_written=False, finished_utc=utc())
                    report['evidence_sha256'] = {p.name: sha(p) for p in output.iterdir() if p.is_file() and p.name not in ('profile.json', 'stdout.log', 'stderr.log')}
                    write(profile_path, report)
                    verify_profile(profile_path, row, args.execution_plan)
    except BaseException as error:
        with (output / 'failure.log').open('a', encoding='utf-8') as stream:
            traceback.print_exc(file=stream)
        is_oom = 'out of memory' in str(error).lower() or isinstance(error, MemoryError)
        if torch_module is not None:
            is_oom = is_oom or isinstance(error, torch_module.cuda.OutOfMemoryError)
        report.update(status='failed', error=repr(error), oom=is_oom, failed_utc=utc(),
            recovery='Retain all evidence. Stop the queue. Never reduce batch or reuse this model automatically.')
        if run is not None:
            report.update(completed_optimizer_amp_steps=getattr(getattr(run, 'loader', None), 'completed_batches', 0),
                actual_adamw_steps=run.actual_optimizer_steps, amp_skips=run.amp_skips, losses=run.loss_observations)
        if torch_module is not None and torch_module.cuda.is_initialized():
            try:
                report.update(peak_allocated_bytes=torch_module.cuda.max_memory_allocated(), peak_reserved_bytes=torch_module.cuda.max_memory_reserved())
            except Exception as measurement_error:
                report['failure_memory_measurement_error'] = repr(measurement_error)
        write(profile_path, report)
        raise

def full_training(args, execution_plan, row, api, gate):
    profile_path = Path(row['profile_directory']) / 'profile.json'
    verify_profile(profile_path, row, args.execution_plan)
    receipt = Path(row['training_receipt_directory'])
    receipt.mkdir(parents=True, exist_ok=False)
    release_path = receipt / 'serial_release.json'
    write_seed_release(row, release_path, args.release_file, execution_plan)
    original_gate = api.serial_release_gate
    def combined_gate(plan_path, derived_release):
        # Called by the frozen train function while it holds the shared GPU lock,
        # after its own full input validation and BEFORE runtime science imports.
        validate_release(args.execution_plan, args.release_file)
        outer_proof = latest_gate(execution_plan, gate)
        verify_profile(profile_path, row, args.execution_plan)
        proof = original_gate(plan_path, derived_release)
        proof['latest_author_queue'] = outer_proof
        proof['outer_execution_plan_sha256'] = sha(args.execution_plan)
        proof['outer_execution_release_sha256'] = sha(args.release_file)
        proof['process_environment'] = validate_stage_environment(execution_plan)
        return proof
    # Only strengthen a process-local release check; the training implementation
    # and its frozen on-disk files remain unchanged.
    with patch.object(api, 'serial_release_gate', combined_gate):
        api.train(SimpleNamespace(plan=row['plan_path'], profile=str(profile_path),
            profile_sha256=sha(profile_path), release_file=str(release_path)))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=('profile', 'train'), required=True)
    parser.add_argument('--execution-plan', type=Path, required=True)
    parser.add_argument('--release-file', type=Path, required=True)
    parser.add_argument('--seed', type=int, choices=(1, 2, 3), required=True)
    args = parser.parse_args()
    execution_plan = validate_release(args.execution_plan, args.release_file)
    validate_stage_environment(execution_plan)
    row = next(row for row in execution_plan['seeds'] if row['seed'] == args.seed)
    api, gate, runtime = frozen_api()
    # Early fail is cheap; both paths also repeat the check under the GPU lock.
    latest_gate(execution_plan, gate)
    if args.stage == 'profile':
        resource_profile(args, execution_plan, row, api, gate, runtime)
    else:
        full_training(args, execution_plan, row, api, gate)

if __name__ == '__main__':
    main()
