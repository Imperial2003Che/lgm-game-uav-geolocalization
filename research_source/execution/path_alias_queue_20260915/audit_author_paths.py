"""Read actual frozen author-evaluation sources without model/scientific imports."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parent
sys.path.insert(0, str(EXECUTION / 'external_efficiency_preparation/newer_native_loader_v1'))
from path_aliases import compare_evidence

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def main():
    plan_path = EXECUTION / 'latest_baseline_plan.json'
    assert sha(plan_path) == '80acc8d9eeb2f4fa15b6ff242c0a64acc180edf2386268aa277d55ffe58c6b1e'
    plan = json.loads(plan_path.read_bytes())
    rows = []
    for job in plan['jobs']:
        command = job['command']
        source = next(Path(x) for x in command if x.endswith('.py'))
        assert sha(source) == job['source_sha256'][str(source.resolve())]
        prepared_path = Path(command[command.index('--prepared') + 1])
        assert sha(prepared_path) == job['source_sha256'][str(prepared_path.resolve())]
        spec = importlib.util.spec_from_file_location('audit_' + job['id'], source)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        prepared = module.load(prepared_path)
        module.verify_seal(prepared)
        actual = module.verify_sources()
        aliases = compare_evidence(prepared['sources'], actual)
        rows.append({'id': job['id'], 'prepared_path': str(prepared_path),
                     'prepared_sha256': sha(prepared_path), 'original_equal': actual == prepared['sources'],
                     'aliases': aliases})
    scientific = [n for n in sys.modules if n.split('.')[0] in {'torch', 'numpy', 'cv2', 'timm', 'PIL', 'albumentations'}]
    assert not scientific
    result = {'scope': 'Actual author prepared/source comparison; standard library only', 'jobs': rows,
              'scientific_modules_imported': scientific, 'queue_changed': False}
    output = HERE / 'ACTUAL_AUTHOR_PATH_AUDIT.json'
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'report': str(output), 'sha256': sha(output),
                      'alias_counts': {r['id']: len(r['aliases']) for r in rows}}))

if __name__ == '__main__':
    main()
