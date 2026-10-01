"""Seal the independently checked one-call repair; never register a queue."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parent
OLD = EXECUTION/'camp_training_preparation'
NEW = EXECUTION/'camp_training_preparation_v2'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    destination = NEW/'PREPARATION_MANIFEST.json'
    if destination.exists():
        raise RuntimeError('The derived preparation manifest is immutable')
    old = json.loads((OLD/'PREPARATION_MANIFEST.json').read_text(encoding='utf-8'))
    review = json.loads((HERE/'CAMP_V2_OBSERVER_REVIEW.json').read_text(encoding='utf-8'))
    assert review['status'] == 'passed' and review['check_count'] == 17
    assert review['runtime_sha256'] == sha(NEW/'camp_train_runtime.py')
    assert sha(OLD/'PREPARATION_MANIFEST.json') == '61f4eacc883421c08a5accd32c58c51c3a1a2287bcd5b146c1f1f270abd6b8fd'
    rows=[]
    for row in old['files']:
        assert sha(OLD/row['path']) == row['sha256']
        path=NEW/row['path']
        rows.append({'path':row['path'],'bytes':path.stat().st_size,'sha256':sha(path)})
    assert [row['path'] for row, prior in zip(rows,old['files']) if row['sha256'] != prior['sha256']] == ['camp_train_runtime.py']
    record=dict(old)
    record.update(sealed_utc=datetime.now(timezone.utc).isoformat(), files=rows,
        bytes=sum(row['bytes'] for row in rows), preparation_revision='v2_observer_parent_signature_fix',
        status='prepared_not_registered',
        original_preparation_manifest={'path':str(OLD/'PREPARATION_MANIFEST.json'),
            'sha256':sha(OLD/'PREPARATION_MANIFEST.json')},
        inherited_preflight_scope='Existing meta/import/real-pair reports are copied historical v1 evidence for unchanged model and reader paths, not new v2 scientific executions.',
        revision_checks={name:{'path':str(HERE/name),'sha256':sha(HERE/name)} for name in
            ('CAMP_OBSERVER_SIGNATURE_COUNTEREXAMPLE.json','CAMP_V2_DERIVATION.json',
             'CAMP_V2_BASE_CPU_VALIDATION.json','CAMP_V2_OBSERVER_REVIEW.json','camp_observer_v2.patch')},
        completed_preflight=old['completed_preflight']+[
            'v2: full existing AST/mock validation rerun with scientific imports blocked',
            'v2: exact official AverageMeter parent and production observation context tested',
            'v2: profile and final train both call the tested observation context'],
        missing_execution_evidence=[
            'new seed plans bound to v2 adapter and existing verified content manifest',
            'new execution/evaluation/outer binding derived without mutating active v1 records',
            'native batch24 actual two-update resource profiles',
            'complete one-epoch independent training and tensor/RNG round-trip',
            'independent final-checkpoint evaluation'])
    destination.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    handoff={'status':'prepared_not_registered','prepared_directory':str(NEW),
        'preparation_manifest_sha256':sha(destination),'runtime_sha256':sha(NEW/'camp_train_runtime.py'),
        'file_count':18,'changed_payloads':['camp_train_runtime.py'],
        'original_payloads_unchanged':True,'gpu_or_training_executed':False,
        'new_release_created':False,'queue_registered':False,
        'review_report':str(HERE/'CAMP_V2_OBSERVER_REVIEW.json'),
        'binding_work_left':'Old seed plans and contracts pin v1; root must bind v2 via a new successor, not edit old registration history.'}
    (HERE/'CAMP_V2_HANDOFF.json').write_text(json.dumps(handoff,indent=2),encoding='utf-8')
    print(json.dumps(handoff))

if __name__ == '__main__':
    main()
