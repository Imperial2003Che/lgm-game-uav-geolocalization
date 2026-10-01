"""Closed B1 outer-guardian source proposal; no runtime authority is installed.

This module supplies exact data contracts and dormant ownership/IPC/exit bodies.
It does not replace the adopted native single-slot encoder lifecycle. Its missing
reviewed bridge, predecessor adjudication, quiet collector and external guardian
observer are explicit hard stops. Every effect-bearing entry rejects first.
Pure functions below check candidate associations only, never execution grants.
"""
import ctypes
from ctypes import wintypes as W
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

HERE = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\external_efficiency_preparation\newer_native_b1_guardian_v1')
PREP = HERE.parent
EX = PREP.parent
HELPER = PREP / 'newer_native_process_evidence_v2' / 'windows_process_evidence.py'
HELPER_SHA = 'cc090bec1429ab429b556200597acedfa13c33e878627155b0cc9f8098c9f5d2'
ADOPTED_LIFECYCLE = PREP / 'newer_native_b1_lifecycle_v1' / 'native_lifecycle.py'
LIFECYCLE_SHA = '407eb2163451877e03578a91a3e496126d49be1141607855eb279d1641469d59'
LOCK = EX / 'latest_baseline_gpu.lock'
LOCK_SHA = '5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9'
LOCK_CREATION_UTC_TICKS = 639262940518466959
FILETIME_TO_UTC_TICKS = 504911232000000000
MAX_CONTROL = 8 * 1024 * 1024
MIN_AVAILABLE_COMMIT = 26 * 1024 ** 3
PROPOSED_B1_TTL_SECONDS = 900
PROPOSED_ORDER = (('CAMP', 1), ('CAMP', 2), ('CAMP', 3),
                  ('DAC', 1), ('DAC', 2), ('DAC', 3))
REVIEWED_EXECUTION_ROOT_PIN = None
REVIEWED_SLOT_BRIDGE_PIN = None
REVIEWED_QUIET_COLLECTOR_PIN = None
REVIEWED_OUTER_OBSERVER_PIN = None
MISSING_INTEGRATION = (
    'adopted upstream completion/exit adjudication including historical primary unknown exit',
    'reviewed one-slot derivative with guardian IPC; adopted v1 has no such interface',
    'actual native venv/base-image/full-command topology and runtime validation',
    'reviewed complete descendant/science quiet collector and external guardian observer',
    'current resource/release/source and retained shared byte-lock execution authority',
)


class ClosedGuardian(RuntimeError):
    __slots__ = ()


class IncompleteIntegration(RuntimeError):
    __slots__ = ()


def _closed(*args, **kwargs):
    raise ClosedGuardian('B1 guardian v1 source only: ' + '; '.join(MISSING_INTEGRATION))


def require(value, message):
    if not value:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(raw):
    require(type(raw) is bytes, 'Raw bytes required')
    return hashlib.sha256(raw).hexdigest()


