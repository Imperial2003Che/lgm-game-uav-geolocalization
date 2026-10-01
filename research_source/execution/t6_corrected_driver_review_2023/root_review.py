"""Independent bounded v3 control review. Real temporary file tests; no science."""
from __future__ import annotations
import ast
import hashlib
import importlib.abc
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

OUT = Path(__file__).resolve().parent
E = OUT.parent
V3 = E / 'external_efficiency_preparation' / 'corrected_driver_v3'
V2 = V3.parent / 'corrected_driver_v2'
FORBIDDEN = {'torch', 'numpy', 'PIL', 'torchvision', 'transformers', 'scipy', 'matplotlib'}
class NoScience(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in FORBIDDEN:
            raise AssertionError('Scientific import forbidden in this review: ' + fullname)
sys.meta_path.insert(0, NoScience())
sys.path.insert(0, str(V3))
import contract as k
import driver as d

checks = []
def check(name, condition):
    checks.append({'name': name, 'passed': bool(condition)})
    if not condition:
        raise AssertionError(name)
def rejects(name, fn, exception=k.GateError):
    try:
        fn()
    except exception:
        check(name, True)
    else:
        check(name, False)
def functions(path):
    return {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(path.read_text(encoding='utf-8-sig')).body if isinstance(n, ast.FunctionDef)}

def main():
    check('Windows actual platform', os.name == 'nt')
    check('v2 source manifest preserved', k.sha(V2 / 'SOURCE_MANIFEST.json') == '59f1c85e6e58541b50aec8054c37ac101b3cf58995e1c565c0abf4b51c0a760e')
    old = k.read(V2 / 'SOURCE_MANIFEST.json')
    check('all 42 v2 source records unchanged', len(old['files']) == 42 and all(k.verify_record(x) for x in old['files']))
    check('all scientific code byte identical', (V3 / 'science.py').read_bytes() == (V2 / 'science.py').read_bytes())
    allowed = {'contract.py': {'read_bound_json', 'verify_plan'}, 'driver.py': {'verify_release', 'acquire_shared_lock', 'release_shared_lock', 'release_own_lock', 'worker', 'run', 'main'}}
    for name, expected in allowed.items():
        before, after = functions(V2 / name), functions(V3 / name)
        diff = {key for key in before.keys() | after.keys() if before.get(key) != after.get(key)}
        check('exact bounded function changes: ' + name, diff == expected)
    check('same four official cases', k.CASES == (('university1652', 'visual'), ('university1652', 'full'), ('sues200', 'visual'), ('sues200', 'full')))
    run_ast = ast.unparse(next(n for n in ast.parse((V3 / 'driver.py').read_text()).body if isinstance(n, ast.FunctionDef) and n.name == 'run'))
    check('four cases and 22 official tasks remain required', 'len(case_results) == 4' in run_ast and 'total_tasks == 22' in run_ast)
    check('no actual runtime plan or run made', not (V3 / 'runs').exists() and not (V3 / 'preparations').exists())
    author = k.read(V3 / 'STDLIB_REVIEW.json')
    check('author 81 standard library checks passed', author['passed'] == 81 and author['failed'] == 0 and author['scientific_execution_performed'] is False)

    with tempfile.TemporaryDirectory(prefix='lgm_primary_v3_independent_') as tmp:
        root = Path(tmp).resolve()
        check('temporary fixtures scoped to OS temp root', root.parent == Path(tempfile.gettempdir()).resolve())
        raw = root / 'raw.json'
        original = '{\r\n  "中文": 1\r\n}\r\n'.encode('utf-8-sig')
        raw.write_bytes(original)
        value, artifact = k.read_bound_json(raw)
        check('UTF8 BOM and CRLF raw object and bytes agree', value == {'中文': 1} and artifact['bytes'] == len(original) and artifact['sha256'] == hashlib.sha256(original).hexdigest())
        original_read = Path.read_bytes
        def changed_after_read(path):
            data = original_read(path)
            if path.resolve() == raw:
                raw.write_bytes(b'{"changed":true}\n')
            return data
        with patch.object(Path, 'read_bytes', changed_after_read):
            rejects('mutation immediately after read rejected', lambda: k.read_bound_json(raw))
        planpath, releasepath = root / 'plan.json', root / 'release.json'
        plan_record = k.write_new(planpath, {'fixture_only': True})
        release_record = k.write_new(releasepath, {'allow_run': True, 'plan': plan_record, 'fixture_only': True})
        value, rr, pr = d.verify_release(releasepath, planpath)
        check('release positive binds initial plan and release artifacts', value['allow_run'] and rr == release_record and pr == plan_record)
        read_bound = k.read_bound_json
        def mutate_release_between_reads(path):
            obj, rec = read_bound(path)
            if Path(path).resolve() == planpath:
                releasepath.write_bytes(b'{"allow_run":false}\n')
            return obj, rec
        with patch.object(k, 'read_bound_json', side_effect=mutate_release_between_reads):
            rejects('release changed during plan read rejected', lambda: d.verify_release(releasepath, planpath))
        rejects('inactive release rejected', lambda: d.verify_release(releasepath, planpath))
        planpath.write_bytes(b'{"changed_plan":true}\n')
        rejects('verify_plan rejects changed captured record before any science', lambda: k.verify_plan(planpath, {}, expected_record=plan_record))

        # Exercise full verify_plan control against explicitly marked local fixture files.
        source = k.write_new(root / 'SOURCE_MANIFEST.json', {'fixture_only': True})
        marker = k.write_new(root / 'fixture_artifact.json', {'fixture_only': True})
        fixed = {'cases': [{'dataset': dataset, 'variant': variant, 'checkpoint': marker, 'files': [marker]} for dataset, variant in k.CASES],
                 'source_manifest': source, 'device_index': 0, 'descriptor_batch_size': 128, 'descriptor_workers': 0,
                 'cache_and_split': [marker], 'predecessors': [marker], 'aggregate_proof': {'fixture_only': True},
                 'clip': {'fixture_only': True}, 'runtime': {'fixture_only': True}}
        fixed['payload_sha256'] = k.canonical(fixed)
        fixedpath = root / 'fixed.json'
        fixed_record = k.write_new(fixedpath, fixed)
        with patch.object(k, 'HERE', root), patch.object(k, 'aggregate_proof', return_value={'fixture_only': True}), patch.object(k, 'verify_snapshot', return_value={'fixture_only': True}), patch.object(k, 'runtime_snapshot', return_value={'fixture_only': True}):
            check('valid complete plan contract accepts same captured bytes', k.verify_plan(fixedpath, {'baseline_runtime': {'fixture_only': True}}, expected_record=fixed_record) == fixed)
            def mutate_after_last_external_check():
                fixedpath.write_bytes(b'{"changed_after_runtime":true}\n')
                return {'fixture_only': True}
            with patch.object(k, 'runtime_snapshot', side_effect=mutate_after_last_external_check):
                rejects('end-of-plan validation detects mid-validation change', lambda: k.verify_plan(fixedpath, {'baseline_runtime': {'fixture_only': True}}, expected_record=fixed_record))

        shared = root / 'persistent_shared.lock'
        shared_bytes = b'prior CAMP/DAC persistent byte lock fixture\r\n'
        shared.write_bytes(shared_bytes)
        shared_record = k.record(shared)
        stream, evidence = d.acquire_shared_lock(shared)
        try:
            check('persistent byte lock protocol declared', evidence['persistent_file_not_deleted'] is True)
            rejects('real Windows competing handle refused', lambda: d.acquire_shared_lock(shared), OSError)
            with patch.object(k, 'HERE', root), patch.object(k, 'verify_record', side_effect=AssertionError('shared bytes must not be hashed')) as hasher:
                rejects('shared path rejected by private cleanup before hash', lambda: d.release_own_lock(shared_record))
                check('shared path had no hash attempt', hasher.call_count == 0)
        finally:
            d.release_shared_lock(stream)
        stream, _ = d.acquire_shared_lock(shared)
        d.release_shared_lock(stream)
        check('unlock and reacquire preserve original bytes and file', shared.read_bytes() == shared_bytes and k.record(shared) == shared_record)
        private = root / 'corrected_primary_gpu.lock'
        private_record = k.write_new(private, {'fixture_only': True})
        with patch.object(k, 'HERE', root):
            d.release_own_lock(private_record)
        check('owned private lease cleanup works', not private.exists())
        changed_private = k.write_new(private, {'fixture_only': True})
        private.write_bytes(b'{"changed_owner":true}\n')
        with patch.object(k, 'HERE', root):
            rejects('changed private lease retained', lambda: d.release_own_lock(changed_private))
        check('changed private lease was not removed', private.exists())
    check('scientific libraries never imported', not FORBIDDEN.intersection(sys.modules))
    report = {'schema': 'independent-primary-v3-bounded-control-review.v1', 'status': 'passed', 'utc': k.now(),
              'checks': checks, 'source_files': {str(V3 / name): k.sha(V3 / name) for name in ('driver.py', 'contract.py', 'science.py')},
              'actual_tests': 'Windows temporary first-byte locks; raw JSON/plan/release mutation checks and unchanged scientific source.',
              'not_performed': ['model import', 'GPU operation', 'runtime prepare', 'active release', 'training', 'scientific timing'],
              'scientific_execution_performed': False, 'author_review': k.record(V3 / 'STDLIB_REVIEW.json')}
    record = k.write_new(OUT / 'ROOT_V3_RECHECK.json', report)
    print(json.dumps({'report': record, 'checks_passed': len(checks)}, ensure_ascii=False))
if __name__ == '__main__':
    main()
