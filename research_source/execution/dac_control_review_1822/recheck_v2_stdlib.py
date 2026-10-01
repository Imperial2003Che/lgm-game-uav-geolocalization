"""Independent v2 recheck: stdlib/AST/mocks only. All fixtures live under this audit."""
import ast
from copy import deepcopy
import importlib.abc
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

OUT=Path(__file__).resolve().parent
V2=OUT.parent/'dac_training_control_v2'
FIX=OUT/'v2_fixtures';FIX.mkdir(exist_ok=True)
BLOCKED={'torch','torchvision','numpy','PIL','cv2','timm','albumentations','scipy','sklearn','transformers','tensorboard'}
ATTEMPTS=[];sys.dont_write_bytecode=True
class DenyScientific(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in BLOCKED:
            ATTEMPTS.append(fullname);raise RuntimeError('Real scientific import prohibited '+fullname)
sys.meta_path.insert(0,DenyScientific())
sys.path.insert(0,str(V2))
import dac2_contracts as c
import dac2_gates as gates
import run_dac_stage as stage
SOURCES={n:c.sha(V2/n) for n in ('dac2_contracts.py','dac2_gates.py','run_dac_stage.py','TRUSTED_CPU_EXECUTION.json')}
RESULTS=[]
def expect(value,message='assertion failed'):
    if not value:raise AssertionError(message)
def rejects(fn):
    try:fn()
    except (RuntimeError,ValueError,KeyError,TypeError,FileExistsError):return
    raise AssertionError('Expected rejection did not occur')
def check(name,fn,kind='contract_check'):
    try:RESULTS.append({'name':name,'passed':True,'kind':kind,'detail':fn()})
    except BaseException as error:RESULTS.append({'name':name,'passed':False,'kind':kind,'error':repr(error)})
def bound_file(name,value):
    path=FIX/name;c.write(path,value);return c.Bound.load(path,c.sha(path))

check('all v2 source AST parses without scientific import',lambda:[ast.parse((V2/n).read_text(encoding='utf-8')) and n for n in SOURCES if n.endswith('.py')])
check('frozen scientific source binding accepted',lambda:c.science_binding())
def real_cpu():
    proof=c.read(c.CPU_RESULT);refs=c.read(c.SCIENCE/'INPUT_REFERENCES.json')
    plan={**refs,'cpu_compatibility_proof':{'path':str(c.CPU_RESULT),'sha256':c.CPU_RESULT_SHA},'environment':proof['environment']}
    bound,artifacts=c.validate_cpu(plan)
    return {'result_sha256':bound.sha256,'artifact_count':len(artifacts),'execution':'read-only existing genuine proof and root exit receipt'}
check('actual CPU proof plus independent root exit receipt accepted',real_cpu,'read_only_positive')
def fake_cpu_rejected():
    proof=c.read(c.CPU_RESULT);refs=c.read(c.SCIENCE/'INPUT_REFERENCES.json')
    fake=bound_file('cpu_fixture.json',{'fixture_only':True,'status':'passed'})
    rejects(lambda:c.validate_cpu({**refs,'cpu_compatibility_proof':{'path':str(fake.path),'sha256':fake.sha256},'environment':proof['environment']}))
check('v1-style explicit mock CPU result rejected at genuine anchor',fake_cpu_rejected)
for value in (float('nan'),float('inf'),True,1.5):
    check('memory numeric contract rejects '+repr(value),lambda value=value:rejects(lambda:c.number(value,1,True)))
check('strict JSON rejects NaN',lambda:rejects(lambda:c.strict_json('{"peak":NaN}')))
check('strict JSON rejects Infinity',lambda:rejects(lambda:c.strict_json('{"peak":Infinity}')))
check('nested explicit fixture is rejected',lambda:rejects(lambda:c.no_fixture({'nested':{'fixture_only':True}})))

def fixture_profile():
    p={'actual_adamw_steps':2,'completed_optimizer_amp_steps':3,'amp_skips':1,
        'initial_parameter_sha256':'a'*64,'final_parameter_sha256':'b'*64,
        'representative_parameter':'model_1.convnext.downsample_layers.0.0.weight',
        'peak_allocated_bytes':100,'peak_reserved_bytes':200,'post_validation_peak_allocated_bytes':100,'post_validation_peak_reserved_bytes':200,'seconds_including_initialization':3.0,
        'final_scaler_state':{'scale':1024},'losses':[1.0,0.9,0.8]}
    batch=[];resource=[]
    for index,steps in enumerate((0,1,2),1):
        batch.append({'batch_attempt':index,'actual_optimizer_steps':steps,'amp_skips':index-steps,'optimizer_updated_this_batch':index>1,
            'loss_finite':True,'loss':p['losses'][index-1],'scale_after_update':1024,'lr_after_scheduler':0.001})
        resource.append({'batch_attempt':index,'actual_adamw_steps':steps,'amp_skips':index-steps,
            'peak_allocated_bytes':100,'peak_reserved_bytes':200,'allocated_bytes':80,'reserved_bytes':200,
            'seconds_including_data_and_synchronization':1.0})
    return p,batch,resource
def profile_test(mutate=None,accepted=True):
    p,b,r=fixture_profile()
    if mutate:mutate(p,b,r)
    if accepted:return c.profile_trace(p,b,r)
    rejects(lambda:c.profile_trace(p,b,r))
check('bounded profile allows one AMP skip plus two actual updates',lambda:profile_test())
check('trace rejects NaN peak',lambda:profile_test(lambda p,b,r:r[0].update(peak_allocated_bytes=float('nan')),False))
check('trace rejects Infinite summary',lambda:profile_test(lambda p,b,r:p.update(peak_allocated_bytes=float('inf')),False))
check('trace rejects smaller summary than trace',lambda:profile_test(lambda p,b,r:p.update(peak_allocated_bytes=1),False))
check('trace rejects unchanged parameter fingerprint',lambda:profile_test(lambda p,b,r:p.update(final_parameter_sha256=p['initial_parameter_sha256']),False))
check('trace rejects missing actual second update',lambda:profile_test(lambda p,b,r:p.update(actual_adamw_steps=1),False))
check('trace rejects false loss summary',lambda:profile_test(lambda p,b,r:p.update(losses=[0,0,0]),False))
check('summary differing from post-validation measurement rejected',lambda:profile_test(lambda p,b,r:p.update(peak_allocated_bytes=10000,peak_reserved_bytes=20000),False))
check('post-validation peak may exceed final batch after finite-state checks',lambda:profile_test(lambda p,b,r:p.update(peak_allocated_bytes=150,peak_reserved_bytes=250,post_validation_peak_allocated_bytes=150,post_validation_peak_reserved_bytes=250)))

def complete_profile_consumer(kind='valid'):
    stamp=c.utc().replace(':','').replace('.','')
    d=FIX/('profile_consumer_'+kind+'_'+stamp);d.mkdir()
    receipts=d/'receipts';receipts.mkdir()
    plan=bound_file('profile_consumer_plan_'+stamp+'.json',{'control_binding':{'audit_test_source':'not an admitted production binding'},'science_binding':{'audit_test_source':'not production'},
        'environment':{'audit_test_environment':'no scientific runtime'},'profile_directory':str(d),'profile_receipt_directory':str(receipts)})
    p,batch,resource=fixture_profile()
    p.update(schema='dac-native-resource-profile.v2',method='DAC',status='passed',plan_sha256=plan.sha256,
        control_binding=plan.value['control_binding'],science_binding=plan.value['science_binding'],
        nominal_batch_pairs=24,microbatch_pairs=24,gradient_accumulation=1,img_size=384,model_state_count=402,mixed_precision=True,
        loss_weights={'InfoNCE':1.0,'classification':0.1,'DSA':0.6},all_official_losses=True,oom=False,
        all_observed_losses_finite=True,all_model_floating_state_finite=True,all_optimizer_floating_state_finite=True,
        representative_parameter_changed=True,research_result=False,research_checkpoint_written=False,
        environment=plan.value['environment'],process_environment=c.PROCESS_ENV,optimizer_step_min=2,optimizer_step_max=2,pid=222,started_utc='2026-09-14T00:00:00+00:00')
    (d/'plan.json').write_bytes(plan.data)
    c.write(d/'serial_release.json',{'audit_contract_data_only':True})
    artifacts={'initial_parameter_evidence.json':{'sha256':p['initial_parameter_sha256'],'name':p['representative_parameter']},
        'dac_model_binding.json':{'tensor_count':402},'pretrained_binding.json':{'audit_contract_data_only':True},
        'dac_optimizer_initialization.json':{'weight_infonce':1.0,'weight_cls':0.1,'weight_dsa':0.6,'class':'torch.optim.adamw.AdamW'},
        'runtime_environment.json':{'audit_contract_data_only':True},'serial_release_gate.json':{'audit_contract_data_only':True},
        'stage_bindings.json':{'plan_sha256':plan.sha256,'release_sha256':c.sha(d/'serial_release.json')},
        'code_manifest.json':{'science':plan.value['science_binding'],'control':plan.value['control_binding']},
        'environment_manifest.json':plan.value['environment'],'epoch01_sampling.json':{'audit_contract_data_only':True},
        'final_resource_measurement.json':{'phase':'after_finite_state_validation','pid':222,'plan_sha256':plan.sha256,'peak_allocated_bytes':100,'peak_reserved_bytes':200}}
    if kind=='wrong_phase':artifacts['final_resource_measurement.json']['phase']='before_initialization'
    if kind=='wrong_final_peak':artifacts['final_resource_measurement.json']['peak_allocated_bytes']=99
    for name,value in artifacts.items():c.write(d/name,value)
    for name,rows in [('batch_progress.jsonl',batch),('resource_batches.jsonl',resource)]:
        (d/name).write_text(''.join(json.dumps(row)+'\n' for row in rows),encoding='utf-8')
    p['evidence_sha256']={path.name:c.sha(path) for path in d.iterdir() if path.is_file()}
    c.write(d/'profile.json',p);bound=c.Bound.load(d/'profile.json',c.sha(d/'profile.json'))
    receipt={'schema':'dac-stage-lifecycle.v2','stage':'profile','status':'completed','exit_code':0,'plan_sha256':plan.sha256,'result_sha256':bound.sha256,
        'child_pid':222,'child_started_utc':p['started_utc']}
    if kind=='wrong_worker':receipt['child_pid']=999
    if kind=='wrong_result_hash':receipt['result_sha256']='f'*64
    c.write(receipts/'lifecycle.json',receipt);receipt_bound=c.Bound.load(receipts/'lifecycle.json',c.sha(receipts/'lifecycle.json'))
    checked=[]
    def fn():
        with patch.object(c,'science_binding',return_value=plan.value['science_binding']),patch.object(c,'control_binding',return_value=plan.value['control_binding']):
            return c.validate_profile(bound,plan,receipt_bound,lambda value:checked.append(value))
    if kind=='valid':
        result=fn();expect(len(checked)==1)
        return {'trace':result,'actual_exit_checker_invoked':True,'scope':'isolated consumer contract fixture; fake code/environment bindings cannot pass production validate_plan'}
    rejects(fn)
check('full profile consumer accepts coherent captured artifacts and lifecycle contract',complete_profile_consumer)
for kind in ('wrong_phase','wrong_final_peak','wrong_worker','wrong_result_hash'):
    check('full profile consumer rejects '+kind,lambda kind=kind:complete_profile_consumer(kind))

def bound_mutation():
    original=bound_file('mutable_plan.json',{'seed':1})
    copy_path=FIX/'frozen_plan.json'
    if copy_path.exists():
        # Overwrite fixture through a new unique path; no deletion needed.
        copy_path=FIX/('frozen_plan_'+c.utc().replace(':','').replace('.','')+'.json')
    copied=original.copy(copy_path)
    c.write(original.path,{'seed':3})
    expect(original.value==copied.value=={'seed':1})
    rejects(original.unchanged);copied.unchanged()
    c.write(copied.path,{'seed':2});rejects(copied.unchanged)
check('Bound keeps admitted bytes and rejects external or snapshot mutation',bound_mutation)

START='2026-09-14T00:00:00+00:00';FINISH='2026-09-14T00:10:00+00:00'
def lifecycle(actual,finish=FINISH):
    value={'status':'completed','pid':101,'started_utc':START,'exit_code':0}
    if finish is not None:value['finished_utc']=finish
    with patch.object(gates,'process_started',return_value=actual):return gates.exited(value)
check('absent preceding PID accepted',lambda:lifecycle(None))
check('same live owner rejected',lambda:rejects(lambda:lifecycle(START)))
check('slow spawn before recorded finish remains blocked',lambda:rejects(lambda:lifecycle('2026-09-14T00:05:00+00:00')))
check('live PID without finish never treated as reused',lambda:rejects(lambda:lifecycle('2026-09-14T00:20:00+00:00',None)))
check('PID created strictly after recorded finish counts as reused',lambda:lifecycle('2026-09-14T00:20:00+00:00'))
check('PID created exactly at finish remains blocked',lambda:rejects(lambda:lifecycle(FINISH)))
check('missing owner timezone rejected',lambda:rejects(lambda:list(gates.owners({'pid':101,'started_utc':'2026-09-14T00:00:00'}))))
for value in ({'status':'completed','commands':[{'status':'failed','exit_code':1}]},
              {'status':'completed','commands':[{'nested':{'returncode':1}}]},
              {'status':'completed','jobs':[{'status':'running'}]}):
    check('recursive failed or active execution rejected '+str(value),lambda value=value:rejects(lambda:gates.reject_failed_records(value)))
for row in ('101, python.exe','102, train_native.exe','103, julia.exe','104, [Not Found]'):
    check('all GPU process executables rejected: '+row,lambda row=row:rejects(lambda:gates.gpu_empty(row)))
check('empty GPU output accepted',lambda:gates.gpu_empty('\n'))

def serial_five(include_fifth=True):
    names={'status.json':'completed','pipeline_status.json':'ready_for_extension_preparation','extension_status.json':'registered_extensions_finished_review_pending',
        'latest_baseline_status.json':'latest_baselines_finished_review_pending','independent_comparison_status.json':'independent_comparisons_finished_review_pending'}
    job=lambda ident:{'id':ident,'status':'completed','exit_code':0}
    plans={'extension_plan.json':{'jobs':[job('e'+str(i)) for i in range(4)]},'latest_baseline_plan.json':{'jobs':[job('l'+str(i)) for i in range(2)]},'independent_comparison_plan_v2.json':{'jobs':[job('i'+str(i)) for i in range(3)]}}
    hashes={n:c.digest(json.dumps(v).encode()) for n,v in plans.items()}
    hashes['independent_comparison_plan_v2.json']='a5318f7a60497cc7c9ccb74b7cd82ef7f71fcb072c36a90fb192ea27acc6ca49'
    states={};rows=[]
    pipeline=['formal_aggregate','formal_figures','cross_dataset_transfer','robustness','robustness_aggregate','query_analysis','formal_efficiency_component']
    for n,status in names.items():
        if n.startswith('independent') and not include_fifth:continue
        state={'status':status,'pid':101,'started_utc':START,'finished_utc':FINISH}
        row={'status_path':str(c.EXECUTION/n),'status_sha256':'d'*64,'required_status':status}
        if n=='status.json':state['stage']='all'
        elif n=='pipeline_status.json':state['jobs']=[job(x) for x in pipeline]
        else:
            plan_name={'extension_status.json':'extension_plan.json','latest_baseline_status.json':'latest_baseline_plan.json','independent_comparison_status.json':'independent_comparison_plan_v2.json'}[n]
            state.update(jobs=plans[plan_name]['jobs'],plan_sha256=hashes[plan_name]);row['plan_sha256']=hashes[plan_name]
        states[n]=state;rows.append(row)
    plan=bound_file('five_plan.json',{'control_binding':{'x':1},'science_binding':{'y':1}})
    release=bound_file('five_release.json',{'schema':'dac-serial-release.v2','allow_cuda':True,'plan_sha256':plan.sha256,'stages':['profile'],'control_binding':{'x':1},'science_binding':{'y':1},'predecessors':rows})
    def mock_bound(path,expected):
        name=Path(path).name
        value=states.get(name,plans.get(name))
        expect(value is not None)
        return c.Bound(Path(path),json.dumps(value).encode(),expected)
    with patch.object(c.Bound,'load',side_effect=mock_bound),patch.object(c.Bound,'unchanged'),patch.object(gates,'process_started',return_value=None),patch.object(gates.subprocess,'run',return_value=SimpleNamespace(stdout='')):
        if include_fifth:
            report=gates.serial_gate(plan,release,'profile');expect(len(report['predecessors'])==5);return {'prerequisite_count':5,'process_and_files':'explicit mocks'}
        rejects(lambda:gates.serial_gate(plan,release,'profile'))
check('five complete prerequisite mock paths are reachable',lambda:serial_five(True))
check('missing fifth independent-comparison stage rejected',lambda:serial_five(False))

def observer_mock():
    log=[]
    class Base:
        def __init__(self,config,plan_path,profile_path):self.actual_optimizer_steps=0;self.amp_skips=0;self.plan_path=plan_path;self.profile_path=profile_path
        def before_epoch(self,*a):log.append('official_before_epoch')
        def after_batch(self,n):log.append(('official_after_batch',n));self.amp_skips=n-self.actual_optimizer_steps
        def save_complete(self,ns):log.append('official_save_complete')
    output=FIX/'observer';output.mkdir(exist_ok=True)
    cuda=SimpleNamespace(synchronize=lambda:log.append('synchronize'),max_memory_allocated=lambda:100,max_memory_reserved=lambda:200,memory_allocated=lambda:80,memory_reserved=lambda:200)
    session=SimpleNamespace(config={},output=output,args=SimpleNamespace(stage='profile'),modules={'dac_train_runtime':SimpleNamespace(DACTrainRun=Base)})
    run=stage.make_run(session,SimpleNamespace(cuda=cuda));run.before_epoch(1,None)
    run.after_batch(1)
    run.actual_optimizer_steps=1;run.after_batch(2)
    run.actual_optimizer_steps=2
    try:run.after_batch(3)
    except stage.ProfileComplete:pass
    else:raise AssertionError('Profile did not terminate after second actual step')
    expect([x for x in log if isinstance(x,tuple)]==[('official_after_batch',1),('official_after_batch',2),('official_after_batch',3)])
    rejects(lambda:run.save_complete({}))
    return {'observed_callbacks':3,'actual_steps':2,'amp_skip':1,'all_objects':'stdlib mocks; no real optimizer or CUDA'}
check('profile observer calls original bookkeeping before two-update termination',observer_mock)
check('profile rejects 32 attempts without two updates',lambda:rejects(lambda:stage.profile_decision(1,32)))
check('profile allows 31 attempts with one update while waiting for second',lambda:expect(stage.profile_decision(1,31)=='continue'))

def snapshot_save_mock():
    log=[];output=FIX/'training_snapshot';output.mkdir(exist_ok=True)
    class Base:
        def __init__(self,config,plan_path,profile_path):self.plan_path=plan_path;self.profile_path=profile_path
        def save_complete(self,namespace):log.append('save');c.write(output/'status.json',{'status':'completed','epoch_completed':1})
    session=SimpleNamespace(config={},output=output,args=SimpleNamespace(stage='train'),modules={'dac_train_runtime':SimpleNamespace(DACTrainRun=Base)},unchanged=lambda:log.append('unchanged'))
    run=stage.make_run(session,SimpleNamespace());run.save_complete({})
    expect(log==['unchanged','save','unchanged'])
    expect(run.plan_path==output/'plan.json' and run.profile_path==output/'resource_profile.json')
    return {'plan_path':'internal plan.json','profile_path':'internal resource_profile.json','check_order':log}
check('real subclass save path uses internal snapshots and before/after integrity checks',snapshot_save_mock)

def root_windows_identity():
    path=OUT/'REAL_WINDOWS_LAUNCHER_IDENTITY.json'
    expect(c.sha(path)=='b34a2869b11bd64000993a496555f1f8e7dd19a7742bed4a4516e2c72f7b2ed5')
    proof=c.read(path)
    expect(proof['exit_code']==0 and proof['popen_pid']!=proof['actual_child']['pid'])
    expect(proof['actual_child']['parent_pid']==proof['popen_pid'] and proof['scientific_imports']==[])
    return {'source_sha256':c.sha(path),'launcher_pid':proof['popen_pid'],'worker_pid':proof['actual_child']['pid'],'root_actual_execution':'stdlib only; not re-executed by this reviewer'}
check('real Windows launcher differs from actual worker identity',root_windows_identity,'read_only_reachability_evidence')

def root_windows_api_smoke():
    path=OUT/'REAL_PROCESS_API_SMOKE_1822.json'
    expect(c.sha(path)=='b36f0762835cca5934293f9a86388f9be73079e1834d07fe5cceed282a9f5cad')
    proof=c.read(path)
    expect(proof['status']=='passed' and proof['scientific_imports']==[] and proof['gpu_api_called'] is False)
    expect(proof['script_sha256']==c.sha(OUT/'smoke_windows_process_api_1822.py'))
    expect(all(c.sha(V2/name)==digest for name,digest in proof['source_files_sha256'].items()))
    expect(len(proof['cases'])==2 and {row['expected_exit_code'] for row in proof['cases']}=={0,7})
    for row in proof['cases']:
        expect(row['launcher_exit_code']==row['actual_worker_exit_code']==row['expected_exit_code'])
        expect(row['retained_handle_verified_running_then_actual_exit'] is True and row['distinct_launcher_and_worker'] is True)
        expect(row['actual_worker_identity']['lineage'][1]['pid']==row['popen_pid'])
    return {'sha256':c.sha(path),'actual_cases':[0,7],'source_hashes_match':True,'reviewer_did_not_launch_process':True}
check('root real retained Win32 handles verify distinct workers and actual exit codes',root_windows_api_smoke,'read_only_reachability_evidence')

def supervisor_launcher_repro(actual_exit=0):
    stamp=c.utc().replace(':','').replace('.','')
    d=FIX/('launcher_repro_'+stamp);d.mkdir()
    output=d/'worker';output.mkdir()
    receipt=d/'receipt'
    config={'control_binding':{'control':'mock'},'science_binding':{'science':'mock'},
        'environment':{'executable':sys.executable},'process_environment':c.PROCESS_ENV,
        'profile_directory':str(output),'profile_receipt_directory':str(receipt)}
    plan=bound_file('launcher_plan_'+stamp+'.json',config)
    release=bound_file('launcher_release_'+stamp+'.json',{'test_data_only':True})
    args=SimpleNamespace(plan=str(plan.path),plan_sha256=plan.sha256,release_file=str(release.path),release_sha256=release.sha256,stage='profile')
    class Launcher:
        pid=15488;returncode=0;_handle=154880
        def __init__(self):
            handshake={'schema':'dac-actual-worker-identity.v2','pid':38232,'started_utc':'2026-09-14T00:00:01+00:00',
                'plan_sha256':plan.sha256,'release_sha256':release.sha256,
                'lineage':[{'pid':38232,'started_utc':'2026-09-14T00:00:01+00:00','parent_process_id':15488},
                    {'pid':15488,'started_utc':START,'parent_process_id':stage.os.getpid()},
                    {'pid':stage.os.getpid(),'started_utc':START,'parent_process_id':999}]}
            c.write(receipt/'worker_identity.json',handshake)
        def wait(self):
            c.write(output/'status.json',{'status':'completed','pid':38232,'started_utc':'2026-09-14T00:00:01+00:00'})
            c.write(output/'profile.json',{'test_data_only':True})
            return 0
        def poll(self):return 0
    class Observation:
        def __init__(self,pid,existing_handle=None):self.pid=pid;self.started_utc='2026-09-14T00:00:01+00:00' if pid==38232 else START
        def exit_code(self):return actual_exit if self.pid==38232 else 0
        def close(self):pass
    with patch.object(c,'control_binding',return_value=config['control_binding']),patch.object(c,'science_binding',return_value=config['science_binding']),patch.object(gates,'process_started',return_value=START),patch.object(gates,'ProcessObservation',Observation),patch.object(stage.subprocess,'Popen',side_effect=lambda *a,**k:Launcher()):
        if actual_exit==0:stage.supervise_one(args)
        else:rejects(lambda:stage.supervise_one(args))
    lifecycle=c.read(receipt/'lifecycle.json')
    expect(lifecycle['status']==('completed' if actual_exit==0 else 'failed') and lifecycle['exit_code']==actual_exit)
    expect(lifecycle['launcher_pid']==15488 and lifecycle['child_pid']==38232)
    return {'status':lifecycle['status'],'worker_exit_code':actual_exit,'launcher_exit_code':0,'launcher_pid':15488,'actual_worker_pid':38232,'execution':'stdlib subprocess/handle mocks shaped to independently observed Windows launcher'}
check('successful different launcher/worker PID admitted by complete supervisor function',supervisor_launcher_repro)
check('zero launcher exit cannot conceal failed actual worker',lambda:supervisor_launcher_repro(1))
check('zero launcher exit cannot conceal still-active actual worker',lambda:supervisor_launcher_repro(259))

def ancestry_case(mutation=None):
    supervisor={'pid':10,'started_utc':START};launcher={'pid':11,'started_utc':START}
    value={'schema':'dac-actual-worker-identity.v2','pid':12,'started_utc':START,'plan_sha256':'a'*64,'release_sha256':'b'*64,
        'lineage':[{'pid':12,'started_utc':START,'parent_process_id':11},{'pid':11,'started_utc':START,'parent_process_id':10},{'pid':10,'started_utc':START,'parent_process_id':1}]}
    if mutation:
        mutation(value);rejects(lambda:gates.validate_worker_identity(value,'a'*64,'b'*64,supervisor,launcher))
    else:gates.validate_worker_identity(value,'a'*64,'b'*64,supervisor,launcher)
check('actual worker-launcher-supervisor three-part ancestry accepted',ancestry_case)
check('missing launcher in worker ancestry rejected',lambda:ancestry_case(lambda v:v['lineage'][1].update(pid=99)))
check('wrong worker creation identity rejected',lambda:ancestry_case(lambda v:v.update(started_utc=FINISH)))
check('broken worker parent link rejected',lambda:ancestry_case(lambda v:v['lineage'][0].update(parent_process_id=99)))

def static_execution():
    tree=ast.parse((V2/'run_dac_stage.py').read_text())
    child=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='child')
    calls=[(ast.unparse(n.func),n.lineno) for n in ast.walk(child) if isinstance(n,ast.Call)]
    lin=lambda name:min(line for name_,line in calls if name_==name)
    expect(lin('gates.serial_gate')<lin('session.modules[\'input_audit\'].runtime_environment') if any(n=="session.modules['input_audit'].runtime_environment" for n,l in calls) else False)
    imports=[n.lineno for n in ast.walk(child) if isinstance(n,ast.Import) and any(x.name=='torch' for x in n.names)]
    expect(len(imports)==1 and lin('gates.serial_gate')<imports[0]<lin('runpy.run_path'))
    pathcalls=[n for n in ast.walk(child) if isinstance(n,ast.Call) and ast.unparse(n.func)=='runpy.run_path']
    expect(len(pathcalls)==2 and all('train_university_train_only.py' in ast.unparse(n) and "run_name='__main__'" in ast.unparse(n) for n in pathcalls))
    afters=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='after_batch']
    forbidden={'backward','step','update','zero_grad'}
    expect(not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in forbidden for n in ast.walk(afters[0])))
    original=ast.parse((c.SCIENCE/'scientific_source/sample4geo/trainer.py').read_text(encoding='utf-8'))
    expect(any(isinstance(n,ast.Call) and ast.unparse(n.func)=='scheduler.step' for n in ast.walk(original)))
    return {'gate_line':lin('gates.serial_gate'),'torch_import_line':imports[0],'entry_line':lin('runpy.run_path'),'original_entry_paths':2,'observer_calls_no_scientific_update':True}
check('frozen official scientific entry reached only after lock/gate; observers never step optimizer',static_execution)
check('no scientific import executed or attempted',lambda:expect(not ATTEMPTS and not BLOCKED.intersection(sys.modules)))
CURRENT={n:c.sha(V2/n) for n in SOURCES}
report={'schema':'dac-v2-independent-control-recheck.v1','generated_utc':c.utc(),'checks':RESULTS,'passed':sum(x['passed'] for x in RESULTS),'total':len(RESULTS),
    'initial_source_sha256':SOURCES,'final_source_sha256':CURRENT,'author_files_changed_during_test':CURRENT!=SOURCES,
    'scientific_import_attempts':ATTEMPTS,'actual_scientific_execution':False,'reviewer_modified_author_source':False}
c.write(OUT/'V2_RECHECK.json',report)
print(json.dumps({'passed':report['passed'],'total':report['total'],'failures':[x for x in RESULTS if not x['passed']],'source_changed':CURRENT!=SOURCES}))
if report['passed']!=report['total']:raise SystemExit(1)
