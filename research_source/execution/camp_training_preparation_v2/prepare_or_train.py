"""Explicit CPU plan creation, followed by separately gated official CAMP training.

No scheduler registration, CUDA probe, model import, or large checkpoint load is
performed by --help, inventory, or make-plan. The train subcommand is GPU work.
"""
import argparse
import ast
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
import importlib.metadata
import importlib
import json
import os
from pathlib import Path
import platform
import runpy
import shutil
import sys
import traceback
from camp_train_runtime import HERE, WEIGHT_URL, TrainRun, no_network, sha_file, write_json
from serial_release import serial_release_gate, exclusive_latest_baseline_lock

def environment():
    return {'executable': str(Path(sys.executable).resolve()), 'python': platform.python_version(),
            'prefix': str(Path(sys.prefix).resolve()), 'platform': platform.platform(),
            'packages': {d.metadata['Name'].lower(): d.version for d in importlib.metadata.distributions()}}

def runtime_environment(output):
    """Verify actual imported module origins/versions before the first CUDA query."""
    mapping = {'torch':'torch', 'torchvision':'torchvision', 'timm':'timm', 'numpy':'numpy',
               'PIL':'pillow', 'cv2':'opencv-python-headless', 'albumentations':'albumentations',
               'sklearn':'scikit-learn', 'transformers':'transformers', 'tensorboard':'tensorboard'}
    report = {}
    for module_name, distribution in mapping.items():
        module = importlib.import_module(module_name)
        origin = Path(module.__file__).resolve()
        if not origin.is_relative_to(Path(sys.prefix).resolve()):
            raise RuntimeError(f'Runtime module escaped the registered environment: {module_name}: {origin}')
        version = str(getattr(module, '__version__', ''))
        if module_name == 'cv2':
            try:
                expected = importlib.metadata.version(distribution)
            except importlib.metadata.PackageNotFoundError:
                distribution = 'opencv-python'
                expected = importlib.metadata.version(distribution)
            consistent = expected == version or expected.startswith(version + '.')
        else:
            expected = importlib.metadata.version(distribution)
            consistent = expected == version
        if not consistent:
            raise RuntimeError(f'Runtime / metadata version mismatch: {module_name}: {version} vs {expected}')
        report[module_name] = {'version': version, 'distribution': distribution,
                               'distribution_version': expected, 'origin': str(origin)}
    write_json(output / 'runtime_environment.json', report)
    return report

def code_manifest():
    pin = json.loads((HERE / 'SOURCE_PIN.json').read_text(encoding='utf-8'))
    source = Path(pin['source_directory'])
    for row in pin['files']:
        if sha_file(source / row['path']) != row['sha256']:
            raise RuntimeError(f'Pinned official source changed: {row["path"]}')
    own = {p.name: sha_file(p) for p in HERE.glob('*.py')}
    own.update({name: sha_file(HERE / name) for name in ('SOURCE_PIN.json', 'official_to_train_only.patch')})
    return {'official_commit': pin['commit_sha'], 'official': pin['files'], 'adapter': own}

def data_manifest(root):
    root = Path(root).resolve()
    if root.name.lower() != 'train' or not root.is_dir():
        raise RuntimeError('--train-root must be the explicit University train directory')
    rows, enumeration = [], {}
    id_sets = []
    for view in ('satellite', 'drone'):
        folder = root / view
        if not folder.is_dir():
            raise RuntimeError(f'Missing train view: {view}')
        ids = [p.name for p in folder.iterdir() if p.is_dir()]
        if len(ids) != 701 or not all(i.isdigit() for i in ids):
            raise RuntimeError('Expected the complete 701-ID University training split')
        id_sets.append(set(ids))
        # Preserve OS traversal order: the official get_data intentionally does not sort files.
        enumeration[view] = []
        for current, dirs, files in os.walk(folder, topdown=False):
            enumeration[view].append({'directory': Path(current).relative_to(root).as_posix(),
                                      'directories': dirs[:], 'files': files[:]})
        for identity in ids:
            files = list((folder / identity).iterdir())
            if not files or (view == 'satellite' and len(files) != 1):
                raise RuntimeError('Each training ID needs one satellite and at least one drone image')
            for image in files:
                if not image.is_file() or not image.resolve().is_relative_to(root) or image.suffix.lower() not in {'.jpg','.jpeg','.png'}:
                    raise RuntimeError(f'Unexpected file in training split: {image}')
                rows.append({'path': image.relative_to(root).as_posix(), 'bytes': image.stat().st_size,
                             'sha256': sha_file(image)})
    if id_sets[0] != id_sets[1]:
        raise RuntimeError('Training identity sets differ between views')
    return {'dataset': 'University-1652', 'split': 'train', 'identity_count': 701,
            'train_root': str(root), 'files': sorted(rows, key=lambda r:r['path']),
            'official_os_walk_order': enumeration}

