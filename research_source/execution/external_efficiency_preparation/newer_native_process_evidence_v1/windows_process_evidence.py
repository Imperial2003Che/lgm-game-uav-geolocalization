"""Source-only candidate: read/synchronize Windows process evidence, no spawn.

No imports of scientific packages and no execution/admission authority. Windows
API objects are created only when WinAPI() is explicitly instantiated. Failure
to query any required field is fatal; no reduced-evidence fallback is provided.
"""
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import os
from pathlib import Path
import time

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
SYNCHRONIZE = 0x00100000
EVIDENCE_ACCESS = PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE
WAIT_OBJECT_0, WAIT_TIMEOUT, WAIT_FAILED = 0, 258, 0xFFFFFFFF
MAX_COMMAND_BYTES = 1024 * 1024
FILETIME_TO_DOTNET_TICKS = 504911232000000000


class EvidenceError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def create_json(path, value):
    """CreateNew; retain a partial file if writing fails. Never overwrite."""
    with Path(path).open('xb') as f:
        f.write(canonical(value) + b'\n')
        f.flush()
        os.fsync(f.fileno())


class Ledger:
    def __init__(self, directory, actor):
        self.directory = Path(directory)
        self.actor = actor
        self.index = 0

    def emit(self, event, **data):
        self.index += 1
        create_json(self.directory / f'{self.actor}_{self.index:04d}_{event}.json',
                    {'event': event, 'actor': self.actor, 'pid': os.getpid(),
                     'utc_ns': time.time_ns(), **data})


class FILETIME(C.Structure):
    _fields_ = [('low', W.DWORD), ('high', W.DWORD)]


class UNICODE_STRING(C.Structure):
    _fields_ = [('Length', W.USHORT), ('MaximumLength', W.USHORT), ('Buffer', C.c_void_p)]


class PROCESSENTRY32W(C.Structure):
    _fields_ = [('dwSize', W.DWORD), ('cntUsage', W.DWORD),
                ('th32ProcessID', W.DWORD), ('th32DefaultHeapID', C.c_size_t),
                ('th32ModuleID', W.DWORD), ('cntThreads', W.DWORD),
                ('th32ParentProcessID', W.DWORD), ('pcPriClassBase', W.LONG),
                ('dwFlags', W.DWORD), ('szExeFile', W.WCHAR * 260)]


def ticks(ft):
    return (int(ft.high) << 32) | int(ft.low)


