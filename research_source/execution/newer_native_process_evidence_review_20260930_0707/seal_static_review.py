"""Seal an AI static review. Reads small text only; never imports reviewed code."""
import difflib
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
EX = HERE.parent
SRC = EX / 'external_efficiency_preparation' / 'newer_native_process_evidence_v1'
records = {}

def bind(path):
    raw = path.read_bytes()
    assert len(raw) < 100000, 'Small-file review only'
    item = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    records[str(path)] = item
    return raw, item

def check(item):
    raw, actual = bind(Path(item['path']))
    assert actual == item, item['path']
    return raw

def create(name, obj):
    with (HERE / name).open('xb') as f:
        f.write((json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8'))

manifest_raw, manifest_binding = bind(SRC / 'SOURCE_MANIFEST.json')
assert manifest_binding['sha256'] == '0ca3e4acea597ceaad41eeb35285338d8a0a6f837c2480410faf857631ab9603'
manifest = json.loads(manifest_raw)
assert len(manifest['files']) == 9
assert manifest['execution_released'] is False and manifest['runtime_validated'] is False
for item in manifest['files']:
    check(item)
input_raw, _ = bind(SRC / 'REVIEW_INPUTS.json')
inputs = json.loads(input_raw)
for item in inputs['scientific_predecessor_context']:
    check(item)
delivery_raw, _ = bind(SRC / 'DELIVERY.json')
delivery = json.loads(delivery_raw)
check(delivery['source_manifest'])
check(delivery['review_inputs'])
parts = []
for name in ('windows_process_evidence.py', 'benign_fixture.py', 'README.md'):
    old = (SRC / 'draft_before_independent_fixes' / name).read_bytes().decode('utf-8')
    new = (SRC / name).read_bytes().decode('utf-8')
    parts.extend(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                     fromfile='draft_before_independent_fixes/' + name, tofile=name))
assert ''.join(parts).encode('utf-8') == (SRC / 'COMPLETE_DIFF_FROM_PRESERVED_DRAFT.patch').read_bytes()
assert not (SRC / 'runtime_attempt_v1').exists(), 'Unexpected actual attempt; no retrospective pre-execution claim'
bind(Path(__file__).resolve())

sources = [
 ('NtQueryInformationProcess', 'https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntqueryinformationprocess', 'The documented class list omits 60. Microsoft says this internal API and its structures may change; this source does not establish a public class60 contract.'),
 ('GetProcessTimes', 'https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes', 'Creation and exit FILETIME use 100 ns integers since 1601. Exit-time output is undefined for a running process.'),
 ('FILETIME', 'https://learn.microsoft.com/en-us/windows/win32/api/minwinbase/ns-minwinbase-filetime', 'Two DWORD parts form a 64-bit 100 ns count. The reviewed code combines integers and separately converts the epoch.'),
 ('UNICODE_STRING', 'https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_unicode_string', 'Length and MaximumLength are byte counts. Length excludes a trailing NUL. This does not document information class60 itself.'),
 ('PROCESSENTRY32W', 'https://learn.microsoft.com/en-us/windows/win32/api/tlhelp32/ns-tlhelp32-processentry32w', 'Toolhelp provides snapshot PID and parent number; the entry executable name is not a full image path.'),
 ('Win32_Process', 'https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-process', 'Microsoft explicitly warns parent PID numbers may refer to a terminated or reused process. Creation identity must be considered. CIM was researched, not called by this review or helper.'),
 ('WaitForSingleObject', 'https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobject', 'SYNCHRONIZE is needed. Signaled, timeout and failure returns are distinct. Closing a handle during a pending wait is undefined.'),
 ('GetExitCodeProcess', 'https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getexitcodeprocess', 'The function can return STILL_ACTIVE=259 before termination; a program can also actually exit259. The code requires signaled wait first.'),
 ('Process rights', 'https://learn.microsoft.com/en-us/windows/win32/procthread/process-security-and-access-rights', 'Limited query permits required identity/exit queries; SYNCHRONIZE permits waiting. These differ from terminate or VM-write rights.'),
 ('QueryFullProcessImageNameW', 'https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-queryfullprocessimagenamew', 'Uses a process handle and reports image path length. Failure is checked in the candidate.'),
 ('OpenProcess', 'https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openprocess', 'Requested access and inheritance are explicit; failure cannot be taken as absence or exit.'),
 ('CloseHandle', 'https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle', 'Closing a process handle does not terminate that process.'),
 ('CreateFileW', 'https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew', 'Read-only sharing conflicts with existing write/delete access and excludes compatible new write/delete opens while retained. It is not historical writer exclusion.'),
 ('Python subprocess3.11', 'https://docs.python.org/3.11/library/subprocess.html', 'Popen waits and returncode concern the process represented by Popen. Redirect files avoid pipe-fill deadlock here. No terminate/kill or run(timeout) auto-kill is used.'),
 ('Python msvcrt3.11', 'https://docs.python.org/3.11/library/msvcrt.html', 'open_osfhandle converts an OS handle into a descriptor; descriptor/stream closure must follow transfer, including fdopen failure.')
]
observations = [
 'Final helper and fixture were read in full as text, along with README, full preserved-draft diff, producer sealer, source manifest, review inputs and delivery. No reviewed module was imported or executed.',
 'Held evidence handles request non-inheritable limited query plus synchronize (0x101000). Popen creation handles are separate and are not claimed to have those minimal rights.',
 'Kernel identity contains PID, actual QueryFullProcessImageName path, raw creation_filetime_100ns and creation_utc_ticks with integer offset504911232000000000. No float or microsecond conversion is used.',
 'Fresh handle snapshots compare identity before/after command/Toolhelp capture against retained identity; complete exact command and os.path.samefile image comparison precede ACK. Parent snapshot and child creation order limit PID-reuse mistakes; claims remain contemporaneous parentage, not complete history.',
 'Nt class60 status must match expected size-status and then zero success; allocations and returned byte count are bounded, UNICODE_STRING lengths even and ordered, pointer aligned and whole MaximumLength inside returned buffer before dereference. No shortened/self-report fallback exists. Experimental current-host behavior remains unvalidated.',
 'Launcher waits for its request-hash/held-identity ACK before child spawn. The child task follows external dual observation and its own bound ACK. Child self-ready is checked against independent externally opened identity, never used alone as proof.',
 'External fixture parent retains distinct launcher and child evidence handles. Each requires WAIT_OBJECT_0, successful GetExitCodeProcess and unchanged held identity; real exit FILETIME is read only afterward. Timeout returns no exit record; WAIT_FAILED/errors raise. DWORD259 is interpreted only after signaled wait.',
 'Exception return-intentions now reset child92/launcher93 even after intended zero was set; cleanup errors choose94. A reporting exception may itself propagate; it cannot be silently accepted as success.',
 'All stream and held-handle cleanup attempts are separate; errors are recorded when logging works. CloseHandle does not kill or prove exit. No process termination, deletion, app closure, priority/privilege/pagefile or scientific source change appears.',
 'All four case stdout/stderr logs are hashed only after both designated external exits and external redirect streams close. CreateFile uses read-only sharing during hashing; fdopen failure closes transferred fd. This is cooperative file/process evidence, not immutable protection against all arbitrary writers.',
 'Fixed ordinary Python311 uses -I -S -B with exact samefile check, controlled source-directory child roles and CREATE_NO_WINDOW; only stdlib imports and a small integer sum occur. Cases zero and nonzero17 expect 0/0 and17/17. No original scientific venv or redirection behavior is verified.',
 'Existing runtime_attempt_v1 refuses replay, including partial/empty directory. CreateNew JSON publication is not atomic; observing partial JSON intentionally fails without retry. Control source pinning before eventual launch remains root responsibility.',
 'The fixture records only controller return intent; the external root launcher must separately capture its real process identity/exit and close streams. Case result files alone, especially before cleanup completion or a later case failure, are insufficient to accept the whole fixture.',
 'B1 source SHA remains eed9b25b... and all previously unconditional refusal gates remain untouched. This helper supplies no boot/resource/release/lock/predecessor admission and no six native workers/fresh ranking/parity/timing/T6 result.'
]
review = {
 'schema': 'newer-native-process-evidence-independent-static-review.v1',
 'reviewed_utc': datetime.now(timezone.utc).isoformat(),
 'reviewer': 'Independent AI agent /root/boot_review_0405; no human review claimed',
 'decision': 'No remaining static blocker found for a separate root decision on one controlled benign fixture attempt on this host only.',
 'execution_released_by_review': False, 'fixture_executed_by_reviewer': False,
 'windows_api_executed_by_reviewer': False, 'candidate_imported_by_reviewer': False,
 'runtime_validated': False, 'scientific_admission': False,
 'review_method': 'Full AI text inspection plus exact small-file byte/manifest and complete saved-draft diff binding; no synthetic or runtime tests, no old suites.',
 'observations': observations,
 'resolved_before_freeze': ['Child/launcher post-success exceptions could retain code0; final catches reset92/93.', 'UTF16 pointer alignment was missing; final explicitly requires even address.', 'Final dual FILETIME/.NET epoch fields are explicit; the preserved draft already includes the earlier unsealed epoch/case edits.', 'Image-path length/nonempty and fdopen-error descriptor closure are explicit in final source.'],
 'history_limit': inputs['snapshot_limit'],
 'web_research': {'date_utc': '2026-09-30', 'clock_anchor_during_research_utc': '2026-09-30 06:10:57 UTC', 'last_retrieval_clock_utc': '2026-09-30 06:23:16 UTC', 'exact_time_each_first_batch_call_not_recorded': True, 'primary_sources': [{'title': a, 'url': b, 'reading': c} for a,b,c in sources], 'failed_url': 'https://learn.microsoft.com/en-us/windows/win32/api/winternl/ns-winternl-unicode_string', 'failure': 'web open returned Internal Error; official ntdef UNICODE_STRING page succeeded. Microsoft pages displayed generic authorization banners but full relevant article text was returned.'},
 'runtime_attempt_absent_at_seal': True,
 'input_binding_count': len(records), 'inputs': list(records.values())
}
create('REVIEW.json', review)
with (HERE / 'REVIEW.md').open('x', encoding='utf-8', newline='\n') as f:
    f.write('Independent AI static review only. Final source has no remaining static blocker for a separate root decision on one ordinary-Python benign fixture attempt. No candidate, Win32 API, fixture, scientific environment or old suite was executed by this reviewer.\n\nThe final exception-code reset and UTF-16 alignment fixes were inspected; exact integer FILETIME/.NET epochs, held identity comparison, complete commands, ACK ordering, actual signaled waits, closed-log sealing and failure cleanup were reviewed. Nt information class 60 is experimental and undocumented as a stable public contract. Current-host success, if later observed, cannot establish general compatibility or scientific admission.\n\nRoot must independently capture the fixture controller exit, inspect all actor failure/cleanup records and preserve any partial attempt. A case result or controller return-intent is insufficient. Scientific B1 gates, predecessor/boot/resource/release/locks, original venv redirection, six workers and T6 remain unresolved.\n')
_, rb = bind(HERE / 'REVIEW.json')
_, mb = bind(HERE / 'REVIEW.md')
create('DELIVERY.json', {'schema': 'newer-native-process-evidence-independent-review-delivery.v1', 'review': rb, 'explanation': mb, 'review_sealer': records[str(Path(__file__).resolve())], 'execution_released': False, 'scientific_admission': False})
raw = (HERE / 'DELIVERY.json').read_bytes()
print(json.dumps({'review': rb, 'delivery': {'path': str(HERE / 'DELIVERY.json'), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}, 'input_binding_count': review['input_binding_count']}, ensure_ascii=False))
