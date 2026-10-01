"""Freeze adapter source only. No completed slot binding, tensor read or process."""
from pathlib import Path
import sys
import json

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bindings as b

def main():
    k = b.common()
    k.require(not (HERE / 'SOURCE_MANIFEST.json').exists(), 'Source already frozen')
    job = k.read(b.BASE / 't1_job.json')
    files = [*HERE.glob('*.py'), HERE / 'HANDOFF.md', HERE / 'STDLIB_REVIEW.json',
        b.V2 / 'SOURCE_MANIFEST.json', b.V2 / 'contract.py',
        b.COMPONENTS / 'SOURCE_MANIFEST.json', b.COMPONENTS / 'measurement_components.py',
        b.BASE / 't1_job.json', b.HERE.parent / 'CORRECTIVE_MEASUREMENT_PLAN.md',
        b.HERE.parent / 'SCOPE_INDEPENDENT_REVIEW.json']
    for path_string, expected in job['source_sha256'].items():
        path = Path(path_string)
        # This registered list contains only source/configuration/CPU audit files;
        # no final-fit checkpoint or weight tensor is accessed here.
        k.require(path.suffix.lower() not in {'.pt', '.pth', '.ckpt', '.safetensors'}, 'Unexpected tensor file in source registry')
        k.require(k.sha(path) == expected, 'Frozen T1 source changed: ' + str(path))
        files.append(path)
    lock = k.read(b.EXT / 'transactions_environment_lock.json')
    for source in lock['compatibility_revision']['source_manifests'].values():
        root = Path(source['source_root'])
        for path in root.rglob('*'):
            if path.is_file() and (path.suffix.lower() in {'.py', '.yaml', '.yml', '.json', '.toml', '.ini'} or path.name == 'requirements.txt'):
                files.append(path)
    for environment in lock['environments'].values():
        files.append(Path(environment['executable']))
    checks = k.read(HERE / 'STDLIB_REVIEW.json')
    k.require(checks['failed'] == 0 and checks['scientific_execution_performed'] is False, 'Static review failed')
    manifest = {'schema': 'external-t1-native-efficiency-adapter-source.v1', 'created_utc': k.now(),
        'files': [k.record(p) for p in sorted(set(files), key=lambda p: str(p).casefold())],
        'registered_slots': b.slots(), 'scientific_execution_performed': False, 'scientific_imports': [],
        'completed_checkpoint_binding_created': False, 'active_plan_created': False, 'release_created': False,
        'scope': 'native model-load, descriptor and isolated sample timing interfaces; not integrated into a controller',
        'external_efficiency_samples_measured': 0, 'full_t6_complete': False, 'manuscript_result': False}
    result = k.write_new(HERE / 'SOURCE_MANIFEST.json', manifest)
    print(json.dumps({'source_manifest': result, 'source_files': len(manifest['files']), 'prepared_only': True}))

if __name__ == '__main__':
    main()
