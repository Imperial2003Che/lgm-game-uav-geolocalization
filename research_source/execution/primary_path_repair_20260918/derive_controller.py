"""Add path adaptation while preserving actual environment import and science."""
from pathlib import Path
import ast
import difflib
import json
from source_contract import sha

HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parent
original = EXECUTION / 'continue_formal_matrix.py'
assert sha(original) == '4bac7204d1a152b726ed0fb4ebb806a9ef9f5a81b1c2d53f03ba44b0b124d4da'
source = original.read_text(encoding='utf-8')
def once(old, new):
    global source
    assert source.count(old) == 1, old
    source = source.replace(old, new)
once('import msvcrt\n', "import msvcrt\nsys.path.insert(0, str(Path(__file__).resolve().parent / 'primary_path_repair_20260918'))\nfrom project_paths import FrozenProjectPath\nfrom source_contract import verify as verify_path_compatibility\n")
once("    args=parser.parse_args()\n", "    parser.add_argument('--path-compat-sha256')\n    args=parser.parse_args()\n")
once("    if args.workers<0: raise ValueError('workers must be nonnegative')\n",
     "    path_compatibility = verify_path_compatibility(args.path_compat_sha256)\n    if args.workers<0: raise ValueError('workers must be nonnegative')\n")
once("    legacy=importlib.util.module_from_spec(spec);sys.modules[spec.name]=legacy;spec.loader.exec_module(legacy)\n",
     "    legacy=importlib.util.module_from_spec(spec);sys.modules[spec.name]=legacy;spec.loader.exec_module(legacy)\n    legacy.Path = FrozenProjectPath\n")
once("'stage':args.stage,'python':sys.executable,'runtime_provenance':runtime,'events':[]}",
     "'stage':args.stage,'python':sys.executable,'runtime_provenance':runtime,'events':[],\n            'project_path_compatibility':path_compatibility}")
once("            return result\n", "            if Path(result[1]).resolve() != (ORIGINAL/'lgm_game_pytorch/lgm_game_pytorch/formal_retrieval.py').resolve():\n                raise RuntimeError('Unexpected scientific entry point')\n            verify_path_compatibility(args.path_compat_sha256)\n            return [result[0],str(HERE/'primary_path_repair_20260918/run_formal_worker.py'),\n                    '--path-compat-sha256',args.path_compat_sha256,*result[2:]]\n")
ast.parse(source)
target = EXECUTION / 'continue_formal_matrix_path_compat_v1.py'
with target.open('x', encoding='utf-8', newline='\n') as stream: stream.write(source)
with (HERE / 'controller.patch').open('x', encoding='utf-8') as stream:
    stream.writelines(difflib.unified_diff(original.read_text(encoding='utf-8').splitlines(True), source.splitlines(True), fromfile=original.name, tofile=target.name))
files = [HERE / name for name in ('project_paths.py', 'source_contract.py', 'run_formal_worker.py',
          'audit_registry.py', 'ACTUAL_REGISTRY_AUDIT.json', 'derive_controller.py')]
files += [original, target,
          Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724/lgm_game_pytorch/lgm_game_pytorch/formal_retrieval.py'),
          Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724/lgm_game_pytorch/experiments/run_frozen_formal_matrix.py')]
manifest = {'schema': 'original-project-path-adapter.v1', 'status': 'prepared_pending_verification_no_training',
            'files': [{'path': str(p), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in files]}
with (HERE / 'SOURCE_MANIFEST.json').open('x', encoding='utf-8') as stream: json.dump(manifest, stream, ensure_ascii=False, indent=2)
print(json.dumps({'source_manifest_sha256': sha(HERE / 'SOURCE_MANIFEST.json'), 'controller_sha256': sha(target)}))
