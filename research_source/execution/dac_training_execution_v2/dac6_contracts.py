"""Small six-stage orchestration contracts; scientific code remains frozen DAC v2."""
import hashlib
import importlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
EXECUTION=HERE.parent
CONTROL=EXECUTION/'dac_training_control_v2'
INPUTS=EXECUTION/'dac_training_inputs_v2'
CONTROL_SHA='09211d0e9871eaa5cd22df2edeb500e30c783867dfe375947a8d3213e7e878ec'
INPUT_SHA='0052a0e96f8124e1f0978fb574e4535207e2539acb75ec4f45eedc2f424dfc4f'
ORDER=[f'seed_{seed}_{stage}' for seed in (1,2,3) for stage in ('profile','train')]

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def require(condition,message):
    if not condition:raise RuntimeError(message)
def pin_package(root,expected):
    path=root/('INPUT_PREPARATION_MANIFEST.json' if root==INPUTS else 'PREPARATION_MANIFEST.json')
    require(sha(path)==expected,'Frozen package manifest changed: '+str(root))
    data=json.loads(path.read_bytes())
    for row in data['files']:
        target=(root/row['path']).resolve()
        require(target.is_relative_to(root) and sha(target)==row['sha256'],'Frozen payload changed: '+str(target))
    return data

pin_package(CONTROL,CONTROL_SHA)
sys.path.insert(0,str(CONTROL))
for name in ('dac2_contracts','dac2_gates','run_dac_stage'):
    if name in sys.modules:require(Path(sys.modules[name].__file__).resolve()==CONTROL/(name+'.py'),'Conflicting frozen control module')
c=importlib.import_module('dac2_contracts')
g=importlib.import_module('dac2_gates')

def own_manifest():
    path=HERE/'PREPARATION_MANIFEST.json';data=c.read(path)
    for row in data['files']:
        target=(HERE/row['path']).resolve()
        require(target.is_relative_to(HERE) and sha(target)==row['sha256'],'Six-stage execution source changed')
    return sha(path)

def spec_bound(path,expected):
    bound=c.Bound.load(path,expected);spec=bound.value;c.no_fixture(spec)
    require(spec['schema']=='dac-six-stage-execution-spec.v2' and [row['id'] for row in spec['jobs']]==ORDER,'Wrong fixed six-stage order')
    require(spec['control_manifest_sha256']==CONTROL_SHA and spec['input_manifest_sha256']==INPUT_SHA,'Frozen package identity mismatch')
    require(spec['process_environment']==c.PROCESS_ENV,'Executor process environment differs from original prepared DAC environment')
    pin_package(CONTROL,CONTROL_SHA);inputs=pin_package(INPUTS,INPUT_SHA)
    plans={row['seed']:row for row in inputs['seeds']}
    for row in spec['jobs']:
        seed,stage=row['seed'],row['stage'];require(row['id']==f'seed_{seed}_{stage}','Stage ID mismatch')
        reference=plans[seed]
        require(row['plan_path']==reference['plan_path'] and row['plan_sha256']==reference['plan_sha256'],'Seed plan differs from sealed inputs')
        plan=c.Bound.load(row['plan_path'],row['plan_sha256']).value
        require(row['output_directory']==plan['profile_directory' if stage=='profile' else 'output_directory'],'Planned stage output changed')
        require(row['control_receipt_path']==str(Path(plan['profile_receipt_directory' if stage=='profile' else 'training_receipt_directory'])/'lifecycle.json'),'Control receipt path changed')
    require(Path(spec['status_path']).resolve()==HERE/'runtime/status.json' and Path(spec['completion_path']).resolve()==HERE/'runtime/completion_manifest.json','Execution status escaped its separate runtime directory')
    return bound

def release_bound(path,expected,spec):
    bound=c.Bound.load(path,expected);value=bound.value;c.no_fixture(value)
    require(value['schema']=='dac-six-stage-release.v2' and value['allow_run'] is True,'No explicit later serial execution release')
    require(value['execution_spec_sha256']==spec.sha256 and value['execution_manifest_sha256']==own_manifest(),'Release does not admit these exact executor bytes')
    require(value['stage_order']==ORDER and value.get('predecessors'),'Release lacks the exact sequence or five preceding stages')
    required={'status.json','pipeline_status.json','extension_status.json','latest_baseline_status.json','independent_comparison_status.json'}
    require({Path(x['status_path']).resolve() for x in value['predecessors']}=={EXECUTION/x for x in required} and len(value['predecessors'])==5,'Release must bind exactly the five registered predecessors')
    return bound

