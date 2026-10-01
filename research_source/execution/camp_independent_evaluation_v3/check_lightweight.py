"""AST and pure-Python mocks only. Scientific imports are actively forbidden."""
import ast
import copy
import importlib.abc
import json
from pathlib import Path
import sys
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
BLOCKED={'torch','numpy','scipy','cv2','PIL','timm','albumentations','sklearn','matplotlib','pptx'}
class NoScientificImports(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in BLOCKED:raise RuntimeError('Scientific import forbidden in lightweight audit: '+fullname)
guard=NoScientificImports();sys.meta_path.insert(0,guard);sys.path.insert(0,str(HERE));sys.dont_write_bytecode=True
import protocol as p
import run_evaluation as r
import camp_independent_model as model_module

checks=[]
def passed(name):checks.append(name)
def reject(label,call):
    try:call()
    except (RuntimeError,ValueError,KeyError):passed(label)
    else:raise AssertionError('Expected rejection: '+label)

for name in ('protocol.py','run_evaluation.py','camp_independent_model.py'):
    tree=ast.parse((HERE/name).read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            names=[a.name for a in node.names] if isinstance(node,ast.Import) else [node.module or '']
            assert not any(n.split('.')[0] in BLOCKED for n in names)
passed('All delivered modules parse and import using standard library only')
sources=p.source_evidence();passed('Pinned original model, reviewed ranking helper, split and training preparation hashes match')
helper=p.helpers();assert not any(name in sys.modules for name in BLOCKED)
passed('Importing the reviewed ranking-helper definitions executes no scientific import')

tree=ast.parse((HERE/'camp_independent_model.py').read_text(encoding='utf-8'))
builds=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='build_camp_model']
assert len(builds)==1
keywords={x.arg:ast.literal_eval(x.value) for x in builds[0].keywords}
assert keywords=={'device':'meta','author_checkpoint_schema':False}
assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ('load_author_model','validate_checkpoint_state') for n in ast.walk(tree))
loads=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='load_state_dict']
assert len(loads)==1 and {x.arg:ast.literal_eval(x.value) for x in loads[0].keywords}=={'strict':True,'assign':True}
torchloads=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='torch' and n.func.attr=='load']
assert len(torchloads)==2
for n in torchloads:
    kw={x.arg:ast.literal_eval(x.value) for x in n.keywords}
    assert kw=={'map_location':'cpu','weights_only':True,'mmap':True}
passed('AST enforces original 395-state construction, no author-schema branch, strict assignment and restricted complete/end reads')

expected={f'fixture_only_{i}':((1,),'torch.float32') for i in range(394)}
expected['model_1.pos_scale']=((),'torch.float32')
assert p.compare_schema(expected,dict(expected))['tensor_count']==395
without_pos={k:v for k,v in expected.items() if k!='model_1.pos_scale'}
reject('Author-like 394-state mapping without learned pos_scale rejected',lambda:p.compare_schema(expected,without_pos))
reject('Extra state key rejected',lambda:p.compare_schema(expected,dict(expected,fixture_extra=((),'torch.float32'))))
wrong=dict(expected);wrong['model_1.pos_scale']=((1,),'torch.float32')
reject('Wrong learned pos_scale shape rejected',lambda:p.compare_schema(expected,wrong))
wrong_dtype=dict(expected);wrong_dtype['model_1.pos_scale']=((),'torch.float64')
reject('Wrong learned pos_scale dtype rejected',lambda:p.compare_schema(expected,wrong_dtype))

proto={'dataset':'University-1652','epochs':1,'nominal_batch_pairs':24,'microbatch_pairs':24,'gradient_accumulation':1,
       'img_size':384,'mixed_precision':True,'num_workers':0,'checkpoint_selection':'complete final epoch','training_test_access':False}
plan={'schema_version':1,'seed':1,'output_directory':str(p.EXECUTION/'camp_independent_runs/seed_1'),
      'source_directory':str(helper.SOURCE),'protocol':proto}
p.validate_training_plan(plan,1);passed('Fixed full-batch one-epoch no-test training plan accepted')
for key,value in [('epochs',2),('microbatch_pairs',12),('gradient_accumulation',2),('training_test_access',True),('checkpoint_selection','best test')]:
    changed=copy.deepcopy(plan);changed['protocol'][key]=value
    reject('Changed training protocol rejected: '+key,lambda q=changed:p.validate_training_plan(q,1))

