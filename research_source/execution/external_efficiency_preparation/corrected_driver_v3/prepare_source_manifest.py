"""Seal the bounded v3 control repair after independent review; stdlib only."""
import argparse
import ast
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import contract as k

def functions(path):
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    return {node.name: ast.dump(node, include_attributes=False) for node in tree.body if isinstance(node, ast.FunctionDef)}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', type=Path, required=True)
    args = parser.parse_args()
    prior = HERE.parent / 'corrected_driver_v2'
    k.require(k.sha(prior / 'SOURCE_MANIFEST.json') == '59f1c85e6e58541b50aec8054c37ac101b3cf58995e1c565c0abf4b51c0a760e', 'Prior v2 seal changed')
    k.require(not (HERE / 'SOURCE_MANIFEST.json').exists(), 'V3 source already sealed')
    old = k.read(prior / 'SOURCE_MANIFEST.json')
    for item in old['files']:
        k.verify_record(item)
    k.require((HERE / 'science.py').read_bytes() == (prior / 'science.py').read_bytes(), 'Scientific source bytes changed')
    changed = {}
    expected = {'contract.py': {'read_bound_json', 'verify_plan'},
        'driver.py': {'verify_release', 'acquire_shared_lock', 'release_shared_lock', 'release_own_lock', 'worker', 'run', 'main'}}
    for name, allowed in expected.items():
        before, after = functions(prior / name), functions(HERE / name)
        actual = {key for key in before.keys() | after.keys() if before.get(key) != after.get(key)}
        k.require(actual == allowed, 'Unexpected functional change in ' + name)
        changed[name] = sorted(actual)
    review = k.read(args.review)
    k.require(review.get('status') == 'passed' and review['checks'] and all(x['passed'] for x in review['checks']), 'Independent review failed')
    for path, expected_sha in review.get('source_files', {}).items():
        k.require(k.sha(path) == expected_sha, 'Reviewed source changed')
    checks = k.read(HERE / 'STDLIB_REVIEW.json')
    k.require(checks['failed'] == 0 and checks['scientific_execution_performed'] is False, 'Stdlib review failed')
    k.require(not any(n in sys.modules for n in ('torch', 'numpy', 'PIL', 'transformers', 'torchvision', 'scipy')), 'Scientific module imported')
    k.require(not (HERE / 'runs').exists() and not (HERE / 'preparations').exists(), 'Runtime outputs created during source preparation')
    diff = {'schema': 'corrected-primary-v3-control-diff.v1', 'parent_manifest': k.record(prior / 'SOURCE_MANIFEST.json'),
        'function_changes': changed, 'science_exact_byte_equal': True, 'science_sha256': k.sha(HERE / 'science.py'),
        'unchanged': ['all science.py', 'contract numerical/resource/PID/prepare functions', 'four case registry and 22 task scope'],
        'execution_performed': False}
    k.write_new(HERE / 'SOURCE_DIFF_REVIEW.json', diff)
    files = [*HERE.glob('*.py'), *HERE.glob('STDLIB_REVIEW*.json'), HERE / 'HANDOFF.md', HERE / 'SOURCE_DIFF_REVIEW.json',
        prior / 'SOURCE_MANIFEST.json', k.E / 'dac_training_control_v2' / 'dac2_gates.py',
        k.E / 'camp_preparation' / 'run_camp_author_evaluation.py', args.review, *args.review.parent.glob('*.py')]
    files.extend(Path(item['path']) for item in old['files'])
    files = sorted(set(path.resolve() for path in files), key=lambda x: str(x).casefold())
    k.require(all(p.suffix.lower() not in {'.pt', '.pth', '.ckpt', '.safetensors'} for p in files), 'Tensor payload in source-only seal')
    result = {'schema': 'corrected-primary-t6-source-preparation.v3', 'created_utc': k.now(),
        'parent_v2_manifest': k.record(prior / 'SOURCE_MANIFEST.json'),
        'independent_review': k.record(args.review), 'independent_checks_passed': len(review['checks']),
        'files': [k.record(path) for path in files], 'pipeline_jobs': old['pipeline_jobs'], 'baseline_runtime': old['baseline_runtime'],
        'stdlib_checks_passed': checks['passed'], 'execution_performed': False, 'scientific_imports': [],
        'driver_prepared_plan_created': False, 'release_created': False, 'registered_in_any_queue': False,
        'full_t6_complete': False, 'completed_scope': 'bounded shared-byte-lock/lease and same-raw plan-release source repair',
        'science_source_byte_identical_to_v2': True, 'external_efficiency_rows_implemented': 0,
        'missing_full_t6': old['missing_full_t6']}
    record = k.write_new(HERE / 'SOURCE_MANIFEST.json', result)
    print(json.dumps({'source_manifest': record, 'files': len(files), 'prepared_only': True}))

if __name__ == '__main__':
    main()