def serial_release(plan,root_release,stage):
    return {'schema':'dac-serial-release.v2','allow_cuda':True,'plan_sha256':plan.sha256,
        'stages':[stage],'control_binding':plan.value['control_binding'],'science_binding':plan.value['science_binding'],
        'predecessors':root_release.value['predecessors']}

def stage_directory(identifier):
    require(identifier in ORDER,'Unknown stage')
    return HERE/'runtime/stages'/identifier

def request_bound(path,expected):
    request=c.Bound.load(path,expected);value=request.value;c.no_fixture(value)
    require(value['schema']=='dac-six-stage-request.v2','Wrong stage request schema')
    spec=spec_bound(value['execution_spec_path'],value['execution_spec_sha256'])
    release=release_bound(value['root_release_path'],value['root_release_sha256'],spec)
    row=next(x for x in spec.value['jobs'] if x['id']==value['id'])
    require(Path(path).resolve()==stage_directory(row['id'])/'request.json','Stage request escaped fixed directory')
    plan=c.Bound.load(row['plan_path'],row['plan_sha256'])
    inner=c.Bound.load(value['serial_release_path'],value['serial_release_sha256'])
    require(inner.value==serial_release(plan,release,row['stage']),'Inner serial release differs from root admission')
    require(inner.path==stage_directory(row['id'])/'serial_release.json','Inner release path escaped stage')
    if row['stage']=='train':
        pair=value['profile_binding'];require(set(pair)=={'profile_sha256','receipt_sha256'},'Bad late-bound profile schema')
        c.validate_profile(c.Bound.load(Path(plan.value['profile_directory'])/'profile.json',pair['profile_sha256']),plan,
            c.Bound.load(Path(plan.value['profile_receipt_directory'])/'lifecycle.json',pair['receipt_sha256']),g.exited)
    else:require(value.get('profile_binding') is None,'Profile must start from original initialization, not a previous profile')
    return request,spec,release,row,plan,inner

def artifact(path):
    path=Path(path).resolve()
    return {'path':str(path),'sha256':sha(path),'bytes':path.stat().st_size}

def bound_artifact(row):
    path=Path(row['path']).resolve()
    require(path.stat().st_size==row['bytes'] and sha(path)==row['sha256'],'Completed artifact changed: '+str(path))
    return path

def stage_owners_exited(job):
    # The recorded ancestry reaches the current coordinator while running. Check
    # just this stage's observed launcher and actual supervisor here; the final
    # completion API separately checks the coordinator and all nested owners.
    return g.exited({'status':'completed','finished_utc':job['finished_utc'],
        'launcher_pid':job['launcher_pid'],'launcher_started_utc':job['launcher_started_utc'],
        'launcher_exit_code':job['launcher_exit_code'],
        'supervisor_pid':job['supervisor_pid'],'supervisor_started_utc':job['supervisor_started_utc'],
        'supervisor_exit_code':job['supervisor_exit_code']})

