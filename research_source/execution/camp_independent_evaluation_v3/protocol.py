"""Standard-library contract and completion checks for independent CAMP models."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
EXECUTION=HERE.parent
AUTHOR=EXECUTION/'camp_preparation'
TRAIN=EXECUTION/'camp_training_preparation_v2'
AUTHOR_EVAL=AUTHOR/'run_camp_author_evaluation.py'
AUTHOR_EVAL_SHA='cd26c3d4fc68f084e2c3fa4cbb772f80ee311cf5952851af976109bd5203f1bd'
MODEL_FACTORY=AUTHOR/'camp_model.py'
MODEL_FACTORY_SHA='e67acf439eedd0baaeb663f91cb5b785c8609dc5152be437f15f8c90be026b67'
TRAIN_PREPARATION_SHA='12747158ce2647474c6d24688ba3ebb872ac137118fab7aefd1c1e0ecfad40ec'
DEFAULT_MEMBERSHIP=AUTHOR/'preparations/20260914T045031917075Z/manifest.json'
MEMBERSHIP_SHA='ddb8a3029557a1039c005e94648d40bf95397ee7b84cad0f33ab6dcacfaa1ec7'
SCHEMA='camp-independent-evaluation.v1'
BINDING_SCHEMA='camp-independent-final-checkpoint-binding.v1'
RELEASE_SCHEMA='camp-independent-evaluation-release.v1'
CONTROLLER_RELEASE_SCHEMA='camp-independent-evaluation-controller-release.v1'
BINDING_POLICY='bind all three verified completed fixed-final checkpoints, then evaluate all 30 tasks'
SEEDS=(1,2,3)
LATEST_IDS=('camp_author_checkpoint_full_gallery_10tasks','dac_author_checkpoint_full_gallery_10tasks')
THREAD_ENVIRONMENT={name:'1' for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')}

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def canonical(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def artifact(path):
    path=Path(path).resolve();return {'path':str(path),'bytes':path.stat().st_size,'sha256':sha(path)}
def verify_artifact(value):
    if artifact(value['path'])!=value:raise RuntimeError('Artifact changed: '+value['path'])
def seal(value):return {**value,'payload_sha256':canonical(value)}
def verify_seal(value):
    body=dict(value);expected=body.pop('payload_sha256',None)
    if canonical(body)!=expected:raise RuntimeError('Contract payload seal mismatch')
def local_output(path):
    path=Path(path).resolve()
    if not path.is_relative_to(HERE):raise RuntimeError('Output must stay inside camp_independent_evaluation')
    return path
def save(path,value):
    import os
    path=local_output(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.writing')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    os.replace(temp,path)
def utc():return datetime.now(timezone.utc).isoformat()

def helpers():
    """Import only the stdlib top level of the pinned evaluator, never its CLI."""
    if sha(AUTHOR_EVAL)!=AUTHOR_EVAL_SHA:raise RuntimeError('Reviewed evaluation helpers changed')
    name='_camp_independent_frozen_evaluation_helpers'
    if name not in sys.modules:
        spec=importlib.util.spec_from_file_location(name,AUTHOR_EVAL)
        module=importlib.util.module_from_spec(spec);sys.modules[name]=module
        spec.loader.exec_module(module)
    return sys.modules[name]

def source_evidence():
    h=helpers()
    if sha(MODEL_FACTORY)!=MODEL_FACTORY_SHA:raise RuntimeError('Reviewed full CAMP factory changed')
    if sha(TRAIN/'PREPARATION_MANIFEST.json')!=TRAIN_PREPARATION_SHA:raise RuntimeError('Training preparation changed')
    preparation=load(TRAIN/'PREPARATION_MANIFEST.json')
    for item in preparation['files']:
        path=TRAIN/item['path']
        if path.stat().st_size!=item['bytes'] or sha(path)!=item['sha256']:raise RuntimeError('Frozen training source changed: '+str(path))
    pins=load(AUTHOR/'source_pins.json')
    for relative,item in pins['official_source_files'].items():
        path=h.SOURCE/relative
        if path.stat().st_size!=item['bytes'] or sha(path)!=item['sha256']:raise RuntimeError('Official CAMP source changed')
    if sha(h.CORE)!=h.CORE_SHA or sha(h.SPLIT)!=h.SPLIT_SHA:raise RuntimeError('Frozen metrics/split changed')
    files=[AUTHOR_EVAL,MODEL_FACTORY,AUTHOR/'source_pins.json',h.CORE,h.SPLIT,TRAIN/'PREPARATION_MANIFEST.json']
    files.extend(HERE/name for name in ('protocol.py','camp_independent_model.py','run_evaluation.py'))
    return {'files':[artifact(path) for path in files],'official_source_tree_sha256':canonical(pins['official_source_files'])}

def validate_training_plan(plan,expected_seed):
    if plan.get('schema_version')!=1 or plan.get('seed')!=expected_seed:raise RuntimeError('Training plan seed/schema differs')
    required={'dataset':'University-1652','epochs':1,'nominal_batch_pairs':24,'microbatch_pairs':24,
              'gradient_accumulation':1,'img_size':384,'mixed_precision':True,'num_workers':0,
              'checkpoint_selection':'complete final epoch','training_test_access':False}
    if any(plan.get('protocol',{}).get(key)!=value for key,value in required.items()):raise RuntimeError('Training plan is not the fixed full-batch final-epoch protocol')
    expected_output=(EXECUTION/'camp_independent_runs'/f'seed_{expected_seed}').resolve()
    if Path(plan['output_directory']).resolve()!=expected_output:raise RuntimeError('Training output differs from the declared seed directory')
    h=helpers()
    if Path(plan['source_directory']).resolve()!=h.SOURCE.resolve():raise RuntimeError('Training model source differs')
    return expected_output


def validate_execution_plan(path,declared,python):
    path=Path(path).resolve();value=load(path)
    if path!=EXECUTION/'camp_training_execution_v2/execution_plan.json' or value.get('schema')!='camp-independent-training-plan.v1':raise RuntimeError('Expected the fixed independent-training execution plan')
    if value.get('preparation_manifest_sha256')!=TRAIN_PREPARATION_SHA:raise RuntimeError('Training execution uses a different frozen preparation')
    if Path(value.get('python_executable','')).resolve()!=Path(python).resolve():raise RuntimeError('Training/evaluation runtime paths differ')
    if value.get('preceding_latest_plan_sha256')!=sha(EXECUTION/'latest_baseline_plan.json'):raise RuntimeError('Training predecessor plan differs')
    rows=value.get('seeds',[])
    if [row.get('seed') for row in rows]!=list(SEEDS):raise RuntimeError('Execution plan must contain all three seeds in order')
    for row,item in zip(rows,declared):
        if row.get('plan_sha256')!=item['plan']['sha256'] or Path(row.get('plan_path','')).resolve()!=Path(item['plan']['path']).resolve() or Path(row.get('output_directory','')).resolve()!=Path(item['output_directory']).resolve():raise RuntimeError('Execution plan seed bindings differ')
    for name,digest in value.get('execution_code_sha256',{}).items():
        source=path.parent/name
        if source.parent!=path.parent or sha(source)!=digest:raise RuntimeError('Training execution source changed')
    if len(value.get('execution_code_sha256',{}))!=4:raise RuntimeError('Expected four fixed training wrapper source files')
    for record,digest in value.get('environment_records_sha256',{}).items():
        if sha(record)!=digest:raise RuntimeError('Shared locked runtime RECORD changed')
    if len(value.get('environment_records_sha256',{}))!=70:raise RuntimeError('Expected the fixed 70-package runtime provenance')
    return value

def membership_evidence(path=DEFAULT_MEMBERSHIP):
    path=Path(path).resolve()
    if path!=DEFAULT_MEMBERSHIP.resolve() or sha(path)!=MEMBERSHIP_SHA:raise RuntimeError('Expected the frozen reviewed complete-gallery membership manifest')
    manifest=load(path);verify_seal(manifest)
    for name in ('inventory','tasks'):verify_artifact(manifest[name])
    inventory=load(manifest['inventory']['path']);tasks=load(manifest['tasks']['path'])
    if len(inventory)!=131062 or len(tasks)!=10:raise RuntimeError('Complete-gallery membership differs')
    if [t['distractor_identity_count'] for t in tasks]!=[250,250]+[120]*8:raise RuntimeError('Distractor memberships differ')
    common_settings={key:manifest['settings'][key] for key in ('image_size','descriptor_dim','descriptor','normalization','amp','flip_tta','batch_size','workers','ranking_chunk_size','device','gallery_protocol','ranking')}
    return {'source_manifest':artifact(path),'inventory':manifest['inventory'],'tasks':manifest['tasks'],
            'roots':manifest['roots'],'runtime':manifest['runtime'],'settings':common_settings,
            'reuse_scope':'Only frozen input membership, common metrics and validated transforms; no author checkpoint or auxiliary schema is adopted.'}

def verify_latest_completed(prepared):
    h=helpers();plan_path=EXECUTION/'latest_baseline_plan.json'
    if sha(plan_path)!=prepared['latest_baseline_plan']['sha256']:raise RuntimeError('Latest-baseline plan changed')
    state_path=EXECUTION/'latest_baseline_status.json';state=load(state_path)
    if state.get('status')!='latest_baselines_finished_review_pending' or state.get('plan_sha256')!=sha(plan_path):raise RuntimeError('Both latest author-baseline jobs must complete first')
    if tuple(j.get('id') for j in state.get('jobs',[]))!=LATEST_IDS:raise RuntimeError('Latest-baseline job inventory differs')
    h.require_process_exit(state,'supervisor_pid','supervisor_started_utc','latest-baseline supervisor')
    for job in state['jobs']:
        if job.get('status')!='completed' or job.get('exit_code')!=0:raise RuntimeError('A latest-baseline job is incomplete')
        h.require_process_exit(job,'pid','started_utc','latest-baseline child '+job['id'])
    return artifact(state_path)

def validate_training_completion(state,prepared,process_exit):
    """Pure structure checks plus injected process-exit verifier for mock tests."""
    if state.get('schema')!='camp-independent-training-status.v1' or state.get('status')!='completed' or state.get('exit_code')!=0:raise RuntimeError('All three independent training runs must finish')
    if state.get('plan_sha256')!=prepared['training_execution_plan']['sha256']:raise RuntimeError('Completed training wrapper refers to another execution plan')
    if state.get('supervisor_started_utc')!=state.get('started_utc'):raise RuntimeError('Training supervisor creation timestamps disagree')
    process_exit(state,'supervisor_pid','supervisor_started_utc','CAMP training supervisor')
    rows=state.get('seeds',[])
    if [row.get('seed') for row in rows]!=list(SEEDS):raise RuntimeError('Expected all three registered seeds in order')
    for row,declared in zip(rows,prepared['training_plans']):
        if row.get('status')!='completed' or row.get('exit_code')!=0:raise RuntimeError('A registered training seed is incomplete')
        if row.get('plan_sha256')!=declared['plan']['sha256'] or Path(row.get('plan_path','')).resolve()!=Path(declared['plan']['path']).resolve():raise RuntimeError('Seed plan identity differs')
        if Path(row.get('output_directory','')).resolve()!=Path(declared['output_directory']).resolve():raise RuntimeError('Seed output identity differs')
        for key in ('profile_record','training_record'):
            child=row.get(key,{})
            if child.get('status')!='completed' or child.get('exit_code')!=0:raise RuntimeError('Missing completed training/profile child')
            process_exit(child,'pid','started_utc',f'seed{row["seed"]} '+key)
    return rows

def validate_training_evidence(status,evidence,configuration,seed):
    if status.get('status')!='completed' or status.get('epoch_completed')!=1 or status.get('selection')!='fixed final epoch' or status.get('test_data_read') is not False:raise RuntimeError('Training status is not a complete no-test final epoch')
    actual=evidence.get('actual_adamw_steps',0);attempts=evidence.get('attempted_batches',0);skips=evidence.get('amp_skips',-1)
    if type(actual) is not int or actual<1 or type(attempts) is not int or attempts<actual or type(skips) is not int or skips<0 or actual+skips!=attempts:raise RuntimeError('Invalid actual optimizer/AMP evidence')
    if status.get('actual_adamw_steps')!=actual or status.get('optimizer_step_attempts')!=attempts or status.get('amp_skips')!=skips:raise RuntimeError('Training status/evidence counts differ')
    if not math.isfinite(evidence.get('epoch_loss',float('nan'))) or evidence.get('all_model_floating_state_finite') is not True or evidence.get('representative_parameter_changed') is not True:raise RuntimeError('Training validity evidence incomplete')
    if evidence.get('initial_parameter_sha256')==evidence.get('final_parameter_sha256'):raise RuntimeError('Training parameter did not change')
    if configuration.get('seed')!=seed or configuration.get('epochs')!=1 or configuration.get('nclasses')!=701:raise RuntimeError('Effective trained configuration differs')
    return {'actual_adamw_steps':actual,'attempted_batches':attempts,'amp_skips':skips}

def validate_resource_profile(profile,plan_sha256):
    if profile.get('status')!='passed' or profile.get('plan_sha256')!=plan_sha256:raise RuntimeError('Training resource profile is unbound or incomplete')
    actual=profile.get('actual_adamw_steps',0);attempts=profile.get('completed_optimizer_amp_steps',0)
    if type(actual) is not int or type(attempts) is not int or not 2<=actual<=attempts<=32 or profile.get('amp_skips')!=attempts-actual:raise RuntimeError('Two actual AdamW updates and consistent bounded AMP accounting are required')
    for key,value in {'nominal_batch_pairs':24,'microbatch_pairs':24,'gradient_accumulation':1,'img_size':384,'all_official_losses':True,'mixed_precision':True,'oom':False,'exclusive_gpu_allocation':True}.items():
        if profile.get(key)!=value:raise RuntimeError('Training resource protocol differs: '+key)


def bind_seed(declared):
    verify_artifact(declared['plan']);plan=load(declared['plan']['path'])
    output=validate_training_plan(plan,declared['seed'])
    if sha(output/'plan.json')!=declared['plan']['sha256']:raise RuntimeError('Copied final training plan differs')
    names=('plan.json','status.json','training_evidence.json','effective_configuration.json','checkpoint_manifest.json',
           'resource_profile.json','code_manifest.json','data_manifest.json','environment_manifest.json','runtime_environment.json',
           'serial_release_gate.json','serial_release.json','pretrained_binding.json','epoch01_sample_order.json')
    evidence={name:artifact(output/name) for name in names}
    status=load(output/'status.json');training=load(output/'training_evidence.json');configuration=load(output/'effective_configuration.json')
    counts=validate_training_evidence(status,training,configuration,declared['seed'])
    if load(output/'code_manifest.json')!=plan['code_manifest'] or load(output/'environment_manifest.json')!=plan['environment']:raise RuntimeError('Training code/environment provenance differs')
    if sha(output/'data_manifest.json')!=plan['data_manifest_sha256']:raise RuntimeError('Training data provenance differs')
    profile=load(output/'resource_profile.json')
    validate_resource_profile(profile,declared['plan']['sha256'])
    manifest=load(output/'checkpoint_manifest.json')
    if set(manifest)!={'checkpoint_complete.pth','weights_end.pth'}:raise RuntimeError('Expected exact complete/end checkpoint contract')
    checkpoints={}
    for name,expected in manifest.items():
        actual=artifact(output/name)
        if actual['sha256']!=expected.get('sha256') or actual['bytes']!=expected.get('bytes'):raise RuntimeError('Completed checkpoint bytes differ: '+name)
        checkpoints[name]=actual
    return {'seed':declared['seed'],'plan':declared['plan'],'output_directory':str(output),'training_files':evidence,
            'checkpoints':checkpoints,'optimizer_counts':counts,'checkpoint_sha256_source':'computed from completed local files at bind time',
            'tensor_coverage':'not loaded at binding; runtime must verify all 395 keys and exact complete/end tensor equality'}

def compare_schema(expected,actual):
    """Pure-Python metadata comparison; also used by the future torch loader."""
    missing=sorted(set(expected)-set(actual));extra=sorted(set(actual)-set(expected))
    different=[key for key in sorted(set(expected)&set(actual)) if expected[key]!=actual[key]]
    if missing or extra or different:raise RuntimeError(f'Strict independent CAMP schema mismatch: missing={missing}, extra={extra}, shape_dtype={different}')
    if len(actual)!=395 or actual.get('model_1.pos_scale')!=((), 'torch.float32'):raise RuntimeError('Independent CAMP requires 395 states including learned scalar pos_scale')
    return {'tensor_count':395,'missing_keys':missing,'unexpected_keys':extra,'shape_dtype_mismatches':different,'schema_adaptation':'none','key_renaming':'none'}
