"""Seal the new source-only bridge and retained control history; stdlib only."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FINAL_SHA = 'd0dca4cf031b312c770c12dc653f5a47577c94e191b1f3ce5c7cb9514195372e'


def artifact(path):
    path = Path(path).resolve(strict=True)
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


source = HERE / 'ranking_bridge.py'
assert artifact(source)['sha256'] == FINAL_SHA
previous = HERE / 'CANDIDATE_3c48574_BEFORE_QUERY_CONTENT_BINDING.py'
assert artifact(previous)['sha256'] == '3c48574f4a94083d32d1e8987e36a3327be813365232286f9ebc8ac2415f6b36'
for name, before, label in (
    ('SOURCE_DIFF.patch', [], '/dev/null'),
    ('FINAL_BINDING_DIFF.patch', previous.read_text(encoding='utf-8').splitlines(True), previous.name),
):
    with (HERE / name).open('x', encoding='utf-8', newline='\n') as stream:
        stream.writelines(difflib.unified_diff(before, source.read_text(encoding='utf-8').splitlines(True),
                                              fromfile=label, tofile='ranking_bridge.py'))
controls = [artifact(HERE / name) for name in ('CONTROL_REVIEW.json', 'CONTROL_REVIEW_FINAL.json',
                                            'CONTROL_REVIEW_BINDING_FINAL.json')]
final = json.loads((HERE / 'CONTROL_REVIEW_BINDING_FINAL.json').read_text(encoding='utf-8'))
assert final['status'] == 'passed' and final['test_count'] == 5 and final['source']['sha256'] == FINAL_SHA
assert final['scientific_imports'] == [] and final['scientific_execution'] is False
parents = {name: artifact(HERE.parent / name / 'SOURCE_MANIFEST.json') for name in (
    'corrected_driver_v3', 'external_t1_adapter_v2', 'external_t1_driver_v2',
    'external_t1_execution_v1', 'newer_native_ops_v1', 'newer_native_loader_v1')}
report = {
    'schema': 'newer-native-ranking-source-preparation.v1',
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'status': 'source_prepared_public_measurement_entry_disabled',
    'source': artifact(source), 'source_diff': artifact(HERE / 'SOURCE_DIFF.patch'),
    'final_binding_diff': artifact(HERE / 'FINAL_BINDING_DIFF.patch'),
    'previous_candidate': artifact(previous), 'existing_manifests': parents,
    'control_reports': controls,
    'control_summary': {'initial': '10 tests, one fixture-injection failure retained',
        'corrected_fixture': '10 passed; runtime candidate unchanged',
        'final': '5 affected-interface tests passed; two regressions plus three new guards',
        'distinct_tests_in_final_test_source': 13, 'earlier_loader_ops_driver_suites_rerun': False},
    'integration': ['strict LoadedSlot and completed same-seed descriptors',
        'fixed first query and complete frozen gallery order',
        'completed original image-content ledger and actual query bytes binding',
        'CPU FP32 full stable ranking and raw native image-to-ranking timing primitives',
        'original helper one-query all-positive rank/AP validation',
        'exclusive closed-file output evidence and failure arrays'],
    'public_entry': 'unconditionally rejects before reading inputs; no caller array/boolean admission',
    'native_protocol': {'CAMP_complete_state_count': 395, 'DAC_complete_state_count': 402,
        'ops_version': 'newer_native_ops_v1', 'loader_version': 'newer_native_loader_v1',
        'batch1_reference': 'independent executor and provenance not yet integrated',
        'gallery': 'completed actual same-seed descriptor artifact, not freshly encoded here'},
    'pending': ['independent original B1 executor and evidence gate', 'six fresh workers',
        'fresh full gallery encoding/parity', 'full-dataset online accuracy',
        'predecessor/resource/release/shared lock admission',
        'actual separate Windows launcher/worker exits and parent closed-stream aggregation',
        'scientific forward/GPU/parity/timing execution', 'independent review and root adoption'],
    'scientific_imports': [], 'scientific_execution': False, 'scientific_process_launches': False,
    'live_or_frozen_files_changed': False, 'queue_registration_changed': False,
    'manuscript_result': False, 'full_T6_complete': False,
    'limitations': 'Source preparation and stdlib symbolic control tests only. No measurement or independent B1 parity accepted.'
}
write(HERE / 'PREPARATION_REPORT.json', report)
files = sorted(path for path in HERE.iterdir() if path.is_file() and path.suffix in {'.py', '.md', '.json', '.patch'})
write(HERE / 'SOURCE_MANIFEST.json', {
    'schema': 'newer-native-ranking-source-manifest.v1',
    'status': 'source_preparation_only_not_registered_not_released',
    'files': [artifact(path) for path in files],
    'runtime_source_sha256': FINAL_SHA,
    'public_measurement_entry_enabled': False, 'scientific_execution': False,
})
print(json.dumps({'report': artifact(HERE / 'PREPARATION_REPORT.json'),
                  'manifest': artifact(HERE / 'SOURCE_MANIFEST.json'),
                  'final_controls': controls[-1]}, indent=2))
