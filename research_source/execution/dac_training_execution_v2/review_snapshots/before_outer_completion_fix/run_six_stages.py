"""Explicit future serial DAC execution. No release/registration or science at import."""
import argparse
from contextlib import contextmanager
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import dac6_contracts as d

@contextmanager
def controller_lock():
    d.require(os.name=='nt','Windows execution only')
    import msvcrt
    root=d.HERE/'runtime';root.mkdir(exist_ok=True)
    with (root/'controller.lock').open('a+b') as stream:
        stream.seek(0,os.SEEK_END)
        if not stream.tell():stream.write(b'0');stream.flush()
        stream.seek(0)
        try:msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        except OSError as error:raise RuntimeError('This six-stage coordinator is already owned') from error
        try:yield
        finally:stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)

def closed_execution_evidence(row):
    root=d.stage_directory(row['id']);inner=Path(row['control_receipt_path']).parent
    return {key:d.artifact(path) for key,path in {
        'request':root/'request.json','serial_release':root/'serial_release.json',
        'worker_identity':root/'worker_identity.json','parent_observed':root/'parent_observed.json',
        'supervisor_stdout':root/'supervisor_stdout.log','supervisor_stderr':root/'supervisor_stderr.log',
        'science_stdout':Path(row['output_directory'])/'stdout.log','science_stderr':Path(row['output_directory'])/'stderr.log',
        'inner_stdout':inner/'child_stdout.log','inner_stderr':inner/'child_stderr.log',
        'inner_identity':inner/'worker_identity.json','inner_lifecycle':inner/'lifecycle.json'}.items()}

def late_profile_binding(row,previous):
    if row['stage']=='profile':return None
    d.require(previous is not None and previous['id']==f"seed_{row['seed']}_profile" and previous['status']=='completed','Training cannot bypass its own successful native profile')
    return {'profile_sha256':previous['artifact_verification']['profile']['sha256'],
        'receipt_sha256':previous['artifact_verification']['lifecycle']['sha256']}

