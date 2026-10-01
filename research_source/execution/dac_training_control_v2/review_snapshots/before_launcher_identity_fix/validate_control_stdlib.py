"""Adversarial control fixtures only; zero scientific imports or real process probes."""
import ast
from copy import deepcopy
import importlib.abc
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

BLOCKED={'torch','numpy','PIL','cv2','timm','torchvision','scipy','albumentations','transformers','tensorboard','sklearn'}
attempts=[]
class BlockScience(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in BLOCKED:
            attempts.append(fullname);raise RuntimeError('Science import forbidden in static fixture')
sys.meta_path.insert(0,BlockScience());sys.dont_write_bytecode=True
import dac2_contracts as c
import dac2_gates as g
import run_dac_stage as stage

checks=[]
def check(name,function):
    try: function();checks.append({'name':name,'passed':True})
    except BaseException as error: checks.append({'name':name,'passed':False,'error':repr(error)})
def rejects(function):
    try: function()
    except (RuntimeError,ValueError,TypeError,KeyError): return
    raise AssertionError('Bad evidence was admitted')
def assert_(condition):
    if not condition: raise AssertionError('Control fixture mismatch')

def profile_data():
    batch=[];resources=[]
    for index,steps in enumerate((0,1,2),1):
        batch.append({'batch_attempt':index,'loss':1/index,'loss_finite':True,
            'actual_optimizer_steps':steps,'optimizer_updated_this_batch':index>1,'amp_skips':index-steps,
            'scale_after_update':1024,'lr_after_scheduler':0.0001})
        resources.append({'batch_attempt':index,'actual_adamw_steps':steps,'amp_skips':index-steps,
            'peak_allocated_bytes':100*index,'peak_reserved_bytes':200*index,
            'allocated_bytes':100,'reserved_bytes':200,'seconds_including_data_and_synchronization':0.01})
    report={'actual_adamw_steps':2,'completed_optimizer_amp_steps':3,'amp_skips':1,
        'initial_parameter_sha256':'a'*64,'final_parameter_sha256':'b'*64,
        'representative_parameter':'model_1.convnext.downsample_layers.0.0.weight',
        'peak_allocated_bytes':300,'peak_reserved_bytes':600,'seconds_including_initialization':1.0,
        'final_scaler_state':{'scale':1024},'losses':[row['loss'] for row in batch]}
    return report,batch,resources

def fixture_bound(path,value,hash_value=None):
    data=json.dumps(value,allow_nan=False).encode()
    return c.Bound(Path(path).resolve(),data,hash_value or c.digest(data))

def gate_fixture(kind):
    start='2026-09-14T00:00:00+00:00';finish='2026-09-14T00:01:00+00:00'
    job=lambda ident:{'id':ident,'status':'completed','exit_code':0,'pid':777,'started_utc':start,'finished_utc':finish}
    specs=[('status.json','completed',None),('pipeline_status.json','ready_for_extension_preparation',
        ['formal_aggregate','formal_figures','cross_dataset_transfer','robustness','robustness_aggregate','query_analysis','formal_efficiency_component']),
        ('extension_status.json','registered_extensions_finished_review_pending',['a','b','c','d']),
        ('latest_baseline_status.json','latest_baselines_finished_review_pending',['camp','dac']),
        ('independent_comparison_status.json','independent_comparisons_finished_review_pending',['matched','camp_train','camp_eval'])]
    files={};rows=[]
    for name,status,ids in specs:
        value={'status':status,'pid':777,'started_utc':start,'finished_utc':finish,'commands':[{'pid':778,'exit_code':0}]}
        if name=='status.json': value['stage']='all'
        if ids: value['jobs']=[job(ident) for ident in ids]
        row={'status_path':str(c.EXECUTION/name),'required_status':status}
        plan_name={'extension_status.json':'extension_plan.json','latest_baseline_status.json':'latest_baseline_plan.json','independent_comparison_status.json':'independent_comparison_plan_v2.json'}.get(name)
        if plan_name:
            predecessor=fixture_bound(c.EXECUTION/plan_name,{'jobs':[job(ident) for ident in ids]},'a5318f7a60497cc7c9ccb74b7cd82ef7f71fcb072c36a90fb192ea27acc6ca49' if name=='independent_comparison_status.json' else None)
            files[predecessor.path]=predecessor;row['plan_sha256']=predecessor.sha256;value['plan_sha256']=predecessor.sha256
        if kind=='nested_failed' and name=='status.json': value['commands'][0]['exit_code']=1
        if kind=='nested_running' and name=='status.json': value['commands'][0]['status']='running'
        if kind=='wrong_ids' and name=='extension_status.json': value['jobs'][0]['id']='wrong'
        if kind=='failed_child' and name=='latest_baseline_status.json': value['jobs'][0]['exit_code']=1
        if kind=='fifth_running' and name=='independent_comparison_status.json': value['status']='running'
        if kind=='no_finish': value.pop('finished_utc')
        state=fixture_bound(c.EXECUTION/name,value);files[state.path]=state;row['status_sha256']=state.sha256;rows.append(row)
    if kind=='missing_fifth': rows=rows[:-1]
    if kind=='wrong_fifth_plan': rows[-1]['plan_sha256']='b'*64
    plan=fixture_bound(c.EXECUTION/'mock_plan',{'control_binding':{'mock_control':'fixture'},'science_binding':{'mock_science':'fixture'}})
    release=fixture_bound(c.EXECUTION/'mock_release',{'schema':'dac-serial-release.v2','allow_cuda':True,
        'plan_sha256':plan.sha256,'stages':['profile','train'],'control_binding':plan.value['control_binding'],
        'science_binding':plan.value['science_binding'],'predecessors':rows})
    current=None
    if kind in ('slow_start','no_finish'): current='2026-09-14T00:00:40+00:00'
    if kind=='reused_after_finish': current='2026-09-14T00:02:00+00:00'
    def load(path,expected):
        bound=files[Path(path).resolve()]
        c.require(bound.sha256==expected,'Mock pinned input changed')
        return bound
    gpu='222, custom_cuda_app.exe' if kind=='nonpython_gpu' else '222, python.exe' if kind=='python_gpu' else ''
    with patch.object(c.Bound,'load',side_effect=load),patch.object(c.Bound,'unchanged',return_value=None),patch.object(g,'process_started',return_value=current),patch.object(g.subprocess,'run',return_value=SimpleNamespace(stdout=gpu)):
        action=lambda:g.serial_gate(plan,release,'profile')
        if kind in ('valid','reused_after_finish'): assert_(len(action()['predecessors'])==5)
        else: rejects(action)

def main():
    check('all new Python sources parse without imports',lambda:[ast.parse(path.read_text(encoding='utf-8')) for path in c.HERE.glob('*.py')])
    check('v1 sealed 42 payloads unchanged and eight scientific files bound',lambda:assert_(len(c.science_binding()['source_files_sha256'])==8))
    refs=c.read(c.SCIENCE/'INPUT_REFERENCES.json');proof=c.read(c.CPU_RESULT)
    cpu_plan={'cpu_compatibility_proof':{'path':str(c.CPU_RESULT),'sha256':c.CPU_RESULT_SHA},
        'environment':proof['environment'],'pretrained':refs['pretrained'],
        'data_manifest_path':refs['data_manifest_path'],'data_manifest_sha256':refs['data_manifest_sha256']}
    check('genuine pinned CPU result, raw artifacts and actual root exit0 accepted',lambda:c.validate_cpu(cpu_plan))
    for kind in ('fixture','wrong_hash','wrong_environment','missing_origin'):
        def bad_cpu(kind=kind):
            plan=deepcopy(cpu_plan)
            if kind=='wrong_hash':plan['cpu_compatibility_proof']['sha256']='0'*64
            if kind=='wrong_environment':plan['environment']={}
            if kind in ('fixture','missing_origin'):
                altered=deepcopy(proof)
                if kind=='fixture':altered['fixture_only']=True
                else:altered['runtime_environment']={}
                original=c.Bound.load
                def patched(path,expected):
                    if Path(path).resolve()==c.CPU_RESULT:return fixture_bound(path,altered,c.CPU_RESULT_SHA)
                    return original(path,expected)
                with patch.object(c.Bound,'load',side_effect=patched):rejects(lambda:c.validate_cpu(plan))
            else:rejects(lambda:c.validate_cpu(plan))
        check('reject forged/incomplete CPU evidence: '+kind,bad_cpu)
    for kind in ('valid','fixture','nan_peak','inf_peak','float_bytes','bool_bytes','smaller_summary','bad_loss','wrong_actual','same_weight','bad_scaler','trace_gap','negative_elapsed'):
        def profile_case(kind=kind):
            report,batch,resource=profile_data()
            if kind=='fixture':report['fixture_only']=True
            elif kind=='nan_peak':report['peak_allocated_bytes']=float('nan')
            elif kind=='inf_peak':resource[-1]['peak_allocated_bytes']=float('inf')
            elif kind=='float_bytes':report['peak_allocated_bytes']=300.0
            elif kind=='bool_bytes':report['peak_allocated_bytes']=True
            elif kind=='smaller_summary':report['peak_allocated_bytes']=200
            elif kind=='bad_loss':batch[-1]['loss']=float('inf')
            elif kind=='wrong_actual':report['actual_adamw_steps']=3;report['amp_skips']=0
            elif kind=='same_weight':report['final_parameter_sha256']=report['initial_parameter_sha256']
            elif kind=='bad_scaler':report['final_scaler_state']['scale']=0
            elif kind=='trace_gap':resource.pop()
            elif kind=='negative_elapsed':resource[-1]['seconds_including_data_and_synchronization']=-1
            action=lambda:c.profile_trace(report,batch,resource)
            if kind=='valid':assert_(action()['actual_adamw_steps']==2)
            else:rejects(action)
        check('profile summary/real-trace pure contract: '+kind,profile_case)
    for value in ('NaN','Infinity','-Infinity'):
        check('nonfinite JSON rejected before any admission: '+value,lambda value=value:rejects(lambda:c.strict_json('{"value":'+value+'}')))
    for kind in ('valid','nested_failed','nested_running','wrong_ids','failed_child','fifth_running','missing_fifth','wrong_fifth_plan','slow_start','no_finish','reused_after_finish','nonpython_gpu','python_gpu'):
        check('fresh five-stage/process/GPU gate mocked only: '+kind,lambda kind=kind:gate_fixture(kind))
    def inherited_worker():
        value={'started_utc':'2026-09-14T00:00:00Z','finished_utc':'2026-09-14T00:02:00Z',
            'workers':[{'worker_pid':9,'process_created_utc':'2026-09-14T00:00:50Z'}]}
        result=list(g.owners(value));assert_(result[0]['started_utc'].endswith('50Z') and result[0]['finished_utc'].endswith('02:00Z'))
    check('historical worker creation and parent finish inherited',inherited_worker)
    with tempfile.TemporaryDirectory(prefix='contract_fixtures_',dir=c.HERE) as temporary:
        root=Path(temporary).resolve();assert_(root.is_relative_to(c.HERE))
        def bound_change():
            path=root/'input.json';path.write_text('{"seed":1}',encoding='utf-8')
            admitted=c.Bound.load(path,c.sha(path));saved=admitted.copy(root/'copy.json')
            path.write_text('{"seed":3}',encoding='utf-8')
            assert_(admitted.value['seed']==1 and saved.value['seed']==1)
            rejects(admitted.unchanged);saved.unchanged()
        check('immutable admission keeps old bytes and detects external mutation',bound_change)
    for actual,attempted,expected in ((0,1,'continue'),(1,2,'continue'),(2,3,'complete'),(2,2,'complete')):
        check('two real updates stop only at post-batch boundary '+str((actual,attempted)),lambda actual=actual,attempted=attempted,expected=expected:assert_(stage.profile_decision(actual,attempted)==expected))
    check('all AMP skipped for32 attempts fails instead of completed',lambda:rejects(lambda:stage.profile_decision(0,32)))
    def checkpoint_binding():
        source=(c.HERE/'run_dac_stage.py').read_text(encoding='utf-8');tree=ast.parse(source)
        save=next(node for node in ast.walk(tree) if isinstance(node,ast.FunctionDef) and node.name=='save_complete')
        statements=[ast.unparse(node) for node in save.body]
        start=next(i for i,line in enumerate(statements) if 'super().save_complete(namespace)' in line)
        assert_('session.unchanged()' in statements[start-1] and 'session.unchanged()' in statements[start+1])
    check('fixed snapshot binding verified both before and after original checkpoint serialization',checkpoint_binding)
    check('no scientific imports or actual process/GPU probes executed in tests',lambda:assert_(not attempts and not BLOCKED.intersection(sys.modules)))
    report={'schema':'dac-v2-control-stdlib-validation.v1','generated_utc':c.utc(),
        'status':'passed' if all(row['passed'] for row in checks) else 'failed','passed':sum(row['passed'] for row in checks),'total':len(checks),
        'checks':checks,'source_files_sha256':{p.name:c.sha(p) for p in c.HERE.glob('*.py')},
        'scientific_imports':False,'real_process_gpu_queries':False,'new_cpu_model_probe':False,'new_resource_measurements':False,
        'mock_values_are_not_measurements':True,'v1_manifest_sha256':c.SCIENCE_MANIFEST_SHA,'real_cpu_result_anchor_sha256':c.CPU_RESULT_SHA}
    c.write(c.HERE/'CONTROL_VALIDATION.json',report)
    print(json.dumps({'status':report['status'],'passed':report['passed'],'total':report['total'],'failures':[row for row in checks if not row['passed']]}))
    if report['status']!='passed':raise SystemExit(1)
if __name__=='__main__':main()
