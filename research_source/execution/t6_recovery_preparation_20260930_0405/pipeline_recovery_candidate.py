"""PREPARATION ONLY until a separately adopted manifest and fresh root release exist.

This control-only guardian never imports scientific packages. The future native
environment probe is the original isolated function, not a metadata substitute.
No primary or successor controller is launched. No recovery/ValidateOnly mode is
provided. Importing this module has no filesystem or process side effects.
"""
from __future__ import annotations

import argparse
import copy
import ctypes
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).absolute().parent
EX = HERE.parent
ROOT = Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724')
PYTHON = Path(r'C:\项目\.venvs\lgm-baselines\Scripts\python.exe')
IO_SHA = 'd8e6209f5ff2c2180d053e6444cb7df6ec0846405fea7ad6dee9b76a8fcb8dfb'
MIN_COMMIT = 26 * 1024**3
STATE_NAMES = ('status.json', 'pipeline_status.json', 'extension_status.json',
               'latest_baseline_status.json', 'independent_comparison_status.json')
JOB_IDS = ('formal_aggregate', 'formal_figures', 'cross_dataset_transfer',
           'robustness', 'robustness_aggregate', 'query_analysis',
           'formal_efficiency_component')
ARTIFACTS = ('launch_intent.json', 'retired_pipeline_status.json',
             'launch.json', 'failure_after_intent.json', 'observed_exit.json',
             'pipeline.stdout.log', 'pipeline.stderr.log')
SCIENTIFIC = {'numpy', 'PIL', 'torch', 'torchvision', 'scipy', 'matplotlib'}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def binding(path):
    path = Path(path)
    require(path.suffix.lower() not in {'.pt', '.npz', '.npy', '.jpg', '.png'},
            'Forbidden large/scientific input: ' + str(path))
    data = path.read_bytes()
    require(len(data) < 16 * 1024**2, 'Input exceeds small-file bound: ' + str(path))
    return {'path': str(path), 'bytes': len(data), 'sha256': digest(data)}


def verify_binding(expected):
    got = binding(expected['path'])
    require(got == expected, 'Changed small input: ' + expected['path'])
    return got


def immutable(path, payload):
    with Path(path).open('xb') as stream:
        stream.write(encoded(payload))
        stream.flush()
        os.fsync(stream.fileno())


def assert_unused(folder):
    require(not Path(folder).exists(), 'Any previous attempt directory forbids replay')


def derive_seed(original, spec, capture_binding):
    require(original.get('schema') == 'lgm-evidence-pipeline.v1', 'Wrong pipeline schema')
    require(original.get('status') == 'failed', 'Expected exact failed attempt')
    jobs = original.get('jobs', [])
    require([j.get('id') for j in jobs] == list(JOB_IDS), 'Wrong seven-job order')
    for job in jobs[:6]:
        require(job.get('status') == 'completed' and type(job.get('exit_code')) is int
                and job['exit_code'] == 0, 'Predecessor not completed with original parent exit0')
        require(all(job.get(k) is not None for k in ('pid', 'started_utc', 'finished_utc')),
                'Missing original predecessor evidence')
    last = jobs[6]
    require(last.get('status') == 'failed' and last.get('exit_code') == 1,
            'Seventh job is not the captured exit1')
    require(last['command'] == spec['original_t6_command'], 'Changed T6 command')
    require(last['entrypoint_sha256'] == spec['original_t6_entrypoint_sha256'],
            'Changed T6 source')
    seed = copy.deepcopy(original)
    for key in ('supervisor_pid', 'supervisor_started_utc', 'heartbeat_utc',
                'active_stage', 'error', 'stopped_utc', 'ready_utc'):
        seed.pop(key, None)
    seed['status'] = 'waiting_for_primary'
    for key in ('pid', 'started_utc', 'finished_utc', 'exit_code', 'elapsed_seconds'):
        seed['jobs'][6].pop(key, None)
    seed['jobs'][6]['status'] = 'pending'
    seed['recovery_preparation'] = {
        'schema': 't6-pipeline-seed.v1', 'incident_capture': capture_binding,
        'failed_state_sha256': digest(encoded(original)),
        'failed_state_sha256_encoding': 'canonical preparation serialization; exact bytes separately bound',
        'scope': 'Only original seventh stage pending; first six complete records byte-value unchanged',
        'not_launched': True,
    }
    require(seed['jobs'][:6] == original['jobs'][:6], 'Predecessor record mutated')
    return seed


