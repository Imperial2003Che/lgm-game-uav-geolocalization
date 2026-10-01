"""Independent static/hash review. Never imports reviewed scientific modules."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

BASE = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914')
EX = BASE / 'execution'
DAC = EX / 'dac_training_preparation_v1'
SCI = DAC / 'scientific_source'
OUT = Path(__file__).resolve().parent
OFF = BASE / 'literature/official_repos/snapshots/SummerpanKing__DAC__5612a79c3928'
checks = []

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def read(path):
    return Path(path).read_text('utf-8-sig')

def js(path):
    return json.loads(read(path))

def tree(path):
    return ast.parse(read(path))

def dump(node):
    return ast.dump(node, include_attributes=False)

def check(name, ok, evidence=None):
    checks.append({'name': name, 'passed': bool(ok), 'evidence': evidence})

def named(root, name):
    return next(n for n in ast.walk(root) if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == name)

def call_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return call_name(node.value) + '.' + node.attr
    return ''

def calls(root, name):
    return [n for n in ast.walk(root) if isinstance(n, ast.Call) and call_name(n.func) == name]

pin = js(DAC / 'SOURCE_PIN.json')
manifest = js(DAC / 'SCIENTIFIC_SOURCE_MANIFEST.json')
official_rows = [{**r, 'actual_sha256': sha(OFF / r['path'])} for r in pin['files']]
derived_rows = [{**r, 'actual_original_sha256': sha(OFF / r['path']),
    'actual_derived_sha256': sha(SCI / r['path'])} for r in manifest['files']]
check('all_36_official_source_hashes', len(official_rows) == 36 and all(r['sha256'] == r['actual_sha256'] for r in official_rows), official_rows)
check('all_19_scientific_manifest_hashes', len(derived_rows) == 19 and all(r['actual_original_sha256'] == r['original_sha256'] and r['actual_derived_sha256'] == r['derived_sha256'] for r in derived_rows), derived_rows)
changed = [r['path'] for r in derived_rows if r['original_sha256'] != r['derived_sha256']]
check('only_dataset_and_trainer_derived', sorted(changed) == ['sample4geo/dataset/university.py', 'sample4geo/trainer.py'], changed)
actual_source = {p.relative_to(SCI).as_posix() for p in SCI.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
check('scientific_source_manifest_complete', actual_source == {r['path'] for r in manifest['files']}, sorted(actual_source))

orig_train, new_train = tree(OFF / 'sample4geo/trainer.py'), tree(SCI / 'sample4geo/trainer.py')
check('official_train_function_ast_exact', dump(named(orig_train, 'train')) == dump(named(new_train, 'train')),
    {'original_line': named(orig_train,'train').lineno, 'derived_line': named(new_train,'train').lineno})
orig_dataset, new_dataset = tree(OFF / 'sample4geo/dataset/university.py'), tree(SCI / 'sample4geo/dataset/university.py')
for n in ['get_data', 'U1652DatasetTrain', 'get_transforms']:
    check(n + '_ast_exact', dump(named(orig_dataset, n)) == dump(named(new_dataset, n)),
        {'original_line': named(orig_dataset,n).lineno, 'derived_line': named(new_dataset,n).lineno})
check('dataset_keeps_only_normal_train_definitions', [n.name for n in new_dataset.body if isinstance(n,(ast.ClassDef,ast.FunctionDef))] == ['get_data','U1652DatasetTrain','get_transforms'])
check('trainer_keeps_only_train', [n.name for n in new_train.body if isinstance(n,(ast.ClassDef,ast.FunctionDef))] == ['train'])

oe, ne = tree(OFF / 'train_university.py'), tree(DAC / 'train_university_train_only.py')
def arguments(root):
    return {n.args[0].value: dump(n) for n in calls(named(root,'Configuration'),'parser.add_argument')}
oa, na = arguments(oe), arguments(ne)
deleted = ['--only_test','--ckpt_path','--batch_size_eval','--eval_every_n_epoch','--eval_gallery_n','--zero_shot','--checkpoint_start','--data_folder']
check('entry_only_declared_cli_removed', set(oa)-set(na) == set(deleted) and not set(na)-set(oa), sorted(set(oa)-set(na)))
modified_defaults = [k for k in na if na[k] != oa[k]]
check('all_retained_argument_definitions_exact_except_device_no_probe', modified_defaults == ['--device'], modified_defaults)
parse_args = calls(named(ne,'Configuration'),'parser.parse_args')
check('configuration_cannot_take_undeclared_cli', len(parse_args)==1 and dump(parse_args[0].args[0]) == 'List(elts=[], ctx=Load())')
for call in ['setup_system','DataLoader','U1652DatasetTrain','get_transforms','GradScaler','train','torch.optim.AdamW']:
    oc, nc = calls(oe,call),calls(ne,call)
    # There were extra evaluation DataLoaders in the original. The original train one is first.
    if call == 'DataLoader':
        oc = oc[:1]
    check('entry_' + call + '_call_ast_exact', [dump(n) for n in oc] == [dump(n) for n in nc],
        {'original_lines':[n.lineno for n in oc], 'derived_lines':[n.lineno for n in nc]})
def branch(root, test):
    return next(n for n in ast.walk(root) if isinstance(n,ast.If) and ast.unparse(n.test) == test)
for test in ['config.decay_exclue_bias', "config.scheduler == 'polynomial'", 'config.mixed_precision']:
    a,b = branch(oe,test),branch(ne,test)
    check('entry_branch_' + test + '_ast_exact', dump(a)==dump(b),{'original_line':a.lineno,'derived_line':b.lineno})
for var in ['train_steps_per','train_steps','warmup_steps','loss_functions']:
    select=lambda t: next(n for n in ast.walk(t) if isinstance(n,ast.Assign) and any(isinstance(v,ast.Name) and v.id==var for v in n.targets))
    a,b=select(oe),select(ne)
    check(var+'_ast_exact',dump(a)==dump(b),{'original_line':a.lineno,'derived_line':b.lineno})
shuffle = calls(ne,'train_dataloader.dataset.shuffle')
trainsteps = next(n for n in ast.walk(ne) if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='train_steps' for x in n.targets))
check('scheduler_before_original_initial_shuffle_and_postepoch_shuffle_retained', len(shuffle)==2 and trainsteps.lineno < shuffle[0].lineno < calls(ne,'train')[0].lineno < shuffle[1].lineno)
prohibited = {'evaluate','predict','U1652DatasetEval','query_dataloader_test','gallery_dataloader_test','query_folder_test','gallery_folder_test','zero_shot','only_test','best_score','checkpoint_start','ckpt_path'}
active_names = {n.id for n in ast.walk(ne) if isinstance(n,ast.Name)} | {n.attr for n in ast.walk(ne) if isinstance(n,ast.Attribute)}
check('entry_no_test_selection_or_author_checkpoint_names', not active_names & prohibited, sorted(active_names & prohibited))
check('entry_first_statement_admission_guard', isinstance(ne.body[0],ast.If) and isinstance(ne.body[0].body[0],ast.Raise) and 'DAC_RUN' in ast.unparse(ne.body[0].test))

schema_path = DAC / 'DAC_EXPECTED_MODEL_SCHEMA.json'
schema = js(schema_path)
metadata_path = Path(schema['source_report_path'])
metadata = js(metadata_path)
expected = {r['key']:{'shape':r['shape'],'dtype':r['dtype']} for r in metadata['tensor_comparisons']}
check('402_schema_exact_existing_DAC_meta_proof', len(expected)==402 and schema['tensors']==expected and sha(metadata_path)==schema['source_report_sha256'] and all(r['matches'] is True for r in metadata['tensor_comparisons']),
    {'source_path':str(metadata_path),'source_sha256':sha(metadata_path),'count':len(expected), 'historical_proof_real_storage_load':metadata['real_tensor_checkpoint_load'],'historical_proof_gpu':metadata['gpu_executed']})

runtime = tree(DAC / 'dac_train_runtime.py')
schema_namespace = {'HERE':DAC,'json':json,'sha_file':sha}
exec(compile(ast.Module(body=[named(runtime,'validate_model_schema')],type_ignores=[]),'extracted-schema-check-only','exec'),schema_namespace)
fake = {k:SimpleNamespace(shape=v['shape'],dtype=v['dtype']) for k,v in expected.items()}
schema_fn = schema_namespace['validate_model_schema']
check('schema_mock_correct_402_accepts',schema_fn(fake)['tensor_count']==402)
for label,mutate in [
    ('CAMP_like_395',lambda d:dict(list(d.items())[:395])),
    ('same_count_wrong_key',lambda d:{**dict(list(d.items())[1:]),'not_DAC':next(iter(d.values()))}),
    ('wrong_shape',lambda d:{**d,next(iter(d)):SimpleNamespace(shape=[999],dtype=next(iter(d.values())).dtype)}),
    ('wrong_dtype',lambda d:{**d,next(iter(d)):SimpleNamespace(shape=next(iter(d.values())).shape,dtype='torch.float16')})]:
    try:
        schema_fn(mutate(fake))
        rejected=False
    except RuntimeError:
        rejected=True
    check('schema_mock_rejects_'+label,rejected)

cr_path=DAC/'common_runtime.py'
camp_cr=EX/'camp_training_preparation_v2/train_runtime.py'
# The previous adapter calls this file train_runtime.py.
check('generic_runtime_prior_verified_SHA',sha(cr_path)=='3cbf41ddef34fba1bb1a57f5eca287129748708abb21941f63ff9a5ac40d9b26', {'path':str(cr_path),'sha256':sha(cr_path)})
cr=tree(cr_path)
localfactory=named(cr,'local_factory')
localconstructor=calls(localfactory,'backbone.ConvNeXt')[0]
originalconstructor=calls(named(tree(SCI/'sample4geo/hand_convnext/ConvNext/backbones/model_convnext.py'),'convnext_base'),'ConvNeXt')[0]
check('local_backbone_constructor_exact_original_arguments', [dump(a) for a in localconstructor.args]==[dump(a) for a in originalconstructor.args] and [dump(k) for k in localconstructor.keywords]==[dump(k) for k in originalconstructor.keywords], {'original_line':originalconstructor.lineno,'runtime_line':localconstructor.lineno})
check('local_factory_strict_coverage_and_CPU_load', "model.load_state_dict(state, strict=True)" in read(cr_path) and "map_location='cpu', weights_only=True, mmap=True" in read(cr_path) and 'if missing or extra or mismatch:' in read(cr_path))

ref=js(DAC/'INPUT_REFERENCES.json')
historic=js(EX/'camp_training_preparation_v2/PRETRAINED_META_VALIDATION.json')
pretrain_hash=sha(ref['pretrained']['path'])
check('actual_local_original_weight_bytes_match_historical_344_proof',pretrain_hash==ref['pretrained']['sha256']==historic['pretrained']['sha256'] and Path(ref['pretrained']['path']).stat().st_size==historic['pretrained']['bytes'] and historic['passed'] is True and historic['expected_tensors']==historic['checkpoint_tensors']==344 and not historic['missing_keys'] and not historic['unexpected_keys'] and not historic['shape_or_dtype_mismatch'],
    {'actual_path':ref['pretrained']['path'],'actual_sha256':pretrain_hash,'bytes':Path(ref['pretrained']['path']).stat().st_size,'historic_proof_path':str(EX/'camp_training_preparation_v2/PRETRAINED_META_VALIDATION.json'),'historic_proof_sha256':sha(EX/'camp_training_preparation_v2/PRETRAINED_META_VALIDATION.json'),'current_review_real_tensor_load':False})
camp_manifest=js(EX/'camp_training_preparation_v2/SOURCE_PIN.json')
camp_backbone=next(r['sha256'] for r in camp_manifest['files'] if r['path']=='sample4geo/hand_convnext/ConvNext/backbones/model_convnext.py')
check('DAC_backbone_bytes_match_344_meta_constructor_source',sha(SCI/'sample4geo/hand_convnext/ConvNext/backbones/model_convnext.py')==camp_backbone,{'sha256':camp_backbone})
check('existing_train_manifest_hash_bound',sha(ref['data_manifest_path'])==ref['data_manifest_sha256'],{'path':ref['data_manifest_path'],'sha256':sha(ref['data_manifest_path']),'images_rescanned':False})

original_utils=read(SCI/'sample4geo/utils.py')
check('backend_evidence_records_actual_original_typo_object', 'torch.backends.cudnn_benchmark_enabled = cudnn_benchmark' in original_utils and "getattr(torch.backends, 'cudnn_benchmark_enabled', None)" in read(DAC/'dac_train_runtime.py'))
scope_files=['train_university_train_only.py','dac_train_runtime.py','common_runtime.py','SCIENTIFIC_SOURCE_MANIFEST.json','SOURCE_PIN.json','DAC_EXPECTED_MODEL_SCHEMA.json','INPUT_REFERENCES.json']
scope_hashes={name:sha(DAC/name) for name in scope_files}
for file in [DAC/'train_university_train_only.py',DAC/'dac_train_runtime.py',DAC/'common_runtime.py']:
    compile(read(file),str(file),'exec')
check('three_main_reviewed_modules_parse_compile',True)
check('no_scientific_libraries_imported_by_review',not any(k in sys.modules for k in ['torch','numpy','PIL','cv2','timm','transformers']))
report={'schema':'dac-independent-scientific-static-review.v1','finished_utc':datetime.now(timezone.utc).isoformat(),
    'reviewer':'memory_failure_1544_review','official_commit':pin['commit_sha'],'scope_hashes':scope_hashes,
    'review_script_sha256':sha(__file__),'checks':checks,'pass_count':sum(x['passed'] for x in checks),'check_count':len(checks),
    'failed_checks':[c['name'] for c in checks if not c['passed']],
    'executed_scope':{'source_read_hash_ast':True,'extracted_schema_function_fake_tensor_tests':True,'new_scientific_imports':False,'new_real_tensor_load':False,'new_model_forward':False,'training':False,'GPU':False,'environment_change':False,'author_file_change':False},
    'not_reviewed':['changing run_dac_training control/gate implementation','resource admission truth on later execution','new CPU constructor/real-image probe','new CUDA full-loss/AdamW update','complete training results'],
    'scientific_findings':[
      'Official train AST, normal train dataset/augmentation AST, losses, AdamW/AMP/scheduler calls and ordering are retained.',
      'Default DSA is one minus mean cosine similarity after original projection/normalization/softmax/concatenation and flattening; function name mse_loss is misleading but not altered.',
      'Scheduler count is planned before original first custom shuffle: ceil(37854/24)=1578 and warmup157.8. Actual sampler batch count is recorded, not silently substituted.',
      'Classifier CE smoothing0 and InfoNCE CE smoothing0.1 remain distinct; gradient clipping is value100.',
      'New model schema uses existing DAC402 meta proof only as expected key/shape/dtype. Author-trained DAC tensors are not loaded in training factory.',
      '344 pretrained proof is historical metadata tied to current exact weight bytes and same exact backbone source. New actual DAC initialization is still required.',
      'Official torch.backends.cudnn_benchmark_enabled typo is preserved. The corrected evidence must read that exact object, while actual cudnn.benchmark is separately recorded.',
      'Test dataset paths/loaders/evaluation/score-based checkpoint selection removed. Runtime pins original satellite/drone train paths and guards scans and image reads. Control must activate that boundary.',
      'Scientific defaults preserved apart from explicitly registered single-GPU Windows execution and local input/output bindings; seeds2/3 are local repeated-run extension.'
    ]}
(OUT/'INDEPENDENT_SCIENTIFIC_REVIEW.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':report['pass_count'],'total':report['check_count'],'failed':report['failed_checks'],'scope_hashes':scope_hashes,'report_sha256':sha(OUT/'INDEPENDENT_SCIENTIFIC_REVIEW.json')},ensure_ascii=True,indent=2))
