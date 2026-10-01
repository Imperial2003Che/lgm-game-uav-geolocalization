"""Seal v2 source and exact v1 diff without any scientific runtime admission."""
import ast
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import driver_contract as d

def functions(path):
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    return {node.name: ast.dump(node, include_attributes=False) for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}

def main():
    d.no_science_loaded()
    k, b = d.common(), d.adapters()[0]
    prior = HERE.parent / 'external_t1_driver_v1'
    k.require(k.sha(prior / 'SOURCE_MANIFEST.json') == '7100d5f1eb93f4b2803fbc1cf4ef01f64ac75b92ff67539932547de23bec4762', 'Prior seal changed')
    k.require(not (HERE / 'SOURCE_MANIFEST.json').exists(), 'Driver source already sealed')
    old_manifest = k.read(prior / 'SOURCE_MANIFEST.json')
    for item in old_manifest['files']:
        k.verify_record(item)
    expected_changes = {'driver.py': {'allowed_locks', 'shared_gpu_lock', 'run_one'},
        'driver_contract.py': {'prepare', 'verify_plan', 'verify_release', 'read_bound_json'}, 'scientific_worker.py': {'measure_task_sample'}}
    changes = {}
    for filename, expected in expected_changes.items():
        old, new = functions(prior / filename), functions(HERE / filename)
        changed = {name for name in old.keys() | new.keys() if old.get(name) != new.get(name)}
        k.require(changed == expected, 'Unexpected functional diff in ' + filename)
        changes[filename] = {'changed_or_added': sorted(changed), 'unchanged': sorted(old.keys() & new.keys() - changed)}
    diff = {'schema': 'external-t1-driver-v2-diff.v1', 'parent_manifest': k.record(prior / 'SOURCE_MANIFEST.json'),
        'functions': changes, 'all_model_load_and_native_adapter_sources_unchanged': True,
        'native_complete_ranking_function_ast_unchanged': True,
        'full_native_batch_extraction_and_official_metric_calls_unchanged': True,
        'scientific_execution_performed': False}
    k.write_new(HERE / 'SOURCE_DIFF_REVIEW.json', diff)
    review = k.read(HERE / 'STDLIB_REVIEW.json')
    k.require(review['failed'] == 0 and review['scientific_execution_performed'] is False, 'Standard-library checks failed')
    independent_dir = b.E / 'external_t1_driver_review_1923'
    independent = k.read(independent_dir / 'ROOT_V2_RECHECK.json')
    k.require(independent['count'] == 29 and all(row['passed'] for row in independent['checks']), 'Independent review did not pass')
    for path, expected_sha in independent['source_files'].items():
        k.require(k.sha(path) == expected_sha, 'Reviewed v2 runtime source changed')
    k.require(not (HERE / 'preparations').exists() and not (HERE / 'runs').exists(), 'Runtime output exists in source-only preparation')
    files = [*HERE.glob('*.py'), *HERE.glob('STDLIB_REVIEW*.json'), HERE / 'HANDOFF.md', HERE / 'SOURCE_DIFF_REVIEW.json',
        prior / 'SOURCE_MANIFEST.json', b.E / 'dac_training_control_v2' / 'dac2_gates.py',
        b.E / 'camp_preparation' / 'run_camp_author_evaluation.py',
        independent_dir / 'ROOT_V2_RECHECK.json', independent_dir / 'root_review.py']
    files.extend(Path(item['path']) for item in old_manifest['files'])
    files = sorted(set(files), key=lambda x: str(x).casefold())
    k.require(all(x.suffix.lower() not in {'.pt', '.pth', '.ckpt', '.safetensors'} for x in files), 'Weights cannot enter source seal')
    source = {'schema': 'external-t1-native-single-slot-driver-source.v2', 'created_utc': k.now(),
        'parent_v1_manifest': k.record(prior / 'SOURCE_MANIFEST.json'),
        'native_adapter_v2_manifest': k.record(d.ADAPTER / 'SOURCE_MANIFEST.json'),
        'independent_root_review': k.record(independent_dir / 'ROOT_V2_RECHECK.json'),
        'independent_root_checks_passed': independent['count'],
        'files': [k.record(path) for path in files], 'registered_slots': b.slots(),
        'task_count_per_slot': 10, 'seven_slot_task_count': 70,
        'stdlib_checks_passed': review['passed'], 'stdlib_checks_failed': review['failed'],
        'scientific_execution_performed': False, 'scientific_imports': [],
        'actual_checkpoint_bindings_created': 0, 'runtime_plan_created': False, 'active_release_created': False,
        'real_efficiency_samples_measured': 0, 'full_t6_complete': False, 'manuscript_result': False,
        'changes': ['persistent shared first-byte Windows lock; private existence lock remains separate',
            'B1 versus native batch diagnostic arrays instead of exact cross-batch rejection; independent B1-vs-B1 parity remains exact',
            'single-read JSON/raw-byte plan and release records verified through admission and result completion'],
        'implemented': ['real single-slot native worker', 'future seven-slot completed input binding',
            'nine native complete views with exact fingerprints', 'ten official full-gallery six-metric rechecks',
            'four native timing scopes including complete CPU ranking', 'actual parity failure arrays'],
        'not_implemented': ['seven-slot serial supervisor', 'combined primary/external T6 table',
            'CAMP/DAC efficiency', 'full-operation FLOPs', 'full-dataset B1 accuracy', 'actual scientific validation']}
    record = k.write_new(HERE / 'SOURCE_MANIFEST.json', source)
    print(json.dumps({'source_manifest': record, 'source_files': len(source['files']), 'prepared_only': True}))

if __name__ == '__main__':
    main()