def verify_training_artifacts(plan_bound,receipt_bound):
    plan=plan_bound.value;root=Path(plan['output_directory']).resolve()
    receipt=receipt_bound.value
    require(receipt['stage']=='train' and receipt['status']=='completed' and type(receipt['exit_code']) is int and receipt['exit_code']==0,'Training did not produce an actual exit0 receipt')
    require(receipt['plan_sha256']==plan_bound.sha256 and Path(receipt['output_directory']).resolve()==root,'Training receipt belongs to a different plan/output')
    g.exited(receipt)
    status=c.read(root/'status.json')
    require(status['status']=='completed' and status['epoch_completed']==1 and status['pid']==receipt['child_pid'] and status['started_utc']==receipt['child_started_utc'],'Training final epoch/actual worker identity mismatch')
    require(receipt['status_sha256']==sha(root/'status.json'),'Training status changed after actual parent receipt')
    manifest=c.read(root/'checkpoint_manifest.json')
    require(receipt['result_sha256']==sha(root/'checkpoint_manifest.json'),'Training checkpoint manifest changed')
    require(set(manifest)=={'weights_end.pth','checkpoint_complete.pth'},'Both actual final weights and full recovery checkpoint are required')
    evidence=c.read(root/'training_evidence.json');protocol=c.read(root/'dac_training_protocol_evidence.json')
    for value in (receipt,status,evidence,protocol):c.no_fixture(value)
    actual=c.number(evidence['actual_adamw_steps'],1,True);attempts=c.number(evidence['attempted_batches'],actual,True)
    require(evidence['amp_skips']==attempts-actual and status['actual_adamw_steps']==actual and status['optimizer_step_attempts']==attempts and status['amp_skips']==attempts-actual,'Final actual AdamW/AMP accounting mismatch')
    require(c.number(evidence['epoch_loss']) is not None and evidence['all_model_floating_state_finite'] is True,'Missing finite real training evidence')
    require(c.is_sha(evidence['initial_parameter_sha256']) and c.is_sha(evidence['final_parameter_sha256']) and evidence['initial_parameter_sha256']!=evidence['final_parameter_sha256'],'No actual parameter byte change')
    require(evidence['representative_parameter_changed'] is True and evidence['final_scaler_state'],'Incomplete optimizer/scaler evidence')
    require(protocol['method']=='DAC' and protocol['model_state_count']==402 and protocol['epoch']==1 and protocol['actual_adamw_steps']==actual,'Final protocol is not the declared DAC run')
    require(protocol['actual_loader_batches']==protocol['scheduler_attempts']==attempts and protocol['optimizer_step_max']==actual and protocol['all_optimizer_moments_finite'] is True and protocol['amp_skips']==attempts-actual,'Scheduler/optimizer completion evidence mismatch')
    require(protocol['test_set_read_or_model_selection'] is False,'Training evidence reports test-set selection')
    require(protocol['scheduler_steps_planned_before_shuffle']==1578 and protocol['warmup_steps_planned_before_shuffle']==157.8,'Original pre-shuffle scheduler plan changed')
    sampling=c.read(root/'epoch01_sampling.json');order=c.read(root/'epoch01_sample_order.json')
    require(sampling['official_pair_count']==37854 and sampling['nominal_pairs_per_batch']==24 and sampling['expected_batches']==attempts,'Official full pair set or original loader completion differs')
    require(sampling['sample_count']==len(order)==attempts*24 and sampling['excluded_tail_pairs']==37854-len(order) and sampling['sample_order_sha256']==sha(root/'epoch01_sample_order.json'),'Saved sampler sequence does not match completed batches')
    require(0<len(order)<=37854 and all(len({x[0] for x in order[i:i+24]})==24 for i in range(0,len(order),24)),'Original unique-place batch invariant failed')
    batches=[c.strict_json(line) for line in (root/'batch_progress.jsonl').read_bytes().splitlines()]
    require(len(batches)==attempts,'Not all actual batch updates were recorded')
    previous=0
    for i,batch in enumerate(batches,1):
        count=c.number(batch['actual_optimizer_steps'],0,True)
        require(batch['epoch']==1 and batch['batch_attempt']==i and count-previous in (0,1) and batch['optimizer_updated_this_batch'] is bool(count-previous),'Invalid original per-batch optimizer hook trace')
        require(batch['amp_skips']==i-count and batch['loss_finite'] is True,'AMP accounting/finite loss trace differs')
        c.number(batch['loss']);c.number(batch['scale_after_update'],0);c.number(batch['lr_after_scheduler'],0)
        require(batch['scale_after_update']>0,'Invalid AMP scale')
        previous=count
    require(previous==actual and c.read(root/'initial_parameter_evidence.json')['sha256']==evidence['initial_parameter_sha256'],'Final optimizer count or original parameter digest differs from trace')
    require(c.number(evidence['final_scaler_state']['scale'],0)==batches[-1]['scale_after_update'],'Final AMP scale differs from actual post-update trace')
    require(sha(root/'plan.json')==plan_bound.sha256 and sha(root/'data_manifest.json')==plan['data_manifest_sha256'],'Training used different immutable input bytes')
    require(c.read(root/'code_manifest.json')=={'science':plan['science_binding'],'control':plan['control_binding']} and c.read(root/'environment_manifest.json')==plan['environment'],'Training source/environment lineage mismatch')
    expected_effective=INPUTS/f"seed_{plan['seed']}_effective_configuration.json"
    require(c.read(root/'effective_configuration.json')==c.read(expected_effective),'Effective configuration differs from prepared actual seed config')
    values={}
    for name in ('weights_end.pth','checkpoint_complete.pth'):
        entry=artifact(root/name)
        require(entry['bytes']==manifest[name]['bytes'] and entry['sha256']==manifest[name]['sha256'],'Actual final checkpoint bytes differ from manifest')
        values[name]=entry
    for name in ('checkpoint_manifest.json','training_evidence.json','dac_training_protocol_evidence.json',
        'status.json','plan.json','data_manifest.json','code_manifest.json','environment_manifest.json',
        'runtime_environment.json','effective_configuration.json','epoch01_sampling.json','epoch01_sample_order.json',
        'stage_bindings.json','serial_release.json','serial_release_gate.json','resource_profile.json','resource_profile_lifecycle.json',
        'batch_progress.jsonl','initial_parameter_evidence.json','dac_optimizer_initialization.json','dac_model_binding.json'):
        values[name]=artifact(root/name)
    return {'epoch_completed':1,'actual_adamw_steps':actual,'attempted_batches':attempts,
        'amp_skips':attempts-actual,'model_state_count_from_pinned_runtime':402,
        'tensor_values_independently_loaded':False,'files':values}

