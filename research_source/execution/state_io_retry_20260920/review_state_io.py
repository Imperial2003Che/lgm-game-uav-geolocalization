"""Standard-library tests, including an actual Windows deny-delete reader."""
from pathlib import Path
import ctypes
from ctypes import wintypes
import hashlib
import importlib.util
import json
import os
import sys
import threading
import time
from resilient_state import wrap
HERE=Path(__file__).resolve().parent
EXPECTED='3519d4b5ddcc6252fb6e1d2ed164d7eda0f4ef6ec8f8b7baa87c60382dacdc4f'

def main():
    target=HERE.parent/'run_controller_with_state_retry.py'
    spec=importlib.util.spec_from_file_location('retry_controller_test',target)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    checks=[]
    def check(name,condition):
        if not condition: raise AssertionError(name)
        checks.append(name)
    loaded={role:module.load(role,EXPECTED) for role in module.TARGETS}
    for role,controller in loaded.items():
        if role=='extensions': controller=controller.load_controller('b985182c80577fa1a98a7511ce5de2a6a360f908ab063d6f6a0e5a2395be3640')
        check(role+'_writer_wrapped',hasattr(controller.save,'__wrapped__'))
    case=HERE/'actual_windows_reader_test';case.mkdir()
    path=case/'status.json';path.write_text('{"old":true}',encoding='utf-8')
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    k.CreateFileW.restype=wintypes.HANDLE
    k.CloseHandle.argtypes=[wintypes.HANDLE];k.CloseHandle.restype=wintypes.BOOL
    handle=k.CreateFileW(str(path),0x80000000,1|2,None,3,0,None)
    if handle in (None,ctypes.c_void_p(-1).value): raise ctypes.WinError(ctypes.get_last_error())
    locked=threading.Event();finished=threading.Event();outcomes=[]
    def original_writer(p,value):
        temp=p.with_suffix('.tmp')
        temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
        try: os.replace(temp,p)
        except PermissionError as error:
            outcomes.append(error.winerror);locked.set();raise
    writer=wrap(original_writer,diagnostic_path=case/'events.jsonl',provenance={'test':True})
    result=[]
    def publish():
        try:writer(path,{'new':42});result.append('returned')
        except BaseException as error:result.append(repr(error))
        finally:finished.set()
    thread=threading.Thread(target=publish);thread.start()
    try:
        check('real_sharing_denial_observed',locked.wait(5))
        check('publisher_waits_while_denied',not finished.is_set())
        check('old_json_stays_valid_during_denial',json.loads(path.read_bytes())=={'old':True})
    finally:k.CloseHandle(handle)
    thread.join(10)
    check('real_writer_returns_after_reader_release',not thread.is_alive() and result==['returned'])
    expected={'new':42,'state_io_compatibility':{'test':True}}
    check('exact_original_serialization_preserved',path.read_text(encoding='utf-8')==json.dumps(expected,ensure_ascii=False,indent=2))
    log=[json.loads(line) for line in (case/'events.jsonl').read_text(encoding='utf-8').splitlines()]
    check('actual_denial_and_recovery_audited',[x['event'] for x in log]==['state_publication_waiting','state_publication_recovered'])
    for label,error in [('plain_permission',PermissionError('synthetic_non_windows')),('other_io',OSError('synthetic_disk_error'))]:
        def raising(*args): raise error
        wrapped=wrap(raising,diagnostic_path=case/'not_used.jsonl',provenance={})
        try:wrapped(path,{})
        except type(error) as caught:check(label+'_propagates',caught is error)
        else:raise AssertionError('Unexpected suppression')
    for winerror in (5,32,33):
        calls=[];sleeps=[]
        def sometimes(p,v):
            calls.append(1)
            if len(calls)<9:
                error=PermissionError('injected control error');error.winerror=winerror;raise error
            return 'published'
        actual=wrap(sometimes,diagnostic_path=case/('mock_'+str(winerror)+'.jsonl'),provenance={},sleeper=sleeps.append)(path,{})
        check('mock_'+str(winerror)+'_blocks_until_success',actual=='published' and len(calls)==9 and len(sleeps)==8 and max(sleeps)<=5)
    check('no_scientific_imports',not any(n.split('.')[0] in ('torch','numpy','PIL','matplotlib') for n in sys.modules))
    report={'status':'passed','scope':'Root standard-library and actual Windows sharing test; no science or live controller start',
            'manifest_sha256':EXPECTED,'checks':checks,'count':len(checks),'actual_winerrors':outcomes,
            'actual_denial_then_release':True,'synthetic_errors_are_control_tests_only':True,
            'controller_sources_unchanged':True,'live_training_not_touched':True}
    path=HERE/'ROOT_IO_REVIEW.json'
    with path.open('x',encoding='utf-8') as stream:json.dump(report,stream,ensure_ascii=False,indent=2)
    print(json.dumps({'report':str(path),'count':len(checks),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()},ensure_ascii=False))

if __name__=='__main__':main()
