"""Independent DAC6 candidate audit. stdlib/AST/mocks, no real stage or release."""
import ast
from contextlib import ExitStack
from copy import deepcopy
import importlib.abc
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

OUT=Path(__file__).resolve().parent
SOURCE=OUT.parent/'dac_training_execution_v2'
FIX=OUT/'fixtures';FIX.mkdir(exist_ok=True)
BLOCKED={'torch','torchvision','numpy','PIL','cv2','timm','scipy','sklearn','albumentations','transformers','tensorboard'}
ATTEMPTS=[];sys.dont_write_bytecode=True
class NoScience(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in BLOCKED:
            ATTEMPTS.append(fullname);raise RuntimeError('Scientific import forbidden: '+fullname)
sys.meta_path.insert(0,NoScience());sys.path.insert(0,str(SOURCE))
import dac6_contracts as d
import run_six_stages as run
import stage_entry
import validate_execution_stdlib as author_tests

CHECKS=[]
EXPECTED={'dac6_contracts.py':'e35c59ec784a96062cafe905dcf15943d7d23780e98c296b0f9fd5523d38a6e3',
    'run_six_stages.py':'3e68d2cb4c03f1e0b69947e15699b87669c9567e1e0fa9f631fed56fbab5af21',
    'stage_entry.py':'1fa5f47623a1341b0c3637fc2b2f161e38a8816e614ec04648a6cdea05322232',
    'execution_spec.json':'069c8531fd73de799b47d538ff95f11bedab9a720f29dc607bebe5d397b7d78e'}
INITIAL={p.relative_to(SOURCE).as_posix():d.sha(p) for p in SOURCE.rglob('*') if p.is_file()}
def require(value,message='assertion failed'):
    if not value:raise AssertionError(message)
def rejects(fn):
    try:fn()
    except (RuntimeError,ValueError,KeyError,TypeError,FileNotFoundError,FileExistsError):return
    raise AssertionError('Invalid data was not rejected')
def check(name,fn,kind='contract_check'):
    try:CHECKS.append({'name':name,'passed':True,'kind':kind,'detail':fn()})
    except BaseException as error:CHECKS.append({'name':name,'passed':False,'kind':kind,'error':repr(error)})
def new_dir(label):
    path=FIX/(label+'_'+d.c.utc().replace(':','').replace('.',''));path.mkdir();return path

check('candidate files match handed-off SHA values',lambda:require(all(d.sha(SOURCE/n)==v for n,v in EXPECTED.items())))
spec=d.spec_bound(SOURCE/'execution_spec.json',EXPECTED['execution_spec.json'])
check('real spec resolves exact sealed inputs and ordered six stages',lambda:require([x['id'] for x in spec.value['jobs']]==d.ORDER))
check('no real executor runtime or manifest exists at review start',lambda:require(not (SOURCE/'runtime').exists() and not (SOURCE/'PREPARATION_MANIFEST.json').exists()))
check('profile begins without inherited state',lambda:require(run.late_profile_binding({'stage':'profile'},None) is None))
prior={'id':'seed_1_profile','status':'completed','artifact_verification':{'profile':{'sha256':'a'*64},'lifecycle':{'sha256':'b'*64}}}
check('train binds actual immediately preceding same-seed profile hashes',lambda:require(run.late_profile_binding({'stage':'train','seed':1},prior)=={'profile_sha256':'a'*64,'receipt_sha256':'b'*64}))
check('train refuses missing profile',lambda:rejects(lambda:run.late_profile_binding({'stage':'train','seed':1},None)))
check('train refuses another seed profile',lambda:rejects(lambda:run.late_profile_binding({'stage':'train','seed':2},prior)))
check('train refuses failed prior profile',lambda:rejects(lambda:run.late_profile_binding({'stage':'train','seed':1},{**prior,'status':'failed'})))

def release_case(kind):
    root=new_dir('root_release_contract')
    value={'schema':'dac-six-stage-release.v2','allow_run':True,'execution_spec_sha256':spec.sha256,
        'execution_manifest_sha256':'a'*64,'stage_order':d.ORDER,
        'predecessors':[{'status_path':str(d.EXECUTION/name)} for name in ('status.json','pipeline_status.json','extension_status.json','latest_baseline_status.json','independent_comparison_status.json')]}
    if kind=='four':value['predecessors'].pop()
    if kind=='duplicate':value['predecessors'][-1]=value['predecessors'][0]
    if kind=='wrong_manifest':value['execution_manifest_sha256']='b'*64
    if kind=='wrong_spec':value['execution_spec_sha256']='b'*64
    if kind=='wrong_order':value['stage_order']=list(reversed(d.ORDER))
    path=root/'test_release_contract.json';d.c.write(path,value)
    with patch.object(d,'own_manifest',return_value='a'*64):
        if kind=='valid':return d.release_bound(path,d.sha(path),spec).sha256
        rejects(lambda:d.release_bound(path,d.sha(path),spec))
check('root release requires exact own/spec and five predecessor path contract',lambda:release_case('valid'))
for kind in ('four','duplicate','wrong_manifest','wrong_spec','wrong_order'):
    check('root release rejects '+kind,lambda kind=kind:release_case(kind))

def producer_contract_keys():
    common=d.c.SCIENCE/'common_runtime.py';dac=d.c.SCIENCE/'dac_train_runtime.py'
    def dict_keys(node):return {k.value for k in node.keys if isinstance(k,ast.Constant) and isinstance(k.value,str)}
    def assignments(path):
        tree=ast.parse(path.read_text(encoding='utf-8'));result={}
        for node in ast.walk(tree):
            if isinstance(node,ast.Assign) and isinstance(node.value,ast.Dict):
                for target in node.targets:
                    if isinstance(target,ast.Name):result[target.id]=dict_keys(node.value)
        return tree,result
    common_tree,assigned=assignments(common);dac_tree,_=assignments(dac)
    def output_keys(tree,name,assigned):
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and len(node.args)>=2 and name in ast.unparse(node.args[0]):
                obj=node.args[1]
                if isinstance(obj,ast.Dict):return dict_keys(obj)
                if isinstance(obj,ast.Name) and obj.id in assigned:return assigned[obj.id]
        raise AssertionError('Could not find producer '+name)
    producer={'evidence':output_keys(common_tree,'training_evidence.json',assigned),
        'protocol':output_keys(dac_tree,'dac_training_protocol_evidence.json',{}),
        'sampling':output_keys(common_tree,'epoch01_sampling.json',assigned),'batch':assigned['row'],
        'status':output_keys(common_tree,"'status.json'",assigned)|{'pid','started_utc'}}
    consumer=next(n for n in ast.parse((SOURCE/'dac6_contracts.py').read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef) and n.name=='verify_training_artifacts')
    used={name:set() for name in producer}
    for node in ast.walk(consumer):
        if isinstance(node,ast.Subscript) and isinstance(node.value,ast.Name) and node.value.id in used and isinstance(node.slice,ast.Constant):used[node.value.id].add(node.slice.value)
    for name in used:require(used[name].issubset(producer[name]),'Consumer expects nonexistent producer keys: '+name+str(used[name]-producer[name]))
    return {name:sorted(keys) for name,keys in used.items()}
check('training artifact consumer keys agree with frozen real producer AST',producer_contract_keys)

def artifact_case(kind):
    root=new_dir('artifact_'+kind)
    plan,receipt,output,inputs=author_tests.train_fixture(root)
    if kind=='weights_changed':(output/'weights_end.pth').write_bytes(b'INDEPENDENT STDLIB NEGATIVE TEST, NOT WEIGHTS')
    elif kind=='missing_optimizer_trace':(output/'batch_progress.jsonl').write_bytes(b'')
    elif kind=='changed_scale':
        evidence=d.c.read(output/'training_evidence.json');evidence['final_scaler_state']['scale']=512;d.c.write(output/'training_evidence.json',evidence)
    elif kind=='wrong_batchsize':
        sampling=d.c.read(output/'epoch01_sampling.json');sampling['nominal_pairs_per_batch']=12;d.c.write(output/'epoch01_sampling.json',sampling)
    elif kind=='changed_final_config':d.c.write(output/'effective_configuration.json',{'seed':3})
    with patch.object(d,'INPUTS',inputs),patch.object(d.g,'exited',return_value=[]):
        if kind=='valid':
            result=d.verify_training_artifacts(plan,receipt)
            require(set(result['files'])>={'weights_end.pth','checkpoint_complete.pth','batch_progress.jsonl','serial_release.json','resource_profile_lifecycle.json'})
            require(result['tensor_values_independently_loaded'] is False)
            return {'bound_files':len(result['files']),'scope':'clearly labelled stdlib placeholder fixture only; no checkpoint tensor load'}
        rejects(lambda:d.verify_training_artifacts(plan,receipt))
check('producer-shaped artifact fixture has reachable full verifier path',lambda:artifact_case('valid'))
for kind in ('weights_changed','missing_optimizer_trace','changed_scale','wrong_batchsize','changed_final_config'):
    check('artifact verifier rejects '+kind,lambda kind=kind:artifact_case(kind))

def outer_case(actual_code=0,launcher_code=0,job_count=6,candidate_bad=False,mutate_release=False):
    root=new_dir('outer_observer');stamp='2026-09-14T00:00:00+00:00'
    rows=[{'id':ident} for ident in d.ORDER]
    fake_spec=SimpleNamespace(path=root/'spec.json',sha256='a'*64,value={'jobs':rows,'status_path':str(root/'runtime/status.json'),'completion_path':str(root/'runtime/completion_manifest.json')},unchanged=lambda:None)
    release_path=root/'test_root_release.json';d.c.write(release_path,{'test_contract_only':True})
    fake_release=d.c.Bound.load(release_path,d.sha(release_path))
    verified=[];events=[]
    class Process:
        def __init__(self,*args,**kwargs):
            self.pid=101;self._handle=1;self.returncode=None
            request=d.c.read(root/'runtime/coordinator_request.json')
            identity={'schema':'dac-actual-worker-identity.v2','pid':202,'started_utc':stamp,'plan_sha256':fake_spec.sha256,'release_sha256':fake_release.sha256,
                'lineage':[{'pid':202,'started_utc':stamp,'parent_process_id':101},{'pid':101,'started_utc':stamp,'parent_process_id':request['parent_pid']},
                    {'pid':request['parent_pid'],'started_utc':stamp,'parent_process_id':999}]}
            d.c.write(root/'runtime/coordinator_identity.json',identity)
        def poll(self):return self.returncode
        def wait(self):
            events.append('launcher_wait_returned');self.returncode=launcher_code
            state={'schema':'dac-six-stage-execution-status.v2','status':'completed','exit_code':0,'controller_pid':202,'controller_started_utc':stamp,'finished_utc':'2026-09-14T00:01:00+00:00',
                'execution_spec_sha256':fake_spec.sha256,'jobs':rows[:job_count]}
            d.c.write(root/'runtime/status.json',state)
            d.c.write(root/'runtime/candidate_completion.json',{'schema':'dac-six-stage-completion.v2','execution_spec_sha256':fake_spec.sha256,
                'execution_manifest_sha256':'c'*64,'status_sha256':d.sha(root/'runtime/status.json'),'training_artifacts':[] if candidate_bad else [{'seed':s} for s in (1,2,3)]})
            if mutate_release:d.c.write(release_path,{'mutated_after_admission':True})
            return launcher_code
    class Handle:
        def __init__(self,pid,existing_handle=None):self.pid=pid;self.started_utc=stamp
        def exit_code(self):events.append('actual_worker_exit_checked');return actual_code
        def close(self):pass
    with ExitStack() as stack:
        for obj,name,value in ((d,'HERE',root),(d,'spec_bound',lambda *a:fake_spec),(d,'release_bound',lambda *a:fake_release),
            (d,'own_manifest',lambda:'c'*64),(d.g,'process_started',lambda pid:None),(d.g,'ProcessObservation',Handle),(run.subprocess,'Popen',Process),
            (d,'verify_stage',lambda row,record:verified.append((row['id'],record['id'])) or {'test_result_only':True})):
            stack.enter_context(patch.object(obj,name,value))
        # Observer's own identity requires a live start, while post-wait ownership
        # sees the actual recorded coordinator as gone. Never probe the host.
        stack.enter_context(patch.object(d.g,'process_started',side_effect=lambda pid:stamp if pid==run.os.getpid() else None))
        error=None
        try:run.supervise_coordinator('test_spec','a'*64,str(release_path),fake_release.sha256)
        except BaseException as e:error=repr(e)
    completed=(root/'runtime/completion_manifest.json').exists()
    lifecycle=d.c.read(root/'runtime/controller_lifecycle.json')
    return {'actual_code':actual_code,'launcher_code':launcher_code,'candidate_job_count':job_count,'candidate_bad_artifacts':candidate_bad,
        'completion_written':completed,'lifecycle_status':lifecycle['status'],'verification_calls':verified,'events':events,'error':error,
        'fixture_directory':str(root),'all_processes_mocked':True}

def outer_negative(actual,launcher,mutate=False):
    value=outer_case(actual,launcher,mutate_release=mutate)
    require(not value['completion_written'] and value['lifecycle_status']=='failed');return value
check('outer only seals after actual coordinator and launcher exit0',lambda: (lambda r:(require(r['completion_written'] and r['lifecycle_status']=='completed' and len(r['verification_calls'])==6),r)[1])(outer_case()))
for actual,launcher in ((7,0),(0,7),(259,0)):
    check(f'outer rejects actual coordinator {actual}/launcher {launcher}',lambda actual=actual,launcher=launcher:outer_negative(actual,launcher))
check('changed admitted release rejects final completion and retains failure',lambda:outer_negative(0,0,True))
check('outer accepts truncated five-job completion candidate',lambda:(lambda r:(require(r['completion_written'] and len(r['verification_calls'])==5),r)[1])(outer_case(job_count=5)),'gap_reproduced')
check('outer accepts empty candidate training-artifact list',lambda:(lambda r:(require(r['completion_written']),r)[1])(outer_case(candidate_bad=True)),'gap_reproduced')

def lock_and_stream_AST():
    tree=ast.parse((SOURCE/'run_six_stages.py').read_text(encoding='utf-8'))
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='launch_stage')
    locks=[n for n in ast.walk(fn) if isinstance(n,ast.With) and 'd.g.shared_lock()' in ','.join(ast.unparse(i.context_expr) for i in n.items)]
    require(len(locks)==1 and not any(isinstance(n,ast.Call) and ast.unparse(n.func)=='subprocess.Popen' for n in ast.walk(locks[0])),'GPU lock held over child launch causes deadlock')
    for name,hash_call in (('launch_stage','closed_execution_evidence'),('supervise_coordinator','d.artifact')):
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
        filewith=[n for n in ast.walk(node) if isinstance(n,ast.With) and 'stdout.log' in ast.unparse(n.items)][0]
        hashes=[n for n in ast.walk(node) if isinstance(n,ast.Call) and ast.unparse(n.func)==hash_call]
        require(hashes and all(n.lineno>filewith.end_lineno for n in hashes),'Log hashed before close')
    return {'early_gpu_lock_released_before_Popen':True,'logs_hashed_after_with_closed':True}
