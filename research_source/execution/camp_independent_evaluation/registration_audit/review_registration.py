"""Read-only registration audit: import definitions, never call main()."""
import ast
import copy
import importlib.abc
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
EVAL=HERE.parent
EXECUTION=EVAL.parent
sys.path.insert(0,str(EVAL));sys.dont_write_bytecode=True
BLOCKED={'torch','torchvision','numpy','scipy','PIL','cv2','matplotlib','timm','sklearn','pptx'}
class BlockScientific(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in BLOCKED:raise RuntimeError('Scientific import forbidden')
sys.meta_path.insert(0,BlockScientific())
import protocol

source=EXECUTION/'register_independent_comparisons.py'
spec=importlib.util.spec_from_file_location('_registration_readonly_review',source)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
tree=ast.parse(source.read_text(encoding='utf-8'));compile(tree,str(source),'exec')
checks=[]
def ok(label,condition):
    if not condition:raise AssertionError(label)
    checks.append(label)
def rejected(label,fn):
    try:fn()
    except RuntimeError:checks.append(label)
    else:raise AssertionError('Expected rejection: '+label)

ok('Module definitions parse/import without running main or importing science',not any(name in sys.modules for name in BLOCKED))
ok('Final independent controller hash equals reviewed 0b4678 source',module.sha(module.CONTROLLER)==module.EXPECTED_CONTROLLER)
ok('Existing latest author queue SHA matches fixed predecessor',module.sha(EXECUTION/'latest_baseline_plan.json')==module.LATEST_SHA)
training=protocol.load(EXECUTION/'camp_training_execution/execution_plan.json')
ok('CAMP training execution plan matches exact frozen SHA',module.sha(EXECUTION/'camp_training_execution/execution_plan.json')==module.TRAIN_PLAN_SHA)
handoff=protocol.load(EVAL/'QUEUE_HANDOFF.json')
ok('Final 30-evaluation preparation matches registration SHA',protocol.sha(handoff['prepared']['path'])==module.EVAL_SHA)
probe={'source_sha256':{}}
module.pin_manifest(probe,EVAL/'PREPARATION_MANIFEST.json',EVAL)
ok('All evaluation preparation-manifest entries resolve and match, including absolute artifact paths',len(probe['source_sha256'])==12)
module.pin_manifest(probe,EXECUTION/'camp_training_execution/PREPARATION_MANIFEST.json',EXECUTION/'camp_training_execution')
module.pin_manifest(probe,EXECUTION/'camp_training_preparation/PREPARATION_MANIFEST.json',EXECUTION/'camp_training_preparation')
ok('New and original CAMP training preparation manifests resolve without imports',True)
for path,digest in handoff['job']['source_sha256'].items():
    module.pin(probe,path,digest)
ok('All inherited evaluation job source and membership pins match current files',True)
for name in ('weights_end.pth','checkpoint_complete.pth'):
    ok('Future '+name+' absent from registration pin requirements',all(name not in path for path in handoff['job']['source_sha256']))
ok('Evaluation command uses future bind-and-evaluate run entry',handoff['job']['command'][3]=='run')
ok('Evaluation future completion path is the fixed training supervisor status',handoff['job']['command'][7]==str(EXECUTION/'camp_training_execution/status.json'))

template=protocol.load(handoff['template']['path'])
ok('Controller release source template is frozen and inactive',protocol.sha(handoff['template']['path'])==handoff['template']['sha256'] and template['allow_cuda'] is False)
ok('Controller release binds latest plan, training plan, three seeds and all30 tasks',
   template['schema']==protocol.CONTROLLER_RELEASE_SCHEMA and template['latest_baseline_plan_sha256']==module.LATEST_SHA and
   template['training_execution_plan_sha256']==module.TRAIN_PLAN_SHA and template['binding_policy']==protocol.BINDING_POLICY and template['seeds']==[1,2,3] and template['task_count']==30)
ok('Actual controller release path agrees with queued command',handoff['job']['command'][9]==handoff['missing_release_to_create_and_pin'])
main=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='main')
job_assignment=next(node for node in ast.walk(main) if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='jobs' for t in node.targets))
ok('Registered task order is matched-view, CAMP training, CAMP independent evaluation',isinstance(job_assignment.value,ast.List) and [node.id for node in job_assignment.value.elts]==['matched_job','train_job','eval_job'])
write_calls=[node for node in ast.walk(main) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='write_new']
ok('Registration writes only new release files, new own queue and own receipt',len(write_calls)==3)
write_function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='write_new')
ok('Exclusive-create write mode forbids overwrite',any(isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='open' and node.args and isinstance(node.args[0],ast.Constant) and node.args[0].value=='xb' for node in ast.walk(write_function)))
ok('Registration never starts subprocesses or CUDA',not any(isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr in ('Popen','cuda') for node in ast.walk(main)))
with patch.object(module,'sha',return_value='mock_current'):
    memory={'source_sha256':{}}
    module.pin(memory,source,'mock_current')
    rejected('Unexpected expected source hash rejected',lambda:module.pin(memory,source,'mock_wrong'))
    memory['source_sha256'][str(source.resolve())]='mock_other'
    rejected('Conflicting inherited source pin rejected',lambda:module.pin(memory,source))

check_plan_calls=sorted(node.lineno for node in ast.walk(main) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='check_plan')
first_release_write=min(node.lineno for node in write_calls)
preflight_before_release=bool(check_plan_calls and check_plan_calls[0]<first_release_write)
dry_run_branch=next(node for node in ast.walk(main) if isinstance(node,ast.If) and isinstance(node.test,ast.Name) and node.test.id=='validate_only')
ok('Validate-only returns after preflight and before any release/plan write',check_plan_calls[0]<dry_run_branch.lineno<first_release_write and any(isinstance(node,ast.Return) for node in dry_run_branch.body))
findings=[]
if not preflight_before_release:
    findings.append({'severity':'needs_fix_before_registration','finding':'Full command/cwd/entrypoint validation occurs only after active releases are written; malformed prepared job can leave three releases without a registered plan.',
                     'suggestion':'Build and preflight the plan before any release write, then add actual release pins and revalidate before exclusive plan creation.'})
matched=EXECUTION/'matched_view_execution/prepared_manifest.json'
report={'schema':'independent-comparison-registration-external-review.v1','checked_utc':protocol.utc(),'source':protocol.artifact(source),
        'status':'passed_read_only_review' if not findings else 'findings_require_root_review','check_count':len(checks),'checks':checks,
        'plan_preflight_before_active_release_writes':preflight_before_release,'findings':findings,
        'matched_prepared_manifest_currently_exists':matched.exists(),'matched_scope':'Await matched agent final freeze; this review does not reconstruct or register missing artifacts.',
        'contracts':{name:protocol.artifact(path) for name,path in {
             'evaluation_handoff':EVAL/'QUEUE_HANDOFF.json','evaluation_source_freeze':EVAL/'PREPARATION_MANIFEST.json',
             'evaluation_prepared':Path(handoff['prepared']['path']),'training_execution_plan':EXECUTION/'camp_training_execution/execution_plan.json'}.items()},
        'scientific_imports':[],'main_executed':False,'actual_release_files_created':0,'subprocesses_launched':0,'GPU_queries':0,
        'existing_queues_modified':False,'source_files_modified':False}
output=HERE/('REGISTRATION_REVIEW_'+protocol.sha(source)[:12]+'.json')
protocol.save(output,report)
print(json.dumps({'status':report['status'],'check_count':len(checks),'report':str(output),'findings':findings},ensure_ascii=True))
