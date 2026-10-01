"""Stopped-training live environment probe; the parent remains stdlib-only."""
import importlib.util, sys, json, hashlib, datetime, ast, difflib
from pathlib import Path
root=Path(__file__).resolve().parent
incident=root/'memory_recovery_20260914_1424'
source=root/'continue_formal_matrix.py'
spec=importlib.util.spec_from_file_location('verify_controller',source)
controller=importlib.util.module_from_spec(spec);spec.loader.exec_module(controller)
assert controller.scientific_modules()==[]
prior=(incident/'controllers/continue_formal_matrix.py').read_text(encoding='utf-8')
current=source.read_text(encoding='utf-8')
old_ast=ast.parse(prior); new_ast=ast.parse(current)
find=lambda tree,name: next(n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name)
unchanged=[]
for name in ('verify_training_environment','monitored_run','resource_command','sha','save'):
    assert ast.dump(find(old_ast,name),include_attributes=False)==ast.dump(find(new_ast,name),include_attributes=False),name
    unchanged.append(name)
runtime=controller.verify_training_environment_isolated()
assert len(runtime['verified_completed_fit_manifests'])==13
assert runtime['isolation']['exit_code']==0 and controller.scientific_modules()==[]
assert set(runtime['isolation']['preserved_import_environment_keys'])<=controller.IMPORT_ENVIRONMENT_KEYS
legacy_spec=importlib.util.spec_from_file_location('original_frozen_matrix',controller.SCRIPT)
legacy=importlib.util.module_from_spec(legacy_spec);sys.modules[legacy_spec.name]=legacy;legacy_spec.loader.exec_module(legacy)
assert controller.scientific_modules()==[]
with source.open('rb') as stream: new_sha=hashlib.file_digest(stream,'sha256').hexdigest()
with (incident/'controllers/continue_formal_matrix.py').open('rb') as stream: old_sha=hashlib.file_digest(stream,'sha256').hexdigest()
report={'status':'passed_live_isolated_environment_probe','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'prior_controller_sha256':old_sha,'new_controller_sha256':new_sha,'unchanged_function_ast':unchanged,'runtime':runtime,'scientific_modules_after_legacy_import':controller.scientific_modules(),'scope':'Real dependency checks only; no CUDA initialization and no training was started. Both probe interpreter and launcher exited before this parent continued.'}
(incident/'isolated_environment_live_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(incident/'controller_memory_isolation.patch').write_text(''.join(difflib.unified_diff(prior.splitlines(True),current.splitlines(True),fromfile='prior/continue_formal_matrix.py',tofile='current/continue_formal_matrix.py')),encoding='utf-8')
print(json.dumps({'status':report['status'],'completed_fit_manifests':13,'parent_scientific_modules':[],'preserved_import_env_keys':runtime['isolation']['preserved_import_environment_keys'],'source_sha256':new_sha}))
