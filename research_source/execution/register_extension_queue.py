"""Register reviewed extension entry points without starting any experiment."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724')
PYTHON = Path(r'C:\项目\.venvs\lgm-baselines\Scripts\python.exe')
U = Path(r'C:\项目\IMTMN\datasets\University-1652')
S = Path(r'C:\项目\IMTMN\datasets\SUES-200')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check_analysis_runtime(snapshot):
    """Require the original model stack plus separately prepared analysis extras."""
    versions = {name.lower().replace('_', '-'): version for name, version in snapshot['distributions']}
    expected = {'numpy': '2.4.4', 'pillow': '12.2.0', 'torch': '2.11.0+cu126', 'torchvision': '0.26.0+cu126'}
    errors = [f'{name}={versions.get(name)!r}; required {version}' for name, version in expected.items() if versions.get(name) != version]
    errors += ['missing ' + name for name in ('scikit-learn', 'scipy', 'matplotlib') if name not in versions]
    if errors:
        raise RuntimeError('Prepare an isolated analysis interpreter cloned from the original baseline environment; do not modify the training environment. ' + '; '.join(errors))


def build_plan(t1_job=None, analysis_python=None):
    """Prepare an in-memory plan; this function never registers or starts it."""
    jobs = []
    pin_path = HERE / 'heldout_evaluation/frozen_source_pins.json'
    pins = json.loads(pin_path.read_text(encoding='utf-8-sig'))
    original_sources = [ROOT / relative for relative in pins['files']]
    for relative, record in pins['files'].items():
        if sha(ROOT / relative) != record['sha256']:
            raise RuntimeError('Original source differs from reviewed pins: ' + relative)

    def add(name, script, arguments, dependencies=(), python=PYTHON):
        paths = [script, *dependencies]
        jobs.append({'id': name, 'command': [str(python), str(script), *map(str, arguments)],
                     'cwd': str(ROOT), 'source_sha256': {str(p.resolve()): sha(p) for p in paths}})

    add('real_model_visualizations', HERE / 'make_real_model_visualizations.py', ['--device', 'cuda', '--batch-size', '16'],
        [*original_sources, Path(r'C:\Windows\Fonts\arial.ttf'), Path(r'C:\Windows\Fonts\arialbd.ttf')],
        python=Path(analysis_python).resolve() if analysis_python else PYTHON)
    common = ['--delivery-root', ROOT, '--university-root', U, '--sues-root', S, '--python', PYTHON]
    add('heldout_height_training', ROOT / 'lgm_game_pytorch/experiments/run_transactions_t2_heldout_matrix.py',
        [*common, '--stage', 'train'], original_sources)
    add('heldout_and_seen_height_evaluation', HERE / 'heldout_evaluation/run_heldout_evaluation.py',
        [*common, '--stage', 'evaluate', '--scope', 'all', '--device', 'cuda:0', '--workers', '0'],
        [pin_path, *original_sources])
    remaining = [
        'Manual render/caption review of the actual model figures; incorporate actual formal, transfer, robustness and heldout results in the manuscript',
        'CAMP/DAC independent full-paper-recipe comparisons: complete isolated adapters, environment and training registration before execution',
        'Complete external-baseline efficiency comparison and table integration',
        'Recompile final manuscript and upload a new verified Overleaf project after login',
    ]
    if t1_job:
        jobs.append(json.loads(Path(t1_job).read_text(encoding='utf-8-sig')))
    else:
        remaining.insert(0, 'T1 resource profiling and seven baseline fits/70 evaluations: finish compatible source registration and append a separately registered queue')
    from supervise_extensions import check_plan, runtime_snapshot
    runtime_cache = {}
    for job in jobs:
        python = str(Path(job['command'][0]).resolve())
        if python not in runtime_cache:
            runtime_cache[python] = runtime_snapshot(python)
        job.setdefault('runtime_snapshot', runtime_cache[python])
        if job['id'] == 'real_model_visualizations':
            check_analysis_runtime(job['runtime_snapshot'])
    plan = {'schema': 'lgm-extension-queue.v1',
            'controller_sha256': sha(HERE / 'supervise_extensions.py'),
            'registration_script_sha256': sha(Path(__file__)),
            'registered_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'preceding_status_required': 'ready_for_extension_preparation',
            'status': 'registered_not_executed', 'jobs': jobs, 'remaining_work': remaining,
            'selection_rule': 'All predeclared fits and all protocol tasks, final epoch checkpoints; no target-test selection',
            'scope_note': 'T2 includes 24 fits and 192 tasks. The 48 heldout and 144 seen-height task results are labelled separately.'}
    check_plan(plan)
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--t1-job', type=Path, help='Reviewed JSON job specification including command and source_sha256')
    parser.add_argument('--analysis-python', type=Path, help='Isolated original-version model environment with scikit-learn, scipy and matplotlib; required when baseline environment lacks analysis extras')
    args = parser.parse_args()
    destination = HERE / 'extension_plan.json'
    if destination.exists() or (HERE / 'extension_status.json').exists():
        raise RuntimeError('Existing registered queue must be inspected; refusing replacement')
    plan = build_plan(args.t1_job, args.analysis_python)
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(plan, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'status': 'registered_not_executed', 'plan_path': str(destination),
                      'plan_sha256': sha(destination), 'jobs': [x['id'] for x in plan['jobs']]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
