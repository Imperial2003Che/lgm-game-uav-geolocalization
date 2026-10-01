"""Prepare three actual DAC input plans with stdlib only; never launch a stage."""
import argparse
from copy import deepcopy
import hashlib
import importlib.abc
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
EXECUTION=HERE.parent
CONTROL=EXECUTION/'dac_training_control_v2'
EXPECTED_CONTROL_SHA='09211d0e9871eaa5cd22df2edeb500e30c783867dfe375947a8d3213e7e878ec'
SCIENCE_IMPORTS={'torch','numpy','PIL','cv2','timm','torchvision','scipy','albumentations','transformers','tensorboard','sklearn'}
attempts=[]
class BlockScience(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in SCIENCE_IMPORTS:
            attempts.append(fullname)
            raise RuntimeError('Scientific imports are prohibited in DAC input preparation: '+fullname)

sys.dont_write_bytecode=True
sys.meta_path.insert(0,BlockScience())
sys.path.insert(0,str(CONTROL))
import dac2_contracts as c

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def current_payload():
    return [{'path':p.relative_to(HERE).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)}
        for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='INPUT_PREPARATION_MANIFEST.json']

def expected_outputs(seed):
    return {'output_directory':str(EXECUTION/'dac_independent_runs_v2'/f'seed_{seed}'),
        'profile_directory':str(EXECUTION/'dac_independent_resources_v2'/f'seed_{seed}'),
        'profile_receipt_directory':str(EXECUTION/'dac_independent_receipts_v2'/f'seed_{seed}'/'profile'),
        'training_receipt_directory':str(EXECUTION/'dac_independent_receipts_v2'/f'seed_{seed}'/'train')}

def late_arguments(stage):
    required=[{'argument':'--release-file','value_source':'New release created only after all five registered predecessor stages have completed and all owners exited'},
        {'argument':'--release-sha256','value_source':'SHA-256 of that actual reviewed serial release'}]
    if stage=='train':
        required += [{'argument':'--profile-sha256','value_source':'SHA-256 of actual passed native24 DAC profile.json, not available during input preparation'},
            {'argument':'--profile-receipt-sha256','value_source':'SHA-256 of actual parent lifecycle receipt after observed launcher and science worker exit0'}]
    return required

