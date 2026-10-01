"""Focused T1 parity exception recheck; stdlib fake arrays, no scientific imports."""
import ast
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

OUT=Path(__file__).resolve().parent
BASE=OUT.parent/'external_efficiency_preparation'
OLD=BASE/'external_t1_adapter_v1';NEW=BASE/'external_t1_adapter_v2'
checks=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return Path(p).read_text('utf-8-sig')
def check(n,ok,e=None):checks.append({'name':n,'passed':bool(ok),'evidence':e})
def dump(n):return ast.dump(n,include_attributes=False)
for name in ['bindings.py','native_load.py']:
 check(name+'_byte_identical',sha(OLD/name)==sha(NEW/name))
trees=[ast.parse(read(p/'native_ops.py')) for p in [OLD,NEW]]
for t in trees:compile(t,'native_ops-no-execution','exec')
old,new=trees
class RemoveAddedCopies(ast.NodeTransformer):
 def visit_Assign(self,n):
  if any(isinstance(t,ast.Attribute) and isinstance(t.value,ast.Name) and t.value.id=='error' and t.attr in ['actual_descriptor_array','expected_descriptor_array'] for t in n.targets):return None
  return self.generic_visit(n)
check('entire_native_ops_AST_identical_except_two_exception_copy_fields',dump(old)==dump(RemoveAddedCopies().visit(copy.deepcopy(new))))
fn=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='descriptor_parity')
namespace={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'actual-v2-parity-function-only','exec'),namespace)
parity=namespace['descriptor_parity']
class Array:
 def __init__(self,values,shape=(1,2),dtype='float32'):self.values=list(values);self.shape=shape;self.dtype=dtype;self.copy_calls=0
 def __sub__(self,o):return Array([a-b for a,b in zip(self.values,o.values)],self.shape,self.dtype)
 def __ne__(self,o):return Array([a!=b for a,b in zip(self.values,o.values)],self.shape,'bool')
 def max(self):return max(self.values)
 def copy(self):self.copy_calls+=1;return Array(copy.deepcopy(self.values),tuple(self.shape),self.dtype)
class Error(RuntimeError):pass
np=SimpleNamespace(array_equal=lambda a,b:a.values==b.values,abs=lambda a:Array([abs(x) for x in a.values],a.shape,a.dtype),count_nonzero=lambda a:sum(x!=0 for x in a.values))
ctx=SimpleNamespace(runtime=SimpleNamespace(numpy=np),components=SimpleNamespace(MeasurementError=Error))
def capture(a,b):
 try:parity(ctx,a,b,'stdlib_fixture_only')
 except Error as e:return e
 raise AssertionError('Mismatch was not rejected')
a,b=Array([1,2]),Array([1,3]);e=capture(a,b)
check('value_mismatch_remains_rejected',e.evidence['passed'] is False and e.evidence['different_element_count']==1)
check('both_actual_array_fields_present',e.actual_descriptor_array.values==[1,2] and e.expected_descriptor_array.values==[1,3])
check('copies_are_distinct_objects',e.actual_descriptor_array is not a and e.expected_descriptor_array is not b and a.copy_calls==b.copy_calls==1)
a.values[0]=99;b.values[1]=88
check('input_mutation_cannot_change_failure_copies',e.actual_descriptor_array.values==[1,2] and e.expected_descriptor_array.values==[1,3])
e.actual_descriptor_array.values[1]=77;e.expected_descriptor_array.values[0]=66
check('failure_copy_mutation_cannot_change_inputs',a.values==[99,2] and b.values==[1,88])
serialized=json.dumps(e.evidence,allow_nan=False,sort_keys=True)
check('JSON_evidence_remains_serializable_and_array_free',json.loads(serialized)==e.evidence and all(not isinstance(v,Array) for v in e.evidence.values()))
shape_error=capture(Array([1,2]),Array([1,2,3],shape=(1,3)))
check('shape_mismatch_preserves_both_original_shapes',shape_error.actual_descriptor_array.shape==(1,2) and shape_error.expected_descriptor_array.shape==(1,3))
dtype_error=capture(Array([1,2],dtype='float32'),Array([1,2],dtype='float64'))
check('dtype_mismatch_preserves_original_dtypes',dtype_error.actual_descriptor_array.dtype=='float32' and dtype_error.expected_descriptor_array.dtype=='float64')
success=parity(ctx,Array([1,2]),Array([1,2]),'success_fixture_only')
check('exact_match_success_unchanged',success['passed'] is True and json.loads(json.dumps(success))==success)
v1=json.loads(read(OLD/'SOURCE_MANIFEST.json'))
check('all173_v1_sealed_files_unchanged',len(v1['files'])==173 and all(sha(x['path'])==x['sha256'] and Path(x['path']).stat().st_size==x['bytes'] for x in v1['files']))
check('no_scientific_imports',not any(n in sys.modules for n in ['torch','numpy','PIL','scipy','torchvision','transformers']))
report={'schema':'external-t1-adapter-v2-independent-recheck.v1','created_utc':datetime.now(timezone.utc).isoformat(),'reviewer':'memory_failure_1544_review','source_hashes':{n:sha(NEW/n) for n in ['bindings.py','native_load.py','native_ops.py']},'checks':checks,'check_count':len(checks),'pass_count':sum(x['passed'] for x in checks),'prior_finding':'P2-PARITY-ARRAY-LOSS fixed; standard-library actual-function replay passed','scientific_math_changed':False,'source_manifest_exists_at_code_review':(NEW/'SOURCE_MANIFEST.json').exists(),'review_script_sha256':sha(__file__),'execution_scope':'AST/hash/extracted parity function with fake ordinary arrays only; no scientific import/model/GPU/queue/output release; writes only independent review directory'}
(OUT/'V2_RECHECK.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':report['pass_count'],'total':report['check_count'],'failed':[x['name'] for x in checks if not x['passed']],'source_hashes':report['source_hashes'],'manifest_exists':report['source_manifest_exists_at_code_review'],'report_sha256':sha(OUT/'V2_RECHECK.json')},indent=2))
