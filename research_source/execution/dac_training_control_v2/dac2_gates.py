"""Fresh serial ownership checks; all process/GPU calls are explicit, never at import."""
from contextlib import contextmanager
import csv
import ctypes
from datetime import datetime, timezone
import io
import os
from pathlib import Path
import subprocess
from dac2_contracts import EXECUTION, Bound, number, require, sha, strict_json, utc

def process_started(pid):
    require(os.name=='nt','This execution is pinned to the current Windows host')
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.c_uint32]
    kernel.OpenProcess.restype=ctypes.c_void_p
    handle=kernel.OpenProcess(0x1000,False,int(pid))
    if not handle:
        error=ctypes.get_last_error()
        require(error in (0,87),'Cannot verify process identity: Win32 error '+str(error))
        return None
    try:
        code=ctypes.c_ulong()
        require(kernel.GetExitCodeProcess(ctypes.c_void_p(handle),ctypes.byref(code)),'GetExitCodeProcess failed')
        if code.value!=259: return None
        class FT(ctypes.Structure): _fields_=[('low',ctypes.c_uint32),('high',ctypes.c_uint32)]
        created,exited,kernel_time,user=FT(),FT(),FT(),FT()
        require(kernel.GetProcessTimes(ctypes.c_void_p(handle),ctypes.byref(created),ctypes.byref(exited),ctypes.byref(kernel_time),ctypes.byref(user)),'GetProcessTimes failed')
        seconds=((created.high<<32)|created.low)/10000000-11644473600
        return datetime.fromtimestamp(seconds,timezone.utc).isoformat()
    finally: kernel.CloseHandle(ctypes.c_void_p(handle))

class ProcessObservation:
    """Retain a real process handle so its actual exit code survives termination."""
    def __init__(self,pid,existing_handle=None):
        require(os.name=='nt','Windows actual-process observation required')
        self.pid=int(pid);self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.kernel.OpenProcess.restype=ctypes.c_void_p
        self.owns_handle=existing_handle is None
        self.handle=self.kernel.OpenProcess(0x1000,False,self.pid) if self.owns_handle else int(existing_handle)
        require(self.handle,'Cannot retain actual process handle')
        class FT(ctypes.Structure): _fields_=[('low',ctypes.c_uint32),('high',ctypes.c_uint32)]
        a,b,c,d=FT(),FT(),FT(),FT()
        require(self.kernel.GetProcessTimes(ctypes.c_void_p(self.handle),ctypes.byref(a),ctypes.byref(b),ctypes.byref(c),ctypes.byref(d)),'Cannot read retained actual process creation time')
        seconds=((a.high<<32)|a.low)/10000000-11644473600
        self.started_utc=datetime.fromtimestamp(seconds,timezone.utc).isoformat()
    def exit_code(self):
        value=ctypes.c_ulong()
        require(self.kernel.GetExitCodeProcess(ctypes.c_void_p(self.handle),ctypes.byref(value)),'Cannot read actual worker exit code')
        return value.value
    def close(self):
        if self.handle and self.owns_handle:self.kernel.CloseHandle(ctypes.c_void_p(self.handle))
        self.handle=None

def direct_parent_pid(pid):
    require(os.name=='nt','Windows parent identity is required')
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateToolhelp32Snapshot.restype=ctypes.c_void_p
    snapshot=kernel.CreateToolhelp32Snapshot(2,0)
    require(snapshot not in (None,ctypes.c_void_p(-1).value),'Process snapshot failed')
    class Entry(ctypes.Structure):
        _fields_=[('dwSize',ctypes.c_uint32),('cntUsage',ctypes.c_uint32),('th32ProcessID',ctypes.c_uint32),
            ('th32DefaultHeapID',ctypes.c_size_t),('th32ModuleID',ctypes.c_uint32),('cntThreads',ctypes.c_uint32),
            ('th32ParentProcessID',ctypes.c_uint32),('pcPriClassBase',ctypes.c_long),('dwFlags',ctypes.c_uint32),('szExeFile',ctypes.c_wchar*260)]
    entry=Entry();entry.dwSize=ctypes.sizeof(entry)
    try:
        success=kernel.Process32FirstW(ctypes.c_void_p(snapshot),ctypes.byref(entry))
        while success:
            if entry.th32ProcessID==pid:return int(entry.th32ParentProcessID)
            success=kernel.Process32NextW(ctypes.c_void_p(snapshot),ctypes.byref(entry))
        raise RuntimeError('Actual worker is missing from process ancestry snapshot')
    finally:kernel.CloseHandle(ctypes.c_void_p(snapshot))

