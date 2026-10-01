"""Future explicit DAC resource/train stages; no scientific imports at module load."""
import argparse
from contextlib import contextmanager, redirect_stderr, redirect_stdout
import json
import math
import os
from pathlib import Path
import runpy
import subprocess
import sys
import time
import traceback
from unittest.mock import patch
import dac2_contracts as c
import dac2_gates as gates

class ProfileComplete(Exception): pass

def profile_decision(actual,attempts):
    c.number(actual,0,True);c.number(attempts,0,True)
    c.require(actual<=attempts<=32,'Invalid bounded native profile step accounting')
    if actual>=2: return 'complete'
    c.require(attempts<32,'Two actual AdamW updates were not reached within 32 original batches')
    return 'continue'

class Session:
    """All external inputs are captured once with externally admitted SHA values."""
    def __init__(self,args):
        self.args=args
        self.plan=c.Bound.load(args.plan,args.plan_sha256)
        self.release=c.Bound.load(args.release_file,args.release_sha256)
        self.profile=self.profile_receipt=None
        if args.stage=='train':
            self.profile=c.Bound.load(args.profile,args.profile_sha256)
            self.profile_receipt=c.Bound.load(args.profile_receipt,args.profile_receipt_sha256)
        self.snapshots=[]
    def load(self):
        self.config,self.modules,self.inventory,self.cpu,self.cpu_artifacts=c.validate_plan(self.plan,check_content=True)
        if self.profile:
            c.validate_profile(self.profile,self.plan,self.profile_receipt,gates.exited)
        self.output=Path(self.config['profile_directory' if self.args.stage=='profile' else 'output_directory']).resolve()
        return self
    def unchanged(self):
        for item in (self.plan,self.release,self.inventory,self.cpu,self.profile,self.profile_receipt,*self.snapshots):
            if item is not None: item.unchanged()
        c.require(self.config['science_binding']==c.science_binding() and self.config['control_binding']==c.control_binding(),'Bound code changed during execution')
        c.require(self.modules['input_audit'].environment()==self.config['environment'],'Runtime metadata changed during execution')
        c.require(all(os.environ.get(k)==v for k,v in c.PROCESS_ENV.items()),'Process environment changed during execution')
        c.validate_cpu(self.config)
        if self.profile: c.validate_profile(self.profile,self.plan,self.profile_receipt,gates.exited)
    def save_snapshots(self):
        for original,name in ((self.plan,'plan.json'),(self.release,'serial_release.json'),(self.inventory,'data_manifest.json'),(self.cpu,'cpu_result.json'),(self.profile,'resource_profile.json'),(self.profile_receipt,'resource_profile_lifecycle.json')):
            if original is not None: self.snapshots.append(original.copy(self.output/name))
        c.write(self.output/'stage_bindings.json',{'schema':'dac-stage-immutable-bindings.v2',
            'plan_sha256':self.plan.sha256,'release_sha256':self.release.sha256,
            'profile_sha256':self.profile.sha256 if self.profile else None,
            'profile_receipt_sha256':self.profile_receipt.sha256 if self.profile_receipt else None,
            'cpu_result_sha256':self.cpu.sha256,'original_paths':{str(x.path):x.sha256 for x in (self.plan,self.release,self.inventory,self.cpu,self.profile,self.profile_receipt) if x is not None}})
        c.write(self.output/'code_manifest.json',{'science':self.config['science_binding'],'control':self.config['control_binding']})
        c.write(self.output/'environment_manifest.json',self.config['environment'])

