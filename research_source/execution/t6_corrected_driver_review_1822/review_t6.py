"""Independent read/hash/AST and standard-library-only fixtures; no launch APIs."""
import ast
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import struct
import sys
from typing import Sequence, Iterable
from unittest.mock import patch
import zipfile

sys.dont_write_bytecode = True
OUT=Path(__file__).resolve().parent
EX=OUT.parent
HERE=EX/'external_efficiency_preparation/corrected_driver_v1'
P=Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724/lgm_game_pytorch')
checks=[]
def read(p):return Path(p).read_text('utf-8-sig')
def js(p):return json.loads(read(p))
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for chunk in iter(lambda:f.read(4*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def check(name,passed,evidence=None):checks.append({'name':name,'passed':bool(passed),'evidence':evidence})
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod);return mod
def node(tree,name):return next(x for x in ast.walk(tree) if isinstance(x,(ast.FunctionDef,ast.ClassDef)) and x.name==name)
def dump(n):return ast.dump(n,include_attributes=False)
def refused(fn):
 try:fn()
 except (ValueError,RuntimeError,FileExistsError,KeyError):return True
 return False

manifest=js(HERE/'SOURCE_MANIFEST.json')
hashrows=[]
for item in manifest['files']:
 p=Path(item['path']);actual=sha(p);hashrows.append({'path':str(p),'expected_sha256':item['sha256'],'actual_sha256':actual,'bytes':p.stat().st_size,'match':actual==item['sha256'] and p.stat().st_size==item['bytes']})
check('all_manifest_file_hashes_match',all(x['match'] for x in hashrows),hashrows)
trees={n:ast.parse(read(HERE/n)) for n in ['contract.py','driver.py','science.py']}
for name,tree in trees.items():compile(tree,str(HERE/name),'exec')
check('reviewed_modules_parse_and_compile_without_execution',True)
k=load('contract',HERE/'contract.py')
d=load('review_t6_driver',HERE/'driver.py')
s=load('review_t6_science',HERE/'science.py')
check('module_imports_do_not_load_science',not any(x in sys.modules for x in ['torch','numpy','PIL','scipy','transformers','torchvision']))

core_tree=ast.parse(read(P/'lgm_game_pytorch/formal_retrieval.py'))
agg_tree=ast.parse(read(P/'experiments/aggregate_frozen_formal_results.py'))
helper_tree=ast.parse(read(P/'experiments/run_transactions_formal_efficiency.py'))
pure={'dataclass':dataclass,'Path':Path,'Sequence':Sequence,'Iterable':Iterable,'defaultdict':defaultdict}
for name in ['EvidenceRecord','RetrievalTask','_group_by_label','_assert_task','build_official_evaluation_tasks']:
 n=node(core_tree,name);exec(compile(ast.Module(body=[n],type_ignores=[]),'extracted-official-pure-'+name,'exec'),pure)
pure['SUES_ALTITUDES']=('150','200','250','300')
split=P/'manifests/sues200_official_train_ids.yaml'
trainids=re.findall(r'^\s*-\s*["\']?([0-9]{4})["\']?\s*$',read(split),flags=re.MULTILINE)
check('official_SUES_split_has_120_unique_ids',len(trainids)==len(set(trainids))==120)
tasks_by_dataset={};cache_rows=[]
for dataset in ['university1652','sues200']:
 cache=P/'evidence_cache'/(dataset+'_clip_image_evidence.npz');records=[]
 with zipfile.ZipFile(cache) as z,z.open('paths.npy') as f:
  magic=f.read(8);hlen=struct.unpack('<H' if magic[6]==1 else '<I',f.read(2 if magic[6]==1 else 4))[0];h=ast.literal_eval(f.read(hlen).decode('latin1'))
  assert h['descr'].startswith('<U') and len(h['shape'])==1 and not h['fortran_order']
  width=int(h['descr'][2:])*4
  for index in range(h['shape'][0]):
   path=f.read(width).decode('utf-32le').rstrip('\0');parts=path.split('/');low=[v.lower() for v in parts]
   if dataset=='university1652':
    # Mirror source path role classification; no pixel read/file import.
    roles={'drone':('train','drone','train_drone'),'satellite':('train','satellite','train_satellite'),'street':('train','street','train_street')}
    roles.update({role:('test',role.split('_',1)[1],role) for role in ['query_drone','gallery_drone','query_satellite','gallery_satellite','query_street','gallery_street']})
    found=[(i,roles[v]) for i,v in enumerate(low) if v in roles]
    if not found:continue
    i,(partition,view,role)=found[-1];label=parts[i+1];alt=''
   else:
    partition='protocol_derived'
    if 'drone_view_512' in low:
     i=len(low)-1-low[::-1].index('drone_view_512');label=parts[i+1];alt=re.sub('[^0-9]','',parts[i+2]);view=role='drone'
    elif 'satellite-view' in low:
     i=len(low)-1-low[::-1].index('satellite-view');label=parts[i+1];view=role='satellite';alt=''
    else:continue
   records.append(pure['EvidenceRecord'](index,path,Path(k.DATA_ROOTS[dataset])/Path(*parts),label,partition,view,role,alt))
 tasks=pure['build_official_evaluation_tasks'](records,dataset,trainids)
 tasks_by_dataset[dataset]=tasks
 cache_rows.append({'dataset':dataset,'archive_sha256':sha(cache),'path_array_header':h,'recognized_records':len(records),'task_scale':[{'name':t.name,'queries':len(t.query),'gallery':len(t.gallery),'query_ids':len({r.label for r in t.query}),'gallery_ids':len({r.label for r in t.gallery})} for t in tasks]})
 del records
check('actual_cache_paths_plus_original_task_builder_3_and_8',len(tasks_by_dataset['university1652'])==3 and len(tasks_by_dataset['sues200'])==8,cache_rows)
check('four_primary_cases_imply_22_official_task_checks',len(k.CASES)==4 and sum(len(tasks_by_dataset[data]) for data,var in k.CASES)==22)
check('SUES_full_gallery_retains_all200_IDs',all(len({r.label for r in t.gallery})==200 for t in tasks_by_dataset['sues200']))
check('task_counts_not_invented_26', 'total_tasks == 22' in read(HERE/'driver.py'))
metrics=[x.value for x in ast.walk(node(helper_tree,'_verify_full_gallery_metrics')) if isinstance(x,ast.Constant) and isinstance(x.value,str) and x.value in ['r_at_1','r_at_5','r_at_10','r_at_20','official_trapezoid_mAP','MRR']]
check('actual_bound_helper_verifies_all_six_metrics',len(metrics)==6,metrics)
check('uses_original_all_query_full_gallery_metric_path', 'core.rank_task(task, encoded, chunk_size=256)' in read(HERE/'science.py') and 'helpers._verify_full_gallery_metrics(observed, reported, task.name)' in read(HERE/'science.py'))
check('workers0_batch128_contract', "plan['descriptor_batch_size'] == 128 and plan['descriptor_workers'] == 0" in read(HERE/'contract.py'))
check('original_encode_records_inference_mode', any(ast.unparse(x)=='torch.inference_mode()' for x in node(core_tree,'encode_records').decorator_list))
check('original_encoder_uses_amp', 'with amp_context(device, amp_enabled)' in ast.unparse(node(core_tree,'encode_records')))
check('cached_encoding_is_not_claimed_as_raw_online', "'online_accuracy_scope': 'one first query per official task against cached gallery'" in read(HERE/'science.py'))
check('CLIP_expected_slow_image_fast_tokenizer_offline',all(x in read(HERE/'science.py') for x in ['use_safetensors=False','local_files_only=True',"'CLIPImageProcessor'","'CLIPTokenizerFast'", "transformers.__version__ == '4.57.6'"]))
check('full_real_online_path_calls_live_generator', 'components._live_probabilities' in ast.unparse(node(trees['science.py'],'raw_descriptor')))
check('ranking_explicit_matrix_and_stable_FP32',all(x in ast.unparse(node(trees['science.py'],'ranking_timing')) for x in ['dtype == t.float32','stable=True','query_gpu @ gallery_gpu.T','range(5)','range(20)']))
check('four_complete_cases_not_full_T6',"'full_t6_complete': False" in read(HERE/'driver.py') and "'manuscript_result': False" in read(HERE/'driver.py'))

fixtures=OUT/'stdlib_fixtures';fixtures.mkdir(exist_ok=True)
release_plan=fixtures/'mock_plan.json'
if not release_plan.exists():k.write_new(release_plan,{'fixture_only':True})
for name,payload in [('inactive',{'allow_run':False,'plan':k.record(release_plan)}),('wrong',{'allow_run':True,'plan':{'sha256':'0'*64}}),('valid',{'allow_run':True,'plan':k.record(release_plan)})]:
 p=fixtures/(name+'.json')
 if not p.exists():k.write_new(p,payload)
 check('release_'+name,refused(lambda:d.verify_release(p,release_plan)) if name!='valid' else d.verify_release(p,release_plan)['allow_run'] is True)
check('new_output_traversal_refuses',refused(lambda:k.scoped_new(fixtures,'../escape')))
check('new_output_existing_refuses',refused(lambda:k.scoped_new(OUT,'stdlib_fixtures')))
pidrows=[{'ProcessId':100,'ParentProcessId':200,'Name':'python.exe','CreatedUtc':'2026-09-14T10:00:00+00:00','ExecutablePath':'fixture_driver'}, {'ProcessId':200,'ParentProcessId':1,'Name':'python.exe','CreatedUtc':'2026-09-14T10:30:00+00:00','ExecutablePath':'fixture_unrelated'}]
with patch.object(k.os,'getpid',return_value=100):
 allowed=k.self_and_verified_ancestors(pidrows)
 wrongly_admitted=not refused(lambda:k.no_foreign_python(pidrows,allowed))
check('PID_reused_parent_is_not_allowed',not wrongly_admitted,{'fixture_only':True,'processes':pidrows,'actual_allowlist':sorted(allowed),'foreign_process_was_admitted':wrongly_admitted})
check('live_same_PID_slow_spawn_refuses',not k.exited(200,'2026-09-14T08:00:00+00:00',pidrows))
check('PID_reuse_after_recorded_finish_accepts',k.exited(200,'2026-09-14T08:00:00+00:00',pidrows,'2026-09-14T09:00:00+00:00'))
check('same_PID_before_recorded_finish_refuses',not k.exited(100,'2026-09-14T08:00:00+00:00',pidrows,'2026-09-14T10:00:10+00:00'))
check('unknown_Python_refuses',refused(lambda:k.no_foreign_python(pidrows,{100})))
# Demonstrate the exact lifecycle issue, not a claim that a scientific worker ran.
log=fixtures/'buffered_stdout.log'
with log.open('wb',buffering=8192) as f:
 f.write(b'fixture output buffered until worker exit\n')
 early=k.record(log)
 f.flush()
late=k.record(log)
check('worker_artifact_enumeration_excludes_open_parent_logs',not ('outputs = [k.record(p) for p in sorted(output.rglob' in read(HERE/'science.py')),{'fixture_only':True,'before_flush':early,'after_flush':late,'record_changes':early!=late,'open_logs_in_driver':"(case_dir / 'stdout.log').open('xb')" in read(HERE/'driver.py')})

physical=15957440*1024
resource_rows=[]
for data,var in k.CASES:
 scales={t.name:{'queries':len(t.query),'gallery':len(t.gallery)} for t in tasks_by_dataset[data]}
 ck=P/'runs/formal_main'/data/var/'seed_1/best.pt'
 actual_size=ck.stat().st_size if ck.exists() else None
 # Use 0 only to derive the exactly known part, never as a guessed checkpoint size.
 fake_plan={'cases':[{'evaluation_dir':'mock_binding_only','variant':var,'checkpoint':{'bytes':actual_size or 0}}], 'clip':{'files':[{'path':'pytorch_model.bin','bytes':605247071}]}}
 with patch.object(k,'read',return_value={'results':scales}):budget=k.resource_budget(fake_plan,0)
 known=budget['host_required_available_bytes']-(2*actual_size if actual_size else 0)
 resource_rows.append({'dataset':data,'variant':var,'actual_checkpoint_bytes_if_present':actual_size,'known_host_bytes_excluding_checkpoint':known,'host_required_formula':'known_host_bytes + 2 * actual checkpoint bytes','actual_host_required_bytes_if_checkpoint_present':budget['host_required_available_bytes'] if actual_size else None,'max_checkpoint_bytes_feasible_on_observed_total_physical':(physical-known)//2,'total_physical_from_readonly_CIM':physical,'largest_full_ranking_elements':max(x['queries']*x['gallery'] for x in scales.values()),'GPU_rank_admission_bytes_excluding_resident_descriptors_models':28*max(x['queries']*x['gallery'] for x in scales.values())+256*1024**2,'allocation_is_unprofiled_estimate':True})
check('source_scales_gates_not_intrinsically_impossible_on_host',all(r['max_checkpoint_bytes_feasible_on_observed_total_physical']>1024**3 for r in resource_rows),resource_rows)
check('no_scientific_imports_at_review_end',not any(x in sys.modules for x in ['torch','numpy','PIL','scipy','transformers','torchvision']))
report={'schema':'t6-independent-driver-review.v1','finished_utc':datetime.now(timezone.utc).isoformat(),'reviewer':'memory_failure_1544_review','source_manifest_sha256':sha(HERE/'SOURCE_MANIFEST.json'),'source_files':{n:sha(HERE/n) for n in trees},'review_script_sha256':sha(__file__),'checks':checks,'pass_count':sum(x['passed'] for x in checks),'check_count':len(checks),'findings':[{'id':'P1-ANCESTRY-PID-REUSE','status':'unresolved_in_reviewed_source','file':str(HERE/'contract.py'),'function':'self_and_verified_ancestors','summary':'Raw parent PID chain admits a newer unrelated Python process as ancestor; standard-library fixture reproduced.'},{'id':'P2-OPEN-LOG-ARTIFACT-HASH','status':'unresolved_in_reviewed_source','file':str(HERE/'science.py'),'function':'_run_case final output enumeration','summary':'Worker artifact list includes parent-open stdout/stderr files before exit/flush; standard-library buffered-log fixture demonstrates hash invalidation. Occurrence in an actual scientific worker has not been tested.'}],'execution_boundary':{'author_sources_changed':False,'plans_status_releases_changed':False,'scientific_imports':False,'models_or_real_tensors_loaded':False,'GPU_or_training':False,'launch_functions_called':False,'PowerPoint':False,'filesystem_writes':'only this independent review directory','real_evidence_read':'source/cache path strings/metadata/file hashes; lightweight host CIM observed separately'},'limitations':['No true driver prepare/run/worker executed.','No complete original four evaluations currently available at fixed paths.','Cached six-metric reproduction, B=1 CLIP parity, CUDA kernels, allocator headroom and timing remain unmeasured.','Host formula plausibility does not establish actual peak sufficiency.']}
(OUT/'INDEPENDENT_REVIEW.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':report['pass_count'],'total':report['check_count'],'failed':[x['name'] for x in checks if not x['passed']],'source_files':report['source_files'],'report_sha256':sha(OUT/'INDEPENDENT_REVIEW.json'),'resources':resource_rows},ensure_ascii=True,indent=2))
