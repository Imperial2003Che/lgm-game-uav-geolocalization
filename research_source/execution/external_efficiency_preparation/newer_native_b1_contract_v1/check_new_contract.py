"""Only new B1 contract controls. Synthetic bytes are never scientific results."""
import copy
import datetime
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import traceback

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('_b1_contract_control', HERE / 'b1_contract.py')
k = importlib.util.module_from_spec(spec)
spec.loader.exec_module(k)
RESULTS = []


def check(name, operation):
    try:
        operation()
        RESULTS.append({'name': name, 'passed': True})
    except BaseException:
        RESULTS.append({'name': name, 'passed': False, 'traceback': traceback.format_exc()})


def rejects(operation):
    try:
        operation()
    except (RuntimeError, ValueError, NotImplementedError, KeyError):
        return
    raise AssertionError('Expected rejection')


def npy(value=1.0, dtype='<f4', shape=(1, 1024), fortran=False):
    header = repr({'descr': dtype, 'fortran_order': fortran, 'shape': shape}).encode('latin1')
    header += b' ' * ((64 - (10 + len(header) + 1) % 64) % 64) + b'\n'
    return b'\x93NUMPY\x01\x00' + struct.pack('<H', len(header)) + header + struct.pack('<1024f', value, *([0.0] * 1023))


def write(path, value):
    raw = value if isinstance(value, bytes) else json.dumps(value).encode()
    path.write_bytes(raw)
    return k.artifact(path)


def fixture(root, method, recipe):
    prepared = {'method': method, 'python': sys.executable,
                'settings': {'batch_size': 16, 'thread_environment': {'OMP_NUM_THREADS': '1'}}}
    prepared_record = write(root / 'prepared.json', prepared)
    _, derived = k.derive_b1_prepared(prepared)
    request = {'method': method, 'seed': 1, 'prepared': prepared_record,
        'source_recipe': recipe, 'derivation': derived,
        'selected_inventory_indices': [0], 'selected_rows': [{'key': 'query.jpg', 'bytes': 3, 'label': 1}],
        'selected_content': [{'key': 'query.jpg', 'bytes': 3, 'sha256': '1' * 64}],
        'seed_binding': {'checkpoints': {'weights_end.pth': {'sha256': '2' * 64},
                                       'checkpoint_complete.pth': {'sha256': '3' * 64}}}}
    proof = {'strict': True, 'assign': True, 'weights_only': True, 'mmap': True, 'seed': 1,
        'complete_and_end_tensors_byte_equal': 395 if method == 'CAMP' else 402,
        'final_checkpoint_sha256': '2' * 64, 'complete_checkpoint_sha256': '3' * 64}
    if method == 'CAMP':
        proof.update(learned_pos_scale_preserved=True, model_factory_author_checkpoint_schema=False)
    else:
        proof.update(three_classifier_heads_and_DSA_projection_retained=True, author_checkpoint_values_loaded=False)
    resultdir = root / method
    resultdir.mkdir()
    candidate = {'schema': 'newer-native-b1-candidate.v1', 'method': method, 'seed': 1,
        'request_canonical_sha256': k.sha(k.canonical(request)), 'source_recipe': recipe, 'derivation': derived,
        'artifacts': {'descriptors.npy': write(resultdir / 'descriptors.npy', npy()),
            'image_content_sha256.jsonl': write(resultdir / 'image_content_sha256.jsonl',
                (json.dumps(request['selected_content'][0]) + '\n').encode()),
            'strict_complete_final_load.json': write(resultdir / 'strict_complete_final_load.json', proof),
            'runtime_actual.json': write(resultdir / 'runtime_actual.json', {'python': sys.executable,
                'thread_environment': prepared['settings']['thread_environment'], 'amp': True,
                'cuda_initialized': True, 'torch_cpu_threads': 1, 'opencv_cpu_threads': 1})}}
    return request, candidate, resultdir