def verify_execution_evidence(row,record,receipt):
    files=record['execution_evidence'];base=stage_directory(row['id']);inner_dir=Path(row['control_receipt_path']).parent
    paths={'request':base/'request.json','serial_release':base/'serial_release.json',
        'worker_identity':base/'worker_identity.json','parent_observed':base/'parent_observed.json',
        'supervisor_stdout':base/'supervisor_stdout.log','supervisor_stderr':base/'supervisor_stderr.log',
        'science_stdout':Path(row['output_directory'])/'stdout.log','science_stderr':Path(row['output_directory'])/'stderr.log',
        'inner_stdout':inner_dir/'child_stdout.log','inner_stderr':inner_dir/'child_stderr.log',
        'inner_identity':inner_dir/'worker_identity.json','inner_lifecycle':inner_dir/'lifecycle.json'}
    require(set(files)==set(paths),'Missing closed log or real lifecycle artifact')
    for name,path in paths.items():require(bound_artifact(files[name])==path.resolve(),'Execution evidence path mismatch')
    request,spec,release,admitted,plan,serial=request_bound(files['request']['path'],files['request']['sha256'])
    require(admitted==row and request.value['controller_pid']==record['controller_pid'] and request.value['controller_started_utc']==record['controller_started_utc'],'Stage coordinator admission differs')
    require(files['serial_release']['sha256']==serial.sha256==receipt.value['release_sha256'],'Serial release hash differs from actual child receipt')
    identity=c.read(paths['worker_identity'])
    g.validate_worker_identity(identity,plan.sha256,serial.sha256,
        {'pid':record['controller_pid'],'started_utc':record['controller_started_utc']},
        {'pid':record['launcher_pid'],'started_utc':record['launcher_started_utc']})
    require(identity['pid']==record['supervisor_pid'] and identity['started_utc']==record['supervisor_started_utc'],'Observed stage parent differs from handshake')
    observed=c.read(paths['parent_observed'])
    require(observed=={'request_sha256':request.sha256,'worker_identity_sha256':files['worker_identity']['sha256'],
        'controller_pid':record['controller_pid'],'controller_started_utc':record['controller_started_utc']},'Stage began without admitted actual-worker observation')
    require(receipt.value['worker_identity_sha256']==files['inner_identity']['sha256'] and files['inner_lifecycle']['sha256']==receipt.sha256,'Inner actual identity/lifecycle bytes changed')
    output=Path(row['output_directory']);bindings=c.read(output/'stage_bindings.json')
    require(bindings['plan_sha256']==plan.sha256 and bindings['release_sha256']==serial.sha256 and sha(output/'serial_release.json')==serial.sha256,'Science process used different immutable plan/release')
    if row['stage']=='train':
        require(request.value['profile_binding']==record['profile_binding'],'Training late-bound profile differs from launch request')
        require(bindings['profile_sha256']==record['profile_binding']['profile_sha256'] and bindings['profile_receipt_sha256']==record['profile_binding']['receipt_sha256'],'Science process used a different resource profile')
    gate=c.read(output/'serial_release_gate.json')
    require(gate['schema']=='dac-current-serial-allocation.v2' and gate['stage']==row['stage'] and gate['plan_sha256']==plan.sha256 and gate['release_sha256']==serial.sha256 and gate['gpu_compute_rows']==[] and gate['shared_gpu_lock_held'] is True,'Missing actual admitted serial GPU allocation')
    required=release.value['predecessors'];checked=gate['predecessors']
    require(len(checked)==len(required)==5,'Incomplete five-layer serial gate evidence')
    for expected,proof in zip(required,checked):
        require(Path(proof['path']).resolve()==Path(expected['status_path']).resolve() and proof['sha256']==expected['status_sha256'],'Gate prerequisite differs from admitted immutable predecessor')
        predecessor=c.Bound.load(expected['status_path'],expected['status_sha256'])
        require(predecessor.value['status']==expected['required_status'],'Admitted predecessor state changed')
        require(g.exited(predecessor.value)==proof['owners'],'Admitted predecessor owner identity evidence differs')
    request.unchanged();spec.unchanged();release.unchanged();serial.unchanged()
    return release.sha256

