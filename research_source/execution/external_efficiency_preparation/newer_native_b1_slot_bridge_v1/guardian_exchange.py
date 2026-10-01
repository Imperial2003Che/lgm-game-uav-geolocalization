"""Closed one-slot guardian IPC proposal; no execution authority is installed.

Pure functions only check saved associations. All live reads/imports/API/IPC and
CLI paths first reject. The old eight-field candidate is never an execution grant.
This adapter does not run an encoder or replace the preserved native lifecycle.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

HERE = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\external_efficiency_preparation\newer_native_b1_slot_bridge_v1')
PREP = HERE.parent
EX = PREP.parent
GUARDIAN = PREP / 'newer_native_b1_guardian_v1' / 'guardian_v3.py'
GUARDIAN_SHA = 'f2b355c93d1d3660edecece06304403dd64b06873fcf878be1cffb9f5e9a52fc'
CONTROLLER = HERE / 'native_lifecycle_bridge.py'
WORKER = HERE / 'reference_worker_bridge.py'
HELPER = PREP / 'newer_native_process_evidence_v2' / 'windows_process_evidence.py'
HELPER_SHA = 'cc090bec1429ab429b556200597acedfa13c33e878627155b0cc9f8098c9f5d2'
MAX_CONTROL = 8 * 1024 * 1024
TTL_PROPOSAL_SECONDS = 900
MIN_COMMIT = 26 * 1024 ** 3
REVIEWED_EXECUTION_AUTHORITY_PIN = None


class ClosedBridge(RuntimeError):
    __slots__ = ()


class MissingAuthority(RuntimeError):
    __slots__ = ()


def _closed(*args, **kwargs):
    raise ClosedBridge('B1 IPC bridge source-only: actual upstream, native, authority, quiet and external observer interfaces remain unvalidated')


def require(value, message):
    if not value:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(raw):
    require(type(raw) is bytes, 'Raw bytes required')
    return hashlib.sha256(raw).hexdigest()


def parse(raw):
    require(type(raw) is bytes and len(raw) <= MAX_CONTROL, 'Bounded raw JSON required')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('Nonfinite JSON: ' + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def descriptor(value):
    require(type(value) is dict and set(value) == {'path', 'bytes', 'sha256'}, 'Exact descriptor required')
    require(type(value['path']) is str and Path(value['path']).is_absolute() and '\x00' not in value['path'], 'Absolute path required')
    require(type(value['bytes']) is int and 0 <= value['bytes'] <= MAX_CONTROL, 'Strict bounded byte size required')
    require(type(value['sha256']) is str and len(value['sha256']) == 64 and
            all(c in '0123456789abcdef' for c in value['sha256']), 'SHA256 required')
    return value


def identity(value):
    require(type(value) is dict and set(value) == {'pid', 'creation_filetime_100ns', 'creation_utc_ticks', 'image'}, 'Exact held identity required')
    require(all(type(value[key]) is int and value[key] > 0 for key in ('pid', 'creation_filetime_100ns', 'creation_utc_ticks')),
            'Exact integer held identity required')
    require(value['creation_utc_ticks'] == value['creation_filetime_100ns'] + 504911232000000000 and
            type(value['image']) is str and Path(value['image']).is_absolute(), 'Held identity ticks/image differ')
    return value


def timestamp(value):
    require(type(value) is str and len(value) <= 64, 'Bounded timezone timestamp required')
    instant = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(instant.tzinfo is not None, 'Explicit timezone required')
    return instant.astimezone(timezone.utc)


def exchange_relation(value, spec):
    """Acyclic static declaration; excludes spec/plan/root/release self-hashes."""
    require(type(value) is dict and set(value) == {
        'schema', 'guardian_source', 'guardian_image', 'guardian_complete_command',
        'controller_source', 'worker_source', 'process_helper_source', 'guardian_exchange_source',
        'request', 'bootstrap', 'nonce', 'guardian_control_directory'}, 'Exact static exchange keys required')
    require(value['schema'] == 'newer-native-b1-slot-exchange-declaration-proposal.v1', 'Wrong exchange declaration schema')
    for key in ('guardian_source', 'guardian_image', 'controller_source', 'worker_source', 'process_helper_source', 'guardian_exchange_source', 'request', 'bootstrap'):
        descriptor(value[key])
    require(value['guardian_source']['path'] == str(GUARDIAN) and value['guardian_source']['sha256'] == GUARDIAN_SHA,
            'Exact authored guardian v3 source required; not adopted runtime authority')
    require(value['controller_source']['path'] == str(CONTROLLER) and value['worker_source']['path'] == str(WORKER) and
            value['process_helper_source']['path'] == str(HELPER) and value['process_helper_source']['sha256'] == HELPER_SHA,
            'Exact derivative sources and adopted helper required')
    require(value['guardian_exchange_source']['path'] == str(HERE / 'guardian_exchange.py'), 'Exact exchange module descriptor required')
    require(type(value['guardian_complete_command']) is str and value['guardian_complete_command'] and
            '\x00' not in value['guardian_complete_command'], 'Predeclared guardian complete command required')
    require(value['request'] == spec['request'] and value['bootstrap'] == spec['bootstrap'] and value['nonce'] == spec['nonce'],
            'Static exchange/request/bootstrap/nonce differs')
    path = value['guardian_control_directory']
    require(type(path) is str and Path(path).parent == GUARDIAN.parent / 'runs', 'Exact proposed guardian slot root required')
    return {'candidate_association_only': True, 'execution_permission': False}


def grant_relation(value, spec_record, spec, actual_identities):
    """Saved association only; no caller dictionary constitutes permission."""
    require(type(value) is dict and set(value) == {
        'schema', 'spec', 'request', 'bootstrap', 'nonce', 'release', 'authority_root',
        'guardian_identity', 'controller_identity', 'launcher_identity', 'interpreter_identity',
        'resource', 'actual_retained_lock_identity', 'execute_original_reference',
        'measurement_admitted', 'scope'}, 'Exact NEW guardian proposed grant required')
    require(value['schema'] == 'newer-native-b1-guardian-preack-grant-proposal.v1' and
            value['spec'] == spec_record and value['request'] == spec['request'] and value['bootstrap'] == spec['bootstrap'] and
            value['nonce'] == spec['nonce'] and value['execute_original_reference'] is True and value['measurement_admitted'] is False,
            'New grant association differs; sealed old candidate cannot grant')
    for name in ('release', 'authority_root', 'resource'):
        descriptor(value[name])
    for name in ('guardian', 'controller', 'launcher', 'interpreter'):
        identity(value[name + '_identity'])
        require(value[name + '_identity'] == actual_identities[name], 'Saved grant identity differs')
    require(len({value[name + '_identity']['pid'] for name in ('guardian', 'controller', 'launcher', 'interpreter')}) == 4,
            'Four distinct actual process identities required')
    lock_identity = value['actual_retained_lock_identity']
    require(type(lock_identity) is list and len(lock_identity) == 6 and
            all(type(x) is int and x >= 0 for x in lock_identity) and lock_identity[-1] == 639262940518466959,
            'Saved carrier identity differs; saved list is not independent proof of holding an OS lock')
    return {'reference_consistency_only': True, 'execution_permission': False,
            'independent_lock_holding_proven': False, 'measurement_admitted': False}


def _read_bound(record):
    _closed(record)
    descriptor(record)
    path = Path(record['path'])
    require(path == path.resolve(strict=True), 'Exact physical control path required')
    before = path.stat()
    require(before.st_size == record['bytes'], 'Actual size differs before bounded read')
    with path.open('rb') as stream:
        raw = stream.read(record['bytes'] + 1)
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) and
            len(raw) == record['bytes'] and digest(raw) == record['sha256'], 'Actual bound bytes changed')
    return raw


def _new_json(path, value):
    _closed(path, value)
    raw = canonical(value) + b'\n'
    require(len(raw) <= MAX_CONTROL, 'Bounded IPC record required before CreateNew')
    with Path(path).open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {'path': str(path), 'bytes': len(raw), 'sha256': digest(raw)}


def _wait_bound(path):
    _closed(path)
    deadline = time.monotonic() + 45
    while not Path(path).exists():
        if time.monotonic() >= deadline:
            raise TimeoutError('Guardian IPC timeout; preserve all partial files, never replay')
        time.sleep(0.05)
    before = Path(path).stat()
    require(before.st_size <= MAX_CONTROL, 'Bounded discovered IPC required')
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_CONTROL + 1)
    record = {'path': str(path), 'bytes': len(raw), 'sha256': digest(raw)}
    require(before.st_size == len(raw) and _read_bound(record) == raw, 'Discovered IPC bytes changed')
    return record, parse(raw)


def _read_exchange(spec):
    _closed(spec)
    raw = _read_bound(spec['guardian_exchange'])
    value = parse(raw)
    require(raw == canonical(value) + b'\n', 'Canonical static exchange plus LF required')
    exchange_relation(value, spec)
    bootstrap = parse(_read_bound(spec['bootstrap']))
    require(bootstrap['guardian_exchange_source'] == value['guardian_exchange_source'], 'Exchange dependency differs from bootstrap')
    for key in ('guardian_source', 'guardian_image', 'controller_source', 'worker_source', 'process_helper_source', 'guardian_exchange_source', 'request', 'bootstrap'):
        _read_bound(value[key])
    return value


def _check_authority(spec_record, spec, grant=None):
    _closed(spec_record, spec, grant)
    if REVIEWED_EXECUTION_AUTHORITY_PIN is None:
        raise MissingAuthority('No independently reviewed actual execution authority; caller grant/paths do not supply it')
    root = parse(_read_bound(REVIEWED_EXECUTION_AUTHORITY_PIN))
    require(root['schema'] == 'newer-native-b1-reviewed-execution-authority.v1', 'Wrong actual future authority root')
    plan = parse(_read_bound(root['plan']))
    matches = [slot for slot in plan['slots'] if slot['spec'] == spec_record]
    require(len(matches) == 1 and matches[0]['request'] == spec['request'] and
            matches[0]['bootstrap'] == spec['bootstrap'] and matches[0]['nonce'] == spec['nonce'] and
            matches[0]['method'] == spec['method'] and type(matches[0]['seed']) is int and matches[0]['seed'] == spec['seed'],
            'Reviewed root plan does not bind the exact slot')
    for record in root['predecessor_authorities']:
        _read_bound(record)
    if grant is not None:
        require(grant['authority_root'] == REVIEWED_EXECUTION_AUTHORITY_PIN and grant['release'] == matches[0]['release'],
                'Grant cannot choose its own authority or release')
        release = parse(_read_bound(grant['release']))
        require(set(release) == {'schema', 'scope', 'execute', 'guardian_source', 'authority_root', 'plan', 'slot_spec',
                                'request', 'bootstrap', 'predecessors', 'boot_utc_ticks', 'issued_utc', 'expires_utc'} and
                release['schema'] == 'newer-native-b1-guardian-release-proposal.v1' and release['execute'] is True and
                release['authority_root'] == REVIEWED_EXECUTION_AUTHORITY_PIN and release['plan'] == root['plan'] and
                release['slot_spec'] == spec_record and release['request'] == spec['request'] and release['bootstrap'] == spec['bootstrap'],
                'Exact proposed B1 release differs')
        issued, expires = timestamp(release['issued_utc']), timestamp(release['expires_utc'])
        require(issued <= datetime.now(timezone.utc) < expires and 0 < (expires - issued).total_seconds() <= TTL_PROPOSAL_SECONDS,
                'NEW proposed B1 TTL invalid; not an inherited issued contract')
        resource = parse(_read_bound(grant['resource']))
        require(type(resource['boot_utc_ticks']) is int and resource['boot_utc_ticks'] == plan['boot_utc_ticks'] == release['boot_utc_ticks'] and
                all(type(resource[key]) is int for key in ('commit_limit_bytes', 'committed_bytes', 'available_commit_bytes', 'gpu_query_exit')) and
                resource['available_commit_bytes'] == resource['commit_limit_bytes'] - resource['committed_bytes'] and
                resource['available_commit_bytes'] >= MIN_COMMIT and resource['gpu_query_exit'] == 0 and resource['gpu_rows'] == [],
                'Exact boot/integer26GiB/fully-empty GPU saved resource association differs')
        for key in ('raw_gpu_stdout', 'raw_gpu_stderr', 'raw_memory_stdout', 'raw_memory_stderr'):
            _read_bound(resource[key])
    # This adapter cannot independently query another process's retained byte
    # lock or redo historical exits. Actual reviewed guardian/outer observer
    # authority remains mandatory; this body never promotes saved arrays to it.
    return root


def _capture_guardian(h, api, ledger, controller, exchange, bootstrap):
    _closed(h, api, ledger, controller, exchange, bootstrap)
    controller_snapshot = controller.snapshot()
    guardian = h.HeldProcess(api, controller_snapshot['parent_pid'], ledger, 'bridge_actual_guardian_parent')
    try:
        guardian_values = []
        for index in range(2):
            value = guardian.snapshot()
            require(value['command_line'] == exchange['guardian_complete_command'] and
                    os.path.samefile(value['image'], exchange['guardian_image']['path']), 'Actual guardian differs from predeclared image/complete command')
            guardian_values.append(value)
            if index == 0:
                time.sleep(0.25)
        require(guardian_values[0] == guardian_values[1], 'Guardian live identity changed')
        controller.confirm_twice(bootstrap['controller_complete_command'], bootstrap['controller_image']['path'], guardian)
        return guardian, guardian_values
    except BaseException:
        guardian.close()  # evidence-reference release only; never process exit/lock release
        raise


def _initial_controller_check(h, api, ledger, me, spec_record, spec, bootstrap):
    _closed(h, api, ledger, me, spec_record, spec, bootstrap)
    exchange = _read_exchange(spec)
    _check_authority(spec_record, spec)  # hard stop BEFORE native spawn
    guardian, observations = _capture_guardian(h, api, ledger, me, exchange, bootstrap)
    try:
        return {'actual_guardian_identity': guardian.identity, 'observations': observations,
                'candidate_relation_only': True, 'current_execution_authority_not_validated': True}
    finally:
        guardian.close()


def _controller_preack(h, api, ledger, me, launcher, interpreter, spec_record, spec, bootstrap):
    _closed(h, api, ledger, me, launcher, interpreter, spec_record, spec, bootstrap)
    exchange = _read_exchange(spec)
    _check_authority(spec_record, spec)
    guardian, guardian_observations = _capture_guardian(h, api, ledger, me, exchange, bootstrap)
    try:
        launcher.confirm_twice(bootstrap['launcher_complete_command'], bootstrap['launcher_image']['path'], me)
        interpreter.confirm_twice(bootstrap['interpreter_complete_command'], bootstrap['interpreter_image']['path'], launcher)
        request = {'schema': 'newer-native-b1-guardian-preack-request-proposal.v1',
                   'spec': spec_record, 'request': spec['request'], 'bootstrap': spec['bootstrap'], 'nonce': spec['nonce'],
                   'launcher': launcher.identity, 'interpreter': interpreter.identity}
        control = Path(exchange['guardian_control_directory'])
        request_record = _new_json(control / 'preack_request.json', request)
        grant_record, grant = _wait_bound(control / 'preack_grant.json')
        actual = {'guardian': guardian.identity, 'controller': me.identity,
                  'launcher': launcher.identity, 'interpreter': interpreter.identity}
        grant_relation(grant, spec_record, spec, actual)
        _check_authority(spec_record, spec, grant)
        _read_exchange(spec)
        require(guardian.snapshot() == guardian_observations[-1], 'Actual guardian changed before ACK')
        launcher.confirm_twice(bootstrap['launcher_complete_command'], bootstrap['launcher_image']['path'], me)
        interpreter.confirm_twice(bootstrap['interpreter_complete_command'], bootstrap['interpreter_image']['path'], launcher)
        ledger.emit('guardian_grant_candidate_received_before_worker_ACK', request=request_record, grant=grant_record,
                    saved_lock_identity_is_not_independent_lock_proof=True, measurement_admitted=False)
        return grant_record
    finally:
        guardian.close()  # no Quit/Kill; actual parent exit remains external observer's job


def _worker_validate_grant(h, api, ledger, me, spec_record, spec, bootstrap, grant_record):
    _closed(h, api, ledger, me, spec_record, spec, bootstrap, grant_record)
    exchange = _read_exchange(spec)
    grant_raw = _read_bound(grant_record)
    grant = parse(grant_raw)
    _check_authority(spec_record, spec, grant)
    captured = []
    errors = []
    try:
        parent = me.snapshot()['parent_pid']
        launcher = h.HeldProcess(api, parent, ledger, 'worker_actual_launcher_parent'); captured.append(launcher)
        controller_pid = launcher.snapshot()['parent_pid']
        controller = h.HeldProcess(api, controller_pid, ledger, 'worker_actual_controller_parent'); captured.append(controller)
        guardian, observations = _capture_guardian(h, api, ledger, controller, exchange, bootstrap); captured.append(guardian)
        launcher.confirm_twice(bootstrap['launcher_complete_command'], bootstrap['launcher_image']['path'], controller)
        me.confirm_twice(bootstrap['interpreter_complete_command'], bootstrap['interpreter_image']['path'], launcher)
        grant_relation(grant, spec_record, spec, {'guardian': guardian.identity, 'controller': controller.identity,
                                                'launcher': launcher.identity, 'interpreter': me.identity})
        _read_exchange(spec)
        _check_authority(spec_record, spec, grant)
        require(_read_bound(grant_record) == grant_raw and guardian.snapshot() == observations[-1], 'Grant/guardian changed before original imports')
        return {'grant': grant_record, 'actual_guardian_identity': guardian.identity,
                'measurement_admitted': False, 'independent_lock_holding_proven': False}
    finally:
        for actor in reversed(captured):
            try:
                actor.close()
            except BaseException as error:
                errors.append({'release_reference_error': str(error), 'identity': actor.identity})
        ledger.emit('worker_guardian_reference_cleanup_only', errors=errors,
                    parent_exit_proven=False, lock_release_authorized=False)
        require(not errors, 'Parent evidence-reference cleanup failed; preserve partial and keep guardian owner')


def controller_preack(*args, **kwargs):
    _closed(*args, **kwargs)
    return _controller_preack(*args, **kwargs)


def main(*args, **kwargs):
    _closed(*args, **kwargs)


if __name__ == '__main__':
    raise ClosedBridge('No standalone IPC/runtime CLI or scientific admission')
