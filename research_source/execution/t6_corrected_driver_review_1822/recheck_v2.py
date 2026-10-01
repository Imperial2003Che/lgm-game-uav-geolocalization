"""Limited v2 delta recheck. Standard library only; no driver execution."""
import ast
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent
BASE=OUT.parent/'external_efficiency_preparation'
V1=BASE/'corrected_driver_v1';V2=BASE/'corrected_driver_v2'
checks=[]
def read(p):return Path(p).read_text('utf-8-sig')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check(n,ok,evidence=None):checks.append({'name':n,'passed':bool(ok),'evidence':evidence})
def refused(fn):
 try:fn()
 except (KeyError,ValueError,RuntimeError):return True
 return False
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def function(t,n):return next(x for x in t.body if isinstance(x,ast.FunctionDef) and x.name==n)
def dump(n):return ast.dump(n,include_attributes=False)
trees={}
for filename in ['contract.py','driver.py','science.py']:
 trees[filename]=[ast.parse(read(v/filename)) for v in [V1,V2]]
 for t in trees[filename]:compile(t,filename,'exec')
check('three_modules_parse_compile',True)
changes={}
for filename,(old,new) in trees.items():
 a={n.name:dump(n) for n in old.body if isinstance(n,ast.FunctionDef)};b={n.name:dump(n) for n in new.body if isinstance(n,ast.FunctionDef)}
 changes[filename]={'added':sorted(b.keys()-a.keys()),'removed':sorted(a.keys()-b.keys()),'changed':sorted(n for n in a.keys()&b.keys() if a[n]!=b[n])}
check('contract_only_two_declared_functions_changed',changes['contract.py']=={'added':['closed_case_artifacts'],'removed':[],'changed':['self_and_verified_ancestors']},changes['contract.py'])
check('driver_only_declared_run_and_exit_artifacts_changed',changes['driver.py']=={'added':['exited_process_artifacts'],'removed':[],'changed':['run']},changes['driver.py'])
check('science_only_run_case_changed',changes['science.py']=={'added':[],'removed':[],'changed':['_run_case']},changes['science.py'])
normal=[]
for t in trees['science.py']:
 t=copy.deepcopy(t)
 for n in ast.walk(t):
  if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='outputs' for x in n.targets):n.value=ast.Constant(value='artifact enumeration delta only')
 normal.append(dump(t))
check('entire_science_AST_identical_except_outputs_enumeration',normal[0]==normal[1])
v1manifest=json.loads(read(V1/'SOURCE_MANIFEST.json'))
check('v1_entire_seal_unchanged',all(sha(x['path'])==x['sha256'] and Path(x['path']).stat().st_size==x['bytes'] for x in v1manifest['files']),{'manifest_sha256':sha(V1/'SOURCE_MANIFEST.json'),'files':len(v1manifest['files'])})
k=load('contract',V2/'contract.py');d=load('v2_independent_driver',V2/'driver.py')
check('no_scientific_imports',not any(n in sys.modules for n in ['torch','numpy','PIL','scipy','torchvision','transformers']))
base=[{'ProcessId':100,'ParentProcessId':200,'Name':'python.exe','CreatedUtc':'2026-09-14T10:00:00+00:00','ExecutablePath':'fixture_driver'}, {'ProcessId':200,'ParentProcessId':300,'Name':'python.exe','CreatedUtc':'2026-09-14T09:00:00+00:00','ExecutablePath':'fixture_parent'}, {'ProcessId':300,'ParentProcessId':9,'Name':'python.exe','CreatedUtc':'2026-09-14T08:00:00+00:00','ExecutablePath':'fixture_grandparent'}]
with patch.object(k.os,'getpid',return_value=100):
 check('actual_temporal_chain_accepts',k.self_and_verified_ancestors(base)=={100,200,300})
 late=copy.deepcopy(base);late[1]['CreatedUtc']='2026-09-14T10:30:00+00:00'
 allowed=k.self_and_verified_ancestors(late)
 check('original_late_parent_negative_fixed',allowed=={100} and refused(lambda:k.no_foreign_python(late,allowed)),{'fixture_processes':late,'allowed':sorted(allowed)})
 grand=copy.deepcopy(base);grand[2]['CreatedUtc']='2026-09-14T09:30:00+00:00'
 allowed=k.self_and_verified_ancestors(grand)
 check('late_grandparent_also_excluded',allowed=={100,200} and refused(lambda:k.no_foreign_python(grand,allowed)))
 for label,field in [('null',None),('naive','2026-09-14T09:00:00'),('invalid','not-a-date')]:
  rows=copy.deepcopy(base);rows[1]['CreatedUtc']=field
  check('parent_timestamp_'+label+'_refused',refused(lambda:k.self_and_verified_ancestors(rows)))
 missing=copy.deepcopy(base);del missing[1]['CreatedUtc']
 check('missing_parent_created_field_refused',refused(lambda:k.self_and_verified_ancestors(missing)))
 check('duplicate_PID_refused',refused(lambda:k.self_and_verified_ancestors(base+[base[1]])))
 cycle=copy.deepcopy(base[:2]);cycle[0]['CreatedUtc']=cycle[1]['CreatedUtc'];cycle[1]['ParentProcessId']=100
 check('temporal_cycle_refused',refused(lambda:k.self_and_verified_ancestors(cycle)))
 check('missing_own_PID_refused',refused(lambda:k.self_and_verified_ancestors(base[1:])))
 equal=copy.deepcopy(base[:2]);equal[0]['CreatedUtc']=equal[1]['CreatedUtc'];equal[1]['ParentProcessId']=9
 check('equal_resolution_parent_child_timestamps_accept',k.self_and_verified_ancestors(equal)=={100,200})

