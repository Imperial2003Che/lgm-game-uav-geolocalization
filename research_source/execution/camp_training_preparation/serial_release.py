"""Fresh serial release checks; never load torch or register/alter a queue."""
from contextlib import contextmanager
import ctypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
from camp_train_runtime import HERE, sha_file

EXECUTION = HERE.parent
PIPELINE_IDS = ['formal_aggregate','formal_figures','cross_dataset_transfer','robustness',
                'robustness_aggregate','query_analysis','formal_efficiency_component']
EXTENSION_IDS = ['real_model_visualizations','heldout_height_training','heldout_and_seen_height_evaluation',
                 't1_v3_native_resource_profile_then_7fits_70eval']

def alive(pid, started=None):
    """Check owner identity, including creation time so a reused PID is not mistaken."""
    if not pid:
        return False
    if os.name != 'nt':
        raise RuntimeError('This release verifier is registered for the current Windows host')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.restype = ctypes.c_void_p
    handle = kernel.OpenProcess(0x1000, False, int(pid))
    if not handle:
        error = ctypes.get_last_error()
        if error == 5:
            raise RuntimeError('Cannot verify preceding owner process: access denied')
        if error not in (0, 87):
            raise RuntimeError(f'Cannot verify preceding owner process: Win32 error {error}')
        return False
    try:
        code = ctypes.c_ulong()
        if not kernel.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(code)):
            raise RuntimeError('Cannot query preceding process exit')
        if code.value != 259:
            return False
        if started:
            class FT(ctypes.Structure):
                _fields_ = [('low',ctypes.c_uint32),('high',ctypes.c_uint32)]
            a,b,c,d = FT(),FT(),FT(),FT()
            if not kernel.GetProcessTimes(ctypes.c_void_p(handle),ctypes.byref(a),ctypes.byref(b),ctypes.byref(c),ctypes.byref(d)):
                raise RuntimeError('Cannot verify process creation identity')
            created = ((a.high << 32) | a.low) / 10000000 - 11644473600
            if abs(created - datetime.fromisoformat(started).timestamp()) > 15:
                return False
        return True
    finally:
        kernel.CloseHandle(ctypes.c_void_p(handle))

def owners(value):
    """Collect all recorded owner/child PIDs, including nested primary fit commands."""
    if isinstance(value, dict):
        for key, item in value.items():
            if (key == 'pid' or key.endswith('_pid')) and isinstance(item, int) and item > 0:
                started = value.get('supervisor_started_utc') if key == 'supervisor_pid' else value.get('started_utc')
                yield item, started
            elif isinstance(item, (dict,list)):
                yield from owners(item)
    elif isinstance(value,list):
        for item in value:
            yield from owners(item)

def serial_release_gate(plan_path, release_path):
    if release_path is None:
        raise RuntimeError('A later explicit serial release bound to this training plan is required')
    release_path = Path(release_path)
    release = json.loads(release_path.read_text(encoding='utf-8'))
    if release.get('schema') != 'camp-university-training-release.v1' or release.get('allow_cuda') is not True:
        raise RuntimeError('This is not an active CAMP training serial release')
    if release.get('training_plan_sha256') != sha_file(plan_path):
        raise RuntimeError('Serial release is not bound to this exact training plan')
    extension_plan = EXECUTION / 'extension_plan.json'
    if release.get('preceding_extension_plan_sha256') != sha_file(extension_plan):
        raise RuntimeError('Serial release binds a different preceding extension plan')
    states = {name: json.loads((EXECUTION / name).read_text(encoding='utf-8'))
              for name in ('status.json','pipeline_status.json','extension_status.json')}
    if states['status.json'].get('status') != 'completed':
        raise RuntimeError('Primary matrix has not completed')
    for name, final_status, ids in (
        ('pipeline_status.json','ready_for_extension_preparation',PIPELINE_IDS),
        ('extension_status.json','registered_extensions_finished_review_pending',EXTENSION_IDS)):
        state = states[name]
        if state.get('status') != final_status or [j.get('id') for j in state.get('jobs',[])] != ids:
            raise RuntimeError('Preceding queue has not completed: ' + name)
        if any(j.get('status') != 'completed' or j.get('exit_code') != 0 for j in state['jobs']):
            raise RuntimeError('A preceding job is incomplete or failed: ' + name)
    if states['extension_status.json'].get('plan_sha256') != release['preceding_extension_plan_sha256']:
        raise RuntimeError('Completed extension status does not match the bound plan')
    checked = []
    for pid, started in set(pair for state in states.values() for pair in owners(state)):
        if alive(pid, started):
            raise RuntimeError(f'Preceding owner/child process is still running: PID {pid}')
        checked.append({'pid':pid,'recorded_started_utc':started,'original_owner_alive':False})
    result = subprocess.run(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader,nounits'],
        capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30,check=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if any('python' in line.lower() for line in lines):
        raise RuntimeError('Another Python GPU compute process is active')
    return {'verified_utc':datetime.now(timezone.utc).isoformat(),
            'release_sha256':sha_file(release_path),'training_plan_sha256':sha_file(plan_path),
            'preceding_status_sha256':{name:sha_file(EXECUTION/name) for name in states},
            'preceding_extension_plan_sha256':sha_file(extension_plan),
            'owners':checked,'nvidia_compute_rows':lines,'other_python_compute_processes':False}

@contextmanager
def exclusive_latest_baseline_lock():
    """Runtime shared lock for later baseline jobs; acquiring it is not scheduling."""
    if os.name != 'nt':
        raise RuntimeError('Windows baseline lock required')
    import msvcrt
    path = EXECUTION / 'latest_baseline_gpu.lock'
    with open(path, 'a+b') as stream:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            raise RuntimeError('Another latest-baseline job holds the serial GPU lock') from error
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
