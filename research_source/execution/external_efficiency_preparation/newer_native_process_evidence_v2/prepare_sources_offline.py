"""Offline byte derivation only; never import the candidate or query Windows APIs."""
import datetime
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EX = HERE.parent.parent
OLD = HERE.parent / 'newer_native_process_evidence_v1'
OUTER = EX / 'newer_native_process_execution_20260930_0810' / 'outer_runtime_attempt_v1'
INNER = OLD / 'runtime_attempt_v1'


def write_new(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)


def dump(path, value):
    write_new(path, (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8'))


def binding(path):
    raw = path.read_bytes()
    return {'path': str(path.resolve()), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def replace_once(raw, old, new):
    before, after = old.encode('utf-8'), new.encode('utf-8')
    assert raw.count(before) == 1, 'Byte patch target missing or ambiguous'
    return raw.replace(before, after, 1)


def main():
    assert not (HERE / 'runtime_attempt_v1').exists(), 'No v2 attempt may exist for source preparation'
    before_helper = (OLD / 'windows_process_evidence.py').read_bytes()
    before_fixture = (OLD / 'benign_fixture.py').read_bytes()
    assert hashlib.sha256(before_helper).hexdigest() == 'b21c05e40ec721b343a376e95ba10ae590288ce3eecb33b7238fcf58a16ed023'
    assert hashlib.sha256(before_fixture).hexdigest() == '05379eda9addbac90faea33d73eb9a0faa4fc59450bf65e3e1f11de677fca50f'
    after_helper = replace_once(before_helper, '''    def signaled_exit_times(self, handle):
        """Call only after WAIT_OBJECT_0; running-process exit time is undefined."""
        creation, exit_time, kernel, user = (FILETIME() for _ in range(4))
        if not self.k.GetProcessTimes(handle, C.byref(creation), C.byref(exit_time), C.byref(kernel), C.byref(user)):
            raise self.error('GetProcessTimes after signaled wait')
        value = ticks(exit_time)
        require(value > 0, 'Signaled process lacks an exit FILETIME')
        return {'exit_filetime_100ns': value, 'exit_utc_ticks': value + FILETIME_TO_DOTNET_TICKS}
''', '''    def signaled_exit_times(self, handle, expected_identity, ledger, label):
        """Same retained handle after WAIT_OBJECT_0; no exited-image/PID reopen."""
        pid = int(self.k.GetProcessId(handle))
        ledger.emit('signaled_pid_candidate', label=label, pid_from_held_handle=pid,
                    complete_exit_evidence=False)
        if pid == 0:
            raise self.error('GetProcessId after signaled wait')
        creation, exit_time, kernel, user = (FILETIME() for _ in range(4))
        if not self.k.GetProcessTimes(handle, C.byref(creation), C.byref(exit_time), C.byref(kernel), C.byref(user)):
            raise self.error('GetProcessTimes after signaled wait')
        raw_creation, raw_exit = ticks(creation), ticks(exit_time)
        value = {'pid': pid, 'creation_filetime_100ns': raw_creation,
                 'creation_utc_ticks': raw_creation + FILETIME_TO_DOTNET_TICKS,
                 'exit_filetime_100ns': raw_exit,
                 'exit_utc_ticks': raw_exit + FILETIME_TO_DOTNET_TICKS}
        ledger.emit('signaled_identity_times_candidate', label=label, value=value,
                    complete_exit_evidence=False)
        require(pid == expected_identity['pid'] and raw_creation > 0 and
                raw_creation == expected_identity['creation_filetime_100ns'] and
                value['creation_utc_ticks'] == expected_identity['creation_utc_ticks'],
                'Signaled retained handle PID/creation identity changed')
        require(raw_exit > 0, 'Signaled process lacks an exit FILETIME')
        return value
''')
    after_helper = replace_once(after_helper, '''        now = self.api.kernel_identity(self.handle)
        require(now == self.identity, 'Signaled held identity changed')
        self.exit_observation = {'identity': self.identity, 'wait_result': result,
                                 'exit_code_unsigned_dword': int(code.value), 'observed_utc_ns': time.time_ns(),
                                 **self.api.signaled_exit_times(self.handle),
                                 'exit259_is_valid_after_signaled_wait': True}
''', '''        partial = {'retained_live_identity': self.identity, 'wait_result': result,
                   'exit_code_unsigned_dword': int(code.value), 'observed_utc_ns': time.time_ns(),
                   'complete_exit_evidence': False}
        self.ledger.emit('exit_candidate', label=self.label, value=partial)
        observed_times = self.api.signaled_exit_times(self.handle, self.identity, self.ledger, self.label)
        self.exit_observation = {'identity': self.identity, 'wait_result': result,
                                 'exit_code_unsigned_dword': int(code.value), 'observed_utc_ns': time.time_ns(),
                                 **observed_times, 'same_retained_handle_pid_creation_verified': True,
                                 'image_scope': 'Retained live image; not requeried after exit',
                                 'exit259_is_valid_after_signaled_wait': True}
''')
    write_new(HERE / 'windows_process_evidence.py', after_helper)
    write_new(HERE / 'benign_fixture.py', before_fixture)
    assert before_fixture == (HERE / 'benign_fixture.py').read_bytes()
    before_readme = (OLD / 'README.md').read_bytes()
    readme = '''# Source-only v2 repair: retained process handle exit evidence

This is a new, unexecuted candidate. It does not authorize another fixture invocation or any scientific execution. The v1 source and both consumed v1 attempt directories remain unchanged. No v2 runtime attempt, release, scientific intent, lock or state is created by this preparation. Independent static review and a separate root execution decision are still required.

The actual v1 benign CPU attempt failed: a signaled held wait was followed by QueryFullProcessImageNameW on the already-exited process, which returned WinError 31. The launcher, fixture controller and outer observer recorded this failure. No complete exit_observed or case result was produced; the nonzero17 case did not run. The child's saved task and return intention are not adopted as proof of its actual exit. Absence or the outer tool result cannot fill the missing held exit evidence. The consumed v1 paths must never be replayed or deleted.

Only the helper's post-signaled exit branch changes. WAIT_OBJECT_0 remains mandatory before querying the actual unsigned DWORD exit code. That DWORD and the retained live identity are immediately persisted as an incomplete exit_candidate. The same, continuously retained evidence handle is then used for GetProcessId and GetProcessTimes. Actual candidate PID and raw creation/exit FILETIME values are persisted before identity gates. PID and raw creation must equal the previously retained live identity; creation must be positive and the integer .NET UTC conversion must agree. The actual exit FILETIME must be positive. Only successful completion of these checks sets exit_observation and writes exit_observed. An incomplete candidate, API failure or mismatched creation never permits log sealing.

There is no image or command query, fresh OpenProcess, PID lookup or self-report fallback in the exited branch. The stored image is explicitly the retained live image; it is not claimed to have been queried after exit. Live image/full-command capture and the two complete contemporaneous confirmations remain byte-identical. Evidence handles still request only PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, are non-inheritable, and remain held until observation/closure. Popen's separate creation handles are not presented as these minimum-rights evidence handles. Closing any handle neither kills a process nor proves it exited.

The Microsoft GetProcessId/GetProcessTimes contracts support limited-query handles. GetProcessTimes describes creation and exit times as integer 100 ns counts from 1601; exit time is undefined before process exit. Microsoft's process-termination documentation describes signaled process objects and object lifetime while another process retains a handle. These sources support the proposed same-handle mechanism; they do not demonstrate that this v2 Windows runtime works. Unsupported/denied API behavior still fails closed. NtQueryInformationProcess class 60 remains an undocumented, experimental current-host command query with no general Windows compatibility claim.

benign_fixture.py is byte-identical to v1. Its HERE derives the distinct v2 directory, so its single-use runtime_attempt_v1 would be a new v2 path only after a future root execution decision. Every role still requires the exact ordinary Python311 interpreter with -I -S -B; imports use only the standard library/helper. The zero and nonzero17 cases, ACK/request-byte/held-identity protocol, two external launcher/interpreter captures, bounded waits, CreateNew failure preservation, separate Popen status, cleanup branches and no-kill/no-retry behavior are unchanged. The outer root caller must independently capture the fixture controller's actual held exit; its return-intent record does not prove its own exit.

Log seals still require complete actual designated held exits and controller redirect-stream closure, and read-only sharing excludes incompatible write/delete handles during the hash. This is cooperative lifecycle evidence, not global malicious-writer history or atomic publication. CreateNew filenames can become visible before JSON is complete; partial JSON is preserved failure, not a retry. No v1 result is retroactively reconstructed.

This source preparation does not validate B1, scientific native environments, predecessor completion/exits, boot/release/resource admission, GPU exclusivity, memory, shared-byte locks, six scientific workers, gallery encoding, ranking, online CLIP or T6. All old B1 and ranking refusal gates and frozen scientific protocols remain unchanged. No source-adoption or execution authority is issued here.

Official references read for this proposed delta:

- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocessid
- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes
- https://learn.microsoft.com/en-us/windows/win32/procthread/terminating-a-process

The documentation was read as web text during source preparation, not exercised through Windows APIs. Source byte hashes and complete v1-to-v2 differences are recorded alongside this README. This README is not a future execution decision.
'''
    write_new(HERE / 'README.md', readme.encode('utf-8'))
    diffs = []
    for name, old, new in [('windows_process_evidence.py', before_helper, after_helper),
                           ('benign_fixture.py', before_fixture, before_fixture),
                           ('README.md', before_readme, readme.encode('utf-8'))]:
        diffs.extend(difflib.diff_bytes(difflib.unified_diff, old.splitlines(keepends=True),
                     new.splitlines(keepends=True), fromfile=('v1/' + name).encode(),
                     tofile=('v2/' + name).encode()))
    write_new(HERE / 'COMPLETE_BYTE_DIFF_FROM_V1.patch', b''.join(diffs))
    dump(HERE / 'SEMANTIC_DELTA.json', {
        'helper_changed_blocks': ['signaled_exit_times', 'HeldProcess.wait post-GetExitCodeProcess'],
        'fixture_byte_identical': True, 'partial_candidate_is_not_complete_exit': True,
        'same_retained_handle_required': True, 'live_image_command_and_two_confirmations_unchanged': True,
        'exited_image_query_removed': True, 'actual_pid_and_raw_creation_checked': True,
        'positive_actual_exit_filetime_required': True, 'integer_epoch_conversion_unchanged': True,
        'fresh_pid_or_selfreport_fallback': False, 'handle_rights_unchanged': True,
        'old_attempt_replay_or_deletion': False, 'fixture_executed': False, 'windows_api_executed': False,
        'scientific_source_or_gate_changed': False, 'source_adoption_issued': False, 'execution_released': False,
        'current_host_compatibility_validated': False})
    failure_paths = [OUTER / 'OUTER_FAILURE.json', OUTER / 'outer_0022_wait_result.json',
                     OUTER / 'OUTER_RETURN_INTENT_AND_CLEANUP.json', OUTER / 'controller.stderr.log',
                     INNER / 'zero' / 'launcher_0004_wait_result.json', INNER / 'zero' / 'launcher_0005_failure.json',
                     INNER / 'zero' / 'controller_0028_wait_result.json', INNER / 'zero' / 'controller_0029_failure.json',
                     INNER / 'parent_0011_failure.json']
    dump(HERE / 'FAILURE_INPUT_BINDINGS.json', {
        'scope': 'Selected actual v1 failure records, not full runtime adoption or reconstructed exit status',
        'files': [binding(p) for p in failure_paths], 'v1_and_outer_attempts_unchanged': True,
        'v1_nonzero17_exists': (INNER / 'nonzero17').exists(),
        'v1_zero_result_exists': (INNER / 'zero' / 'result.json').exists(),
        'v1_return_intent_exists': (INNER / 'return_intent.json').exists()})
    dump(HERE / 'OFFICIAL_REFERENCE_SCOPE.json', {
        'read_during_this_preparation': True, 'runtime_api_test': False,
        'urls': ['https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocessid',
                 'https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes',
                 'https://learn.microsoft.com/en-us/windows/win32/procthread/terminating-a-process'],
        'inference': 'A continuously retained handle permits querying the same process object after signaled wait; proposed PID/creation/exit checks avoid dependence on exited image lookup.',
        'limit': 'Primary documentation supports the proposal, not current-host runtime success or arbitrary Windows compatibility.'})
    names = ['windows_process_evidence.py', 'benign_fixture.py', 'README.md', 'SEMANTIC_DELTA.json',
             'COMPLETE_BYTE_DIFF_FROM_V1.patch', 'FAILURE_INPUT_BINDINGS.json',
             'OFFICIAL_REFERENCE_SCOPE.json', 'prepare_sources_offline.py']
    dump(HERE / 'SOURCE_MANIFEST.json', {
        'schema': 'native-process-evidence-source-manifest.v2',
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Bounded unexecuted post-signaled same-handle repair',
        'files': [binding(HERE / name) for name in names],
        'parent_source_bindings': [binding(OLD / n) for n in
                                   ('windows_process_evidence.py', 'benign_fixture.py', 'README.md', 'SOURCE_MANIFEST.json', 'DELIVERY.json')],
        'source_prepared': True, 'source_adopted': False, 'execution_released': False,
        'fixture_or_helper_imported': False, 'runtime_validated': False,
        'scientific_execution_or_admission': False})
    dump(HERE / 'DELIVERY.json', {
        'schema': 'native-process-evidence-source-delivery.v2',
        'source_manifest': binding(HERE / 'SOURCE_MANIFEST.json'),
        'source_prepared': True, 'source_adopted': False, 'execution_released': False,
        'fixture_attempt_exists': (HERE / 'runtime_attempt_v1').exists(),
        'helper_or_fixture_imported_or_executed': False, 'windows_api_executed': False,
        'runtime_validated': False, 'old_attempt_replayed_deleted_or_changed': False,
        'scientific_gate_or_source_changed': False, 'independent_review_required': True,
        'scope': 'New source-only repair; no exit recovery or runtime compatibility claim'})
    print(json.dumps({'prepared': True, 'helper': binding(HERE / 'windows_process_evidence.py'),
                      'fixture': binding(HERE / 'benign_fixture.py'),
                      'manifest': binding(HERE / 'SOURCE_MANIFEST.json'),
                      'delivery': binding(HERE / 'DELIVERY.json')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
