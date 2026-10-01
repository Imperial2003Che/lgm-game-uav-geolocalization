"""CPU/stdlib gate and lifecycle checks; no scientific imports or GPU queries."""
import ast, copy, datetime, hashlib, importlib.util, json, sys, tempfile
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
source=HERE/'supervise_independent_comparisons.py'
spec=importlib.util.spec_from_file_location('independent_supervisor_under_review',source)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
fixtures=[]
def check(name,fn):
    fn();fixtures.append({'name':name,'passed':True})
def require_error(fn):
    try: fn()
    except (RuntimeError,ValueError): return
    raise AssertionError('Expected failure')
def same(a,b): assert a==b,(a,b)
stamp='2026-09-14T00:00:00+00:00'
ready={'status':'latest_baselines_finished_review_pending','plan_sha256':'f'*64,
       'supervisor_pid':100,'supervisor_started_utc':stamp,
       'jobs':[{'id':identifier,'status':'completed','exit_code':0,'pid':200+i,'started_utc':stamp} for i,identifier in enumerate(m.PRECEDING_JOBS)]}
def gate(value,live=lambda *_:False):
    return m.preceding_ready(value,is_alive=live,expected_plan_sha256='f'*64)
check('completed_author_jobs_and_exited_owners_pass',lambda:same(gate(ready),True))
check('live_controller_waits',lambda:same(gate(ready,lambda pid,*_:pid==100),False))
check('live_child_waits',lambda:same(gate(ready,lambda pid,*_:pid==201),False))
check('waiting_predecessor_cannot_release',lambda:same(gate({**ready,'status':'waiting_for_registered_extensions'}),False))
check('wrong_completed_plan_rejected',lambda:require_error(lambda:gate({**ready,'plan_sha256':'0'*64})))
check('missing_job_rejected',lambda:require_error(lambda:gate({**ready,'jobs':ready['jobs'][:1]})))
check('wrong_job_order_rejected',lambda:require_error(lambda:gate({**ready,'jobs':list(reversed(ready['jobs']))})))
for field,value in [('status','running'),('exit_code',1)]:
    bad=copy.deepcopy(ready);bad['jobs'][0][field]=value
    check('unsuccessful_job_'+field,lambda bad=bad:require_error(lambda:gate(bad)))
bad=copy.deepcopy(ready);bad['jobs'][0]['children']=[{'worker_pid':300,'started_utc':stamp}]
check('nested_live_worker_waits',lambda:same(gate(bad,lambda pid,*_:pid==300),False))
bad=copy.deepcopy(ready);del bad['jobs'][0]['started_utc']
check('child_without_identity_time_rejected',lambda:require_error(lambda:gate(bad)))
def deny(*_): raise RuntimeError('access denied fixture')
check('unknown_pid_access_rejected',lambda:require_error(lambda:gate(ready,deny)))
check('missing_supervisor_identity_rejected',lambda:require_error(lambda:gate({**ready,'supervisor_started_utc':None})))
for pid in (None,0,-1,True,'201'):
    invalid=copy.deepcopy(ready);invalid['jobs'][0]['pid']=pid
    check('invalid_top_level_job_pid_'+repr(pid),lambda invalid=invalid:require_error(lambda:gate(invalid)))
for stamp_value in (None,'2026-09-14T00:00:00','not-a-time'):
    invalid=copy.deepcopy(ready);invalid['jobs'][1]['started_utc']=stamp_value
    check('invalid_job_start_'+repr(stamp_value),lambda invalid=invalid:require_error(lambda:gate(invalid)))
check('supervisor_boolean_pid_rejected',lambda:require_error(lambda:gate({**ready,'supervisor_pid':True})))
check('real_current_predecessor_does_not_release',lambda:same(gate(m.read(HERE/'latest_baseline_status.json')),False))

before=ast.parse((HERE/'supervise_latest_baselines.py').read_text(encoding='utf-8'))
after=ast.parse(source.read_text(encoding='utf-8'))
def functions(tree):return {x.name:ast.dump(x,include_attributes=False) for x in tree.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef))}
b,a=functions(before),functions(after)
for name in ('alive','runtime_snapshot','entrypoint','assert_gpu_idle','check_state_jobs','save','sha'):
    check('preserved_reviewed_function_'+name,lambda name=name:same(b[name],a[name]))
text=source.read_text(encoding='utf-8')
check('new_queue_uses_own_state_and_lock',lambda:same(all(x in text for x in ("path = HERE / 'independent_comparison_status.json'","HERE / 'independent_comparison_supervisor.lock'","default=HERE / 'independent_comparison_plan.json'")),True))
check('preserves_per_experiment_resource_environment',lambda:same("environment['OMP_NUM_THREADS']" in text or "for variable in ('OPENBLAS_NUM_THREADS'" in text,False))

class FakeChild:
    pid=555
    returncode=0
    def poll(self): return 0
class Kernel:
    def SetThreadExecutionState(self,*_): return 1
class Windll: kernel32=Kernel()
launches=[]
with tempfile.TemporaryDirectory(prefix='lgm_independent_lifecycle_') as tmp:
    folder=Path(tmp); plan_path=folder/'independent_comparison_plan.json'
    predecessor={**ready,'plan_sha256':'f'*64}
    (folder/'latest_baseline_status.json').write_text(json.dumps(predecessor),encoding='utf-8')
    jobs=[{'id':'fixture_one','command':['python',str(source)],'cwd':str(folder),'source_sha256':{str(source):m.sha(source)}}]
    plan={'jobs':jobs,'preceding_latest_plan_sha256':'f'*64,'remaining_work':['not a final manuscript']}
    plan_path.write_text(json.dumps(plan),encoding='utf-8')
    def fake_launch(*args,**kwargs):
        persisted=m.read(folder/'independent_comparison_status.json')
        assert persisted['jobs'][0]['status']=='running'
        assert 'started_utc' in persisted['jobs'][0]
        launches.append('intent_persisted_before_spawn');return FakeChild()
    with patch.object(m,'HERE',folder),patch.object(m,'check_plan',lambda _:None),patch.object(m,'preceding_ready',lambda *a,**k:True),patch.object(m,'assert_gpu_idle',lambda:None),patch.object(m.subprocess,'Popen',fake_launch),patch.object(m.ctypes,'windll',Windll()),patch.object(sys,'argv',[str(source),'--plan',str(plan_path)]):
        m.main()
        result=m.read(folder/'independent_comparison_status.json')
        check('mock_success_final_namespace',lambda:same(result['status'],'independent_comparisons_finished_review_pending'))
        check('mock_child_evidence_has_exit_and_hashes',lambda:same(result['jobs'][0]['exit_code']==0 and bool(result['jobs'][0]['stdout_sha256']) and result['jobs'][0]['pid']==555,True))
        check('persist_launch_intent_before_child',lambda:same(launches,['intent_persisted_before_spawn']))
        check('completed_state_cannot_silently_rerun',lambda:require_error(m.main))
    # Remove only files in this temporary fixture through TemporaryDirectory.

for name in ('torch','torchvision','numpy','scipy','matplotlib','PIL','sklearn'):
    assert name not in sys.modules,name
report={'schema':'independent-supervisor-stdlib-review.v1','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':m.sha(source),'passed':len(fixtures),'fixtures':fixtures,'scientific_modules_imported':[],'actual_children_launched':0,'gpu_queries':0,'scope':'Behavioral release/lifecycle fixtures with all child execution mocked; no experiment run.'}
(HERE/'independent_supervisor_stdlib_review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'passed':len(fixtures),'source_sha256':report['source_sha256']}))
