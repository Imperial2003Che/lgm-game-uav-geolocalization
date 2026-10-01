"""Actual pure-function negative fixtures and AST checks; no scientific imports."""
import ast
import copy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch
import protocol as p

HERE=Path(__file__).resolve().parent;checks=[]
def check(name,ok):
    checks.append({'name':name,'passed':bool(ok)})
    if not ok:raise AssertionError(name)
def rejects(name,fn):
    try:fn()
    except (RuntimeError,ValueError,KeyError,TypeError,FileNotFoundError):check(name,True)
    else:check(name,False)
def astfn(path,name):return next(n for n in ast.parse(path.read_text('utf-8')).body if isinstance(n,ast.FunctionDef) and n.name==name)
def dump(node):return ast.dump(node,include_attributes=False)

for name in ('protocol.py','run_evaluation.py','dac_independent_model.py','complete_state_checks.py'):
    source=(HERE/name).read_text('utf-8');tree=ast.parse(source);compile(tree,name,'exec')
    imports=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]
    forbidden={'torch','numpy','PIL','cv2','scipy','timm','transformers','albumentations'}
    check(name+'_no_module_level_science',all((n.module or '').split('.')[0] not in forbidden if isinstance(n,ast.ImportFrom) else all(a.name.split('.')[0] not in forbidden for a in n.names) for n in imports))
check('all_existing_source_pins_verified',len(p.source_evidence()['files'])==112)
member=p.membership_evidence();tasks=p.load(member['tasks']['path']);inventory=p.load(member['inventory']['path'])
check('full_131062_image_inventory',len(inventory)==131062)
check('ten_tasks_each_seed_thirty_total',len(tasks)==10 and len(tasks)*len(p.SEEDS)==30)
check('all_distractor_locations_preserved',[t['distractor_identity_count'] for t in tasks]==[250,250]+[120]*8)
task_counts=[{'name':t['name'],'query':len(t['query_indices']),'gallery':len(t['gallery_indices']),'distractors':t['distractor_identity_count']} for t in tasks]
check('university_query_gallery_counts',[(x['query'],x['gallery']) for x in task_counts[:2]]==[(37855,951),(701,51355)])
check('sues_all_height_query_gallery_counts',[(x['query'],x['gallery']) for x in task_counts[2:]]==[(4000,200),(80,10000)]*4)
check('official_dac_transform_delegated','h.make_validation_transform()' in (HERE/'run_evaluation.py').read_text('utf-8'))
check('official_dac_rank_and_per_query_revalidation_delegated','h.rank_with_query_evidence' in (HERE/'run_evaluation.py').read_text('utf-8') and 'h.validate_query_arrays' in (HERE/'run_evaluation.py').read_text('utf-8'))

schema={k:(tuple(v['shape']),v['dtype']) for k,v in p.load(p.TRAIN/'DAC_EXPECTED_MODEL_SCHEMA.json')['tensors'].items()}
check('exact_DAC402_accepted',p.compare_schema(schema,schema)['tensor_count']==402)
for label,bad in [('395_keys',dict(list(schema.items())[:395])),('394_keys',dict(list(schema.items())[:394])),('344_backbone_only',dict(list(schema.items())[:344]))]:rejects('reject_'+label,lambda bad=bad:p.compare_schema(schema,bad))
for head in ('classifier1','classifier_mcb1','classifier_mcb2'):
    key=next(k for k in schema if f'.{head}.' in k);bad=dict(schema);del bad[key];rejects('reject_removed_'+head,lambda bad=bad:p.compare_schema(schema,bad))
for key in ('model_1.proj.mlp.0.weight','model_1.proj_obj.mlp.0.weight'):
    check('DSA_projection_key_present_'+key,key in schema)
    bad=dict(schema);del bad[key];rejects('reject_removed_DSA_projection_'+key,lambda:p.compare_schema(schema,bad))
key=next(iter(schema));bad=dict(schema);bad[key]=((1,),'torch.float64');rejects('reject_shape_dtype_change',lambda:p.compare_schema(schema,bad))
loader=(HERE/'dac_independent_model.py').read_text('utf-8');tree=ast.parse(loader)
calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
loads=[n for n in calls if isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='torch' and n.func.attr=='load']
check('two_restricted_mmap_CPU_loads',len(loads)==2 and all({k.arg:ast.literal_eval(k.value) for k in n.keywords}=={'map_location':'cpu','weights_only':True,'mmap':True} for n in loads))
strict=[n for n in calls if isinstance(n.func,ast.Attribute) and n.func.attr=='load_state_dict']
check('strict_full402_assignment_only',len(strict)==1 and {k.arg:ast.literal_eval(k.value) for k in strict[0].keywords}=={'strict':True,'assign':True})
check('no_author_checkpoint_or_compatibility_loader',all(x not in loader for x in ('CHECKPOINT_SHA','CHECKPOINT=','validate_checkpoint_state','build_camp_model','author_checkpoint_schema=')))
check('bytewise_complete_final_equality','left.view(torch.uint8)' in loader and 'right.view(torch.uint8)' in loader and 'torch.equal' in loader)
check('extra_complete_optimizer_check_called','validate_full_training_state(complete,binding,torch)' in loader)

