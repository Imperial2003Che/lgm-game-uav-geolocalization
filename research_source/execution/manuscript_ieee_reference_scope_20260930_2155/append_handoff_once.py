import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

EX = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution')
WORK = EX / 'manuscript_ieee_reference_scope_20260930_2155'
path = EX / 'HANDOFF.md'
expected_bytes = 525019
expected_sha = '6a790c1f3c22bfd51b169d734b65c7b5bd8da5ff0150d2ffec0353ba8e07de87'
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
def record(file):
    raw = file.read_bytes()
    return {'path': str(file), 'bytes': len(raw), 'sha256': digest(raw)}
receipt_path = WORK / 'HANDOFF_APPEND_RECEIPT.json'
assert not receipt_path.exists()
old = path.read_bytes()
assert len(old) == expected_bytes and digest(old) == expected_sha
raw = (WORK / 'HANDOFF_APPEND.md').read_bytes()
append = b'\r\n' + raw.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
# Cooperative file/prefix guard only; no claim of arbitrary-writer atomic exclusion.
with path.open('r+b') as stream:
    current = stream.read()
    assert current == old
    stream.seek(0, 2)
    stream.write(append)
    stream.flush()
    os.fsync(stream.fileno())
new = path.read_bytes()
assert new == old + append
receipt = {'schema': 'guarded-handoff-append.v1', 'utc': datetime.now(timezone.utc).isoformat(),
    'source': record(Path(__file__)), 'append_source': record(WORK / 'HANDOFF_APPEND.md'),
    'prefix': {'bytes': expected_bytes, 'sha256': expected_sha},
    'append_bytes': len(append), 'append_sha256': digest(append),
    'new_handoff': record(path), 'existing_prefix_preserved_exact': True,
    'method_limit': 'Cooperative read/compare/append/flush; not arbitrary-writer exclusion.',
    'delivery': record(WORK / 'DELIVERY.json'), 'automation_kept': True,
    'new_scientific_result': False, 'Overleaf_updated': False}
with receipt_path.open('xb') as stream:
    stream.write((json.dumps(receipt, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    stream.flush(); os.fsync(stream.fileno())
print(json.dumps({'receipt': record(receipt_path), 'handoff': receipt['new_handoff']}, ensure_ascii=False))