def make_run(session,torch_module):
    base=session.modules['dac_train_runtime'].DACTrainRun
    class AdmittedRun(base):
        def __init__(self):
            # Original scientific plan fields and seed are unchanged. Runtime SHA
            # lookups refer to copied admitted bytes, never mutable external inputs.
            super().__init__(session.config,session.output/'plan.json',
                session.output/('resource_profile.json' if session.args.stage=='train' else 'profile.json'))
            self.output=session.output
            self.model=None
            self.resource_started=time.perf_counter()
            self.previous_batch_time=None
        def observe_optimizer(self,optimizer,model,scaler):
            self.model=model
            super().observe_optimizer(optimizer,model,scaler)
        def before_epoch(self,epoch,loader):
            super().before_epoch(epoch,loader)
            if session.args.stage=='profile':
                torch_module.cuda.synchronize();self.previous_batch_time=time.perf_counter()
        def after_batch(self,completed_batches):
            super().after_batch(completed_batches)
            if session.args.stage=='profile':
                # The official trainer has finished scaler.step, scaler.update,
                # zero_grad and scheduler.step before this loader resumes.
                torch_module.cuda.synchronize(); now=time.perf_counter()
                row={'batch_attempt':completed_batches,'actual_adamw_steps':self.actual_optimizer_steps,
                    'amp_skips':self.amp_skips,'seconds_including_data_and_synchronization':now-self.previous_batch_time,
                    'peak_allocated_bytes':torch_module.cuda.max_memory_allocated(),
                    'peak_reserved_bytes':torch_module.cuda.max_memory_reserved(),
                    'allocated_bytes':torch_module.cuda.memory_allocated(),'reserved_bytes':torch_module.cuda.memory_reserved()}
                self.previous_batch_time=now
                with (self.output/'resource_batches.jsonl').open('a',encoding='utf-8') as stream:
                    stream.write(json.dumps(row,allow_nan=False)+'\n')
                if profile_decision(self.actual_optimizer_steps,completed_batches)=='complete': raise ProfileComplete()
        def save_complete(self,namespace):
            if session.args.stage=='profile': raise RuntimeError('A resource profile cannot write a research checkpoint')
            session.unchanged()
            super().save_complete(namespace)
            # Reject old-value/new-hash provenance even if external files changed
            # while original checkpoint serialization was in progress.
            session.unchanged()
            complete=c.read(self.output/'status.json')
            c.require(complete['status']=='completed' and complete['epoch_completed']==1,'Missing fixed final-epoch completion')
    return AdmittedRun()

def finite_update(run,torch):
    schema=run.model.state_dict()
    run_module=__import__('dac_train_runtime')
    run_module.validate_model_schema(schema)
    bad_model=[name for name,value in schema.items() if value.is_floating_point() and not torch.isfinite(value).all().item()]
    state=run.optimizer.state_dict()
    c.require(state.get('state') and state.get('param_groups'),'Native profile lacks actual AdamW moment state')
    steps=[]
    for row in state['state'].values():
        c.require({'step','exp_avg','exp_avg_sq'}.issubset(row),'Incomplete native AdamW state')
        value=float(row['step']);c.number(value,1)
        c.require(value==int(value),'Invalid AdamW step counter');steps.append(int(value))
        c.require(all(torch.isfinite(row[key]).all().item() for key in ('exp_avg','exp_avg_sq')),'Nonfinite AdamW moments')
    c.require(max(steps)==run.actual_optimizer_steps,'Real update hook differs from AdamW state')
    final=run.parameter_digest(run.representative_parameter)
    c.require(not bad_model and final!=run.initial_parameter_sha256,'Native profile did not produce finite changed parameters')
    c.require(run.scaler.is_enabled(),'Native AMP scaler is disabled')
    scaler=run.scaler.state_dict();c.require(c.number(scaler['scale'],0)>0,'Invalid final scaler')
    return {'all_model_floating_state_finite':True,'all_optimizer_floating_state_finite':True,
        'representative_parameter':run.representative_name,'initial_parameter_sha256':run.initial_parameter_sha256,
        'final_parameter_sha256':final,'representative_parameter_changed':True,
        'optimizer_step_min':min(steps),'optimizer_step_max':max(steps),'final_scaler_state':scaler}

@contextmanager
def tracked_writers():
    import torch.utils.tensorboard as module
    original=module.SummaryWriter;writers=[]
    def create(*args,**kwargs):
        writer=original(*args,**kwargs);writers.append(writer);return writer
    with patch.object(module,'SummaryWriter',create):
        try: yield
        finally:
            for writer in writers: writer.close()

