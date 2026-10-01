"""Seal only this AI text review and bounded small-file bindings; never import/run candidates."""
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EX = HERE.parent
SOURCE = EX / 'external_efficiency_preparation' / 'newer_native_process_evidence_v1'
OUTER = EX / 'newer_native_process_execution_20260930_0810'

def bind(path):
    path = Path(path)
    size = path.stat().st_size
    if not 0 <= size < 100000:
        raise ValueError('Only known small review/source files are bound')
    with path.open('rb') as stream:
        raw = stream.read(100000)
    if len(raw) != size:
        raise ValueError('Source metadata changed or oversized read')
    return {'path': str(path), 'bytes': size, 'sha256': hashlib.sha256(raw).hexdigest()}

record = {
    'schema': 'independent-outer-benign-fixture-source-review.v1',
    'reviewed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'reviewer': 'Independent AI agent /root/process_runtime_review_0758; no human review',
    'decision': 'No new text-review blocker found for a separate root decision on one ordinary-Python CPU fixture invocation on this host.',
    'execution_released': False,
    'fixture_or_helper_executed_by_reviewer': False,
    'runtime_validated': False,
    'scientific_admission': False,
    'method': 'Full text reading of helper/fixture/README, existing independent static report/delivery, and new run_outer.py. No prior static checker or suite was rerun.',
    'findings': [
        'run_outer.py has exactly one controlled Popen controller invocation using ordinary Python311 -I -S -B and CREATE_NO_WINDOW; it does not launch an original scientific worker.',
        'Explicit decision, pinned small bindings, and both absent attempt paths precede creation of the one outer attempt. Any existing empty/partial attempt refuses replay.',
        'The caller opens its own minimum-rights evidence handle separately from the Popen internal creation handle, confirms two complete controller snapshots, and checks exact command/image/current parent PID with retained creation identities.',
        'The actual controller held WAIT_OBJECT_0 and exit code zero are required before separate Popen exit-zero comparison and stream closure. Inner launcher/interpreter exits require later independent review of their own records.',
        'The two controller logs are sealed only after the held controller exit and both caller-owned redirect streams close. CreateFile read sharing excludes compatible write/delete access during hashing, without a global writer-history claim.',
        'Exceptions preserve OUTER_FAILURE when possible; finally independently attempts all stream and evidence-handle cleanup. Cleanup errors choose return intention94; records do not assume an absent process exited.',
        'The caller records its own actual exit as unknown. A subsequent outer tool exit concerns that caller only and cannot replace the held controller or inner exits.',
        'binding() reads bytes before applying its length cap. This one decision must bind known small source/review/observation files; the source does not establish a generic pre-read bounded-reader guarantee.',
        'Nt information class60 remains experimental on this host; no stable public compatibility guarantee is established.',
        'No kill/terminate, cleanup deletion, automatic restart, replay, user-app attachment, scientific library import, GPU operation, shared-lock acquisition, scientific intent, resource/boot admission or B1/ranking gate change appears.',
        'CreateNew partial JSON remains a fail-closed preserved failure. Controller result records require cleanup records and external actual exit before whole-fixture acceptance.',
        'Saved existing static report is prior source evidence only. No actual runtime or scientific success is inferred by this review.'
    ],
    'inputs': [bind(path) for path in [
        OUTER / 'run_outer.py', SOURCE / 'windows_process_evidence.py',
        SOURCE / 'benign_fixture.py', SOURCE / 'README.md',
        SOURCE / 'SOURCE_MANIFEST.json',
        EX / 'newer_native_process_evidence_review_20260930_0707' / 'REVIEW.json',
        EX / 'newer_native_process_evidence_review_20260930_0707' / 'DELIVERY.json',
        Path(__file__)
    ]]
}
with (HERE / 'OUTER_SOURCE_REVIEW.json').open('xb') as stream:
    raw = (json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    stream.write(raw)
print(json.dumps({'report': str(HERE / 'OUTER_SOURCE_REVIEW.json'), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'input_count': len(record['inputs'])}))
