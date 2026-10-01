"""CreateNew source manifests/patches only; never import or run candidate code."""
import ast
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKER = HERE.parent / 'newer_native_b1_worker_v2'
EX = HERE.parent.parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def put(path, raw):
    with path.open('xb') as f:
        f.write(raw); f.flush(); os.fsync(f.fileno())


def descriptor(path):
    raw = path.read_bytes()
    return {'path': str(path.resolve(strict=True)), 'bytes': len(raw), 'sha256': sha(raw)}


def json_new(path, value):
    put(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8') + b'\n')


def main():
    for snapshot, target, name in (
        ('INITIAL_PRE_REVIEW_native_lifecycle.py.txt', 'native_lifecycle.py', 'COMPLETE_INITIAL_TO_FINAL_LIFECYCLE.patch'),
        ('PRE_CLEANUP_REVIEW_native_lifecycle.py.txt', 'native_lifecycle.py', 'COMPLETE_CLEANUP_DELTA.patch'),
        ('INITIAL_PRE_REVIEW_evidence_contract.py.txt', 'evidence_contract.py', 'COMPLETE_INITIAL_TO_FINAL_EVIDENCE.patch'),
        ('INITIAL_PRE_REVIEW_prepare_worker_source_offline.py.txt', 'prepare_worker_source_offline.py', 'COMPLETE_OFFLINE_DERIVER_DELTA.patch')):
        a, b = (HERE / snapshot).read_bytes(), (HERE / target).read_bytes()
        raw = b''.join(difflib.diff_bytes(difflib.unified_diff,
            a.splitlines(keepends=True), b.splitlines(keepends=True),
            fromfile=str(HERE / snapshot).encode('utf-8'), tofile=str(HERE / target).encode('utf-8')))
        put(HERE / name, raw)
    source_roles = {
        'controller': HERE / 'native_lifecycle.py', 'reference_consistency_checker': HERE / 'evidence_contract.py',
        'worker': WORKER / 'reference_worker.py', 'offline_worker_deriver': HERE / 'prepare_worker_source_offline.py',
        'offline_manifest_sealer': Path(__file__).resolve()}
    # Merely parse source for a publication index; no AST statement execution.
    index = {}
    for role, path in source_roles.items():
        tree = ast.parse(path.read_bytes().decode('utf-8'))
        index[role] = {'source': descriptor(path),
                       'functions': [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]}
    json_new(HERE / 'SOURCE_INDEX.json', {
        'schema': 'newer-native-b1-lifecycle-source-index.v1', 'created_utc': datetime.now(timezone.utc).isoformat(),
        'roles': index, 'ast_parsing_only': True, 'synthetic_controls_executed': False,
        'process_api_or_native_science_executed': False,
        'source_adopted': False, 'execution_released': False, 'native_venv_validated': False})
    items = [descriptor(path) for path in sorted(HERE.iterdir()) if path.is_file()]
    worker_items = [descriptor(path) for path in sorted(WORKER.iterdir()) if path.is_file()]
    common = {'source_prepared': True, 'source_adopted': False, 'execution_released': False,
              'native_venv_validated': False, 'scientific_environment_validated': False,
              'scientific_execution_performed': False, 'synthetic_controls_executed': False,
              'independent_execution_proven': False, 'measurement_admitted': False,
              'full_t6_complete': False, 'manuscript_result': False}
    json_new(WORKER / 'SOURCE_MANIFEST.json', {
        'schema': 'newer-native-b1-worker-v2-source-manifest.v1', **common,
        'files': worker_items, 'original_v1': descriptor(HERE / 'PRIOR_WORKER_V1.py.txt'),
        'complete_byte_diff': descriptor(HERE / 'COMPLETE_WORKER_V1_TO_V2.patch'),
        'body_derivation_metadata': descriptor(HERE / 'WORKER_BODY_DERIVATION.json')})
    json_new(HERE / 'SOURCE_MANIFEST.json', {
        'schema': 'newer-native-b1-lifecycle-v1-source-manifest.v1', **common,
        'files': items, 'worker_files': worker_items,
        'worker_manifest': descriptor(WORKER / 'SOURCE_MANIFEST.json'),
        'scope_analysis': descriptor(EX / 'b1_integration_scope_20260930_0912' / 'INTEGRATION_SCOPE.json'),
        'scope_source_blocks': descriptor(EX / 'b1_integration_scope_20260930_0912' / 'SOURCE_BLOCKS.json')})
    print(json.dumps({'controller': descriptor(HERE / 'native_lifecycle.py'),
                      'evidence': descriptor(HERE / 'evidence_contract.py'), 'worker': descriptor(WORKER / 'reference_worker.py'),
                      'lifecycle_manifest': descriptor(HERE / 'SOURCE_MANIFEST.json'),
                      'worker_manifest': descriptor(WORKER / 'SOURCE_MANIFEST.json')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
