"""Root adoption: verify independent reports and their exact raw evidence bindings.

No scientific imports or repeated weight hashing; actual weights were checked by
the independent bounded audits. Live process identity comes from root CIM capture.
"""
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parent

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def require(value, message):
    if not value:
        raise RuntimeError(message)

def record(path):
    path = Path(path)
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}

verified = {}
def verify_binding(binding):
    path = Path(binding.get('snapshot', binding.get('path')))
    actual = record(path)
    require(actual['bytes'] == binding['bytes'] and actual['sha256'] == binding['sha256'], 'Binding mismatch: '+str(path))
    verified[str(path)] = actual
    return read(path) if path.suffix == '.json' else None

batch_path = HERE/'BATCH_COMPLETION_1611.json'
single_path = HERE/'SUES_VISUAL_CONTENT_SEED2_COMPLETION.json'
require(sha(batch_path) == 'f88259d145316e76b36f63130800f2a47f91c0cbdf863fd9cabb2381bbca0bb2', 'Batch report changed')
require(sha(single_path) == '48987b92b39e9f311fc886b16bc90d007770e693e2fa287908f02dc276220067', 'Single report changed')
batch, single = read(batch_path), read(single_path)
require(batch['batch_passed'] and single['passed'], 'Audit not passed')
require(batch['new_fits_fully_artifact_verified'] == 11 and batch['accepted_total_with_this_bounded_batch'] == 28, 'Wrong batch scope')
require(single['completed_fit_count'] == 29, 'Wrong final count')
require(set(single['completed_fit_ids']) == set(batch['accepted_total_fit_ids']) | {single['run_identifier']}, 'Final ID mismatch')
require(set(batch['completed_outside_this_bounded_batch_pending_root_review']) == {single['run_identifier']}, 'Unreviewed completion remains')
require(not batch['concrete_identity_findings'] and not single['exit_evidence']['old_pid_cim_rows_at_audit'], 'Identity issue')
for report in (batch, single):
    verify_binding(report['review_script'])
    ledger = verify_binding(report['ledger_raw_snapshot'])
    parent = verify_binding(report['parent_status_raw_snapshot'])
    require(parent['controller_pid'] == 36528, 'Unexpected original controller')
    require(report['registered_registry_sha256'] == ledger['registered_registry_sha256'] == '49661e3dbe622f99bd7db7e9875f72b2ae4358071804d70336ec5abd61f1c72e', 'Registry mismatch')
    for binding in report['frozen_sources'].values():
        verify_binding(binding)
    provenance = report['source_provenance']
    require(sha(provenance['manifest_path']) == provenance['manifest_sha256'] == '11de17bd611431e4471eec1b8ac072a2159fbd02e4eb2cb041b4f3b0f00012a1', 'Path adoption mismatch')
    require(report['formal_evaluation_manifest_count'] == 0 and not report['scientific_modules'] and not report['torch_checkpoint_loaded'], 'Wrong evaluation/import claim')
    for row in report.get('new_runs', [report]):
        manifest = verify_binding(row['manifest_raw_snapshot'])
        config = verify_binding(row['config_raw_snapshot'])
        history = verify_binding(row['history_raw_snapshot'])
        require(not row['original_training_completion_issues'], 'Original validator failed')
        require(len(history) == 80 and [h['epoch'] for h in history] == list(range(80)), 'Incomplete history')
        steps = config['immutable_config']['optimization']['steps_per_epoch_actual']
        require(steps in (375, 652) and all(h['optimizer_steps'] == steps for h in history), 'Epoch steps mismatch')
        require(manifest['status'] == 'completed' and manifest['epochs_completed'] == 80, 'Manifest incomplete')
        require(set(row['artifacts_sha256_verified']) == set(manifest['artifacts']) == {'best.pt','last.pt','history.json','run_config.json','run.log'}, 'Artifact inventory mismatch')
        for name, binding in row['artifacts_sha256_verified'].items():
            require(binding['sha256'] == manifest['artifacts'][name]['sha256'] and binding['bytes'] == manifest['artifacts'][name]['bytes'], 'Independent artifact report/manifest mismatch')
        event = row['parent_completed_event']
        require(event in parent['events'] and event['status'] == 'completed' and event['exit_code'] == 0, 'Parent event mismatch')
verify_binding(batch['accepted_baseline_report'])
verify_binding(single['preceding_verified_batch'])
snapshot_path = EXECUTION/'state_write_recovery_20260920_0138/HEARTBEAT_20260921_164212.json'
live = read(snapshot_path)
require(len(live['states']) == 5 and all(s['same_owner_identity'] for s in live['states']), 'Root owner mismatch')
require(live['training_commands_and_parentage_match'] and all(p['same_identity'] for p in live['training_processes']), 'Root science identity mismatch')
require(all(p['matches'] for p in live['pins']), 'Root source/plan mismatch')
result = {
    'schema': 'root-independent-completion-adoption.v1',
    'adopted_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'root_review_script': record(__file__),
    'independent_reports': [record(batch_path), record(single_path)],
    'raw_bindings_and_small_sources_verified': list(verified.values()),
    'root_live_snapshot': record(snapshot_path),
    'new_completed_fits_adopted': 12, 'completed_fit_count': 29,
    'completed_fit_ids': single['completed_fit_ids'], 'formal_evaluation_count': 0,
    'root_read_audit_source_and_report': True,
    'root_repeated_scientific_import_or_weight_hashing': False,
    'actual_weight_sha_evidence': 'Independent audits checked all five artifacts of each of twelve new fits; root checked exact reports and raw bindings.',
    'exit_evidence_limit': 'Original parent Popen exit0 events, plus later PID identity checks. These audits did not independently hold dual Windows worker handles or observe interpreter returncodes.',
    'current_training': {'run': live['active_run'], 'history_rows_at_snapshot': live['current_history_rows'], 'science_processes': live['training_processes']},
    'adopted': True,
}
output = HERE/'ROOT_BATCH_29_ADOPTION_20260921.json'
with output.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'adoption':record(output),'verified_small_bindings':len(verified),'accepted_fit_count':29,'formal_eval':0},ensure_ascii=False))
