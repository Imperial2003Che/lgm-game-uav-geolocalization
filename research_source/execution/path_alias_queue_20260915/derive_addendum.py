"""Derive a transparent execution addendum; do not alter registered plans."""
from pathlib import Path
import ast
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parent
PLANS = {'latest': ('latest_baseline_plan.json', '80acc8d9eeb2f4fa15b6ff242c0a64acc180edf2386268aa277d55ffe58c6b1e'),
         'independent': ('independent_comparison_plan_v2.json', 'a5318f7a60497cc7c9ccb74b7cd82ef7f71fcb072c36a90fb192ea27acc6ca49')}
ORIGINALS = {'latest': 'supervise_latest_baselines.py', 'independent': 'supervise_independent_comparisons.py'}

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def save_new(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')

def once(source, old, new):
    if source.count(old) != 1:
        raise RuntimeError('Expected one exact replacement: ' + old)
    return source.replace(old, new)

def main():
    registry = {'schema': 'fixed-source-alias-roles.v1', 'plans': {}, 'controllers': {},
                'alias_helper': str(EXECUTION / 'external_efficiency_preparation/newer_native_loader_v1/path_aliases.py'),
                'roles': {'camp_author': {'family': 'latest', 'job_id': 'camp_author_checkpoint_full_gallery_10tasks'},
                          'dac_author': {'family': 'latest', 'job_id': 'dac_author_checkpoint_full_gallery_10tasks'},
                          'camp_independent': {'family': 'independent', 'job_id': 'camp_independent_3seed_full_gallery_30tasks'}}}
    files = {Path(__file__), HERE / 'compatibility.py', HERE / 'run_evaluator.py', Path(registry['alias_helper'])}
    for family, (name, expected) in PLANS.items():
        plan_path = EXECUTION / name
        assert sha(plan_path) == expected
        plan = json.loads(plan_path.read_bytes())
        registry['plans'][family] = {'path': str(plan_path), 'sha256': expected}
        original = EXECUTION / ORIGINALS[family]
        assert sha(original) == plan['controller_sha256']
        target = original.with_name(original.stem + '_path_compat_v1.py')
        registry['controllers'][family] = {'path': str(target), 'original_path': str(original),
                                          'original_sha256': sha(original)}
        source = original.read_text(encoding='utf-8')
        revised = once(source, 'import traceback\n',
            "import traceback\nimport sys\nsys.path.insert(0, str(Path(__file__).resolve().parent / 'path_alias_queue_20260915'))\nimport compatibility as path_compat\n")
        revised = once(revised, 'def check_plan(plan):\n',
            f"def check_plan(plan):\n    path_compat.active().check_plan('{family}', plan, __file__)\n")
        revised = once(revised, "sha(Path(__file__))", f"sha(HERE / '{original.name}')")
        revised = once(revised, "    parser.add_argument('--check-plan', action='store_true')\n",
            "    parser.add_argument('--check-plan', action='store_true')\n    parser.add_argument('--addendum-sha256', required=True)\n")
        revised = once(revised, '    args = parser.parse_args()\n',
            '    args = parser.parse_args()\n    addendum = path_compat.configure(args.addendum_sha256)\n')
        revised = once(revised, '    state.update(supervisor_pid=os.getpid(), supervisor_started_utc=utc())\n',
            f"    state.update(supervisor_pid=os.getpid(), supervisor_started_utc=utc(),\n                 execution_addendum=addendum.evidence('{family}'))\n")
        revised = once(revised, "            job.update(status='running', started_utc=utc())\n",
            f"            job['execution_command'] = addendum.command('{family}', job)\n            job.update(status='running', started_utc=utc())\n")
        revised = once(revised, "subprocess.Popen(job['command'],", "subprocess.Popen(job['execution_command'],")
        if family == 'independent':
            revised = once(revised, "default=HERE / 'independent_comparison_plan.json'", "default=HERE / 'independent_comparison_plan_v2.json'")
        ast.parse(revised)
        with target.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(revised)
        with (HERE / (family + '_controller.patch')).open('x', encoding='utf-8') as stream:
            stream.writelines(difflib.unified_diff(source.splitlines(True), revised.splitlines(True), fromfile=original.name, tofile=target.name))
        files.update((original, target, plan_path))
    registry_path = HERE / 'REGISTRY.json'
    save_new(registry_path, registry)
    files.add(registry_path)
    # The manifest has no future checkpoint/result values and changes no release.
    manifest = {'schema': 'same-file-path-execution-addendum.v1', 'status': 'source_prepared_not_registered_or_launched',
                'registry_sha256': sha(registry_path),
                'purpose': 'Explicit same-file source-path compatibility for three queued evaluation entries',
                'plan_semantics': 'Original plan bytes, registered commands, science and releases remain unchanged. Actual execution_command and this addendum are separately recorded.',
                'files': [{'path': str(p.resolve()), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(files)]}
    save_new(HERE / 'EXECUTION_ADDENDUM.json', manifest)
    print(json.dumps({'manifest_sha256': sha(HERE / 'EXECUTION_ADDENDUM.json'), 'source_count': len(files)}))

if __name__ == '__main__':
    main()