def parse(raw):
    require(type(raw) is bytes and len(raw) <= MAX_CONTROL, 'Bounded raw control bytes required')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('Nonfinite JSON constant: ' + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def integer(value, lower=0):
    require(type(value) is int and value >= lower, 'Exact integer required; bool/float rejected')
    return value


def descriptor(value, maximum=MAX_CONTROL):
    require(type(value) is dict and set(value) == {'path', 'bytes', 'sha256'}, 'Exact descriptor keys required')
    require(type(value['path']) is str and Path(value['path']).is_absolute() and '\x00' not in value['path'],
            'Absolute bounded descriptor path required')
    integer(value['bytes'])
    require(value['bytes'] <= maximum, 'Descriptor exceeds declared byte bound')
    require(type(value['sha256']) is str and len(value['sha256']) == 64 and
            all(c in '0123456789abcdef' for c in value['sha256']), 'Lowercase SHA256 required')
    return value


def utc(value):
    require(type(value) is str and len(value) <= 64, 'Bounded explicit time string required')
    instant = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(instant.tzinfo is not None and instant.utcoffset() is not None, 'Timezone required')
    return instant.astimezone(timezone.utc)


def saved_identity(value):
    require(type(value) is dict, 'Saved identity mapping required')
    integer(value['pid'], 1)
    integer(value['creation_filetime_100ns'], 1)
    integer(value['creation_utc_ticks'], 1)
    require(value['creation_utc_ticks'] == value['creation_filetime_100ns'] + FILETIME_TO_UTC_TICKS,
            'Saved identity tick systems differ')
    require(type(value['image']) is str and Path(value['image']).is_absolute(), 'Saved actual image required')
    return value


def saved_exit_relation(value, identity, require_zero=True):
    """Saved association only; this function does not retain or query a process."""
    saved_identity(identity)
    require(type(value) is dict and value['identity'] == identity and value['wait_result'] == 0,
            'Saved signaled held identity differs')
    integer(value['exit_code_unsigned_dword'])
    require(value['exit_code_unsigned_dword'] <= 0xffffffff, 'Actual DWORD range required')
    require(not require_zero or value['exit_code_unsigned_dword'] == 0, 'Zero exit required')
    integer(value['exit_filetime_100ns'], 1)
    integer(value['exit_utc_ticks'], 1)
    require(value['exit_utc_ticks'] == value['exit_filetime_100ns'] + FILETIME_TO_UTC_TICKS and
            value['exit_utc_ticks'] >= identity['creation_utc_ticks'] and
            value['same_retained_handle_pid_creation_verified'] is True, 'Saved exit time/identity relation differs')
    return {'saved_relation_only': True, 'execution_permission': False}


def resource_relation(value, expected_boot_ticks):
    require(type(value) is dict and set(value) == {
        'schema', 'sampled_utc', 'boot_utc_ticks', 'commit_limit_bytes',
        'committed_bytes', 'available_commit_bytes', 'gpu_query_exit',
        'gpu_rows', 'raw_gpu_stdout', 'raw_gpu_stderr', 'raw_memory_stdout',
        'raw_memory_stderr'}, 'Exact resource candidate fields required')
    require(value['schema'] == 'newer-native-b1-resource-candidate.v1', 'Wrong resource candidate schema')
    utc(value['sampled_utc'])
    integer(value['boot_utc_ticks'], 1)
    require(value['boot_utc_ticks'] == expected_boot_ticks, 'Current boot differs')
    limit = integer(value['commit_limit_bytes'], 1)
    used = integer(value['committed_bytes'])
    available = integer(value['available_commit_bytes'])
    require(available == limit - used and available >= MIN_AVAILABLE_COMMIT, '26GiB available commit admission failed')
    require(type(value['gpu_query_exit']) is int and value['gpu_query_exit'] == 0 and
            type(value['gpu_rows']) is list and value['gpu_rows'] == [],
            'Complete successful GPU query must be fully empty, without PID exemptions')
    for name in ('raw_gpu_stdout', 'raw_gpu_stderr', 'raw_memory_stdout', 'raw_memory_stderr'):
        descriptor(value[name])
    return {'candidate_consistency_only': True, 'execution_permission': False}


def release_relation(value, plan_record, slot, now):
    """Proposed new B1 schema, not an inherited issued release or an issuer."""
    require(type(value) is dict and set(value) == {
        'schema', 'scope', 'execute', 'guardian_source', 'authority_root',
        'plan', 'slot_spec', 'request', 'bootstrap', 'predecessors',
        'boot_utc_ticks', 'issued_utc', 'expires_utc'}, 'Exact proposed release fields required')
    require(value['schema'] == 'newer-native-b1-guardian-release-proposal.v1' and
            value['scope'] == 'one_native_B1_slot_after_five_layers_and_extra_DAC' and
            value['execute'] is True, 'Wrong proposed B1 release scope')
    for key in ('guardian_source', 'authority_root', 'plan', 'slot_spec', 'request', 'bootstrap'):
        descriptor(value[key])
    require(value['plan'] == plan_record and value['slot_spec'] == slot['spec'] and
            value['request'] == slot['request'] and value['bootstrap'] == slot['bootstrap'], 'Slot release association differs')
    require(type(value['predecessors']) is list and value['predecessors'], 'Predecessor descriptors required')
    for item in value['predecessors']:
        descriptor(item)
    integer(value['boot_utc_ticks'], 1)
    issued, expires = utc(value['issued_utc']), utc(value['expires_utc'])
    require(type(now) is datetime and now.tzinfo is not None and
            issued <= now.astimezone(timezone.utc) < expires and
            0 < (expires - issued).total_seconds() <= PROPOSED_B1_TTL_SECONDS,
            'Proposed 900-second B1 freshness bound failed')
    return {'candidate_association_only': True, 'execution_permission': False,
            'ttl_is_new_proposal_not_inherited_contract': True}


def plan_relation(value, allow_template=False):
    require(type(value) is dict and set(value) == {
        'schema', 'template_only', 'order_is_new_proposal', 'guardian_source',
        'authority_root', 'slot_bridge', 'quiet_collector', 'outer_observer',
        'boot_utc_ticks', 'predecessor_authorities', 'slots'}, 'Exact plan fields required')
    require(value['schema'] == 'newer-native-b1-six-slot-plan-proposal.v1' and
            type(value['template_only']) is bool and value['order_is_new_proposal'] is True,
            'Explicit proposed plan required')
    require(allow_template or value['template_only'] is False, 'Immutable null template is never an execution plan')
    slots = value['slots']
    require(type(slots) is list and len(slots) == 6 and
            tuple((x['method'], x['seed']) for x in slots) == PROPOSED_ORDER,
            'Each CAMP/DAC seed1/2/3 in explicit proposed order exactly once')
    template = value['template_only']
    for key in ('guardian_source', 'authority_root', 'slot_bridge', 'quiet_collector', 'outer_observer'):
        require(template and value[key] is None or not template and descriptor(value[key]), 'Unknown authority cannot be invented')
    if template:
        require(value['boot_utc_ticks'] is None and value['predecessor_authorities'] is None,
                'Template must retain unknown actual boot/predecessor authority')
    else:
        integer(value['boot_utc_ticks'], 1)
        require(type(value['predecessor_authorities']) is list and len(value['predecessor_authorities']) == 6,
                'Five adopted layer authorities and extra DAC authority required')
    nonces, fresh_roots = set(), set()
    for slot in slots:
        require(type(slot) is dict and set(slot) == {
            'method', 'seed', 'prepared', 'completed_binding', 'completion',
            'request', 'spec', 'bootstrap', 'release', 'nonce', 'guardian_control_directory'}, 'Exact slot fields required')
        require(type(slot['seed']) is int and slot['seed'] in (1, 2, 3), 'Strict seed required')
        descriptor(slot['prepared'])
        for key in ('completed_binding', 'completion', 'request', 'spec', 'bootstrap', 'release'):
            require(template and slot[key] is None or not template and descriptor(slot[key]), 'Template unknown descriptor differs')
        if template:
            require(slot['nonce'] is None and slot['guardian_control_directory'] is None, 'Template has no live nonce/path')
        else:
            nonce = slot['nonce']
            require(type(nonce) is str and len(nonce) == 64 and all(c in '0123456789abcdef' for c in nonce) and
                    nonce not in nonces, 'Distinct fresh declared slot nonce required')
            nonces.add(nonce)
            control = slot['guardian_control_directory']
            require(type(control) is str and Path(control).parent == HERE / 'runs' and control not in fresh_roots,
                    'Distinct exact guardian control root required')
            fresh_roots.add(control)
    return {'candidate_consistency_only': True, 'execution_permission': False}


def _read_bound(record):
    _closed(record)
    descriptor(record)
    path = Path(record['path'])
    require(path == path.resolve(strict=True), 'Exact resolved file path required')
    before = path.stat()
    require(before.st_size == record['bytes'], 'Actual size before bounded read differs')
    with path.open('rb') as f:
        raw = f.read(record['bytes'] + 1)
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) and
            len(raw) == record['bytes'] and digest(raw) == record['sha256'], 'Actual source/control bytes differ')
    return raw


