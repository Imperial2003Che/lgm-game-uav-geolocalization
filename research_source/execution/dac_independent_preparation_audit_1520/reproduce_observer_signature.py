"""Execute only AST-extracted scalar classes; never import a scientific module."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
EXEC = HERE.parent
SOURCE = EXEC.parent / 'literature/official_repos/snapshots/Mabel0403__CAMP__b04a9c856711'
base_file = SOURCE / 'sample4geo/utils.py'
runtime_file = EXEC / 'camp_training_preparation/camp_train_runtime.py'

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

base = next(n for n in ast.parse(base_file.read_text(encoding='utf-8')).body if isinstance(n, ast.ClassDef) and n.name == 'AverageMeter')
runtime_tree = ast.parse(runtime_file.read_text(encoding='utf-8'))
observer = next(n for n in ast.walk(runtime_tree) if isinstance(n, ast.ClassDef) and n.name == 'ObservedAverageMeter')
namespace = {}
exec(compile(ast.Module(body=[base], type_ignores=[]), str(base_file), 'exec'), namespace)
calls = []
namespace.update(original=namespace['AverageMeter'], run=SimpleNamespace(observe_loss=lambda *a: calls.append(a)))
exec(compile(ast.Module(body=[observer], type_ignores=[]), str(runtime_file), 'exec'), namespace)
observed = namespace['ObservedAverageMeter']()
try:
    observed.update(2.5)
except TypeError as error:
    failure = str(error)
else:
    raise AssertionError('Counterexample unexpectedly did not fail')
record = {
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'status': 'confirmed_first_loss_observation_typeerror',
    'base': {'path': str(base_file), 'sha256': digest(base_file), 'line': 27, 'signature': 'update(self, val)'},
    'wrapper': {'path': str(runtime_file), 'sha256': digest(runtime_file), 'line': 241, 'call': 'super().update(val, n)'},
    'error': failure, 'observer_calls_before_exception': calls,
    'base_meter_count_after_failure': observed.count,
    'executed': 'Only AST-extracted AverageMeter and ObservedAverageMeter scalar classes',
    'scientific_imports': [], 'training': False, 'cuda': False,
    'source_mutations': [],
}
(HERE / 'CAMP_OBSERVER_SIGNATURE_COUNTEREXAMPLE.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print(json.dumps(record))
