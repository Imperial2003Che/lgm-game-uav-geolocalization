"""CreateNew producer controls/delivery bindings, never rerun any source control."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKER = HERE.parent / 'newer_native_b1_worker_v2'


def bind(path):
    raw = path.read_bytes()
    return {'path': str(path.resolve(strict=True)), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def exact(item):
    if bind(Path(item['path'])) != item:
        raise RuntimeError('Exact producer source/delivery bytes changed')


def main():
    manifest = json.loads((HERE / 'SOURCE_REVIEW_MANIFEST.json').read_bytes())
    for item in manifest['roles'].values():
        exact(item)
    exact(manifest['preserved_source_manifest'])
    exact(manifest['preserved_worker_manifest'])
    exact(manifest['selected_checker_delta'])
    controls = HERE / 'source_controls_v1'
    report = json.loads((controls / 'NEW_SOURCE_CONTROLS.json').read_bytes())
    receipt = json.loads((controls / 'ACTUAL_TOOL_RECEIPT.json').read_bytes())
    if (report['count'] != 50 or len(report['checks']) != 50 or
        not all(item['passed'] is True for item in report['checks']) or
        receipt['chunk_id'] != '0d7034' or receipt['exit_code'] != 0 or
        report['windows_process_api_or_helper_executed'] is not False or
        report['subprocess_or_native_venv_executed'] is not False):
        raise RuntimeError('Single pure-control receipt/report scope differs')
    exact(receipt['reported_artifact'])
    for item in report['source_bindings']:
        exact(item)
    records = [bind(path) for path in sorted(HERE.iterdir()) if path.is_file()]
    records += [bind(path) for path in sorted(WORKER.iterdir()) if path.is_file()]
    records += [bind(path) for path in sorted(controls.iterdir()) if path.is_file()]
    if len({item['path'] for item in records}) != len(records):
        raise RuntimeError('Duplicate producer delivery path')
    value = {'schema': 'newer-native-b1-lifecycle-source-producer-delivery.v1',
             'created_utc': datetime.now(timezone.utc).isoformat(), 'files': records,
             'selected_source_review_manifest': bind(HERE / 'SOURCE_REVIEW_MANIFEST.json'),
             'original_body_byte_derivation': bind(HERE / 'WORKER_BODY_DERIVATION.json'),
             'new_pure_controls': bind(controls / 'NEW_SOURCE_CONTROLS.json'),
             'new_pure_controls_tool_receipt': bind(controls / 'ACTUAL_TOOL_RECEIPT.json'),
             'new_pure_control_count': 50,
             'source_prepared': True, 'source_adopted': False,
             'new_pure_controls_completed_once': True,
             'api_native_scientific_execution': False, 'native_venv_validated': False,
             'execution_released': False, 'immutable_independent_execution_root_implemented': False,
             'independent_execution_proven': False, 'measurement_admitted': False,
             'full_t6_complete': False, 'manuscript_result': False,
             'initial_manifests_kept_historical': True,
             'review_scope': 'Producer source preparation and one new pure metadata/closed-gate control. AI independent static review and root adoption remain separate.'}
    target = HERE / 'DELIVERY.json'
    with target.open('xb') as f:
        f.write(json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8') + b'\n')
        f.flush(); os.fsync(f.fileno())
    print(json.dumps({'delivery': bind(target), 'unique_bindings': len(records),
                      'new_controls': bind(controls / 'NEW_SOURCE_CONTROLS.json')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
