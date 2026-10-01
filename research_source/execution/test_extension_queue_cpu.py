"""Metadata/standard-library-only controller review; never registers or launches a queue."""
import argparse
import ast
import copy
import datetime
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys

HERE=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(HERE))
import supervise_extensions as controller
import register_extension_queue as registration

guard_paths=[HERE/'extension_plan.json',HERE/'extension_status.json',HERE/'extension_supervisor.lock']
before={str(p):(controller.sha(p) if p.is_file() else None) for p in guard_paths}
baseline_runtime=controller.runtime_snapshot(registration.PYTHON)
analysis_missing=[]
try:registration.check_analysis_runtime(baseline_runtime)
except RuntimeError as exc:analysis_missing.append(str(exc))
else:raise AssertionError('Baseline training environment unexpectedly has all analysis extras; update this pending-environment test')
transactions_runtime=controller.runtime_snapshot(Path(r'C:\项目\.venvs\lgm-transactions\Scripts\python.exe'))
try:registration.check_analysis_runtime(transactions_runtime)
except RuntimeError as exc:assert 'numpy' in str(exc) and 'pillow' in str(exc)
else:raise AssertionError('Mismatched Transactions versions accepted for original-model analysis')
valid_analysis_fixture=copy.deepcopy(baseline_runtime)
valid_analysis_fixture['distributions'] += [['scikit-learn','1.6.1'],['scipy','1.17.1'],['matplotlib','3.10.0']]
registration.check_analysis_runtime(valid_analysis_fixture)  # Metadata contract fixture only.
try:registration.build_plan()
except RuntimeError as exc:assert 'isolated analysis interpreter' in str(exc)
else:raise AssertionError('Missing analysis dependencies did not block real registration')
with patch.object(registration,'check_analysis_runtime',return_value=None):
    plan=registration.build_plan()  # In-memory controller tests only, not an executable registration.
assert [j['id'] for j in plan['jobs']]==['real_model_visualizations','heldout_height_training','heldout_and_seen_height_evaluation']
assert all(not j['runtime_snapshot']['scientific_modules_imported'] for j in plan['jobs'])
assert all(j['command'][0]==str(registration.PYTHON) for j in plan['jobs'])
assert all(j['command'][j['command'].index('--python')+1]==str(registration.PYTHON) for j in plan['jobs'][1:])
controller.check_plan(plan)
controller.check_state_jobs({'jobs':[{**j,'status':'pending'} for j in plan['jobs']]},plan)
modified_state={'jobs':copy.deepcopy(plan['jobs'])}
modified_state['jobs'][0]['command'][-1]='8'
try:controller.check_state_jobs(modified_state,plan)
except RuntimeError:pass
else:raise AssertionError('Persisted-state command drift accepted')

def rejects(changed):
    try:controller.check_plan(changed)
    except RuntimeError:return
    raise AssertionError('Invalid queue accepted')

bad=copy.deepcopy(plan);bad['jobs'][0]['id']='../escaped';rejects(bad)
bad=copy.deepcopy(plan);bad['controller_sha256']='0'*64;rejects(bad)
bad=copy.deepcopy(plan);key=next(iter(bad['jobs'][0]['source_sha256']));bad['jobs'][0]['source_sha256'][key]='0'*64;rejects(bad)
bad=copy.deepcopy(plan);bad['jobs'][0]['runtime_snapshot']['python']='changed';rejects(bad)
bad=copy.deepcopy(plan);bad['jobs'].append(copy.deepcopy(bad['jobs'][0]));rejects(bad)
flagged=copy.deepcopy(plan['jobs'][0]);flagged['command'].insert(1,'-B')
assert controller.entrypoint(flagged)==Path(plan['jobs'][0]['command'][1]).resolve()

preceding={'status':'ready_for_extension_preparation','supervisor_pid':123,'supervisor_started_utc':'2026-09-14T00:00:00+00:00',
           'jobs':[{'id':name,'status':'completed','exit_code':0} for name in controller.PRECEDING_JOBS]}
