"""Independent read-only path/AST review; no scientific imports or experiment writes."""
from pathlib import Path
import ast
import datetime
import hashlib
import importlib.util
import json
import os
import pickle
import sys

HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parent
ADAPTER = EXECUTION / 'primary_path_repair_20260918'
sys.path.insert(0, str(ADAPTER))
import project_paths as paths

def sha(p):
    with Path(p).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

checks = []
def check(label, condition, detail=None):
    if not condition:
        raise AssertionError(label)
    checks.append({'check': label, 'passed': True, 'detail': detail})

def rejected(label, fn, expected):
    try:
        fn()
    except expected as exc:
        checks.append({'check': label, 'passed': True, 'rejection': type(exc).__name__})
    else:
        raise AssertionError(label)

logical, physical = paths.LOGICAL, paths.PHYSICAL
check('actual fixed roots are one file object', os.path.samefile(logical, physical), paths.root_identity())
core = logical / 'lgm_game_pytorch/lgm_game_pytorch/formal_retrieval.py'
runner = logical / 'lgm_game_pytorch/experiments/run_frozen_formal_matrix.py'
check('original numerical core remains frozen', sha(core) == '081f327f8f83d79ab078adc61e76070c140f13e0ac9a0d8f423bfad15df59862')
check('original matrix runner remains frozen', sha(runner) == 'f251e5088b306ddec4769fab06799008d06194bc459282f2432ac3238f4ba59f')
resolved = paths.FrozenProjectPath(core).resolve(strict=True)
check('logical input retains historical spelling', str(resolved) == str(core))
check('physical input resolves to checked logical alias', paths.FrozenProjectPath(Path(core).resolve()).resolve(strict=True) == resolved)
check('native pathlib is not patched', Path(core).resolve() == physical / core.relative_to(logical))
check('existing aliases retain same actual file', os.path.samefile(resolved, core))
check('Path subclass round-trip is pickle-importable', type(pickle.loads(pickle.dumps(resolved))) is paths.FrozenProjectPath and pickle.loads(pickle.dumps(resolved)) == resolved)
outside = HERE / 'review_stdlib.py'
check('unrelated existing paths retain native spelling', paths.FrozenProjectPath(outside).resolve(strict=True) == Path(outside).resolve(strict=True))
prospective = logical / 'lgm_game_pytorch/runs/__path_review_nonexistent_20260920__/future.json'
check('prospective test destination is absent', not prospective.exists() and not prospective.parent.exists())
check('nonexistent output maps through same existing parent', str(paths.FrozenProjectPath(prospective).resolve()) == str(prospective))
rejected('strict resolution still rejects missing files', lambda: paths.FrozenProjectPath(prospective).resolve(strict=True), FileNotFoundError)
check('prospective check made no directories', not prospective.exists() and not prospective.parent.exists())
paths.LOGICAL = HERE
try:
    rejected('different existing roots are rejected', lambda: paths.preserve_project_path(Path(core).resolve()), RuntimeError)
finally:
    paths.LOGICAL = logical

config_details = []
for config_path in sorted((logical / 'lgm_game_pytorch/runs/formal_main').glob('*/*/seed_*/run_config.json')):
    raw = config_path.read_bytes()
    obj = json.loads(raw)
    immutable = obj['immutable_config']
    canonical = json.dumps(immutable, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=str).encode('utf-8')
    check('stored immutable hash ' + str(config_path.relative_to(logical)), hashlib.sha256(canonical).hexdigest() == obj['run_config_sha256'])
    for item in immutable['evidence_caches']:
        for field in ('path', 'meta_path'):
            check('frozen descriptor ' + field + ' ' + str(config_path.relative_to(logical)), str(paths.FrozenProjectPath(item[field]).resolve(strict=True)) == item[field])
    check('frozen dataset root ' + str(config_path.relative_to(logical)), str(paths.FrozenProjectPath(immutable['data_root']).resolve(strict=True)) == immutable['data_root'])
    record = immutable['model']['pretrained_initialization']
    if record.get('cached_file'):
        check('frozen pretrained path ' + str(config_path.relative_to(logical)), str(paths.FrozenProjectPath(record['cached_file']).resolve(strict=True)) == record['cached_file'])
    check('run config is unchanged after read-only checks ' + str(config_path.relative_to(logical)), config_path.read_bytes() == raw)
    config_details.append({'path': str(config_path), 'sha256': sha(config_path), 'run_config_sha256': obj['run_config_sha256']})

source = core.read_text(encoding='utf-8')
tree = ast.parse(source)
classes = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
functions = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
for class_name, methods in [('PairTrainingDataset', ('__getitem__', '_image', '_gallery_for')), ('RecordDataset', ('__getitem__',))]:
    cls = classes[class_name]
    for node in (n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in methods):
        check('worker method has no project Path resolution ' + class_name + '.' + node.name,
              not any(isinstance(n, ast.Name) and n.id == 'Path' for n in ast.walk(node)) and
              not any(isinstance(n, ast.Attribute) and n.attr == 'resolve' for n in ast.walk(node)))
