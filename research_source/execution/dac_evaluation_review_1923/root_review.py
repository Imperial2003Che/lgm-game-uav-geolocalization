"""Independent stdlib review; temporary control fixtures are not research data."""
import ast
from datetime import datetime, timezone
import hashlib
import importlib.abc
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
E=HERE.parent
OLD=E/'dac_independent_evaluation_v1'
NEW=E/'dac_independent_evaluation_v2'
checks=[]
def check(name,value):
    checks.append({'name':name,'passed':bool(value)})
    if not value: raise AssertionError(name)
def rejected(name,call):
    try:call()
    except (RuntimeError,ValueError):check(name,True)
    else:check(name,False)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def tree(root,name):return ast.parse((root/name).read_text('utf-8-sig'))
def function(root,file,name):return next(x for x in tree(root,file).body if isinstance(x,ast.FunctionDef) and x.name==name)
def dump(node):return ast.dump(node,include_attributes=False)

class NoScience(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'torch','numpy','scipy','PIL','cv2','matplotlib','torchvision','transformers'}:
            raise AssertionError('Review attempted scientific import: '+fullname)
sys.meta_path.insert(0,NoScience())
sys.path.insert(0,str(NEW))
import contract_snapshots as s
import run_evaluation as r

check('strict402 loader unchanged byte for byte',sha(OLD/'dac_independent_model.py')==sha(NEW/'dac_independent_model.py'))
check('complete optimizer/RNG checks unchanged byte for byte',sha(OLD/'complete_state_checks.py')==sha(NEW/'complete_state_checks.py'))
check('actual image/model encoding AST unchanged',dump(function(OLD,'run_evaluation.py','encode_seed'))==dump(function(NEW,'run_evaluation.py','encode_seed')))
for iterator,label in (("binding['seeds']",'all three actual seed encoding/ranking loops'),("('r_at_1', 'r_at_5', 'r_at_10', 'r_at_20', 'official_trapezoid_mAP', 'rank_precision_mAP', 'MRR')",'mean and sample SD metric loop')):
    nodes=[]
    for root in (OLD,NEW):
        nodes.append([dump(x) for x in ast.walk(function(root,'run_evaluation.py','evaluate')) if isinstance(x,ast.For) and ast.unparse(x.iter)==iterator])
    check(label+' unchanged',bool(nodes[0]) and nodes[0]==nodes[1])
source_strings={x.value for x in ast.walk(function(NEW,'protocol.py','source_evidence')) if isinstance(x,ast.Constant) and isinstance(x.value,str)}
check('prepared identity covers all five actual adapter modules',{'protocol.py','run_evaluation.py','dac_independent_model.py','complete_state_checks.py','contract_snapshots.py'}<=source_strings)
execution_files=set()
for x in ast.walk(function(E/'dac_training_execution_v2','dac6_contracts.py','verify_training_artifacts')):
    if isinstance(x,ast.For) and isinstance(x.target,ast.Name) and x.target.id=='name' and isinstance(x.iter,ast.Tuple):
        execution_files.update(y.value for y in x.iter.elts if isinstance(y,ast.Constant) and isinstance(y.value,str))
binding_names=set()
for x in ast.walk(function(NEW,'protocol.py','bind_seed')):
    if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='names' for t in x.targets):
        binding_names.update(y.value for y in x.value.elts)
check('actual training API attachments all mapped by evaluator',execution_files<=binding_names|{'checkpoint_complete.pth','weights_end.pth'})