def worker_lineage(worker_pid,supervisor_pid,supervisor_started):
    result=[];current=worker_pid
    for _ in range(8):
        started=process_started(current);require(started,'Missing live process in worker ancestry')
        parent=direct_parent_pid(current)
        result.append({'pid':current,'started_utc':started,'parent_process_id':parent})
        if current==supervisor_pid:
            require(started==supervisor_started,'Supervising ancestor creation identity changed')
            return result
        require(parent>0 and parent not in [row['pid'] for row in result],'Invalid worker ancestry chain')
        current=parent
    raise RuntimeError('Actual worker is not descended from the admitted supervisor')

def validate_worker_identity(identity,plan_sha,release_sha,supervisor,launcher):
    require(identity['schema']=='dac-actual-worker-identity.v2' and identity['plan_sha256']==plan_sha and identity['release_sha256']==release_sha,'Worker handshake belongs to another launch')
    lineage=identity['lineage'];require(lineage and lineage[0]['pid']==identity['pid'] and lineage[0]['started_utc']==identity['started_utc'],'Actual worker is not first in lineage')
    require(lineage[-1]['pid']==supervisor['pid'] and lineage[-1]['started_utc']==supervisor['started_utc'],'Wrong supervising ancestor')
    require(any(row['pid']==launcher['pid'] and row['started_utc']==launcher['started_utc'] for row in lineage),'Popen launcher is absent from actual worker lineage')
    for child,parent in zip(lineage,lineage[1:]):require(child['parent_process_id']==parent['pid'],'Broken worker-parent linkage')
    require(len({row['pid'] for row in lineage})==len(lineage),'Repeated worker ancestry identity')
    return identity

def owners(value,inherited_start=None,inherited_finish=None):
    if isinstance(value,dict):
        generic_start=next((value[name] for name in ('started_utc','process_started_utc','process_created_utc','actual_created_utc','creation_time_utc','created_utc') if value.get(name)),inherited_start)
        generic_finish=next((value[name] for name in ('finished_utc','ended_utc','completed_utc','exited_utc','exit_observed_utc') if value.get(name)),inherited_finish)
        for key,item in value.items():
            if key=='pid' or key.endswith('_pid'):
                if item is None: continue
                number(item,1,True)
                prefix=key[:-4] if key.endswith('_pid') else ''
                start=value.get(prefix+'_started_utc',generic_start) if prefix else generic_start
                finish=value.get(prefix+'_finished_utc',generic_finish) if prefix else generic_finish
                require(isinstance(start,str),'Owner PID lacks matching start time: '+key)
                require(datetime.fromisoformat(start).tzinfo is not None,'Owner timestamp lacks timezone')
                if finish is not None:
                    require(isinstance(finish,str) and datetime.fromisoformat(finish).tzinfo is not None,'Owner finish timestamp lacks timezone')
                    require(datetime.fromisoformat(finish)>=datetime.fromisoformat(start),'Owner finished before it started')
                yield {'pid':item,'started_utc':start,'finished_utc':finish,'field':key}
            elif isinstance(item,(dict,list)): yield from owners(item,generic_start,generic_finish)
    elif isinstance(value,list):
        for item in value: yield from owners(item,inherited_start,inherited_finish)

def reject_failed_records(value):
    """Reject nested commands/jobs even if an ancestor misleadingly says completed."""
    if isinstance(value,dict):
        for key,item in value.items():
            if key in ('exit_code','returncode','return_code') or key.endswith('_exit_code'):
                require(type(item) is int and item==0,'Nested command did not exit successfully')
            if key=='status':
                require(item not in ('failed','error','running','starting','pending','queued','interrupted','cancelled','canceled','killed','blocked','not_run'),'Nested command/status is unfinished or failed')
            if isinstance(item,(dict,list)): reject_failed_records(item)
    elif isinstance(value,list):
        for item in value: reject_failed_records(item)

def exited(value):
    reject_failed_records(value)
    recorded=list(owners(value)); require(recorded,'Missing actual process owner evidence')
    for owner in recorded:
        actual=process_started(owner['pid'])
        if actual is not None:
            # Startup can take much longer than a fixed tolerance on Windows.
            # Only a process created AFTER the recorded completion proves PID
            # reuse; absent a finish timestamp, a live PID always blocks release.
            require(owner['finished_utc'] is not None and datetime.fromisoformat(actual)>datetime.fromisoformat(owner['finished_utc']),
                'A preceding owner is still alive or its reuse cannot be proved')
    return recorded