check('worker RNG seeding never resolves a project path', not any(isinstance(n, ast.Name) and n.id == 'Path' for n in ast.walk(functions['seed_worker'])))
inventory_source = ast.get_source_segment(source, functions['inventory_hash'])
check('inventory encodes relative rather than absolute image location', 'digest.update(relative_path.encode("utf-8"))' in inventory_source and 'stat = absolute_path.stat()' in inventory_source and 'absolute_path.encode' not in inventory_source)
default = functions['default_sues_manifest_path']
module = ast.Module(body=[default], type_ignores=[])
namespace = {'Path': paths.FrozenProjectPath, '__file__': str(core)}
exec(compile(module, '<extracted exact default_sues_manifest_path>', 'exec'), namespace)
sues = logical / 'lgm_game_pytorch/manifests/sues200_official_train_ids.yaml'
check('exact original default SUES function restores logical path', namespace['default_sues_manifest_path']() == str(sues))

old_tree = ast.parse((EXECUTION / 'continue_formal_matrix.py').read_text(encoding='utf-8'))
new_tree = ast.parse((EXECUTION / 'continue_formal_matrix_path_compat_v1.py').read_text(encoding='utf-8'))
old_functions = {n.name: n for n in old_tree.body if isinstance(n, ast.FunctionDef)}
new_functions = {n.name: n for n in new_tree.body if isinstance(n, ast.FunctionDef)}
for name in old_functions.keys() - {'main'}:
    check('unchanged original controller function ' + name, ast.dump(old_functions[name]) == ast.dump(new_functions[name]))
worker_source = (ADAPTER / 'run_formal_worker.py').read_text(encoding='utf-8')
check('bare original core import avoids extra package initialization', "importlib.import_module('formal_retrieval')" in worker_source and "sys.path.insert(0, str(package / 'lgm_game_pytorch'))" in worker_source and "importlib.import_module('lgm_game_pytorch.formal_retrieval')" not in worker_source)
from source_contract import verify
manifest_sha = sha(ADAPTER / 'SOURCE_MANIFEST.json')
check('updated fixed manifest identity', manifest_sha == '11de17bd611431e4471eec1b8ac072a2159fbd02e4eb2cb041b4f3b0f00012a1')
check('actual all-source contract verification passes', verify(manifest_sha)['manifest_sha256'] == manifest_sha)
check('scientific libraries never imported by review', not any(n.split('.')[0] in {'torch', 'torchvision', 'numpy', 'PIL', 'cv2'} for n in sys.modules))
report = {
    'schema': 'independent-primary-path-review.v1',
    'reviewer': '/root/primary_path_adapter_review',
    'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'scope': 'Independent standard-library actual path/read-only configuration and AST audit. No scientific import, numerical execution, GPU, training, or DataLoader run.',
    'checks': checks,
    'stored_run_configs': config_details,
    'source_files': [{'path': str(p), 'sha256': sha(p)} for p in [core, runner, ADAPTER / 'project_paths.py', ADAPTER / 'run_formal_worker.py', ADAPTER / 'SOURCE_MANIFEST.json', EXECUTION / 'continue_formal_matrix_path_compat_v1.py']],
    'finding': {'severity': 'source-contract gap', 'original_prepared_worker': '1927f0be33dea6df829927cb6820860ef321501934c313e5b55b38f82b9fe674', 'description': 'Qualified package import executes unfrozen __init__.py and model.py that the original standalone core did not execute. Present extra modules define classes without model construction, but are not in the source manifest.', 'minimal_correction': "Insert the core directory itself into sys.path and import bare formal_retrieval; verify exact core file identity. This also provides an ordinary importable module name for Windows multiprocessing unpickling.", 'status': 'Root applied the bare import correction and retained previous prepared worker/manifest. Final source and new manifest verified by this reviewer.'},
    'review_harness_history': ['Initial run reached inventory AST check then failed because reviewer asserted the literal expression record.absolute_path.stat(), while original code binds absolute_path inside the loop. The reviewer corrected this assertion to match the inspected original code. No source defect, source edit, report overwrite, or scientific execution occurred.'],
    'limitations': ['Standard-library pickle round-trip is not a live torch DataLoader spawn test.', 'Actual EvidenceStore numerical validation, live Windows spawn, resumed model state and GPU training must be verified separately by root.', 'Only fourteen existing main-run configurations currently exist; no configuration or result was fabricated for unstarted runs.'],
}
output = HERE / 'INDEPENDENT_STDLIB_REVIEW.json'
with output.open('x', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(json.dumps({'checks': len(checks), 'configs': len(config_details), 'report': str(output), 'sha256': sha(output)}, ensure_ascii=False))