def launch_stage(row,state,spec,release):
    root=d.stage_directory(row['id']);d.require(not root.exists(),'Stage execution directory already exists; preserve and review the failed/partial run')
    root.mkdir(parents=True)
    plan=d.c.Bound.load(row['plan_path'],row['plan_sha256'])
    serial=d.serial_release(plan,release,row['stage']);d.c.write(root/'serial_release.json',serial)
    serial_bound=d.c.Bound.load(root/'serial_release.json',d.sha(root/'serial_release.json'))
    previous=state['jobs'][-1] if state['jobs'] else None
    pair=late_profile_binding(row,previous)
    request={'schema':'dac-six-stage-request.v2','id':row['id'],
        'execution_spec_path':str(spec.path),'execution_spec_sha256':spec.sha256,
        'root_release_path':str(release.path),'root_release_sha256':release.sha256,
        'serial_release_path':str(serial_bound.path),'serial_release_sha256':serial_bound.sha256,
        'profile_binding':pair,'controller_pid':state['controller_pid'],
        'controller_started_utc':state['controller_started_utc']}
    d.c.write(root/'request.json',request);request_bound=d.c.Bound.load(root/'request.json',d.sha(root/'request.json'))
    command=[plan.value['environment']['executable'],'-B',str(d.HERE/'stage_entry.py'),
        '--request',str(request_bound.path),'--request-sha256',request_bound.sha256]
    record={**row,'status':'starting','controller_pid':state['controller_pid'],
        'controller_started_utc':state['controller_started_utc'],'command':command,
        'process_environment':d.c.PROCESS_ENV,'profile_binding':pair,'request_sha256':request_bound.sha256}
    state['jobs'].append(record);d.c.write(Path(spec.value['status_path']),state)
    process=launcher_handle=worker_handle=None
    try:
        # Admission is repeated by the native child under the shared GPU lock.
        # This early check never holds that lock while launching a child.
        with d.g.shared_lock():d.g.serial_gate(plan,serial_bound,row['stage'])
        environment=os.environ.copy();environment.update(d.c.PROCESS_ENV)
        with (root/'supervisor_stdout.log').open('x',encoding='utf-8') as out,(root/'supervisor_stderr.log').open('x',encoding='utf-8') as err:
            process=subprocess.Popen(command,stdout=out,stderr=err,env=environment,creationflags=subprocess.CREATE_NO_WINDOW)
            launcher_handle=d.g.ProcessObservation(process.pid,existing_handle=process._handle)
            record.update(status='running',launcher_pid=process.pid,launcher_started_utc=launcher_handle.started_utc)
            d.c.write(spec.value['status_path'],state)
            deadline=time.monotonic()+60
            while not (root/'worker_identity.json').exists():
                d.require(process.poll() is None,'Stage launcher exited before the actual supervisor handshake')
                d.require(time.monotonic()<deadline,'Stage actual supervisor handshake timeout')
                time.sleep(.05)
            identity=d.g.validate_worker_identity(d.c.read(root/'worker_identity.json'),plan.sha256,serial_bound.sha256,
                {'pid':state['controller_pid'],'started_utc':state['controller_started_utc']},
                {'pid':process.pid,'started_utc':launcher_handle.started_utc})
            worker_handle=d.g.ProcessObservation(identity['pid'])
            d.require(worker_handle.started_utc==identity['started_utc'],'Actual supervisor handle does not match its handshake')
            record.update(supervisor_pid=identity['pid'],supervisor_started_utc=identity['started_utc'])
            d.c.write(spec.value['status_path'],state)
            d.c.write(root/'parent_observed.json',{'request_sha256':request_bound.sha256,
                'worker_identity_sha256':d.sha(root/'worker_identity.json'),'controller_pid':state['controller_pid'],
                'controller_started_utc':state['controller_started_utc']})
            launcher_code=process.wait()
        actual_code=worker_handle.exit_code()
        record.update(launcher_exit_code=launcher_code,supervisor_exit_code=actual_code,exit_code=actual_code,finished_utc=d.c.utc())
        d.require(launcher_code==actual_code==0,'Actual supervisor or launcher failed/remains live; retain all outputs and stop')
        for bound in (plan,spec,release,serial_bound,request_bound):bound.unchanged()
        receipt=d.c.Bound.load(row['control_receipt_path'],d.sha(row['control_receipt_path']))
        d.require(receipt.value['pid']==record['supervisor_pid'] and receipt.value['started_utc']==record['supervisor_started_utc'],'Inner control receipt is from a different actual supervisor')
        d.g.exited(receipt.value)
        record.update(control_receipt_sha256=receipt.sha256,result_sha256=receipt.value['result_sha256'],
            execution_evidence=closed_execution_evidence(row))
        if row['stage']=='profile':
            profile=d.c.Bound.load(Path(row['output_directory'])/'profile.json',record['result_sha256'])
            d.c.validate_profile(profile,plan,receipt,d.g.exited)
            verified={'profile':d.artifact(profile.path),'lifecycle':d.artifact(receipt.path)}
        else:verified=d.verify_training_artifacts(plan,receipt)
        record.update(status='completed',artifact_verification=verified)
        d.verify_stage(row,record)
        d.c.write(spec.value['status_path'],state)
        return record
    except BaseException as error:
        record.update(status='failed',error=repr(error),failed_utc=d.c.utc())
        if process is not None:
            record['launcher_still_alive']=process.poll() is None
            if process.poll() is not None:record['launcher_exit_code']=process.returncode
        if worker_handle is not None:record['supervisor_exit_code']=worker_handle.exit_code()
        d.c.write(spec.value['status_path'],state)
        raise
    finally:
        if worker_handle is not None:worker_handle.close()
        if launcher_handle is not None:launcher_handle.close()

