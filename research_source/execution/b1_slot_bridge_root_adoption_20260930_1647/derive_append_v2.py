"""One offline metadata-reader correction; no tests/candidate/old-suite execution."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import difflib
import json
import os

HERE = Path(__file__).resolve().parent
EX = HERE.parent
CAP = 262144

def new(path, raw):
    if len(raw) > CAP:
        raise ValueError('bounded new metadata input')
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

for name in ('DELIVERY.json', 'HANDOFF_APPEND_RECEIPT.json'):
    if (HERE / name).exists():
        raise ValueError('Metadata append may have written; no repair replay')
handoff = (EX / 'HANDOFF.md').read_bytes()
if len(handoff) != 487281 or hashlib.sha256(handoff).hexdigest() != '35e1094a0597f22e0be863f312c797ad5fcb0f25baf084dd5b3c2daa615df2e3':
    raise ValueError('Journal changed; no replacement append')
old_path = HERE / 'append_handoff.py'
old = old_path.read_bytes()
if len(old) > CAP:
    raise ValueError('Source bound')
raw = old.decode('utf-8')
needle = 'if not 0 < before.st_size <= CAP:'
if raw.count(needle) != 1:
    raise ValueError('Expected sole zero-size bound')
updated = raw.replace(needle, 'if not 0 <= before.st_size <= CAP:')
updated = updated.replace("'append_handoff.py'))", "'append_handoff.py', 'append_handoff_v2.py', 'derive_append_v2.py', 'APPEND_V2_DERIVATION.json', 'append_handoff_v1_to_v2.patch', 'FAILED_HANDOFF_APPEND_TOOL_RETURN.json'))")
paragraph = '\n本局部append_handoff.py首112c04 exit1仅metadata reader错误要求size>0而拒绝真实0B闭合pipeline.stdout.log，非过大log/科学失败；发生在DELIVERY/journal写前，根核旧487281B journal prefix与两个报告均未改，原源和实际失败完整保留。另append_handoff_v2.py只允许0<=size<=262144且追加本说明/错误来源索引，完整delta与offline派生封存，未重跑已通过源审查或科学/control suite。\n'
closing = "'''\naddition = text.encode('utf-8')"
if updated.count(closing) != 1:
    raise ValueError('Expected journal literal close')
updated = updated.replace(closing, paragraph + closing)
current = updated.encode('utf-8')
outputs = [new(HERE / 'append_handoff_v2.py', current)]
delta = ''.join(difflib.unified_diff(raw.splitlines(keepends=True), updated.splitlines(keepends=True),
                                  fromfile='append_handoff.py', tofile='append_handoff_v2.py')).encode('utf-8')
outputs.append(new(HERE / 'append_handoff_v1_to_v2.patch', delta))
failure_path = HERE / 'FAILED_HANDOFF_APPEND_TOOL_RETURN.json'
failure_raw = failure_path.read_bytes()
report = {
    'schema': 'metadata-append-source-zero-byte-reader-derivation.v1',
    'utc': datetime.now(timezone.utc).isoformat(),
    'old_source': {'path': str(old_path), 'bytes': len(old), 'sha256': hashlib.sha256(old).hexdigest()},
    'new_source_and_complete_delta': outputs,
    'failed_actual_tool': {'path': str(failure_path), 'bytes': len(failure_raw), 'sha256': hashlib.sha256(failure_raw).hexdigest()},
    'failure_wrote_no_delivery_or_handoff': True,
    'old_journal_prefix_verified': {'bytes': len(handoff), 'sha256': hashlib.sha256(handoff).hexdigest()},
    'scope': 'Only bounded saved-file zero-size acceptance and explicit failure provenance; all execution/source/research states unchanged',
    'new_append_executed_by_this_derivation': False,
    'candidate_or_scientific_or_old_suite_execution': False,
}
result = new(HERE / 'APPEND_V2_DERIVATION.json', (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
print(json.dumps({'outputs': outputs, 'derivation': result}, ensure_ascii=False))
