"""Independent saved-byte review only; never import candidate or call Windows APIs."""
import datetime
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EX = HERE.parent
OLD = EX / 'external_efficiency_preparation' / 'newer_native_process_evidence_v1'
NEW = EX / 'external_efficiency_preparation' / 'newer_native_process_evidence_v2'
OUTER1 = EX / 'newer_native_process_execution_20260930_0810'
OUTER2 = EX / 'newer_native_process_execution_v2_20260930_0820'
bindings = {}
checks = []


def raw(path):
    path = Path(path).resolve()
    size = path.stat().st_size
    if size > 100000:
        raise RuntimeError('Only named small review/source files allowed')
    with path.open('rb') as stream:
        value = stream.read(100001)
    if len(value) != size:
        raise RuntimeError('Small input size changed during read')
    item = {'path': str(path), 'bytes': size, 'sha256': hashlib.sha256(value).hexdigest()}
    prior = bindings.get(str(path))
    if prior is not None and prior != item:
        raise RuntimeError('Input changed during review')
    bindings[str(path)] = item
    return value


def read_json(path):
    return json.loads(raw(path))


def check(name, value):
    if value is not True:
        raise RuntimeError('Failed new delta check: ' + name)
    checks.append(name)


def write_new(name, value):
    value = ((json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
             if isinstance(value, dict) else value)
    with (HERE / name).open('xb') as stream:
        stream.write(value)


def diff(old, new, before, after):
    return b''.join(difflib.diff_bytes(difflib.unified_diff, old.splitlines(keepends=True),
                                    new.splitlines(keepends=True), fromfile=before, tofile=after))


def block(value, start, stop):
    begin = value.index(start)
    end = value.index(stop, begin)
    return value[begin:end]


method1 = raw(HERE / 'seal_failed_runtime_review.py')
method2 = raw(HERE / 'seal_failed_runtime_review_v2.py')
old_line = b"    paths = sorted(folder.glob(actor + '_*.json'))"
new_line = b"    paths = sorted(path for path in folder.glob(actor + '_*.json') if path.name.split('_')[1].isdigit())"
check('review sealer repair is exactly one ledger-name filter line',
      method1.count(old_line) == 1 and method1.replace(old_line, new_line, 1) == method2)
method_failure = read_json(HERE / 'REVIEW_SEALER_V1_FAILURE.json')
failed_review = read_json(HERE / 'FAILED_RUNTIME_REVIEW.json')
failed_delivery = read_json(HERE / 'FAILED_RUNTIME_DELIVERY.json')
check('preserved failed runtime report is explicitly not a passed fixture', failed_review['fixture_passed'] is False)
check('first new review sealer failure is saved as exit1', method_failure['first_exit_code'] == 1)
method_patch = diff(method1, method2, b'review-sealer-v1.py', b'review-sealer-v2.py')
write_new('FAILED_RUNTIME_REVIEW_SEALER_DIFF.patch', method_patch)
raw(HERE / 'FAILED_RUNTIME_REVIEW_SEALER_DIFF.patch')
raw(__file__)
method_report = {
    'schema': 'independent-failed-runtime-review-method-addendum.v1',
    'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'sealed_report_modified': False, 'fixture_passed': False,
    'first_review_sealer': {'actual_exit_code': 1, 'outputs_created_before_failure': False,
        'cause': 'Windows case-insensitive outer_*.json glob included OUTER_FAILURE.json; numeric ledger index conversion failed.'},
    'minimal_new_review_source': 'One saved-ledger filename filter now includes numeric second underscore fields only. Original source/failure preserved; final review sealer separately saved.',
    'final_review_sealer': {'actual_exit_code': 0, 'diagnostic_checks': failed_review['diagnostic_check_count'],
        'meaning': 'Saved-byte failure evidence checks, not successful fixture cases, Windows API tests, or scientific tests.'},
    'scope': 'This addendum discloses a new reviewer utility failure and exact one-line repair. No candidate/fixture import, Windows API, science, old suite or runtime replay.',
    'candidate_or_attempt_modified': False,
    'inputs': list(bindings.values())}
write_new('FAILED_RUNTIME_METHOD_ADDENDUM.json', method_report)
raw(HERE / 'FAILED_RUNTIME_METHOD_ADDENDUM.json')

manifest = read_json(NEW / 'SOURCE_MANIFEST.json')
delivery = read_json(NEW / 'DELIVERY.json')
check('new manifest is source-only, unreleased and runtime unvalidated',
      manifest['source_adopted'] is False and manifest['execution_released'] is False and manifest['runtime_validated'] is False)
check('producer delivery is source-only and no attempt was made during preparation',
      delivery['execution_released'] is False and delivery['runtime_validated'] is False and delivery['fixture_attempt_exists'] is False)
check('exact bounded v2 source member count', len(manifest['files']) == 8)
check('exact bounded v1 parent member count', len(manifest['parent_source_bindings']) == 5)
for item in manifest['files'] + manifest['parent_source_bindings']:
    raw(item['path'])
    check('manifest binding ' + Path(item['path']).name, bindings[str(Path(item['path']).resolve())] == item)
raw(delivery['source_manifest']['path'])
check('producer delivery binds exact manifest bytes', bindings[str((NEW / 'SOURCE_MANIFEST.json').resolve())] == delivery['source_manifest'])
old_helper, new_helper = raw(OLD / 'windows_process_evidence.py'), raw(NEW / 'windows_process_evidence.py')
old_fixture, new_fixture = raw(OLD / 'benign_fixture.py'), raw(NEW / 'benign_fixture.py')
check('fixture bytes identical and distinct directory supplies fresh HERE', old_fixture == new_fixture)
old_times = block(old_helper, b'    def signaled_exit_times(', b'    def command_line(')
new_times = block(new_helper, b'    def signaled_exit_times(', b'    def command_line(')
old_wait = block(old_helper, b'    def wait(', b'    def close(')
new_wait = block(new_helper, b'    def wait(', b'    def close(')
restored = new_helper.replace(new_times, old_times, 1).replace(new_wait, old_wait, 1)
check('all helper bytes outside two post-signaled methods are unchanged', restored == old_helper)
check('removed exited image requery only from wait; live capture remains',
      b'kernel_identity(self.handle)' not in new_wait and b'kernel_identity(self.handle)' in old_wait and b'kernel_identity(self.handle)' in new_helper)
check('postsignaled function uses passed retained handle with no OpenProcess/image/command/PID lookup',
      b'GetProcessId(handle)' in new_times and b'GetProcessTimes(handle,' in new_times and
      not any(term in new_times for term in (b'OpenProcess(', b'kernel_identity(', b'command_line(', b'parent_row(')))
check('wait still requires signaled result before actual code query',
      new_wait.index(b'require(result == WAIT_OBJECT_0') < new_wait.index(b'GetExitCodeProcess') < new_wait.index(b"self.ledger.emit('exit_candidate'"))
check('incomplete code candidate persisted before times and complete assignment',
      new_wait.index(b"self.ledger.emit('exit_candidate'") < new_wait.index(b'signaled_exit_times(self.handle, self.identity') < new_wait.index(b'self.exit_observation ='))
check('PID candidate saved before zero gate', new_times.index(b"ledger.emit('signaled_pid_candidate'") < new_times.index(b'if pid == 0:'))
check('raw times candidates saved before identity and positive exit gates',
      new_times.index(b"ledger.emit('signaled_identity_times_candidate'") < new_times.index(b"require(pid == expected_identity['pid']") < new_times.index(b'require(raw_exit > 0'))
check('integer creation and epoch comparisons retained', all(term in new_times for term in
      (b"raw_creation == expected_identity['creation_filetime_100ns']", b"value['creation_utc_ticks'] == expected_identity['creation_utc_ticks']", b'FILETIME_TO_DOTNET_TICKS')))
check('retained live image provenance explicit in completed exit', b"'image_scope': 'Retained live image; not requeried after exit'" in new_wait)
patch = b''
for name in ('windows_process_evidence.py', 'benign_fixture.py', 'README.md'):
    patch += diff(raw(OLD / name), raw(NEW / name), ('v1/' + name).encode(), ('v2/' + name).encode())
check('complete producer byte diff exactly matches current v1/v2 sources and README', patch == raw(NEW / 'COMPLETE_BYTE_DIFF_FROM_V1.patch'))
failure_inputs = read_json(NEW / 'FAILURE_INPUT_BINDINGS.json')
for item in failure_inputs['files']:
    inherited = {p['path']: p for p in failed_review['inputs']}
    check('selected failed-runtime binding inherited from independent saved-byte review ' + Path(item['path']).name,
          inherited.get(item['path']) == item)
read_json(NEW / 'OFFICIAL_REFERENCE_SCOPE.json')
read_json(NEW / 'SEMANTIC_DELTA.json')
read_json(OUTER1 / 'ROOT_EXIT_REPAIR_PRIMARY_SOURCES.json')
old_outer, new_outer = raw(OUTER1 / 'run_outer.py'), raw(OUTER2 / 'run_outer.py')
check('outer preserved prior source equals actual consumed v1 source', raw(OUTER2 / 'OUTER_V1_SOURCE.py.txt') == old_outer)
old_dir, new_dir = b"'newer_native_process_evidence_v1'", b"'newer_native_process_evidence_v2'"
check('outer source delta is exactly one v1-to-v2 source-directory string',
      old_outer.count(old_dir) == 1 and old_outer.replace(old_dir, new_dir, 1) == new_outer)
outer_patch = diff(old_outer, new_outer, b'outer-v1/run_outer.py', b'outer-v2/run_outer.py')
write_new('OUTER_V1_TO_V2_COMPLETE_BYTE_DIFF.patch', outer_patch)
raw(HERE / 'OUTER_V1_TO_V2_COMPLETE_BYTE_DIFF.patch')
check('old consumed attempts still exist', (OLD / 'runtime_attempt_v1').is_dir() and (OUTER1 / 'outer_runtime_attempt_v1').is_dir())
check('new helper and outer attempts remain absent at this review instant',
      not (NEW / 'runtime_attempt_v1').exists() and not (OUTER2 / 'outer_runtime_attempt_v1').exists())
report = {
    'schema': 'independent-native-process-v2-preexec-source-review.v1',
    'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_delta_accepted': True, 'new_static_blocker_found': False,
    'execution_released': False, 'runtime_validated': False, 'fixture_passed': False,
    'scientific_execution_or_admission': False, 'candidate_imported_or_executed': False,
    'windows_api_called_by_reviewer': False, 'old_static_checker_or_suite_repeated': False,
    'method': 'Independent AI reading of complete v1/v2 helper, byte-identical fixture, producer offline derivation, complete diff, README, manifests, actual failure report and outer caller; bounded byte comparisons of the new delta only.',
    'accepted_scope': [
        'Only signaled_exit_times and wait change in helper; every other helper byte remains identical.',
        'Actual unsigned DWORD exit candidate is saved immediately after the successful code API. Same continuously held handle supplies PID/raw creation/actual exit FILETIME candidates before gates; exact retained creation identity and positive exit time required before complete observation.',
        'Exited image/command requery removed. Earlier complete live image/full-command/two-confirmation capture and minimum-rights noninheritable evidence handles are unchanged.',
        'Fixture is byte-identical. Distinct v2 HERE selects a separate single-use attempt path; consumed v1 paths remain preserved.',
        'Outer differs by exactly one source-directory string; separate controller held wait, Popen status, own stream closure, log sealing, failure preservation and no-kill behavior are unchanged.'
    ],
    'limits': [
        'This is source review, not current-host Windows runtime or successful fixture evidence. Any API/identity/log failure must still preserve a partial attempt and deny success.',
        'Neither incomplete candidate nor reported return intent is an actual exit observation; no v1 missing code/time is reconstructed.',
        'Current attempt absence is a review snapshot, not future invocation permission. Separate root execution decision and fresh checks remain required.',
        'Official Microsoft pages were read by producer/root; this reviewer reads their saved research record and makes no separate web/API validation claim.',
        'NtQueryInformationProcess class60 stays experimental on this host with no public stable-contract guarantee.',
        'Outer byte-length cap is checked after reading named inputs; accepted scope is already-known small source/review inputs, not arbitrary bounded-read enforcement.',
        'Benign ordinary-Python two-case fixture cannot validate scientific venv redirection, predecessor exits, current boot/resource/release/shared-byte-lock admission, six B1 scientific workers, full gallery/ranking/parity/timing/online CLIP, or original T6.'
    ],
    'new_delta_check_count': len(checks), 'new_delta_checks': checks,
    'inputs': list(bindings.values()), 'old_sources_or_attempts_modified': False}
write_new('V2_PREEXEC_SOURCE_REVIEW.json', report)
raw(HERE / 'V2_PREEXEC_SOURCE_REVIEW.json')
result = {'schema': 'independent-native-process-v2-source-review-delivery.v1',
          'execution_released': False, 'runtime_validated': False,
          'source_review': bindings[str((HERE / 'V2_PREEXEC_SOURCE_REVIEW.json').resolve())],
          'failed_runtime_method_addendum': bindings[str((HERE / 'FAILED_RUNTIME_METHOD_ADDENDUM.json').resolve())],
          'outer_diff': bindings[str((HERE / 'OUTER_V1_TO_V2_COMPLETE_BYTE_DIFF.patch').resolve())],
          'method_diff': bindings[str((HERE / 'FAILED_RUNTIME_REVIEW_SEALER_DIFF.patch').resolve())],
          'review_source': bindings[str(Path(__file__).resolve())],
          'new_delta_check_count': len(checks)}
write_new('V2_SOURCE_REVIEW_DELIVERY.json', result)
print(json.dumps(result, ensure_ascii=False))
