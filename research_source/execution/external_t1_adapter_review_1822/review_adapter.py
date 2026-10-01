"""Independent static/native-contract review; never imports scientific packages."""
import ast
import copy
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent
HERE=OUT.parent/'external_efficiency_preparation/external_t1_adapter_v1'
checks=[]
def read(p):return Path(p).read_text('utf-8-sig')
def js(p):return json.loads(read(p))
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for chunk in iter(lambda:f.read(4*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def check(n,ok,e=None):checks.append({'name':n,'passed':bool(ok),'evidence':e})
def tree(p):return ast.parse(read(p))
def fun(t,n):return next(x for x in t.body if isinstance(x,ast.FunctionDef) and x.name==n)
def literal(t,n):return ast.literal_eval(next(x.value for x in t.body if isinstance(x,ast.Assign) and any(isinstance(a,ast.Name) and a.id==n for a in x.targets)))
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def refuses(fn):
 try:fn()
 except (RuntimeError,KeyError,ValueError,FileNotFoundError):return True
 return False

check('adapter_source_manifest_exact_parent_pin',sha(HERE/'SOURCE_MANIFEST.json')=='932dde425f4cc53db1c6c5d3e0844adcfff90dbdf4343d18407bdd3f6257311b')
manifest=js(HERE/'SOURCE_MANIFEST.json')
records=[{'path':x['path'],'sha256':sha(x['path']),'bytes':Path(x['path']).stat().st_size,'matches':sha(x['path'])==x['sha256'] and Path(x['path']).stat().st_size==x['bytes']} for x in manifest['files']]
check('all173_sealed_source_files_match',len(records)==173 and all(x['matches'] for x in records),records)
trees={n:tree(HERE/n) for n in ['bindings.py','native_load.py','native_ops.py']}
for name,t in trees.items():compile(t,name,'exec')
check('all_adapter_modules_parse_compile',True)
b=load('bindings',HERE/'bindings.py');n=load('native_ops',HERE/'native_ops.py');loader=load('native_load',HERE/'native_load.py')
k=b.common()
check('actual_common_contract_is_pinned_v2',k.HERE==b.V2 and sha(b.V2/'SOURCE_MANIFEST.json')==b.V2_MANIFEST_SHA)
check('no_scientific_imports_after_adapter_imports',not any(x in sys.modules for x in ['torch','numpy','PIL','scipy','torchvision','transformers']))
rows=b.slots();qt=tree(b.EXT/'qdfl_official_evaluation.py');mt=tree(b.EXT/'mccg_official_evaluation.py');mx=tree(b.EXT/'run_transactions_t1_matrix.py')
check('seven_exact_actual_matrix_slots',len(rows)==7 and [x['seed'] for x in rows[:3]]==[1,2,3],rows)
check('actual_evaluation_batch_config_matches',b.BATCHES==literal(mx,'EVALUATION_BATCH_SIZE'))
check('QDFL_family_all_input_sizes_match',all(b.SIZES[x]==size for x,size in literal(qt,'EXPECTED_TEST_SIZE').items()))
recipe_node=next(x.value for x in tree(b.EXT/'mccg_adapter.py').body if isinstance(x,ast.Assign) and any(isinstance(a,ast.Name) and a.id=='PUBLISHED_RECIPE' for a in x.targets))
recipe_size=next(ast.literal_eval(v) for key,v in zip(recipe_node.keys,recipe_node.values) if ast.literal_eval(key)=='image_size')
check('MCCG_input_size_recipe_match',b.SIZES['mccg_convnext_tiny']==tuple(recipe_size))
check('ten_tasks_per_slot_no_external_street',len(b.EXPECTED_TASKS)==10 and b.EXPECTED_TASKS==literal(mx,'EXPECTED_EVALUATION_TASKS') and not any('street' in x for x in b.EXPECTED_TASKS))
for role in ['satellite_drone','street','query_uav','',None]:check('unknown_role_refused_'+str(role),refuses(lambda:b.role_kind(role)))
for row in rows:
 expected=b.RUNS/'fits'/row['run_id']/('checkpoints/last.ckpt' if row['framework']=='qdfl' else 'net_last.pth')
 check('final_checkpoint_path_'+row['run_id'],b.checkpoint_path(row)==expected)

envlock=js(b.EXT/'transactions_environment_lock.json');envchecks=[]
for name,e in envlock['environments'].items():
 site=Path(e['executable']).parent.parent/'Lib/site-packages'
 actual=[list(x) for x in sorted({(str(d.metadata.get('Name','')).strip().lower(),d.version) for d in importlib.metadata.distributions(path=[str(site)]) if str(d.metadata.get('Name','')).strip()})]
 envchecks.append({'name':name,'python':e['executable'],'python_sha256':sha(e['executable']),'distributions_count':len(actual),'exact_lock_match':actual==e['installed_distributions']['rows'],'key_versions':{x[0]:x[1] for x in actual if x[0] in ['numpy','pillow','timm','torch','torchvision','transformers']}})
check('both_native_environments_metadata_exact_current_disk',all(x['exact_lock_match'] for x in envchecks),envchecks)
check('both_native_environments_distinct_from_primary_baseline',all('lgm-baselines' not in x['python'] for x in envchecks))
for family,t in [('qdfl',qt),('mccg',mt)]:
 source=ast.unparse(fun(t,'load_model'))
 check(family+'_original_loader_is_strict_and_CPU', 'strict=True' in source and "map_location='cpu'" in source and 'weights_only=True' in source and 'mmap=True' in source)
 trans=ast.unparse(fun(t,'build_transform'))
 check(family+'_original_BICUBIC_ImageNet_transform',all(x in trans for x in ['BICUBIC','0.485','0.456','0.406','0.229','0.224','0.225']))
 source=ast.unparse(fun(t,'extract_'+family+'_descriptors'))
 check(family+'_original_extract_inference_and_full_order_guard','torch.inference_mode()' in source and 'expected_index != len(dataloader.dataset)' in source)
 check(family+'_native_load_calls_original_loader', ('model = official.load_model(gate, device)' if family=='qdfl' else "model = official.load_model(args.source_root, gate['checkpoint_path'], device)") in read(HERE/'native_load.py'))
qpost=ast.unparse(fun(qt,'qdfl_postprocess'))
check('QDFL_CPU_raw_mirror_math_preserved', "device='cpu', dtype=torch.float32" in qpost and 'value = value / norm.expand_as(value)' in qpost and 'value = value + mirrored_output.detach().to' in qpost)
mpost=ast.unparse(fun(mt,'mccg_postprocess'))
check('MCCG_sqrt_parts_math_preserved','norm = norm * math.sqrt(value.shape[-1])' in mpost)
check('native_descriptor_delegates_original_family_postprocess', 'context.official.qdfl_postprocess(original, mirrored)' in read(HERE/'native_ops.py') and 'context.official.mccg_postprocess(original + mirrored).cpu()' in read(HERE/'native_ops.py'))
source_roots=envlock['compatibility_revision']['source_manifests']
check('QDFL_medium_precision_is_real_source_side_effect',"torch.set_float32_matmul_precision('medium')" in read(Path(source_roots['qdfl']['source_root'])/'plModules/U1652_baseline.py'))
sharedclass=next(x for x in tree(Path(source_roots['mccg']['source_root'])/'models/model.py').body if isinstance(x,ast.ClassDef) and x.name=='two_view_net')
check('MCCG_actual_two_view_class_shares_only_model1','self.model_2' not in ast.unparse(sharedclass) and ast.unparse(sharedclass).count('self.model_1(')==2)

loadfn=fun(trees['native_load.py'],'load_native_slot')
imports=[x.lineno for x in ast.walk(loadfn) if isinstance(x,ast.Import) and any(a.name in ['torch','numpy'] for a in x.names)]
for guard in ['verify_binding','verify_current_environment','gpu_idle']:
 line=next(x.lineno for x in ast.walk(loadfn) if isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr==guard)
 check(guard+'_precedes_scientific_import',line<min(imports))
check('original_all7_fit_and_evaluation_validators_used',all(x in read(HERE/'native_load.py') for x in ['for registered in b.slots():','matrix.validate_existing_fit(registered, fit)','matrix.validate_existing_evaluation(registered, evaluation)']))
with patch.object(b,'source_manifest',return_value={}),patch.object(b,'slots',return_value=rows),patch.object(k,'read',return_value={'status':'incomplete_fixture_only'}),patch.object(b,'checkpoint_path') as cp:
 check('incomplete_whole_T1_refuses_before_checkpoint_resolution',refuses(lambda:b.bind_completed_slot(rows[0]['run_id'])) and not cp.called)

# Run actual native_descriptor control flow with tagged ordinary objects, not tensors.
class Tag:
 def __init__(self,name,events):self.name=name;self.events=events;self.requires_grad=False;self.ndim=2;self.shape=(1,2)
 def __add__(self,other):self.events.append(('sum',self.name,other.name));return Tag('sum',self.events)
 def cpu(self):self.events.append(('D2H',self.name));return self
 def numpy(self):self.events.append(('numpy',self.name));return self
class NPTag:
 float32='float32'
 def ascontiguousarray(self,x,dtype):x.dtype=dtype;return x
 def isfinite(self,x):return SimpleNamespace(all=lambda:True)
events_by_family={}
for family in ['qdfl','mccg']:
 for role in ['query_drone','query_satellite']:
  ev=[]
  class Model:
   def __call__(self,*images):
    image=next(x for x in images if x is not None);ev.append(('forward',image.name));out=Tag(image.name+'_out',ev)
    return out if len(images)==1 else (out,None) if images[0] is not None else (None,out)
  model=Model()
  namespace={'Any':Any,'DescriptorEvaluationError':RuntimeError}
  exec(compile(ast.Module(body=[fun(mt,'_view_output')],type_ignores=[]),'official-view-routing-only','exec'),namespace)
  def flip(x,dims):ev.append(('flip',dims));return Tag('mirror',ev)
  def qpost(a,c):ev.append(('official_qpost',a.name,c.name));return Tag('qpost',ev)
  def mpost(a):ev.append(('official_mpost',a.name));return Tag('mpost',ev)
  context=SimpleNamespace(runtime=SimpleNamespace(torch=SimpleNamespace(Tensor=Tag,flip=flip),numpy=NPTag()),family=family,model=model,official=SimpleNamespace(_view_output=namespace['_view_output'],qdfl_postprocess=qpost,mccg_postprocess=mpost))
  with patch.object(n,'require_native',return_value=None):n.native_descriptor(context,Tag('original',ev),role)
  check(family+'_'+role+'_actual_forward_and_flip_control_order',ev[:3]==[('forward','original'),('flip',(3,)),('forward','mirror')])
  check(family+'_'+role+'_native_postprocess_order',ev[3]==('official_qpost','original_out','mirror_out') if family=='qdfl' else ev[3:6]==[('sum','original_out','mirror_out'),('official_mpost','sum'),('D2H','mpost')])
  events_by_family[family+'/'+role]=ev

class Array:
 dtype='float32';shape=(1,2)
 def __init__(self,values):self.values=list(values)
 def __sub__(self,other):return Array([a-b for a,b in zip(self.values,other.values)])
 def __ne__(self,other):return Array([a!=b for a,b in zip(self.values,other.values)])
 def max(self):return max(self.values)
class TestError(RuntimeError):pass
fake_np=SimpleNamespace(array_equal=lambda a,b:a.values==b.values,abs=lambda a:Array([abs(x) for x in a.values]),count_nonzero=lambda a:sum(x!=0 for x in a.values))
ctx=SimpleNamespace(runtime=SimpleNamespace(numpy=fake_np),components=SimpleNamespace(MeasurementError=TestError))
check('descriptor_parity_exact_match_accepts',n.descriptor_parity(ctx,Array([1,2]),Array([1,2]),'fixture')['passed'])
failure=None
try:n.descriptor_parity(ctx,Array([1,2]),Array([1,3]),'fixture_mismatch_only')
except TestError as error:failure=error
check('descriptor_parity_real_mismatch_not_suppressed',failure is not None and failure.evidence['passed'] is False)
recoverable=any(hasattr(failure,x) for x in ['observed','expected','arrays','observed_array','expected_array','actual_arrays'])
check('failure_interface_exposes_actual_arrays_to_caller',recoverable,{'fixture_only':True,'exception_attributes':vars(failure),'observed_locally':[1,2],'expected_locally':[1,3],'caller_receives_arrays':recoverable})
ops=read(HERE/'native_ops.py')
check('CUDA_forward_and_wall_mixed_CPU_clocks_distinct',ops.count("clock='cuda_event'")==1 and ops.count("clock='synchronized_wall'")==2)
check('native_FP32_AMP_false_and_precision_guards_present',all(x in ops for x in ["t.is_autocast_enabled('cuda')","t.is_autocast_enabled('cpu')",'precision_state(context) == expected',"flags.pop('native_formal_autocast', None)","flags.pop('native_clip_autocast', None)"]))
check('full_view_original_extractor_fixed_batch_workers0',all(x in ops for x in ['batch_size=b.BATCHES[','num_workers=0','drop_last=False','extract_qdfl_descriptors','extract_mccg_descriptors']))
check('no_ranking_or_completed_T6_misclaim',all(x in ops for x in ["'ranking_measured': False","'full_gallery_metrics_recomputed_here': False","'full_t6_complete': False","'manuscript_result': False"]))
check('sample_success_returns_actual_descriptors', 'return result, observed, raw_descriptor' in ops)
check('no_scientific_imports_at_end',not any(x in sys.modules for x in ['torch','numpy','PIL','scipy','torchvision','transformers']))
report={'schema':'external-t1-adapter-independent-review.v1','created_utc':datetime.now(timezone.utc).isoformat(),'reviewer':'memory_failure_1544_review','source_manifest_sha256':sha(HERE/'SOURCE_MANIFEST.json'),'source_hashes':{p:sha(HERE/p) for p in trees},'checks':checks,'pass_count':sum(x['passed'] for x in checks),'check_count':len(checks),'mock_operation_traces':events_by_family,'findings':[{'id':'P2-PARITY-ARRAY-LOSS','scope':'failure evidence interface; not a finding of incorrect model output','file':str(HERE/'native_ops.py'),'function':'descriptor_parity / measure_sample','summary':'On mismatch, only shape/dtype/difference counts escape; actual arrays stay in unwound locals before measure_sample returns, preventing the stated caller persistence of both failed arrays. Standard-library fixture reproduced.'}],'normal_success_path_scientific_blockers_found':[],'not_executed':['real completed binding','official scientific validators','model loading or weights','real tensor/NumPy/Pillow/science import','GPU/timing','active queue/release/control changes'],'writes':'independent review directory only','review_script_sha256':sha(__file__)}
(OUT/'INDEPENDENT_REVIEW.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':report['pass_count'],'total':report['check_count'],'failed':[x['name'] for x in checks if not x['passed']],'hashes':report['source_hashes'],'report_sha256':sha(OUT/'INDEPENDENT_REVIEW.json')},indent=2))