def gpu_empty(stdout):
    rows=list(csv.reader(io.StringIO(stdout)))
    rows=[row for row in rows if any(cell.strip() for cell in row)]
    # CUDA owners of any executable block admission, including Julia/C++/unknown.
    require(not rows,'GPU compute allocation is occupied: '+repr(rows))
    return rows

@contextmanager
def shared_lock():
    require(os.name=='nt','Windows byte-range lock required')
    import msvcrt
    path=EXECUTION/'latest_baseline_gpu.lock'
    with path.open('a+b') as stream:
        stream.seek(0,os.SEEK_END)
        if not stream.tell(): stream.write(b'0');stream.flush()
        stream.seek(0)
        try: msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        except OSError as error: raise RuntimeError('Another serial baseline owns the GPU lock') from error
        try: yield
        finally:
            stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)

def serial_gate(plan_bound,release_bound,stage):
    plan,release=plan_bound.value,release_bound.value
    require(release.get('schema')=='dac-serial-release.v2' and release.get('allow_cuda') is True,'No separate DAC serial release')
    require(release['plan_sha256']==plan_bound.sha256 and stage in release['stages'],'Release does not admit this exact plan/stage')
    require(release['control_binding']==plan['control_binding'] and release['science_binding']==plan['science_binding'],'Release source binding mismatch')
    required={'status.json':'completed','pipeline_status.json':'ready_for_extension_preparation',
        'extension_status.json':'registered_extensions_finished_review_pending',
        'latest_baseline_status.json':'latest_baselines_finished_review_pending',
        'independent_comparison_status.json':'independent_comparisons_finished_review_pending'}
    rows=release['predecessors']; paths=[Path(row['status_path']).resolve() for row in rows]
    require(len(paths)==len(set(paths)),'Duplicate prerequisite binding')
    require(all(EXECUTION/name in paths for name in required),'Missing one of the five registered preceding stages')
    checked=[]
    for row in rows:
        path=Path(row['status_path']).resolve()
        require(path.is_relative_to(EXECUTION),'Prerequisite escaped execution workspace')
        bound=Bound.load(path,row['status_sha256']); state=bound.value
        expected_status=required.get(path.name,row['required_status'])
        require(state['status']==expected_status==row['required_status'],'Prerequisite is not at admitted completion stage')
        if path.name=='status.json': require(state.get('stage')=='all','Primary matrix incomplete')
        if path.name=='pipeline_status.json':
            expected_ids=['formal_aggregate','formal_figures','cross_dataset_transfer','robustness','robustness_aggregate','query_analysis','formal_efficiency_component']
        elif path.name in ('extension_status.json','latest_baseline_status.json','independent_comparison_status.json'):
            plan_name={'extension_status.json':'extension_plan.json','latest_baseline_status.json':'latest_baseline_plan.json','independent_comparison_status.json':'independent_comparison_plan_v2.json'}[path.name]
            if path.name=='independent_comparison_status.json':
                require(row['plan_sha256']=='a5318f7a60497cc7c9ccb74b7cd82ef7f71fcb072c36a90fb192ea27acc6ca49','The fifth registered queue plan is not the reviewed v2')
            predecessor=Bound.load(EXECUTION/plan_name,row['plan_sha256'])
            require(state['plan_sha256']==predecessor.sha256,'Preceding job plan mismatch')
            expected_ids=[job['id'] for job in predecessor.value['jobs']]
            require(len(expected_ids)=={'extension_status.json':4,'latest_baseline_status.json':2,'independent_comparison_status.json':3}[path.name],'Wrong required predecessor job count')
        else: expected_ids=row.get('job_ids')
        if expected_ids is not None:
            require([job['id'] for job in state.get('jobs',[])]==expected_ids,'Preceding job IDs differ')
            require(all(job['status']=='completed' and type(job.get('exit_code')) is int and job['exit_code']==0 for job in state['jobs']),'Missing/failed preceding job exit')
        processes=exited(state)
        bound.unchanged()
        checked.append({'path':str(path),'sha256':bound.sha256,'owners':processes})
    response=subprocess.run(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader,nounits'],
        capture_output=True,text=True,timeout=30,check=True,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    rows=gpu_empty(response.stdout)
    plan_bound.unchanged(); release_bound.unchanged()
    return {'schema':'dac-current-serial-allocation.v2','verified_utc':utc(),'stage':stage,
        'plan_sha256':plan_bound.sha256,'release_sha256':release_bound.sha256,'predecessors':checked,
        'gpu_compute_rows':rows,'shared_gpu_lock_held':True}