check('shared GPU byte lock does not surround child launch and logs hash after close',lock_and_stream_AST)
check('no scientific import or real runtime created',lambda:require(not ATTEMPTS and not BLOCKED.intersection(sys.modules) and not (SOURCE/'runtime').exists()))
FINAL={p.relative_to(SOURCE).as_posix():d.sha(p) for p in SOURCE.rglob('*') if p.is_file()}
check('author candidate bytes unchanged by reviewer',lambda:require(FINAL==INITIAL))
report={'schema':'dac-six-stage-independent-candidate-review.v1','generated_utc':d.c.utc(),'passed':sum(x['passed'] for x in CHECKS),'total':len(CHECKS),'checks':CHECKS,
    'core_source_sha256':{n:d.sha(SOURCE/n) for n in EXPECTED},'all_source_before':INITIAL,'all_source_after':FINAL,
    'scientific_import_attempts':ATTEMPTS,'actual_scientific_execution':False,'actual_processes_or_GPU_launched':False,
    'active_release_created':False,'author_files_modified':False,'real_runtime_created':False}
d.c.write(OUT/'CANDIDATE_REVIEW_CHECKS.json',report)
print(json.dumps({'passed':report['passed'],'total':report['total'],'failures':[x for x in CHECKS if not x['passed']],
    'confirmed_gaps':[x['name'] for x in CHECKS if x['passed'] and x['kind']=='gap_reproduced']}))
