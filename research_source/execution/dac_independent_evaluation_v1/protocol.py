"""Independent DAC final-checkpoint evaluation contracts; stdlib at import."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
EXECUTION=HERE.parent
AUTHOR=EXECUTION/'dac_preparation'
TRAIN=EXECUTION/'dac_training_preparation_v1'
CONTROL=EXECUTION/'dac_training_control_v2'
INPUTS=EXECUTION/'dac_training_inputs_v2'
TRAIN_EXECUTION=EXECUTION/'dac_training_execution_v2'
AUTHOR_EVAL=AUTHOR/'run_dac_author_evaluation.py'
MODEL_FACTORY=AUTHOR/'dac_model.py'
DEFAULT_MEMBERSHIP=AUTHOR/'preparations/20260914T045232800767Z/manifest.json'
SCHEMA='dac-independent-evaluation.v1'
BINDING_SCHEMA='dac-independent-final-checkpoint-binding.v1'
RELEASE_SCHEMA='dac-independent-evaluation-release.v1'
CONTROLLER_RELEASE_SCHEMA='dac-independent-evaluation-controller-release.v1'
BINDING_POLICY='bind all three verified completed fixed-final checkpoints, then evaluate all 30 tasks'
SEEDS=(1,2,3)
THREAD_ENVIRONMENT={name:'1' for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')}
THREAD_ENVIRONMENT['NO_ALBUMENTATIONS_UPDATE']='1'

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def load(path):return json.loads(Path(path).read_bytes(),parse_constant=lambda x:(_ for _ in ()).throw(ValueError('Nonfinite JSON '+x)))
def canonical(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def require(ok,message):
    if not ok:raise RuntimeError(message)
def artifact(path):
    path=Path(path).resolve();return {'path':str(path),'bytes':path.stat().st_size,'sha256':sha(path)}
def verify_artifact(value):require(artifact(value['path'])==value,'Artifact changed: '+value['path'])
def seal(value):return {**value,'payload_sha256':canonical(value)}
def verify_seal(value):
    body=dict(value);expected=body.pop('payload_sha256',None);require(canonical(body)==expected,'Contract payload seal mismatch')
def local_output(path):
    path=Path(path).resolve();require(path.is_relative_to(HERE),'Output escaped independent DAC evaluation directory');return path
def save(path,value):
    import os
    path=local_output(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.writing')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8');os.replace(temp,path)
def utc():return datetime.now(timezone.utc).isoformat()
def pins():return load(HERE/'SOURCE_PINS.json')
def pinned_import(name,path):
    path=Path(path).resolve();expected=pins()['files'][str(path)]
    require(sha(path)==expected,'Pinned module changed: '+str(path))
    if name in sys.modules:
        require(Path(sys.modules[name].__file__).resolve()==path,'Conflicting module origin: '+name)
        return sys.modules[name]
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module);return module
def helpers():return pinned_import('_dac_independent_official_helpers',AUTHOR_EVAL)
def controls():
    c=pinned_import('dac2_contracts',CONTROL/'dac2_contracts.py')
    g=pinned_import('dac2_gates',CONTROL/'dac2_gates.py')
    return c,g
def source_evidence():
    data=pins()
    for path,digest in data['files'].items():require(sha(path)==digest,'Frozen source changed: '+path)
    # Both official DAC construction and its unchanged private training model are bound.
    private=load(TRAIN/'SCIENTIFIC_SOURCE_MANIFEST.json')
    for row in private['files']:
        path=TRAIN/'scientific_source'/row['path'];require(sha(path)==row['derived_sha256'],'Private DAC source changed')
    official=load(TRAIN/'SOURCE_PIN.json')
    for row in official['files']:require(sha(Path(official['official_source_directory'])/row['path'])==row['sha256'],'Official DAC source changed')
    return {'source_pins':artifact(HERE/'SOURCE_PINS.json'),'files':[artifact(path) for path in data['files']],
        'adapter_files':[artifact(HERE/name) for name in ('protocol.py','dac_independent_model.py','complete_state_checks.py','run_evaluation.py')],
        'private_scientific_tree_sha256':canonical(private),'official_scientific_tree_sha256':canonical(official)}
def validate_training_plan(plan,seed):
    frozen=INPUTS/f'seed_{seed}_plan.json';require(sha(frozen)==pins()['files'][str(frozen)],'Frozen seed plan changed')
    require(plan==load(frozen) and plan['seed']==seed,'Only exact declared seed plan is admitted')
    require(plan['method']=='DAC' and plan['official_configuration_defaults']['epochs']==1,'Wrong independent training method/epoch')
    output=EXECUTION/'dac_independent_runs_v2'/f'seed_{seed}'
    require(Path(plan['output_directory']).resolve()==output,'Wrong declared independent output')
    return output
def validate_execution_plan(path,declared,python):
    path=Path(path).resolve();require(path==TRAIN_EXECUTION/'execution_spec.json','Expected DAC v2 execution specification')
    # The exact newly sealed supervisor is an explicit late-bound input at prepare.
    # It is never derived from a completed model or an author checkpoint.
    value=load(path)
    require([x['seed'] for x in declared]==list(SEEDS),'Three ordered seed plans required')
    for item in declared:
        verify_artifact(item['plan']);validate_training_plan(load(item['plan']['path']),item['seed'])
    require(Path(python).resolve()==Path(load(INPUTS/'seed_1_plan.json')['environment']['executable']).resolve(),'Wrong exact DAC runtime')
    return value
def membership_evidence(path=DEFAULT_MEMBERSHIP):
    path=Path(path).resolve();require(path==DEFAULT_MEMBERSHIP and sha(path)==pins()['files'][str(path)],'Wrong frozen full-gallery membership')
    manifest=load(path);verify_seal(manifest)
    for name in ('inventory','tasks'):verify_artifact(manifest[name])
    inventory=load(manifest['inventory']['path']);tasks=load(manifest['tasks']['path'])
    require(len(inventory)==131062 and len(tasks)==10,'Full inventory/task count changed')
    require([t['distractor_identity_count'] for t in tasks]==[250,250]+[120]*8,'Distractor galleries changed')
    keys=('image_size','descriptor_dim','descriptor','normalization','amp','flip_tta','batch_size','workers','ranking_chunk_size','device','gallery_protocol','ranking')
    return {'source_manifest':artifact(path),'inventory':manifest['inventory'],'tasks':manifest['tasks'],'roots':manifest['roots'],
        'runtime':manifest['runtime'],'settings':{key:manifest['settings'][key] for key in keys},
        'reuse_scope':'Frozen image membership, original DAC validation transform and common full-gallery metrics only; author weight values and author result rows are not used.'}
def exited(row,pid_key,start_key,label):
    c,g=controls();pid=row.get(pid_key);start=row.get(start_key);finish=row.get('finished_utc') or row.get('ended_utc')
    c.number(pid,1,True);require(isinstance(start,str) and isinstance(finish,str),'Missing '+label+' process lifecycle')
    a=datetime.fromisoformat(start);b=datetime.fromisoformat(finish)
    require(a.tzinfo is not None and b.tzinfo is not None and b>=a,'Invalid '+label+' lifecycle times')
    actual=g.process_started(pid)
    if actual is not None:require(datetime.fromisoformat(actual)>b,'Original or ambiguous '+label+' owner still active')
def validate_training_completion(state,prepared,process_exit=exited):
    require(state.get('schema')=='dac-six-stage-execution-status.v2' and state.get('status')=='completed' and type(state.get('exit_code')) is int and state['exit_code']==0,'DAC six-stage supervision is incomplete')
    require(state.get('execution_spec_sha256')==prepared['training_execution_plan']['sha256'],'DAC completion specification differs')
    require(Path(state['execution_spec_path']).resolve()==Path(prepared['training_execution_plan']['path']).resolve(),'DAC completion specification path differs')
    process_exit(state,'controller_pid','controller_started_utc','DAC training controller')
    jobs=state.get('jobs',[]);expected=[f'seed_{s}_{stage}' for s in SEEDS for stage in ('profile','train')]
    require([j.get('id') for j in jobs]==expected,'All six declared jobs in order are required')
    for index,job in enumerate(jobs):
        seed=index//2+1;stage=('profile','train')[index%2];declared=prepared['training_plans'][seed-1]
        require(job.get('seed')==seed and job.get('stage')==stage,'Job seed/stage mismatch')
        require(job.get('status')=='completed','Incomplete DAC stage')
        for key in ('exit_code','launcher_exit_code','supervisor_exit_code'):require(type(job.get(key)) is int and job[key]==0,'Stage owner exit code is not actual zero')
        require(job.get('plan_sha256')==declared['plan']['sha256'] and Path(job['plan_path']).resolve()==Path(declared['plan']['path']).resolve(),'Stage plan binding differs')
        plan=load(declared['plan']['path']);out=Path(plan['profile_directory' if stage=='profile' else 'output_directory']).resolve()
        require(Path(job['output_directory']).resolve()==out,'Stage output differs')
        for prefix in ('launcher','supervisor'):process_exit(job,prefix+'_pid',prefix+'_started_utc',f'DAC seed{seed} {stage} '+prefix)
        receipt=Path(job['control_receipt_path']).resolve();expected_receipt=Path(plan['profile_receipt_directory' if stage=='profile' else 'training_receipt_directory'])/'lifecycle.json'
        require(receipt==expected_receipt and sha(receipt)==job['control_receipt_sha256'],'Stage lifecycle artifact differs')
        life=load(receipt)
        require(life.get('schema')=='dac-stage-lifecycle.v2' and life.get('stage')==stage and life.get('status')=='completed','Wrong or unfinished control lifecycle')
        require(life.get('plan_sha256')==declared['plan']['sha256'],'Control lifecycle plan differs')
        for key in ('exit_code','launcher_exit_code'):require(type(life.get(key)) is int and life[key]==0,'Actual worker/launcher exit not zero')
        require(life['pid']==job['supervisor_pid'] and life['started_utc']==job['supervisor_started_utc'],'Actual supervisor identity differs')
        for pk,sk in (('pid','started_utc'),('launcher_pid','launcher_started_utc'),('child_pid','child_started_utc')):process_exit(life,pk,sk,'DAC stage control '+pk)
        result=out/('profile.json' if stage=='profile' else 'checkpoint_manifest.json')
        require(Path(life['result_path']).resolve()==result and life['result_sha256']==sha(result) and life['status_sha256']==sha(out/'status.json'),'Exited stage result binding differs')
    return jobs
def validate_training_evidence(status,evidence,configuration,seed,protocol,sampling,trace):
    require(status.get('status')=='completed' and type(status.get('epoch_completed')) is int and status['epoch_completed']==1 and status.get('selection')=='fixed final epoch' and status.get('test_data_read') is False,'Expected complete train-only final epoch')
    a=evidence.get('actual_adamw_steps');n=evidence.get('attempted_batches');skip=evidence.get('amp_skips')
    require(type(a) is int and type(n) is int and type(skip) is int and 0<a<=n and a+skip==n,'Invalid AdamW/AMP accounting')
    require(status.get('actual_adamw_steps')==a and status.get('optimizer_step_attempts')==n and status.get('amp_skips')==skip,'Status/step evidence differs')
    require(type(evidence.get('epoch_loss')) in (int,float) and math.isfinite(evidence['epoch_loss']) and evidence.get('all_model_floating_state_finite') is True and evidence.get('representative_parameter_changed') is True,'Training finite/change evidence missing')
    require(evidence['initial_parameter_sha256']!=evidence['final_parameter_sha256'],'Trained parameter unchanged')
    require(configuration==load(INPUTS/f'seed_{seed}_effective_configuration.json'),'Complete effective configuration differs from frozen seed configuration')
    fixed={'method':'DAC','model_state_count':402,'epoch':1,'scheduler_steps_planned_before_shuffle':1578,'warmup_steps_planned_before_shuffle':157.8,
        'actual_loader_batches':n,'scheduler_attempts':n,'actual_adamw_steps':a,'amp_skips':skip,'optimizer_step_max':a,'all_optimizer_moments_finite':True,'test_set_read_or_model_selection':False}
    require(all(protocol.get(k)==v for k,v in fixed.items()),'DAC epoch/scheduler/loss protocol differs')
    require(type(protocol.get('optimizer_step_min')) is int and 1<=protocol['optimizer_step_min']<=a,'Invalid actual optimizer state steps')
    require(sampling['official_pair_count']==37854 and sampling['expected_batches']==n and sampling['nominal_pairs_per_batch']==24,'Original full-epoch sampler differs')
    require(sampling['sample_count']+sampling['excluded_tail_pairs']==37854 and 0<sampling['sample_count']<=37854 and sampling['excluded_tail_pairs']>=0 and sampling['sample_count']%24==0 and sampling['sample_count']//24==n,'Original sampler/full-loader accounting differs')
    require(len(trace)==n,'Missing original batch observations')
    previous=0
    for i,row in enumerate(trace,1):
        actual=row.get('actual_optimizer_steps');require(type(actual) is int and actual-previous in (0,1),'Invalid original optimizer hook progression')
        require(row['epoch']==1 and row['batch_attempt']==i and row['amp_skips']==i-actual and row['optimizer_updated_this_batch'] is bool(actual-previous),'Batch trace accounting differs')
        require(row['loss_finite'] is True and type(row['loss']) in (int,float) and math.isfinite(row['loss']),'Invalid batch loss')
        require(type(row['scale_after_update']) in (int,float) and math.isfinite(row['scale_after_update']) and row['scale_after_update']>0,'Invalid AMP scale')
        require(type(row.get('lr_after_scheduler')) in (int,float) and math.isfinite(row['lr_after_scheduler']) and row['lr_after_scheduler']>=0,'Invalid scheduled learning rate')
        previous=actual
    require(previous==a,'Final AdamW trace differs')
    return {'actual_adamw_steps':a,'attempted_batches':n,'amp_skips':skip}
def bind_seed(declared):
    verify_artifact(declared['plan']);plan=load(declared['plan']['path']);out=validate_training_plan(plan,declared['seed'])
    names=('plan.json','status.json','training_evidence.json','dac_training_protocol_evidence.json','effective_configuration.json','checkpoint_manifest.json',
        'resource_profile.json','resource_profile_lifecycle.json','code_manifest.json','data_manifest.json','environment_manifest.json','runtime_environment.json',
        'serial_release_gate.json','serial_release.json','pretrained_binding.json','epoch01_sample_order.json','epoch01_sampling.json','batch_progress.jsonl',
        'dac_model_binding.json','dac_optimizer_initialization.json','stage_bindings.json','cpu_result.json')
    files={name:artifact(out/name) for name in names}
    require(files['plan.json']['sha256']==declared['plan']['sha256'],'Copied training plan differs')
    c,g=controls();c.no_fixture({name:load(out/name) for name in names if name.endswith('.json')})
    evidence=load(out/'training_evidence.json');protocol=load(out/'dac_training_protocol_evidence.json');sampling=load(out/'epoch01_sampling.json')
    counts=validate_training_evidence(load(out/'status.json'),evidence,load(out/'effective_configuration.json'),declared['seed'],protocol,sampling,[json.loads(x) for x in (out/'batch_progress.jsonl').read_text('utf-8').splitlines()])
    require(sampling['sample_order_sha256']==files['epoch01_sample_order.json']['sha256'],'Actual epoch order changed')
    require(len(load(out/'epoch01_sample_order.json'))==sampling['sample_count'],'Actual epoch order count differs')
    require(load(out/'code_manifest.json')=={'science':plan['science_binding'],'control':plan['control_binding']} and load(out/'environment_manifest.json')==plan['environment'],'Training code/environment differs')
    require(files['data_manifest.json']['sha256']==plan['data_manifest_sha256'],'Training complete content inventory differs')
    model=load(out/'dac_model_binding.json');require(model['tensor_count']==402 and model['schema_sha256']==pins()['files'][str(TRAIN/'DAC_EXPECTED_MODEL_SCHEMA.json')],'Training was not exact DAC402')
    optimizer=load(out/'dac_optimizer_initialization.json');require(optimizer['class'].endswith('.AdamW') and [optimizer[k] for k in ('weight_infonce','weight_cls','weight_dsa')]==[1.0,0.1,0.6],'Official optimizer/loss differs')
    p=c.Bound.load(declared['plan']['path'],declared['plan']['sha256'])
    profile=c.Bound.load(Path(plan['profile_directory'])/'profile.json',files['resource_profile.json']['sha256'])
    receipt=c.Bound.load(Path(plan['profile_receipt_directory'])/'lifecycle.json',files['resource_profile_lifecycle.json']['sha256'])
    c.validate_profile(profile,p,receipt,g.exited)
    checkpoint_manifest=load(out/'checkpoint_manifest.json');require(set(checkpoint_manifest)=={'checkpoint_complete.pth','weights_end.pth'},'Only complete/final pair is admitted')
    checkpoints={}
    for name,expected in checkpoint_manifest.items():
        actual=artifact(out/name);require(actual['sha256']==expected['sha256'] and actual['bytes']==expected['bytes'],'Final checkpoint bytes differ');checkpoints[name]=actual
    return {'seed':declared['seed'],'plan':declared['plan'],'output_directory':str(out),'training_files':files,'checkpoints':checkpoints,
        'optimizer_counts':counts,'checkpoint_sha256_source':'Actual completed local files, after external owner-exit verification',
        'tensor_coverage':'Runtime requires all 402 original keys and byte-identical complete/final model tensors'}
def compare_schema(expected,actual):
    official={k:(tuple(v['shape']),v['dtype']) for k,v in load(TRAIN/'DAC_EXPECTED_MODEL_SCHEMA.json')['tensors'].items()}
    require(expected==official and actual==official and len(actual)==402,'Strict DAC402 schema mismatch; no author compatibility/key renaming/head deletion')
    return {'tensor_count':402,'missing_keys':[],'unexpected_keys':[],'shape_dtype_mismatches':[],'schema_adaptation':'none','key_renaming':'none','three_classifier_heads_and_DSA_projection_retained':True}

def execution_package_evidence():return artifact(TRAIN_EXECUTION/'PREPARATION_MANIFEST.json')
def verify_execution_package(reference,external_sha=None):
    require(Path(reference['path']).resolve()==TRAIN_EXECUTION/'PREPARATION_MANIFEST.json','Expected DAC v2 execution package')
    if external_sha is not None:require(reference['sha256']==external_sha,'Externally admitted execution package SHA differs')
    verify_artifact(reference);manifest=load(reference['path'])
    rows=manifest['files'];require(rows and len({x['path'] for x in rows})==len(rows),'Invalid execution source manifest')
    for row in rows:
        path=(TRAIN_EXECUTION/row['path']).resolve();require(path.is_relative_to(TRAIN_EXECUTION),'Execution manifest path escaped package')
        require(sha(path)==row['sha256'] and path.stat().st_size==row['bytes'],'Execution package source changed')
    require(any(Path(x['path']).name=='dac6_contracts.py' for x in rows),'Missing independently reviewed supervision contract')
    return reference
def verify_completed_supervision(prepared,completion_path,completion_sha):
    verify_execution_package(prepared['training_execution_package'])
    # Source hashes come from the exact externally pinned package, not a future
    # status claiming success. No scientific package is imported by this module.
    path=TRAIN_EXECUTION/'dac6_contracts.py';name='_dac_independent_supervision_contract'
    old=list(sys.path)
    try:
        sys.path.insert(0,str(TRAIN_EXECUTION));controls()
        if name in sys.modules:require(Path(sys.modules[name].__file__).resolve()==path,'Wrong DAC supervision module')
        else:
            spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
            sys.modules[name]=module;spec.loader.exec_module(module)
        result=sys.modules[name].verify_completed_execution(prepared['training_execution_plan']['path'],prepared['training_execution_plan']['sha256'],str(completion_path),completion_sha)
        verify_execution_package(prepared['training_execution_package']);verify_artifact(prepared['training_execution_plan'])
        return result
    finally:sys.path[:]=old
