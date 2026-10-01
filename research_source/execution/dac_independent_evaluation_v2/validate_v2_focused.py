"""Focused source-v2 fix fixtures: stdlib only, no actual processes/GPU."""
import ast
import copy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import contract_snapshots as s
import protocol as p
import run_evaluation as e

HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'dac_independent_evaluation_v1';checks=[]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def check(name,condition):
    checks.append({'name':name,'passed':bool(condition)})
    if not condition:raise AssertionError(name)
def rejects(name,fn):
    try:fn()
    except (RuntimeError,ValueError,KeyError,FileNotFoundError):check(name,True)
    else:check(name,False)
def fn(path,name):return next(n for n in ast.parse(path.read_text('utf-8')).body if isinstance(n,ast.FunctionDef) and n.name==name)
def dump(node):return ast.dump(node,include_attributes=False)
def write(path,value):path.write_text(json.dumps(value,allow_nan=False),encoding='utf-8')
def all_artifacts():
    m=json.loads((OLD/'PREPARATION_MANIFEST.json').read_text('utf-8'))
    return all((OLD/x['path']).stat().st_size==x['bytes'] and sha(OLD/x['path'])==x['sha256'] for x in m['files'])
check('all_v1_sealed_sources_preserved',all_artifacts() and sha(OLD/'PREPARATION_MANIFEST.json')=='5a65d21c005771a98f9b28716cba775cc15f45b436246544926b14be5a799049')
for name in ('dac_independent_model.py','complete_state_checks.py'):check(name+'_byte_identical',sha(HERE/name)==sha(OLD/name))
check('encode_seed_AST_unchanged',dump(fn(HERE/'run_evaluation.py','encode_seed'))==dump(fn(OLD/'run_evaluation.py','encode_seed')))
def science_region(path):
    node=fn(path,'evaluate');body=next(n for n in node.body if isinstance(n,ast.Try)).body
    inside=next(n for n in body if isinstance(n,ast.With)).body
    start=next(i for i,n in enumerate(inside) if isinstance(n,ast.Import) and any(a.name=='numpy' for a in n.names))
    end=next(i for i,n in enumerate(inside) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='verify_inventory')
    return [dump(n) for n in inside[start:end]]
check('entire_science_iteration_ranking_summary_AST_unchanged',science_region(HERE/'run_evaluation.py')==science_region(OLD/'run_evaluation.py'))
supervision=p.TRAIN_EXECUTION/'dac6_contracts.py'
verifier=fn(supervision,'verify_training_artifacts')
returned_files=set()
for node in ast.walk(verifier):
    if isinstance(node,ast.For) and isinstance(node.target,ast.Name) and node.target.id=='name' and isinstance(node.iter,ast.Tuple):
        returned_files.update(ast.literal_eval(node.iter))
bind_node=fn(HERE/'protocol.py','bind_seed')
names_node=next(n for n in bind_node.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='names' for t in n.targets))
bound_files=set(ast.literal_eval(names_node.value))|{'checkpoint_complete.pth','weights_end.pth'}
check('current_real_supervision_returned_files_covered',bool(returned_files) and returned_files<=bound_files)
check('new_initial_parameter_evidence_bound','initial_parameter_evidence.json' in returned_files and 'initial_parameter_evidence.json' in bound_files)
for label,stdout in [('python','482, python.exe'),('nonPythonCUDA','491, native-cuda-app.exe'),('unknownCUDA','498, [Not Found]')]:rejects('reject_'+label+'_CUDA_owner',lambda stdout=stdout:e.validate_cuda_rows(stdout))
check('empty_CUDA_rows_accepted',e.validate_cuda_rows(' \n\t\n')==[])

