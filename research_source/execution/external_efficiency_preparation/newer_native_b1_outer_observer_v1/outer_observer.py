"""Closed external continuously-held guardian observer SOURCE proposal.

Every effect/public/private/CLI entry rejects FIRST. No execution root, runtime
guardian derivative, physical admission producer or finite quiet producer exists
here. A saved return intent cannot prove its writer's exit. Ordinary self-held
snapshots cannot prove the external observer's own eventual exit either.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

HERE = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\external_efficiency_preparation\newer_native_b1_outer_observer_v1')
PREP = HERE.parent
HELPER = PREP / 'newer_native_process_evidence_v2' / 'windows_process_evidence.py'
HELPER_PIN = {'path': str(HELPER), 'bytes': 16238,
    'sha256': 'cc090bec1429ab429b556200597acedfa13c33e878627155b0cc9f8098c9f5d2'}
REVIEWED_OUTER_EXECUTION_AUTHORITY_PIN = None
REVIEWED_GUARDIAN_RUNTIME_SOURCE_PIN = None
REVIEWED_PHYSICAL_ADMISSION_PRODUCER_PIN = None
REVIEWED_FINITE_QUIET_PRODUCER_PIN = None
MAX_CONTROL = 4 * 1024 * 1024
MAX_SOURCE = 256 * 1024
MAX_IMAGE = 64 * 1024 * 1024
MAX_CLOSED_LOG = 64 * 1024 * 1024
FILETIME_TO_UTC_TICKS = 504911232000000000
MIN_COMMIT_BYTES = 26 * 1024 ** 3
ACK_TIMEOUT_SECONDS = 45
RELEASE_TTL_SECONDS = 900
PROPOSED_ACTOR_ARGUMENTS = ('--guardian-actor', '--spec-binding')


class ClosedOuterObserver(RuntimeError):
    pass


class IncompleteOuterEvidence(RuntimeError):
    pass


def require(value, message):
    if not value:
        raise ValueError(message)


def integer(value, lower=0):
    require(type(value) is int and value >= lower, 'Exact integer required; bool/float rejected')
    return value


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def digest(raw):
    require(type(raw) is bytes, 'Actual bytes required')
    return hashlib.sha256(raw).hexdigest()


def parse(raw, maximum=MAX_CONTROL):
    require(type(raw) is bytes and len(raw) <= maximum, 'Bounded UTF8 bytes required')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('Nonfinite JSON constant: ' + value)
    return json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=pairs, parse_constant=constant)


def descriptor(value, maximum=MAX_CONTROL):
    require(type(value) is dict and set(value) == {'path', 'bytes', 'sha256'}, 'Exact source/byte binding required')
    require(type(value['path']) is str and Path(value['path']).is_absolute() and '\x00' not in value['path'], 'Absolute path required')
    integer(value['bytes'])
    require(value['bytes'] <= maximum, 'Bounded byte size required')
    require(type(value['sha256']) is str and len(value['sha256']) == 64 and
            all(c in '0123456789abcdef' for c in value['sha256']), 'Lowercase SHA256 required')
    return value


def explicit_utc(value):
    require(type(value) is str and len(value) <= 64, 'Bounded explicit time string required')
    instant = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(instant.tzinfo is not None and instant.utcoffset() is not None, 'Explicit timezone required')
    return instant.astimezone(timezone.utc)


def held_identity_relation(identity):
    require(type(identity) is dict and set(identity) == {'pid', 'creation_filetime_100ns', 'creation_utc_ticks', 'image'},
            'Exact saved held identity required')
    for key in ('pid', 'creation_filetime_100ns', 'creation_utc_ticks'):
        integer(identity[key], 1)
    require(identity['creation_utc_ticks'] == identity['creation_filetime_100ns'] + FILETIME_TO_UTC_TICKS,
            'Held birth tick systems differ')
    require(type(identity['image']) is str and Path(identity['image']).is_absolute(), 'Saved actual image required')
    return identity


def saved_exit_relation(value, identity):
    """Saved relation, not actual process/API/exit reacquisition or SCI success."""
    held_identity_relation(identity)
    require(type(value) is dict and value['identity'] == identity and type(value['wait_result']) is int and
            value['wait_result'] == 0, 'Continuously held signaled exit required')
    for key in ('pid', 'creation_filetime_100ns', 'creation_utc_ticks'):
        integer(value[key], 1)
        require(value[key] == identity[key], 'Saved actual exit identity differs')
    integer(value['exit_code_unsigned_dword'])
    require(value['exit_code_unsigned_dword'] <= 0xffffffff, 'Actual DWORD outside range')
    integer(value['exit_filetime_100ns'], 1)
    integer(value['exit_utc_ticks'], 1)
    require(value['exit_utc_ticks'] == value['exit_filetime_100ns'] + FILETIME_TO_UTC_TICKS and
            value['exit_utc_ticks'] >= identity['creation_utc_ticks'] and
            value['same_retained_handle_pid_creation_verified'] is True, 'Saved complete held birth/exit relation required')
    return {'candidate_relation_only': True, 'actual_DWORD': value['exit_code_unsigned_dword'],
            'exit_is_scientific_measurement_admission': False, 'execution_permission': False}


def bootstrap_relation(value, spec):
    require(type(value) is dict and set(value) == {'schema', 'observer_source', 'actor_source', 'guardian_runtime_source',
            'helper_source', 'observer_image', 'observer_complete_command', 'observer_parent_identity',
            'launcher_image', 'launcher_complete_command', 'interpreter_image', 'interpreter_complete_command',
            'guardian_plan', 'request', 'nonce', 'guardian_control_directory'}, 'Exact proposed bootstrap keys required')
    require(value['schema'] == 'newer-native-b1-external-guardian-bootstrap-proposal.v1', 'Wrong bootstrap proposal')
    for key in ('observer_source', 'actor_source', 'guardian_runtime_source', 'helper_source'):
        descriptor(value[key], MAX_SOURCE)
    for key in ('observer_image', 'launcher_image', 'interpreter_image'):
        descriptor(value[key], MAX_IMAGE)
    for key in ('guardian_plan', 'request'):
        descriptor(value[key])
    for key in ('observer_complete_command', 'launcher_complete_command', 'interpreter_complete_command'):
        require(type(value[key]) is str and value[key] and '\x00' not in value[key], 'Predeclared complete command required')
    held_identity_relation(value['observer_parent_identity'])
    require(value['helper_source'] == HELPER_PIN and value['guardian_plan'] == spec['guardian_plan'] and
            value['request'] == spec['request'] and value['nonce'] == spec['nonce'] and
            value['guardian_control_directory'] == spec['guardian_control_directory'], 'Bootstrap association differs')
    return {'candidate_relation_only': True, 'runtime_topology_validated': False}


def spec_relation(value):
    require(type(value) is dict and set(value) == {'schema', 'observer_source', 'actor_source', 'guardian_runtime_source',
            'guardian_plan', 'authority_root', 'request', 'bootstrap', 'release', 'boot_utc_ticks', 'nonce',
            'outer_control_directory', 'guardian_control_directory'}, 'Exact proposed observer spec keys required')
    require(value['schema'] == 'newer-native-b1-external-guardian-observer-spec-proposal.v1', 'Wrong observer spec')
    for key in ('observer_source', 'actor_source', 'guardian_runtime_source'):
        descriptor(value[key], MAX_SOURCE)
    for key in ('guardian_plan', 'authority_root', 'request', 'bootstrap', 'release'):
        descriptor(value[key])
    integer(value['boot_utc_ticks'], 1)
    require(type(value['nonce']) is str and len(value['nonce']) == 64 and
            all(c in '0123456789abcdef' for c in value['nonce']), 'Declared raw nonce required')
    require(value['observer_source'] == value['actor_source'] and
            value['observer_source']['path'] == str(HERE / 'outer_observer.py'), 'Exact one-module two-mode source required')
    outer, actor = Path(value['outer_control_directory']), Path(value['guardian_control_directory'])
    require(outer.parent == HERE / 'runs' and actor == outer / 'guardian_actor' and outer != actor,
            'Exact fresh prospective outer/actor control roots required')
    return {'candidate_relation_only': True, 'execution_permission': False}


def release_relation(value, spec, spec_record, now):
    require(type(value) is dict and set(value) == {'schema', 'scope', 'execute', 'observer_source', 'guardian_runtime_source',
            'authority_root', 'guardian_plan', 'request', 'bootstrap', 'boot_utc_ticks', 'nonce', 'issued_utc', 'expires_utc'},
            'Exact proposed outer startup release keys required')
    require(value['schema'] == 'newer-native-b1-external-guardian-observer-release-proposal.v1' and
            value['scope'] == 'external-held-guardian-observation-after-ordered-scientific-completion' and
            value['execute'] is True, 'Wrong proposed release')
    require(all(value[key] == spec[key] for key in
            ('observer_source', 'guardian_runtime_source', 'authority_root', 'guardian_plan', 'request', 'bootstrap', 'boot_utc_ticks', 'nonce')),
            'Exact source/request/boot release associations differ')
    issued, expires = explicit_utc(value['issued_utc']), explicit_utc(value['expires_utc'])
    require(type(now) is datetime and now.tzinfo is not None and issued <= now.astimezone(timezone.utc) < expires and
            0 < (expires - issued).total_seconds() <= RELEASE_TTL_SECONDS, 'Fresh proposed startup release required')
    return {'saved_relation_only': True, 'execution_permission': False, 'new_proposal_not_issued_release': True}


def admission_relation(value, spec, raw_gpu, raw_memory):
    """Saved byte/tick arithmetic only. An actual pinned producer is still owed."""
    require(type(value) is dict and set(value) == {'schema', 'producer_source', 'execution_root', 'spec', 'boot_utc_ticks',
            'sample_start_utc', 'sample_end_utc', 'available_commit_bytes', 'commit_limit_bytes', 'committed_bytes',
            'gpu_query_exit_code', 'gpu_rows', 'raw_gpu_stdout', 'raw_gpu_stderr', 'raw_memory_stdout', 'raw_memory_stderr'},
            'Exact resource proposal required')
    require(value['schema'] == 'newer-native-b1-external-observer-physical-admission-proposal.v1' and
            value['boot_utc_ticks'] == spec['boot_utc_ticks'], 'Saved current boot association differs')
    for key in ('boot_utc_ticks', 'available_commit_bytes', 'commit_limit_bytes', 'committed_bytes'):
        integer(value[key])
    require(type(value['gpu_query_exit_code']) is int and value['gpu_query_exit_code'] == 0 and
            type(value['gpu_rows']) is list and value['gpu_rows'] == [], 'Completely empty successful GPU query required')
    require(type(raw_gpu) is bytes and not any(line.strip() for line in raw_gpu.decode('utf-8', errors='strict').splitlines()),
            'Actual captured raw GPU stdout is not empty')
    memory = parse(raw_memory)
    require(type(memory) is dict and set(memory) == {'boot_utc_ticks', 'commit_limit_bytes', 'committed_bytes', 'available_commit_bytes'},
            'Exact raw actual memory schema required')
    require(all(type(memory[key]) is int and memory[key] == value[key] for key in memory), 'Raw integer memory fields differ')
    require(value['available_commit_bytes'] == value['commit_limit_bytes'] - value['committed_bytes'] and
            value['available_commit_bytes'] >= MIN_COMMIT_BYTES, 'Integer26GiB admission required')
    require(explicit_utc(value['sample_start_utc']) <= explicit_utc(value['sample_end_utc']), 'Admission time reversed')
    return {'saved_relation_only': True, 'physical_resource_authority_established': False, 'execution_permission': False}


@dataclass
class ObserverContext:
    helper: object
    api: object
    ledger: object
    me: object
    parent: object
    directory: Path
    spec_record: dict
    spec: dict
    bootstrap: dict
    root: dict
    processes: list = field(default_factory=list)
    popen_processes: list = field(default_factory=list)
    streams: list = field(default_factory=list)
    finite_unobserved_descendants: bool = False
    diagnostic_failures: list = field(default_factory=list)
    diagnostic_failure_count: int = 0


def _read_bound(record, maximum=MAX_CONTROL):
    raise ClosedOuterObserver('Closed bounded source/evidence read entry; no execution authority exists')
    descriptor(record, maximum)
    path = Path(record['path'])
    require(path.stat().st_size == record['bytes'], 'Actual size differs before read')
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        raw = stream.read(record['bytes'] + 1)
        after = os.fstat(stream.fileno())
    require(len(raw) == record['bytes'] and (before.st_size, before.st_mtime_ns, before.st_ino) ==
            (after.st_size, after.st_mtime_ns, after.st_ino), 'Actual bounded bytes changed')
    require(digest(raw) == record['sha256'], 'Actual SHA differs')
    return raw


def _new_record(path, value):
    raise ClosedOuterObserver('Closed CreateNew control writer; no attempt/request/READY/ACK is permitted now')
    raw = canonical(value) + b'\n'
    require(len(raw) <= MAX_CONTROL, 'Bounded new record required')
    with Path(path).open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {'path': str(Path(path).resolve()), 'bytes': len(raw), 'sha256': digest(raw)}


def _discover_control(path, seconds):
    raise ClosedOuterObserver('Closed raw IPC reader; waiting is not an execution or scientific grant')
    require(type(seconds) is int and 1 <= seconds <= ACK_TIMEOUT_SECONDS, 'Bounded IPC wait required')
    deadline = time.monotonic() + seconds
    while not path.exists():
        if time.monotonic() >= deadline:
            raise TimeoutError('External guardian IPC deadline expired; no retry')
        time.sleep(0.05)
    stat = path.stat()
    require(1 <= stat.st_size <= MAX_CONTROL, 'Bounded actual control size required')
    with path.open('rb') as stream:
        raw = stream.read(stat.st_size + 1)
        after = os.fstat(stream.fileno())
    require(len(raw) == stat.st_size == after.st_size and stat.st_mtime_ns == after.st_mtime_ns,
            'Control file partial/changed')
    record = {'path': str(path.resolve()), 'bytes': len(raw), 'sha256': digest(raw)}
    require(_read_bound(record) == raw, 'Control raw binding changed')
    value = parse(raw)
    require(raw == canonical(value) + b'\n', 'Exact canonical raw IPC plus LF required')
    return record, raw, value


def _load_bound_module(record, label):
    raise ClosedOuterObserver('Closed fixed-source import entry; no guardian/producer/helper import is authorized')
    _read_bound(record, MAX_SOURCE)
    spec = importlib.util.spec_from_file_location(label, record['path'])
    module = importlib.util.module_from_spec(spec)
    sys.modules[label] = module
    spec.loader.exec_module(module)
    require(os.path.samefile(module.__file__, record['path']), 'Loaded source is not exact bound file')
    return module


def _execution_authority(spec_record, spec):
    raise ClosedOuterObserver('Closed independent authority entry; caller/self records do not issue authority')
    if any(pin is None for pin in (REVIEWED_OUTER_EXECUTION_AUTHORITY_PIN, REVIEWED_GUARDIAN_RUNTIME_SOURCE_PIN,
            REVIEWED_PHYSICAL_ADMISSION_PRODUCER_PIN, REVIEWED_FINITE_QUIET_PRODUCER_PIN)):
        raise IncompleteOuterEvidence('Independent issuer, guardian derivative, physical admission and finite quiet producer pins are missing')
    require(spec['authority_root'] == REVIEWED_OUTER_EXECUTION_AUTHORITY_PIN and
            spec['guardian_runtime_source'] == REVIEWED_GUARDIAN_RUNTIME_SOURCE_PIN,
            'Exact reviewed runtime source/root differs')
    root_raw = _read_bound(REVIEWED_OUTER_EXECUTION_AUTHORITY_PIN)
    root = parse(root_raw)
    require(root_raw == canonical(root) + b'\n' and root['schema'] == 'newer-native-b1-external-observer-execution-root-proposal.v1' and
            root['execution_released'] is True and root['observer_source'] == spec['observer_source'] and
            root['guardian_runtime_source'] == spec['guardian_runtime_source'] and
            root['guardian_plan'] == spec['guardian_plan'] and root['request'] == spec['request'] and
            root['bootstrap'] == spec['bootstrap'] and root['nonce'] == spec['nonce'] and
            root['outer_control_directory'] == spec['outer_control_directory'] and
            root['guardian_control_directory'] == spec['guardian_control_directory'] and
            root['boot_utc_ticks'] == spec['boot_utc_ticks'] and
            root['physical_admission_producer'] == REVIEWED_PHYSICAL_ADMISSION_PRODUCER_PIN and
            root['finite_quiet_producer'] == REVIEWED_FINITE_QUIET_PRODUCER_PIN,
            'Separately adopted exact runtime execution associations required')
    # Acyclic proposal: early execution root binds common immutable inputs, nonce
    # and exact directories; later release binds that root/common inputs; final
    # spec binds both descriptors. Root/release never hash the final spec or each
    # other back. Their absent real issuer remains a separate current hard stop.
    require(root['operative_predecessor_adjudication'] is not None and root['all_six_ordered_roles_scientifically_adopted'] is True,
            'Inactive role proposal/unknown historical primary own-exit cannot supply operational adjudication')
    _verify_six_predecessors(root['operative_predecessor_adjudication'])
    for key in ('observer_source', 'guardian_runtime_source', 'physical_admission_producer', 'finite_quiet_producer'):
        _read_bound(root[key], MAX_SOURCE)
    return root


def _verify_six_predecessors(policy_record):
    raise ClosedOuterObserver('Closed six-role raw adjudication reader; inactive proposal or missing historical exit is not operational authority')
    policy_raw = _read_bound(policy_record)
    policy = parse(policy_raw)
    require(policy_raw == canonical(policy) + b'\n' and
            policy['schema'] == 'newer-native-b1-operative-six-role-policy-proposal.v1' and policy['operative'] is True and
            policy['absence_is_exit_proof'] is False and type(policy['adjudications']) is list and
            len(policy['adjudications']) == 6, 'Independently adopted operative finite six-role policy required')
    roles = ('primary', 'pipeline7', 'extension4', 'authors20', 'independent9fit42eval', 'extra_DAC3fit30eval')
    for role, record in zip(roles, policy['adjudications']):
        adjudication = parse(_read_bound(record))
        require(adjudication['schema'] == 'b1-predecessor-adjudication.v1' and adjudication['role'] == role and
                adjudication['science_adopted'] is True and adjudication['scope_complete'] is True and
                adjudication['exit_requirement_adjudicated'] is True and adjudication['absence_is_exit_proof'] is False,
                'Actual role-scoped scientific completion/exit adjudication missing')
        for key in ('status', 'original_spec', 'original_plan', 'source_authority'):
            _read_bound(adjudication[key])
        require(type(adjudication['required_actual_exits']) is list, 'Applicable original-role exit records required')
        # An independently adjudicated role list is not fabricated here. In
        # particular, absence never supplies primary own exit0; historical own
        # exit remains unknown unless genuine original captured evidence exists.
        for item in adjudication['required_actual_exits']:
            saved = parse(_read_bound(item['record']))
            saved_exit_relation(saved, item['identity'])
            require(saved['exit_code_unsigned_dword'] == 0, 'Actual required predecessor exit is nonzero')
    return {'actual_saved_role_bindings_reread': True, 'historical_exit_reacquired': False,
            'missing_historical_primary_exit_fabricated': False}


def _read_spec(spec_record):
    raise ClosedOuterObserver('Closed spec reader; no live runtime plan/bootstrap/request is prepared by this source')
    raw = _read_bound(spec_record)
    spec = parse(raw)
    require(raw == canonical(spec) + b'\n', 'Canonical actual spec plus LF required')
    spec_relation(spec)
    request_raw = _read_bound(spec['request'])
    request = parse(request_raw)
    require(request_raw == canonical(request) + b'\n' and request['schema'] == 'newer-native-b1-external-guardian-start-request-proposal.v1' and
            request['nonce'] == spec['nonce'] and request['guardian_plan'] == spec['guardian_plan'] and
            request['guardian_runtime_source'] == spec['guardian_runtime_source'] and
            request['boot_utc_ticks'] == spec['boot_utc_ticks'], 'Raw request/source/boot/nonce associations differ')
    bootstrap_raw = _read_bound(spec['bootstrap'])
    bootstrap = parse(bootstrap_raw)
    require(bootstrap_raw == canonical(bootstrap) + b'\n', 'Canonical actual bootstrap required')
    bootstrap_relation(bootstrap, spec)
    require(bootstrap['observer_source'] == spec['observer_source'] and bootstrap['actor_source'] == spec['actor_source'] and
            bootstrap['guardian_runtime_source'] == spec['guardian_runtime_source'], 'Exact bootstrap source bindings differ')
    root = _execution_authority(spec_record, spec)
    return raw, spec, request_raw, request, bootstrap_raw, bootstrap, root


def _fresh_physical_admission(context, phase):
    raise ClosedOuterObserver('Closed physical admission producer; no caller array or historical snapshot may grant startup')
    producer = _load_bound_module(REVIEWED_PHYSICAL_ADMISSION_PRODUCER_PIN, 'closed_outer_physical_admission')
    # New fixed-source interface is NOT implemented/installed by sealed sources.
    # A future separately adopted real producer owns actual full queries, current
    # boot and integer commit evidence. Caller-held identities are associations,
    # not resource authority; the returned bytes are reread by exact binding.
    resource_record = producer.collect_actual_outer_guardian_admission(
        REVIEWED_OUTER_EXECUTION_AUTHORITY_PIN, context.spec_record, phase)
    raw = _read_bound(resource_record)
    resource = parse(raw)
    require(raw == canonical(resource) + b'\n' and resource['producer_source'] == REVIEWED_PHYSICAL_ADMISSION_PRODUCER_PIN and
            resource['execution_root'] == REVIEWED_OUTER_EXECUTION_AUTHORITY_PIN and resource['spec'] == context.spec_record,
            'Actual pinned admission producer/source/root associations differ')
    raw_gpu = _read_bound(resource['raw_gpu_stdout'])
    raw_memory = _read_bound(resource['raw_memory_stdout'])
    _read_bound(resource['raw_gpu_stderr'])
    _read_bound(resource['raw_memory_stderr'])
    admission_relation(resource, context.spec, raw_gpu, raw_memory)
    now = datetime.now(timezone.utc)
    require(explicit_utc(resource['sample_end_utc']) <= now and
            (now - explicit_utc(resource['sample_end_utc'])).total_seconds() <= 5,
            'Actual physical admission is no longer current')
    release_relation(parse(_read_bound(context.spec['release'])), context.spec, context.spec_record, now)
    return resource_record


def _capture_interpreter(context, launcher, ready):
    raise ClosedOuterObserver('Closed external retained interpreter capture; raw self-report is not identity proof')
    held_identity_relation(ready['interpreter_identity'])
    require(ready['interpreter_identity']['pid'] != launcher.identity['pid'], 'Two distinct actual guardian actors required')
    interpreter = context.helper.HeldProcess(context.api, ready['interpreter_identity']['pid'], context.ledger,
                                             'external_guardian_interpreter')
    context.processes.append(interpreter)
    require(interpreter.identity == ready['interpreter_identity'], 'Raw READY differs from independent held birth/image')
    observations = interpreter.confirm_twice(context.bootstrap['interpreter_complete_command'],
        context.bootstrap['interpreter_image']['path'], launcher)
    return interpreter, observations


def _actual_finite_quiet(context):
    raise ClosedOuterObserver('Closed independently produced finite quiet boundary; current rows are not historical exit proof')
    producer = _load_bound_module(REVIEWED_FINITE_QUIET_PRODUCER_PIN, 'closed_outer_finite_quiet')
    record = producer.collect_actual_outer_guardian_boundary(
        REVIEWED_OUTER_EXECUTION_AUTHORITY_PIN, context.spec_record)
    raw = _read_bound(record)
    value = parse(raw)
    require(raw == canonical(value) + b'\n' and value['schema'] == 'newer-native-b1-external-guardian-finite-quiet-boundary-proposal.v1' and
            value['producer_source'] == REVIEWED_FINITE_QUIET_PRODUCER_PIN and
            value['execution_root'] == REVIEWED_OUTER_EXECUTION_AUTHORITY_PIN and value['spec'] == context.spec_record and
            value['boot_utc_ticks'] == context.spec['boot_utc_ticks'], 'Exact independent finite quiet producer required')
    require(type(value['actual_samples']) is list and len(value['actual_samples']) == 2, 'Two actual full samples required')
    samples = [parse(_read_bound(item)) for item in value['actual_samples']]
    for sample in samples:
        require(sample['boot_utc_ticks'] == context.spec['boot_utc_ticks'] and
                sample['current_query_succeeded'] is True and sample['full_current_inventory'] is True and
                type(sample['unknown_or_live_descendants']) is list and sample['unknown_or_live_descendants'] == [] and
                type(sample['foreign_scientific_processes']) is list and sample['foreign_scientific_processes'] == [] and
                sample['finite_actual_spawn_window_adjudicated'] is True and sample['absence_is_exit_proof'] is False,
                'Missing actual finite quiet/unknown disposition; no empty caller-list substitute')
        inventory = parse(_read_bound(sample['raw_full_inventory_stdout']))
        _read_bound(sample['raw_full_inventory_stderr'])
        query_exit = parse(_read_bound(sample['actual_query_exit']))
        saved_exit_relation(query_exit, sample['actual_query_identity'])
        require(query_exit['exit_code_unsigned_dword'] == 0 and inventory['boot_utc_ticks'] == context.spec['boot_utc_ticks'] and
                type(inventory['rows']) is list and type(inventory['row_count']) is int and
                1 <= len(inventory['rows']) == inventory['row_count'] <= 65536,
                'Raw full inventory/count and designated actual query exit differ')
        _read_bound(sample['actual_lineage_records'])
        integer(sample['sample_start_utc_ticks'], 1)
        integer(sample['sample_end_utc_ticks'], 1)
        require(sample['sample_start_utc_ticks'] <= sample['sample_end_utc_ticks'], 'Actual full-query interval reversed')
    require(samples[1]['sample_start_utc_ticks'] - samples[0]['sample_end_utc_ticks'] >= 15 * 10000000,
            'Actual query end to next start must be >=15s')
    # This source does not install the presently closed quiet collector or convert
    # its fixed actual-slot unresolved field into a true result by setting a pin.
    return record


def _remember(context, phase, error):
    raise ClosedOuterObserver('Closed diagnostics entry; failure to write does not release held descendants')
    context.diagnostic_failure_count += 1
    value = {'phase': phase, 'error': str(error)[:4096], 'count': context.diagnostic_failure_count,
             'retained_actual_identities': [actor.identity for actor in context.processes],
             'actual_captured_exits': [actor.exit_observation for actor in context.processes],
             'finite_unobserved_descendants': context.finite_unobserved_descendants,
             'shared_lock_release_authorized': False, 'observer_self_exit_proven': False}
    if len(context.diagnostic_failures) < 64:
        context.diagnostic_failures.append(value)
    try:
        context.ledger.emit('outer_observer_partial_failure', **value)
    except BaseException as ledger_error:
        context.diagnostic_failure_count += 1
        context.last_unrecorded_error = str(ledger_error)[:4096]


def _retain_failure(context, error):
    raise ClosedOuterObserver('Closed failure-retention body; no kill/retry/delete/rollback or implicit release')
    try:
        _remember(context, 'initial_failure', error)
    except BaseException:
        context.diagnostic_failure_count += 1
    while True:
        try:
            for actor in context.processes:
                if actor.exit_observation is None:
                    try:
                        actor.wait(1000)
                    except BaseException as observation_error:
                        _remember(context, 'continuous_held_exit_wait', observation_error)
            require(context.processes and all(actor.exit_observation is not None for actor in context.processes),
                    'Captured child exits still missing')
            for proc in context.popen_processes:
                require(type(proc.wait(timeout=0)) is int, 'Popen exit remains separately required')
            for stream in context.streams:
                if not stream.closed:
                    stream.close()
            _actual_finite_quiet(context)
            context.finite_unobserved_descendants = False
            for actor in context.processes:
                actor.close()
            return {'actual_failure_terminal_only': True, 'scientific_success': False, 'lock_release_authorized': False}
        except BaseException as retention_error:
            try:
                _remember(context, 'retention_still_unresolved', retention_error)
                time.sleep(1)
            except BaseException as diagnostic_error:
                context.diagnostic_failure_count += 1
                context.last_unrecorded_error = str(diagnostic_error)[:4096]
            # An API/stream/quiet/diagnostic failure never closes held references
            # by an escaping finally. Host termination may still end the owner;
            # that is a fresh incident, not proof of child exit or OS lock safety.
            continue


def _run_observer(spec_record):
    raise ClosedOuterObserver('Closed external observer mode; no actual guardian spawn or independent current authority')
    spec_raw, spec, request_raw, request, bootstrap_raw, bootstrap, root = _read_spec(spec_record)
    directory = Path(spec['outer_control_directory'])
    require(not directory.exists(), 'Any outer attempt directory, even empty, rejects replay')
    require(not Path(spec['guardian_control_directory']).exists(), 'Any actor attempt directory rejects replay')
    directory.mkdir()
    held_dir = directory / 'external_held_evidence'
    held_dir.mkdir()
    helper = _load_bound_module(HELPER_PIN, 'closed_outer_fixed_process_helper')
    api, ledger = helper.WinAPI(), helper.Ledger(held_dir, 'outer_observer')
    me = helper.HeldProcess(api, os.getpid(), ledger, 'outer_observer_self_live_only')
    parent = helper.HeldProcess(api, bootstrap['observer_parent_identity']['pid'], ledger, 'actual_outer_observer_parent_live')
    require(parent.identity == bootstrap['observer_parent_identity'], 'Actual observer parent birth differs')
    me.confirm_twice(bootstrap['observer_complete_command'], bootstrap['observer_image']['path'], parent)
    context = ObserverContext(helper, api, ledger, me, parent, directory, spec_record, spec, bootstrap, root)
    try:
        initial = _fresh_physical_admission(context, 'before_guardian_spawn')
        for key in ('observer_source', 'actor_source', 'guardian_runtime_source'):
            _read_bound(spec[key], MAX_SOURCE)
        for key in ('observer_image', 'launcher_image', 'interpreter_image'):
            _read_bound(bootstrap[key], MAX_IMAGE)
        actor_control = Path(spec['guardian_control_directory'])
        actor_control.mkdir()
        binding = _new_record(actor_control / 'spec_binding.json', spec_record)
        argv = [bootstrap['launcher_image']['path'], '-B', spec['actor_source']['path'],
                '--guardian-actor', '--spec-binding', binding['path']]
        require(subprocess.list2cmdline(argv) == bootstrap['launcher_complete_command'], 'Predeclared launcher full command differs')
        streams = [ (directory / name).open('xb') for name in ('guardian.stdout.log', 'guardian.stderr.log') ]
        context.streams.extend(streams)
        context.finite_unobserved_descendants = True  # set BEFORE Popen
        ledger.emit('guardian_spawn_intent_only', argv=argv, spec=spec_record, raw_request_sha256=digest(request_raw),
                    actual_spawn_or_exit_not_yet_proven=True, shared_lock_release_authorized=False)
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=streams[0], stderr=streams[1],
                                shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
        context.popen_processes.append(proc)
        launcher = helper.HeldProcess(api, proc.pid, ledger, 'external_guardian_launcher')
        context.processes.append(launcher)
        launcher_observations = launcher.confirm_twice(bootstrap['launcher_complete_command'], bootstrap['launcher_image']['path'], me)
        ready_record, ready_raw, ready = _discover_control(actor_control / 'guardian.ready.json', ACK_TIMEOUT_SECONDS)
        require(set(ready) == {'schema', 'spec', 'spec_raw_sha256', 'request', 'request_raw_sha256', 'bootstrap',
                'nonce', 'interpreter_identity', 'self_snapshot', 'guardian_runtime_imported', 'self_report_is_not_external_exit_proof'} and
                ready['schema'] == 'newer-native-b1-external-guardian-ready-proposal.v1' and ready['spec'] == spec_record and
                ready['spec_raw_sha256'] == digest(spec_raw) and ready['request'] == spec['request'] and
                ready['request_raw_sha256'] == digest(request_raw) and ready['bootstrap'] == spec['bootstrap'] and
                ready['nonce'] == spec['nonce'] and ready['guardian_runtime_imported'] is False and
                ready['self_report_is_not_external_exit_proof'] is True, 'Exact raw guardian READY associations differ')
        interpreter, interpreter_observations = _capture_interpreter(context, launcher, ready)
        require(interpreter_observations[-1] == ready['self_snapshot'], 'Self READY differs from actual external live snapshot')
        final_admission = _fresh_physical_admission(context, 'before_guardian_ACK')
        require(_read_bound(spec_record) == spec_raw and _read_bound(spec['request']) == request_raw and
                _read_bound(spec['bootstrap']) == bootstrap_raw, 'Exact source/request/bootstrap bytes changed before ACK')
        launcher_observations = launcher.confirm_twice(bootstrap['launcher_complete_command'], bootstrap['launcher_image']['path'], me)
        interpreter_observations = interpreter.confirm_twice(bootstrap['interpreter_complete_command'], bootstrap['interpreter_image']['path'], launcher)
        require(interpreter_observations[-1] == ready['self_snapshot'], 'Guardian changed before ACK')
        release_relation(parse(_read_bound(spec['release'])), spec, spec_record, datetime.now(timezone.utc))
        ack_record = _new_record(actor_control / 'observer.ack.json', {
            'schema': 'newer-native-b1-external-guardian-ack-proposal.v1', 'spec': spec_record, 'spec_raw_sha256': digest(spec_raw),
            'request': spec['request'], 'request_raw_sha256': digest(request_raw), 'bootstrap': spec['bootstrap'],
            'nonce': spec['nonce'], 'ready': ready_record, 'execution_root': REVIEWED_OUTER_EXECUTION_AUTHORITY_PIN,
            'startup_release': spec['release'], 'guardian_runtime_source': REVIEWED_GUARDIAN_RUNTIME_SOURCE_PIN,
            'observer_identity': me.identity, 'observer_parent_identity': parent.identity,
            'launcher_identity': launcher.identity, 'interpreter_identity': interpreter.identity,
            'launcher_observations': launcher_observations, 'interpreter_observations': interpreter_observations,
            'initial_admission': initial, 'final_admission': final_admission,
            'run_guardian_runtime': True, 'measurement_admitted': False})
        ledger.emit('ACK_published_before_guardian_runtime_import', ack=ack_record, ready=ready_record,
                    raw_request_sha256=digest(request_raw), observer_self_exit_proven=False)
        for actor in (interpreter, launcher):
            while actor.exit_observation is None:
                actor.wait(60000)  # adopted helper saves actual DWORD candidate FIRST
            saved_exit_relation(actor.exit_observation, actor.identity)
        popen_code = proc.wait(timeout=0)
        require(type(popen_code) is int, 'Popen actual exit remains distinct from held exit')
        for stream in streams:
            stream.close()
        logs = [helper.seal_closed_log(api, directory / name, (launcher, interpreter), streams)
                for name in ('guardian.stdout.log', 'guardian.stderr.log')]
        quiet_record = _actual_finite_quiet(context)
        context.finite_unobserved_descendants = False
        value = {'schema': 'newer-native-b1-external-guardian-held-exit-candidate.v1', 'spec': spec_record,
            'request': spec['request'], 'request_raw_sha256': digest(request_raw), 'nonce': spec['nonce'],
            'guardian_launcher_identity': launcher.identity, 'guardian_interpreter_identity': interpreter.identity,
            'actual_launcher_exit': launcher.exit_observation, 'actual_interpreter_exit': interpreter.exit_observation,
            'separate_popen_exit_code': popen_code, 'READY': ready_record, 'ACK': ack_record, 'closed_logs': logs,
            'finite_quiet_boundary': quiet_record, 'all_designated_actual_exits_zero':
                launcher.exit_observation['exit_code_unsigned_dword'] == interpreter.exit_observation['exit_code_unsigned_dword'] == popen_code == 0,
            'guardian_return_intent_is_exit_proof': False, 'observer_self_exit_proven': False,
            'shared_lock_release_authorized': False, 'measurement_admitted': False,
            'scientific_artifact_admission_or_T6_completion': False}
        candidate_record = _new_record(directory / 'external_guardian_exit_candidate.json', value)
        for actor in (interpreter, launcher):
            actor.close()
        parent.close()
        me.close()  # reference close is NOT self exit or actual own-exit proof
        return _new_record(directory / 'observer_return_intent.json', {
            'candidate': candidate_record, 'expected_own_exit': 0, 'actual_own_exit_unknown_here': True,
            'requires_even_more_external_continuously_held_parent': True, 'measurement_admitted': False})
    except BaseException as error:
        _retain_failure(context, error)
        raise


def _guardian_actor(spec_binding_path):
    raise ClosedOuterObserver('Closed guardian-actor mode; no original v3 primitive or runtime is imported/executed')
    binding_record, binding_raw, spec_record = _discover_control(Path(spec_binding_path), ACK_TIMEOUT_SECONDS)
    descriptor(spec_record)
    spec_raw, spec, request_raw, request, bootstrap_raw, bootstrap, root = _read_spec(spec_record)
    control = Path(spec['guardian_control_directory'])
    require(Path(spec_binding_path).resolve(strict=True) == control / 'spec_binding.json', 'Exact actor binding path required')
    require(not any(name.split('.')[0] in {'torch', 'numpy', 'torchvision', 'timm', 'cv2', 'PIL', 'albumentations'}
                    for name in sys.modules), 'No scientific imports before external ACK')
    helper = _load_bound_module(HELPER_PIN, 'closed_guardian_actor_process_helper')
    ledger_dir = control / 'self_live_evidence'
    ledger_dir.mkdir()
    api, ledger = helper.WinAPI(), helper.Ledger(ledger_dir, 'guardian_actor')
    me = helper.HeldProcess(api, os.getpid(), ledger, 'guardian_actor_self_live_only')
    captured_parents = []
    try:
        self_snapshot = me.snapshot()
        require(self_snapshot['command_line'] == bootstrap['interpreter_complete_command'] and
                os.path.samefile(self_snapshot['image'], bootstrap['interpreter_image']['path']), 'Actual actor image/complete command differs')
        ready_record = _new_record(control / 'guardian.ready.json', {
            'schema': 'newer-native-b1-external-guardian-ready-proposal.v1', 'spec': spec_record,
            'spec_raw_sha256': digest(spec_raw), 'request': spec['request'], 'request_raw_sha256': digest(request_raw),
            'bootstrap': spec['bootstrap'], 'nonce': spec['nonce'], 'interpreter_identity': me.identity,
            'self_snapshot': self_snapshot, 'guardian_runtime_imported': False, 'self_report_is_not_external_exit_proof': True})
        ack_record, ack_raw, ack = _discover_control(control / 'observer.ack.json', ACK_TIMEOUT_SECONDS)
        require(set(ack) == {'schema', 'spec', 'spec_raw_sha256', 'request', 'request_raw_sha256', 'bootstrap', 'nonce',
                'ready', 'execution_root', 'startup_release', 'guardian_runtime_source', 'observer_identity',
                'observer_parent_identity', 'launcher_identity', 'interpreter_identity', 'launcher_observations',
                'interpreter_observations', 'initial_admission', 'final_admission', 'run_guardian_runtime', 'measurement_admitted'} and
                ack['schema'] == 'newer-native-b1-external-guardian-ack-proposal.v1' and ack['spec'] == spec_record and
                ack['spec_raw_sha256'] == digest(spec_raw) and ack['request'] == spec['request'] and
                ack['request_raw_sha256'] == digest(request_raw) and ack['bootstrap'] == spec['bootstrap'] and
                ack['nonce'] == spec['nonce'] and ack['ready'] == ready_record and
                ack['execution_root'] == REVIEWED_OUTER_EXECUTION_AUTHORITY_PIN and ack['startup_release'] == spec['release'] and
                ack['guardian_runtime_source'] == REVIEWED_GUARDIAN_RUNTIME_SOURCE_PIN and
                ack['interpreter_identity'] == me.identity and ack['run_guardian_runtime'] is True and ack['measurement_admitted'] is False,
                'Exact canonical raw ACK associations differ')
        require(ack['interpreter_observations'][-1] == self_snapshot and me.snapshot() == self_snapshot,
                'Actor changed since pre-import READY')
        launcher = helper.HeldProcess(api, ack['launcher_identity']['pid'], ledger, 'actor_actual_launcher_parent_live')
        captured_parents.append(launcher)
        observer = helper.HeldProcess(api, ack['observer_identity']['pid'], ledger, 'actor_actual_outer_observer_parent_live')
        captured_parents.append(observer)
        outer_parent = helper.HeldProcess(api, ack['observer_parent_identity']['pid'], ledger, 'actor_outer_parent_live')
        captured_parents.append(outer_parent)
        require(launcher.identity == ack['launcher_identity'] and observer.identity == ack['observer_identity'] and
                outer_parent.identity == ack['observer_parent_identity'] == bootstrap['observer_parent_identity'] and
                launcher.identity['pid'] != me.identity['pid'], 'Actual distinct live parent identities differ')
        observer.confirm_twice(bootstrap['observer_complete_command'], bootstrap['observer_image']['path'], outer_parent)
        launcher.confirm_twice(bootstrap['launcher_complete_command'], bootstrap['launcher_image']['path'], observer)
        me.confirm_twice(bootstrap['interpreter_complete_command'], bootstrap['interpreter_image']['path'], launcher)
        actor_context = ObserverContext(helper, api, ledger, observer, outer_parent, Path(spec['outer_control_directory']),
                                        spec_record, spec, bootstrap, root)
        # The physical producer is reread/called via the fixed reviewed pin, not
        # accepted because an ACK carries a self-asserted resource descriptor.
        actor_admission = _fresh_physical_admission(actor_context, 'actor_before_guardian_runtime_import')
        require(_read_bound(spec_record) == spec_raw and _read_bound(spec['request']) == request_raw and
                _read_bound(spec['bootstrap']) == bootstrap_raw and _read_bound(spec['release']) ==
                canonical(parse(_read_bound(spec['release']))) + b'\n', 'Actual authority bytes changed after ACK')
        ledger.emit('external_ACK_verified_before_runtime_import', ack=ack_record, actual_resource=actor_admission,
                    actual_self_exit_unknown=True, measurement_admitted=False)
        runtime = _load_bound_module(REVIEWED_GUARDIAN_RUNTIME_SOURCE_PIN, 'closed_independent_guardian_runtime_derivative')
        # This must be a separately reviewed FUTURE runtime derivative. The old
        # sealed guardian_v3 remains closed and is NOT called or bypassed here.
        result = runtime.run_guardian(spec['guardian_plan'])
        return _new_record(control / 'guardian_actor_return_intent.json', {
            'guardian_runtime_return_candidate': result, 'expected_own_exit': 0, 'actual_own_exit_unknown_here': True,
            'actual_guardian_exit_requires_external_held_observer': True, 'measurement_admitted': False})
    except BaseException as error:
        try:
            ledger.emit('guardian_actor_partial_before_actual_exit', error=repr(error), traceback=traceback.format_exc(),
                        actual_self_exit_unknown=True, no_retry_or_termination=True, measurement_admitted=False)
        except BaseException:
            pass
        raise
    finally:
        reference_errors = []
        for actor in list(reversed(captured_parents)) + [me]:
            try:
                actor.close()  # live reference close is never exit proof
            except BaseException as reference_error:
                reference_errors.append(repr(reference_error))
        if reference_errors:
            try:
                ledger.emit('guardian_actor_reference_cleanup_incomplete', errors=reference_errors,
                            actual_self_exit_unknown=True, actual_parent_exits_not_inferred=True)
            except BaseException:
                pass
            raise IncompleteOuterEvidence('Guardian actor reference cleanup incomplete; original partial is retained')


def run_observer(spec_record):
    raise ClosedOuterObserver('Closed public external observer entry; no current execution authority')
    return _run_observer(spec_record)


def run_guardian_actor(spec_binding_path):
    raise ClosedOuterObserver('Closed public guardian-actor entry; original v3 remains sealed/refusing')
    return _guardian_actor(spec_binding_path)


def main():
    raise ClosedOuterObserver('Both observer/guardian-actor CLI modes are closed source proposals, not startup runners')
    require(len(sys.argv) == 4, 'Exact prospective mode/path/SHA or mode/binding CLI required')
    if sys.argv[1] == '--guardian-actor':
        require(sys.argv[2] == '--spec-binding', 'Exact proposed actor mode required')
        return _guardian_actor(sys.argv[3])
    require(sys.argv[1] == '--observer-spec', 'Exact proposed observer mode required')
    path = Path(sys.argv[2])
    record = {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sys.argv[3]}
    return _run_observer(record)


if __name__ == '__main__':
    raise SystemExit('External guardian observer SOURCE ONLY: every effect entry and both modes are closed')