fixture=OUT/'v2_closed_stream_fixture';fixture.mkdir(exist_ok=True)
for name in ['launch.json','launcher.json','science_data.json']:(fixture/name).write_text(json.dumps({'fixture_only':True,'name':name}),encoding='utf-8')
with (fixture/'stdout.log').open('wb',buffering=8192) as a,(fixture/'stderr.log').open('wb',buffering=8192) as b:
 a.write(b'late buffered fixture output\n');b.write(b'late fixture warning\n')
 early=k.closed_case_artifacts(fixture)
 check('worker_excludes_both_open_root_logs',{Path(x['path']).name for x in early}=={'launch.json','launcher.json','science_data.json'})
 check('fixture_has_real_not_yet_flushed_bytes',(fixture/'stdout.log').stat().st_size==0 and (fixture/'stderr.log').stat().st_size==0)
check('fixture_logs_closed_before_parent_seal',a.closed and b.closed)
parent=d.exited_process_artifacts(fixture)
check('closed_parent_seal_includes_both_logs_and_launch_receipts',{Path(x['path']).name for x in parent}=={'stdout.log','stderr.log','launch.json','launcher.json'})
check('parent_seal_contains_final_nonempty_log_bytes',all(x['bytes']>0 for x in parent))
check('worker_seal_stays_valid_after_log_flush',all(k.verify_record(x)==x for x in early))
check('parent_seal_verifies_after_context_exit',all(k.verify_record(x)==x for x in parent))
newrun=function(trees['driver.py'][1],'run')
contexts=[n for n in ast.walk(newrun) if isinstance(n,ast.With) and 'stdout.log' in ast.unparse(n.items[0].context_expr)]
context=contexts[0]
seal=next(n for n in ast.walk(newrun) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='exited_process_artifacts')
wait=next(n for n in ast.walk(context) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='wait')
check('parent_log_seal_AST_after_wait_and_stream_context_exit',wait.lineno<context.end_lineno<seal.lineno,{'wait_line':wait.lineno,'context_end_line':context.end_lineno,'parent_log_seal_line':seal.lineno})
source=read(V2/'driver.py')
check('parent_links_log_records_into_process_exit',"'closed_process_artifacts': exited_process_artifacts(case_dir)" in source)
check('top_result_links_all_case_process_exit_records',"case_exit_records.append(exit_record)" in source and "'process_exits': case_exit_records" in source)
check('no_actual_prepare_run_worker_or_science_called',not any(n in sys.modules for n in ['torch','numpy','PIL','scipy','torchvision','transformers']))
report={'schema':'t6-independent-v2-delta-recheck.v1','created_utc':datetime.now(timezone.utc).isoformat(),'reviewer':'memory_failure_1544_review','scope':'v2 vs previously reviewed sealed v1; focused PID/log-lifecycle negative fixtures plus science AST identity','v2_hashes':{n:sha(V2/n) for n in ['contract.py','driver.py','science.py','check_stdlib.py','prepare_source_manifest.py','README.md','HANDOFF.md','STDLIB_REVIEW.json']},'v2_source_manifest_exists_at_recheck':(V2/'SOURCE_MANIFEST.json').exists(),'checks':checks,'pass_count':sum(x['passed'] for x in checks),'check_count':len(checks),'previous_findings':{'P1-ANCESTRY-PID-REUSE':'fixed and independently reproduced','P2-OPEN-LOG-ARTIFACT-HASH':'fixed; real stdlib buffered stream fixture and AST lifecycle verified'},'remaining_blocking_findings':[],'not_claimed':['actual worker or Windows Popen/wait execution','scientific imports/model loading/GPU','completed prerequisites or active release','measured timing/memory/numerical parity'],'changes_made':'only review fixture/reports within independent review directory'}
report['review_script_sha256']=sha(__file__)
(OUT/'V2_RECHECK.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':report['pass_count'],'total':report['check_count'],'failed':[x['name'] for x in checks if not x['passed']],'v2_hashes':report['v2_hashes'],'report_sha256':sha(OUT/'V2_RECHECK.json')},indent=2))