def run(spec_path,spec_sha256,release_path,release_sha256):
    spec=d.spec_bound(spec_path,spec_sha256);release=d.release_bound(release_path,release_sha256,spec)
    # Refuse to overwrite any prior partial, failed, or completed run. Restarting
    # requires a reviewed continuation plan, not a silent fresh model or new SHA.
    with controller_lock():
        status_path=Path(spec.value['status_path']);completion_path=Path(spec.value['completion_path'])
        d.require(not status_path.exists() and not completion_path.exists(),'Existing six-stage execution must be reviewed; no automatic rerun/resume')
        state={'schema':'dac-six-stage-execution-status.v2','status':'running',
            'execution_spec_path':str(spec.path),'execution_spec_sha256':spec.sha256,
            'execution_manifest_sha256':d.own_manifest(),'root_release_path':str(release.path),'root_release_sha256':release.sha256,
            'controller_pid':os.getpid(),'controller_started_utc':d.g.process_started(os.getpid()),'jobs':[]}
        d.c.write(status_path,state)
        try:
            for row in spec.value['jobs']:
                for prior_row,prior_record in zip(spec.value['jobs'],state['jobs']):d.verify_stage(prior_row,prior_record)
                spec.unchanged();release.unchanged();d.own_manifest()
                launch_stage(row,state,spec,release)
            seeds=[]
            for row,record in zip(spec.value['jobs'],state['jobs']):
                verified=d.verify_stage(row,record)
                if row['stage']=='train':seeds.append({'seed':row['seed'],'plan_path':row['plan_path'],'plan_sha256':row['plan_sha256'],
                    'output_directory':row['output_directory'],'control_receipt_path':record['control_receipt_path'],
                    'control_receipt_sha256':record['control_receipt_sha256'],'artifacts':verified})
            spec.unchanged();release.unchanged();d.own_manifest()
            state.update(status='completed',exit_code=0,finished_utc=d.c.utc(),exit_code_scope='coordinator return intent; external verifier must also prove actual owner exit')
            d.c.write(status_path,state)
            d.c.write(d.HERE/'runtime/candidate_completion.json',{'schema':'dac-six-stage-completion.v2','execution_spec_sha256':spec.sha256,
                'execution_manifest_sha256':d.own_manifest(),'status_sha256':d.sha(status_path),'training_artifacts':seeds})
        except BaseException as error:
            state.update(status='failed',error=repr(error),failed_utc=d.c.utc(),traceback=traceback.format_exc())
            d.c.write(status_path,state)
            raise

def coordinator_child(request_path,request_sha256):
    request=d.c.Bound.load(request_path,request_sha256);value=request.value
    d.require(request.path==d.HERE/'runtime/coordinator_request.json' and value['schema']=='dac-six-stage-coordinator-request.v2','Wrong coordinator launch request')
    spec=d.spec_bound(value['spec_path'],value['spec_sha256']);release=d.release_bound(value['release_path'],value['release_sha256'],spec)
    identity={'schema':'dac-actual-worker-identity.v2','pid':os.getpid(),'started_utc':d.g.process_started(os.getpid()),
        'plan_sha256':spec.sha256,'release_sha256':release.sha256,
        'lineage':d.g.worker_lineage(os.getpid(),value['parent_pid'],value['parent_started_utc'])}
    root=d.HERE/'runtime';d.c.write(root/'coordinator_identity.json',identity);deadline=time.monotonic()+60
    while not (root/'coordinator_observed.json').exists():
        d.require(time.monotonic()<deadline,'Coordinator observation timeout')
        d.require(d.g.process_started(value['parent_pid'])==value['parent_started_utc'],'Observing parent disappeared')
        time.sleep(.05)
    d.require(d.c.read(root/'coordinator_observed.json')=={'request_sha256':request.sha256,'identity_sha256':d.sha(root/'coordinator_identity.json')},'Coordinator observation acknowledgement mismatch')
    request.unchanged();run(str(spec.path),spec.sha256,str(release.path),release.sha256)
    request.unchanged()