def prepare(verify_content=False):
    c.require(not (HERE/'INPUT_PREPARATION_MANIFEST.json').exists(),'Inputs already frozen; do not overwrite them')
    c.require(sha(CONTROL/'PREPARATION_MANIFEST.json')==EXPECTED_CONTROL_SHA,'Frozen control v2 manifest changed')
    c.require(not SCIENCE_IMPORTS.intersection(sys.modules),'Science was loaded before the stdlib guard')
    cpu=c.read(c.CPU_RESULT)
    c.require(Path(sys.executable).resolve()==Path(cpu['environment']['executable']).resolve(),'Use the same isolated lgm-camp interpreter as the actual CPU proof')
    # These are process-local declarations for validating the future child contract.
    # No library is imported that can use CUDA; no system/user environment is edited.
    os.environ.update(c.PROCESS_ENV)
    modules=c.runtime_modules()
    actual_environment=modules['input_audit'].environment()
    c.require(actual_environment==cpu['environment'],'Current isolated package metadata differs from genuine CPU proof')
    refs=modules['input_contract'].references()
    inventory=c.Bound.load(refs['data_manifest_path'],refs['data_manifest_sha256'])
    rows=inventory.value['files']
    counts={view:sum(row['path'].startswith(view+'/') for row in rows) for view in ('satellite','drone')}
    c.require(counts=={'satellite':701,'drone':37854} and len(rows)==38555,'Incomplete University training content inventory')
    c.require(inventory.value['identity_count']==701,'Unexpected training identity count')
    scientific=c.science_binding();control=c.control_binding()
    defaults=modules['input_contract'].configuration_defaults()
    records=[];commands=[]
    all_outputs=[]
    for seed in (1,2,3):
        paths=expected_outputs(seed)
        for name,path in paths.items():
            c.require(not Path(path).exists(),'A future stage output already exists: '+path)
            all_outputs.append(Path(path).resolve())
        plan={'schema':'dac-university-training-plan.v2','method':'DAC','seed':seed,
            'science_binding':scientific,'control_binding':control,
            'source_directory':str(c.SCIENCE/'scientific_source'),
            'official_configuration_defaults':deepcopy(defaults),'environment':actual_environment,
            'process_environment':dict(c.PROCESS_ENV),
            'train_root':refs['train_root'],'pretrained':refs['pretrained'],
            'data_manifest_path':refs['data_manifest_path'],'data_manifest_sha256':refs['data_manifest_sha256'],
            'cpu_compatibility_proof':{'path':str(c.CPU_RESULT),'sha256':c.CPU_RESULT_SHA},
            'protocol':{'dataset':'University-1652','training_views':['satellite','drone'],
                'training_identity_count':701,'training_pair_count':37854,'epochs':1,
                'nominal_batch_pairs':24,'resolution':[384,384],'mixed_precision':True,
                'loss_weights':{'InfoNCE':1.0,'classification':0.1,'DSA':0.6},
                'selection':'fixed final epoch; no test-set access or checkpoint selection',
                'scheduler_total_steps':'Original calculation before custom shuffle; actual consumed batches separately recorded'},
            **paths}
        plan_path=HERE/f'seed_{seed}_plan.json'
        c.require(not plan_path.exists(),'Seed plan already exists; no overwrite')
        c.write(plan_path,plan)
        bound=c.Bound.load(plan_path,sha(plan_path))
        # Exact frozen admission API: no model/image/scientific imports. Optional
        # content verification reads image bytes solely for SHA, never decoding them.
        c.validate_plan(bound,check_content=verify_content and seed==1)
        config=modules['input_contract'].make_configuration()
        run=modules['dac_train_runtime'].DACTrainRun(plan,plan_path,HERE/'not_yet_existing_resource_profile')
        captured=[]
        with patch.object(modules['common_runtime'],'write_json',side_effect=lambda path,value:captured.append((str(path),deepcopy(value)))):
            run.configure(config)
        c.require(len(captured)==1 and captured[0][0]==str(Path(paths['output_directory'])/'effective_configuration.json'),'Original runtime configuration capture changed')
        effective=captured[0][1]
        c.require(effective['seed']==seed and effective['epochs']==1 and effective['batch_size']==24 and effective['img_size']==384 and effective['num_workers']==0,'Actual seed configuration deviated from original DAC recipe')
        c.require(effective['weight_infonce']==1.0 and effective['weight_cls']==0.1 and effective['weight_dsa']==0.6,'Official loss weights changed')
        effective_path=HERE/f'seed_{seed}_effective_configuration.json';c.write(effective_path,effective)
        record={'seed':seed,'plan_path':str(plan_path),'plan_sha256':bound.sha256,
            'effective_configuration_path':str(effective_path),'effective_configuration_sha256':sha(effective_path),
            'validate_plan_passed':True,'check_content':bool(verify_content and seed==1),
            'future_stage_outputs_not_created':paths}
        records.append(record)
        for stage in ('profile','train'):
            argv=['-B',str(CONTROL/'run_dac_stage.py'),'--stage',stage,'--plan',str(plan_path),'--plan-sha256',bound.sha256]
            if stage=='train':
                argv += ['--profile',str(Path(paths['profile_directory'])/'profile.json'),
                    '--profile-receipt',str(Path(paths['profile_receipt_directory'])/'lifecycle.json')]
            commands.append({'seed':seed,'stage':stage,'executable':actual_environment['executable'],
                'working_directory':str(CONTROL),'argv_with_all_currently_known_values':argv,
                'process_environment':dict(c.PROCESS_ENV),'late_bound_arguments_required':late_arguments(stage),
                'runnable_now':False,'scheduled':False})
        bound.unchanged()
    c.require(len(set(all_outputs))==12,'Stage output paths collide between seeds')
    c.require(all(not (left!=right and left.is_relative_to(right)) for left in all_outputs for right in all_outputs),'Stage outputs overlap by ancestry')
    c.require(all(not p.exists() for p in all_outputs),'Input preparation created a future run directory')
    c.require(not attempts and not SCIENCE_IMPORTS.intersection(sys.modules),'Scientific import occurred during input preparation')
    c.write(HERE/'COMMAND_SPECIFICATIONS.json',{'schema':'dac-stage-command-specifications.v2',
        'commands':commands,'note':'All six command specifications deliberately lack actual future release/profile SHA values. This file is not an active queue.'})
    report={'schema':'dac-three-seed-input-validation.v2','status':'passed','validated_utc':c.utc(),
        'interpreter':sys.executable,'environment':actual_environment,'seeds':records,
        'control_manifest_sha256':EXPECTED_CONTROL_SHA,'science_manifest_sha256':c.SCIENCE_MANIFEST_SHA,
        'real_cpu_result_sha256':c.CPU_RESULT_SHA,'inventory_sha256':inventory.sha256,
        'inventory_counts':counts,'inventory_total_unique_images':len(rows),
        'inventory_full_images_rehashed':verify_content,'pretrained_bytes_rehashed_by_frozen_admission':True,
        'original_DACTrainRun_configure_checked_without_output_side_effects':True,
        'scientific_import_attempts':attempts,'scientific_modules_loaded':sorted(SCIENCE_IMPORTS.intersection(sys.modules)),
        'cuda_executed':False,'new_model_or_image_decoding':False,'stages_launched':0,
        'future_profile_or_weight_hashes_fabricated':False,'active_queue_or_release_created':False,
        'future_output_directories_created':False}
    c.write(HERE/'INPUT_VALIDATION.json',report)
    payload=current_payload()
    c.write(HERE/'INPUT_PREPARATION_MANIFEST.json',{'schema':'dac-three-seed-input-preparation.v2',
        'status':'prepared_not_registered','prepared_utc':c.utc(),'files':payload,
        'payload_files':len(payload),'payload_bytes':sum(row['bytes'] for row in payload),
        'seeds':records,'control_manifest_sha256':EXPECTED_CONTROL_SHA,
        'science_manifest_sha256':c.SCIENCE_MANIFEST_SHA,'actual_profile_results_available':False,
        'actual_final_checkpoints_available':False,'active_queue_or_release_created':False})
    print(json.dumps({'status':'prepared_not_registered','seeds':[{'seed':row['seed'],'plan_sha256':row['plan_sha256']} for row in records],
        'manifest_sha256':sha(HERE/'INPUT_PREPARATION_MANIFEST.json'),'scientific_imports':False,'stage_launches':0}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-content',action='store_true',help='Rehash every existing training image once using stdlib only; never decode images')
    args=parser.parse_args();prepare(args.verify_content)