class WinAPI:
    def __init__(self):
        require(os.name == 'nt', 'This candidate supports Windows only')
        self.k = C.WinDLL('kernel32', use_last_error=True)
        self.n = C.WinDLL('ntdll', use_last_error=True)
        declarations = {
            'OpenProcess': ([W.DWORD, W.BOOL, W.DWORD], W.HANDLE),
            'CloseHandle': ([W.HANDLE], W.BOOL),
            'GetProcessId': ([W.HANDLE], W.DWORD),
            'GetProcessTimes': ([W.HANDLE] + [C.POINTER(FILETIME)] * 4, W.BOOL),
            'QueryFullProcessImageNameW': ([W.HANDLE, W.DWORD, W.LPWSTR, C.POINTER(W.DWORD)], W.BOOL),
            'WaitForSingleObject': ([W.HANDLE, W.DWORD], W.DWORD),
            'GetExitCodeProcess': ([W.HANDLE, C.POINTER(W.DWORD)], W.BOOL),
            'CreateToolhelp32Snapshot': ([W.DWORD, W.DWORD], W.HANDLE),
            'Process32FirstW': ([W.HANDLE, C.POINTER(PROCESSENTRY32W)], W.BOOL),
            'Process32NextW': ([W.HANDLE, C.POINTER(PROCESSENTRY32W)], W.BOOL),
            'CreateFileW': ([W.LPCWSTR, W.DWORD, W.DWORD, C.c_void_p, W.DWORD, W.DWORD, W.HANDLE], W.HANDLE),
        }
        for name, (args, result) in declarations.items():
            fn = getattr(self.k, name)
            fn.argtypes, fn.restype = args, result
        self.n.NtQueryInformationProcess.argtypes = [W.HANDLE, W.ULONG, C.c_void_p, W.ULONG, C.POINTER(W.ULONG)]
        self.n.NtQueryInformationProcess.restype = W.LONG

    def error(self, operation):
        return EvidenceError(f'{operation}: WinError {C.get_last_error()}')

    def close(self, handle):
        if not self.k.CloseHandle(handle):
            raise self.error('CloseHandle')

    def kernel_identity(self, handle):
        creation, exit_time, kernel, user = (FILETIME() for _ in range(4))
        if not self.k.GetProcessTimes(handle, C.byref(creation), C.byref(exit_time), C.byref(kernel), C.byref(user)):
            raise self.error('GetProcessTimes')
        size = W.DWORD(32768)
        image = C.create_unicode_buffer(size.value)
        if not self.k.QueryFullProcessImageNameW(handle, 0, image, C.byref(size)):
            raise self.error('QueryFullProcessImageNameW')
        require(0 < size.value < len(image) and bool(image.value), 'Invalid or empty kernel image path')
        pid = int(self.k.GetProcessId(handle))
        require(pid > 0 and ticks(creation) > 0, 'Missing kernel process identity')
        raw_creation = ticks(creation)
        return {'pid': pid, 'creation_filetime_100ns': raw_creation,
                'creation_utc_ticks': raw_creation + FILETIME_TO_DOTNET_TICKS, 'image': image.value}

    def signaled_exit_times(self, handle):
        """Call only after WAIT_OBJECT_0; running-process exit time is undefined."""
        creation, exit_time, kernel, user = (FILETIME() for _ in range(4))
        if not self.k.GetProcessTimes(handle, C.byref(creation), C.byref(exit_time), C.byref(kernel), C.byref(user)):
            raise self.error('GetProcessTimes after signaled wait')
        value = ticks(exit_time)
        require(value > 0, 'Signaled process lacks an exit FILETIME')
        return {'exit_filetime_100ns': value, 'exit_utc_ticks': value + FILETIME_TO_DOTNET_TICKS}

    def command_line(self, handle, ledger, label):
        needed = W.ULONG()
        status = int(self.n.NtQueryInformationProcess(handle, 60, None, 0, C.byref(needed))) & 0xFFFFFFFF
        ledger.emit('nt_command_size', label=label, status=status, required_bytes=int(needed.value))
        require(status in (0xC0000004, 0xC0000023, 0x80000005), 'Unexpected Nt class60 size status')
        require(C.sizeof(UNICODE_STRING) <= needed.value <= MAX_COMMAND_BYTES, 'Unbounded/short Nt command buffer')
        capacity = int(needed.value)
        buf = C.create_string_buffer(capacity)
        returned = W.ULONG()
        status = int(self.n.NtQueryInformationProcess(handle, 60, buf, capacity, C.byref(returned))) & 0xFFFFFFFF
        ledger.emit('nt_command_result', label=label, status=status, returned_bytes=int(returned.value), capacity=capacity)
        require(status == 0, 'Nt class60 command query unsupported or failed')
        require(C.sizeof(UNICODE_STRING) <= returned.value <= capacity, 'Invalid returned Nt buffer length')
        u = UNICODE_STRING.from_buffer(buf)
        base = C.addressof(buf)
        address = int(u.Buffer or 0)
        require(address % 2 == 0, 'Unaligned UTF16 command pointer')
        require(u.Length % 2 == 0 and u.MaximumLength % 2 == 0, 'Odd UTF16 length')
        require(0 < u.Length <= u.MaximumLength, 'Empty or inconsistent command line')
        require(base + C.sizeof(UNICODE_STRING) <= address and
                address + u.MaximumLength <= base + returned.value,
                'Nt command pointer/length outside returned buffer')
        value = C.wstring_at(address, u.Length // 2)
        require('\x00' not in value, 'Embedded NUL in command line')
        return value

    def parent_row(self, pid):
        h = self.k.CreateToolhelp32Snapshot(0x2, 0)
        require(h not in (None, C.c_void_p(-1).value), 'Toolhelp snapshot failed')
        try:
            row = PROCESSENTRY32W()
            row.dwSize = C.sizeof(row)
            ok = self.k.Process32FirstW(h, C.byref(row))
            while ok:
                if int(row.th32ProcessID) == pid:
                    return {'pid': pid, 'parent_pid': int(row.th32ParentProcessID), 'toolhelp_name': row.szExeFile}
                ok = self.k.Process32NextW(h, C.byref(row))
            raise EvidenceError('PID missing from current Toolhelp snapshot')
        finally:
            self.close(h)


class HeldProcess:
    """Independent evidence handle; only limited-query and synchronize rights."""
    def __init__(self, api, pid, ledger, label):
        self.api, self.ledger, self.label = api, ledger, label
        self.handle = api.k.OpenProcess(EVIDENCE_ACCESS, False, int(pid))
        self.identity = None
        self.exit_observation = None
        if not self.handle:
            raise api.error('OpenProcess limited evidence')
        try:
            self.identity = api.kernel_identity(self.handle)
            ledger.emit('held_open', label=label, identity=self.identity, access_mask=EVIDENCE_ACCESS,
                        authority='unconfirmed candidate; no ownership or execution grant')
        except BaseException:
            api.close(self.handle)
            self.handle = None
            raise

    def snapshot(self):
        require(self.handle is not None, 'Closed evidence handle')
        held_now = self.api.kernel_identity(self.handle)
        fresh = self.api.k.OpenProcess(EVIDENCE_ACCESS, False, self.identity['pid'])
        if not fresh:
            raise self.api.error('OpenProcess fresh PID comparison')
        try:
            before = self.api.kernel_identity(fresh)
            parent = self.api.parent_row(self.identity['pid'])
            cmd = self.api.command_line(fresh, self.ledger, self.label)
            after = self.api.kernel_identity(fresh)
            value = {**before, **parent, 'command_line': cmd, 'fresh_after': after, 'held_now': held_now}
            self.ledger.emit('candidate_snapshot', label=self.label, value=value)
            require(before == after == held_now == self.identity, 'PID reuse or kernel identity changed')
            return value
        finally:
            self.api.close(fresh)

    def confirm_twice(self, expected_command, expected_image, parent, interval_seconds=0.25):
        require(type(interval_seconds) in (int, float) and 0 < interval_seconds <= 1, 'Bounded confirmation interval required')
        values = []
        for index in range(2):
            p = parent.snapshot()
            s = self.snapshot()
            self.ledger.emit('confirmation_gate', label=self.label, index=index,
                             expected_command=expected_command, expected_image=str(expected_image),
                             expected_parent=parent.identity, observed=s)
            require(s['parent_pid'] == p['pid'] == parent.identity['pid'], 'Current parent PID differs')
            require(p['creation_utc_ticks'] == parent.identity['creation_utc_ticks'], 'Current parent creation differs')
            require(s['creation_utc_ticks'] >= p['creation_utc_ticks'], 'Child predates parent')
            require(s['command_line'] == expected_command, 'Complete command line differs')
            require(os.path.samefile(s['image'], expected_image), 'Executable is not the exact expected file')
            require(s['pid'] != p['pid'], 'Child/parent identity collision')
            values.append(s)
            if index == 0:
                time.sleep(interval_seconds)
        require(values[0] == values[1], 'Two complete observations differ')
        self.ledger.emit('confirmed', label=self.label, observations=values,
                         parentage_scope='two current Toolhelp observations with both held creation identities; not complete historical ancestry')
        return values

    def wait(self, milliseconds):
        require(type(milliseconds) is int and 0 <= milliseconds <= 60000, 'Bounded integer wait required')
        require(self.handle is not None, 'Cannot wait closed handle')
        result = int(self.api.k.WaitForSingleObject(self.handle, milliseconds))
        self.ledger.emit('wait_result', label=self.label, result=result, milliseconds=milliseconds)
        if result == WAIT_TIMEOUT:
            return None
        require(result != WAIT_FAILED, 'WaitForSingleObject failed')
        require(result == WAIT_OBJECT_0, 'Unexpected wait result')
        code = W.DWORD()
        if not self.api.k.GetExitCodeProcess(self.handle, C.byref(code)):
            raise self.api.error('GetExitCodeProcess after signaled wait')
        now = self.api.kernel_identity(self.handle)
        require(now == self.identity, 'Signaled held identity changed')
        self.exit_observation = {'identity': self.identity, 'wait_result': result,
                                 'exit_code_unsigned_dword': int(code.value), 'observed_utc_ns': time.time_ns(),
                                 **self.api.signaled_exit_times(self.handle),
                                 'exit259_is_valid_after_signaled_wait': True}
        self.ledger.emit('exit_observed', label=self.label, value=self.exit_observation)
        return self.exit_observation

    def close(self):
        if self.handle is not None:
            handle, self.handle = self.handle, None
            self.api.close(handle)
            self.ledger.emit('held_closed', label=self.label, exit_observed=self.exit_observation is not None,
                             process_not_terminated=True)


def seal_closed_log(api, path, exited_processes, own_streams):
    """Hash only after actual held exits and own stream closure; deny other writers."""
    require(exited_processes and all(p.exit_observation is not None for p in exited_processes),
            'All designated actual held exits required before log seal')
    require(all(f.closed for f in own_streams), 'Controller redirect streams still open')
    # GENERIC_READ, FILE_SHARE_READ only: existing/new write/delete handles excluded.
    h = api.k.CreateFileW(str(Path(path).resolve(strict=True)), 0x80000000, 0x1,
                         None, 3, 0x08000000, None)
    require(h not in (None, C.c_void_p(-1).value), 'Log is unavailable or an incompatible writer remains')
    import msvcrt
    try:
        fd = msvcrt.open_osfhandle(int(h), os.O_RDONLY | os.O_BINARY)
    except BaseException:
        api.close(h)
        raise
    try:
        stream = os.fdopen(fd, 'rb')
    except BaseException:
        os.close(fd)
        raise
    with stream as f:
        before = os.fstat(f.fileno())
        sha = hashlib.file_digest(f, 'sha256').hexdigest()
        after = os.fstat(f.fileno())
        require((before.st_size, before.st_mtime_ns, before.st_ino) ==
                (after.st_size, after.st_mtime_ns, after.st_ino), 'Log metadata changed while read-locked')
    return {'path': str(Path(path).resolve()), 'bytes': after.st_size, 'sha256': sha,
            'read_lock_denied_write_delete': True, 'controller_streams_closed': True,
            'designated_process_exit_scope':'All designated held processes exited; their OS handles closed on exit. This is not global malicious-writer exclusion history.'}


if __name__ == '__main__':
    raise SystemExit('Helper is not an execution entry or scientific admission authority')