def validate_seed(seed, original, spec, capture_binding):
    require(seed == derive_seed(original, spec, capture_binding), 'Seed differs from exact derivative')
    for index in range(7):
        require({k: seed['jobs'][index][k] for k in ('id', 'command', 'entrypoint_sha256')} ==
                {k: original['jobs'][index][k] for k in ('id', 'command', 'entrypoint_sha256')},
                'Frozen job definition changed')


def validate_final_state(state, original):
    require(state.get('status') == 'ready_for_extension_preparation', 'Pipeline not ready')
    require(state.get('jobs', [])[:6] == original['jobs'][:6], 'Completed predecessor evidence changed')
    require(len(state.get('jobs', [])) == 7, 'Final pipeline job coverage differs')
    last = state['jobs'][6]
    require(all(last.get(k) == original['jobs'][6][k] for k in ('id', 'command', 'entrypoint_sha256')),
            'Final T6 command/source differs')
    require(last.get('status') == 'completed' and type(last.get('exit_code')) is int and last['exit_code'] == 0,
            'Original T6 parent exit0 absent')
    require(all(last.get(k) is not None for k in ('pid', 'started_utc', 'finished_utc')), 'Final T6 attempt identity missing')


def gpu_gate(result):
    require(type(result['exit_code']) is int and result['exit_code'] == 0, 'GPU query failed')
    rows = []
    for line in result['stdout'].splitlines():
        if not line.strip():
            continue
        cells = line.split(',', 1)
        require(len(cells) == 2 and cells[0].strip().isdigit(), 'Ambiguous nonempty GPU query row')
        pid = int(cells[0].strip())
        require(pid > 0 and bool(cells[1].strip()), 'Invalid GPU query identity')
        rows.append({'pid': pid, 'name': cells[1].strip()})
    require(not rows, 'Frozen GPU exclusivity not satisfied: ' + repr(rows))
    return result


def memory_gate(sample):
    for key in ('commit_limit_bytes', 'committed_bytes'):
        require(type(sample[key]) is int and sample[key] >= 0, 'Commit counter must be nonnegative integer')
    require(sample['commit_limit_bytes'] > 0 and sample['committed_bytes'] <= sample['commit_limit_bytes'],
            'Invalid commit counters')
    require(type(sample['available_commit_bytes']) is int, 'Commit bytes must be exact integer')
    require(sample['available_commit_bytes'] == sample['commit_limit_bytes']-sample['committed_bytes'],
            'Available commit calculation differs')
    require(sample['available_commit_bytes'] >= MIN_COMMIT, 'Available commit below 26 GiB admission')
    return sample


def prefix_gate(path, expected):
    # Before launch the entire file must equal the old closed attempt. After launch
    # verify the old byte prefix and report only the newly appended range.
    path = Path(path)
    with path.open('rb') as stream:
        old = stream.read(expected['bytes'])
        remaining = stream.read()
    require(len(old) == expected['bytes'] and digest(old) == expected['sha256'],
            'Old append-log prefix changed: ' + str(path))
    return {'path': str(path), 'old_bytes': expected['bytes'], 'old_sha256': digest(old),
            'new_start_offset': expected['bytes'], 'new_end_offset': expected['bytes'] + len(remaining),
            'new_bytes': len(remaining), 'new_sha256': digest(remaining)}


def state_cas(bindings):
    return [verify_binding(item) for item in bindings]


