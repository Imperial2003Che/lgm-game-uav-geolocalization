"""Independent AST/byte inspection only. Never import or execute producer code."""
from pathlib import Path
import ast, difflib, hashlib, json
from datetime import datetime, timezone

R=Path(__file__).resolve().parent
E=R.parent
W=E/'external_efficiency_preparation/newer_native_b1_worker_v1'

def pin(p):
    p=Path(p); raw=p.read_bytes()
    return {'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

def parse(p):
    return ast.parse(Path(p).read_text(encoding='utf-8-sig'))

def funcs(tree):
    return {n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}

def first(node):
    body=node.body
    if isinstance(body[0],ast.Expr) and isinstance(body[0].value,ast.Constant) and isinstance(body[0].value.value,str):
        body=body[1:]
    return body[0]

checklist=json.loads((R/'INPUT_CHECKLIST.json').read_text(encoding='utf-8-sig'))
old=[]
for p in checklist['source_bindings']:
    now=pin(p['path'])
    assert now==p,p['path']
    old.append(now)
source=W/'reference_worker.py'
observed=pin(source)
assert observed['sha256']=='eed9b25b1204edbcf5172ea2fb24e272b7ff39103f98448e554a3dae779b7f46'
tree=parse(source); fn=funcs(tree)
guards={}
for name in ['run_reference','admit_reference','_execute_original_reference','_load_sources_after_admission','_import_pinned']:
    stmt=first(fn[name]); value=stmt.value if isinstance(stmt,(ast.Expr,ast.Assign)) else None
    assert isinstance(value,ast.Call) and isinstance(value.func,ast.Name) and value.func.id=='_closed_execution_admission',name
    guards[name]={'line':stmt.lineno,'statement':ast.unparse(stmt)}
gate=fn['_closed_execution_admission']
assert len(gate.body)==1 and isinstance(gate.body[0],ast.Raise)
assert all(not isinstance(n,ast.Return) for n in ast.walk(gate))
encode_calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='encode_seed']
assert len(encode_calls)==1
call=encode_calls[0]
assert ast.unparse(call.func)=='package.evaluator.encode_seed'
assert [ast.unparse(a) for a in call.args]==['derived',"inputs.seed_binding(rebuilt['seed'])","rebuilt['selected_rows']",'native','log']
imports=[ast.unparse(n) for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]
assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in ['exec','eval'] for n in ast.walk(tree))
assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ['load_native_slot','_measure_task_ranking_unreleased','measure_task_ranking'] for n in ast.walk(tree))
old_source=W/'PRE_ROOT_REVIEW_reference_worker.py.txt'
a=parse(old_source); af=funcs(a)
changed=[name for name in fn if ast.dump(fn[name],include_attributes=False)!=ast.dump(af[name],include_attributes=False)]
assert changed==['read_control','derivation_envelope'],changed
diff=''.join(difflib.unified_diff(old_source.read_text(encoding='utf-8').splitlines(True),source.read_text(encoding='utf-8').splitlines(True),fromfile='first_source_5b888a1e.py',tofile='final_source_eed9b25b.py'))
with (R/'INDEPENDENT_FINAL_AMENDMENT.patch').open('x',encoding='utf-8',newline='\n') as f:f.write(diff)
encoders={}
for method,directory in [('CAMP','camp_independent_evaluation_v3'),('DAC','dac_independent_evaluation_v2')]:
    p=E/directory/'run_evaluation.py'
    node=funcs(parse(p))['encode_seed']
    encoders[method]={'source':pin(p),'start_line':node.lineno,'end_line':node.end_lineno,
      'encoder_ast_sha256':hashlib.sha256(ast.dump(node).encode()).hexdigest(),
      'interface':ast.unparse(node.args)}

extra=[E/'external_efficiency_preparation/newer_native_loader_v1/source_bindings.py',
       E/'external_efficiency_preparation/newer_native_loader_v1/path_aliases.py',
       E/'camp_independent_evaluation_v3/preparations/frozen_three_seed_final_v3/manifest.json',
       E/'dac_independent_evaluation_v2/preparations/fixed_three_seed/manifest.json',
       E/'camp_preparation/run_camp_author_evaluation.py',E/'dac_preparation/run_dac_author_evaluation.py']
runtime=[]
for p in extra[2:4]:
    value=json.loads(p.read_text(encoding='utf-8-sig'))
    runtime.append({'prepared':pin(p),'runtime_keys':sorted(value['runtime']),
      'runtime_prefix_present':isinstance(value['runtime']['prefix'],str),
      'batch_size':value['settings']['batch_size']})

report={'schema':'independent-b1-worker-static-bindings.v1','utc':datetime.now(timezone.utc).isoformat(),
 'reviewer':'Independent AI agent; no human reviewer','passed':True,
 'method':'Raw small-source hashing and AST parsing only; no source imported/executed, no test or scientific call.',
 'source':observed,'old_sources_unchanged':old,'guard_statements':guards,
 'closed_gate_line':gate.lineno,'sole_original_encoder_call':{'line':call.lineno,'expression':ast.unparse(call)},
 'top_level_imports':imports,'original_encoder_interfaces':encoders,
 'first_version':pin(old_source),'changed_function_ASTs':changed,
 'complete_amendment_diff':pin(R/'INDEPENDENT_FINAL_AMENDMENT.patch'),
 'additional_sources_read':list(map(pin,extra)),'prepared_runtime_field_check':runtime,
 'producer_executed':False,'old_tests_executed':False,'science_imported':False,'execution_authorized':False}
out=R/'STATIC_BINDING_REVIEW.json'
with out.open('x',encoding='utf-8',newline='\n') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'report':pin(out),'source':observed,'changed_functions':changed,'encoder_ast_hashes':{k:v['encoder_ast_sha256'] for k,v in encoders.items()}},ensure_ascii=True))
