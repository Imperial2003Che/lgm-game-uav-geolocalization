"""Immutable DAC control contracts. Import is standard-library only."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parent
SCIENCE = EXECUTION/'dac_training_preparation_v1'
SCIENCE_MANIFEST_SHA = '169a6eb7c351acc7e291b4ceefdecebda2c80ad70b46a20eeed6d42d14e72bc9'
CPU_RESULT_SHA = '5d1cb509088bb65a8ea5f22d1d7cfc482619bd3c61e0192f4c7aba5b8d094e25'
CPU_RESULT = EXECUTION/'dac_training_preparation_review_1721/real_cpu_probe_1822/result.json'
SCIENTIFIC_NAMES = ('common_runtime.py','dac_train_runtime.py','input_contract.py',
    'train_university_train_only.py','SCIENTIFIC_SOURCE_MANIFEST.json','SOURCE_PIN.json',
    'DAC_EXPECTED_MODEL_SCHEMA.json','INPUT_REFERENCES.json')
PROCESS_ENV = {'CUDA_VISIBLE_DEVICES':'0','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1',
    'OPENBLAS_NUM_THREADS':'1','NUMEXPR_NUM_THREADS':'1','NO_ALBUMENTATIONS_UPDATE':'1'}

def utc(): return datetime.now(timezone.utc).isoformat()
def digest(data): return hashlib.sha256(data).hexdigest()
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(8*1024*1024),b''): h.update(chunk)
    return h.hexdigest()
def require(condition, message):
    if not condition: raise RuntimeError(message)
def strict_json(data):
    return json.loads(data, parse_constant=lambda value:(_ for _ in ()).throw(ValueError('Nonfinite JSON constant: '+value)))
def read(path): return strict_json(Path(path).read_bytes())
def write(path,value):
    path=Path(path); temporary=path.with_name(path.name+'.partial')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    os.replace(temporary,path)
def is_sha(value): return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None
def number(value, minimum=None, integer=False):
    require(type(value) in (int,float) and math.isfinite(value),'Expected a finite numeric measurement')
    require(not integer or type(value) is int,'Expected an integer count/byte measurement')
    require(minimum is None or value>=minimum,'Measurement below allowed bound')
    return value
def no_fixture(value):
    if isinstance(value,dict):
        for key,item in value.items():
            require(not (key.lower() in {'fixture_only','mock','mocked','synthetic','simulated','fake'} and item not in (False,None)), 'Explicit fixture/synthetic evidence cannot be admitted')
            no_fixture(item)
    elif isinstance(value,list):
        for item in value: no_fixture(item)

@dataclass(frozen=True)
class Bound:
    path: Path
    data: bytes
    sha256: str
    @classmethod
    def load(cls,path,expected):
        require(is_sha(expected),'Caller must supply the previously frozen SHA-256')
        path=Path(path).resolve(); data=path.read_bytes()
        require(digest(data)==expected,'File bytes differ from admitted digest: '+str(path))
        strict_json(data)
        return cls(path,data,expected)
    @property
    def value(self): return strict_json(self.data)
    def unchanged(self): require(sha(self.path)==self.sha256,'Bound input changed after admission: '+str(self.path))
    def copy(self,path):
        path=Path(path)
        with path.open('xb') as stream: stream.write(self.data)
        return Bound.load(path,self.sha256)

def science_binding():
    manifest=Bound.load(SCIENCE/'PREPARATION_MANIFEST.json',SCIENCE_MANIFEST_SHA).value
    for row in manifest['files']:
        path=(SCIENCE/row['path']).resolve()
        require(path.is_relative_to(SCIENCE) and sha(path)==row['sha256'],'Frozen v1 science/preparation changed: '+row['path'])
    return {'manifest_sha256':SCIENCE_MANIFEST_SHA,'source_files_sha256':{name:sha(SCIENCE/name) for name in SCIENTIFIC_NAMES}}

def control_binding():
    manifest_path=HERE/'PREPARATION_MANIFEST.json'
    data=manifest_path.read_bytes(); manifest=strict_json(data)
    for row in manifest['files']:
        path=(HERE/row['path']).resolve()
        require(path.is_relative_to(HERE) and sha(path)==row['sha256'],'Control v2 payload changed: '+row['path'])
    return {'manifest_sha256':digest(data),'files':manifest['files']}

def runtime_modules():
    science_binding()
    if str(SCIENCE) not in sys.path: sys.path.insert(0,str(SCIENCE))
    modules={}
    for name in ('common_runtime','dac_train_runtime','input_contract','input_audit'):
        if name in sys.modules:
            require(Path(sys.modules[name].__file__).resolve()==SCIENCE/(name+'.py'),'Conflicting generic module imported: '+name)
        modules[name]=importlib.import_module(name)
        require(Path(modules[name].__file__).resolve()==SCIENCE/(name+'.py'),'Wrong frozen runtime origin')
    modules['dac_train_runtime'].verify_scientific_source()
    return modules

def raw_artifacts(bound):
    proof=bound.value; root=bound.path.parent; expected=proof.get('artifact_sha256',{})
    require(expected,'Missing raw execution artifacts')
    captured=[]
    for relative,digest_value in expected.items():
        path=(root/relative).resolve()
        require(path.is_relative_to(root) and is_sha(digest_value),'Artifact path or hash escaped proof')
        data=path.read_bytes()
        require(digest(data)==digest_value,'Raw proof artifact changed: '+relative)
        captured.append({'path':str(path),'sha256':digest_value})
    return captured

def validate_cpu(plan):
    reference=plan['cpu_compatibility_proof']
    require(Path(reference['path']).resolve()==CPU_RESULT and reference['sha256']==CPU_RESULT_SHA,'Only the reviewed genuine CPU execution is admitted')
    bound=Bound.load(CPU_RESULT,CPU_RESULT_SHA); proof=bound.value; no_fixture(proof)
    expected={'schema':'dac-real-cpu-compatibility.v1','method':'DAC','status':'passed','model_state_count':402,
        'pretrained_strict_tensor_count':344,'author_trained_weights_loaded':False,'all_model_state_cpu':True,
        'all_model_floating_state_finite':True,'real_pair_original_transforms_passed':True,
        'all_pair_floating_values_finite':True,'cuda_initialized':False,'optimizer_steps_executed':0,
        'gpu_profile_executed':False,'research_result':False,'identity_count':701,'training_pair_count':37854}
    for key,value in expected.items(): require(proof.get(key)==value,'CPU proof contract mismatch: '+key)
    require(proof['source_files_sha256']==science_binding()['source_files_sha256'],'CPU proof scientific source mismatch')
    require(proof['environment']==plan['environment'],'CPU proof was produced in a different environment')
    require(len(proof['pair_tensors'])==2 and all(row['shape']==[3,384,384] and row['device']=='cpu' and row['dtype']=='torch.float32' and row['finite'] is True and is_sha(row['sha256']) for row in proof['pair_tensors']),'Missing actual original-augmentation tensor evidence')
    pre=proof['pretrained_binding']
    require(pre['sha256']==plan['pretrained']['sha256'] and pre['expected_tensor_count']==pre['loaded_tensor_count']==344 and pre['load_policy']=='strict=True' and not any(pre[k] for k in ('missing_keys','unexpected_keys','shape_dtype_mismatch','ignored_keys')),'Incomplete original Meta initialization proof')
    inventory=Bound.load(plan['data_manifest_path'],plan['data_manifest_sha256']).value
    images={row['path']:row for row in inventory['files']}
    require(len(proof['real_images'])==2,'Missing original image proof')
    for row in proof['real_images']:
        require(row['relative_path'] in images and row['sha256']==images[row['relative_path']]['sha256'] and row['bytes']==images[row['relative_path']]['bytes'],'CPU probe image differs from complete inventory')
    prefix=Path(plan['environment']['prefix']).resolve()
    require(len(proof['runtime_environment'])==10,'Missing actual scientific module origins')
    for row in proof['runtime_environment'].values():
        require(Path(row['origin']).resolve().is_relative_to(prefix) and row['version'],'CPU runtime module escaped exact environment')
    artifacts=raw_artifacts(bound)
    pin=read(HERE/'TRUSTED_CPU_EXECUTION.json')
    require(pin['result_sha256']==CPU_RESULT_SHA,'Wrong independently reviewed CPU anchor')
    for row in pin['files']:
        require(sha(row['path'])==row['sha256'],'Trusted CPU script/log/exit receipt changed')
    receipt=Bound.load(pin['exit_receipt']['path'],pin['exit_receipt']['sha256']).value
    receipt_files={Path(row['path']).resolve():row['sha256'] for row in receipt['files']}
    require(type(receipt['exit_code']) is int and receipt['exit_code']==0 and receipt['pid']==proof['pid'] and receipt_files.get(CPU_RESULT)==CPU_RESULT_SHA and receipt['actual_pid_absent_at_observation'] is True,'CPU execution did not exit successfully with this result')
    require(receipt['started_utc']==proof['started_utc'] and receipt['probe_finished_utc']==proof['finished_utc'],'CPU process lifecycle differs from genuine probe')
    require(proof['script_sha256'] in receipt_files.values(),'CPU receipt script mismatch')
    return bound,artifacts

def validate_plan(bound,check_content=False):
    plan=bound.value; no_fixture(plan)
    require(plan.get('schema')=='dac-university-training-plan.v2' and plan.get('method')=='DAC','Wrong DAC v2 plan')
    require(type(plan.get('seed')) is int and plan['seed'] in (1,2,3),'Undeclared University seed')
    require(plan['science_binding']==science_binding() and plan['control_binding']==control_binding(),'Plan code binding mismatch')
    modules=runtime_modules(); refs=modules['input_contract'].references()
    for key in ('train_root','pretrained','data_manifest_path','data_manifest_sha256'):
        require(plan[key]==refs[key],'Prepared input changed: '+key)
    require(plan['source_directory']==str(SCIENCE/'scientific_source'),'DAC source path mismatch')
    require(plan['official_configuration_defaults']==modules['input_contract'].configuration_defaults(),'Official DAC default changed')
    require(plan['environment']==modules['input_audit'].environment(),'Runtime metadata differs from pinned environment')
    require(plan['process_environment']==PROCESS_ENV,'Unexpected admitted process environment')
    require(all(os.environ.get(k)==v for k,v in PROCESS_ENV.items()),'Actual process environment changed')
    for key in ('output_directory','profile_directory','profile_receipt_directory','training_receipt_directory'):
        output=Path(plan[key]).resolve()
        require(output.is_relative_to(EXECUTION) and not output.is_relative_to(SCIENCE) and not output.is_relative_to(HERE),'Output escaped new execution directories')
    require(len({str(Path(plan[k]).resolve()) for k in ('output_directory','profile_directory','profile_receipt_directory','training_receipt_directory')})==4,'Stage outputs must be distinct')
    require(sha(plan['pretrained']['path'])==plan['pretrained']['sha256'],'Original initialization changed')
    inventory=Bound.load(plan['data_manifest_path'],plan['data_manifest_sha256'])
    if check_content: require(modules['input_audit'].data_manifest(plan['train_root'])==inventory.value,'Training content/order differs from full manifest')
    cpu,artifacts=validate_cpu(plan)
    bound.unchanged()
    return plan,modules,inventory,cpu,artifacts

def profile_trace(profile,batch,resource):
    """Pure summary/trace cross-check, shared by real producer and strict consumer."""
    no_fixture(profile)
    actual=number(profile['actual_adamw_steps'],2,True)
    attempts=number(profile['completed_optimizer_amp_steps'],2,True)
    require(actual<=attempts<=32 and profile['amp_skips']==attempts-actual,'Invalid bounded actual/AMP step accounting')
    require(len(batch)==len(resource)==attempts,'Profile trace incomplete')
    initial,final=profile['initial_parameter_sha256'],profile['final_parameter_sha256']
    require(is_sha(initial) and is_sha(final) and initial!=final,'Missing actual changed parameter byte fingerprints')
    require(profile['representative_parameter']=='model_1.convnext.downsample_layers.0.0.weight','Wrong observed original shared stem')
    allocated=number(profile['peak_allocated_bytes'],1,True); reserved=number(profile['peak_reserved_bytes'],allocated,True)
    require(allocated==number(profile['post_validation_peak_allocated_bytes'],1,True) and reserved==number(profile['post_validation_peak_reserved_bytes'],allocated,True),'Summary peaks differ from actual post-validation measurement')
    require(number(profile['seconds_including_initialization'],0)>0,'Missing real wall-time measurement')
    require(profile['final_scaler_state'] and number(profile['final_scaler_state']['scale'],0)>0,'Missing finite enabled final AMP scaler')
    previous=0; prior_allocated=0; prior_reserved=0
    losses=[]
    for index,(observed,measured) in enumerate(zip(batch,resource),1):
        no_fixture(observed);no_fixture(measured)
        steps=number(observed['actual_optimizer_steps'],0,True)
        require(steps-previous in (0,1),'Invalid actual AdamW progression')
        require(observed['batch_attempt']==measured['batch_attempt']==index and observed['amp_skips']==measured['amp_skips']==index-steps,'Batch numbering or AMP count mismatch')
        require(observed['optimizer_updated_this_batch'] is bool(steps-previous) and observed['loss_finite'] is True,'Update observation mismatch')
        losses.append(number(observed['loss']))
        require(number(observed['scale_after_update'],0)>0,'Invalid post-update AMP scale');number(observed['lr_after_scheduler'],0)
        require(measured['actual_adamw_steps']==steps,'Resource trace differs from real hook')
        now_a=number(measured['peak_allocated_bytes'],prior_allocated,True)
        now_r=number(measured['peak_reserved_bytes'],max(prior_reserved,now_a),True)
        require(0<now_a<=allocated and now_r<=reserved,'Summary peak is smaller than measured trace')
        number(measured['seconds_including_data_and_synchronization'],0)
        number(measured['allocated_bytes'],0,True);number(measured['reserved_bytes'],0,True)
        previous,prior_allocated,prior_reserved=steps,now_a,now_r
    require(previous==actual and profile['losses']==losses,'Summary differs from actual update/loss trace')
    return {'attempts':attempts,'actual_adamw_steps':actual,'amp_skips':attempts-actual}

def validate_profile(bound,plan_bound,receipt_bound,check_exited):
    profile=bound.value; plan=plan_bound.value; no_fixture(profile)
    require(plan['science_binding']==science_binding() and plan['control_binding']==control_binding(),'Profile references unreviewed code')
    required={'schema':'dac-native-resource-profile.v2','method':'DAC','status':'passed','plan_sha256':plan_bound.sha256,
        'control_binding':plan['control_binding'],'science_binding':plan['science_binding'],
        'nominal_batch_pairs':24,'microbatch_pairs':24,'gradient_accumulation':1,'img_size':384,
        'model_state_count':402,'mixed_precision':True,'loss_weights':{'InfoNCE':1.0,'classification':0.1,'DSA':0.6},
        'all_official_losses':True,'oom':False,'all_observed_losses_finite':True,
        'all_model_floating_state_finite':True,'all_optimizer_floating_state_finite':True,
        'representative_parameter_changed':True,'research_result':False,'research_checkpoint_written':False,
        'environment':plan['environment'],'process_environment':PROCESS_ENV}
    for key,value in required.items(): require(profile.get(key)==value,'Resource profile mismatch: '+key)
    require(Path(bound.path).resolve()==Path(plan['profile_directory']).resolve()/'profile.json','Wrong profile output directory')
    evidence=profile['evidence_sha256']; root=bound.path.parent
    required_evidence={'batch_progress.jsonl','resource_batches.jsonl','initial_parameter_evidence.json','dac_model_binding.json',
        'pretrained_binding.json','dac_optimizer_initialization.json','runtime_environment.json','serial_release_gate.json',
        'stage_bindings.json','plan.json','serial_release.json','code_manifest.json','environment_manifest.json','epoch01_sampling.json','final_resource_measurement.json'}
    require(required_evidence.issubset(evidence),'Missing raw native profile execution evidence')
    for name,value in evidence.items():
        path=(root/name).resolve()
        require(path.is_relative_to(root) and is_sha(value) and sha(path)==value,'Profile evidence byte mismatch')
    initial=read(root/'initial_parameter_evidence.json')
    require(initial['sha256']==profile['initial_parameter_sha256'] and initial['name']==profile['representative_parameter'],'Representative initialization evidence mismatch')
    require(read(root/'dac_model_binding.json')['tensor_count']==402,'Profile is not the actual DAC model')
    require(read(root/'plan.json')==plan and evidence['plan.json']==plan_bound.sha256,'Profile ran a different plan')
    require(read(root/'code_manifest.json')=={'science':plan['science_binding'],'control':plan['control_binding']} and read(root/'environment_manifest.json')==plan['environment'],'Raw profile code/environment manifest mismatch')
    bindings=read(root/'stage_bindings.json')
    require(bindings['plan_sha256']==plan_bound.sha256 and bindings['release_sha256']==evidence['serial_release.json'],'Raw execution used different input snapshots')
    optimizer=read(root/'dac_optimizer_initialization.json')
    require(optimizer['weight_infonce']==1.0 and optimizer['weight_cls']==0.1 and optimizer['weight_dsa']==0.6 and optimizer['class'].endswith('.AdamW'),'Profile optimizer/loss initialization mismatch')
    require(profile['optimizer_step_max']==profile['actual_adamw_steps'] and 1<=profile['optimizer_step_min']<=profile['optimizer_step_max'],'Profile actual optimizer state disagrees with hook')
    final_measurement=read(root/'final_resource_measurement.json')
    require(final_measurement['phase']=='after_finite_state_validation' and final_measurement['pid']==profile['pid'] and final_measurement['plan_sha256']==plan_bound.sha256,'Final resource measurement has wrong phase or owner')
    require(final_measurement['peak_allocated_bytes']==profile['post_validation_peak_allocated_bytes'] and final_measurement['peak_reserved_bytes']==profile['post_validation_peak_reserved_bytes'],'Summary differs from raw final resource measurement')
    batch=[strict_json(line) for line in (root/'batch_progress.jsonl').read_bytes().splitlines()]
    resource=[strict_json(line) for line in (root/'resource_batches.jsonl').read_bytes().splitlines()]
    result=profile_trace(profile,batch,resource)
    receipt=receipt_bound.value; no_fixture(receipt)
    require(Path(receipt_bound.path).resolve()==Path(plan['profile_receipt_directory']).resolve()/'lifecycle.json','Wrong actual profile lifecycle path')
    require(receipt['schema']=='dac-stage-lifecycle.v2' and receipt['stage']=='profile' and receipt['status']=='completed' and type(receipt['exit_code']) is int and receipt['exit_code']==0,'Profile child did not exit successfully')
    require(receipt['plan_sha256']==plan_bound.sha256 and receipt['result_sha256']==bound.sha256,'Lifecycle bound a different resource profile')
    require(receipt['child_pid']==profile['pid'] and receipt['child_started_utc']==profile['started_utc'],'Profile process identity differs from parent receipt')
    check_exited(receipt)
    bound.unchanged(); receipt_bound.unchanged(); plan_bound.unchanged()
    return result