def publish_once(folder, state_path, original_binding, seed_bytes, payload, final_gate):
    """Called only with supervisor/shared locks held. Never rollback a partial.

    Cooperative lock plus final exact-byte comparison is not an OS transactional
    filesystem CAS against an uncooperative writer. Rename and exclusive-create
    failure remains permanently visible; no unseeded controller is launched.
    """
    folder = Path(folder)
    assert_unused(folder)
    final_admission = final_gate()
    verify_binding(original_binding)
    folder.mkdir(exist_ok=False)
    payload = dict(payload, final_admission=final_admission)
    immutable(folder / 'launch_intent.json', payload)
    verify_binding(original_binding)
    retired = folder / 'retired_pipeline_status.json'
    os.rename(state_path, retired)  # Windows refuses destination overwrite.
    require(binding(retired)['sha256'] == original_binding['sha256'], 'Retired state changed')
    with Path(state_path).open('xb') as stream:
        stream.write(seed_bytes)
        stream.flush()
        os.fsync(stream.fileno())
    require(Path(state_path).read_bytes() == seed_bytes, 'Seed publication incomplete')


def powershell(script):
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                            capture_output=True, text=True, encoding='utf-8-sig', errors='strict',
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    require(result.returncode == 0, 'Read-only PowerShell observation failed: ' + result.stderr)
    return json.loads(result.stdout)


def process_snapshot():
    return powershell("$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false); "
        "$rows=@(Get-CimInstance Win32_Process | ForEach-Object { "
        "[ordered]@{pid=[int]$_.ProcessId;parent_pid=[int]$_.ParentProcessId;name=$_.Name;"
        "command=$_.CommandLine;executable=$_.ExecutablePath;"
        "creation_utc=$(if($null-ne $_.CreationDate){$_.CreationDate.ToUniversalTime().ToString('o')}else{$null});"
        "creation_utc_ticks=$(if($null-ne $_.CreationDate){$_.CreationDate.ToUniversalTime().Ticks.ToString()}else{$null})} }); "
        "$boot=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime(); "
        "[ordered]@{observed_utc=[DateTime]::UtcNow.ToString('o');host_boot_utc=$boot.ToString('o');"
        "host_boot_utc_ticks=$boot.Ticks.ToString();processes=$rows} | ConvertTo-Json -Depth 8 -Compress")


def own_python_ids(snapshot):
    table = {p['pid']: p for p in snapshot['processes']}
    require(os.getpid() in table, 'Guardian identity absent')
    current = table[os.getpid()]
    own = set()
    for _ in range(2):
        require(current['name'].lower() in ('python.exe', 'pythonw.exe'), 'Unexpected guardian process name')
        require(str(Path(__file__).absolute()).lower() in (current.get('command') or '').lower(),
                'Guardian ancestry command mismatch')
        own.add(current['pid'])
        parent = table.get(current['parent_pid'])
        if not parent or parent['name'].lower() not in ('python.exe', 'pythonw.exe'):
            break
        current = parent
    return own


def processes_gate(snapshot, primary_pid, allowed):
    rows = snapshot['processes']
    # Original supervisor uses a numerical primary PID check, so even known reuse
    # blocks this candidate. Never alter the completed primary state to evade it.
    require(not any(p['pid'] == primary_pid for p in rows), 'Original primary numeric PID occupied (possibly reuse)')
    conflicts = []
    for p in rows:
        if p['pid'] in allowed:
            continue
        command = (p.get('command') or '').lower()
        if p['name'].lower() in ('python.exe', 'pythonw.exe') or any(x in command for x in (
                'supervise_pipeline.py', 'run_controller_with_state_retry', 'formal_efficiency',
                'continue_formal_matrix', 'supervise_extensions', 'supervise_latest_baselines',
                'supervise_independent_comparisons', 'run_frozen_robustness', 'run_transactions_')):
            conflicts.append(p)
    require(not conflicts, 'A controller/scientific/unknown Python process remains: ' + repr(conflicts))
    return snapshot


