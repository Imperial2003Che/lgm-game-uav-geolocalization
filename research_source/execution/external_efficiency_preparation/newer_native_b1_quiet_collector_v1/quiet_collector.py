"""Closed source proposal for complete CURRENT process-inventory evidence.

No execution pin or guardian integration is installed. Every effect entry raises
first. Pure relations describe saved candidate bytes, not independent authority.
Two successful current inventories do not establish an uncaptured short-lived
child's historical exit or its historical parent. The finite actual-slot lineage
gap stays unresolved until a separately adopted method/policy addresses it.
"""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

HERE = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\external_efficiency_preparation\newer_native_b1_quiet_collector_v1')
PREP = HERE.parent
EX = PREP.parent
HELPER = PREP / 'newer_native_process_evidence_v2' / 'windows_process_evidence.py'
HELPER_BYTES = 16238
HELPER_SHA256 = 'cc090bec1429ab429b556200597acedfa13c33e878627155b0cc9f8098c9f5d2'
REVIEWED_QUIET_EXECUTION_AUTHORITY_PIN = None
REVIEWED_FINITE_SLOT_LINEAGE_METHOD_PIN = None
REVIEWED_GUARDIAN_INTEGRATION_SOURCE_PIN = None
FILETIME_TO_UTC_TICKS = 504911232000000000
MAX_CONTROL = 4 * 1024 * 1024
MAX_INVENTORY = 16 * 1024 * 1024
MAX_STDERR = 2 * 1024 * 1024
MAX_CLOSED_LOG = 64 * 1024 * 1024
MAX_ROWS = 65536
MIN_BOUNDARY_SECONDS = 15
UNRESOLVED_SLOT_HISTORY = 'actual-slot spawn window lacks an independently adopted finite lineage method/role adjudication; unobserved short-lived child exits remain unknown'

# This fixed, unfiltered query body is SOURCE TEXT ONLY. It has never been run.
# CreationDate values that are unavailable remain null; no substituted timestamp
# or process command is inferred from image/service configuration.
CIM_QUERY_PS = r'''param([string]$RequestPath, [string]$ControlDirectory)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
try {
    $requestFile = Get-Item -LiteralPath $RequestPath -ErrorAction Stop
    if ($requestFile.Length -lt 1 -or $requestFile.Length -gt 262144) { throw 'Bounded request size required' }
    $requestRaw = [IO.File]::ReadAllBytes($RequestPath)
    if ($requestRaw.Length -ne $requestFile.Length) { throw 'Request changed' }
    $request = [Text.Encoding]::UTF8.GetString($requestRaw) | ConvertFrom-Json
    $requestHasher = [Security.Cryptography.SHA256]::Create()
    try { $requestSha = ([BitConverter]::ToString($requestHasher.ComputeHash($requestRaw))).Replace('-','').ToLowerInvariant() }
    finally { $requestHasher.Dispose() }
    if ($request.schema -ne 'newer-native-b1-full-cim-read-request-proposal.v1' -or
        $request.nonce -notmatch '^[0-9a-f]{64}$' -or $request.control_directory -cne $ControlDirectory) { throw 'Wrong query request' }
    $readyRaw = [Text.UTF8Encoding]::new($false).GetBytes((@{
        schema = 'newer-native-b1-full-cim-read-ready-proposal.v1'
        nonce = $request.nonce; request_sha256 = $requestSha; self_pid = [long]$PID
        execution_or_science_authority = $false
    } | ConvertTo-Json -Compress) + "`n")
    $readyPath = Join-Path $ControlDirectory 'query_ready.json'
    $readyStream = [IO.File]::Open($readyPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
    try { $readyStream.Write($readyRaw,0,$readyRaw.Length); $readyStream.Flush($true) } finally { $readyStream.Dispose() }
    $ackPath = Join-Path $ControlDirectory 'query_ack.json'
    $deadline = [DateTime]::UtcNow.AddSeconds(45)
    while (-not [IO.File]::Exists($ackPath)) {
        if ([DateTime]::UtcNow -ge $deadline) { throw 'Full-query ACK timeout' }
        Start-Sleep -Milliseconds 50
    }
    $ackFile = Get-Item -LiteralPath $ackPath -ErrorAction Stop
    if ($ackFile.Length -lt 1 -or $ackFile.Length -gt 262144) { throw 'Bounded ACK size required' }
    $ackRaw = [IO.File]::ReadAllBytes($ackPath)
    if ($ackRaw.Length -ne $ackFile.Length) { throw 'ACK changed' }
    $ack = [Text.Encoding]::UTF8.GetString($ackRaw) | ConvertFrom-Json
    if ($ack.schema -ne 'newer-native-b1-full-cim-read-ack-proposal.v1' -or
        $ack.nonce -cne $request.nonce -or $ack.request_sha256 -cne $requestSha -or
        $ack.actual_held_query_identity.pid -ne $PID -or $ack.execution_or_science_authority -ne $false) { throw 'Wrong read-only query ACK' }
    # Collector has now captured and live-confirmed this actual process. ACK is
    # only a start signal for the full read query, never scientific permission.
    $sampleStart = [DateTime]::UtcNow
    $operatingSystem = Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction Stop
    $allProcesses = @(Get-CimInstance -ClassName Win32_Process -ErrorAction Stop)
    $rows = @($allProcesses | ForEach-Object {
        $born = if ($null -eq $_.CreationDate) { $null } else { $_.CreationDate.ToUniversalTime() }
        [ordered]@{
            pid = [long]$_.ProcessId
            parent_pid = [long]$_.ParentProcessId
            name = $_.Name
            creation_utc_ticks = if ($null -eq $born) { $null } else { [long]$born.Ticks }
            creation_utc = if ($null -eq $born) { $null } else { $born.ToString('o') }
            executable_path = $_.ExecutablePath
            command_line = $_.CommandLine
        }
    })
    $sampleEnd = [DateTime]::UtcNow
    $value = [ordered]@{
        schema = 'newer-native-b1-complete-current-process-inventory-proposal.v1'
        sample_start_utc = $sampleStart.ToString('o')
        sample_end_utc = $sampleEnd.ToString('o')
        sample_start_utc_ticks = [long]$sampleStart.Ticks
        sample_end_utc_ticks = [long]$sampleEnd.Ticks
        boot_utc_ticks = [long]$operatingSystem.LastBootUpTime.ToUniversalTime().Ticks
        query_succeeded = $true
        filtered = $false
        row_count = [long]$rows.Count
        rows = $rows
        scope = 'all Win32_Process rows returned at this query; not atomic enumeration or complete historical ancestry'
    }
    [Console]::Out.WriteLine(($value | ConvertTo-Json -Depth 8 -Compress))
    exit 0
} catch {
    [Console]::Error.WriteLine($_.Exception.ToString())
    exit 99
}
'''


