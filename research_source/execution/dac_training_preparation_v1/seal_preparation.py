"""Seal the preparation sources, never make an experiment plan or launch a run."""
from datetime import datetime, timezone
import json
from pathlib import Path
from common_runtime import HERE, sha_file, write_json
from dac_train_runtime import verify_scientific_source

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def main():
    destination = HERE/'PREPARATION_MANIFEST.json'
    if destination.exists():
        raise RuntimeError('Preparation already sealed; do not overwrite frozen sources')
    qa = read(HERE/'CPU_VALIDATION.json')
    if qa['status']!='passed' or qa['passed']!=qa['total'] or qa['scientific_import_attempts'] or qa['real_model_or_images_loaded'] or qa['cuda_used']:
        raise RuntimeError('Preparation standard-library checks did not pass')
    for relative, expected in qa['source_files_sha256'].items():
        if sha_file(HERE/relative)!=expected:
            raise RuntimeError('A source changed after stdlib validation: '+relative)
    current_python={path.relative_to(HERE).as_posix() for path in HERE.rglob('*.py')}
    if current_python!=set(qa['source_files_sha256']):
        raise RuntimeError('New Python source has not been checked')
    verify_scientific_source()
    review_path=HERE.parent/'dac_training_preparation_review_1721/INDEPENDENT_SCIENTIFIC_REVIEW.json'
    review=read(review_path)
    if not review['checks'] or not all(row.get('passed') for row in review['checks']):
        raise RuntimeError('Independent scientific static review has not passed')
    for relative, expected in review['scope_hashes'].items():
        if sha_file(HERE/relative)!=expected:
            raise RuntimeError('Independently reviewed source changed: '+relative)
    refs=read(HERE/'INPUT_REFERENCES.json')
    if sha_file(refs['data_manifest_path'])!=refs['data_manifest_sha256']:
        raise RuntimeError('Existing University inventory JSON changed')
    inherited=HERE.parent/'camp_training_preparation_v2/PREPARATION_MANIFEST.json'
    if sha_file(inherited)!='12747158ce2647474c6d24688ba3ebb872ac137118fab7aefd1c1e0ecfad40ec':
        raise RuntimeError('Inherited CAMP v2 provenance changed')
    rows=[]
    for path in sorted(HERE.rglob('*')):
        if path.is_file():
            if '__pycache__' in path.parts or path.suffix=='.pyc' or path.name.endswith('.partial'):
                raise RuntimeError('Unintended generated file in preparation: '+str(path))
            rows.append({'path':path.relative_to(HERE).as_posix(),'bytes':path.stat().st_size,'sha256':sha_file(path)})
    manifest={'schema':'dac-training-preparation.v1','status':'prepared_not_registered',
        'prepared_utc':datetime.now(timezone.utc).isoformat(),'method':'DAC','protocol':'University two-view, native24, 384, one complete epoch',
        'official_commit':'5612a79c3928d8a71939e4e761bb352f805cb51b','model_state_count':402,
        'files':rows,'payload_file_count':len(rows),'payload_bytes':sum(row['bytes'] for row in rows),
        'stdlib_validation':{'path':'CPU_VALIDATION.json','sha256':sha_file(HERE/'CPU_VALIDATION.json'),'passed':qa['passed'],'total':qa['total']},
        'independent_scientific_review':{'path':str(review_path),'sha256':sha_file(review_path),'check_count':len(review['checks']),'scope':'scientific source, train-only entry, DAC/common runtime; no model execution'},
        'inherited_bookkeeping_provenance':{'manifest_path':str(inherited),'manifest_sha256':sha_file(inherited),
            'byte_identical_runtime_sha256':sha_file(HERE/'common_runtime.py'),'scientific_model_reused_from_CAMP':False},
        'input_references_sha256':sha_file(HERE/'INPUT_REFERENCES.json'),
        'existing_content_inventory_sha256':refs['data_manifest_sha256'],
        'scientific_imports_performed_by_preparation':False,'real_model_or_images_loaded_by_preparation':False,
        'gpu_used':False,'resource_profile_executed':False,'training_executed':False,
        'experiment_plan_or_release_or_queue_written':False,
        'future_required_evidence':['Independent real DAC CPU/344 strict init/402 model/real-pair original augmentation proof',
            'Native24 all-loss DAC profile with at least two actual AdamW updates and finite changed state',
            'Separately frozen three-seed plans and serial release after all predecessor owners exit',
            'Three complete training runs and separately admitted full-gallery final-checkpoint evaluation']}
    write_json(destination,manifest)
    # Verify every sealed payload again; no extraction or scientific runtime involved.
    for row in rows:
        if sha_file(HERE/row['path'])!=row['sha256']:
            raise RuntimeError('Payload changed while sealing')
    print(json.dumps({'status':manifest['status'],'files':len(rows),'bytes':manifest['payload_bytes'],
        'manifest_sha256':sha_file(destination),'checks_passed':qa['passed']}))

if __name__=='__main__': main()