def child(args):
    session=Session(args)
    config=session.plan.value
    output=Path(config['profile_directory' if args.stage=='profile' else 'output_directory']).resolve()
    c.require(output.is_relative_to(c.EXECUTION) and not output.is_relative_to(c.SCIENCE) and not output.is_relative_to(c.HERE),'Invalid output directory')
    output.mkdir(parents=True,exist_ok=False)
    identity={'pid':os.getpid(),'started_utc':gates.process_started(os.getpid()),
        'parent_pid':args.parent_pid,'parent_started_utc':args.parent_started_utc,'execution_started_utc':c.utc()}
    c.require(identity['started_utc'],'Missing actual child creation identity')
    c.require(gates.process_started(args.parent_pid)==args.parent_started_utc,'Actual supervising parent identity changed')
    handshake_path=Path(args.worker_identity_file).resolve()
    expected_receipt=Path(config['profile_receipt_directory' if args.stage=='profile' else 'training_receipt_directory']).resolve()
    c.require(handshake_path==expected_receipt/'worker_identity.json','Worker handshake path differs from admitted receipt directory')
    handshake={'schema':'dac-actual-worker-identity.v2','pid':identity['pid'],'started_utc':identity['started_utc'],
        'plan_sha256':session.plan.sha256,'release_sha256':session.release.sha256,
        'lineage':gates.worker_lineage(identity['pid'],args.parent_pid,args.parent_started_utc)}
    c.write(handshake_path,handshake)
    stage_status={'schema':'dac-child-stage.v2','method':'DAC','stage':args.stage,'status':'starting',**identity,
        'plan_sha256':session.plan.sha256,'release_sha256':session.release.sha256}
    c.write(output/'status.json',stage_status)
    run=torch=None
    try:
        with (output/'stdout.log').open('x',encoding='utf-8',buffering=1) as stdout,(output/'stderr.log').open('x',encoding='utf-8',buffering=1) as stderr:
            with redirect_stdout(stdout),redirect_stderr(stderr):
                session.load();session.save_snapshots()
                common=session.modules['common_runtime']
                sys.dont_write_bytecode=True
                sys.path.insert(0,str(c.SCIENCE/'scientific_source'))
                with gates.shared_lock(),common.no_network():
                    session.unchanged()
                    allocation=gates.serial_gate(session.plan,session.release,args.stage)
                    c.write(output/'serial_release_gate.json',allocation)
                    session.modules['input_audit'].runtime_environment(output)
                    import torch
                    c.require(torch.cuda.is_available() and torch.cuda.device_count()==1,'Exactly one admitted CUDA device required')
                    torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats()
                    run=make_run(session,torch)
                    with run.image_boundary(),run.training_observers(),tracked_writers():
                        if args.stage=='profile':
                            reached=False
                            try:
                                runpy.run_path(str(c.SCIENCE/'train_university_train_only.py'),run_name='__main__',init_globals={'DAC_RUN':run})
                            except ProfileComplete: reached=True
                            c.require(reached and run.actual_optimizer_steps>=2,'Two actual full-loss native AdamW updates were not reached')
                        else:
                            runpy.run_path(str(c.SCIENCE/'train_university_train_only.py'),run_name='__main__',init_globals={'DAC_RUN':run})
                    session.unchanged()
                    if args.stage=='profile':
                        evidence=finite_update(run,torch)
                        c.require(not list(output.glob('*.pth')),'Resource probe wrote a research checkpoint')
                        torch.cuda.synchronize()
                        final_measurement={'phase':'after_finite_state_validation','measured_utc':c.utc(),
                            'pid':identity['pid'],'plan_sha256':session.plan.sha256,
                            'peak_allocated_bytes':torch.cuda.max_memory_allocated(),'peak_reserved_bytes':torch.cuda.max_memory_reserved()}
                        c.write(output/'final_resource_measurement.json',final_measurement)
                        report={'schema':'dac-native-resource-profile.v2','method':'DAC','status':'passed',**identity,
                            'plan_sha256':session.plan.sha256,'control_binding':config['control_binding'],'science_binding':config['science_binding'],
                            'environment':config['environment'],'process_environment':c.PROCESS_ENV,
                            'nominal_batch_pairs':24,'microbatch_pairs':24,'gradient_accumulation':1,'img_size':384,
                            'model_state_count':402,'mixed_precision':True,'loss_weights':{'InfoNCE':1.0,'classification':0.1,'DSA':0.6},
                            'all_official_losses':True,'oom':False,'research_result':False,'research_checkpoint_written':False,
                            'completed_optimizer_amp_steps':run.loader.completed_batches,'actual_adamw_steps':run.actual_optimizer_steps,
                            'amp_skips':run.amp_skips,'losses':run.loss_observations,
                            'all_observed_losses_finite':all(math.isfinite(value) for value in run.loss_observations),
                            'peak_allocated_bytes':final_measurement['peak_allocated_bytes'],'peak_reserved_bytes':final_measurement['peak_reserved_bytes'],
                            'post_validation_peak_allocated_bytes':final_measurement['peak_allocated_bytes'],
                            'post_validation_peak_reserved_bytes':final_measurement['peak_reserved_bytes'],
                            'seconds_including_initialization':time.perf_counter()-run.resource_started,
                            'device':{'name':torch.cuda.get_device_name(),'total_memory_bytes':torch.cuda.get_device_properties(0).total_memory},
                            'torch_threads':{'intraop':torch.get_num_threads(),'interop':torch.get_num_interop_threads()},
                            'finished_utc':c.utc(),**evidence}
                        batch=[c.strict_json(line) for line in (output/'batch_progress.jsonl').read_bytes().splitlines()]
                        resource=[c.strict_json(line) for line in (output/'resource_batches.jsonl').read_bytes().splitlines()]
                        c.profile_trace(report,batch,resource)
                        report['evidence_sha256']={str(path.relative_to(output)):c.sha(path) for path in output.iterdir()
                            if path.is_file() and path.name not in ('profile.json','status.json','stdout.log','stderr.log')}
                        c.write(output/'profile.json',report)
                    else:
                        saved=c.read(output/'status.json')
                        c.require(saved['status']=='completed' and saved['actual_adamw_steps']>0,'No valid complete training checkpoint')
                        stage_status.update(saved)
                    session.unchanged()
                    stage_status.update(status='completed',finished_utc=c.utc(),**identity)
                    c.write(output/'status.json',stage_status)
    except BaseException as error:
        (output/'failure.log').write_text(traceback.format_exc(),encoding='utf-8')
        oom=isinstance(error,MemoryError) or 'out of memory' in str(error).lower()
        if torch is not None: oom=oom or isinstance(error,torch.cuda.OutOfMemoryError)
        stage_status.update(status='failed',error=repr(error),oom=oom,failed_utc=c.utc(),
            recovery='Retain failed output and stop. No reduced batch, no profile-to-research reuse.')
        if run is not None:
            stage_status.update(actual_adamw_steps=run.actual_optimizer_steps,completed_batches=getattr(getattr(run,'loader',None),'completed_batches',0),loss_observations=run.loss_observations)
        if torch is not None and torch.cuda.is_initialized():
            stage_status.update(peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved())
        c.write(output/'status.json',stage_status)
        raise

