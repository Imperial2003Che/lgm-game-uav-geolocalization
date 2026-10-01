"""Independent read-only three-seed input audit. Never configure, stage, or science."""
import ast
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.abc
import json
import os
from pathlib import Path
import sys

OUT=Path(__file__).resolve().parent
EXECUTION=OUT.parent
INPUTS=EXECUTION/'dac_training_inputs_v2'
CONTROL=EXECUTION/'dac_training_control_v2'
SCIENCE=EXECUTION/'dac_training_preparation_v1'
EXPECTED_INPUT='0052a0e96f8124e1f0978fb574e4535207e2539acb75ec4f45eedc2f424dfc4f'
EXPECTED_CONTROL='09211d0e9871eaa5cd22df2edeb500e30c783867dfe375947a8d3213e7e878ec'
EXPECTED_SCIENCE='169a6eb7c351acc7e291b4ceefdecebda2c80ad70b46a20eeed6d42d14e72bc9'
EXPECTED_CPU='5d1cb509088bb65a8ea5f22d1d7cfc482619bd3c61e0192f4c7aba5b8d094e25'
BLOCKED={'torch','torchvision','numpy','PIL','cv2','timm','albumentations','scipy','sklearn','transformers','tensorboard'}
ATTEMPTS=[];sys.dont_write_bytecode=True
class NoScientific(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in BLOCKED:
            ATTEMPTS.append(fullname);raise RuntimeError('Scientific import forbidden in independent input audit: '+fullname)
sys.meta_path.insert(0,NoScientific())
def require(value,message):
    if not value:raise AssertionError(message)
def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def snapshot(root):return {p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file()}
require(not BLOCKED.intersection(sys.modules),'Science was already loaded at startup')
initial={str(root):snapshot(root) for root in (INPUTS,CONTROL,SCIENCE)}
manifest_path=INPUTS/'INPUT_PREPARATION_MANIFEST.json';manifest=read(manifest_path)
require(sha(manifest_path)==EXPECTED_INPUT,'Input manifest SHA differs from requested immutable version')
require(sha(CONTROL/'PREPARATION_MANIFEST.json')==EXPECTED_CONTROL,'Control manifest changed')
require(sha(SCIENCE/'PREPARATION_MANIFEST.json')==EXPECTED_SCIENCE,'Scientific preparation changed')
require(manifest['status']=='prepared_not_registered' and manifest['payload_files']==10,'Input scope/count mismatch')
checks=[]
for row in manifest['files']:
    path=(INPUTS/row['path']).resolve()
    require(path.is_relative_to(INPUTS.resolve()) and sha(path)==row['sha256'] and path.stat().st_size==row['bytes'],'Input payload differs: '+row['path'])
    checks.append({'check':'payload_hash_and_size','path':row['path'],'passed':True})
require(len({row['path'] for row in manifest['files']})==10 and sum(row['bytes'] for row in manifest['files'])==manifest['payload_bytes'],'Payload table duplicates or byte mismatch')
require(set(initial[str(INPUTS)])=={row['path'] for row in manifest['files']}|{'INPUT_PREPARATION_MANIFEST.json'},'Unexpected file outside input seal')

sys.path.insert(0,str(CONTROL))
import dac2_contracts as c
require(c.SCIENCE_MANIFEST_SHA==EXPECTED_SCIENCE and c.CPU_RESULT_SHA==EXPECTED_CPU,'Frozen contracts use unexpected science/CPU anchor')
cpu=c.read(c.CPU_RESULT)
require(Path(sys.executable).resolve()==Path(cpu['environment']['executable']).resolve(),'Audit must use exact registered interpreter')
# Only this audit process receives the frozen declarations. No scientific library
# can use them; system/user environment settings and files remain untouched.
os.environ.update(c.PROCESS_ENV)
science_binding=c.science_binding();control_binding=c.control_binding()
require(control_binding['manifest_sha256']==EXPECTED_CONTROL and science_binding['manifest_sha256']==EXPECTED_SCIENCE,'Live bindings mismatch sealed inputs')
modules=c.runtime_modules()
defaults=modules['input_contract'].configuration_defaults()
references=modules['input_contract'].references()
require(defaults['seed']==1,'Original scientific default seed changed')
plans={};effective={};outputs=[];seed_results=[]
output_keys=('output_directory','profile_directory','profile_receipt_directory','training_receipt_directory')
for record in manifest['seeds']:
    seed=record['seed'];require(type(seed) is int and seed in (1,2,3),'Invalid seed')
    path=Path(record['plan_path']);bound=c.Bound.load(path,record['plan_sha256'])
    require(path.resolve()==(INPUTS/f'seed_{seed}_plan.json').resolve(),'Seed plan path mismatch')
    plan=bound.value;plans[seed]=plan
    require(plan['seed']==seed and plan['science_binding']==science_binding and plan['control_binding']==control_binding,'Plan seed/code binding mismatch')
    require(plan['cpu_compatibility_proof']=={'path':str(c.CPU_RESULT),'sha256':EXPECTED_CPU},'Plan has wrong genuine CPU proof')
    require(plan['official_configuration_defaults']==defaults,'One seed changed official science defaults')
    for name in ('train_root','pretrained','data_manifest_path','data_manifest_sha256'):
        require(plan[name]==references[name],'Prepared scientific input differs: '+name)
    require(not ({'release_sha256','profile_sha256','profile_receipt_sha256','checkpoint_sha256','weights_sha256'} & set(plan)),'Future output hash was supplied before a result exists')
    # Real frozen validator, stdlib only. No patching of contracts or environment
    # metadata; deliberate check_content=False does not walk/re-read image bytes.
    validated,returned_modules,inventory,proof,artifacts=c.validate_plan(bound,check_content=False)
    require(validated==plan and proof.sha256==EXPECTED_CPU,'Frozen admission did not return these inputs')
    for name in output_keys:
        output=Path(plan[name]).resolve();outputs.append(output)
        require(output.is_relative_to(EXECUTION.resolve()) and not output.is_relative_to(CONTROL.resolve()) and not output.is_relative_to(SCIENCE.resolve()),'Future output targets source')
        require(not output.exists(),'Future stage output already exists: '+str(output))
    ep=Path(record['effective_configuration_path'])
    require(sha(ep)==record['effective_configuration_sha256'],'Effective config hash mismatch')
    ef=read(ep);effective[seed]=ef
    expected=deepcopy(defaults)
    expected.update(seed=seed,device='cuda:0',gpu_ids=[0],num_workers=0,
        query_folder_train=str(Path(plan['train_root'])/'satellite'),gallery_folder_train=str(Path(plan['train_root'])/'drone'),
        model_path=plan['output_directory'],data_folder=plan['train_root'])
    require(ef==expected,'Effective config differs from declared original recipe and allowed process/path settings')
    require(ef['batch_size']==24 and ef['epochs']==1 and ef['img_size']==384 and ef['weight_infonce']==1.0 and ef['weight_cls']==0.1 and ef['weight_dsa']==0.6,'Scientific protocol mismatch')
    require(record['check_content'] is False and record['validate_plan_passed'] is True,'Prepared validation scope overclaims image rehash')
    seed_results.append({'seed':seed,'plan_sha256':bound.sha256,'effective_configuration_sha256':sha(ep),'validate_plan_passed':True,
        'check_content':False,'configure_called_by_reviewer':False,'actual_scientific_imports':[],'future_outputs_absent':[str(Path(plan[key]).resolve()) for key in output_keys]})
require(set(plans)=={1,2,3},'Seed coverage incomplete')
variable_keys={'seed',*output_keys}
common_plans=[{key:value for key,value in plans[seed].items() if key not in variable_keys} for seed in (1,2,3)]
require(common_plans[0]==common_plans[1]==common_plans[2],'Plans differ outside seed and output paths')
common_effective=[{key:value for key,value in effective[seed].items() if key not in {'seed','model_path'}} for seed in (1,2,3)]
require(common_effective[0]==common_effective[1]==common_effective[2],'Effective recipes differ outside actual seed/model output')
require(len(set(outputs))==12 and all(not(a!=b and a.is_relative_to(b)) for a in outputs for b in outputs),'Future output paths collide or overlap')

commands=read(INPUTS/'COMMAND_SPECIFICATIONS.json')
require(len(commands['commands'])==6,'Expected profile/train for each of three seeds')
seen=set()
for command in commands['commands']:
    seed,which=command['seed'],command['stage'];require((seed,which) not in seen,'Duplicate command');seen.add((seed,which))
    plan=plans[seed];argv=command['argv_with_all_currently_known_values']
    require(command['runnable_now'] is False and command['scheduled'] is False,'Unsupplied command claims ready/scheduled')
    require(command['executable']==plan['environment']['executable'] and command['working_directory']==str(CONTROL),'Command wrong runtime')
    require(command['process_environment']==plan['process_environment']==c.PROCESS_ENV,'Command process env differs')
    expected=['-B',str(CONTROL/'run_dac_stage.py'),'--stage',which,'--plan',str(INPUTS/f'seed_{seed}_plan.json'),'--plan-sha256',sha(INPUTS/f'seed_{seed}_plan.json')]
    late={'--release-file','--release-sha256'}
    if which=='train':
        expected+=['--profile',str(Path(plan['profile_directory'])/'profile.json'),'--profile-receipt',str(Path(plan['profile_receipt_directory'])/'lifecycle.json')]
        late|={'--profile-sha256','--profile-receipt-sha256'}
    require(argv==expected and {row['argument'] for row in command['late_bound_arguments_required']}==late,'Command contains fabricated/missing inputs')
    require(not late.intersection(argv),'Future release/profile evidence unexpectedly supplied')
require(seen=={(s,t) for s in (1,2,3) for t in ('profile','train')},'Command matrix incomplete')

# Read the preparer as AST only; never execute its writes/configure or import it.
tree=ast.parse((INPUTS/'prepare_inputs_stdlib.py').read_text(encoding='utf-8'))
calls=[node for node in ast.walk(tree) if isinstance(node,ast.Call)]
validate_calls=[node for node in calls if ast.unparse(node.func)=='c.validate_plan']
require(len(validate_calls)==1 and any(arg.arg=='check_content' and ast.unparse(arg.value)=='verify_content and seed == 1' for arg in validate_calls[0].keywords),'Preparer validation scope differs from declaration')
configure_calls=[node for node in calls if ast.unparse(node.func)=='run.configure']
guarded=[node for node in ast.walk(tree) if isinstance(node,ast.With) and 'patch.object' in ast.unparse(node) and "'write_json'" in ast.unparse(node)]
require(len(configure_calls)==1 and any(configure_calls[0] in list(ast.walk(node)) for node in guarded),'Preparer configure write was not captured')
require(not any(isinstance(node,ast.Call) and (ast.unparse(node.func) in {'subprocess.Popen','subprocess.run','runpy.run_path','child','supervise_one'}) for node in ast.walk(tree)),'Input preparer launches a stage')
author_validation=read(INPUTS/'INPUT_VALIDATION.json')
require(author_validation['inventory_full_images_rehashed'] is False and author_validation['pretrained_bytes_rehashed_by_frozen_admission'] is True,'Image/pretrained verification scope mislabeled')
require(author_validation['scientific_modules_loaded']==author_validation['scientific_import_attempts']==[] and author_validation['stages_launched']==0,'Preparation claims actual science or stage execution')
require(not manifest['actual_profile_results_available'] and not manifest['actual_final_checkpoints_available'] and not manifest['active_queue_or_release_created'],'Future evidence claims must remain false')

queue_refs=[];queue_files=[]
for path in EXECUTION.glob('*.json'):
    if not any(word in path.name.lower() for word in ('queue','plan','status')):continue
    text=path.read_text(encoding='utf-8').replace('\\\\','/').replace('\\','/').lower()
    queue_files.append(str(path))
    if 'dac_training_inputs_v2' in text or 'dac_training_control_v2/run_dac_stage.py' in text:queue_refs.append(str(path))
require(not queue_refs,'Top-level active execution registry references these new DAC plans')
require(not ATTEMPTS and not BLOCKED.intersection(sys.modules) and 'run_dac_stage' not in sys.modules,'Unexpected scientific/stage import')
require(all(snapshot(Path(root))==files for root,files in initial.items()),'A sealed input/control/science file changed during the audit')
require(all(not p.exists() for p in outputs),'Audit created future output directories')
report={'schema':'dac-input-plans-independent-verification.v1','status':'passed','verified_utc':datetime.now(timezone.utc).isoformat(),
    'manifest_path':str(manifest_path),'manifest_sha256':EXPECTED_INPUT,'payload_files':10,'payload_bytes':manifest['payload_bytes'],
    'control_manifest_sha256':EXPECTED_CONTROL,'science_manifest_sha256':EXPECTED_SCIENCE,'real_cpu_result_sha256':EXPECTED_CPU,
    'interpreter':sys.executable,'seed_results':seed_results,'configuration_equivalence':{'plan_variable_keys':sorted(variable_keys),'effective_configuration_variable_keys':['seed','model_path'],'all_other_values_identical':True},
    'command_specifications':{'count':6,'known_values_all_match_real_plan_files':True,'future_release_and_profile_SHA_values_unsupplied':True,'runnable_or_scheduled':False},
    'future_output_paths':{'count':12,'all_absent':True,'all_unique_and_nonoverlapping':True,'none_inside_scientific_or_control_source':True},
    'validation_scope':{'actual_validate_plan_calls':3,'check_content':False,'full_image_bytes_rehashed':False,'image_decoding':False,'pretrained_file_bytes_hashed':True,
        'actual_environment_metadata_checked':True,'source_and_input_manifests_checked':True,'genuine_cpu_result_and_raw_artifacts_checked':True,'configure_called':False,'stage_called':False,'gpu_api_called':False},
    'preparer_AST_scope_matches_documentation':True,'top_level_execution_registry_files_read':queue_files,'active_new_DAC_plan_references':queue_refs,
    'sealed_inputs_control_science_all_unchanged':True,'scientific_import_attempts':ATTEMPTS,'scientific_modules_loaded':sorted(BLOCKED.intersection(sys.modules)),
    'payload_checks':checks,'limitations':['No full image content rescan in this audit; manifest SHA and original pretrained bytes were checked by frozen admission.','No model, augmentation, CUDA, native profile, training, evaluation, queue or release was executed.','Registry/path absence is a read-only snapshot at verified_utc, not a future scheduling assertion.']}
(OUT/'INPUT_PLANS_VERIFICATION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':'passed','seed_count':3,'command_count':6,'future_outputs_absent':12,'scientific_imports':[],'report':str(OUT/'INPUT_PLANS_VERIFICATION.json')},ensure_ascii=False))
