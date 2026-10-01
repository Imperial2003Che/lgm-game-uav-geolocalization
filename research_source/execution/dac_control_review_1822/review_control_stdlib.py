"""Independent DAC control audit. Only stdlib and clearly labelled mock objects.

All writes stay in this audit directory. Never invoke the preparation test main,
real scientific imports, nvidia-smi, process probes, model, images, or training.
"""
import ast
import builtins
from contextlib import nullcontext
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.abc
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

OUT = Path(__file__).resolve().parent
PREP = OUT.parent / 'dac_training_preparation_v1'
BLOCKED = {'torch','torchvision','numpy','PIL','cv2','timm','albumentations','scipy','sklearn','transformers','tensorboard'}
ATTEMPTS = []
sys.dont_write_bytecode = True
class NoScience(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in BLOCKED:
            ATTEMPTS.append(fullname)
            raise RuntimeError('Real scientific import prohibited: ' + fullname)
sys.meta_path.insert(0, NoScience())
assert not BLOCKED.intersection(sys.modules)
sys.path.insert(0, str(PREP))
import common_runtime as common
import dac_train_runtime as runtime
import input_contract as inputs
import run_dac_training as launch
import gate_helpers as gate
import validate_preparation_cpu as original_tests

RESULTS = []
FIX = OUT / 'fixtures'
FIX.mkdir(exist_ok=True)
def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
def expect(condition, message='assertion failed'):
    if not condition: raise AssertionError(message)
def rejects(fn):
    try: fn()
    except (RuntimeError,ValueError,KeyError,TypeError,FileExistsError): return
    raise AssertionError('Expected rejection did not occur')
def check(name, fn, kind='positive_control'):
    try:
        detail = fn()
        RESULTS.append({'name':name,'passed':True,'kind':kind,'detail':detail})
    except BaseException as error:
        RESULTS.append({'name':name,'passed':False,'kind':kind,'error':repr(error)})
def before_hashes():
    return {p.relative_to(PREP).as_posix():common.sha_file(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
INITIAL = before_hashes()

def seals():
    seal = json.loads((PREP/'PREPARATION_MANIFEST.json').read_text(encoding='utf-8'))
    for row in seal['files']:
        p=(PREP/row['path']).resolve()
        expect(p.is_relative_to(PREP) and p.stat().st_size==row['bytes'] and common.sha_file(p)==row['sha256'])
    actual=launch.preparation_code_manifest()
    expect(actual['preparation_manifest_sha256']==common.sha_file(PREP/'PREPARATION_MANIFEST.json'))
    expect(len(runtime.verify_scientific_source()['files'])==19)
    expect(len(json.loads((PREP/'SOURCE_PIN.json').read_text())['files'])==36)
    return {'sealed_files':len(seal['files']),'official_files':36,'private_files':19}
check('all sealed payload/source hashes match',seals)
check('source Python AST parses without scientific imports',lambda:[ast.parse(p.read_text(encoding='utf-8')) and str(p.relative_to(PREP)) for p in PREP.rglob('*.py')])
check('registered input-reference manifest SHA matches',lambda:expect(inputs.verify_reference_files(False)['data_manifest_sha256']==common.sha_file(inputs.references()['data_manifest_path'])))

def cpu_case(name, mutation=None, accepted=True):
    proof={'schema':'dac-real-cpu-compatibility.v1','status':'passed','method':'DAC',
        'model_state_count':402,'pretrained_strict_tensor_count':344,
        'real_pair_original_transforms_passed':True,'cuda_initialized':False,
        'author_trained_weights_loaded':False,'all_model_floating_state_finite':True,
        'all_pair_floating_values_finite':True,'source_files_sha256':launch.cpu_source_bindings(),
        'environment':{'fixture':'stdlib only; no scientific environment execution'},
        'fixture_only':True,'real_model_executed':False,'real_images_loaded':False}
    plan={'environment':deepcopy(proof['environment'])}
    if mutation: mutation(proof)
    path=FIX/('cpu_'+name+'.json'); write(path,proof)
    plan['cpu_compatibility_proof']={'path':str(path),'sha256':common.sha_file(path)}
    if accepted:
        launch.validate_cpu_proof(plan)
        return {'accepted':True,'fixture_only':True,'has_runtime_origins':False,'has_raw_pair_proof':False}
    rejects(lambda:launch.validate_cpu_proof(plan))
check('explicit fixture-only CPU proof without raw execution evidence is accepted',lambda:cpu_case('fixture'), 'gap_reproduced')
check('stale CPU source binding rejected',lambda:cpu_case('stale',lambda p:p['source_files_sha256'].update({'dac_train_runtime.py':'stale'}),False))
check('CPU evidence declaring CUDA used rejected',lambda:cpu_case('cuda',lambda p:p.update(cuda_initialized=True),False))
check('CPU evidence declaring nonfinite pair rejected',lambda:cpu_case('pair',lambda p:p.update(all_pair_floating_values_finite=False),False))

def profile_case(name, mutation=None, accepted=True):
    d=FIX/('profile_'+name);d.mkdir(exist_ok=True)
    plan,path,report=original_tests.profile_fixture(d)
    if mutation: mutation(d,report)
    write(path,report)
    if accepted:
        launch.validate_profile(plan,path)
        return {'accepted':True,'fixture_only':report['fixture_only']}
    rejects(lambda:launch.validate_profile(plan,path))
check('explicit fixture-only native profile is accepted',lambda:profile_case('fixture'),'gap_reproduced')
check('zero actual profile AdamW updates rejected',lambda:profile_case('zero',lambda d,r:r.update(actual_adamw_steps=0),False))
check('profile over 32 attempts rejected',lambda:profile_case('over32',lambda d,r:r.update(completed_optimizer_amp_steps=33),False))
check('profile wrong 395 state rejected',lambda:profile_case('wrong_model',lambda d,r:r.update(model_state_count=395),False))
check('profile OOM rejected',lambda:profile_case('oom',lambda d,r:r.update(oom=True),False))
check('profile trace changed without matching hash rejected',lambda:profile_case('tampered',lambda d,r:(d/'batch_progress.jsonl').write_text('{}\n'),False))
check('NaN memory summary is accepted',lambda:profile_case('nan_memory',lambda d,r:r.update(peak_allocated_bytes=float('nan'),peak_reserved_bytes=float('nan'))),'gap_reproduced')
def infinite_memory(d,r):
    path=d/'resource_batches.jsonl'
    rows=[json.loads(x) for x in path.read_text().splitlines()]
    for row in rows:row.update(peak_allocated_bytes=float('inf'),peak_reserved_bytes=float('inf'))
    path.write_text(''.join(json.dumps(row)+'\n' for row in rows))
    r.update(peak_allocated_bytes=float('inf'),peak_reserved_bytes=float('inf'))
    r['evidence_sha256']['resource_batches.jsonl']=common.sha_file(path)
check('infinite per-batch memory and summary accepted',lambda:profile_case('infinite_memory',infinite_memory),'gap_reproduced')
check('memory summary smaller than its measured trace accepted',lambda:profile_case('mismatch_memory',lambda d,r:r.update(peak_allocated_bytes=1,peak_reserved_bytes=2)),'gap_reproduced')

def gate_case(name, mutation=None, accepted=True, gpu=''):
    start='2026-09-14T00:00:00+00:00'
    job=lambda ident:{'id':ident,'status':'completed','exit_code':0,'pid':101,'started_utc':start}
    states={
        'status.json':{'status':'completed','stage':'all','controller_pid':101,'started_utc':start,'commands':[job('primary_fit')]},
        'pipeline_status.json':{'status':'ready_for_extension_preparation','supervisor_pid':102,'supervisor_started_utc':start,'jobs':[job(x) for x in ['formal_aggregate','formal_figures','cross_dataset_transfer','robustness','robustness_aggregate','query_analysis','formal_efficiency_component']]},
        'extension_plan.json':{'jobs':[job('ext1')]},'latest_baseline_plan.json':{'jobs':[job('DAC-author')]}}
    for state,status,plan in [('extension_status.json','registered_extensions_finished_review_pending','extension_plan.json'),('latest_baseline_status.json','latest_baselines_finished_review_pending','latest_baseline_plan.json')]:
        states[state]={'status':status,'plan_sha256':'fixture-'+plan,'supervisor_pid':103,'supervisor_started_utc':start,'jobs':deepcopy(states[plan]['jobs'])}
    release={'schema':'dac-university-training-release.v1','allow_cuda':True,'training_plan_sha256':'fixture-plan','preceding_plan_sha256':{n:'fixture-'+n for n in ['extension_plan.json','latest_baseline_plan.json']}}
    if mutation:mutation(states,release)
    def read_mock(p):return deepcopy(release if Path(p).name=='fixture-release' else states[Path(p).name])
    def hash_mock(p):return 'fixture-plan' if Path(p).name=='fixture-plan' else 'fixture-'+Path(p).name
    with patch.object(launch,'read',read_mock),patch.object(launch,'sha_file',hash_mock),patch.object(launch,'alive',return_value=name=='live_pid'),patch.object(launch.subprocess,'run',return_value=SimpleNamespace(stdout=gpu)):
        fn=lambda:launch.serial_release_gate(Path('fixture-plan'),Path('fixture-release'))
        if accepted:return fn()
        rejects(fn)
check('valid prerequisite mock accepted',lambda:gate_case('valid'))
check('live recorded owner rejected',lambda:gate_case('live_pid',accepted=False))
check('missing owner creation time rejected',lambda:gate_case('no_start',lambda s,r:s['status.json'].pop('started_utc'),False))
check('failed primary header rejected',lambda:gate_case('failed_header',lambda s,r:s['status.json'].update(status='failed'),False))
check('nonzero extension job exit rejected',lambda:gate_case('extension_exit',lambda s,r:s['extension_status.json']['jobs'][0].update(exit_code=1),False))
check('stale latest plan hash rejected',lambda:gate_case('stale_plan',lambda s,r:s['latest_baseline_status.json'].update(plan_sha256='stale'),False))
check('python GPU process rejected',lambda:gate_case('python_gpu',accepted=False,gpu='123, python.exe'))
check('failed primary nested command accepted under completed header',lambda:gate_case('failed_primary_child',lambda s,r:s['status.json']['commands'][0].update(status='failed',exit_code=1)),'gap_reproduced')
check('live non-Python GPU compute application accepted',lambda:gate_case('native_gpu',gpu='123, train_native.exe'),'gap_reproduced')

def current_prerequisites():
    return {name:json.loads((OUT.parent/name).read_text(encoding='utf-8')).get('status') for name in ['status.json','pipeline_status.json','extension_status.json','latest_baseline_status.json']}
check('real predecessor status read-only snapshot',current_prerequisites,'read_only_observation')

def final_snapshot_mock():
    d=FIX/'final_checkpoint_mutation';d.mkdir(exist_ok=True)
    plan_path=d/'external_plan.json';profile_path=d/'external_profile.json'
    write(plan_path,{'seed':1,'frozen':'before admission'});write(profile_path,{'frozen':'before admission'})
    admitted={'plan':common.sha_file(plan_path),'profile':common.sha_file(profile_path)}
    run=original_tests.make_run(d)
    run.plan_path=plan_path;run.profile_path=profile_path
    run.epoch=1;run.expected_batches=3;run.actual_optimizer_steps=2;run.amp_skips=1
    run.representative_name='mock stem';run.representative_parameter=object();run.initial_parameter_sha256='initial-mock-digest'
    run.scaler=SimpleNamespace(state_dict=lambda:{'scale':1024})
    fake_state=original_tests.fake_state()
    for item in fake_state.values():item.is_floating_point=lambda:False
    state={'state':{0:{'step':2,'exp_avg':True,'exp_avg_sq':True}},'param_groups':[{'lr':0.001}]}
    for n in ['code_manifest.json','data_manifest.json','environment_manifest.json','runtime_environment.json','serial_release_gate.json']:
        write(d/n,{'fixture_only':True})
    write(plan_path,{'seed':3,'frozen':'changed after admission'})
    write(profile_path,{'frozen':'changed after admission'})
    saved={}
    fake_torch=ModuleType('torch');fake_torch.__mock_only__=True
    fake_torch.isfinite=lambda v:SimpleNamespace(all=lambda:SimpleNamespace(item=lambda:bool(v)))
    fake_torch.get_rng_state=lambda:b'fake_cpu_rng'
    fake_torch.cuda=SimpleNamespace(get_rng_state_all=lambda:[])
    def fake_save(content,path):
        saved[Path(path).name]=content
        Path(path).write_bytes(b'EXPLICIT STDLIB MOCK; NOT A CHECKPOINT')
    fake_torch.save=fake_save
    fake_numpy=ModuleType('numpy');fake_numpy.__mock_only__=True
    fake_numpy.random=SimpleNamespace(get_state=lambda:('mock',SimpleNamespace(tolist=lambda:[]),0,0,0.0))
    ns={'model':SimpleNamespace(state_dict=lambda:fake_state),'optimizer':SimpleNamespace(state_dict=lambda:state),
        'scheduler':SimpleNamespace(state_dict=lambda:{'last_epoch':3}),'scaler':run.scaler,
        'train_dataloader':SimpleNamespace(completed_batches=3,dataset=SimpleNamespace(samples=[(1,'mock')],pairs=[(1,'mock')],shuffle_batch_size=24)),
        'train_steps':1578,'warmup_steps':157.8,'train_loss':0.5,'config':SimpleNamespace(seed=1)}
    with patch.dict(sys.modules,{'torch':fake_torch,'numpy':fake_numpy}),patch.object(common.TrainRun,'parameter_digest',return_value='final-mock-digest'):
        run.save_complete(ns)
    cp=saved['checkpoint_complete.pth.partial']
    expect(cp['plan_sha256'] != admitted['plan'] and cp['profile_sha256'] != admitted['profile'])
    expect(cp['configuration']['seed']==1)
    expect(json.loads((d/'status.json').read_text())['status']=='completed')
    owner_count=len(list(gate.owners(json.loads((d/'status.json').read_text()))))
    return {'admitted':admitted,'saved_hashes':{'plan':cp['plan_sha256'],'profile':cp['profile_sha256']},'status':'completed','saved_configuration_seed':1,'external_plan_seed':3,'status_owner_count':owner_count,'all_objects_explicit_stdlib_mocks':True,'saved_files_not_real_checkpoints':True}
check('final checkpoint provenance follows mutable external plan/profile',final_snapshot_mock,'gap_reproduced')

def repeated_output_rejected():
    d=FIX/'preexisting_output';d.mkdir(exist_ok=True)
    p=FIX/'repeat_plan.json';write(p,{'output_directory':str(d)})
    rejects(lambda:launch.train(p,FIX/'not_needed_profile',FIX/'not_needed_release'))
    expect(not (d/'status.json').exists())
check('pre-existing output directory is rejected before mutation',repeated_output_rejected)

def static_sequence():
    tree=ast.parse((PREP/'run_dac_training.py').read_text())
    train=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='train')
    imports=[n for n in ast.walk(train) if isinstance(n,ast.Import) and any(x.name=='torch' for x in n.names)]
    locks=[n for n in ast.walk(train) if isinstance(n,ast.With) and any(isinstance(x.context_expr,ast.Call) and ast.unparse(x.context_expr.func)=='exclusive_latest_baseline_lock' for x in n.items)]
    expect(len(imports)==len(locks)==1)
    expect(imports[0] in list(ast.walk(locks[0])))
    calls={ast.unparse(n.func):n.lineno for n in ast.walk(locks[0]) if isinstance(n,ast.Call)}
    expect(calls['serial_release_gate']<calls['input_audit.runtime_environment']<imports[0].lineno< calls['runpy.run_path'])
    return {'gate_line':calls['serial_release_gate'],'runtime_imports_line':calls['input_audit.runtime_environment'],'torch_import_line':imports[0].lineno,'entry_line':calls['runpy.run_path']}
check('scientific entry is downstream of shared lock and fresh gate',static_sequence)
def real_cpu_report_read_only():
    folder=OUT.parent/'dac_training_preparation_review_1721'/'real_cpu_probe_1822'
    path=folder/'result.json'
    expect(common.sha_file(path)=='5d1cb509088bb65a8ea5f22d1d7cfc482619bd3c61e0192f4c7aba5b8d094e25')
    proof=json.loads(path.read_text(encoding='utf-8'))
    expect(proof['script_sha256']==common.sha_file(folder.parent/'verify_dac_cpu_1822.py'))
    expect(proof['source_files_sha256']==launch.cpu_source_bindings())
    expect(proof['preparation']['preparation_manifest_sha256']==common.sha_file(PREP/'PREPARATION_MANIFEST.json'))
    expect(proof['all_model_state_cpu'] is True and proof['cuda_initialized'] is False)
    expect(proof['process_environment']['CUDA_VISIBLE_DEVICES']=='')
    expect(proof['model_state_count']==402 and proof['pretrained_strict_tensor_count']==344)
    expect(len(proof['pair_tensors'])==2)
    expect(all(row['shape']==[3,384,384] and row['dtype']=='torch.float32' and row['device']=='cpu' and row['finite'] is True for row in proof['pair_tensors']))
    expect(all(Path(v).resolve().is_relative_to(runtime.SCIENTIFIC_SOURCE.resolve()) for v in proof['module_origins'].values()))
    checked=[]
    for name,digest in proof['artifact_sha256'].items():
        artifact=(folder/name).resolve()
        expect(artifact.is_relative_to(folder.resolve()) and common.sha_file(artifact)==digest)
        checked.append(name)
    launch.validate_cpu_proof({'environment':proof['environment'],'cpu_compatibility_proof':{'path':str(path),'sha256':common.sha_file(path)}})
    return {'result_sha256':common.sha_file(path),'script_sha256':proof['script_sha256'],'hashed_raw_artifacts':checked,'independently_executed_by_this_review':False,'execution_exit_code_not_rechecked_here':True}
check('root real CPU proof artifact/source contracts match read-only',real_cpu_report_read_only,'read_only_observation')
check('all preparation file bytes unchanged by audit',lambda:expect(before_hashes()==INITIAL))
check('no real scientific module imported or attempted',lambda:expect(not ATTEMPTS and not original_tests.IMPORT_ATTEMPTS and not BLOCKED.intersection(sys.modules)))

report={'schema':'dac-independent-control-review.v1','generated_utc':datetime.now(timezone.utc).isoformat(),
    'review_scope':'stdlib, AST, explicit mock objects only; no scientific imports, model, images, GPU, process probe, or PowerPoint',
    'preparation':str(PREP),'preparation_manifest_sha256':common.sha_file(PREP/'PREPARATION_MANIFEST.json'),
    'result':'control_hardening_required_before_future_admission',
    'test_count':len(RESULTS),'passed':sum(x['passed'] for x in RESULTS),'checks':RESULTS,
    'scientific_import_attempts':ATTEMPTS+original_tests.IMPORT_ATTEMPTS,'actual_scientific_execution':False,
    'sealed_preparation_unchanged':before_hashes()==INITIAL,'source_snapshot_sha256':INITIAL}
write(OUT/'CONTROL_REVIEW_CHECKS.json',report)
print(json.dumps({'result':report['result'],'checks':report['test_count'],'passed':report['passed'],'failures':[r for r in RESULTS if not r['passed']],'report':str(OUT/'CONTROL_REVIEW_CHECKS.json')},ensure_ascii=False))
if report['passed']!=report['test_count']:raise SystemExit(1)
