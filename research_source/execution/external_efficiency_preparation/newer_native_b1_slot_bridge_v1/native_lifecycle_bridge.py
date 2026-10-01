"""Closed native B1 single-slot lifecycle source, not an admission issuer.

No scientific or process helper is imported at module import. Every execution,
API-bearing, spawn, worker-handshake and import entry starts with unconditional
rejection. A future separately reviewed version must implement real predecessor,
boot/resource/release and shared-byte-lock authority; caller records never do so.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

HERE = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\external_efficiency_preparation\newer_native_b1_slot_bridge_v1')
PREPARATION = HERE.parent
WORKER = HERE / 'reference_worker_bridge.py'
HELPER = PREPARATION / 'newer_native_process_evidence_v2' / 'windows_process_evidence.py'
HELPER_SHA = 'cc090bec1429ab429b556200597acedfa13c33e878627155b0cc9f8098c9f5d2'
MAX_CONTROL_BYTES = 8 * 1024 * 1024
ACK_SECONDS = 45
WAIT_MS = 60000
MISSING_ISSUER = (
    'actual predecessor completion and separately captured exits',
    'current boot-bound exact release and immutable adopted source authority',
    'fresh complete GPU query and integer available commit resource gates',
    'retained shared persistent first-byte GPU lock through all descendants',
    'reviewed scientific native redirector/interpreter bootstrap validation',
)


class ClosedExecutionGate(RuntimeError):
    pass


def _closed_execution_admission(*args, **kwargs):
    raise ClosedExecutionGate('Native B1 lifecycle v1 is source-only: ' + '; '.join(MISSING_ISSUER))


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def parse(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, 'Duplicate JSON key')
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(RuntimeError('Nonfinite JSON')))


def require_descriptor(record):
    require(type(record) is dict and set(record) == {'path', 'bytes', 'sha256'},
            'Exact byte descriptor required')
    require(type(record['bytes']) is int and 0 <= record['bytes'] <= MAX_CONTROL_BYTES,
            'Bounded small control/source descriptor required')
    require(type(record['path']) is str and Path(record['path']).is_absolute(), 'Absolute path required')
    require(type(record['sha256']) is str and len(record['sha256']) == 64 and
            all(c in '0123456789abcdef' for c in record['sha256']), 'Exact SHA256 required')


def read_bound(record):
    _closed_execution_admission(record)
    require_descriptor(record)
    path = Path(record['path'])
    require(path == path.resolve(strict=True), 'Resolved path required')
    before = path.stat()
    require(before.st_size == record['bytes'], 'Actual size differs before content read')
    with path.open('rb') as f:
        raw = f.read(record['bytes'] + 1)
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'File changed while read')
    require(len(raw) == record['bytes'] and digest(raw) == record['sha256'], 'Actual bytes differ')
    return raw


def file_descriptor(path):
    _closed_execution_admission(path)
    path = Path(path).resolve(strict=True)
    before = path.stat()
    require(before.st_size <= MAX_CONTROL_BYTES, 'Only bounded control/source bytes are handled here')
    with path.open('rb') as f:
        raw = f.read(MAX_CONTROL_BYTES + 1)
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'File changed while read')
    require(len(raw) == after.st_size and len(raw) <= MAX_CONTROL_BYTES, 'Actual bounded size required')
    return {'path': str(path), 'bytes': len(raw), 'sha256': digest(raw)}


def write_new_json(path, value):
    _closed_execution_admission(path, value)
    raw = canonical(value) + b'\n'
    with Path(path).open('xb') as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    return file_descriptor(path)


def read_unbound_small(path):
    _closed_execution_admission(path)
    # Discovery only. Its value becomes usable solely after exact bound reread.
    path = Path(path).resolve(strict=True)
    before = path.stat()
    require(before.st_size <= MAX_CONTROL_BYTES, 'Oversize discovery control')
    with path.open('rb') as f:
        raw = f.read(MAX_CONTROL_BYTES + 1)
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'Discovery file changed')
    require(len(raw) == after.st_size and len(raw) <= MAX_CONTROL_BYTES, 'Invalid discovery size')
    return raw, parse(raw)


def verify_original_prepared(prepared):
    require(type(prepared) is dict, 'Original prepared mapping required')
    body = dict(prepared)
    seal = body.pop('payload_sha256', None)
    require(type(seal) is str and digest(canonical(body)) == seal, 'Original prepared seal differs')
    require(type(prepared['settings']['batch_size']) is int and
            prepared['settings']['batch_size'] == 16, 'Original batch16 required')


def validate_spec_data(spec, request, prepared, bootstrap):
    """Pure candidate consistency only; none of these records grant execution."""
    require(type(spec) is dict and set(spec) == {
        'schema', 'method', 'seed', 'nonce', 'run_name', 'request', 'prepared',
        'bootstrap', 'handshake_directory', 'worker_control_directory', 'native_directory', 'guardian_exchange'},
        'Exact single-slot spec keys required')
    require(spec['schema'] == 'newer-native-b1-guardian-slot-candidate.v1', 'Wrong slot schema')
    require(spec['method'] in ('CAMP', 'DAC') and type(spec['seed']) is int and
            spec['seed'] in (1, 2, 3), 'One of six method-seed slots required')
    require(type(spec['nonce']) is str and len(spec['nonce']) == 64 and
            all(c in '0123456789abcdef' for c in spec['nonce']), 'Fresh declared nonce required')
    expected_name = spec['method'].lower() + '_seed' + str(spec['seed']) + '_' + spec['nonce']
    require(spec['run_name'] == expected_name, 'Exact method-seed-nonce run name required')
    for name in ('request', 'prepared', 'bootstrap', 'guardian_exchange'):
        require_descriptor(spec[name])
    require(type(request) is dict and request['schema'] == 'newer-native-b1-request.v1' and
            request['method'] == spec['method'] and type(request['seed']) is int and
            request['seed'] == spec['seed'] and request['prepared'] == spec['prepared'],
            'Request/slot/original prepared association differs')
    verify_original_prepared(prepared)
    require(type(bootstrap) is dict and set(bootstrap) == {
        'schema', 'topology', 'launcher_image', 'interpreter_image',
        'controller_image', 'controller_complete_command',
        'launcher_complete_command', 'interpreter_complete_command',
        'worker_source', 'controller_source', 'process_helper_source', 'guardian_exchange_source'},
        'Exact bootstrap declaration required')
    require(bootstrap['schema'] == 'newer-native-b1-guardian-bootstrap-candidate.v1' and
            bootstrap['topology'] == 'distinct_native_redirector_child', 'Only strict two-PID topology supported')
    for name in ('launcher_image', 'interpreter_image', 'controller_image', 'worker_source', 'controller_source', 'process_helper_source'):
        require_descriptor(bootstrap[name])
    require(bootstrap['launcher_image']['path'] == prepared['python'],
            'Predeclared launcher must be exact original prepared Python')
    require(prepared['runtime']['executable'] == prepared['python'] and
            bootstrap['launcher_image']['sha256'] == prepared['runtime']['interpreter_sha256'],
            'Predeclared launcher path/SHA must match frozen original runtime executable/interpreter SHA')
    for name in ('launcher_complete_command', 'interpreter_complete_command', 'controller_complete_command'):
        require(type(bootstrap[name]) is str and bootstrap[name] and '\x00' not in bootstrap[name],
                'Separate complete predeclared native commands required')
    require(bootstrap['launcher_image']['path'] != bootstrap['interpreter_image']['path'],
            'Distinct predeclared launcher and base interpreter images required')
    require(Path(bootstrap['worker_source']['path']) == WORKER and
            Path(bootstrap['controller_source']['path']) == HERE / 'native_lifecycle_bridge.py' and
            Path(bootstrap['process_helper_source']['path']) == HELPER and
            bootstrap['process_helper_source']['sha256'] == HELPER_SHA,
            'Exact new worker/controller and previously reviewed helper source required')
    require_descriptor(bootstrap['guardian_exchange_source'])
    require(bootstrap['guardian_exchange_source']['path'] == str(HERE / 'guardian_exchange.py'), 'Exact new exchange source required')
    handshake = Path(spec['handshake_directory'])
    body = Path(spec['worker_control_directory'])
    native = Path(spec['native_directory'])
    require(all(type(spec[k]) is str and Path(spec[k]).is_absolute() for k in
                ('handshake_directory', 'worker_control_directory', 'native_directory')), 'Absolute output roots required')
    require(handshake.parent == HERE / 'runs' / spec['run_name'] and handshake.name == 'handshake',
            'Lifecycle handshake must be separate from original body control')
    require(body.parent == WORKER.parent / 'worker_runs' and body.name == spec['run_name'], 'Fresh worker control path differs')
    original_root = {'CAMP': 'camp_independent_evaluation_v3', 'DAC': 'dac_independent_evaluation_v2'}[spec['method']]
    require(native.parent == PREPARATION.parent / original_root / 'b1_reference_runs' and
            native.name == spec['run_name'], 'Exact registered original native output root required')
    return {'candidate_consistency_only': True, 'execution_permission': False,
            'native_venv_validated': False, 'measurement_admitted': False}


def worker_argv(spec, bootstrap):
    return [bootstrap['launcher_image']['path'], '-B', bootstrap['worker_source']['path'],
            '--native-spec-binding', str(Path(spec['handshake_directory']) / 'spec_binding.json')]


def _load_process_helper():
    _closed_execution_admission()
    require(file_descriptor(HELPER)['sha256'] == HELPER_SHA, 'Reviewed process helper bytes differ')
    spec = importlib.util.spec_from_file_location('_new_native_b1_process_helper', HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_runtime_spec(spec_record):
    _closed_execution_admission(spec_record)
    raw = read_bound(spec_record)
    spec = parse(raw)
    request_raw = read_bound(spec['request'])
    prepared_raw = read_bound(spec['prepared'])
    bootstrap_raw = read_bound(spec['bootstrap'])
    request, prepared, bootstrap = map(parse, (request_raw, prepared_raw, bootstrap_raw))
    require(raw == canonical(spec) + b'\n' and request_raw == canonical(request) + b'\n' and
            bootstrap_raw == canonical(bootstrap) + b'\n', 'Canonical spec/request/bootstrap plus one LF required')
    validate_spec_data(spec, request, prepared, bootstrap)
    for name in ('launcher_image', 'interpreter_image', 'controller_image', 'worker_source', 'controller_source', 'process_helper_source'):
        read_bound(bootstrap[name])
    exchange = _load_guardian_exchange(spec)
    exchange._read_exchange(spec)
    require(os.path.samefile(prepared['python'], bootstrap['launcher_image']['path']), 'Launcher alias differs')
    require(subprocess.list2cmdline(worker_argv(spec, bootstrap)) == bootstrap['launcher_complete_command'],
            'Exact Popen command differs from independently predeclared bootstrap')
    return raw, spec, request_raw, request, prepared, bootstrap


def _wait_control_file(path, seconds):
    _closed_execution_admission(path, seconds)
    require(type(seconds) is int and 0 < seconds <= ACK_SECONDS, 'Bounded control wait required')
    deadline = time.monotonic() + seconds
    while not Path(path).exists():
        if time.monotonic() >= deadline:
            raise TimeoutError('ACK/identity timeout; preserve partial slot, no retry')
        time.sleep(0.05)
    return read_unbound_small(path)


def _load_guardian_exchange(specification):
    _closed_execution_admission(specification)
    path = HERE / 'guardian_exchange.py'
    bootstrap = parse(read_bound(specification['bootstrap']))
    require_descriptor(bootstrap['guardian_exchange_source'])
    require(bootstrap['guardian_exchange_source']['path'] == str(path), 'Exact declared exchange module required')
    read_bound(bootstrap['guardian_exchange_source'])
    spec = importlib.util.spec_from_file_location('_new_b1_guardian_exchange', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(Path(module.__file__).resolve() == path.resolve(strict=True), 'Exact new guardian exchange source required')
    return module


def _final_admission_before_ack(spec_record, spec, bootstrap, h, api, ledger, me, launcher, interpreter):
    _closed_execution_admission(spec_record, spec, bootstrap, h, api, ledger, me, launcher, interpreter)
    exchange = _load_guardian_exchange(spec)
    return exchange._controller_preack(h, api, ledger, me, launcher, interpreter, spec_record, spec, bootstrap)

def final_admission_relation(record, value, spec_record, spec, identities):
    """Pure association of NEW proposed grant, still no execution authority."""
    require_descriptor(record)
    require(type(value) is dict and set(value) == {
        'schema', 'spec', 'request', 'bootstrap', 'nonce', 'release', 'authority_root',
        'guardian_identity', 'controller_identity', 'launcher_identity', 'interpreter_identity',
        'resource', 'actual_retained_lock_identity', 'execute_original_reference', 'measurement_admitted', 'scope'},
        'Exact distinct guardian proposed grant keys required; old eight-field candidate rejected')
    require(value['schema'] == 'newer-native-b1-guardian-preack-grant-proposal.v1' and
            value['spec'] == spec_record and value['request'] == spec['request'] and
            value['bootstrap'] == spec['bootstrap'] and value['nonce'] == spec['nonce'] and
            value['execute_original_reference'] is True and value['measurement_admitted'] is False,
            'Proposed grant saved association differs')
    for name in ('controller', 'launcher', 'interpreter'):
        require(value[name + '_identity'] == identities[name], 'Proposed grant captured identity differs')
    for name in ('release', 'authority_root', 'resource'):
        require_descriptor(value[name])
    return {'reference_consistency_only': True, 'execution_permission': False,
            'actual_guardian_and_issuer_validation_required': True}

def _confirm_controller_live(controller, bootstrap):
    _closed_execution_admission(controller, bootstrap)
    values = []
    for index in range(2):
        value = controller.snapshot()
        require(value['pid'] == controller.identity['pid'] and
                value['creation_filetime_100ns'] == controller.identity['creation_filetime_100ns'] and
                value['creation_utc_ticks'] == controller.identity['creation_utc_ticks'],
                'Controller held creation identity differs')
        require(value['command_line'] == bootstrap['controller_complete_command'] and
                os.path.samefile(value['image'], bootstrap['controller_image']['path']),
                'Controller actual image/complete command differs from predeclared bootstrap')
        values.append(value)
        if index == 0:
            time.sleep(0.25)
    require(values[0] == values[1], 'Two complete controller observations differ')
    return values


def _worker_validate_ack_live(h, api, ledger, me, self_snapshot, spec_record, raw, spec,
                              request_raw, bootstrap, ack, ready_record):
    _closed_execution_admission(h, api, ledger, me, self_snapshot, spec_record, raw, spec,
                                request_raw, bootstrap, ack, ready_record)
    parents = []
    try:
        controller = h.HeldProcess(api, ack['controller_identity']['pid'], ledger, 'controller_worker_observer')
        parents.append(controller)
        require(controller.identity == ack['controller_identity'], 'ACK controller actual held identity differs')
        controller_observations = _confirm_controller_live(controller, bootstrap)
        require(controller_observations == ack['controller_observations'], 'ACK controller current observations differ')
        launcher = h.HeldProcess(api, ack['launcher_identity']['pid'], ledger, 'launcher_worker_observer')
        parents.append(launcher)
        require(launcher.identity == ack['launcher_identity'], 'ACK launcher actual held identity differs')
        launcher_observations = launcher.confirm_twice(bootstrap['launcher_complete_command'],
                                                     bootstrap['launcher_image']['path'], controller)
        require(launcher_observations == ack['launcher_observations'], 'ACK launcher parent/command/image observations differ')
        interpreter_observations = me.confirm_twice(bootstrap['interpreter_complete_command'],
                                                   bootstrap['interpreter_image']['path'], launcher)
        require(interpreter_observations == ack['interpreter_observations'] and
                interpreter_observations[-1] == self_snapshot, 'ACK interpreter creation/parent/command/image differs')
        for name in ('launcher_image', 'interpreter_image', 'controller_image',
                     'worker_source', 'controller_source', 'process_helper_source'):
            read_bound(bootstrap[name])
        require(read_bound(spec_record) == raw and read_bound(spec['request']) == request_raw and
                read_bound(spec['bootstrap']) == canonical(bootstrap) + b'\n' and ack['ready'] == ready_record,
                'Actual source/bootstrap/spec/request bytes changed after ACK')
        final_raw = read_bound(ack['final_admission'])
        final_admission_relation(ack['final_admission'], parse(final_raw), spec_record, spec, {
            'controller': controller.identity, 'launcher': launcher.identity, 'interpreter': me.identity})
        exchange = _load_guardian_exchange(spec)
        exchange._worker_validate_grant(h, api, ledger, me, spec_record, spec, bootstrap, ack['final_admission'])
        ledger.emit('worker_post_ack_live_chain_and_bytes_confirmed', ready=ready_record,
                    final_admission=ack['final_admission'], candidate_consistency_only=True,
                    execution_permission=False)
    finally:
        # Live references only; no exit conclusion, lock release or termination.
        errors = []
        for parent in reversed(parents):
            try:
                parent.close()
            except BaseException as error:
                errors.append({'label': parent.label, 'handle_close_error': repr(error)})
        ledger.emit('worker_live_parent_reference_cleanup_only', errors=errors,
                    captured_parent_identities=[p.identity for p in parents],
                    actual_parent_exits=[p.exit_observation for p in parents],
                    no_termination=True, lock_release_authorized=False,
                    cleanup_does_not_prove_exit=True)
        if errors:
            raise RuntimeError('Worker parent-reference cleanup incomplete; preserve partial identities')


def _cleanup_references(held, streams, ledger):
    _closed_execution_admission(held, streams, ledger)
    errors = []
    for stream in streams:
        try:
            if not stream.closed:
                stream.close()
        except BaseException as error:
            errors.append({'stream_close_error': repr(error)})
    for process in reversed(held):
        try:
            process.close()
        except BaseException as error:
            errors.append({'handle_close_error': repr(error)})
    ledger.emit('reference_cleanup_only', errors=errors,
                own_streams_closed=[s.closed for s in streams],
                actual_captured_exits=[p.exit_observation for p in held],
                process_termination=False, lock_release_authorized=False,
                safe_guardian_completion_proven=False,
                unobserved_descendants_require_retained_guardian_lock_and_real_exit_review=True)
    return errors


def _run_native_slot(spec_record):
    _closed_execution_admission(spec_record)
    raw, spec, request_raw, request, prepared, bootstrap = _read_runtime_spec(spec_record)
    handshake = Path(spec['handshake_directory'])
    attempt = handshake.parent
    # A partial/empty attempt consumes this slot forever; no rollback or replay.
    require(not Path(spec['worker_control_directory']).exists() and
            not Path(spec['native_directory']).exists(), 'Original body/native outputs already exist')
    attempt.mkdir(parents=True, exist_ok=False)
    handshake.mkdir(exist_ok=False)
    h = _load_process_helper()
    api = h.WinAPI()
    ledger = h.Ledger(attempt, 'controller')
    held, streams, proc = [], [], None
    try:
        me = h.HeldProcess(api, os.getpid(), ledger, 'controller_self'); held.append(me)
        controller_observations = _confirm_controller_live(me, bootstrap)
        exchange = _load_guardian_exchange(spec)
        exchange._initial_controller_check(h, api, ledger, me, spec_record, spec, bootstrap)
        write_new_json(handshake / 'spec_binding.json', spec_record)
        argv = worker_argv(spec, bootstrap)
        out = (attempt / 'worker.stdout.log').open('xb'); streams.append(out)
        err = (attempt / 'worker.stderr.log').open('xb'); streams.append(err)
        environment = os.environ.copy()
        environment.update(prepared['settings']['thread_environment'])
        require(all(type(k) is str and type(v) is str for k, v in environment.items()), 'String environment required')
        ledger.emit('native_spawn_declaration', spec=spec_record, request=spec['request'],
                    request_raw_sha256=digest(request_raw), nonce=spec['nonce'], bootstrap=spec['bootstrap'],
                    argv=argv, full_command=subprocess.list2cmdline(argv),
                    launcher_image=bootstrap['launcher_image'], interpreter_image=bootstrap['interpreter_image'],
                    flags=['-B'], native_site_behavior_unvalidated=True,
                    scientific_admission_issuer_implemented=False)
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                close_fds=True, creationflags=subprocess.CREATE_NO_WINDOW,
                                cwd=str(WORKER.parent), env=environment)
        launcher = h.HeldProcess(api, proc.pid, ledger, 'native_launcher_external'); held.append(launcher)
        launcher_observations = launcher.confirm_twice(bootstrap['launcher_complete_command'],
                                                       bootstrap['launcher_image']['path'], me)
        ready_raw, ready = _wait_control_file(handshake / 'worker.ready.json', ACK_SECONDS)
        ready_record = file_descriptor(handshake / 'worker.ready.json')
        require(read_bound(ready_record) == ready_raw, 'Ready bytes changed before identity capture')
        require(type(ready['pid']) is int and ready['pid'] > 0 and ready['pid'] != proc.pid,
                'Distinct actual interpreter PID required; no one-PID fallback')
        interpreter = h.HeldProcess(api, ready['pid'], ledger, 'native_interpreter_external'); held.append(interpreter)
        observations = interpreter.confirm_twice(bootstrap['interpreter_complete_command'],
                                                 bootstrap['interpreter_image']['path'], launcher)
        require(ready['identity'] == interpreter.identity and ready['self_snapshot'] == observations[-1] and
                ready['request'] == spec['request'] and ready['request_raw_sha256'] == digest(request_raw) and
                ready['spec'] == spec_record and ready['spec_raw_sha256'] == digest(raw) and
                ready['nonce'] == spec['nonce'], 'Worker self-report differs from external held/raw evidence')
        require(read_bound(spec_record) == raw and read_bound(spec['request']) == request_raw,
                'Both original spec/request bytes must remain exact before ACK')
        for name in ('launcher_image', 'interpreter_image', 'controller_image', 'worker_source', 'controller_source', 'process_helper_source'):
            read_bound(bootstrap[name])
        final_admission = _final_admission_before_ack(spec_record, spec, bootstrap, h, api, ledger, me, launcher, interpreter)
        final_raw = read_bound(final_admission)
        final_admission_relation(final_admission, parse(final_raw), spec_record, spec, {
            'controller': me.identity, 'launcher': launcher.identity, 'interpreter': interpreter.identity})
        # Even a future issuer result cannot replace one final same-held snapshot.
        require(launcher.snapshot() == launcher_observations[-1] and
                interpreter.snapshot() == observations[-1], 'Native identity changed before ACK')
        ack = {
            'schema': 'newer-native-b1-guardian-external-ack-proposal.v1', 'nonce': spec['nonce'],
            'guardian_exchange': spec['guardian_exchange'],
            'spec': spec_record, 'spec_raw_sha256': digest(raw), 'request': spec['request'],
            'request_raw_sha256': digest(request_raw), 'bootstrap': spec['bootstrap'],
            'ready': ready_record, 'controller_identity': me.identity,
            'controller_observations': controller_observations,
            'launcher_identity': launcher.identity, 'interpreter_identity': interpreter.identity,
            'launcher_observations': launcher_observations, 'interpreter_observations': observations,
            'final_admission': final_admission,
            'candidate_consistency_is_not_execution_authority': True,
        }
        ack_record = write_new_json(handshake / 'controller.ack.json', ack)
        ledger.emit('ack_published_before_original_source_import', ack=ack_record, request=spec['request'])
        lexit = launcher.wait(WAIT_MS)
        iexit = interpreter.wait(WAIT_MS)
        require(lexit is not None and iexit is not None, 'Both actual held exits required; timeout preserves partial')
        require(lexit['exit_code_unsigned_dword'] == 0 and iexit['exit_code_unsigned_dword'] == 0,
                'Original worker/launcher must both actually exit zero')
        popen_code = proc.wait(timeout=0)
        ledger.emit('popen_exit_separate', exit_code=popen_code,
                    distinct_launcher_exit=lexit, distinct_interpreter_exit=iexit)
        require(type(popen_code) is int and popen_code == 0, 'Separate Popen result differs')
        for stream in streams:
            stream.close()
        logs = [h.seal_closed_log(api, attempt / name, [launcher, interpreter], streams)
                for name in ('worker.stdout.log', 'worker.stderr.log')]
        body = Path(spec['worker_control_directory'])
        candidates = {name: file_descriptor(body / name) for name in
                      ('candidate.json', 'candidate_consistency.json', 'return_intent.json')}
        require(read_bound(spec_record) == raw and read_bound(spec['request']) == request_raw,
                'Original spec/request changed during native execution')
        candidate = {
            'schema': 'newer-native-b1-lifecycle-candidate.v1', 'spec': spec_record,
            'request': spec['request'], 'request_raw_sha256': digest(request_raw),
            'nonce': spec['nonce'], 'bootstrap': spec['bootstrap'], 'ready': ready_record, 'ack': ack_record,
            'controller_identity': me.identity, 'launcher_identity': launcher.identity,
            'interpreter_identity': interpreter.identity, 'launcher_exit': lexit, 'interpreter_exit': iexit,
            'separate_popen_exit_code': popen_code, 'closed_logs': logs, 'worker_candidates': candidates,
            'actual_native_execution_would_still_need_independent_review': True,
            'controller_self_exit_proven': False, 'measurement_admitted': False,
            'fresh_full_gallery_proven': False, 'full_dataset_online_accuracy_proven': False,
            'full_t6_complete': False, 'manuscript_result': False,
        }
        candidate_record = write_new_json(attempt / 'lifecycle_candidate.json', candidate)
        return write_new_json(attempt / 'return_intent.json', {
            'candidate': candidate_record, 'return_intent': 0, 'controller_actual_exit_unknown_here': True,
            'measurement_admitted': False, 'lock_release_authorized': False})
    except BaseException as error:
        ledger.emit('failure_partial_preserved', error=repr(error), traceback=traceback.format_exc(),
                    request=spec['request'], nonce=spec['nonce'], launcher_popen_pid=proc.pid if proc else None,
                    captured_held_identities=[p.identity for p in held],
                    actual_captured_exits=[p.exit_observation for p in held],
                    no_retry=True, no_delete=True, no_termination=True,
                    closed_log_success_not_published=True, lock_release_authorized=False,
                    guardian_must_retain_locks_and_review_all_unobserved_descendants=True)
        raise
    finally:
        errors = _cleanup_references(held, streams, ledger)
        if errors:
            raise RuntimeError('Reference cleanup incomplete; preserved evidence remains partial')


def _worker_pre_science_handshake(spec_binding_path):
    _closed_execution_admission(spec_binding_path)
    raw_binding, spec_record = read_unbound_small(spec_binding_path)
    require(raw_binding == canonical(spec_record) + b'\n', 'Canonical bound spec descriptor required')
    raw, spec, request_raw, request, prepared, bootstrap = _read_runtime_spec(spec_record)
    handshake = Path(spec['handshake_directory'])
    require(Path(spec_binding_path).resolve(strict=True) == handshake / 'spec_binding.json', 'Exact handshake binding path required')
    require(not Path(spec['worker_control_directory']).exists() and not Path(spec['native_directory']).exists(),
            'Handshake must not precreate original body/native directories')
    require(not any(n.split('.')[0] in {'numpy', 'torch', 'torchvision', 'cv2', 'timm', 'albumentations', 'PIL'}
                    for n in sys.modules), 'No original/scientific imports allowed before ACK')
    h = _load_process_helper(); api = h.WinAPI(); ledger = h.Ledger(handshake, 'worker')
    me = h.HeldProcess(api, os.getpid(), ledger, 'worker_self')
    try:
        self_snapshot = me.snapshot()
        require(self_snapshot['command_line'] == bootstrap['interpreter_complete_command'] and
                os.path.samefile(self_snapshot['image'], bootstrap['interpreter_image']['path']),
                'Native worker differs from separately predeclared command/image')
        require(Path(sys.executable).resolve() == Path(prepared['python']).resolve() and
                Path(sys.prefix).resolve() == Path(prepared['runtime']['prefix']).resolve(),
                'Actual registered native sys.executable/prefix required')
        require(not sys.flags.isolated and not sys.flags.no_site and sys.dont_write_bytecode,
                'Native prepared -B behavior required; fixture -I/-S topology forbidden')
        ready_record = write_new_json(handshake / 'worker.ready.json', {
            'schema': 'newer-native-b1-worker-ready.v1', 'pid': os.getpid(), 'identity': me.identity,
            'self_snapshot': self_snapshot, 'nonce': spec['nonce'], 'spec': spec_record,
            'spec_raw_sha256': digest(raw), 'request': spec['request'], 'request_raw_sha256': digest(request_raw),
            'original_source_or_science_imported': False, 'self_report_is_not_external_identity_proof': True})
        ack_raw, ack = _wait_control_file(handshake / 'controller.ack.json', ACK_SECONDS)
        ack_record = file_descriptor(handshake / 'controller.ack.json')
        require(read_bound(ack_record) == ack_raw and ack['schema'] == 'newer-native-b1-guardian-external-ack-proposal.v1' and
                ack['guardian_exchange'] == spec['guardian_exchange'] and
                ack['nonce'] == spec['nonce'] and ack['spec'] == spec_record and
                ack['spec_raw_sha256'] == digest(raw) and ack['request'] == spec['request'] and
                ack['request_raw_sha256'] == digest(request_raw) and ack['ready'] == ready_record and
                ack['bootstrap'] == spec['bootstrap'] and ack['interpreter_identity'] == me.identity,
                'External ACK/raw request/spec/nonce/self identity association differs')
        require(ack['interpreter_observations'][-1] == self_snapshot and me.snapshot() == self_snapshot,
                'Actual held worker identity changed before original imports')
        require(ack['launcher_identity']['pid'] != me.identity['pid'] and
                self_snapshot['parent_pid'] == ack['launcher_identity']['pid'], 'ACK lacks distinct launcher parent')
        require(read_bound(spec_record) == raw and read_bound(spec['request']) == request_raw and
                read_bound(spec['bootstrap']) == canonical(bootstrap) + b'\n', 'Both sides must recheck actual original bytes')
        _worker_validate_ack_live(h, api, ledger, me, self_snapshot, spec_record, raw, spec,
                                  request_raw, bootstrap, ack, ready_record)
        ledger.emit('ack_received_before_original_source_or_scientific_import', ack=ack_record,
                    request=spec['request'], raw_request_sha256=digest(request_raw), native_execution_admitted=False)
        return {'spec': spec_record, 'ack': ack_record, 'ready': ready_record, 'request': spec['request'],
                'nonce': spec['nonce'], 'spec_raw_sha256': digest(raw), 'request_raw_sha256': digest(request_raw),
                'interpreter_identity': me.identity, 'self_snapshot': self_snapshot,
                'worker_control_directory': spec['worker_control_directory'], 'native_directory': spec['native_directory']}
    except BaseException as error:
        ledger.emit('worker_handshake_failure', error=repr(error), traceback=traceback.format_exc(),
                    actual_self_exit_unknown=True, no_retry=True, no_termination=True,
                    lock_release_authorized=False, partial_files_preserved=True)
        raise
    finally:
        # Closing a self evidence reference neither proves nor forces self exit.
        me.close()


def run_reference(*args, **kwargs):
    _closed_execution_admission(*args, **kwargs)


def admit_reference(*args, **kwargs):
    _closed_execution_admission(*args, **kwargs)


def _bridge_cli(arguments=None):
    _closed_execution_admission(arguments)
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--guardian-slot-spec', required=True)
    parser.add_argument('--guardian-control-directory', required=True)
    args = parser.parse_args(arguments)
    spec_raw, spec = read_unbound_small(args.guardian_slot_spec)
    spec_record = file_descriptor(args.guardian_slot_spec)
    require(read_bound(spec_record) == spec_raw, 'Discovered CLI spec bytes changed')
    exchange = _load_guardian_exchange(spec)
    declaration = exchange._read_exchange(spec)
    require(args.guardian_control_directory == declaration['guardian_control_directory'], 'Guardian control directory differs')
    return_record = _run_native_slot(spec_record)
    returned = parse(read_bound(return_record))
    candidate = parse(read_bound(returned['candidate']))
    require(candidate['spec'] == spec_record and candidate['request'] == spec['request'] and
            candidate['measurement_admitted'] is False, 'Preserved slot candidate differs')
    write_new_json(Path(args.guardian_control_directory) / 'slot_candidate.json', candidate)
    # This is only return intent; outer guardian must independently observe exit.
    return 0


def main(*args, **kwargs):
    _closed_execution_admission(*args, **kwargs)
    return _bridge_cli(*args, **kwargs)


if __name__ == '__main__':
    raise ClosedExecutionGate('Source-only guardian one-slot bridge; no runtime or scientific admission')
    raise SystemExit(_bridge_cli())
