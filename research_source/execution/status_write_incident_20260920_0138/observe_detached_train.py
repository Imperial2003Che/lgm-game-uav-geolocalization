"""Retain real Windows handles for the already-running training process pair.

Read-only toward experiment files. Does not resume, train, kill, or mark science complete.
"""
from pathlib import Path
import ctypes
from ctypes import wintypes
import datetime
import hashlib
import json
import os
import sys
import time

HERE = Path(__file__).resolve().parent
CAPTURE_SHA = '48b8688111e0ca5dfeab86b4e1815d86fcff9a1d7fdd75ee2726d0cb455fa956'
RUN = Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\runs\formal_main\university1652\visual_style\seed_2')

def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()
def exclusive(name, value):
    payload=json.dumps(value,ensure_ascii=False,indent=2)
    for attempt in range(10):
        try:
            with (HERE/name).open('x',encoding='utf-8') as stream:
                stream.write(payload); stream.flush(); os.fsync(stream.fileno())
            return
        except PermissionError:
            if attempt == 9: raise
            time.sleep(1)

def main():
    path=HERE/'CAPTURE.json'
    if sha(path)!=CAPTURE_SHA: raise RuntimeError('Capture changed')
    capture=json.loads(path.read_bytes())
    if {r['ProcessId'] for r in capture['processes']}!={7176,29512}: raise RuntimeError('Unexpected process pair')
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.GetProcessTimes.argtypes=[wintypes.HANDLE,*([ctypes.POINTER(wintypes.FILETIME)]*4)];kernel.GetProcessTimes.restype=wintypes.BOOL
    kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];kernel.WaitForSingleObject.restype=wintypes.DWORD
    kernel.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)];kernel.GetExitCodeProcess.restype=wintypes.BOOL
    kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle.restype=wintypes.BOOL
    handles={}; identities=[]; exits={}
    try:
        for row in capture['processes']:
            pid=row['ProcessId']
            if 'run_formal_worker.py' not in row['CommandLine'] or '--seed 2' not in row['CommandLine']:
                raise RuntimeError('Captured command does not identify intended run')
            handle=kernel.OpenProcess(0x00100000|0x1000,False,pid)
            if not handle: raise ctypes.WinError(ctypes.get_last_error())
            handles[pid]=handle
            created,ended,kernel_time,user_time=[wintypes.FILETIME() for _ in range(4)]
            if not kernel.GetProcessTimes(handle,ctypes.byref(created),ctypes.byref(ended),ctypes.byref(kernel_time),ctypes.byref(user_time)):
                raise ctypes.WinError(ctypes.get_last_error())
            ticks=(created.dwHighDateTime<<32)|created.dwLowDateTime
            seconds=(ticks-116444736000000000)/10000000
            expected=datetime.datetime.fromisoformat(row['CreationDate']).timestamp()
            if abs(seconds-expected)>.001: raise RuntimeError('PID creation mismatch')
            if kernel.WaitForSingleObject(handle,0)!=258: raise RuntimeError('Expected live process at handle capture')
            identities.append({**row,'creation_filetime':ticks,'real_handle_acquired_utc':utc()})
        exclusive('OBSERVER_STARTED.json',{'pid':os.getpid(),'started_utc':utc(),'source_sha256':sha(__file__),
                  'capture_sha256':CAPTURE_SHA,'processes':identities,'science_completion':False})
        with (HERE/'observer_events.jsonl').open('x',encoding='utf-8') as stream:
            while len(exits)!=len(handles):
                for pid,handle in handles.items():
                    if pid in exits: continue
                    result=kernel.WaitForSingleObject(handle,0)
                    if result==0:
                        code=wintypes.DWORD()
                        if not kernel.GetExitCodeProcess(handle,ctypes.byref(code)): raise ctypes.WinError(ctypes.get_last_error())
                        exits[pid]={'exit_code':code.value,'observed_utc':utc()}
                    elif result!=258: raise RuntimeError('WaitForSingleObject failed: '+str(result))
                manifest=json.loads((RUN/'run_manifest.json').read_bytes())
                stream.write(json.dumps({'time':utc(),'exits':exits,'run_status':manifest.get('status'),
                    'last_completed_epoch':manifest.get('last_completed_epoch'),'history_rows':manifest.get('history_rows')})+'\n')
                stream.flush()
                if len(exits)!=len(handles): time.sleep(30)
        artifacts={}
        for name in ('run_manifest.json','run_config.json','history.json','run.log','process_stdout.log','process_stderr.log'):
            item=RUN/name
            artifacts[name]={'path':str(item),'bytes':item.stat().st_size,'sha256':sha(item)}
        exclusive('OBSERVED_EXIT.json',{'observed_utc':utc(),'pid':os.getpid(),'processes':identities,
                  'actual_exits':exits,'both_exited_zero':all(v['exit_code']==0 for v in exits.values()),
                  'run_files_after_exit':artifacts,'scientific_completion_not_yet_validated':True})
    finally:
        for handle in handles.values(): kernel.CloseHandle(handle)

if __name__=='__main__': main()