def configuration_defaults():
    tree = ast.parse((HERE / 'train_university_train_only.py').read_text(encoding='utf-8'))
    output = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'add_argument':
            name = ast.literal_eval(node.args[0]).removeprefix('--')
            default = next(k.value for k in node.keywords if k.arg == 'default')
            output[name] = 0 if name == 'num_workers' else ast.literal_eval(default)
    return json.loads(json.dumps(output))

def make_plan(args):
    output = Path(args.plan).resolve()
    if output.exists():
        raise RuntimeError('A plan is immutable: choose a new path')
    data = json.loads(Path(args.data_manifest).read_text(encoding='utf-8'))
    if data['split'] != 'train' or data['identity_count'] != 701:
        raise RuntimeError('Invalid training data manifest')
    pretrained = Path(args.pretrained).resolve()
    if sha_file(pretrained) != args.pretrained_sha256:
        raise RuntimeError('Pretrained file hash mismatch')
    pin = json.loads((HERE / 'SOURCE_PIN.json').read_text(encoding='utf-8'))
    write_json(output, {'schema_version': 1, 'status': 'prepared_not_registered',
        'created_utc': datetime.now(timezone.utc).isoformat(), 'seed': args.seed,
        'source_directory': pin['source_directory'], 'code_manifest': code_manifest(),
        'train_root': data['train_root'], 'data_manifest_path': str(Path(args.data_manifest).resolve()),
        'data_manifest_sha256': sha_file(args.data_manifest), 'environment': environment(),
        'pretrained': {'path': str(pretrained), 'sha256': args.pretrained_sha256, 'source_url': WEIGHT_URL},
        'official_configuration_defaults': configuration_defaults(),
        'output_directory': str(Path(args.output).resolve()),
        'protocol': {'dataset': 'University-1652', 'epochs': 1, 'nominal_batch_pairs': 24,
                     'microbatch_pairs': 24, 'gradient_accumulation': 1, 'img_size': 384,
                     'mixed_precision': True, 'num_workers': 0, 'seed_selection': 'report every registered seed',
                     'warmup': 'official implementation: 0.1 times pre-shuffle total loader steps',
                     'checkpoint_selection': 'complete final epoch', 'training_test_access': False},
        'execution_gate': 'full 24-pair profile with two official optimizer/AMP steps; external serial GPU allocation'})
    print(json.dumps({'plan': str(output), 'sha256': sha_file(output), 'registered': False}))

def validate_gate(plan, plan_path, profile_path, expected_profile_sha):
    if sha_file(profile_path) != expected_profile_sha:
        raise RuntimeError('Resource profile hash mismatch')
    profile = json.loads(Path(profile_path).read_text(encoding='utf-8'))
    required = {'status': 'passed', 'plan_sha256': sha_file(plan_path), 'nominal_batch_pairs': 24,
                'microbatch_pairs': 24, 'gradient_accumulation': 1, 'img_size': 384,
                'all_official_losses': True, 'mixed_precision': True, 'oom': False,
                'exclusive_gpu_allocation': True}
    for key, value in required.items():
        if profile.get(key) != value:
            raise RuntimeError(f'Resource gate failed: {key}')
    if profile.get('completed_optimizer_amp_steps', 0) < 2:
        raise RuntimeError('Two complete official optimizer/AMP steps are required')
    if profile.get('actual_adamw_steps', 0) < 1:
        raise RuntimeError('The resource profile must include a real AdamW update, not only AMP skips')
    if plan['environment'] != environment() or plan['code_manifest'] != code_manifest():
        raise RuntimeError('Code or environment changed since registration')
    if sha_file(plan['pretrained']['path']) != plan['pretrained']['sha256']:
        raise RuntimeError('Pretrained file changed')
    if sha_file(plan['data_manifest_path']) != plan['data_manifest_sha256']:
        raise RuntimeError('Training manifest changed')
    expected = json.loads(Path(plan['data_manifest_path']).read_text(encoding='utf-8'))
    if data_manifest(plan['train_root']) != expected:
        raise RuntimeError('Training image contents or original traversal order changed')
    return profile

