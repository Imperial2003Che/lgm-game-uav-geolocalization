"""Seal source-only worker preparation; never binds checkpoints or admits GPU."""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import driver_contract as d

def main():
    d.no_science_loaded()
    k, b = d.common(), d.adapters()[0]
    k.require(not (HERE / 'SOURCE_MANIFEST.json').exists(), 'Driver source already sealed')
    parent = b.source_manifest()
    review = k.read(HERE / 'STDLIB_REVIEW.json')
    k.require(review['failed'] == 0 and review['scientific_execution_performed'] is False, 'Standard-library checks failed')
    k.require(not (HERE / 'preparations').exists() and not (HERE / 'runs').exists(), 'Source-only preparation created runtime outputs')
    files = [*HERE.glob('*.py'), HERE / 'HANDOFF.md', HERE / 'STDLIB_REVIEW.json',
        HERE / 'STDLIB_REVIEW_INITIAL_63.json', HERE / 'STDLIB_REVIEW_INITIAL_68.json', d.ADAPTER / 'SOURCE_MANIFEST.json']
    files.extend(Path(item['path']) for item in parent['files'])
    files = sorted(set(files), key=lambda x: str(x).casefold())
    k.require(all(x.suffix.lower() not in {'.pt', '.pth', '.ckpt', '.safetensors'} for x in files), 'Scientific weights cannot enter this source-only seal')
    source = {'schema': 'external-t1-native-single-slot-driver-source.v1', 'created_utc': k.now(),
        'native_adapter_v2_manifest': k.record(d.ADAPTER / 'SOURCE_MANIFEST.json'),
        'shared_primary_v2_manifest': k.record(b.V2 / 'SOURCE_MANIFEST.json'),
        'files': [k.record(path) for path in files], 'registered_slots': b.slots(),
        'task_count_per_slot': 10, 'seven_slot_task_count': 70,
        'stdlib_checks_passed': review['passed'], 'stdlib_checks_failed': review['failed'],
        'scientific_execution_performed': False, 'scientific_imports': [],
        'actual_checkpoint_bindings_created': 0, 'runtime_plan_created': False, 'active_release_created': False,
        'real_efficiency_samples_measured': 0, 'full_t6_complete': False, 'manuscript_result': False,
        'implemented': ['real callable single-slot native worker', 'future seven-slot real evidence binding',
            'nine native complete views and exact fingerprints', 'ten official full-gallery six-metric rechecks',
            'four native timing scopes with complete CPU ranking', 'parity failure actual-array persistence'],
        'not_implemented': ['seven-slot serial supervisor', 'combined primary/external T6 table',
            'CAMP/DAC efficiency rows', 'full operation FLOPs', 'full-dataset online B1 accuracy', 'actual scientific validation']}
    record = k.write_new(HERE / 'SOURCE_MANIFEST.json', source)
    print(json.dumps({'source_manifest': record, 'source_files': len(source['files']), 'prepared_only': True}))

if __name__ == '__main__':
    main()
