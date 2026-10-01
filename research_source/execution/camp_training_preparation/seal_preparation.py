"""CPU-only immutable-file manifest for the prepared adapter, not a training result."""
from datetime import datetime, timezone
import json
from camp_train_runtime import HERE, sha_file, write_json

def main():
    files = []
    for path in sorted(HERE.iterdir()):
        if not path.is_file() or path.name == 'PREPARATION_MANIFEST.json':
            continue
        files.append({'path':path.name, 'bytes':path.stat().st_size, 'sha256':sha_file(path)})
    validation = json.loads((HERE/'CPU_VALIDATION.json').read_text(encoding='utf-8'))
    pretrain = json.loads((HERE/'PRETRAINED_META_VALIDATION.json').read_text(encoding='utf-8'))
    pair = json.loads((HERE/'REAL_PAIR_CPU_adapter_reader.json').read_text(encoding='utf-8'))
    assert not validation['torch_imported'] and not validation['gpu_execution'] and pretrain['passed']
    assert pair['status']=='passed' and pair['cuda_initialized'] is False and pair['all_training_imports_passed']
    record = {'schema':'camp-university-training-preparation.v1', 'status':'prepared_not_registered',
              'sealed_utc':datetime.now(timezone.utc).isoformat(),
              'official_commit':'b04a9c856711770ed7a72ebf851838329c5e5b8e',
              'files':files, 'file_count':len(files), 'bytes':sum(r['bytes'] for r in files),
              'gpu_execution':False, 'queue_registration':False,
              'scientific_environment_modified':False,
              'completed_preflight':['AST/source provenance', 'pretrained344/344 meta coverage',
                  'independent camp imports and actual module origins/versions',
                  'one genuine training pair and full official augmentation',
                  'Unicode decoder equality to ASCII cv2.imread'],
              'missing_execution_evidence':['training data content manifest',
                  'full batch24 two-step resource profile',
                  'later serial release', 'complete one-epoch training', 'checkpoint tensor/RNG round-trip',
                  'independent final-checkpoint evaluation']}
    write_json(HERE/'PREPARATION_MANIFEST.json', record)
    print(json.dumps({'manifest':str(HERE/'PREPARATION_MANIFEST.json'),
                      'sha256':sha_file(HERE/'PREPARATION_MANIFEST.json'),
                      'files':len(files), 'bytes':record['bytes']}))

if __name__ == '__main__':
    main()
