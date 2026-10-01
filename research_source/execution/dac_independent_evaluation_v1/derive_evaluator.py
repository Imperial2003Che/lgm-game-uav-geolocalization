"""Initial derivation helper; never overwrite the subsequently reviewed outputs.

Final hardening is recorded in SOURCE_DERIVATION.patch against CAMP v3.
"""
import ast
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camp_independent_evaluation_v3'
if any((HERE/name).exists() for name in ('run_evaluation.py','dac_independent_model.py')):
    raise RuntimeError('Reviewed outputs already exist; initial derivation cannot overwrite them')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def replace_function(source,name,replacement):
    node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name==name)
    lines=source.splitlines(keepends=True)
    return ''.join(lines[:node.lineno-1])+replacement.rstrip()+'\n'+''.join(lines[node.end_lineno:])
source=(OLD/'run_evaluation.py').read_text('utf-8')
source=source.replace('CAMP','DAC').replace('camp_independent_model','dac_independent_model').replace('camp_training_execution_v2','dac_training_execution_v2')
source=source.replace('execution_plan.json','execution_spec.json').replace("checkpoint_schema='395 original state tensors; learned pos_scale retained'","checkpoint_schema='402 original DAC state tensors; three classifier heads and DSA projection retained'")
source=source.replace("EXECUTION/'dac_training_execution_v2/status.json'","EXECUTION/'dac_training_execution_v2/runtime/completion_manifest.json'")
source=source.replace("verify_artifact(value['training_execution_plan']);verify_artifact(value['latest_baseline_plan'])","verify_artifact(value['training_execution_plan']);verify_artifact(value['training_execution_package']);verify_execution_package(value['training_execution_package'])")
source=source.replace("'latest_baseline_plan':artifact(EXECUTION/'latest_baseline_plan.json'),'settings':settings,","'training_execution_package':execution_package_evidence(),'settings':settings,")
source=source.replace("'latest_baseline_plan_sha256':prepared['latest_baseline_plan']['sha256'],","'training_execution_package_sha256':prepared['training_execution_package']['sha256'],")
source=source.replace("'latest_completed_status':latest,","'training_status':latest,").replace("binding['latest_completed_status']","binding['training_status']")
source=source.replace('verify_latest_completed(prepared)',"verify_execution_package(prepared['training_execution_package'])")
source=replace_function(source,'completion_and_bindings','''def completion_and_bindings(prepared,completion_path):
    completion_path=Path(completion_path).resolve()
    require(completion_path==TRAIN_EXECUTION/'runtime/completion_manifest.json','Expected exact DAC v2 terminal manifest')
    completion_before=artifact(completion_path)
    receipt=verify_completed_supervision(prepared,completion_path,completion_before['sha256'])
    state_path=TRAIN_EXECUTION/'runtime/status.json';state_before=artifact(state_path)
    validate_training_completion(load(state_path),prepared)
    seeds=[bind_seed(item) for item in prepared['training_plans']]
    require(receipt==verify_completed_supervision(prepared,completion_path,completion_before['sha256']),'Completed supervision evidence changed during checkpoint binding')
    verify_artifact(completion_before);verify_artifact(state_before)
    return state_before,completion_before,seeds
''')
source=source.replace("validate_execution_plan(args.training_execution_plan,plans,args.python)","require(sha(args.training_execution_plan)==args.training_execution_sha256,'Externally pinned DAC execution specification required')\n    verify_execution_package(execution_package_evidence(),args.training_package_sha256)\n    validate_execution_plan(args.training_execution_plan,plans,args.python)")
source=source.replace("prepare_p.add_argument('--training-execution-plan',type=Path,required=True)","prepare_p.add_argument('--training-execution-plan',type=Path,required=True)\n    prepare_p.add_argument('--training-execution-sha256',required=True)\n    prepare_p.add_argument('--training-package-sha256',required=True)")
(HERE/'run_evaluation.py').write_text(source,encoding='utf-8')
model=(OLD/'camp_independent_model.py').read_text('utf-8').replace('CAMP','DAC').replace('395-state','402-state')
model=model.replace('AUTHOR, MODEL_FACTORY, MODEL_FACTORY_SHA, sha, load, canonical, compare_schema, verify_artifact','AUTHOR, MODEL_FACTORY, pins, sha, load, canonical, compare_schema, verify_artifact, require')
model=model.replace('MODEL_FACTORY_SHA',"pins()['files'][str(MODEL_FACTORY)]").replace('_camp_independent_full_original_model_factory','_dac_independent_full_original_model_factory')
model=model.replace("        # Explicit False keeps the original learned pos_scale Parameter. Never\n        # call the 394-state author loader or its author-specific validator.\n        model=factory.build_camp_model(device='meta',author_checkpoint_schema=False)\n        if not isinstance(model.model_1.pos_scale,torch.nn.Parameter) or not model.model_1.pos_scale.requires_grad:\n            raise RuntimeError('The original learned pos_scale must remain a Parameter')","        # Official DAC factory has no author compatibility switch or altered schema.\n        model=factory.build_dac_model(device='meta')")
model=model.replace("        if not isinstance(model.model_1.pos_scale,torch.nn.Parameter) or not model.model_1.pos_scale.requires_grad:raise RuntimeError('Learned pos_scale was lost during load')", "        validate_full_training_state(complete,binding,torch)")
model=model.replace('learned_pos_scale_preserved=True','three_classifier_heads_and_DSA_projection_retained=True').replace('model_factory_author_checkpoint_schema=False','author_checkpoint_values_loaded=False')
model+='\nfrom complete_state_checks import validate_full_training_state\n'
(HERE/'dac_independent_model.py').write_text(model,encoding='utf-8')
for name in ('run_evaluation.py','dac_independent_model.py'):compile((HERE/name).read_text('utf-8'),str(HERE/name),'exec')
record={'schema':'dac-independent-evaluator-derivation.v1','source_files':{name:sha(OLD/name) for name in ('run_evaluation.py','camp_independent_model.py','protocol.py')},'description':'Reuse CAMP v3 full-gallery loop and complete/final equality structure; replace DAC identities, strict402 schema and independent DAC supervision binding. No author weights or compatibility branch.'}
(HERE/'SOURCE_DERIVATION.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('Derived evaluator and independent full402 loader; AST compiled only.')