assert not controller.preceding_ready(preceding,lambda pid,started:True)
assert controller.preceding_ready(preceding,lambda pid,started:False)
for broken in [preceding['jobs'][:-1],[{**j,'exit_code':1} if i==2 else j for i,j in enumerate(preceding['jobs'])]]:
    try:controller.preceding_ready({**preceding,'jobs':broken},lambda pid,started:False)
    except RuntimeError:pass
    else:raise AssertionError('Incomplete seven-stage gate accepted')
assert controller.alive(os.getpid(),datetime.datetime.now(datetime.timezone.utc).isoformat())
assert not controller.alive(os.getpid(),'2000-01-01T00:00:00+00:00')

# Parse the actual original T2 CLI from its AST, avoiding its scientific imports.
training=plan['jobs'][1]
source=Path(training['command'][1]);tree=ast.parse(source.read_text(encoding='utf-8'))
main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
statements=[]
for n in main.body:
    if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='args' for t in n.targets):break
    statements.append(n)
namespace={'argparse':argparse,'Path':Path,'DELIVERY_ROOT_DEFAULT':registration.ROOT,'__doc__':ast.get_docstring(tree)}
exec(compile(ast.fix_missing_locations(ast.Module(body=statements,type_ignores=[])),str(source),'exec'),namespace)
assert namespace['parser'].parse_args(training['command'][2:]).stage=='train'

# The new T2 parser has only standard-library imports until gate/evaluate execution.
evaluation=plan['jobs'][2]
spec=importlib.util.spec_from_file_location('heldout_cli_review',evaluation['command'][1]);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
parsed=module.parse_args(evaluation['command'][2:]);assert parsed.scope=='all' and parsed.stage=='evaluate' and parsed.workers==0

# Confirm visualization options exist in the actual function without running it.
visual=ast.parse((HERE/'make_real_model_visualizations.py').read_text(encoding='utf-8'))
options={a.value for n in ast.walk(visual) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='add_argument' for a in n.args if isinstance(a,ast.Constant) and isinstance(a.value,str)}
assert {'--device','--batch-size'}<=options
assert not any(name in sys.modules for name in ('torch','torchvision','numpy','matplotlib','sklearn'))
after={str(p):(controller.sha(p) if p.is_file() else None) for p in guard_paths}
assert before==after
versions={name:dict(baseline_runtime['distributions']).get(name) for name in ('torch','torchvision','numpy','pillow','scipy','scikit-learn','matplotlib','contourpy','fonttools','kiwisolver','pyparsing')}
import supervise_pipeline as pipeline
prepared=pipeline.jobs()
assert len(prepared)==7 and all(job['command'][0]==str(registration.PYTHON) for job in prepared)
for job in prepared:
    if '--python' in job['command']:assert job['command'][job['command'].index('--python')+1]==str(registration.PYTHON)
report={'status':'passed','scope':'Standard-library logic and importlib.metadata only; no queue registration, child experiment, scientific import or CUDA initialization',
        'checks':['Three prepared job arguments match current parsers','Source/controller/runtime and persisted-command tamper rejection','Unsafe and duplicate job ID rejection',
                  'Seven-stage completion plus process-exit gate','Reused PID detection','Python -B argument handling','Plan/status/lock files unchanged','No scientific modules imported',
                  'Seven main stages and both T2 stages use original-version baseline interpreter','Real analysis registration rejects absent extras or changed original versions'],
        'metadata_versions':versions,'source_sha256':{p.name:controller.sha(p) for p in (HERE/'supervise_extensions.py',HERE/'supervise_pipeline.py',HERE/'register_extension_queue.py',HERE/'make_real_model_visualizations.py',HERE/'heldout_evaluation/run_heldout_evaluation.py')},
        'scientific_imports_tested':False,'analysis_environment_status':'Not prepared; dependency validator mocked only for in-memory controller unit checks; actual registration correctly refused',
        'analysis_blockers':analysis_missing,'t1_wrapper_review':'Awaiting final wrapper job specification; not included or registered; its declared Transactions interpreter remains independent'}
controller.save(HERE/'extension_queue_cpu_checks.json',report)
print(json.dumps(report,ensure_ascii=False,indent=2))