def verify_stage(row,record):
    require(record['id']==row['id'] and record['seed']==row['seed'] and record['stage']==row['stage'],'Stage record identity mismatch')
    require(record['status']=='completed' and type(record['exit_code']) is int and record['exit_code']==0,'Stage not successfully completed')
    for key in ('plan_path','plan_sha256','output_directory','control_receipt_path'):
        require(record[key]==row[key],'Stage record differs from fixed specification: '+key)
    stage_owners_exited(record)
    plan=c.Bound.load(row['plan_path'],row['plan_sha256'])
    receipt=c.Bound.load(row['control_receipt_path'],record['control_receipt_sha256'])
    require(receipt.value['pid']==record['supervisor_pid'] and receipt.value['started_utc']==record['supervisor_started_utc'],'Actual frozen-control parent differs from observed stage supervisor')
    verify_execution_evidence(row,record,receipt)
    if row['stage']=='profile':
        profile=c.Bound.load(Path(row['output_directory'])/'profile.json',record['result_sha256'])
        c.validate_profile(profile,plan,receipt,g.exited)
        verified={'profile':artifact(profile.path),'lifecycle':artifact(receipt.path)}
    else:
        profile_record=record['profile_binding']
        profile=c.Bound.load(Path(plan.value['profile_directory'])/'profile.json',profile_record['profile_sha256'])
        profile_receipt=c.Bound.load(Path(plan.value['profile_receipt_directory'])/'lifecycle.json',profile_record['receipt_sha256'])
        c.validate_profile(profile,plan,profile_receipt,g.exited)
        verified=verify_training_artifacts(plan,receipt)
    require(verified==record['artifact_verification'],'Completed stage artifact verification changed')
    return verified

