"""Seal new source preparation; never run a scientific or prior-suite entry."""
import datetime
import difflib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('_b1_seal_contract', HERE / 'b1_contract.py')
k = importlib.util.module_from_spec(spec)
spec.loader.exec_module(k)


def write(name, value):
    with (HERE / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2); stream.write('\n')
    return k.artifact(HERE / name)


def main():
    controls = sorted(HERE.glob('CONTROL_REVIEW_*.json'))
    reports = [k.parse(p.read_bytes()) for p in controls]
    assert len(reports) == 2 and all(r['passed'] and r['control_count'] == 23 for r in reports)
    assert reports[-1]['source'] == k.artifact(HERE / 'b1_contract.py')
    recipes = {method: k.source_recipe(method) for method in ('CAMP', 'DAC')}
    assert recipes == reports[-1]['actual_original_source_recipes']
    pins = [('newer_native_ranking_v1/SOURCE_MANIFEST.json', '6cd6aa011d4c996160adfdf81ad42c9c27692727c4b141bb9b64f6ff56740922'),
            ('newer_native_ranking_v1/ranking_bridge.py', 'd0dca4cf031b312c770c12dc653f5a47577c94e191b1f3ce5c7cb9514195372e'),
            ('newer_native_loader_v1/SOURCE_MANIFEST.json', '1a5c34aac80187bda88eaffd24ba9756399d77b741d928047f40c5b3efe1d7c5')]
    bindings = []
    for rel, expected in pins:
        actual = k.artifact(k.PREPARATION / rel)
        assert actual['sha256'] == expected
        bindings.append(actual)
    adopted = k.artifact(k.EXECUTION / 'efficiency_native_ranking_independent_review_20260929/ROOT_SOURCE_ADOPTION.json')
    assert adopted['sha256'] == '9c1b303896ba12799a83146fa1df0ee71f9a398068edc2c6f538142ab5844ceb'
    bindings.append(adopted)
    full_diff = ''.join(''.join(difflib.unified_diff([], (HERE / name).read_text(encoding='utf-8').splitlines(True),
                        fromfile='/dev/null', tofile=name)) for name in ('b1_contract.py', 'check_new_contract.py', 'README.md', 'seal_preparation.py'))
    with (HERE / 'SOURCE_DIFF.patch').open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(full_diff)
    # Reconstruct the exact first tested bytes and verify them against the
    # retained first report before preserving. This is explicitly a hash-proven
    # reconstruction, not a claim that a pre-edit snapshot was made at the time.
    current = (HERE / 'b1_contract.py').read_text(encoding='utf-8')
    start = current.index('    loader_manifest_record = artifact(expected.parent')
    end = current.index('    require(type(seed) is int', start)
    first = current[:start] + current[end:]
    first = first.replace("        'completion_binder': {'manifest': loader_manifest_record, 'sources': loader_sources},\n", '')
    assert k.sha(first.encode()) == reports[0]['source']['sha256']
    with (HERE / 'INITIAL_CONTROL_SOURCE_RECONSTRUCTED.py').open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(first)
    with (HERE / 'BINDER_PIN_ADDITION.patch').open('x', encoding='utf-8', newline='\n') as stream:
        stream.writelines(difflib.unified_diff(first.splitlines(True), current.splitlines(True),
            fromfile='INITIAL_CONTROL_SOURCE_RECONSTRUCTED.py', tofile='b1_contract.py'))
    write('PREPARATION_REPORT.json', {'schema': 'newer-native-b1-source-preparation.v1',
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'source_preparation_only_public_admission_disabled',
        'source': k.artifact(HERE / 'b1_contract.py'), 'source_recipes': recipes,
        'existing_accepted_source_bindings': bindings, 'control_reports': [k.artifact(p) for p in controls],
        'control_count_distinct': 23, 'control_runs': 2, 'control_failures': 0,
        'second_run_reason': 'After explicit binder/path-alias source pin addition, the 23 new-module controls were repeated, not a minimal affected subset. No new coverage; the added CompletedInputs integration remains static-only.',
        'derivative_seal_limit': 'The copied original prepared payload seal is not valid for the in-memory B1 derivative; use separate original byte SHA plus unique diff/derived canonical digest. Do not submit derivative as unchanged sealed prepared input.',
        'first_tested_source_snapshot': {'record': k.artifact(HERE / 'INITIAL_CONTROL_SOURCE_RECONSTRUCTED.py'),
            'method': 'post-edit exact reconstruction verified against initial report SHA, not an original pre-edit snapshot'},
        'new_capabilities': ['Exact original encode_seed AST/source recipe binding',
            'Future CompletedInputs request builder with unchanged original prepared and single in-memory B1 difference',
            'Frozen ten-task first-query subset and original content-ledger matching',
            'Bounded stdlib B1 descriptor/strict-load/runtime candidate-artifact consistency checks'],
        'not_implemented': ['actual reference executor', 'six fresh reference workers',
            'actual external parent dual-handle process/exit and closed-log collection',
            'predecessor/release/resource/GPU-lock admission', 'fresh complete-gallery encoding and parity',
            'full-dataset online accuracy', 'public ranking admission'],
        'completed_input_binding_executed': False, 'scientific_imports': [], 'model_loaded': False,
        'GPU_executed': False, 'new_scientific_results': False, 'old_suites_rerun': False,
        'active_queue_or_release_modified': False, 'full_t6_complete': False, 'limits': k.LIMITS})
    files = [k.artifact(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name != 'SOURCE_MANIFEST.json']
    manifest = write('SOURCE_MANIFEST.json', {'schema': 'newer-native-b1-source-manifest.v1',
        'status': 'source_preparation_only_not_released_not_registered', 'files': files,
        'public_admission': False, 'full_t6_complete': False})
    print(json.dumps({'manifest': manifest, 'report': k.artifact(HERE / 'PREPARATION_REPORT.json'),
                      'source': k.artifact(HERE / 'b1_contract.py'), 'files': len(files)}))


if __name__ == '__main__':
    main()
