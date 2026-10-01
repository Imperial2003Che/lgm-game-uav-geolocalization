"""Independent source and real Windows lock review; no scientific execution."""
import ast
from datetime import datetime,timezone
import hashlib
import importlib.abc
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'external_efficiency_preparation'
OLD=BASE/'external_t1_driver_v1'
NEW=BASE/'external_t1_driver_v2'
checks=[]
def check(name,value):
    checks.append({'name':name,'passed':bool(value)})
    if not value:raise AssertionError(name)
def rejected(name,call):
    try:call()
    except (RuntimeError,OSError):check(name,True)
    else:check(name,False)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def functions(root,file):
    return {x.name:x for x in ast.parse((root/file).read_text('utf-8-sig')).body if isinstance(x,ast.FunctionDef)}
def dump(node):return ast.dump(node,include_attributes=False)
class NoScience(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'torch','numpy','scipy','PIL','cv2','matplotlib','torchvision','transformers'}:
            raise AssertionError('Review attempted scientific import: '+fullname)
sys.meta_path.insert(0,NoScience());sys.path.insert(0,str(NEW))
import driver as cli
import driver_contract as d
k=d.common()
before,after=functions(OLD,'scientific_worker.py'),functions(NEW,'scientific_worker.py')
for name in before:
    if name!='measure_task_sample':check('scientific AST unchanged: '+name,dump(before[name])==dump(after[name]))
sample=after['measure_task_sample']
call=next(x for x in ast.walk(sample) if isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr=='measure_sample')
check('single-query parity uses same-batch original reference inside frozen adapter',not call.keywords)
check('cross-batch reference is saved as a genuine separate array',any(isinstance(x,ast.Constant) and x.value=='actual_native_batch_reference.npy' for x in ast.walk(sample)))
check('private existence lock excludes persistent shared lock',cli.allowed_locks()=={(NEW/'external_t1_gpu.lock').resolve()})
check('frozen native adapter still has its reviewed identity',sha(BASE/'external_t1_adapter_v2/SOURCE_MANIFEST.json')=='1e6fd42b5b8777712e4283a48425bfc3f367fe58467118bf09567f59dbb11464')
for filename,allowed in (('driver.py',{'allowed_locks','run_one','shared_gpu_lock'}),('driver_contract.py',{'read_bound_json','prepare','verify_plan','verify_release'})):
    a,b=functions(OLD,filename),functions(NEW,filename)
    changed={name for name in a.keys()|b.keys() if name not in a or name not in b or dump(a[name])!=dump(b[name])}
    check('control changes remain within reviewed scope: '+filename,changed<=allowed)
with tempfile.TemporaryDirectory(prefix='fixtures_',dir=HERE) as temp:
    root=Path(temp);lock=root/'persistent.lock';lock.write_bytes(b'0retained')
    old_hash=sha(lock)
    with cli.shared_gpu_lock(lock):
        check('real shared lock preserves existing file length',lock.stat().st_size==9)
        rejected('second actual Windows handle cannot acquire owned byte',lambda:cli.shared_gpu_lock(lock).__enter__())
    check('shared lock leaves file and bytes intact',lock.exists() and sha(lock)==old_hash)
    with cli.shared_gpu_lock(lock):pass
    check('existing unlocked persistent file can be reacquired',sha(lock)==old_hash)
    plan=root/'plan.json';release=root/'release.json';plan.write_text('{"value":1}',encoding='utf-8')
    obj,record=d.read_bound_json(plan)
    check('first raw read binds object and exact file SHA',obj=={'value':1} and record['sha256']==sha(plan))
    release.write_text(json.dumps({'allow_run':True,'plan':record,'allowed_run_ids':['test_slot']}),encoding='utf-8')
    rr,pr=d.verify_release(release,plan,'test_slot')
    check('release returns same captured plan identity',pr==record and rr['sha256']==sha(release))
    for path,captured in ((plan,pr),(release,rr)):
        data=path.read_bytes();path.write_bytes(data+b' ')
        rejected('captured '+path.name+' detects later byte change',lambda:k.verify_record(captured))
        path.write_bytes(data)
    rejected('non-admitted run ID rejected',lambda:d.verify_release(release,plan,'not_registered'))
    original_verify=k.verify_record
    # Reproduce mutation immediately after the initial JSON bytes were read.
    for path in (plan,release):
        data=path.read_bytes();changed=[False]
        def mutate_then_verify(item):
            if Path(item['path'])==path and not changed[0]:
                path.write_bytes(data+b' ');changed[0]=True
            return original_verify(item)
        with patch.object(k,'verify_record',side_effect=mutate_then_verify):
            rejected('read-to-record mutation rejected: '+path.name,lambda:d.read_bound_json(path))
        path.write_bytes(data)
check('no scientific modules imported',not any(x in sys.modules for x in ('torch','numpy','PIL','cv2','matplotlib')))
check('no actual plan or scientific run created',not any((NEW/x).exists() for x in ('preparations','runs')))
report={'time':datetime.now(timezone.utc).isoformat(),'status':'passed','scope':'Source AST, raw control fixtures, actual temporary Windows byte locks only',
    'checks':checks,'count':len(checks),'source_files':{str(NEW/name):sha(NEW/name) for name in ('driver.py','driver_contract.py','scientific_worker.py')},
    'original_manifest_sha256':sha(OLD/'SOURCE_MANIFEST.json'),'real_shared_gpu_lock_touched':False,
    'scientific_imports':False,'gpu_run':False,'metrics_or_timings_produced':False}
(HERE/'ROOT_V2_RECHECK.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'passed','checks':len(checks),'report':str(HERE/'ROOT_V2_RECHECK.json')},ensure_ascii=False))