declared=[];rows=[];stamp='2026-09-14T00:00:00+00:00'
for seed in p.SEEDS:
    path=p.EXECUTION/'camp_training_inputs_v2'/f'seed_{seed}_plan.json'
    output=p.EXECUTION/'camp_independent_runs'/f'seed_{seed}'
    # Hash tokens are mock-only in-memory symbols, never saved as checkpoint bindings.
    declared.append({'seed':seed,'plan':{'path':str(path),'sha256':f'mock_plan_{seed}'},'output_directory':str(output)})
    record={'pid':100+seed,'started_utc':stamp,'finished_utc':stamp,'status':'completed','exit_code':0}
    rows.append({'seed':seed,'plan_path':str(path),'plan_sha256':f'mock_plan_{seed}','output_directory':str(output),
                 'status':'completed','exit_code':0,'training_record':dict(record),'profile_record':dict(record,pid=200+seed)})
contract={'training_execution_plan':{'sha256':'mock_execution_plan'},'training_plans':declared}
state={'schema':'camp-independent-training-status.v1','status':'completed','exit_code':0,'supervisor_pid':10,'started_utc':stamp,'supervisor_started_utc':stamp,
       'plan_sha256':'mock_execution_plan','seeds':rows}
with patch.object(helper,'alive',return_value=False):
    p.validate_training_completion(state,contract,helper.require_process_exit);passed('All three completed registered seeds and exited profile/train owners accepted')
    for label,mutate in [
        ('Pending outer training rejected',lambda s:s.update(status='running')),
        ('Failed outer training rejected',lambda s:s.update(exit_code=1)),
        ('Missing seed rejected',lambda s:s['seeds'].pop()),
        ('Reordered seeds rejected',lambda s:s['seeds'].reverse()),
        ('Seed plan hash mismatch rejected',lambda s:s['seeds'][1].update(plan_sha256='wrong')),
        ('Pending training child rejected',lambda s:s['seeds'][0]['training_record'].update(status='running')),
        ('Failed profile child rejected',lambda s:s['seeds'][0]['profile_record'].update(exit_code=1)),
        ('Missing training PID rejected',lambda s:s['seeds'][0]['training_record'].pop('pid')),
        ('Missing supervisor start rejected',lambda s:s.pop('started_utc'))]:
        changed=copy.deepcopy(state);mutate(changed)
        reject(label,lambda q=changed:p.validate_training_completion(q,contract,helper.require_process_exit))
with patch.object(helper,'alive',return_value=True):
    reject('Live training process rejected',lambda:p.validate_training_completion(state,contract,helper.require_process_exit))

status={'status':'completed','epoch_completed':1,'selection':'fixed final epoch','test_data_read':False,
        'actual_adamw_steps':9,'optimizer_step_attempts':10,'amp_skips':1}
ev={'actual_adamw_steps':9,'attempted_batches':10,'amp_skips':1,'epoch_loss':1.0,
    'all_model_floating_state_finite':True,'representative_parameter_changed':True,
    'initial_parameter_sha256':'mock_initial','final_parameter_sha256':'mock_final'}
configuration={'seed':1,'epochs':1,'nclasses':701}
p.validate_training_evidence(status,ev,configuration,1);passed('Finite trained one-epoch evidence accepted')
for label,changed in [('All optimizer steps skipped rejected',dict(ev,actual_adamw_steps=0)),('Nonfinite loss rejected',dict(ev,epoch_loss=float('nan'))),('Unchanged learned parameter rejected',dict(ev,final_parameter_sha256='mock_initial'))]:
    reject(label,lambda q=changed:p.validate_training_evidence(status,q,configuration,1))
reject('Wrong effective training seed rejected',lambda:p.validate_training_evidence(status,ev,dict(configuration,seed=2),1))

profile={'status':'passed','plan_sha256':'mock_plan','actual_adamw_steps':2,'completed_optimizer_amp_steps':3,'amp_skips':1,
         'nominal_batch_pairs':24,'microbatch_pairs':24,'gradient_accumulation':1,'img_size':384,
         'all_official_losses':True,'mixed_precision':True,'oom':False,'exclusive_gpu_allocation':True}
