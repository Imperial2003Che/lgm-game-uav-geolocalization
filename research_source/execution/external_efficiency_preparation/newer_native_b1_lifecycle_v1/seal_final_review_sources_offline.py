"""CreateNew final source review addendum; preserve both initial manifests."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKER = HERE.parent / 'newer_native_b1_worker_v2'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def put(path, raw):
    with path.open('xb') as f:
        f.write(raw); f.flush(); os.fsync(f.fileno())


def descriptor(path):
    raw = path.read_bytes()
    return {'path': str(path.resolve(strict=True)), 'bytes': len(raw), 'sha256': sha(raw)}


def main():
    old = HERE / 'evidence_contract.py'
    new = HERE / 'evidence_contract_v2.py'
    raw = b''.join(difflib.diff_bytes(difflib.unified_diff,
        old.read_bytes().splitlines(keepends=True), new.read_bytes().splitlines(keepends=True),
        fromfile=str(old).encode('utf-8'), tofile=str(new).encode('utf-8')))
    put(HERE / 'COMPLETE_EVIDENCE_V1_TO_V2.patch', raw)
    roles = {'native_lifecycle': HERE / 'native_lifecycle.py',
             'selected_reference_checker': new, 'preserved_initial_reference_checker': old,
             'new_worker': WORKER / 'reference_worker.py',
             'not_yet_executed_new_controls': HERE / 'check_new_source_controls.py',
             'review_addendum': HERE / 'SOURCE_REVIEW_ADDENDUM.md',
             'final_offline_sealer': Path(__file__).resolve()}
    value = {'schema': 'newer-native-b1-final-source-review-manifest.v1',
             'created_utc': datetime.now(timezone.utc).isoformat(),
             'roles': {name: descriptor(path) for name, path in roles.items()},
             'preserved_source_manifest': descriptor(HERE / 'SOURCE_MANIFEST.json'),
             'preserved_worker_manifest': descriptor(WORKER / 'SOURCE_MANIFEST.json'),
             'selected_checker_delta': descriptor(HERE / 'COMPLETE_EVIDENCE_V1_TO_V2.patch'),
             'source_prepared': True, 'source_adopted': False,
             'execution_released': False, 'native_venv_validated': False,
             'new_synthetic_controls_yet_executed': False,
             'original_modules_process_apis_scientific_executed': False,
             'immutable_execution_root_implemented': False,
             'independent_execution_proven': False, 'measurement_admitted': False,
             'full_t6_complete': False, 'manuscript_result': False,
             'earlier_manifest_fields_kept_as_historical_publication': True}
    put(HERE / 'SOURCE_REVIEW_MANIFEST.json', json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8') + b'\n')
    print(json.dumps({'manifest': descriptor(HERE / 'SOURCE_REVIEW_MANIFEST.json'),
                      'sources': value['roles'], 'delta': value['selected_checker_delta']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
