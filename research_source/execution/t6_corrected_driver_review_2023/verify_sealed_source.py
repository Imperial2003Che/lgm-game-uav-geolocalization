"""Read-only real source/predecessor check, no scientific imports or preparation."""
import hashlib
import importlib.abc
import json
from pathlib import Path
import sys

OUT = Path(__file__).resolve().parent
V3 = OUT.parent / 'external_efficiency_preparation' / 'corrected_driver_v3'
FORBIDDEN = {'torch', 'numpy', 'PIL', 'torchvision', 'transformers', 'scipy', 'matplotlib'}
class NoScience(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in FORBIDDEN:
            raise AssertionError('Scientific import forbidden: ' + fullname)
sys.meta_path.insert(0, NoScience())
sys.path.insert(0, str(V3))
import contract as k

assert k.sha(V3 / 'SOURCE_MANIFEST.json') == 'cd6772f389038d23b9491c32d71fd109ee1620402034ce851b369a5be5ffcdc5'
manifest = k.frozen_sources()
rows = k.process_snapshot()
try:
    k.predecessors(manifest, rows)
except k.GateError as error:
    refusal = str(error)
else:
    raise AssertionError('Expected current interrupted predecessor refusal; recheck actual state')
assert refusal == 'status.json is not complete'
assert not FORBIDDEN.intersection(sys.modules)
assert not (V3 / 'runs').exists() and not (V3 / 'preparations').exists()
report = {'schema': 'primary-v3-actual-source-predecessor-check.v1', 'utc': k.now(),
          'status': 'source_verified_predecessor_incomplete', 'source_manifest': k.record(V3 / 'SOURCE_MANIFEST.json'),
          'source_records_verified': len(manifest['files']), 'predecessor_refusal': refusal,
          'main_state': k.record(k.E / 'status.json'), 'main_status': k.read(k.E / 'status.json')['status'],
          'actual_process_snapshot_count': len(rows), 'own_process_identity': k.process_identity(__import__('os').getpid(), rows),
          'scientific_imports': [], 'prepared_plan_created': False, 'active_release_created': False,
          'scientific_execution_performed': False}
receipt = k.write_new(OUT / 'ACTUAL_V3_SOURCE_AND_PREDECESSOR_CHECK.json', report)
print(json.dumps(receipt, ensure_ascii=True))