p.validate_resource_profile(profile,'mock_plan');passed('Profile requires two actual AdamW updates while retaining AMP skip accounting')
for label,changed in [('One actual AdamW profile update rejected',dict(profile,actual_adamw_steps=1,amp_skips=2)),
                     ('Inconsistent profile AMP skips rejected',dict(profile,amp_skips=0)),
                     ('Resource-adapted smaller training batch rejected',dict(profile,microbatch_pairs=12))]:
    reject(label,lambda q=changed:p.validate_resource_profile(q,'mock_plan'))

latest={'status':'latest_baselines_finished_review_pending','plan_sha256':'mock_latest',
        'supervisor_pid':9,'supervisor_started_utc':stamp,
        'jobs':[{'id':name,'status':'completed','exit_code':0,'pid':40+i,'started_utc':stamp} for i,name in enumerate(p.LATEST_IDS)]}
with patch.object(p,'sha',return_value='mock_latest'),patch.object(p,'artifact',return_value={'path':'mock_latest_status','sha256':'mock_latest'}),\
     patch.object(p,'load',side_effect=lambda path:copy.deepcopy(latest)),patch.object(p,'helpers',return_value=helper),patch.object(helper,'alive',return_value=False):
    p.verify_latest_completed({'latest_baseline_plan':{'sha256':'mock_latest'}});passed('Both latest author baselines must finish and exit before independent evaluation')
    latest['jobs'][1]['status']='pending'
    reject('Extensions alone do not permit evaluation while latest DAC job remains pending',lambda:p.verify_latest_completed({'latest_baseline_plan':{'sha256':'mock_latest'}}))
reject('Missing exact evaluation release rejected before GPU query',lambda:r.release_gate({},Path('never_read'),Path('never_read'),None))

parent_contract={'latest_baseline_plan':{'sha256':'mock_latest'},'training_execution_plan':{'sha256':'mock_training'}}
parent={'schema':p.CONTROLLER_RELEASE_SCHEMA,'allow_cuda':True,'prepared_sha256':'mock_prepared',
        'latest_baseline_plan_sha256':'mock_latest','training_execution_plan_sha256':'mock_training',
        'binding_policy':p.BINDING_POLICY,'seeds':[1,2,3],'task_count':30}
with patch.object(r,'load',side_effect=lambda path:copy.deepcopy(parent)),patch.object(r,'sha',return_value='mock_prepared'),patch.object(r,'artifact',return_value={'path':'in_memory_parent'}):
    r.validate_controller_release(parent_contract,Path('mock'),Path('mock'));passed('Parent release authorizes only the exact three-seed complete binding and 30-task policy')
    for key,value in [('allow_cuda',False),('prepared_sha256','wrong'),('latest_baseline_plan_sha256','wrong'),
                      ('training_execution_plan_sha256','wrong'),('binding_policy','select best seed'),('seeds',[1]),('task_count',10)]:
        original=parent[key];parent[key]=value
        reject('Changed parent release rejected: '+key,lambda:r.validate_controller_release(parent_contract,Path('mock'),Path('mock')))
        parent[key]=original
reject('Missing parent release rejected without binding or GPU query',lambda:r.validate_controller_release(parent_contract,Path('mock'),None))

# Orchestration tests mock every side effect. No result/checkpoint/release fixture
# is written; synthetic hash tokens exist only in memory.
mock_output=HERE/'__in_memory_run_not_created'
args=r.argparse.Namespace(prepared=Path('mock_prepared'),training_completion=Path('mock_completion'),
                          controller_release=Path('mock_release'),output_directory=mock_output)
events=[]
with patch.object(r,'read_prepared',return_value=parent_contract),patch.object(Path,'mkdir'),patch.object(Path,'exists',return_value=False),\
     patch.object(r,'save'),patch.object(r,'artifact',side_effect=lambda path:{'path':str(path),'sha256':'mock_only'}),\
     patch.object(r,'sha',return_value='mock_only'),patch.object(r,'verify_artifact'),patch('builtins.print'),\
     patch.object(r,'validate_controller_release',side_effect=lambda *a:(events.append('parent') or {'path':'mock_parent','sha256':'mock_only'})),\
     patch.object(r,'bind',side_effect=lambda a:events.append('bind_completed')) as bind_mock,\
     patch.object(r,'evaluate',side_effect=lambda a:(events.append('evaluate30') or HERE/'mock_result')) as evaluate_mock:
    r.run(args)
    assert events==['parent','bind_completed','parent','evaluate30'];passed('Single queued run validates parent then binds completed files then rechecks parent before evaluation')
    assert bind_mock.call_args.args[0].training_completion==args.training_completion
    events.clear();bind_mock.side_effect=RuntimeError('incomplete training mock')
    evaluate_mock.reset_mock()
    reject('Incomplete training blocks run before exact-release evaluation',lambda:r.run(args))
    assert not evaluate_mock.called