def fresh_gpu():
    completed = subprocess.run(['nvidia-smi', '--query-compute-apps=pid,process_name',
                                '--format=csv,noheader,nounits'], capture_output=True, text=True,
                               encoding='utf-8', errors='strict',
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    return gpu_gate({'observed_utc': utc(), 'exit_code': completed.returncode,
                     'stdout': completed.stdout, 'stderr': completed.stderr})


def fresh_memory():
    data = powershell("$ErrorActionPreference='Stop'; $m=Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory; "
                      "if($null-eq $m.CommitLimit -or $null-eq $m.CommittedBytes){throw 'Missing commit counter'}; "
                      "[ordered]@{observed_utc=[DateTime]::UtcNow.ToString('o');"
                      "commit_limit_bytes=$m.CommitLimit.ToString();committed_bytes=$m.CommittedBytes.ToString();"
                      "available_commit_bytes=([decimal]$m.CommitLimit-[decimal]$m.CommittedBytes).ToString('0')}"
                      " | ConvertTo-Json -Compress")
    for key in ('commit_limit_bytes', 'committed_bytes', 'available_commit_bytes'):
        require(isinstance(data[key], str) and data[key].isdigit(), 'Noninteger memory counter')
        data[key] = int(data[key])
    return memory_gate(data)


class ByteLock:
    def __init__(self, path):
        import msvcrt
        self.path = Path(path)
        require(self.path.is_file() and self.path.stat().st_size >= 1,
                'Persistent byte-lock file missing/empty; separately reviewed initialization required: ' + str(path))
        self.stream = self.path.open('r+b')  # Does not truncate/create/write.
        self.stream.seek(0)
        try:
            msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
        except BaseException:
            self.stream.close()
            raise

    def close(self):
        if self.stream is not None:
            import msvcrt
            self.stream.seek(0)
            msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
            self.stream.close()
            self.stream = None


def release_gate(release_path, release_sha, manifest_path, adoption_path, adoption_sha):
    release_binding = binding(release_path)
    require(release_binding['sha256'] == release_sha, 'Release SHA mismatch')
    release = read(release_path)
    manifest_binding = binding(manifest_path)
    adoption_binding = binding(adoption_path)
    require(adoption_binding['sha256'] == adoption_sha, 'Root adoption SHA mismatch')
    require(release.get('schema') == 't6-pipeline-recovery-release.v1' and
            release.get('scope') == 'pipeline_only_original_stage7' and
            release.get('execute') is True, 'No explicit pipeline-only execution release')
    require(release.get('source_manifest') == manifest_binding and
            release.get('root_adoption') == adoption_binding, 'Release does not bind adopted candidate')
    adoption = read(adoption_path)
    require(adoption.get('schema') == 't6-pipeline-recovery-source-adoption.v1' and
            adoption.get('source_manifest') == manifest_binding and
            adoption.get('approved_for_future_gated_execution') is True, 'Root source adoption missing')
    now = dt.datetime.now(dt.timezone.utc)
    issued = dt.datetime.fromisoformat(release['issued_utc'])
    expires = dt.datetime.fromisoformat(release['expires_utc'])
    require(issued.tzinfo is not None and expires.tzinfo is not None and
            issued <= now < expires and (expires-issued).total_seconds() <= 900,
            'Release expired, future-dated, or longer than 15 minutes')
    return release_binding, manifest_binding, adoption_binding


def load_native_module(path):
    require(not SCIENTIFIC.intersection(name.split('.')[0] for name in sys.modules), 'Guardian imported science')
    spec = importlib.util.spec_from_file_location('t6_original_native_environment_control', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def creation_ticks(handle):
    kernel = ctypes.windll.kernel32
    class FT(ctypes.Structure):
        _fields_ = [('lo', ctypes.c_ulong), ('hi', ctypes.c_ulong)]
    values = [FT() for _ in range(4)]
    require(kernel.GetProcessTimes(ctypes.c_void_p(handle), *[ctypes.byref(v) for v in values]),
            'Cannot obtain child creation time')
    ticks = (values[0].hi << 32) | values[0].lo
    return str(ticks + 504911232000000000)


def exact_process_handle(pid):
    """Capture actual API creation FILETIME and waitable handle; no guessed identity."""
    kernel = ctypes.windll.kernel32
    kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel.OpenProcess.restype = ctypes.c_void_p
    handle = kernel.OpenProcess(0x00100000 | 0x1000, False, pid)
    require(handle, 'Cannot obtain wait/query handle for observed child PID ' + str(pid))
    try:
        return handle, creation_ticks(handle)
    except BaseException:
        kernel.CloseHandle(ctypes.c_void_p(handle))
        raise


def launcher_anchor(child):
    # Duplicate the exact Popen-retained handle, never reopen a possibly reused PID.
    kernel = ctypes.windll.kernel32
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    current = kernel.GetCurrentProcess()
    duplicate = ctypes.c_void_p()
    require(kernel.DuplicateHandle(ctypes.c_void_p(current), ctypes.c_void_p(int(child._handle)),
            ctypes.c_void_p(current), ctypes.byref(duplicate), 0, False, 2), 'Cannot retain Popen launcher handle')
    try:
        ticks = creation_ticks(duplicate.value)
    except BaseException:
        kernel.CloseHandle(duplicate)
        raise
    return {'identity': {'pid': child.pid, 'parent_pid': os.getpid(), 'creation_utc_ticks': ticks,
                         'name': 'python.exe', 'command': None, 'creation_utc': None,
                         'identity_source': 'Popen handle; CIM command not yet observed'},
            'api_creation_utc_ticks': ticks, 'handle': duplicate.value, 'controller_tokens_checked': False}


def command_tokens(command_line):
    shell = ctypes.windll.shell32
    shell.CommandLineToArgvW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
    count = ctypes.c_int()
    pointer = shell.CommandLineToArgvW(command_line, ctypes.byref(count))
    require(bool(pointer), 'Cannot parse actual Windows command')
    try:
        return [pointer[i] for i in range(count.value)]
    finally:
        ctypes.windll.kernel32.LocalFree(ctypes.cast(pointer, ctypes.c_void_p))


def controller_tokens_match(tokens, command, allowed_python_paths):
    require(len(tokens) == len(command) and tokens[1:] == command[1:], 'Controller arguments/role/manifest changed')
    require(os.path.normcase(os.path.abspath(tokens[0])) in allowed_python_paths,
            'Controller executable spelling is not an observed baseline interpreter')


def launch_record_once(folder, payload):
    """No repeated write loop on reentry; existing evidence is immutable and checked."""
    path = folder/'launch.json'
    if path.exists():
        old = read(path)
        require(old['popen_launcher_pid'] == payload['popen_launcher_pid'] and old['command'] == payload['command'] and
                old['launcher_api_creation_utc_ticks'] == payload['launcher_api_creation_utc_ticks'],
                'Existing launch evidence belongs to another identity')
        return
    immutable(path, payload)


def validate_launch_record(folder, pid, api_ticks, command):
    record = read(folder/'launch.json')
    require(record['popen_launcher_pid'] == pid and record['command'] == command and
            record['launcher_api_creation_utc_ticks'] == api_ticks, 'Closed launch record identity mismatch')
    return binding(folder/'launch.json')


def handle_status(handle):
    code = ctypes.c_ulong()
    require(ctypes.windll.kernel32.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(code)),
            'Cannot observe retained process handle')
    return {'signaled': ctypes.windll.kernel32.WaitForSingleObject(ctypes.c_void_p(handle), 0) == 0,
            'exit_code_observed': code.value}


def collect_descendants(snapshot, tracked, anchor, command, allowed_python_paths):
    # tracked entries retain API handles even after numeric PIDs disappear/reuse.
    rows = snapshot['processes']
    changed = True
    while changed:
        changed = False
        for row in rows:
            if row.get('creation_utc_ticks') is None:
                continue
            key = (row['pid'], int(row['creation_utc_ticks'])//10)
            if key in tracked:
                entry = tracked[key]
                if row.get('command') and str(EX/'run_controller_with_state_retry_v2.py').lower() in row['command'].lower():
                    controller_tokens_match(command_tokens(row['command']), command, allowed_python_paths)
                    entry['controller_tokens_checked'] = True
                entry['identity'] = row
                continue
            parents = [entry for entry in tracked.values() if entry['identity']['pid'] == row['parent_pid']
                       and int(row['creation_utc_ticks']) >= int(entry['identity']['creation_utc_ticks'])]
            # A later numerical reuse of the original launcher is not ours.
            if not parents:
                continue
            # Avoid descendants of a later reused PID: parent must be alive on its
            # original retained handle at observation, or direct original launcher.
            if not any(not handle_status(e['handle'])['signaled'] for e in parents):
                continue
            require(row.get('command'), 'Child command unavailable; keep lock and inspect')
            is_controller = str(EX/'run_controller_with_state_retry_v2.py').lower() in row['command'].lower()
            if is_controller:
                controller_tokens_match(command_tokens(row['command']), command, allowed_python_paths)
            handle, api_ticks = exact_process_handle(row['pid'])
            # CIM microsecond truncation vs API 100 ns precision is integer-only.
            if int(api_ticks) // 10 != int(row['creation_utc_ticks']) // 10:
                ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(handle))
                raise RuntimeError('PID changed during CIM/API identity capture')
            tracked[key] = {'identity': row, 'api_creation_utc_ticks': api_ticks, 'handle': handle,
                            'controller_tokens_checked': is_controller}
            changed = True


def serializable_tracked(tracked):
    return [{'identity': entry['identity'], 'api_creation_utc_ticks': entry['api_creation_utc_ticks'],
             'controller_tokens_checked': entry.get('controller_tokens_checked', False),
             'handle_observation': handle_status(entry['handle'])} for entry in tracked.values()]


def observe_until_exit(child, tracked, folder, command, anchor, allowed_python_paths):
    """Keep all outer locks on ANY monitoring error until two clean absence scans.

    Captured handles prove exits only for captured identities. A very short-lived
    descendant can evade polling; original supervisor parent evidence is retained
    separately. No result here is scientific acceptance.
    """
    errors = []
    empty = 0
    seen_owner = False
    launch_record_attempted = False
    while True:
        try:
            snapshot = process_snapshot()
            collect_descendants(snapshot, tracked, anchor, command, allowed_python_paths)
            state = read(EX/'pipeline_status.json')
            owner = state.get('supervisor_pid')
            seen_owner |= any(e['identity']['pid'] == owner and e.get('controller_tokens_checked')
                              for e in tracked.values())
            if not launch_record_attempted and tracked:
                launch_record_attempted = True
                launch_record_once(folder, {'observed_utc': utc(), 'popen_launcher_pid': child.pid,
                          'launcher_api_creation_utc_ticks': anchor['api_creation_utc_ticks'],
                          'command': command, 'identities': serializable_tracked(tracked),
                          'owner_seen': seen_owner})
            # Every Python aside from this guardian is conservative evidence of
            # remaining science, even if a descendant escaped a polling interval.
            allowed = own_python_ids(snapshot)
            foreign = [p for p in snapshot['processes'] if p['pid'] not in allowed and
                       (p['name'].lower() in ('python.exe', 'pythonw.exe') or
                        any(token in (p.get('command') or '').lower() for token in
                            ('run_transactions_', 'run_controller_with_state_retry', 'supervise_pipeline.py')))]
            handles_done = all(handle_status(e['handle'])['signaled'] for e in tracked.values())
            exited = child.poll() is not None and handles_done and not foreign
            empty = empty+1 if exited else 0
            if empty >= 2:
                return {'observed_utc': utc(), 'popen_launcher_exit_code': child.returncode,
                        'captured_processes': serializable_tracked(tracked), 'actual_owner_observed': seen_owner,
                        'final_state': binding(EX/'pipeline_status.json'), 'final_runtime_status': state.get('status'),
                        'two_absence_scans': True, 'monitor_errors': errors,
                        'limits': ['Polling cannot recover an unobserved short-lived interpreter or descendant exit code.',
                                   'Captured handle exits and parent Popen return are distinct evidence.',
                                   'No T6 artifact acceptance or successor release is performed.']}
            time.sleep(1)
        except BaseException as error:
            empty = 0
            errors.append({'utc': utc(), 'type': type(error).__name__, 'error': str(error)})
            # Failure diagnostics must not release the shared lock. Retain first
            # error if possible; continue observing without killing any process.
            try:
                if not (folder/'postlaunch_monitor_error.json').exists():
                    immutable(folder/'postlaunch_monitor_error.json', errors[-1])
            except OSError:
                pass
            try:
                time.sleep(1)
            except BaseException:
                pass


def runtime(args):
    require(os.name == 'nt', 'Windows only')
    require(Path(sys.executable).resolve() == PYTHON.resolve(), 'Use original baseline interpreter')
    manifest_path = HERE/'SOURCE_MANIFEST.json'
    release_info = release_gate(args.release, args.release_sha256, manifest_path,
                                args.root_adoption, args.root_adoption_sha256)
    manifest = read(manifest_path)
    for item in manifest['candidate_files']:
        verify_binding(item)
    contract = read(HERE/'RECOVERY_CONTRACT.json')
    contract_binding = binding(HERE/'RECOVERY_CONTRACT.json')
    for item in contract['input_bindings']:
        verify_binding(item)
    spec = read(contract['recovery_spec']['path'])
    original = read(HERE/'captured_pipeline_status.json')
    seed_bytes = (HERE/'pipeline_seed.json').read_bytes()
    seed = json.loads(seed_bytes)
    validate_seed(seed, original, spec, contract['incident_capture'])
    state_bindings = contract['live_state_bindings']
    original_binding = next(b for b in state_bindings if Path(b['path']).name == 'pipeline_status.json')
    primary = read(EX/'status.json')
    require(primary.get('status') == 'completed', 'Primary not completed')
    require(primary.get('controller_pid') == contract['primary_controller_pid'], 'Primary identity changed')
    output = ROOT/'lgm_game_pytorch/analysis/transactions_t6_formal'
    folder = HERE/'runtime_attempt'
    assert_unused(folder)
    locks = []
    supervisor = None
    child = None
    streams = []
    tracked = {}
    anchor = None
    native = None
    admission = []
    allowed_python_paths = {os.path.normcase(os.path.abspath(p)) for p in
                            (str(PYTHON), sys.executable, sys._base_executable)}
    def readonly_gate():
        require(binding(manifest_path) == release_info[1], 'Candidate manifest changed during admission')
        for item in manifest['candidate_files']:
            verify_binding(item)
        verify_binding(contract_binding)
        require((HERE/'pipeline_seed.json').read_bytes() == seed_bytes, 'Seed bytes changed during admission')
        release_gate(args.release, args.release_sha256, manifest_path,
                     args.root_adoption, args.root_adoption_sha256)
        state_cas(state_bindings)
        for item in contract['input_bindings']:
            verify_binding(item)
        require(not output.exists(), 'T6 output newly exists; capture/review another attempt')
        for log in contract['append_log_prefixes']:
            row = prefix_gate(log['path'], log)
            require(row['new_bytes'] == 0, 'Old stage log already appended before this attempt')
        snapshot = process_snapshot()
        require(snapshot['host_boot_utc_ticks'] == contract['host_boot_utc_ticks'],
                'Host restarted after captured incident; a new incident review is required')
        processes_gate(snapshot, primary['controller_pid'], own_python_ids(snapshot))
        return {'utc': utc(), 'process_snapshot': snapshot, 'gpu': fresh_gpu(), 'commit': fresh_memory()}
    try:
        # Persistent files must already exist: no silent creation before admission.
        for name in ('latest_baseline_gpu.lock', 'matrix.lock', 'extension_supervisor.lock',
                     'latest_baseline_supervisor.lock', 'independent_comparison_supervisor.lock',
                     'supervisor.lock'):
            lock = ByteLock(EX/name)
            locks.append(lock)
            if name == 'supervisor.lock':
                supervisor = lock
        for index in range(3):
            admission.append(readonly_gate())
            if index < 2:
                time.sleep(15)
        # ORIGINAL real imports in short-lived child, applying its allowed env
        # changes to THIS exact Popen parent including TORCHINDUCTOR_CACHE_DIR.
        native_module = load_native_module(EX/'continue_formal_matrix.py')
        native = native_module.verify_training_environment_isolated()
        require(not native_module.scientific_modules(), 'Probe leaked scientific imports')
        after_native = process_snapshot()
        for pid in (native['isolation']['launcher_pid'], native['isolation']['interpreter_pid']):
            require(not any(p['pid'] == pid for p in after_native['processes']),
                    'Native probe numeric PID still occupied; inspect exact reuse before another release')
        admission.append(readonly_gate())
        release_gate(args.release, args.release_sha256, manifest_path,
                     args.root_adoption, args.root_adoption_sha256)
        payload = {'schema': 't6-pipeline-once-intent.v1', 'created_utc': utc(),
                   'release': release_info[0], 'source_manifest': release_info[1], 'root_adoption': release_info[2],
                   'native_environment': native, 'admission': admission,
                   'seed': binding(HERE/'pipeline_seed.json'), 'original_state': original_binding,
                   'append_log_start_offsets': contract['append_log_prefixes'],
                   'guardian_pid': os.getpid(), 'scope': 'pipeline_only_original_stage7'}
        # The final gate rechecks all CAS/source/GPU/process/resource checks before
        # any attempt directory/intent/retirement/seed mutation.
        publish_once(folder, EX/'pipeline_status.json', original_binding,
                     seed_bytes, payload, readonly_gate)
        command = [str(PYTHON), '-B', str(EX/'run_controller_with_state_retry_v2.py'),
                   '--role', 'pipeline', '--io-manifest-sha256', IO_SHA]
        streams = [(folder/'pipeline.stdout.log').open('x', encoding='utf-8'),
                   (folder/'pipeline.stderr.log').open('x', encoding='utf-8')]
        # Unavoidable cooperative-lock transfer gap: original supervisor must
        # acquire this byte itself. Shared/matrix/successor locks remain held.
        # Any race/failed acquire leaves this one-use intent and seed for a NEW
        # incident; never relaunch or rewrite the primary to bypass its guard.
        supervisor.close()
        child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                 stdout=streams[0], stderr=streams[1],
                                 creationflags=subprocess.CREATE_NO_WINDOW)
        anchor = launcher_anchor(child)
        tracked[(child.pid, int(anchor['api_creation_utc_ticks'])//10)] = anchor
        observed = observe_until_exit(child, tracked, folder, command, anchor, allowed_python_paths)
        for stream in streams:
            stream.close()
        streams.clear()
        observed['closed_controller_logs'] = [binding(folder/'pipeline.stdout.log'), binding(folder/'pipeline.stderr.log')]
        observed['append_log_ranges'] = [prefix_gate(log['path'], log) for log in contract['append_log_prefixes']]
        observed['launch_record'] = validate_launch_record(folder, child.pid, anchor['api_creation_utc_ticks'], command)
        immutable(folder/'observed_exit.json', observed)
        require(observed['actual_owner_observed'] and child.returncode == 0 and
                observed['final_runtime_status'] == 'ready_for_extension_preparation',
                'Controller not established successful; retained attempt requires review')
        validate_final_state(read(EX/'pipeline_status.json'), original)
    except BaseException as error:
        if folder.exists():
            try:
                immutable(folder/'failure_after_intent.json', {'utc': utc(), 'error': repr(error),
                          'child_started': child is not None, 'no_rollback_or_replay': True})
            except OSError:
                pass
        # Postlaunch failures must not drop the shared lock while known or
        # potentially missed descendants live. No termination/kill is used.
        if child is not None:
            # Failure to capture the initial handle is itself a retained failure;
            # the exact Popen handle still anchors any later monitoring retry.
            while anchor is None:
                try:
                    anchor = launcher_anchor(child)
                    tracked[(child.pid, int(anchor['api_creation_utc_ticks'])//10)] = anchor
                except BaseException:
                    try:
                        time.sleep(1)
                    except BaseException:
                        pass
            observe_until_exit(child, tracked, folder,
                               [str(PYTHON), '-B', str(EX/'run_controller_with_state_retry_v2.py'),
                                '--role', 'pipeline', '--io-manifest-sha256', IO_SHA], anchor, allowed_python_paths)
        raise
    finally:
        for stream in streams:
            stream.close()
        for entry in tracked.values():
            ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(entry['handle']))
        for lock in reversed(locks):
            lock.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', required=True, type=Path)
    parser.add_argument('--release-sha256', required=True)
    parser.add_argument('--root-adoption', required=True, type=Path)
    parser.add_argument('--root-adoption-sha256', required=True)
    runtime(parser.parse_args())


if __name__ == '__main__':
    main()
