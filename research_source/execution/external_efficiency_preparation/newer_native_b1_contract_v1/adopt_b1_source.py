"""Root source-only adoption; no candidate imports, no controls or science execution."""
import argparse, datetime, difflib, hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
seen = {}

def bind(path, expected=None):
    p = Path(path).resolve()
    assert p.is_file() and p.stat().st_size < 2_000_000, str(p)
    assert p.suffix.lower() not in ('.pt', '.npz', '.npy'), str(p)
    data = p.read_bytes()
    r = {'path': str(p), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    if expected:
        assert r['sha256'] == expected['sha256'], str(p)
        if 'bytes' in expected: assert r['bytes'] == expected['bytes'], str(p)
    key = str(p).casefold()
    if key in seen: assert seen[key] == r
    seen[key] = r
    return r

def read(path, expected=None):
    bind(path, expected)
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def walk(value):
    if isinstance(value, dict):
        if isinstance(value.get('path'), str) and isinstance(value.get('sha256'), str):
            bind(value['path'], value)
        for child in value.values(): walk(child)
    elif isinstance(value, list):
        for child in value: walk(child)

def main():
    args = argparse.ArgumentParser()
    args.add_argument('--review', required=True)
    args.add_argument('--review-sha', required=True)
    a = args.parse_args()
    manifest = read(HERE / 'SOURCE_MANIFEST.json', {'sha256': '35d7290f2f2f3189390bd45eddf2d6c4ac7378e313b14c9507de2536b997c1a4'})
    report = read(HERE / 'PREPARATION_REPORT.json', {'sha256': '8ef5ce01a47199a6e8671f0df1c209c67d7c59e5ba18e06581e32d58e3893b07'})
    walk(manifest); walk(report)
    assert manifest['public_admission'] is False and manifest['full_t6_complete'] is False
    assert report['control_count_distinct'] == 23 and report['control_runs'] == 2
    assert report['new_scientific_results'] is False and report['completed_input_binding_executed'] is False
    sources = ('b1_contract.py', 'check_new_contract.py', 'README.md', 'seal_preparation.py')
    whole_diff = ''.join(''.join(difflib.unified_diff([], (HERE / n).read_text(encoding='utf-8').splitlines(True), fromfile='/dev/null', tofile=n)) for n in sources)
    assert whole_diff == (HERE / 'SOURCE_DIFF.patch').read_text(encoding='utf-8')
    initial = (HERE / 'INITIAL_CONTROL_SOURCE_RECONSTRUCTED.py').read_text(encoding='utf-8')
    final = (HERE / 'b1_contract.py').read_text(encoding='utf-8')
    patch = ''.join(difflib.unified_diff(initial.splitlines(True), final.splitlines(True), fromfile='INITIAL_CONTROL_SOURCE_RECONSTRUCTED.py', tofile='b1_contract.py'))
    assert patch == (HERE / 'BINDER_PIN_ADDITION.patch').read_text(encoding='utf-8')
    controls = [read(x['path'], x) for x in report['control_reports']]
    for index, c in enumerate(controls):
        # The first report records former bytes at the same source path.
        # Bind them only through the explicitly labelled hash-matched reconstruction.
        walk({key: value for key, value in c.items() if index != 0 or key != 'source'})
        assert c['passed'] is True and c['control_count'] == 23
    assert controls[0]['source']['sha256'] == bind(HERE / 'INITIAL_CONTROL_SOURCE_RECONSTRUCTED.py')['sha256']
    assert controls[1]['source'] == bind(HERE / 'b1_contract.py')
    assert controls[0]['source']['sha256'] != controls[1]['source']['sha256']
    review = read(a.review, {'sha256': a.review_sha})
    walk(review)
    assert review['verdict'] == 'no_blocking_defect_for_source_preparation_only'
    assert review['scientific_acceptance'] is False and review['registration_or_execution_admitted'] is False
    bind(__file__)
    output = {'schema': 'root-b1-source-only-adoption.v1', 'time': datetime.datetime.now().astimezone().isoformat(),
        'accepted_scope': 'source preparation only; no independent execution or measurement admission',
        'root_review': 'Read final source and control source, complete binder increment, README, sealer, preparation and independent static report; rebuilt whole source diff from the four read source files and checked exact equality.',
        'independent_static_review': bind(a.review), 'bindings': list(seen.values()), 'unique_files': len(seen),
        'control_history': {'distinct': 23, 'executions': 2, 'second_execution_repeated_all_new_controls': True, 'adds_coverage': False, 'root_reran_controls': False, 'initial_source_is_post_edit_hash_verified_reconstruction': True},
        'source_preparation_adopted': True, 'execution_released': False, 'full_t6_complete': False,
        'completed_input_binding_executed': False, 'new_scientific_results': False, 'public_admission': False,
        'active_queue_modified': False, 'limits': report['limits'], 'not_implemented': report['not_implemented']}
    p = HERE / 'ROOT_SOURCE_ADOPTION.json'
    with p.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(output, f, ensure_ascii=False, indent=2); f.write('\n')
    print(json.dumps({'adoption': bind(p), 'unique_files_checked': output['unique_files']}, ensure_ascii=False))

if __name__ == '__main__': main()
