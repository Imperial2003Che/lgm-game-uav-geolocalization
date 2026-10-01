"""Bind retained two-job audit and prior owner identity; no scientific imports."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def artifact(path):
    path = Path(path).resolve(strict=True)
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


prior = HERE.parent / 'host_recovery_20260929_0341/OWNER_SNAPSHOT_20260929_050054032.json'
assert artifact(prior)['sha256'] == 'a6f6f19eae3a51ef8f221993052372a772278de3ac9bf6b5457d92416a947b47'
prior_bytes = prior.read_bytes()
with (HERE / 'PRIOR_OWNER_SNAPSHOT.json').open('xb') as stream:
    stream.write(prior_bytes)
history = json.loads(prior_bytes.decode('utf-8-sig'))
pipeline = next(state for state in history['states'] if state['role'] == 'pipeline')
current = json.loads((HERE / 'PROCESS_OBSERVATION.json').read_text(encoding='utf-8-sig'))
actual = {row['pid']: row for row in current['actual']}
for role in ('owner', 'launcher'):
    row = pipeline[role]; now = actual[row['pid']]
    assert str(row['creation_utc_ticks']) == now['creation_utc_ticks']
    assert row['parent'] == now['parent_pid'] and row['command'] == now['command_line']
review = json.loads((HERE / 'REVIEW_FINAL.json').read_text(encoding='utf-8'))
assert review['status'] == 'passed_bounded_data_review_with_figure_editability_limitations'
assert review['scientific_imports'] == []
for binding in review['bindings']:
    snapshot = artifact(binding['snapshot'])
    assert snapshot['sha256'] == binding['sha256'] and snapshot['bytes'] == binding['bytes']
metadata = {'schema': 'bounded-pipeline-two-job-review.v1',
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'status': review['status'], 'files': [artifact(p) for p in sorted(HERE.rglob('*')) if p.is_file()],
    'prior_owner_snapshot_original': artifact(prior),
    'pipeline_owner_launcher_exact_pid_creation_ticks_parent_command_match': True,
    'report_snapshot_binding_checks': len(review['bindings']),
    'whole_pipeline_complete': False, 'fully_native_editable_figure_delivery_complete': False,
    'scientific_execution': False, 'live_files_changed': False}
with (HERE / 'METADATA.json').open('x', encoding='utf-8') as stream:
    json.dump(metadata, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({name: artifact(HERE / name) for name in
    ('REVIEW_FINAL.json', 'review_transition_final.py', 'REVIEW.md', 'METADATA.json')}, indent=2))