def supervise_one(args):
    """Actual child exit is recorded only by its waiting parent, never self-declared."""
    plan=c.Bound.load(args.plan,args.plan_sha256);config=plan.value
    c.require(config['control_binding']==c.control_binding() and config['science_binding']==c.science_binding(),'Stage dispatcher code mismatch')
    c.require(Path(sys.executable).resolve()==Path(config['environment']['executable']).resolve(),'Use admitted independent DAC interpreter')
    c.require(config['process_environment']==c.PROCESS_ENV,'Child environment not admitted')
    receipt_dir=Path(config['profile_receipt_directory' if args.stage=='profile' else 'training_receipt_directory']).resolve()
    c.require(receipt_dir.is_relative_to(c.EXECUTION) and not receipt_dir.is_relative_to(c.HERE) and not receipt_dir.is_relative_to(c.SCIENCE),'Invalid receipt directory')
    receipt_dir.mkdir(parents=True,exist_ok=False)
    started=gates.process_started(os.getpid());c.require(started,'Missing supervising process creation time')
    receipt={'schema':'dac-stage-lifecycle.v2','stage':args.stage,'status':'starting','pid':os.getpid(),'started_utc':started,
        'plan_sha256':plan.sha256,'release_sha256':args.release_sha256,'execution_started_utc':c.utc()}
    path=receipt_dir/'lifecycle.json';c.write(path,receipt)
    command=[sys.executable,'-B',str(Path(__file__).resolve()),'--child','--stage',args.stage,
        '--plan',str(plan.path),'--plan-sha256',plan.sha256,'--release-file',args.release_file,'--release-sha256',args.release_sha256,
        '--parent-pid',str(os.getpid()),'--parent-started-utc',started,
        '--worker-identity-file',str(receipt_dir/'worker_identity.json')]
    if args.stage=='train':
        for key in ('profile','profile_sha256','profile_receipt','profile_receipt_sha256'):
            command.extend(['--'+key.replace('_','-'),getattr(args,key)])
    environment=os.environ.copy();environment.update(c.PROCESS_ENV)
    process=worker_observation=launcher_observation=None
    try:
        c.Bound.load(args.release_file,args.release_sha256);plan.unchanged()
        receipt['command']=command;receipt['process_environment']=c.PROCESS_ENV;c.write(path,receipt)
        with (receipt_dir/'child_stdout.log').open('x',encoding='utf-8') as out,(receipt_dir/'child_stderr.log').open('x',encoding='utf-8') as err:
            process=subprocess.Popen(command,stdout=out,stderr=err,env=environment,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            launcher_observation=gates.ProcessObservation(process.pid,existing_handle=process._handle)
            launcher={'pid':process.pid,'started_utc':launcher_observation.started_utc}
            receipt.update(status='running',launcher_pid=process.pid,launcher_started_utc=launcher['started_utc']);c.write(path,receipt)
            handshake_path=receipt_dir/'worker_identity.json';deadline=time.monotonic()+60
            while not handshake_path.exists():
                c.require(process.poll() is None,'Launcher exited before actual worker identity was registered')
                c.require(time.monotonic()<deadline,'Actual worker did not register within the bounded startup window')
                time.sleep(0.05)
            actual=gates.validate_worker_identity(c.read(handshake_path),plan.sha256,args.release_sha256,
                {'pid':os.getpid(),'started_utc':started},launcher)
            worker_observation=gates.ProcessObservation(actual['pid'])
            c.require(worker_observation.started_utc==actual['started_utc'],'Actual worker handle differs from handshake')
            receipt.update(child_pid=actual['pid'],child_started_utc=actual['started_utc'],
                worker_identity=actual,worker_identity_sha256=c.sha(handshake_path));c.write(path,receipt)
            code=process.wait()
        actual_code=worker_observation.exit_code()
        receipt.update(exit_code=actual_code,launcher_exit_code=code,finished_utc=c.utc())
        c.require(code==actual_code==0,'Actual DAC worker or launcher failed/is still running; retain outputs and stop')
        plan.unchanged()
        output=Path(config['profile_directory' if args.stage=='profile' else 'output_directory'])
        status=c.read(output/'status.json')
        c.require(status['status']=='completed' and status['pid']==actual['pid'] and status['started_utc']==actual['started_utc'],'Actual science worker completion identity mismatch')
        result=output/('profile.json' if args.stage=='profile' else 'checkpoint_manifest.json')
        receipt.update(status='completed',result_path=str(result),result_sha256=c.sha(result),
            status_sha256=c.sha(output/'status.json'),output_directory=str(output))
        c.write(path,receipt)
    except BaseException as error:
        receipt.update(status='failed',error=repr(error),failed_utc=c.utc())
        if process is not None:
            receipt['launcher_pid']=process.pid
            receipt['launcher_still_alive']=process.poll() is None
            # Never hide a still-running child behind a completion claim.
            if process.poll() is not None: receipt['launcher_exit_code']=process.returncode
            if worker_observation is not None:receipt['exit_code']=worker_observation.exit_code()
        c.write(path,receipt)
        raise
    finally:
        if worker_observation is not None:worker_observation.close()
        if launcher_observation is not None:launcher_observation.close()

def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage',choices=('profile','train'),required=True)
    for name in ('plan','plan-sha256','release-file','release-sha256'): p.add_argument('--'+name,required=True)
    for name in ('profile','profile-sha256','profile-receipt','profile-receipt-sha256'): p.add_argument('--'+name)
    p.add_argument('--child',action='store_true');p.add_argument('--parent-pid',type=int);p.add_argument('--parent-started-utc')
    p.add_argument('--worker-identity-file')
    return p
def main():
    args=parser().parse_args()
    if args.stage=='train': c.require(all(getattr(args,key) for key in ('profile','profile_sha256','profile_receipt','profile_receipt_sha256')),'Training requires the admitted resource proof and actual-exit receipt')
    if args.child:
        c.require(args.parent_pid and args.parent_started_utc and args.worker_identity_file,'Child requires actual supervising parent identity and handshake')
        child(args)
    else: supervise_one(args)
if __name__=='__main__': main()
