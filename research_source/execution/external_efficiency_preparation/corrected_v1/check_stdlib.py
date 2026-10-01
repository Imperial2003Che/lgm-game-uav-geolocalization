"""Standard-library/AST/failure mocks. No mock timing is saved as research data."""
import ast
import contextlib
import importlib.abc
import json
import math
from pathlib import Path
import subprocess
import sys
import types

HERE = Path(__file__).resolve().parent
BLOCKED = {'torch','numpy','PIL','scipy','matplotlib','cv2','timm','transformers','pptx'}
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in BLOCKED:
            raise RuntimeError('Scientific import forbidden during preparation review: '+fullname)
sys.meta_path.insert(0,Guard())
sys.path.insert(0,str(HERE))
sys.dont_write_bytecode=True
import measurement_components as c

checks=[]
def passed(name): checks.append(name)
def reject(name, call, error=c.MeasurementError):
    try: call()
    except error: passed(name)
    else: raise AssertionError('Expected rejection: '+name)

for name in ('measurement_components.py','runner.py'):
    tree=ast.parse((HERE/name).read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            names=[x.name for x in node.names] if isinstance(node,ast.Import) else [node.module or '']
            assert not any(x.split('.')[0] in BLOCKED for x in names)
passed('All implementation modules parse without any scientific import statement')
assert c.ENCODING_WARMUP==20 and c.ENCODING_REPETITIONS==100
passed('Encoding warmup/repetition protocol remains 20/100')
summary=c.summarize_samples([3.,1.,2.,4.])
assert summary['raw_samples_ms']==[3.,1.,2.,4.] and summary['median']==2.5
assert summary['q1']==1.75 and summary['q3']==3.25 and summary['IQR']==1.5
passed('All raw samples retained; quartiles use linear interpolation')
for name,values in [('empty',[]),('zero',[0]),('negative',[-1]),('nan',[math.nan]),('infinite',[math.inf])]:
    reject('Invalid timing rejected: '+name,lambda v=values:c.summarize_samples(v))

class Tensor:
    def __init__(self, requires_grad=False): self.requires_grad=requires_grad
    def numel(self): return 4
class Event:
    def record(self): pass
    def synchronize(self): pass
    def elapsed_time(self, other): return 1.25
class Torch:
    Tensor=Tensor
    __version__='MOCK_ONLY_NO_REAL_FRAMEWORK'
    version=types.SimpleNamespace(cuda='MOCK_ONLY')
    backends=types.SimpleNamespace(cuda=types.SimpleNamespace(matmul=types.SimpleNamespace(allow_tf32=False)),
        cudnn=types.SimpleNamespace(allow_tf32=False,benchmark=False,deterministic=True))
    def __init__(self):
        self.grad=True
        self.cuda=types.SimpleNamespace(is_available=lambda:True,current_device=lambda:0,synchronize=lambda device:None,
            memory_allocated=lambda device:100,memory_reserved=lambda device:200,
            reset_peak_memory_stats=lambda device:None,max_memory_allocated=lambda device:140,
            max_memory_reserved=lambda device:230,Event=lambda **kwargs:Event())
    @contextlib.contextmanager
    def inference_mode(self):
        old=self.grad;self.grad=False
        try: yield
        finally:self.grad=old
    def is_grad_enabled(self): return self.grad
    def get_float32_matmul_precision(self): return 'MOCK_ONLY'
    def are_deterministic_algorithms_enabled(self):return True
t=Torch()
runtime=c.Runtime(t,types.SimpleNamespace(__version__='MOCK_ONLY'),None,None,types.SimpleNamespace(type='cuda',index=0))
wrong_device=c.Runtime(t,runtime.numpy,None,None,types.SimpleNamespace(type='cuda',index=1))
reject('CUDA event current-device mismatch rejected',lambda:c._require_cuda(wrong_device))
first_model,clip_model=object(),object()
c._require_resident_models({'formal':first_model,'clip':clip_model},(first_model,clip_model))
passed('Both real required model identities must appear in resident declaration')
reject('Missing measured CLIP resident identity rejected',lambda:c._require_resident_models({'formal':first_model},(first_model,clip_model)))
reject('Duplicate aliases of one resident model rejected',lambda:c._require_resident_models({'formal':first_model,'alias':first_model},(first_model,)))
events=[]
def operation():
    assert not t.grad
    events.append('actual_mock_call')
    return Tensor()
measured=c.measure_operation(runtime,operation,clock='cuda_event',scope='MOCK_ONLY_IN_MEMORY',
    resident_models={'MOCK_ONLY':types.SimpleNamespace(training=False)})
assert len(events)==121 and len(measured['timing']['raw_samples_ms'])==100
assert measured['memory']['peak_allocated_minus_baseline']==40 and measured['memory']['peak_reserved_minus_baseline']==30
passed('Every one of 20 warmups + peak pass + 100 CUDA timing mocks executes under inference mode')
passed('Memory report subtracts observed baseline, keeps allocated/reserved separate; mock numbers not serialized')
reject('Output with gradient graph rejected',lambda:c._checked_call(runtime,lambda:Tensor(True)))
reject('No result rejected',lambda:c._checked_call(runtime,lambda:None))
reject('Undeclared resident model set rejected',lambda:c.measure_operation(runtime,operation,clock='cuda_event',scope='mock',resident_models={}))
reject('Training-mode resident model rejected',lambda:c.measure_operation(runtime,operation,clock='cuda_event',scope='mock',resident_models={'m':types.SimpleNamespace(training=True)}))
reject('Ambiguous clock rejected',lambda:c.measure_operation(runtime,operation,clock='unsynchronized_wall',scope='mock',resident_models={'m':types.SimpleNamespace(training=False)}))
events.clear()
c.measure_operation(runtime,operation,clock='synchronized_wall',scope='MOCK_ONLY',resident_models={'m':types.SimpleNamespace(training=False)})
assert len(events)==121
passed('Host/transfer path uses a separate synchronized wall-clock implementation')

class Parameter:
    dtype='MOCK_FLOAT32'
    requires_grad=True
    def __init__(self,n):self.n=n
    def numel(self):return self.n
    def element_size(self):return 4
p1,p2,p_scale=Parameter(10),Parameter(12),Parameter(1)
class Handle:
    def __init__(self,owner,hook):self.owner,self.hook=owner,hook
    def remove(self):self.owner.hooks.remove(self.hook)
class Module:
    training=False
    def __init__(self,params):self.params=params;self.hooks=[]
    def parameters(self,recurse=True):return iter(self.params)
    def register_forward_hook(self,hook):self.hooks.append(hook);return Handle(self,hook)
    def __call__(self):
        out=Tensor()
        for h in self.hooks:h(self,(),out)
        return out
class Conv(Module):
    in_channels=3;groups=1;kernel_size=(3,3)
class Linear(Module):in_features=3
conv,linear=Conv([p1]),Linear([p2])
class Model(Module):
    def __init__(self):super().__init__([p_scale])
    def named_modules(self):return iter([('',self),('conv',conv),('linear',linear)])
    def named_parameters(self,remove_duplicate=True):
        rows=[('logit_scale',p_scale),('conv.weight',p1),('linear.weight',p2)]
        return iter(rows if remove_duplicate else rows+[('shared_alias',p1)])
    def named_buffers(self,remove_duplicate=True):return iter([])
    def parameters(self,recurse=True):return iter([p_scale,p1,p2] if recurse else [p_scale])
model=Model();t.nn=types.SimpleNamespace(Conv2d=Conv,Linear=Linear)
def forward():conv();return linear()
trace=c.trace_parameters_and_partial_macs(runtime,model,forward,formal=True)
assert trace['observed_direct_owner_parameter_elements']==22
assert trace['excluded_whole_model_parameter_names']==['logit_scale']
assert trace['partial_MACs']['count_for_this_single_image_operation']==120
assert trace['partial_MACs']['total_FLOPs_available'] is False
assert not conv.hooks and not linear.hooks and not model.hooks
passed('Actual module-call mocks exclude logit_scale, deduplicate shared parameter objects and retain honest partial MAC label')
reject('Incomplete formal active parameter path rejected',lambda:c.trace_parameters_and_partial_macs(runtime,model,lambda:conv(),formal=True))
inventory=c.parameter_inventory(model,optimization_role='MOCK_ONLY')
assert inventory['whole_model_parameter_elements']==23 and inventory['whole_model_parameter_bytes']==92
passed('Whole-model parameter inventory counts shared alias once and retains requires_grad separately')

tree=ast.parse((HERE/'measurement_components.py').read_text(encoding='utf-8'))
functions={x.name:x for x in tree.body if isinstance(x,ast.FunctionDef)}
parity=functions['probability_parity']
assert any(isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr=='array_equal' for x in ast.walk(parity))
assert not any(isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr in ('allclose','isclose') for x in ast.walk(parity))
assert 'ProbabilityParityError' in ast.unparse(parity) and 'max_abs_difference' in ast.unparse(parity)
passed('Probability parity is exact, without adjustable tolerances, and preserves actual failure differences')
assert '_infer_probabilities' in ast.unparse(functions['_live_probabilities'])
assert '_validate_probability_array' in ast.unparse(functions['measure_raw_query'])
assert not any(isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr=='normalize' for x in ast.walk(functions['measure_raw_query']))
passed('Raw query delegates native CLIP probability generation and frozen FP32 validator; no extra probability renormalization')
assert 'inference_mode' in ast.unparse(functions['prepare_clip_prototypes'])
assert 'CONTENT_CANDIDATES' in ast.unparse(functions['prepare_clip_prototypes']) and 'STYLE_CANDIDATES' in ast.unparse(functions['prepare_clip_prototypes'])
passed('Fixed content/style prototypes are a separate one-time text computation')
for name in ('measure_formal_component','measure_clip_image_evidence','measure_raw_query'):
    text=ast.unparse(functions[name])
    assert "'manuscript_result': False" in text and "'full_t6_complete': False" in text
    assert '_require_resident_models' in text
passed('All component results refuse manuscript/full-T6 completion labels')
passed('Every public model measurement validates required resident object identity')
result=subprocess.run([sys.executable,'-I','-B',str(HERE/'runner.py'),'run'],capture_output=True,text=True,
    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)
assert result.returncode!=0 and 'Execution unavailable:' in result.stderr
passed('CLI run refuses before source/model loading, release or GPU work')
assert not any(x.split('.')[0] in BLOCKED for x in sys.modules)
passed('No scientific modules imported during the complete standard-library review')
report={'schema':'corrected-t6-component-stdlib-review.v1','status':'passed_component_checks_only',
    'check_count':len(checks),'checks':checks,'scientific_imports':[],
    'mock_policy':'Mock numbers existed only in process memory; no timing/memory/parameter/accuracy research result files created',
    'real_gpu_test_executed':False,'real_model_loaded':False,'acceptance_status':'provisional_pending_independent_review_and_future_real_execution'}
output=HERE/'STDLIB_REVIEW.json'
if output.exists():raise RuntimeError('Refuse overwriting a frozen review')
output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':report['status'],'check_count':len(checks),'scientific_imports':[]}))
