"""Seal the reviewed source preparation only; never prepare actual experiment inputs."""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import execution_contract as c
native, k, b, life = c.runtime_helpers()
reviews = HERE.parents[1] / 'external_t1_execution_review_2023'
report_paths = [reviews / 'CONTROL_REVIEW.json', reviews / 'PARENT_FLOW_REVIEW.json']
assert not (HERE / 'SOURCE_MANIFEST.json').exists()
assert not (HERE / 'runs').exists()
assert not any(x in sys.modules for x in ('torch', 'numpy', 'PIL', 'torchvision', 'transformers', 'scipy', 'matplotlib'))
count = 0
for path in report_paths:
    report = k.read(path)
    assert report['status'] == 'passed' and report['checks'] and all(x['passed'] for x in report['checks'])
    for source, digest in report['source_files'].items(): assert k.sha(source) == digest
    count += len(report['checks'])
assert count == 66
frozen = native.verify_sources()
files = {Path(x['path']).resolve() for x in frozen['files']}
files.add((c.NATIVE / 'SOURCE_MANIFEST.json').resolve())
files.update((c.LIFETIME / name).resolve() for name in c.LIFETIME_PINS)
files.update(p.resolve() for p in HERE.glob('*.py'))
files.add((HERE / 'HANDOFF.md').resolve())
files.update(p.resolve() for p in report_paths)
files.update(p.resolve() for p in reviews.glob('*.py'))
assert not any(p.suffix.lower() in {'.pt', '.pth', '.npz', '.npy', '.safetensors'} for p in files)
value = {'schema': 'external-t1-seven-slot-execution-source.v1', 'created_utc': k.now(),
    'files': [k.record(p) for p in sorted(files)], 'independent_checks_passed': count,
    'reviews': [k.record(p) for p in report_paths], 'frozen_native_source_manifest': k.record(c.NATIVE / 'SOURCE_MANIFEST.json'),
    'ordered_registry': b.slots(), 'official_tasks_per_slot': list(b.EXPECTED_TASKS),
    'scientific_execution_performed': False, 'actual_checkpoints_bound': False,
    'actual_native_plan_prepared': False, 'active_release_created': False, 'registered_in_any_queue': False,
    'full_t6_complete': False, 'CAMP_DAC_efficiency_included': False,
    'actual_windows_lifetime_smoke': 'separate venv launcher and actual worker, retained handles observed exit0 and controlled exit7',
    'parent_flow_test_scope': 'actual launch_slot control with explicit stdlib subprocess/resource stubs',
    'final_acceptor_requirement': 'observe this serial parent exit0 before final T6 acceptance'}
record = k.write_new(HERE / 'SOURCE_MANIFEST.json', value)
print(json.dumps({'source_manifest': record, 'source_files': len(files), 'checks_passed': count}, ensure_ascii=True))
