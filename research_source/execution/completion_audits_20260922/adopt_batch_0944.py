"""Root evidence adoption; no scientific imports or repeated checkpoint hashing."""
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXEC = HERE.parent
def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()
def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def need(v, message):
    if not v:
        raise RuntimeError(message)
def rec(p):
    p = Path(p)
    return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
bindings = []
def verify(r):
    p = r.get('snapshot',r.get('path'))
    a = rec(p)
    need(a['sha256'] == r['sha256'] and a['bytes'] == r['bytes'], 'Evidence binding mismatch: '+p)
    bindings.append(a)
    return read(p) if p.endswith('.json') else None

report_path = HERE/'BATCH_COMPLETION_0944.json'
need(sha(report_path) == '2183ab32674d171f0d7ce15ea96b5e72b1990ad7071404e89403108f28f96a25', 'Report changed')
r = read(report_path)
need(r['batch_passed'] and r['requested_new_fit_count'] == r['new_fits_fully_artifact_verified'] == 4, 'Incorrect batch result')
need(r['accepted_total_with_this_bounded_batch'] == r['original_42spec_completion_count_at_audit'] == 36, 'Incorrect total')
need(not r['completed_outside_this_bounded_batch_pending_root_review'] and not r['concrete_identity_findings'], 'Unresolved findings')
need(r['formal_evaluation_manifest_count'] == 0 and not r['scientific_modules'] and not r['torch_checkpoint_loaded'], 'Incorrect scope')
verify(r['review_script'])
prior = verify(r['accepted_baseline_report'])
for b in r['accepted_baseline_independent_reports']:
    verify(b)
need(prior['adopted'] and prior['completed_fit_count'] == 32, 'Unaccepted baseline')
parent = verify(r['parent_status_raw_snapshot'])
ledger = verify(r['ledger_raw_snapshot'])
need(parent['controller_pid'] == 36528, 'Unexpected parent')
need(r['registered_registry_sha256'] == ledger['registered_registry_sha256'] == '49661e3dbe622f99bd7db7e9875f72b2ae4358071804d70336ec5abd61f1c72e', 'Registry mismatch')
for b in r['frozen_sources'].values():
    verify(b)
need(sha(r['source_provenance']['manifest_path']) == r['source_provenance']['manifest_sha256'] == '11de17bd611431e4471eec1b8ac072a2159fbd02e4eb2cb041b4f3b0f00012a1', 'Path provenance mismatch')
new_ids = set()
for row in r['new_runs']:
    new_ids.add(row['run_identifier'])
    m = verify(row['manifest_raw_snapshot'])
    c = verify(row['config_raw_snapshot'])
    h = verify(row['history_raw_snapshot'])
    need(not row['original_training_completion_issues'], 'Original gate failed')
    need(m['status'] == 'completed' and m['epochs_completed'] == 80 and m['best_epoch'] == 79, 'Incomplete manifest')
    need(len(h) == 80 and [x['epoch'] for x in h] == list(range(80)), 'Incomplete history')
    need(c['immutable_config']['optimization']['steps_per_epoch_actual'] == 375 and all(x['optimizer_steps'] == 375 for x in h), 'Steps mismatch')
    need(set(row['artifacts_sha256_verified']) == set(m['artifacts']) == {'best.pt','last.pt','history.json','run_config.json','run.log'}, 'Wrong artifacts')
    for name,b in row['artifacts_sha256_verified'].items():
        need(b['sha256'] == m['artifacts'][name]['sha256'] and b['bytes'] == m['artifacts'][name]['bytes'], 'Manifest/report artifact mismatch')
    event = row['parent_completed_event']
    need(event in parent['events'] and event['status'] == 'completed' and event['exit_code'] == 0, 'Original event mismatch')
need(not new_ids & set(prior['completed_fit_ids']) and set(r['accepted_total_fit_ids']) == new_ids | set(prior['completed_fit_ids']), 'Admission set mismatch')
snap_path = EXEC/'state_write_recovery_20260920_0138/HEARTBEAT_20260922_094412.json'
incident_path = EXEC/'resource_incident_20260922_0945/CAPTURE.json'
snap, incident = read(snap_path), read(incident_path)
need(all(s['same_owner_identity'] for s in snap['states']) and all(p['matches'] for p in snap['pins']), 'Prior root owner or plan mismatch')
need(snap['training_commands_and_parentage_match'], 'Prior active command mismatch')
need(sha(incident_path) == '80392228a125ad6f705ba54f91172013d2c5df9b089a4e769e2496b9eae06747', 'Incident capture changed')
need(incident['old_science_and_controllers_absent'] and not incident['actual_python_processes'], 'Unexpected live owner at capture')
need(incident['active']['status'] == 'failed' and incident['active']['exit_code'] == 1, 'Unexpected sensitivity outcome')
need('formal_sensitivity' in incident['active']['output_dir'], 'Wrong failed run')
need(all('formal_main/' in x for x in r['accepted_total_fit_ids']), 'Completed main fits not exact')
result = {
    'schema':'root-independent-completion-adoption.v1','adopted_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'root_script':rec(__file__),'independent_report':rec(report_path),'verified_small_evidence_bindings':bindings,
    'root_observational_evidence':[rec(snap_path),rec(incident_path)],'latest_incident_note':'First sensitivity training later failed after 24 epochs, all Python processes absent at capture. This does not invalidate the separate 36 completed main fits.',
    'new_completed_fits_adopted':4,'completed_fit_count':36,'completed_fit_ids':r['accepted_total_fit_ids'],'formal_evaluation_count':0,
    'root_read_final_audit_diff_and_report':True,'actual_checkpoint_byte_hashes_verified_by':'Independent bounded audit, not repeated by root',
    'no_scientific_imports_or_live_changes':True,
    'exit_evidence_limit':'Original parent Popen exit0 events plus later PID identity checks; no independent dual Windows handles or interpreter exit code observations.',
    'last_active_run':incident['active']['output_dir'],'last_active_status':'failed','last_active_complete_epochs':24,'adopted':True,
}
output = HERE/'ROOT_BATCH_36_ADOPTION_20260922.json'
with output.open('x',encoding='utf-8') as f:
    json.dump(result,f,ensure_ascii=False,indent=2)
    f.write('\n')
print(json.dumps({'adoption':rec(output),'small_bindings_verified':len(bindings),'fits':36,'formal_evals':0},ensure_ascii=False))