with patch.object(r,'read_prepared',return_value=parent_contract),patch.object(Path,'exists',return_value=True):
    reject('Existing queued-run evidence forbids automatic replay',lambda:r.run(args))
with patch.object(r,'read_prepared',return_value=parent_contract),patch.object(Path,'mkdir'),patch.object(Path,'exists',return_value=False),\
     patch.object(r,'save'),patch.object(r,'artifact',return_value={'path':'in_memory'}),\
     patch.object(r,'validate_controller_release',side_effect=RuntimeError('unauthorized parent mock')),\
     patch.object(r,'bind') as bind_mock,patch.object(r,'evaluate') as evaluate_mock:
    reject('Invalid parent release stops queued run before checkpoint binding and evaluation',lambda:r.run(args))
    assert not bind_mock.called and not evaluate_mock.called

real_declared=[]
for seed in p.SEEDS:
    real_path=p.EXECUTION/'camp_training_inputs_v2'/f'seed_{seed}_plan.json'
    real_plan=p.load(real_path)
    real_declared.append({'seed':seed,'plan':p.artifact(real_path),'output_directory':str(p.validate_training_plan(real_plan,seed))})
p.validate_execution_plan(p.EXECUTION/'camp_training_execution_v2/execution_plan.json',real_declared,Path(r'C:\项目\.venvs\lgm-camp\Scripts\python.exe'))
passed('Actual prepared three-seed execution plan, four source pins and 70 runtime RECORD hashes match by standard-library reads')

runtime_tree=ast.parse((p.TRAIN/'camp_train_runtime.py').read_text(encoding='utf-8'))
save_complete=next(n for n in ast.walk(runtime_tree) if isinstance(n,ast.FunctionDef) and n.name=='save_complete')
checkpoint_assignment=next(n for n in ast.walk(save_complete) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='checkpoint' for t in n.targets))
checkpoint_keys={ast.literal_eval(k) for k in checkpoint_assignment.value.keys}
assert {'schema_version','epoch_completed','next_epoch','global_step','attempted_batches','training_evidence','model','optimizer','scheduler','scaler','rng','sampler','configuration','plan_sha256','profile_sha256','manifests'}<=checkpoint_keys
assert "('checkpoint_complete.pth', checkpoint), ('weights_end.pth', model.state_dict())" in (p.TRAIN/'camp_train_runtime.py').read_text(encoding='utf-8')
passed('Complete/end checkpoint names and required payload fields match the frozen TrainRun.save_complete source')

sealed=p.seal({'stage':'fixture'});p.verify_seal(sealed)
reject('Tampered contract rejected',lambda:p.verify_seal(dict(sealed,stage='changed')))
assert not any(name in sys.modules for name in BLOCKED)
report={'status':'passed_standard_library_only','check_count':len(checks),'checks':checks,
        'scientific_imports':[],'model_constructed':False,'checkpoint_loaded':False,'GPU_executed':False,
        'fixture_policy':'Only in-memory mock dictionaries and synthetic metadata; no checkpoint file, real result or planned weight SHA created',
        'sources':sources,'files':{name:p.artifact(HERE/name) for name in ('protocol.py','camp_independent_model.py','run_evaluation.py','check_lightweight.py')},
        'limitations':['No new torch/model test in this memory-constrained task','No real new checkpoint exists yet; 395-state matching and full/final equality remain mandatory runtime gates','No independent evaluation contract, release or queue has been registered by this check']}
p.save(HERE/'LIGHTWEIGHT_REVIEW.json',report)
print(json.dumps({'status':report['status'],'check_count':report['check_count'],'scientific_imports':[]},indent=2))