with tempfile.TemporaryDirectory(prefix='fixtures_',dir=HERE) as temp:
    root=Path(temp)
    document=root/'snapshot.json'
    document.write_bytes(s.serialized_json({'seed':1}))
    with s.snapshot_scope():
        frozen=s.input_snapshot(document)
        check('first-read artifact identifies its actual original bytes',frozen.sha256==sha(document) and frozen.value=={'seed':1})
        document.write_bytes(s.serialized_json({'seed':2}))
        check('captured parsed object does not switch to new bytes',frozen.value=={'seed':1})
        rejected('mutated first-read source rejected',lambda:s.input_snapshot(document))
    document.write_bytes(s.serialized_json({'seed':1}))
    with s.snapshot_scope():
        original=s.input_snapshot(document)
        with s.snapshot_scope():check('nested command reuses same input snapshot',s.input_snapshot(document) is original)
        document.write_bytes(s.serialized_json({'seed':3}))
        rejected('nested command mutation propagates to final check',s.unchanged_inputs)
    with s.snapshot_scope():
        out=root/'written.json';value={'caption':'真实字节','values':[1,2]}
        out.write_bytes(s.serialized_json(value));created=s.bind_written(out,value)
        check('Windows actual written bytes match producer artifact',created.sha256==sha(out))
        out.write_bytes(s.serialized_json({'caption':'changed'}))
        rejected('generated contract mutation rejected',s.unchanged_inputs)
    prepared_path=root/'prepared.json';binding_path=root/'binding.json';release_path=root/'release.json'
    prepared={'training_execution_package':{'sha256':'a'*64},'training_execution_plan':{'sha256':'b'*64}}
    prepared_path.write_bytes(s.serialized_json(prepared));binding_path.write_bytes(s.serialized_json({'seed_count':3}))
    release={'schema':r.RELEASE_SCHEMA,'allow_cuda':True,'prepared_sha256':sha(prepared_path),'binding_sha256':sha(binding_path),
             'training_execution_package_sha256':'a'*64,'training_execution_plan_sha256':'b'*64}
    def reset_release():release_path.write_bytes(s.serialized_json(release))
    reset_release()
    for row,should_pass in (('',True),('123, native_cuda.exe\n',False),('456, python.exe\n',False),('789, unknown_process\n',False)):
        with s.snapshot_scope(),patch.object(r,'verify_execution_package',return_value=None),patch.object(r.subprocess,'run',return_value=SimpleNamespace(stdout=row)):
            call=lambda:r.release_gate(prepared,prepared_path,binding_path,release_path)
            if should_pass:check('empty CUDA-owner inventory admitted',call()['nvidia_compute_rows']==[])
            else:rejected('active CUDA owner rejected: '+row.strip(),call)
    for path in (prepared_path,binding_path,release_path):
        original=path.read_bytes()
        with s.snapshot_scope(),patch.object(r,'verify_execution_package',return_value=None),patch.object(r.subprocess,'run',return_value=SimpleNamespace(stdout='')) as command:
            for item in (prepared_path,binding_path,release_path):s.input_snapshot(item)
            path.write_bytes(original+b' ')
            rejected('read-to-gate mutation rejected: '+path.name,lambda:r.release_gate(prepared,prepared_path,binding_path,release_path))
            check('mutated '+path.name+' rejected before CUDA query',not command.called)
        path.write_bytes(original)

check('review imported no scientific package',not any(x in sys.modules for x in ('torch','numpy','scipy','PIL','cv2','matplotlib')))
check('no real evaluation preparation/release/output created',not any((NEW/x).exists() for x in ('preparations','runtime','results')))
files=[NEW/x for x in ('protocol.py','run_evaluation.py','dac_independent_model.py','complete_state_checks.py','contract_snapshots.py')]
report={'time':datetime.now(timezone.utc).isoformat(),'status':'passed','scope':'Independent stdlib/AST/control fixtures; no model, GPU, science, or research data generated',
        'checks':checks,'count':len(checks),'source_files':{str(p):sha(p) for p in files},
        'training_contract_sha256':sha(E/'dac_training_execution_v2/dac6_contracts.py'),
        'review_independence':'same model family, separate reviewer from implementation; deterministic checks only',
        'gpu_execution_performed':False,'test_metrics_produced':False}
(HERE/'ROOT_V2_RECHECK.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':report['status'],'checks':len(checks),'report':str(HERE/'ROOT_V2_RECHECK.json')},ensure_ascii=False))
