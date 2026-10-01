"""Validate the authentic four-job plan in memory; never register or execute it."""
import argparse
import ast
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import register_extension_queue as registration
import supervise_extensions as controller

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--analysis-python',type=Path,required=True)
parser.add_argument('--t1-job',type=Path,default=HERE/'baseline_preparation/t1_job.json')
args=parser.parse_args()

guard_paths=[HERE/'extension_plan.json',HERE/'extension_status.json',HERE/'extension_supervisor.lock',args.t1_job]
before={str(p):(controller.sha(p) if p.is_file() else None) for p in guard_paths}
plan=registration.build_plan(args.t1_job,args.analysis_python)
expected=['real_model_visualizations','heldout_height_training','heldout_and_seen_height_evaluation','t1_v3_native_resource_profile_then_7fits_70eval']
assert [j['id'] for j in plan['jobs']]==expected
assert plan['jobs'][0]['command'][0]==str(args.analysis_python.resolve())
assert all(j['command'][0]==str(registration.PYTHON) for j in plan['jobs'][1:3])
assert plan['jobs'][3]['command'][0]==r'C:\项目\.venvs\lgm-transactions\Scripts\python.exe'
assert all(j['command'][j['command'].index('--python')+1]==str(registration.PYTHON) for j in plan['jobs'][1:3])
controller.check_plan(plan)
controller.check_state_jobs({'jobs':[{**j,'status':'pending'} for j in plan['jobs']]},plan)

t1=plan['jobs'][3]
assert len(t1['source_sha256'])==34
assert all(controller.sha(Path(path))==digest for path,digest in t1['source_sha256'].items())
entry=controller.entrypoint(t1)
tree=ast.parse(entry.read_text(encoding='utf-8'))
main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
statements=[]
for node in main.body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='a' for t in node.targets):
        break
    statements.append(node)
namespace={'argparse':argparse,'Path':Path,'__doc__':ast.get_docstring(tree)}
exec(compile(ast.fix_missing_locations(ast.Module(body=statements,type_ignores=[])),str(entry),'exec'),namespace)
parsed=namespace['ap'].parse_args(t1['command'][t1['command'].index(str(entry))+1:])
assert parsed.stage=='all' and parsed.device_index==0
assert all(getattr(parsed,name).exists() for name in ('plan','train_root','test_root','sues_root','sues_manifest'))
after={str(p):(controller.sha(p) if p.is_file() else None) for p in guard_paths}
assert before==after
assert not any(name in sys.modules for name in ('torch','torchvision','numpy','PIL','matplotlib','sklearn'))
report={'status':'passed','scope':'Actual four-job build_plan and check_plan with metadata-only runtime probes; no mocks, scientific imports, registration, model, CUDA or experiment process',
        'job_ids':expected,'t1_source_pin_count':len(t1['source_sha256']),'t1_all_source_pins_match':True,
        't1_job_sha256':controller.sha(args.t1_job),'t1_actual_parser_accepts_command':True,
        'queue_files_unchanged':True,'jobs':[{'id':j['id'],'interpreter':j['command'][0],'entrypoint':str(controller.entrypoint(j)),
                                             'source_pin_count':len(j['source_sha256']),'runtime_snapshot':j['runtime_snapshot']} for j in plan['jobs']],
        'controller_sha256':plan['controller_sha256'],'registration_script_sha256':plan['registration_script_sha256'],
        'gate_note':'Runtime execution still waits for completed primary 42/evaluations, all seven preceding stages and preceding PID exit; downstream runners enforce their own scientific prerequisites.'}
controller.save(HERE/'extension_four_job_cpu_checks.json',report)
print(json.dumps({k:v for k,v in report.items() if k!='jobs'},ensure_ascii=True,indent=2))