def main():
    recipes = {method: k.source_recipe(method) for method in ('CAMP', 'DAC')}
    check('Pinned original sources read without science imports', lambda: (
        k.require(all(r['encoder_ast_sha256'] for r in recipes.values()), 'AST binding'),
        k.require(not any(n.split('.')[0] in {'torch', 'numpy', 'cv2', 'PIL'} for n in sys.modules), 'Science imported')))
    def derivative():
        p = {'settings': {'batch_size': 16, 'image_size': 384}, 'immutable': {'a': [1]}}
        before = copy.deepcopy(p)
        derived, diff = k.derive_b1_prepared(p)
        assert p == before and derived['settings']['batch_size'] == 1
        assert diff['json_pointer'] == '/settings/batch_size'
        derived['immutable']['a'].append(2)
        assert p == before
    check('Only in-memory batch16 to1 derivative; original unchanged', derivative)
    check('Original batch size mismatch rejects', lambda: rejects(lambda: k.derive_b1_prepared({'settings': {'batch_size': 1}})))
    inventory = [{'key': f'{i}.jpg', 'label': 0, 'bytes': 1} for i in range(4)]
    tasks = [{'name': str(i), 'query_indices': [i % 2], 'gallery_indices': [2, 3]} for i in range(10)]
    check('Ten tasks deduplicate first queries and retain full gallery order', lambda: (
        k.require(k.select_queries(inventory, tasks)[0] == [0, 1], 'Subset order'),
        k.require(all(r['full_gallery_indices'] == [2, 3] for r in k.select_queries(inventory, tasks)[1]), 'Gallery order')))
    bad = copy.deepcopy(tasks); bad[0]['query_indices'] = [False]
    check('Boolean query index rejects', lambda: rejects(lambda: k.select_queries(inventory, bad)))
    bad2 = copy.deepcopy(tasks); bad2[0]['gallery_indices'] = [0, 2]
    check('Query inside gallery rejects', lambda: rejects(lambda: k.select_queries(inventory, bad2)))
    check('Bounded genuine-format float32 synthetic NPY parses', lambda: k.decode_npy_fp32(npy(), 1))
    check('Object dtype rejects', lambda: rejects(lambda: k.decode_npy_fp32(npy(dtype='|O'), 1)))
    check('Wrong descriptor dimension rejects', lambda: rejects(lambda: k.decode_npy_fp32(npy(shape=(1, 512)), 1)))
    check('Fortran order rejects', lambda: rejects(lambda: k.decode_npy_fp32(npy(fortran=True), 1)))
    check('Trailing descriptor payload rejects', lambda: rejects(lambda: k.decode_npy_fp32(npy() + b'x', 1)))
    check('Nonfinite descriptor rejects', lambda: rejects(lambda: k.decode_npy_fp32(npy(float('nan')), 1)))
    check('Non-normalized descriptor rejects', lambda: rejects(lambda: k.decode_npy_fp32(npy(0.0), 1)))
    with tempfile.TemporaryDirectory(prefix='b1-contract-new-only-') as temp:
        root = Path(temp)
        fixtures = {}
        for method in ('CAMP', 'DAC'):
            folder = root / method; folder.mkdir()
            fixtures[method] = fixture(folder, method, recipes[method])
            request, candidate, resultdir = fixtures[method]
            def valid(r=request, c=candidate, d=resultdir):
                result = k.check_candidate_artifacts(r, c, d)
                assert result['candidate_artifact_consistency'] is True
                assert result['independent_execution_proven'] is False
                assert result['measurement_admitted'] is False and result['fresh_gallery_proven'] is False
            check(method + ' synthetic candidate consistency stays non-admitting', valid)
        r, c, d = fixtures['CAMP']
        altered = copy.deepcopy(c); altered['seed'] = 2
        check('Cross-seed candidate rejects', lambda: rejects(lambda: k.check_candidate_artifacts(r, altered, d)))
        altered2 = copy.deepcopy(c); altered2['source_recipe']['encoder_ast_sha256'] = '0' * 64
        check('Encoder AST binding mismatch rejects', lambda: rejects(lambda: k.check_candidate_artifacts(r, altered2, d)))
        altered3 = copy.deepcopy(c); altered3['derivation']['derived'] = 16
        check('Undeclared configuration derivative rejects', lambda: rejects(lambda: k.check_candidate_artifacts(r, altered3, d)))
        old = (d / 'descriptors.npy').read_bytes(); (d / 'descriptors.npy').write_bytes(old + b'corrupt')
        check('Changed descriptor actual SHA rejects', lambda: rejects(lambda: k.check_candidate_artifacts(r, c, d)))
        (d / 'descriptors.npy').write_bytes(old)
        escape = copy.deepcopy(c)
        escape['artifacts']['descriptors.npy'] = write(root / 'elsewhere.npy', old)
        check('Same bytes at different artifact identity rejects', lambda: rejects(lambda: k.check_candidate_artifacts(r, escape, d)))
        # A forged filename, bool, arbitrary array stand-in or candidate cannot
        # unlock the public gate. Parent evidence is never accepted here.
        parent = write(root / 'forged_parent_receipt.json', {'exited': True})
        for name in ('execute_reference', 'admit_reference', 'measure_task_ranking'):
            check(name + ' rejects forged parent proof, caller boolean and array', lambda n=name: rejects(
                lambda: getattr(k, n)(r, c, [1.0], verified=True, parent_proof=parent)))
    report = {'schema': 'newer-native-b1-new-controls.v1', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source': k.artifact(HERE / 'b1_contract.py'), 'control_source': k.artifact(__file__),
        'actual_original_source_recipes': recipes, 'controls': RESULTS,
        'passed': all(r['passed'] for r in RESULTS), 'control_count': len(RESULTS),
        'synthetic_only': True, 'original_encoder_executed': False, 'scientific_imports': [],
        'completed_input_binding_executed': False, 'public_admission': False,
        'old_suite_rerun': False, 'limits': k.LIMITS}
    output = HERE / ('CONTROL_REVIEW_' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S_%f') + '.json')
    with output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False); stream.write('\n')
    print(json.dumps({'report': k.artifact(output), 'passed': report['passed'], 'controls': len(RESULTS)}))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