def supervise_coordinator(spec_path,spec_sha256,release_path,release_sha256):
    """One non-scientific observer records the real coordinator exit before sealing."""
    spec=d.spec_bound(spec_path,spec_sha256);release=d.release_bound(release_path,release_sha256,spec)
    root=d.HERE/'runtime'
    # Atomic directory creation is the outer observer's single-owner reservation.
    # Any existing directory is retained for review, never overwritten/resumed.
    root.mkdir(exist_ok=False)
    parent={'pid':os.getpid(),'started_utc':d.g.process_started(os.getpid())}
    request={'schema':'dac-six-stage-coordinator-request.v2','spec_path':str(spec.path),'spec_sha256':spec.sha256,
        'release_path':str(release.path),'release_sha256':release.sha256,'parent_pid':parent['pid'],'parent_started_utc':parent['started_utc']}
    d.c.write(root/'coordinator_request.json',request)
    bound=d.c.Bound.load(root/'coordinator_request.json',d.sha(root/'coordinator_request.json'))
    receipt={'schema':'dac-six-stage-controller-lifecycle.v2','status':'starting',**parent,
        'execution_spec_sha256':spec.sha256,'root_release_sha256':release.sha256}
    path=root/'controller_lifecycle.json';d.c.write(path,receipt)
    command=[sys.executable,'-B',str(Path(__file__).resolve()),'--coordinator-child',
        '--request',str(bound.path),'--request-sha256',bound.sha256]
    process=launcher_handle=worker_handle=None
    try:
        with (root/'coordinator_stdout.log').open('x',encoding='utf-8') as out,(root/'coordinator_stderr.log').open('x',encoding='utf-8') as err:
            process=subprocess.Popen(command,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
            launcher_handle=d.g.ProcessObservation(process.pid,existing_handle=process._handle)
            receipt.update(status='running',launcher_pid=process.pid,launcher_started_utc=launcher_handle.started_utc);d.c.write(path,receipt)
            deadline=time.monotonic()+60
            while not (root/'coordinator_identity.json').exists():
                d.require(process.poll() is None,'Coordinator launcher exited before actual identity handshake')
                d.require(time.monotonic()<deadline,'Coordinator identity handshake timeout')
                time.sleep(.05)
            identity=d.g.validate_worker_identity(d.c.read(root/'coordinator_identity.json'),spec.sha256,release.sha256,parent,
                {'pid':process.pid,'started_utc':launcher_handle.started_utc})
            worker_handle=d.g.ProcessObservation(identity['pid'])
            d.require(worker_handle.started_utc==identity['started_utc'],'Coordinator actual handle differs from handshake')
            receipt.update(child_pid=identity['pid'],child_started_utc=identity['started_utc']);d.c.write(path,receipt)
            d.c.write(root/'coordinator_observed.json',{'request_sha256':bound.sha256,'identity_sha256':d.sha(root/'coordinator_identity.json')})
            launcher_code=process.wait()
        actual_code=worker_handle.exit_code()
        receipt.update(exit_code=actual_code,launcher_exit_code=launcher_code,finished_utc=d.c.utc())
        d.require(actual_code==launcher_code==0,'Coordinator or launcher failed/remains live; do not seal completion')
        spec.unchanged();release.unchanged();bound.unchanged();d.own_manifest()
        state=d.c.read(spec.value['status_path']);d.g.exited(state)
        d.require(state['status']=='completed' and state['controller_pid']==identity['pid'] and state['controller_started_utc']==identity['started_utc'],'Final state is not from actual completed coordinator')
        candidate=d.c.Bound.load(root/'candidate_completion.json',d.sha(root/'candidate_completion.json'))
        d.require(candidate.value['status_sha256']==d.sha(spec.value['status_path']),'Candidate status changed before real exit receipt')
        for row,record in zip(spec.value['jobs'],state['jobs']):d.verify_stage(row,record)
        evidence={key:d.artifact(root/name) for key,name in {'stdout':'coordinator_stdout.log','stderr':'coordinator_stderr.log',
            'identity':'coordinator_identity.json','request':'coordinator_request.json','acknowledgement':'coordinator_observed.json','candidate':'candidate_completion.json'}.items()}
        receipt.update(status='completed',status_sha256=candidate.value['status_sha256'],evidence=evidence);d.c.write(path,receipt)
        candidate.unchanged()
        d.c.write(spec.value['completion_path'],{**candidate.value,'controller_lifecycle':d.artifact(path)})
    except BaseException as error:
        receipt.update(status='failed',error=repr(error),failed_utc=d.c.utc())
        if process is not None:
            receipt['launcher_still_alive']=process.poll() is None
            if process.poll() is not None:receipt['launcher_exit_code']=process.returncode
        if worker_handle is not None:receipt['exit_code']=worker_handle.exit_code()
        d.c.write(path,receipt)
        raise
    finally:
        if worker_handle is not None:worker_handle.close()
        if launcher_handle is not None:launcher_handle.close()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('spec','spec-sha256','release-file','release-sha256','request','request-sha256'):p.add_argument('--'+name)
    p.add_argument('--coordinator-child',action='store_true');args=p.parse_args()
    if args.coordinator_child:
        d.require(args.request and args.request_sha256,'Internal coordinator requires captured launch request')
        coordinator_child(args.request,args.request_sha256)
    else:
        d.require(all((args.spec,args.spec_sha256,args.release_file,args.release_sha256)),'Future execution requires actual admitted specification and release hashes')
        supervise_coordinator(args.spec,args.spec_sha256,args.release_file,args.release_sha256)

if __name__=='__main__':main()