with tempfile.TemporaryDirectory(prefix='dac_eval_v2_mock_') as temp:
    folder=Path(temp);prepared=folder/'prepared.json';binding=folder/'binding.json';release=folder/'release.json';controller=folder/'controller.json'
    for path in (prepared,binding,release,controller):write(path,{'version':1})
    with s.snapshot_scope():
        snap=s.input_snapshot(prepared);before=snap.artifact
        check('first_read_exact_raw_SHA_and_bytes',before=={'path':str(prepared),'bytes':len(prepared.read_bytes()),'sha256':sha(prepared)})
        write(prepared,{'version':2})
        check('retained_value_does_not_change_after_path_mutation',snap.value=={'version':1} and snap.artifact==before)
        rejects('prepared_mutation_rejected_on_recapture',lambda:s.input_snapshot(prepared))
        rejects('prepared_mutation_rejected_before_science',s.unchanged_inputs)
    for key,path in [('prepared',prepared),('binding',binding),('release_file',release),('controller_release',controller)]:
        write(path,{'version':1});calls=[]
        @s.snapshot_command
        def outer(args):
            first=s.input_snapshot(path).artifact;write(path,{'version':2})
            @s.snapshot_command
            def nested(inner):calls.append('science');return first
            return nested(SimpleNamespace(**{key:path}))
        rejects('nested_run_bind_'+key+'_mutation',lambda key=key,path=path:outer(SimpleNamespace(**{key:path})))
        check('nested_'+key+'_blocked_before_body',calls==[])
    for path in (prepared,binding,release):write(path,{'version':1})
    with s.snapshot_scope():
        read=[s.input_snapshot(path) for path in (prepared,binding,release)]
        p_art,b_art,r_art=[snap.artifact for snap in read]
        info={'training_execution_package':{'sha256':'7'*64},'training_execution_plan':{'sha256':'8'*64}}
        valid={'schema':p.RELEASE_SCHEMA,'allow_cuda':True,'prepared_sha256':p_art['sha256'],'binding_sha256':b_art['sha256'],'training_execution_package_sha256':'7'*64,'training_execution_plan_sha256':'8'*64}
    write(release,valid)
    with s.snapshot_scope(),patch.object(e,'verify_execution_package',return_value=None),patch.object(e.subprocess,'run',return_value=SimpleNamespace(stdout='')):
        s.input_snapshot(prepared);s.input_snapshot(binding);snap=s.input_snapshot(release)
        gate=e.release_gate(info,prepared,binding,release)
        check('gate_receipt_uses_same_first_read_release',gate['release']==snap.artifact and gate['prepared']==p_art and gate['binding']==b_art)
    for key,path in [('prepared',prepared),('binding',binding),('release',release)]:
        write(prepared,{'version':1});write(binding,{'version':1});write(release,valid)
        with s.snapshot_scope(),patch.object(e,'verify_execution_package',return_value=None),patch.object(e.subprocess,'run',return_value=SimpleNamespace(stdout='')) as cuda_probe:
            for entry in (prepared,binding,release):s.input_snapshot(entry)
            write(path,{'changed_between_read_and_gate':True})
            rejects('actual_release_gate_rejects_'+key+'_mutation',lambda:e.release_gate(info,prepared,binding,release))
            check(key+'_change_blocked_before_GPU_probe',not cuda_probe.called)
    write(prepared,{'version':1});write(binding,{'version':1});write(release,valid)
    with s.snapshot_scope(),patch.object(e,'verify_execution_package',return_value=None):
        for entry in (prepared,binding,release):s.input_snapshot(entry)
        def mutate_during_probe(*args,**kwargs):write(release,{'version':'changed during GPU query'});return SimpleNamespace(stdout='')
        with patch.object(e.subprocess,'run',side_effect=mutate_during_probe):rejects('release_changed_during_GPU_query_rejected',lambda:e.release_gate(info,prepared,binding,release))
    new=folder/'derived_binding.json';value={'scientific_object':'the value actually written'}
    with s.snapshot_scope():
        raw=(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode();new.write_bytes(raw)
        check('generated_binding_pins_emitted_raw_bytes',s.bind_written(new,value).raw==raw)
    with s.snapshot_scope(),patch.object(p,'local_output',return_value=new):
        p.save(new,{'multiline':'first\nsecond','unicode':'实际写入'})
        proof=s.bind_written(new,{'multiline':'first\nsecond','unicode':'实际写入'})
        check('actual_save_bytes_equal_snapshot_on_Windows',new.read_bytes()==proof.raw and b'\r\n' not in proof.raw)
    with s.snapshot_scope():
        write(new,{'replacement':'before registration'})
        rejects('replacement_between_save_and_binding_rejected',lambda:s.bind_written(new,value))
    write(prepared,{'version':1})
    with s.snapshot_scope():
        first=s.input_snapshot(prepared)
        with s.snapshot_scope():check('nested_scopes_reuse_first_snapshot',s.input_snapshot(prepared) is first)
        write(prepared,{'changed':'after scientific work'});rejects('final_input_check_rejects_postscience_mutation',s.unchanged_inputs)

tree=ast.parse((HERE/'run_evaluation.py').read_text('utf-8'))
for name in ('prepare','bind','run','evaluate'):
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    check(name+'_shared_first_read_snapshot_scope',any(isinstance(d,ast.Name) and d.id=='snapshot_command' for d in node.decorator_list))
check('state_checker_and_snapshot_module_in_prepared_source_identity',all(name in (HERE/'protocol.py').read_text('utf-8') for name in ("'complete_state_checks.py'","'contract_snapshots.py'")))
check('no_scientific_imports',not any(x in sys.modules for x in ('numpy','torch','PIL','cv2','scipy','timm','transformers','albumentations')))
check('no_runtime_release_or_results_created',not any((HERE/n).exists() for n in ('runtime','results','runs','preparations','controller_release.json')))
report={'schema':'dac-independent-evaluation-v2-focused-stdlib.v1','created_utc':datetime.now(timezone.utc).isoformat(),'checks':checks,'check_count':len(checks),'pass_count':sum(x['passed'] for x in checks),'scope':'Pure stdlib raw-byte fixtures plus actual release gate with mocked NVIDIA call; no scientific imports/model/GPU/process/queue/release','prior_v1_manifest_sha256':sha(OLD/'PREPARATION_MANIFEST.json'),'actual_supervision_contract_sha256':sha(supervision),'actual_supervision_returned_files':sorted(returned_files),'bound_files':sorted(bound_files)}
(HERE/'V2_FOCUSED_VALIDATION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':report['pass_count'],'total':report['check_count']},indent=2))
