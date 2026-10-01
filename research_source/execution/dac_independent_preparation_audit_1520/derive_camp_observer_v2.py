"""Verified byte-copy and one-call observer repair; no scientific imports."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parent
OLD = EXECUTION / 'camp_training_preparation'
NEW = EXECUTION / 'camp_training_preparation_v2'
EXPECTED = '61f4eacc883421c08a5accd32c58c51c3a1a2287bcd5b146c1f1f270abd6b8fd'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    old_manifest = OLD / 'PREPARATION_MANIFEST.json'
    assert sha(old_manifest) == EXPECTED
    manifest = json.loads(old_manifest.read_text(encoding='utf-8'))
    assert len(manifest['files']) == 18
    for row in manifest['files']:
        path = OLD / row['path']
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], row['path']
    NEW.mkdir(exist_ok=False)
    for row in manifest['files']:
        shutil.copy2(OLD / row['path'], NEW / row['path'])
        assert sha(NEW / row['path']) == row['sha256']
    runtime = NEW / 'camp_train_runtime.py'
    before = runtime.read_bytes()
    old_call = b'return super().update(val, n)'
    new_call = b'return super().update(val)'
    assert before.count(old_call) == 1
    runtime.write_bytes(before.replace(old_call, new_call))
    patch = ''.join(difflib.unified_diff(before.decode('utf-8').splitlines(True),
        runtime.read_bytes().decode('utf-8').splitlines(True),
        fromfile='camp_training_preparation/camp_train_runtime.py',
        tofile='camp_training_preparation_v2/camp_train_runtime.py'))
    (HERE / 'camp_observer_v2.patch').write_text(patch, encoding='utf-8', newline='')
    rows = []
    for row in manifest['files']:
        p = NEW / row['path']
        rows.append({'path': row['path'], 'bytes': p.stat().st_size,
                     'sha256': sha(p), 'old_sha256': row['sha256'],
                     'byte_identical_to_v1': sha(p) == row['sha256']})
    changed = [r['path'] for r in rows if not r['byte_identical_to_v1']]
    assert changed == ['camp_train_runtime.py']
    record = {'created_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'derived_not_sealed_not_registered',
        'original_preparation': str(OLD), 'new_preparation': str(NEW),
        'original_manifest_sha256': EXPECTED, 'files': rows,
        'only_change': 'ObservedAverageMeter forwards val only to the exact official AverageMeter.update(self, val).',
        'patch_sha256': sha(HERE / 'camp_observer_v2.patch'),
        'scientific_imports': [], 'training': False, 'queue_registration': False,
        'changed_original_files': []}
    (HERE / 'CAMP_V2_DERIVATION.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(json.dumps({'directory': str(NEW), 'changed': changed, 'runtime_sha256': sha(runtime)}))

if __name__ == '__main__':
    main()