def verify_completed_execution(spec_path,spec_sha256,completion_path,completion_sha256):
    """Public stdlib completion API for future independent DAC evaluation binding.

    Caller supplies the SHA of the actually produced final completion manifest.
    This function never imports Torch/NumPy or claims tensor-content validation.
    """
    spec=spec_bound(spec_path,spec_sha256)
    completion=c.Bound.load(completion_path,completion_sha256);value=completion.value;c.no_fixture(value)
    require(Path(completion_path).resolve()==Path(spec.value['completion_path']).resolve(),'Completion path differs from prepared executor')
    require(value['schema']=='dac-six-stage-completion.v2' and value['execution_spec_sha256']==spec.sha256 and value['execution_manifest_sha256']==own_manifest(),'Completion belongs to different executor/specification')
    status=c.Bound.load(spec.value['status_path'],value['status_sha256']);state=status.value
    require(state['schema']=='dac-six-stage-execution-status.v2' and state['status']=='completed' and type(state['exit_code']) is int and state['exit_code']==0,'Six-stage execution is incomplete')
    require(state['execution_spec_sha256']==spec.sha256 and [job['id'] for job in state['jobs']]==ORDER,'Final sequence or spec mismatch')
    root_release=release_bound(state['root_release_path'],state['root_release_sha256'],spec)
    lifecycle_path=bound_artifact(value['controller_lifecycle'])
    require(lifecycle_path==HERE/'runtime/controller_lifecycle.json','Controller actual-exit receipt path mismatch')
    lifecycle=c.read(lifecycle_path)
    require(lifecycle['schema']=='dac-six-stage-controller-lifecycle.v2' and lifecycle['status']=='completed' and lifecycle['exit_code']==lifecycle['launcher_exit_code']==0,'Coordinator or Windows launcher did not actually exit0')
    require(type(lifecycle['exit_code']) is int and type(lifecycle['launcher_exit_code']) is int,'Coordinator actual exit codes must be integers')
    require(lifecycle['child_pid']==state['controller_pid'] and lifecycle['child_started_utc']==state['controller_started_utc'] and lifecycle['status_sha256']==status.sha256,'Coordinator actual-exit receipt differs from final status')
    require(lifecycle['execution_spec_sha256']==spec.sha256 and lifecycle['root_release_sha256']==root_release.sha256,'Coordinator actual-exit receipt belongs to different admission')
    expected_evidence={'stdout':'coordinator_stdout.log','stderr':'coordinator_stderr.log','identity':'coordinator_identity.json','request':'coordinator_request.json','acknowledgement':'coordinator_observed.json','candidate':'candidate_completion.json'}
    require(set(lifecycle['evidence'])==set(expected_evidence),'Incomplete coordinator closed logs/actual lifecycle evidence')
    for key,name in expected_evidence.items():require(bound_artifact(lifecycle['evidence'][key])==HERE/'runtime'/name,'Coordinator evidence path mismatch')
    identity=c.read(HERE/'runtime/coordinator_identity.json')
    g.validate_worker_identity(identity,spec.sha256,root_release.sha256,
        {'pid':lifecycle['pid'],'started_utc':lifecycle['started_utc']},
        {'pid':lifecycle['launcher_pid'],'started_utc':lifecycle['launcher_started_utc']})
    require(identity['pid']==state['controller_pid'] and identity['started_utc']==state['controller_started_utc'],'Actual coordinator identity differs from final status')
    request=c.read(HERE/'runtime/coordinator_request.json')
    require(request['spec_sha256']==spec.sha256 and request['release_sha256']==root_release.sha256 and request['parent_pid']==lifecycle['pid'] and request['parent_started_utc']==lifecycle['started_utc'],'Coordinator request differs from observed launch')
    require(c.read(HERE/'runtime/coordinator_observed.json')=={'request_sha256':lifecycle['evidence']['request']['sha256'],'identity_sha256':lifecycle['evidence']['identity']['sha256']},'Coordinator execution lacked actual-parent observation')
    candidate=c.read(HERE/'runtime/candidate_completion.json')
    require({k:v for k,v in value.items() if k!='controller_lifecycle'}==candidate,'Final manifest differs from actual coordinator candidate')
    g.exited(lifecycle)
    g.exited(state)  # includes real coordinator and every nested stage/worker owner
    seeds=[]
    for row,record in zip(spec.value['jobs'],state['jobs']):
        require(record['controller_pid']==state['controller_pid'] and record['controller_started_utc']==state['controller_started_utc'],'Completed stage came from a different coordinator')
        require(c.read(stage_directory(row['id'])/'request.json')['root_release_sha256']==root_release.sha256,'Stage root release differs from final status')
        verified=verify_stage(row,record)
        if row['stage']=='train':
            seeds.append({'seed':row['seed'],'plan_path':row['plan_path'],'plan_sha256':row['plan_sha256'],
                'output_directory':row['output_directory'],'control_receipt_path':record['control_receipt_path'],
                'control_receipt_sha256':record['control_receipt_sha256'],'artifacts':verified})
    require(value['training_artifacts']==seeds,'Final completion manifest differs from actual three-seed artifacts')
    status.unchanged();completion.unchanged();spec.unchanged();root_release.unchanged()
    return {'status':'completed','all_recorded_owners_exited':True,'execution_spec_path':str(spec.path),
        'execution_spec_sha256':spec.sha256,'status_path':str(status.path),'status_sha256':status.sha256,
        'completion_path':str(completion.path),'completion_sha256':completion.sha256,'seeds':seeds}