n=1577;a=1575;seed=2
status={'status':'completed','epoch_completed':1,'selection':'fixed final epoch','test_data_read':False,'actual_adamw_steps':a,'optimizer_step_attempts':n,'amp_skips':n-a}
evidence={'actual_adamw_steps':a,'attempted_batches':n,'amp_skips':n-a,'epoch_loss':1.2,'all_model_floating_state_finite':True,'representative_parameter_changed':True,'initial_parameter_sha256':'1'*64,'final_parameter_sha256':'2'*64}
config=p.load(p.INPUTS/'seed_2_effective_configuration.json')
protocol={'method':'DAC','model_state_count':402,'epoch':1,'scheduler_steps_planned_before_shuffle':1578,'warmup_steps_planned_before_shuffle':157.8,'actual_loader_batches':n,'scheduler_attempts':n,'actual_adamw_steps':a,'amp_skips':n-a,'optimizer_step_min':a,'optimizer_step_max':a,'all_optimizer_moments_finite':True,'test_set_read_or_model_selection':False}
sampling={'official_pair_count':37854,'expected_batches':n,'nominal_pairs_per_batch':24,'sample_count':n*24,'excluded_tail_pairs':37854-n*24}
trace=[{'epoch':1,'batch_attempt':i,'actual_optimizer_steps':min(i,a),'amp_skips':i-min(i,a),'optimizer_updated_this_batch':i<=a,'loss_finite':True,'loss':1.2,'scale_after_update':65536.0,'lr_after_scheduler':0.001} for i in range(1,n+1)]
base=[status,evidence,config,seed,protocol,sampling,trace]
check('full_epoch_original_trace_and_AMP_skips_accepted',p.validate_training_evidence(*base)=={'actual_adamw_steps':a,'attempted_batches':n,'amp_skips':2})
for label,pos,key,value in [('unfinished_epoch',0,'epoch_completed',0),('test_selection',0,'test_data_read',True),('no_updates',1,'actual_adamw_steps',0),('bool_update',1,'actual_adamw_steps',True),('nonfinite_loss',1,'epoch_loss',float('nan')),('unchanged_parameters',1,'final_parameter_sha256','1'*64),('wrong_seed',2,'seed',1),('CAMP_schema',4,'model_state_count',395),('wrong_loss_method',4,'method','CAMP'),('wrong_scheduler',4,'scheduler_attempts',n-1),('missing_optimizer_finite',4,'all_optimizer_moments_finite',False),('wrong_planned_steps',4,'scheduler_steps_planned_before_shuffle',1577),('sample_count_drift',5,'sample_count',n*24-1)]:
    args=copy.deepcopy(base);args[pos][key]=value;rejects(label,lambda args=args:p.validate_training_evidence(*args))
args=copy.deepcopy(base);args[6].pop();rejects('missing_final_batch_trace',lambda:p.validate_training_evidence(*args))
args=copy.deepcopy(base);args[6][1]['actual_optimizer_steps']=20;rejects('impossible_hook_jump',lambda:p.validate_training_evidence(*args))
args=copy.deepcopy(base);args[6][1]['lr_after_scheduler']=float('nan');rejects('nonfinite_scheduler_lr',lambda:p.validate_training_evidence(*args))
args=copy.deepcopy(base);args[0]['epoch_completed']=True;rejects('bool_completed_epoch',lambda:p.validate_training_evidence(*args))

import complete_state_checks as cc
class FakeTensor:
    def __init__(self,values):self.values=list(values);self.device=SimpleNamespace(type='cpu')
    def reshape(self,*args):return self
    def numel(self):return len(self.values)
    def __getitem__(self,index):return FakeTensor(self.values[index])
    def all(self):return all(self.values)