class ClosedQuietCollector(RuntimeError):
    pass


class IncompleteQuietEvidence(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise ValueError(message)


def integer(value, minimum=0):
    require(type(value) is int and value >= minimum, 'Exact nonnegative integer required; bool/float are rejected')
    return value


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def parse(raw, maximum=MAX_CONTROL):
    require(type(raw) is bytes and len(raw) <= maximum, 'Bounded actual bytes required')
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
    require(type(value) is dict and set(value) == {'path', 'bytes', 'sha256'}, 'Exact byte descriptor required')
    require(type(value['path']) is str and Path(value['path']).is_absolute() and '\x00' not in value['path'],
            'Absolute path required')
    integer(value['bytes'])
    require(value['bytes'] <= maximum, 'Byte descriptor exceeds bound')
    require(type(value['sha256']) is str and len(value['sha256']) == 64 and
            all(c in '0123456789abcdef' for c in value['sha256']), 'Lowercase SHA256 required')
    return value


def time_relation(text_value, ticks_value):
    """Integer consistency of a saved ISO8601 string; no current clock query."""
    integer(ticks_value, 1)
    require(type(text_value) is str and len(text_value) <= 64, 'Bounded explicit UTC string required')
    instant = datetime.fromisoformat(text_value.replace('Z', '+00:00'))
    require(instant.tzinfo is not None and instant.utcoffset().total_seconds() == 0, 'Explicit UTC required')
    epoch = datetime(1, 1, 1, tzinfo=timezone.utc)
    delta = instant.astimezone(timezone.utc) - epoch
    observed_microsecond_ticks = ((delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds) * 10
    require(observed_microsecond_ticks // 10 == ticks_value // 10, 'Saved time string and integer ticks disagree')
    return {'saved_relation_only': True, 'sub_microsecond_ticks_preserved': ticks_value % 10}


def row_relation(row):
    require(type(row) is dict and set(row) == {'pid', 'parent_pid', 'name', 'creation_utc_ticks',
            'creation_utc', 'executable_path', 'command_line'}, 'Exact complete inventory row required')
    integer(row['pid'])  # PID0 is a genuine Windows row, never an actor identity.
    integer(row['parent_pid'])
    for key in ('name', 'executable_path', 'command_line'):
        require(row[key] is None or (type(row[key]) is str and '\x00' not in row[key]), 'Raw nullable text must be preserved')
    if row['creation_utc_ticks'] is None:
        require(row['creation_utc'] is None, 'Missing creation requires raw null time')
    else:
        time_relation(row['creation_utc'], row['creation_utc_ticks'])
    return row


def inventory_relation(raw_stdout, raw_stderr, actual_query_exit, expected_boot_ticks):
    """Saved candidate consistency only. Even success has no release authority."""
    integer(expected_boot_ticks, 1)
    require(type(raw_stderr) is bytes and len(raw_stderr) <= MAX_STDERR, 'Bounded exact stderr required')
    require(type(actual_query_exit) is int and actual_query_exit == 0, 'Actual external query exit0 required; absence is not exit')
    value = parse(raw_stdout, MAX_INVENTORY)
    require(type(value) is dict and set(value) == {'schema', 'sample_start_utc', 'sample_end_utc',
            'sample_start_utc_ticks', 'sample_end_utc_ticks', 'boot_utc_ticks', 'query_succeeded',
            'filtered', 'row_count', 'rows', 'scope'}, 'Exact full inventory result required')
    require(value['schema'] == 'newer-native-b1-complete-current-process-inventory-proposal.v1' and
            value['query_succeeded'] is True and value['filtered'] is False, 'Full successful CIM query required')
    require(value['boot_utc_ticks'] == expected_boot_ticks, 'Current boot differs')
    time_relation(value['sample_start_utc'], value['sample_start_utc_ticks'])
    time_relation(value['sample_end_utc'], value['sample_end_utc_ticks'])
    require(value['sample_start_utc_ticks'] <= value['sample_end_utc_ticks'], 'Query time reversed')
    require(type(value['rows']) is list and 1 <= len(value['rows']) <= MAX_ROWS, 'Bounded nonempty full list required')
    integer(value['row_count'])
    require(value['row_count'] == len(value['rows']), 'Full row count differs')
    seen = set()
    for row in value['rows']:
        row_relation(row)
        require(row['pid'] not in seen, 'Duplicate PID makes current inventory ambiguous')
        seen.add(row['pid'])
    return {'inventory': value, 'stderr_bytes': len(raw_stderr), 'saved_relation_only': True,
            'historical_descendant_exclusion_proven': False, 'execution_permission': False}


def held_identity_relation(identity):
    require(type(identity) is dict, 'Saved held identity mapping required')
    integer(identity['pid'], 1)
    integer(identity['creation_filetime_100ns'], 1)
    integer(identity['creation_utc_ticks'], 1)
    require(identity['creation_utc_ticks'] == identity['creation_filetime_100ns'] + FILETIME_TO_UTC_TICKS,
            'Held FILETIME and UTC ticks disagree')
    require(type(identity['image']) is str and Path(identity['image']).is_absolute(), 'Saved actual held image required')
    return identity


def held_exit_relation(exit_value, identity):
    """Association to already saved continuous-held exit, never API reobservation."""
    held_identity_relation(identity)
    require(type(exit_value) is dict and exit_value['identity'] == identity and
            exit_value['wait_result'] == 0 and type(exit_value['wait_result']) is int,
            'Saved continuously held signaled exit required')
    for key in ('pid', 'creation_filetime_100ns', 'creation_utc_ticks'):
        integer(exit_value[key], 1)
        require(exit_value[key] == identity[key], 'Saved exited identity differs')
    integer(exit_value['exit_code_unsigned_dword'])
    require(exit_value['exit_code_unsigned_dword'] <= 0xffffffff, 'Actual DWORD out of range')
    integer(exit_value['exit_filetime_100ns'], 1)
    integer(exit_value['exit_utc_ticks'], 1)
    require(exit_value['exit_utc_ticks'] == exit_value['exit_filetime_100ns'] + FILETIME_TO_UTC_TICKS and
            exit_value['exit_utc_ticks'] >= identity['creation_utc_ticks'] and
            exit_value['same_retained_handle_pid_creation_verified'] is True, 'Saved complete actual exit required')
    return {'saved_relation_only': True, 'exit_code_unsigned_dword': exit_value['exit_code_unsigned_dword'],
            'scientific_success_inferred': False, 'process_reopened_after_exit': False}


def same_cim_birth(row, identity):
    """CIM microseconds vs API100ns: integer bins, never float/round or PID-only."""
    row_relation(row)
    held_identity_relation(identity)
    return row['pid'] == identity['pid'] and row['creation_utc_ticks'] is not None and \
        row['creation_utc_ticks'] // 10 == identity['creation_utc_ticks'] // 10


def classify_candidate_inventory(inventory, captured_actors, live_observer_identities,
                                 science_scope, actual_slot_history_unresolved):
    """Pure caller-data relation, explicitly NOT the actual independent collector.

    Runtime body rereads independently pinned declared evidence; passing arrays
    directly here never licenses guardian.unobserved_descendants=False or unlock.
    """
    require(type(inventory) is dict and type(inventory['rows']) is list, 'Saved validated inventory required')
    require(type(captured_actors) is list and type(live_observer_identities) is list and
            type(actual_slot_history_unresolved) is bool, 'Candidate actor/observer mappings required')
    require(type(science_scope) is dict and set(science_scope) == {'exact_commands', 'diagnostic_path_fragments',
            'science_capable_image_names'}, 'Explicit candidate command/path range required')
    for values in science_scope.values():
        require(type(values) is list and all(type(s) is str and s for s in values), 'Saved scope lists required')
    rows = inventory['rows']
    for row in rows:
        row_relation(row)
    by_pid = {row['pid']: row for row in rows}
    require(len(by_pid) == len(rows), 'Ambiguous duplicate PID')
    unresolved, foreign, current_parent_rows, pid_reuses = [], [], [], []
    actor_births = {}
    for actor in captured_actors:
        require(type(actor) is dict and set(actor) == {'label', 'identity', 'actual_exit', 'confirmation'}, 'Exact actor candidate required')
        require(type(actor['label']) is str and actor['label'], 'Actor label required')
        identity = held_identity_relation(actor['identity'])
        key = (identity['pid'], identity['creation_utc_ticks'])
        require(key not in actor_births, 'Duplicate captured actor identity')
        actor_births[key] = actor
        if actor['actual_exit'] is None:
            unresolved.append({'kind': 'captured_actual_exit_missing', 'label': actor['label'], 'identity': identity})
        else:
            held_exit_relation(actor['actual_exit'], identity)
        require(type(actor['confirmation']) is list and len(actor['confirmation']) == 2,
                'Two saved live confirmations required')
        for snapshot in actor['confirmation']:
            require(snapshot['pid'] == identity['pid'] and snapshot['creation_utc_ticks'] == identity['creation_utc_ticks'],
                    'Saved live confirmation identity differs')
        current = by_pid.get(identity['pid'])
        if current is not None:
            if same_cim_birth(current, identity):
                unresolved.append({'kind': 'captured_actor_currently_present', 'label': actor['label'], 'row': current,
                                   'saved_exit_claim_present': actor['actual_exit'] is not None})
            elif current['creation_utc_ticks'] is None:
                unresolved.append({'kind': 'same_numeric_pid_creation_unknown', 'identity': identity, 'row': current})
            else:
                pid_reuses.append({'old_identity': identity, 'current_row': current, 'not_old_actor': True,
                                   'old_exit_inferred': False})
    live_keys = set()
    for observer in live_observer_identities:
        require(type(observer) is dict and set(observer) == {'identity', 'complete_command', 'current_parent_identity'},
                'Exact actual live observer association required')
        identity = held_identity_relation(observer['identity'])
        parent_identity = held_identity_relation(observer['current_parent_identity'])
        row = by_pid.get(identity['pid'])
        parent = by_pid.get(parent_identity['pid'])
        require(row is not None and same_cim_birth(row, identity) and row['command_line'] == observer['complete_command'] and
                type(observer['complete_command']) is str and parent is not None and same_cim_birth(parent, parent_identity) and
                row['parent_pid'] == parent['pid'] and parent['creation_utc_ticks'] <= row['creation_utc_ticks'],
                'Actual observer command/current parent identity differs')
        live_keys.add((row['pid'], row['creation_utc_ticks']))
    for row in rows:
        parent = by_pid.get(row['parent_pid'])
        parent_state = 'current_parent_missing'
        if parent is not None:
            if row['creation_utc_ticks'] is None or parent['creation_utc_ticks'] is None:
                parent_state = 'current_parent_birth_unknown'
            elif parent['creation_utc_ticks'] > row['creation_utc_ticks']:
                parent_state = 'parent_numeric_pid_reused_after_child_birth'
            else:
                parent_state = 'current_parent_identity_candidate_not_historical_parent_proof'
        current_parent_rows.append({'child': row, 'current_parent': parent, 'relation': parent_state})
        exact_observer = (row['pid'], row['creation_utc_ticks']) in live_keys
        command = row['command_line']
        image_name = (row['name'] or '').casefold()
        diagnostics = []
        if command is not None:
            if command in science_scope['exact_commands']:
                diagnostics.append('exact declared scientific command')
            folded = command.casefold()
            if any(fragment.casefold() in folded for fragment in science_scope['diagnostic_path_fragments']):
                diagnostics.append('declared scientific path fragment; diagnostic blocker, not ownership proof')
        science_capable = image_name in {s.casefold() for s in science_scope['science_capable_image_names']}
        if not exact_observer and (diagnostics or science_capable):
            foreign.append({'row': row, 'classification': 'potential external scientific process',
                            'reasons': diagnostics or ['science-capable image name'], 'ownership_inferred': False})
            if command is None:
                unresolved.append({'kind': 'science_capable_actual_command_unknown', 'row': row})
        elif command is None and not exact_observer:
            # A nullable system command remains unknown. This need not be called
            # foreign science, but cannot support a claim of complete exclusion.
            unresolved.append({'kind': 'non_observer_actual_command_unknown', 'row': row,
                               'foreign_science_asserted': False})
    # Enumerate the full CURRENT parent graph, including all reachable levels.
    # A missing old parent cannot be matched by PID alone as a proved ancestor.
    # It may still create a finite birth-window residual candidate, marked unknown.
    possible = {}
    for row in rows:
        if (row['pid'], row['creation_utc_ticks']) in live_keys:
            continue
        for actor in captured_actors:
            identity = actor['identity']
            if row['parent_pid'] != identity['pid']:
                continue
            parent = by_pid.get(identity['pid'])
            lower = identity['creation_utc_ticks'] // 10
            upper = actor['actual_exit']['exit_utc_ticks'] // 10 if actor['actual_exit'] is not None else None
            born = row['creation_utc_ticks'] // 10 if row['creation_utc_ticks'] is not None else None
            live_parent_match = parent is not None and same_cim_birth(parent, identity)
            bounded_birth_candidate = born is None or (born >= lower and (upper is None or born <= upper))
            if live_parent_match or bounded_birth_candidate:
                possible[row['pid']] = {'row': row, 'captured_anchor_identity': identity,
                    'current_parent': parent, 'kind': 'possible_current_descendant_anchor',
                    'direct_current_parent_birth_matches': live_parent_match,
                    'historical_parentage_proven': False, 'numeric_pid_alone_is_ancestor_proof': False}
    remaining = True
    while remaining:
        remaining = False
        for row in rows:
            if row['pid'] in possible or (row['pid'], row['creation_utc_ticks']) in live_keys:
                continue
            parent = by_pid.get(row['parent_pid'])
            if parent is None or parent['pid'] not in possible:
                continue
            child_born, parent_born = row['creation_utc_ticks'], parent['creation_utc_ticks']
            if child_born is None or parent_born is None or parent_born <= child_born:
                possible[row['pid']] = {'row': row, 'current_parent': parent,
                    'captured_anchor_identity': possible[parent['pid']]['captured_anchor_identity'],
                    'kind': 'possible_current_descendant_graph', 'historical_parentage_proven': False,
                    'numeric_pid_alone_is_ancestor_proof': False}
                remaining = True
    unresolved.extend(possible.values())
    if actual_slot_history_unresolved:
        unresolved.append({'kind': 'finite_actual_slot_lineage_unresolved', 'reason': UNRESOLVED_SLOT_HISTORY,
                           'unbounded_arbitrary_history_required': False})
    return {'unknown_or_live_descendants': unresolved, 'foreign_scientific_processes': foreign,
            'current_parent_observations': current_parent_rows, 'numeric_pid_reuses': pid_reuses,
            'caller_candidate_relation_only': True, 'release_authorized': False,
            'absence_is_exit_proof': False, 'full_current_inventory_is_historical_capture': False}


def boundary_candidate_relation(first, second):
    """Saved sampling interval only, not real sleep or permission to release."""
    integer(first['sample_end_utc_ticks'], 1)
    integer(second['sample_start_utc_ticks'], 1)
    gap = second['sample_start_utc_ticks'] - first['sample_end_utc_ticks']
    require(gap >= MIN_BOUNDARY_SECONDS * 10000000, 'Saved full-query intervals must be at least15s apart')
    require(first['boot_utc_ticks'] == second['boot_utc_ticks'], 'Boundary spans different boots')
    return {'saved_relation_only': True, 'separation_utc_ticks': gap, 'release_authorized': False}


def _read_bound(record, maximum=MAX_CONTROL):
    raise ClosedQuietCollector('Closed source-only bounded reader; independent execution authority is not installed')
    descriptor(record, maximum)
    path = Path(record['path'])
    require(path.stat().st_size == record['bytes'], 'Actual size differs before bounded read')
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        raw = stream.read(record['bytes'] + 1)
        after = os.fstat(stream.fileno())
    require(len(raw) == record['bytes'] and (before.st_size, before.st_mtime_ns, before.st_ino) ==
            (after.st_size, after.st_mtime_ns, after.st_ino), 'Bounded bytes changed')
    require(hashlib.sha256(raw).hexdigest() == record['sha256'], 'Actual SHA256 differs')
    return raw


def _new_record(path, value):
    raise ClosedQuietCollector('Closed source-only CreateNew writer; no observation or attempt is permitted')
    raw = canonical(value) + b'\n'
    require(len(raw) <= MAX_CONTROL, 'New record exceeds bound')
    with Path(path).open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {'path': str(Path(path).resolve()), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def _fixed_helper():
    raise ClosedQuietCollector('Closed source-only import/API interface; adopted CPU fixture is not native runtime validation')
    record = {'path': str(HELPER), 'bytes': HELPER_BYTES, 'sha256': HELPER_SHA256}
    _read_bound(record)
    spec = importlib.util.spec_from_file_location('closed_quiet_fixed_evidence_helper', HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _authority(context):
    raise ClosedQuietCollector('Closed source-only authority reader; context or caller arrays cannot grant execution')
    if any(pin is None for pin in (REVIEWED_QUIET_EXECUTION_AUTHORITY_PIN,
            REVIEWED_FINITE_SLOT_LINEAGE_METHOD_PIN, REVIEWED_GUARDIAN_INTEGRATION_SOURCE_PIN)):
        raise IncompleteQuietEvidence('Independent quiet source/finite-slot-lineage/guardian integration pins are absent')
    root = parse(_read_bound(REVIEWED_QUIET_EXECUTION_AUTHORITY_PIN))
    require(root['schema'] == 'newer-native-b1-quiet-execution-authority-proposal.v1' and
            root['execution_released'] is True and root['guardian_plan'] == context.plan_record,
            'Exact separately adopted quiet execution root and original guardian plan binding required')
    require(root['guardian_integration'] == REVIEWED_GUARDIAN_INTEGRATION_SOURCE_PIN and
            root['finite_slot_lineage_method'] == REVIEWED_FINITE_SLOT_LINEAGE_METHOD_PIN,
            'Independent actual source pins differ')
    _read_bound(root['guardian_integration'])
    _read_bound(root['finite_slot_lineage_method'])
    require(root['guardian_identity'] == context.me.identity and root['observation_parent'] == str(context.directory),
            'Actual guardian and finite evidence directory differ')
    _read_bound(root['collector_source'])
    require(root['collector_source']['path'] == str(HERE / 'quiet_collector.py'), 'Wrong exact collector path')
    return root


def _query_full_inventory(context, authority, directory):
    raise ClosedQuietCollector('Closed source-only full CIM subprocess body; never executed, no Popen or API permission')
    helper = _fixed_helper()
    require(not directory.exists(), 'Any previous sample directory, even empty, rejects replay')
    directory.mkdir()
    query_script = directory / 'full_inventory.ps1'
    script_raw = CIM_QUERY_PS.encode('utf-8')
    with query_script.open('xb') as stream:
        stream.write(script_raw)
        stream.flush()
        os.fsync(stream.fileno())
    query_source = {'path': str(query_script.resolve()), 'bytes': len(script_raw), 'sha256': hashlib.sha256(script_raw).hexdigest()}
    nonce = os.urandom(32).hex()
    request_record = _new_record(directory / 'query_request.json', {
        'schema': 'newer-native-b1-full-cim-read-request-proposal.v1', 'nonce': nonce,
        'control_directory': str(directory), 'query_source': query_source,
        'actual_guardian_identity': context.me.identity, 'execution_or_science_authority': False})
    _read_bound(authority['query_interpreter_image'])
    argv = [authority['query_interpreter_image']['path'], '-NoLogo', '-NoProfile', '-NonInteractive',
            '-ExecutionPolicy', 'Bypass', '-File', str(query_script), '-RequestPath', request_record['path'],
            '-ControlDirectory', str(directory)]
    complete_command = subprocess.list2cmdline(argv)
    stdout_path, stderr_path = directory / 'query.stdout', directory / 'query.stderr'
    stdout, stderr = stdout_path.open('xb'), stderr_path.open('xb')
    # A future integrated guardian must register this actual prospective child
    # before Popen and retain it on EVERY failure. This original guardian lacks
    # that adopted integration; no temporary source is being installed here.
    context.streams.extend((stdout, stderr))
    context.unobserved_descendants = True
    proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, shell=False,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    context.popen_processes.append(proc)
    held = helper.HeldProcess(context.api, proc.pid, context.ledger, 'actual_full_cim_query_interpreter')
    context.processes.append(held)
    observations = held.confirm_twice(complete_command, authority['query_interpreter_image']['path'], context.me)
    ready_record, ready = _wait_ready(directory / 'query_ready.json', 45)
    require(set(ready) == {'schema', 'nonce', 'request_sha256', 'self_pid', 'execution_or_science_authority'} and
            ready['schema'] == 'newer-native-b1-full-cim-read-ready-proposal.v1' and ready['nonce'] == nonce and
            ready['request_sha256'] == request_record['sha256'] and type(ready['self_pid']) is int and
            ready['self_pid'] == held.identity['pid'] and ready['execution_or_science_authority'] is False,
            'Actual blocked query READY differs from external held identity/request bytes')
    ack_record = _new_record(directory / 'query_ack.json', {
        'schema': 'newer-native-b1-full-cim-read-ack-proposal.v1', 'nonce': nonce,
        'request_sha256': request_record['sha256'], 'actual_held_query_identity': held.identity,
        'execution_or_science_authority': False})
    observed_exit = None
    while observed_exit is None:
        observed_exit = held.wait(60000)
    held_exit_relation(observed_exit, held.identity)
    actual_exit = proc.wait()
    require(type(actual_exit) is int and actual_exit == 0 and observed_exit['exit_code_unsigned_dword'] == 0,
            'Actual query held/Popen exits both must be zero; no synthesized success')
    stdout.close()
    stderr.close()
    raw_stdout = helper.seal_closed_log(context.api, stdout_path, (held,), (stdout, stderr))
    raw_stderr = helper.seal_closed_log(context.api, stderr_path, (held,), (stdout, stderr))
    stdout_bound = {key: raw_stdout[key] for key in ('path', 'bytes', 'sha256')}
    stderr_bound = {key: raw_stderr[key] for key in ('path', 'bytes', 'sha256')}
    relation = inventory_relation(_read_bound(stdout_bound, MAX_INVENTORY), _read_bound(stderr_bound, MAX_STDERR),
                                  actual_exit, authority['boot_utc_ticks'])
    require(observed_exit['exit_utc_ticks'] >= relation['inventory']['sample_end_utc_ticks'],
            'Actual query exit predates its full inventory')
    return {'inventory': relation['inventory'], 'query_source': query_source, 'raw_stdout': raw_stdout,
            'raw_stderr': raw_stderr, 'actual_held_query_identity': held.identity, 'actual_query_exit': observed_exit,
            'actual_popen_exit': actual_exit, 'live_query_confirmations': observations,
            'query_complete_command': complete_command, 'query_current_parent_identity': context.me.identity,
            'request': request_record, 'READY': ready_record, 'ACK': ack_record,
            'measurement_admitted': False, 'current_inventory_not_complete_history': True}


def _wait_ready(path, seconds):
    raise ClosedQuietCollector('Closed source-only bounded READY wait; this is not scientific release or actual execution evidence')
    require(type(seconds) is int and 1 <= seconds <= 45, 'Bounded prospective READY wait required')
    deadline = time.monotonic() + seconds
    while not path.exists():
        if time.monotonic() >= deadline:
            raise IncompleteQuietEvidence('Actual full query READY is absent')
        time.sleep(0.05)
    before = path.stat()
    require(1 <= before.st_size <= 262144, 'Bounded READY required before read')
    with path.open('rb') as stream:
        raw = stream.read(before.st_size + 1)
        after = os.fstat(stream.fileno())
    require(len(raw) == before.st_size == after.st_size and before.st_mtime_ns == after.st_mtime_ns,
            'READY bytes changed or partial')
    return {'path': str(path.resolve()), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}, parse(raw)


def _read_declared_actual_evidence(authority):
    raise ClosedQuietCollector('Closed source-only evidence reader; no caller ledger or saved boolean is independent authority')
    # New declared evidence format deliberately is NOT claimed to be emitted by
    # sealed guardian_v3/helper. Future root adoption must bind its real producer.
    record = authority['finite_slot_evidence']
    value = parse(_read_bound(record))
    require(value['schema'] == 'newer-native-b1-finite-slot-quiet-evidence-proposal.v1' and
            value['producer_source'] == REVIEWED_FINITE_SLOT_LINEAGE_METHOD_PIN and
            value['guardian_identity'] == authority['guardian_identity'], 'Independent finite-slot producer relation differs')
    require(value['caller_assertions_are_authority'] is False and value['absence_is_exit_proof'] is False,
            'Incorrect evidence interpretation')
    # Each raw record is reread once by fixed binding; a caller-supplied array is
    # never accepted as independently captured held/process/stream evidence.
    require(type(value['actual_ledger_records']) is list and len(value['actual_ledger_records']) <= 4096,
            'Bounded actual ledger declaration required')
    actual_records = {}
    for item in value['actual_ledger_records']:
        descriptor(item)
        require(item['path'] not in actual_records, 'Duplicate ledger path')
        actual_records[item['path']] = parse(_read_bound(item))
    actors = []
    for declaration in value['captured_actor_declarations']:
        live = actual_records[declaration['held_open']['path']]
        confirm = actual_records[declaration['confirmed']['path']]
        terminal = actual_records[declaration['exit_observed']['path']]
        require(live['event'] == 'held_open' and confirm['event'] == 'confirmed' and terminal['event'] == 'exit_observed' and
                live['label'] == confirm['label'] == terminal['label'] == declaration['label'], 'Actual saved event labels differ')
        for event in (live, confirm, terminal):
            integer(event['utc_ns'], 1)
        require(live['utc_ns'] <= confirm['utc_ns'] <= terminal['utc_ns'], 'Saved held event order differs')
        identity = live['identity']
        held_exit_relation(terminal['value'], identity)
        actors.append({'label': declaration['label'], 'identity': identity, 'actual_exit': terminal['value'],
                       'confirmation': confirm['observations']})
    # Raw log content and saved close declaration remain two distinct bindings.
    # This source cannot prove global arbitrary-writer exclusion history.
    for log in value['actual_closed_stream_records']:
        closed = parse(_read_bound(log))
        require(closed['read_lock_denied_write_delete'] is True and closed['controller_streams_closed'] is True,
                'Saved designated held-exit/closed-stream seal required')
        integer(authority['maximum_closed_log_bytes'])
        require(authority['maximum_closed_log_bytes'] <= MAX_CLOSED_LOG, 'Closed control-log bound exceeds source maximum')
        _read_bound({key: closed[key] for key in ('path', 'bytes', 'sha256')}, authority['maximum_closed_log_bytes'])
    return value, actors


def _collect_snapshot(context):
    raise ClosedQuietCollector('Closed source-only quiet interface; guardian source remains sealed/unintegrated')
    authority = _authority(context)
    # Fresh actual timestamp names this new sample; a collision is fatal, never
    # an overwrite/retry. The fixed adopted parent is the authority boundary.
    sample_name = 'quiet_sample_' + str(time.time_ns())
    directory = Path(authority['observation_parent']) / sample_name
    sample = _query_full_inventory(context, authority, directory)
    evidence, actors = _read_declared_actual_evidence(authority)
    query_observer = {'identity': sample['actual_held_query_identity'],
        'complete_command': sample['query_complete_command'],
        'current_parent_identity': sample['query_current_parent_identity']}
    live_observers = evidence['actual_live_observer_declarations'] + [query_observer]
    candidate = classify_candidate_inventory(sample['inventory'], actors, live_observers,
            authority['scientific_command_scope'], actual_slot_history_unresolved=True)
    # No live collector/lineage integration has been validated. This exact source
    # refuses to clear the real flag from saved declarations or current absence.
    # A future reviewed derivative may resolve this FINITE actual-slot gap using
    # the separately adopted method/policy; it must preserve unknown historical
    # exits. Nothing demands proof of arbitrary unrelated past processes.
    candidate.update({'raw_sample': sample, 'independent_actual_slot_lineage_method_validated': False,
                      'guardian_unobserved_descendants_cleared': False, 'measurement_admitted': False})
    candidate['saved_report'] = _new_record(directory / 'quiet_candidate.json', candidate)
    return candidate


def collect_snapshot(context):
    raise ClosedQuietCollector('Closed public source-only entry; no current/future execution permission')
    return _collect_snapshot(context)


def collect_boundary(context):
    raise ClosedQuietCollector('Closed public source-only two-sample boundary; no sleep/API/lock release permission')
    first = _collect_snapshot(context)
    time.sleep(MIN_BOUNDARY_SECONDS)
    second = _collect_snapshot(context)
    boundary_candidate_relation(first['raw_sample']['inventory'], second['raw_sample']['inventory'])
    return {'first': first, 'second': second, 'release_authorized': False, 'measurement_admitted': False}


def main():
    raise ClosedQuietCollector('No startup runner or executable quiet collector is supplied by this closed source')


if __name__ == '__main__':
    raise SystemExit('Closed source-only quiet collector; not an execution or scientific admission entry')