def _new_record(path, value):
    _closed(path, value)
    raw = canonical(value) + b'\n'
    require(len(raw) <= MAX_CONTROL, 'Bounded record required before CreateNew')
    with Path(path).open('xb') as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    return {'path': str(path), 'bytes': len(raw), 'sha256': digest(raw)}


def _publish_grant(path, value):
    _closed(path, value)
    require(value['schema'] == 'newer-native-b1-guardian-preack-grant-proposal.v1', 'Not the old eight-field candidate')
    return _new_record(path, value)


def _load_helper():
    _closed()
    before = HELPER.stat()
    require(before.st_size <= MAX_CONTROL, 'Bounded process helper required')
    record = {'path': str(HELPER), 'bytes': before.st_size, 'sha256': HELPER_SHA}
    _read_bound(record)
    spec = importlib.util.spec_from_file_location('_b1_guardian_pinned_helper', HELPER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _reviewed_authority(plan):
    _closed(plan)
    if any(pin is None for pin in (REVIEWED_EXECUTION_ROOT_PIN, REVIEWED_SLOT_BRIDGE_PIN,
                                  REVIEWED_QUIET_COLLECTOR_PIN, REVIEWED_OUTER_OBSERVER_PIN)):
        raise IncompleteIntegration('Reviewed authority/IPC bridge/quiet collector/outer observer pins do not exist')
    for key, pin in (('authority_root', REVIEWED_EXECUTION_ROOT_PIN), ('slot_bridge', REVIEWED_SLOT_BRIDGE_PIN),
                     ('quiet_collector', REVIEWED_QUIET_COLLECTOR_PIN), ('outer_observer', REVIEWED_OUTER_OBSERVER_PIN)):
        require(plan[key] == pin, 'Plan cannot install caller-selected execution authority')
        _read_bound(pin)
    root = parse(_read_bound(REVIEWED_EXECUTION_ROOT_PIN))
    require(root['schema'] == 'newer-native-b1-reviewed-execution-authority.v1' and
            root['plan'] == plan['plan_descriptor'] and root['native_topology_validated'] is True,
            'Separately adopted actual execution scope required')
    return root


def _verify_predecessors(plan, root):
    _closed(plan, root)
    require(plan['predecessor_authorities'] == root['predecessor_authorities'], 'Exact adopted predecessor descriptors required')
    names = ('primary', 'pipeline7', 'extension4', 'authors20', 'independent9fit42eval', 'extra_DAC3fit30eval')
    for expected, record in zip(names, plan['predecessor_authorities']):
        current = parse(_read_bound(record))
        require(current['schema'] == 'b1-predecessor-adjudication.v1' and current['role'] == expected and
                current['science_adopted'] is True and current['scope_complete'] is True,
                'Upstream adopted scientific completion missing')
        require(current['exit_requirement_adjudicated'] is True and current['absence_is_exit_proof'] is False,
                'Historical primary unknown exit requires real root adjudication, never invented zero')
        for field_name in ('status', 'original_spec', 'original_plan', 'source_authority'):
            _read_bound(current[field_name])
        require(type(current['required_actual_exits']) is list, 'Declared original-contract exit evidence required')
        for item in current['required_actual_exits']:
            saved = parse(_read_bound(item['record']))
            saved_exit_relation(saved, item['identity'])
    return {'live_reread_scope': 'exact adjudicated source/state and saved exits; no historical handle reacquisition'}


def _capture_query(argv, directory, label):
    _closed(argv, directory, label)
    require(type(argv) is list and argv and all(type(x) is str and '\x00' not in x for x in argv), 'Exact argv required')
    out_path, err_path = directory / (label + '.stdout'), directory / (label + '.stderr')
    with out_path.open('xb') as out, err_path.open('xb') as err:
        result = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                shell=False, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
        out.flush()
        err.flush()
        os.fsync(out.fileno())
        os.fsync(err.fileno())
    records = []
    for path in (out_path, err_path):
        actual = path.stat()
        require(actual.st_size <= MAX_CONTROL, 'Query output exceeds bound')
        with path.open('rb') as f:
            raw = f.read(MAX_CONTROL + 1)
        records.append({'path': str(path), 'bytes': len(raw), 'sha256': digest(raw)})
    return result.returncode, records


def _resource_sample(plan, root, directory, stage):
    _closed(plan, root, directory, stage)
    # Commands and executable bytes must be independently fixed by the future root.
    adapter = root['resource_adapter']
    _read_bound(adapter['powershell_image'])
    _read_bound(adapter['gpu_query_image'])
    memory_script = ("$ErrorActionPreference='Stop';$o=Get-CimInstance Win32_OperatingSystem;"
                     "$m=Get-CimInstance Win32_PerfRawData_PerfOS_Memory;"
                     "[ordered]@{boot_utc_ticks=$o.LastBootUpTime.ToUniversalTime().Ticks.ToString();"
                     "commit_limit_bytes=$m.CommitLimit.ToString();committed_bytes=$m.CommittedBytes.ToString()}"
                     "|ConvertTo-Json -Compress")
    mem_argv = [adapter['powershell_image']['path'], '-NoProfile', '-NonInteractive', '-Command', memory_script]
    gpu_argv = [adapter['gpu_query_image']['path'], '--query-compute-apps=pid,process_name,used_gpu_memory', '--format=csv,noheader,nounits']
    require(mem_argv == adapter['memory_argv'] and gpu_argv == adapter['gpu_argv'], 'Exact reviewed resource query argv differs')
    memory_exit, memory_logs = _capture_query(mem_argv, directory, stage + '_memory')
    gpu_exit, gpu_logs = _capture_query(gpu_argv, directory, stage + '_gpu')
    require(type(memory_exit) is int and memory_exit == 0 and type(gpu_exit) is int and gpu_exit == 0, 'Query failed')
    memory = parse(_read_bound(memory_logs[0]))
    require(set(memory) == {'boot_utc_ticks', 'commit_limit_bytes', 'committed_bytes'} and
            all(type(x) is str and x.isdecimal() for x in memory.values()), 'Exact integer strings required')
    gpu_raw = _read_bound(gpu_logs[0])
    rows = [line for line in gpu_raw.decode('utf-8', errors='strict').splitlines() if line.strip()]
    value = {'schema': 'newer-native-b1-resource-candidate.v1',
             'sampled_utc': datetime.now(timezone.utc).isoformat(),
             'boot_utc_ticks': int(memory['boot_utc_ticks']),
             'commit_limit_bytes': int(memory['commit_limit_bytes']),
             'committed_bytes': int(memory['committed_bytes']),
             'available_commit_bytes': int(memory['commit_limit_bytes']) - int(memory['committed_bytes']),
             'gpu_query_exit': gpu_exit, 'gpu_rows': rows,
             'raw_gpu_stdout': gpu_logs[0], 'raw_gpu_stderr': gpu_logs[1],
             'raw_memory_stdout': memory_logs[0], 'raw_memory_stderr': memory_logs[1]}
    resource_relation(value, plan['boot_utc_ticks'])
    # initial, before-spawn and preACK all have zero exemptions, even captured actors.
    return _new_record(directory / (stage + '_resource.json'), value)


@dataclass
class OwnedByteLock:
    stream: object = None
    file_identity: object = None
    locked: bool = False

    def acquire(self):
        _closed(self)
        import msvcrt
        require(self.stream is None and not self.locked, 'No lock replay')
        stream = LOCK.open('r+b')  # existing only; never initialize/truncate/delete
        self.stream = stream
        stream.seek(0)
        raw = stream.read(2)
        require(raw == b'0' and digest(raw) == LOCK_SHA, 'Persistent carrier bytes differ')
        stat = os.fstat(stream.fileno())
        require(stat.st_size == 1, 'Persistent carrier size differs')
        class FileTime(ctypes.Structure):
            _fields_ = [('low', W.DWORD), ('high', W.DWORD)]
        class Information(ctypes.Structure):
            _fields_ = [('attributes', W.DWORD), ('creation', FileTime), ('access', FileTime),
                        ('write', FileTime), ('volume', W.DWORD), ('size_high', W.DWORD),
                        ('size_low', W.DWORD), ('links', W.DWORD), ('index_high', W.DWORD), ('index_low', W.DWORD)]
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetFileInformationByHandle.argtypes = [W.HANDLE, ctypes.POINTER(Information)]
        kernel.GetFileInformationByHandle.restype = W.BOOL
        info = Information()
        require(kernel.GetFileInformationByHandle(msvcrt.get_osfhandle(stream.fileno()), ctypes.byref(info)), 'Carrier identity API failed')
        creation = (int(info.creation.high) << 32 | int(info.creation.low)) + FILETIME_TO_UTC_TICKS
        require(creation == LOCK_CREATION_UTC_TICKS, 'Persistent carrier creation identity differs')
        self.file_identity = (stat.st_dev, stat.st_ino, info.volume, info.index_high, info.index_low, creation)
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        self.locked = True
        return self.file_identity

    def confirm_live(self):
        _closed(self)
        require(self.locked and self.stream is not None and not self.stream.closed, 'Actual retained lock stream required')
        current = os.fstat(self.stream.fileno())
        require((current.st_dev, current.st_ino) == self.file_identity[:2] and current.st_size == 1,
                'Retained carrier handle identity differs')
        require(os.path.samefile(LOCK, self.stream.name), 'Current carrier path differs from retained file')
        return {'handle_retained': True, 'file_identity': self.file_identity,
                'scope': 'cooperative first-byte OS lock; not arbitrary-writer history exclusion'}

    def release_after_observation(self, context):
        _closed(self, context)
        # Derive live boundary here. A caller boolean/JSON boundary cannot unlock.
        _terminal_boundary(context)
        self.confirm_live()
        import msvcrt
        self.stream.seek(0)
        msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
        self.locked = False
        self.stream.close()


@dataclass
class RuntimeContext:
    plan: dict
    root: dict
    helper: object
    api: object
    ledger: object
    me: object
    byte_lock: OwnedByteLock
    directory: Path
    plan_record: dict
    processes: list = field(default_factory=list)
    popen_processes: list = field(default_factory=list)
    streams: list = field(default_factory=list)
    slot_candidates: list = field(default_factory=list)
    unobserved_descendants: bool = False


def _quiet_snapshot(context):
    _closed(context)
    if REVIEWED_QUIET_COLLECTOR_PIN is None:
        raise IncompleteIntegration('No reviewed complete descendants/science collector; absence cannot release retained lock')
    # Exact future collector contract: an actual source module with a fixed root
    # pin, bounded broad process query and preserved null commands, not callback.
    _read_bound(REVIEWED_QUIET_COLLECTOR_PIN)
    raise IncompleteIntegration('Collector interface implementation is not supplied by current adopted sources')


def _confirm_actor(context, actor, command, image, parent):
    _closed(context, actor, command, image, parent)
    descriptor(image)
    _read_bound(image)
    values = actor.confirm_twice(command, image['path'], parent)
    require(values[0] == values[1], 'Two live actor observations differ')
    return values


def _wait_ipc(path, deadline_seconds):
    _closed(path, deadline_seconds)
    integer(deadline_seconds, 1)
    require(deadline_seconds <= 45, 'Bounded handshake wait required')
    deadline = time.monotonic() + deadline_seconds
    while not path.exists():
        if time.monotonic() >= deadline:
            raise TimeoutError('PreACK IPC timeout; retain partial, never retry')
        time.sleep(0.05)
    before = path.stat()
    require(before.st_size <= MAX_CONTROL, 'Bounded IPC candidate required')
    with path.open('rb') as f:
        raw = f.read(MAX_CONTROL + 1)
    record = {'path': str(path), 'bytes': len(raw), 'sha256': digest(raw)}
    require(before.st_size == len(raw) and _read_bound(record) == raw, 'IPC candidate raw bytes changed')
    return record, parse(raw)


def _slot_reread(context, slot, stage):
    _closed(context, slot, stage)
    _read_bound(context.plan_record)
    _reviewed_authority(context.plan)
    _verify_predecessors(context.plan, context.root)
    context.byte_lock.confirm_live()
    release = parse(_read_bound(slot['release']))
    release_relation(release, context.plan_record, slot, datetime.now(timezone.utc))
    require(release['boot_utc_ticks'] == context.plan['boot_utc_ticks'] and
            release['authority_root'] == REVIEWED_EXECUTION_ROOT_PIN and
            release['guardian_source'] == context.plan['guardian_source'], 'Exact future release authority differs')
    for key in ('prepared', 'completed_binding', 'completion', 'request', 'spec', 'bootstrap'):
        _read_bound(slot[key])
    request_raw = _read_bound(slot['request'])
    request = parse(request_raw)
    require(request_raw == canonical(request) + b'\n' and request['schema'] == 'newer-native-b1-request.v1' and
            request['method'] == slot['method'] and type(request['seed']) is int and request['seed'] == slot['seed'],
            'Original request raw canonical bytes/slot differ')
    # Guardian does not run bind_completed/package imports in its shared method
    # process. The adopted worker owns fresh original reconstruction after ACK.
    bootstrap = parse(_read_bound(slot['bootstrap']))
    for key in ('launcher_image', 'interpreter_image', 'controller_image', 'worker_source', 'controller_source', 'process_helper_source'):
        _read_bound(bootstrap[key])
    return _resource_sample(context.plan, context.root, context.directory, stage)


def _preack_authority(context, slot, controller, ipc_record, ipc):
    _closed(context, slot, controller, ipc_record, ipc)
    require(type(ipc) is dict and set(ipc) == {'schema', 'spec', 'request', 'bootstrap', 'nonce', 'launcher', 'interpreter'} and
            ipc['schema'] == 'newer-native-b1-guardian-preack-request-proposal.v1' and
            ipc['spec'] == slot['spec'] and ipc['request'] == slot['request'] and ipc['bootstrap'] == slot['bootstrap'] and
            ipc['nonce'] == slot['nonce'], 'Exact internal exchange differs')
    _read_bound(ipc_record)
    bootstrap = parse(_read_bound(slot['bootstrap']))
    for key in ('launcher', 'interpreter'):
        saved_identity(ipc[key])
    require(ipc['launcher']['pid'] != ipc['interpreter']['pid'], 'Distinct native topology required')
    launcher = context.helper.HeldProcess(context.api, ipc['launcher']['pid'], context.ledger, 'guardian_native_launcher')
    context.processes.append(launcher)
    interpreter = context.helper.HeldProcess(context.api, ipc['interpreter']['pid'], context.ledger, 'guardian_native_interpreter')
    context.processes.append(interpreter)
    require(launcher.identity == ipc['launcher'] and interpreter.identity == ipc['interpreter'], 'IPC self-report differs from actual external handles')
    _confirm_actor(context, launcher, bootstrap['launcher_complete_command'], bootstrap['launcher_image'], controller)
    _confirm_actor(context, interpreter, bootstrap['interpreter_complete_command'], bootstrap['interpreter_image'], launcher)
    resource = _slot_reread(context, slot, slot['method'].lower() + str(slot['seed']) + '_preack')
    grant = {'schema': 'newer-native-b1-guardian-preack-grant-proposal.v1',
             'spec': slot['spec'], 'request': slot['request'], 'bootstrap': slot['bootstrap'],
             'nonce': slot['nonce'], 'release': slot['release'], 'authority_root': REVIEWED_EXECUTION_ROOT_PIN,
             'guardian_identity': context.me.identity, 'controller_identity': controller.identity,
             'launcher_identity': launcher.identity, 'interpreter_identity': interpreter.identity,
             'resource': resource, 'actual_retained_lock_identity': context.byte_lock.file_identity,
             'execute_original_reference': True, 'measurement_admitted': False,
             'scope': 'proposed new preACK execution grant, never the sealed old eight-field candidate'}
    return _publish_grant(Path(slot['guardian_control_directory']) / 'preack_grant.json', grant), launcher, interpreter


def _run_existing_slot_bridge(context, slot):
    _closed(context, slot)
    if REVIEWED_SLOT_BRIDGE_PIN is None:
        raise IncompleteIntegration('Adopted lifecycle v1 FIRST rejects and has no guardian IPC; no compatible bridge is installed')
    bridge = parse(_read_bound(context.root['slot_bridge_contract']))
    require(bridge['source'] == REVIEWED_SLOT_BRIDGE_PIN and bridge['preserved_one_slot_source_sha256'] == LIFECYCLE_SHA and
            bridge['protocol'] == 'newer-native-b1-guardian-preack-request-proposal.v1', 'Reviewed preserved one-slot bridge contract missing')
    _read_bound(REVIEWED_SLOT_BRIDGE_PIN)
    _slot_reread(context, slot, slot['method'].lower() + str(slot['seed']) + '_before_spawn')
    control = Path(slot['guardian_control_directory'])
    require(not control.exists(), 'Any prior slot control directory refuses replay')
    control.mkdir()
    bootstrap = parse(_read_bound(slot['bootstrap']))
    argv = [bootstrap['controller_image']['path'], '-B', REVIEWED_SLOT_BRIDGE_PIN['path'],
            '--guardian-slot-spec', slot['spec']['path'], '--guardian-control-directory', str(control)]
    require(subprocess.list2cmdline(argv) == bootstrap['controller_complete_command'], 'Predeclared full controller command differs')
    stdout, stderr = (control / 'controller.stdout').open('xb'), (control / 'controller.stderr').open('xb')
    context.streams.extend((stdout, stderr))
    context.unobserved_descendants = True  # before spawn; failure cannot imply no child
    proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, shell=False,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    context.popen_processes.append(proc)
    controller = context.helper.HeldProcess(context.api, proc.pid, context.ledger, 'outer_slot_controller')
    context.processes.append(controller)
    _confirm_actor(context, controller, bootstrap['controller_complete_command'], bootstrap['controller_image'], context.me)
    request_record, request = _wait_ipc(control / 'preack_request.json', 45)
    grant, launcher, interpreter = _preack_authority(context, slot, controller, request_record, request)
    # Parent handles remain continuously retained through actual exits, including
    # native grandchildren. This source does not reopen exited PID identities.
    for actor in (interpreter, launcher, controller):
        observed = None
        while observed is None:
            observed = actor.wait(60000)
        saved_exit_relation(observed, actor.identity)
    code = proc.wait()
    require(type(code) is int and code == 0, 'Popen exit is separately required, not dual-held proof')
    for stream in (stdout, stderr):
        stream.close()
    logs = [context.helper.seal_closed_log(context.api, path, (controller, launcher, interpreter), (stdout, stderr))
            for path in (control / 'controller.stdout', control / 'controller.stderr')]
    candidate_record, candidate = _wait_ipc(control / 'slot_candidate.json', 45)
    require(candidate['measurement_admitted'] is False and candidate['request'] == slot['request'] and
            candidate['spec'] == slot['spec'], 'Candidate association only; no artifact semantic admission')
    # Full quiet collector is mandatory before clearing unknown-descendant state.
    quiet = _quiet_snapshot(context)
    require(quiet['unknown_or_live_descendants'] == [] and quiet['foreign_scientific_processes'] == [], 'Unresolved descendants remain')
    context.unobserved_descendants = False
    value = {'schema': 'newer-native-b1-outer-slot-candidate.v1', 'slot': slot,
             'preack_grant': grant, 'child_candidate': candidate_record,
             'actual_exits': [actor.exit_observation for actor in (controller, launcher, interpreter)],
             'popen_exit': code, 'closed_logs': logs, 'measurement_admitted': False,
             'original_artifact_semantics_rechecked': False, 'guardian_exit_proven': False}
    record = _new_record(control / 'outer_slot_candidate.json', value)
    context.slot_candidates.append(record)
    return record


def _terminal_boundary(context):
    _closed(context)
    require(not context.unobserved_descendants and context.processes and
            all(x.exit_observation is not None for x in context.processes) and
            all(x.closed for x in context.streams), 'Real complete child exits/closed streams required')
    for actor in context.processes:
        saved_exit_relation(actor.exit_observation, actor.identity, require_zero=False)
    # Nonzero actual exit may terminate the scientific attempt, but is never a
    # successful slot or permission to advance; safe release still needs quiet.
    first = _quiet_snapshot(context)
    time.sleep(15)
    second = _quiet_snapshot(context)
    for sample in (first, second):
        require(sample['unknown_or_live_descendants'] == [] and sample['foreign_scientific_processes'] == [],
                'Actual terminal quiet boundary missing')
    return (first, second)


def _failure_handoff(context, error):
    _closed(context, error)
    _new_record(context.directory / 'failure_partial.json', {
        'schema': 'newer-native-b1-guardian-partial-failure.v1',
        'error': str(error), 'traceback': traceback.format_exc(),
        'captured_identities': [x.identity for x in context.processes],
        'captured_exits': [x.exit_observation for x in context.processes],
        'spawned_pids': [x.pid for x in context.popen_processes],
        'unobserved_descendants': context.unobserved_descendants,
        'shared_lock_release_authorized': False, 'measurement_admitted': False,
        'own_reference_or_stream_cleanup_is_not_child_exit': True})
    # Running incident retention only, never start a native slot merely to wait
    # for initial GPU admission. Never kill/delete/rollback/retry an attempt.
    while True:
        for actor in context.processes:
            if actor.exit_observation is None:
                actor.wait(1000)
        try:
            _terminal_boundary(context)
        except (ValueError, IncompleteIntegration):
            time.sleep(1)
            continue
        context.byte_lock.release_after_observation(context)
        return


def _run_guardian(plan_record):
    _closed(plan_record)
    raw = _read_bound(plan_record)
    plan = parse(raw)
    plan_relation(plan)
    require(raw == canonical(plan) + b'\n', 'Canonical actual plan plus LF required')
    # internal association is not a new on-disk plan field or self-hash
    runtime_plan = dict(plan, plan_descriptor=plan_record)
    root = _reviewed_authority(runtime_plan)
    _verify_predecessors(runtime_plan, root)
    # Initial query occurs before lock/intent/native launch; nonempty refuses.
    initial_dir = Path(root['initial_observation_directory'])
    require(not initial_dir.exists(), 'Any prior initial directory refuses replay')
    initial_dir.mkdir()
    _resource_sample(runtime_plan, root, initial_dir, 'initial')
    lock = OwnedByteLock()
    lock.acquire()
    context = None
    try:
        directory = Path(root['guardian_attempt_directory'])
        require(directory.parent == HERE / 'runs' and not directory.exists(), 'Any attempt, even empty, refuses replay')
        directory.mkdir()
        helper = _load_helper()
        ledger, api = helper.Ledger(directory / 'held_evidence', 'guardian'), helper.WinAPI()
        me = helper.HeldProcess(api, os.getpid(), ledger, 'guardian_self_live_only')
        context = RuntimeContext(runtime_plan, root, helper, api, ledger, me, lock, directory, plan_record)
        require(me.snapshot()['command_line'] == root['guardian_complete_command'] and
                os.path.samefile(me.identity['image'], root['guardian_image']['path']), 'Actual guardian identity differs')
        _read_bound(root['guardian_image'])
        for slot in runtime_plan['slots']:
            _run_existing_slot_bridge(context, slot)
            _terminal_boundary(context)  # every previous slot exits before successor
        context.byte_lock.release_after_observation(context)
        return _new_record(directory / 'guardian_return_intent.json', {
            'schema': 'newer-native-b1-guardian-return-intent.v1', 'slot_candidates': context.slot_candidates,
            'expected_exit': 0, 'actual_guardian_exit_unknown': True, 'measurement_admitted': False,
            'requires_external_retained_observer': REVIEWED_OUTER_OBSERVER_PIN})
    except BaseException as error:
        if context is None:
            # No scientific spawn has been reached, but this cannot assert an OS
            # quiet boundary or successful release. Missing initialized observer
            # is an explicit integration failure. Keep the acquired stream alive.
            while True:
                time.sleep(1)
        _failure_handoff(context, error)
        raise


def run_guardian(plan_record):
    _closed(plan_record)
    return _run_guardian(plan_record)


def main():
    _closed()
    require(len(sys.argv) == 4 and sys.argv[1] == '--plan' and sys.argv[2] and sys.argv[3],
            'Exact future plan path/independently supplied SHA CLI required')
    path = Path(sys.argv[2])
    record = {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sys.argv[3]}
    _run_guardian(record)
    return 0


if __name__ == '__main__':
    raise ClosedGuardian('Guardian source-only CLI is unconditionally closed')
    raise SystemExit(main())