fake_torch=SimpleNamespace(Tensor=FakeTensor,isfinite=lambda tensor:FakeTensor([__import__('math').isfinite(v) for v in tensor.values]))
complete={'optimizer':{'state':{0:{'step':a,'exp_avg':FakeTensor([1.0,2.0]),'exp_avg_sq':FakeTensor([1.0,2.0])}},'param_groups':[{'params':[0]}]},'scheduler':{'last_epoch':n},'scaler':{'scale':65536.0},'training_evidence':{'final_scaler_state':{'scale':65536.0}},'scheduler_total_steps_before_initial_shuffle':1578,'warmup_steps':157.8,'rng':{'python':{},'numpy':{},'torch_cpu':{},'torch_cuda':[{}]},'sampler':{'pairs':[0]*37854,'shuffle_batch_size':24,'samples_for_next_epoch':[0]*24}}
binding={'training_files':{'dac_training_protocol_evidence.json':{'path':'fake_protocol'},'epoch01_sampling.json':{'path':'fake_sampling'}},'optimizer_counts':{'actual_adamw_steps':a,'attempted_batches':n}}
with patch.object(cc,'load',side_effect=lambda path:protocol if path=='fake_protocol' else sampling):
    cc.validate_full_training_state(complete,binding,fake_torch);check('actual_complete_state_validator_fake_tensor_fixture',True)
    for label,mutate in [('missing_moment',lambda x:x['optimizer']['state'][0].pop('exp_avg')),('wrong_moment_step',lambda x:x['optimizer']['state'][0].update(step=a-1)),('nonfinite_moment',lambda x:x['optimizer']['state'][0].update(exp_avg=FakeTensor([float('inf')]))),('wrong_scheduler_attempts',lambda x:x['scheduler'].update(last_epoch=n-1)),('wrong_scaler',lambda x:x['scaler'].update(scale=1.0)),('missing_CUDA_rng',lambda x:x['rng'].update(torch_cuda=[])),('missing_pairs',lambda x:x['sampler'].update(pairs=[])),('missing_next_samples',lambda x:x['sampler'].update(samples_for_next_epoch=[]))]:
        bad=copy.deepcopy(complete);mutate(bad);rejects('complete_state_'+label,lambda bad=bad:cc.validate_full_training_state(bad,binding,fake_torch))

fake_c=SimpleNamespace(number=lambda value,minimum,integer:p.require(type(value) is int and value>=minimum,'Invalid PID'))
row={'pid':42,'started_utc':'2026-09-14T10:00:00+00:00','finished_utc':'2026-09-14T10:01:00+00:00'}
for label,actual,accepted in [('absent_owner',None,True),('later_reused_PID','2026-09-14T10:02:00+00:00',True),('same_live_owner','2026-09-14T10:00:00+00:00',False),('older_live_PID','2026-09-14T09:00:00+00:00',False),('ambiguous_within_lifecycle','2026-09-14T10:00:30+00:00',False)]:
    with patch.object(p,'controls',return_value=(fake_c,SimpleNamespace(process_started=lambda pid,actual=actual:actual))):
        if accepted:p.exited(row,'pid','started_utc',label);check(label,True)
        else:rejects(label,lambda:p.exited(row,'pid','started_utc',label))
run=(HERE/'run_evaluation.py').read_text('utf-8');run_tree=ast.parse(run)
check('three_seeds_included_in_summary',"['1','2','3']" in run and 'statistics.stdev' in run and 'values_by_seed' in run)
check('all_6_primary_metrics_and_named_alternate_AP',all(x in run for x in ('r_at_1','r_at_5','r_at_10','r_at_20','official_trapezoid_mAP','MRR','rank_precision_mAP')))
check('training_supervision_rechecked_before_and_after_binding',sum(1 for n in ast.walk(astfn(HERE/'run_evaluation.py','completion_and_bindings')) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='verify_completed_supervision')==2)
check('external_package_and_spec_SHA_required',"--training-package-sha256" in run and "--training-execution-sha256" in run)
check('only_future_checkpoint_hash_none_at_prepare',"'checkpoint_sha256':None" in run)
check('all_seeds_decode_same_image_bytes',"len(set(image_hashes))==1" in run)
prepared={'training_execution_plan':{'path':str(p.TRAIN_EXECUTION/'execution_spec.json'),'sha256':'e'*64},'training_plans':[]}
lookup={};hashes={};jobs=[]
for seed in (1,2,3):
    plan_path=p.INPUTS/f'seed_{seed}_plan.json';plan=p.load(plan_path);plan_sha=p.sha(plan_path)
    prepared['training_plans'].append({'seed':seed,'plan':{'path':str(plan_path),'sha256':plan_sha},'output_directory':plan['output_directory']})
    lookup[str(plan_path)]=plan
    for stage in ('profile','train'):
        out=Path(plan['profile_directory' if stage=='profile' else 'output_directory'])
        life_path=Path(plan['profile_receipt_directory' if stage=='profile' else 'training_receipt_directory'])/'lifecycle.json'
        result=out/('profile.json' if stage=='profile' else 'checkpoint_manifest.json')
        stamp='2026-09-14T10:00:00+00:00';finished='2026-09-14T10:01:00+00:00'
        job={'id':f'seed_{seed}_{stage}','seed':seed,'stage':stage,'status':'completed','exit_code':0,'plan_path':str(plan_path),'plan_sha256':plan_sha,'output_directory':str(out),'launcher_pid':100+len(jobs),'launcher_started_utc':stamp,'launcher_exit_code':0,'supervisor_pid':200+len(jobs),'supervisor_started_utc':stamp,'supervisor_exit_code':0,'control_receipt_path':str(life_path),'control_receipt_sha256':'a'*64,'finished_utc':finished}
        life={'schema':'dac-stage-lifecycle.v2','stage':stage,'status':'completed','plan_sha256':plan_sha,'pid':job['supervisor_pid'],'started_utc':stamp,'launcher_pid':300+len(jobs),'launcher_started_utc':stamp,'launcher_exit_code':0,'child_pid':400+len(jobs),'child_started_utc':stamp,'exit_code':0,'finished_utc':finished,'result_path':str(result),'result_sha256':'b'*64,'status_sha256':'c'*64}
        lookup[str(life_path)]=life;hashes[str(life_path)]='a'*64;hashes[str(result)]='b'*64;hashes[str(out/'status.json')]='c'*64;jobs.append(job)
