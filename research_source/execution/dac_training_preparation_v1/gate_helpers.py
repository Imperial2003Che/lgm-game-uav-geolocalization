"""Exact existing Windows identity/shared-lock helpers; no process probe at import."""
from contextlib import contextmanager
import ctypes
from datetime import datetime
import os
from common_runtime import HERE
EXECUTION=HERE.parent

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