def train(args):
    plan_path = Path(args.plan).resolve()
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    output = Path(plan['output_directory']).resolve()
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'status.json', {'status': 'starting', 'started_utc': datetime.now(timezone.utc).isoformat()})
    try:
        with open(output / 'stdout.log', 'a', encoding='utf-8', buffering=1) as out, open(output / 'stderr.log', 'a', encoding='utf-8', buffering=1) as err:
            with redirect_stdout(out), redirect_stderr(err), no_network():
                # Preflight errors also retain logs; all checks here precede torch import.
                validate_gate(plan, plan_path, args.profile, args.profile_sha256)
                shutil.copy2(plan_path, output / 'plan.json')
                shutil.copy2(args.profile, output / 'resource_profile.json')
                shutil.copy2(plan['data_manifest_path'], output / 'data_manifest.json')
                write_json(output / 'code_manifest.json', plan['code_manifest'])
                write_json(output / 'environment_manifest.json', environment())
                run = TrainRun(plan, plan_path, args.profile)
                sys.dont_write_bytecode = True
                sys.path.insert(0, plan['source_directory'])
                with exclusive_latest_baseline_lock():
                    # Fresh predecessor/PID/nvidia-smi checks, after hashing and before scientific imports.
                    release_proof = serial_release_gate(plan_path, args.release_file)
                    write_json(output / 'serial_release_gate.json', release_proof)
                    shutil.copy2(args.release_file, output / 'serial_release.json')
                    runtime_environment(output)
                    # CUDA is intentionally reached only by this separately gated subcommand.
                    import torch
                    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
                        raise RuntimeError('Registered training requires exactly one visible CUDA GPU')
                    with run.image_boundary(), run.training_observers():
                        runpy.run_path(str(HERE / 'train_university_train_only.py'), run_name='__main__',
                                       init_globals={'CAMP_RUN': run})
                status = json.loads((output / 'status.json').read_text(encoding='utf-8'))
                if status['status'] != 'completed':
                    raise RuntimeError('Training returned without a complete checkpoint')
    except BaseException as error:
        with open(output / 'failure.log', 'a', encoding='utf-8') as stream:
            traceback.print_exc(file=stream)
        write_json(output / 'status.json', {'status': 'failed', 'error': repr(error),
            'failed_utc': datetime.now(timezone.utc).isoformat(), 'partial_epoch_restart_policy':
            'retain failed directory; restart same registered seed from original initialization in a new directory; no automatic batch change'})
        raise

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    inventory = sub.add_parser('inventory', help='CPU stream hashes only; no image/model loading')
    inventory.add_argument('--train-root', required=True)
    inventory.add_argument('--output', required=True)
    plan = sub.add_parser('make-plan', help='CPU-only; no scheduler registration')
    plan.add_argument('--data-manifest', required=True)
    plan.add_argument('--pretrained', required=True)
    plan.add_argument('--pretrained-sha256', required=True)
    plan.add_argument('--seed', type=int, choices=(1,2,3), default=1)
    plan.add_argument('--output', required=True)
    plan.add_argument('--plan', required=True)
    execute = sub.add_parser('train', help='GPU execution; requires separately measured full-batch resource gate')
    execute.add_argument('--plan', required=True)
    execute.add_argument('--profile', required=True)
    execute.add_argument('--profile-sha256', required=True)
    execute.add_argument('--release-file', required=True, help='Later serial allocation bound to this training plan')
    args = parser.parse_args()
    if args.command == 'inventory':
        if Path(args.output).exists():
            raise RuntimeError('Do not overwrite an existing immutable data manifest')
        write_json(args.output, data_manifest(args.train_root))
    elif args.command == 'make-plan':
        make_plan(args)
    else:
        train(args)

if __name__ == '__main__':
    main()