state={'schema':'dac-six-stage-execution-status.v2','status':'completed','exit_code':0,'execution_spec_path':prepared['training_execution_plan']['path'],'execution_spec_sha256':'e'*64,'controller_pid':99,'controller_started_utc':stamp,'finished_utc':finished,'jobs':jobs}
owners=[]
with patch.object(p,'load',side_effect=lambda path:copy.deepcopy(lookup[str(path)])),patch.object(p,'sha',side_effect=lambda path:hashes[str(path)]):
    check('actual_six_stage_completion_function_accepts_all_bound_owners',len(p.validate_training_completion(state,prepared,lambda row,pk,sk,label:owners.append((row[pk],row[sk]))))==6)
    check('all_31_owner_exit_checks_requested',len(owners)==31)
    for label,mutate in [('missing_seed3',lambda x:x['jobs'].pop()),('reordered_stages',lambda x:x['jobs'].reverse()),('top_incomplete',lambda x:x.update(status='running')),('bool_top_exit',lambda x:x.update(exit_code=False)),('wrong_execution_sha',lambda x:x.update(execution_spec_sha256='f'*64)),('failed_launcher',lambda x:x['jobs'][1].update(launcher_exit_code=1)),('bool_supervisor_exit',lambda x:x['jobs'][1].update(supervisor_exit_code=False)),('wrong_plan_seed2',lambda x:x['jobs'][3].update(plan_sha256='9'*64)),('wrong_receipt_hash',lambda x:x['jobs'][3].update(control_receipt_sha256='8'*64))]:
        bad=copy.deepcopy(state);mutate(bad);rejects('completion_'+label,lambda bad=bad:p.validate_training_completion(bad,prepared,lambda *args:None))
    rejects('completion_any_owner_still_alive',lambda:p.validate_training_completion(state,prepared,lambda *args:(_ for _ in ()).throw(RuntimeError('fixture live owner'))))
    broken=copy.deepcopy(lookup);broken[jobs[-1]['control_receipt_path']]['exit_code']=1
    with patch.object(p,'load',side_effect=lambda path:copy.deepcopy(broken[str(path)])):
        rejects('completion_failed_actual_scientific_worker',lambda:p.validate_training_completion(state,prepared,lambda *args:None))
check('no_runtime_or_active_release_created',not (HERE/'results').exists() and not (HERE/'runtime').exists() and not (HERE/'controller_release.json').exists())
check('no_scientific_imports',not any(n in sys.modules for n in ('torch','numpy','PIL','cv2','scipy','timm','transformers','albumentations')))
report={'schema':'dac-independent-evaluation-stdlib-validation.v1','created_utc':datetime.now(timezone.utc).isoformat(),'checks':checks,'pass_count':sum(x['passed'] for x in checks),'check_count':len(checks),'task_memberships':task_counts,'model_schema_count':len(schema),'execution_scope':'Actual pure-function mocks/AST/source hashes only; no model, real numerical arrays, GPU, active plan/release/status/queue or checkpoints generated.'}
(HERE/'STDLIB_VALIDATION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':report['pass_count'],'total':report['check_count']},indent=2))
