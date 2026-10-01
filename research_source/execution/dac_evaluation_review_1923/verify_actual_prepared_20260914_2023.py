"""Bounded read-only verification of actual prepared DAC evaluation; standard library only."""
from datetime import datetime, timezone
import hashlib
import importlib.abc
import importlib.metadata
import json
from pathlib import Path
import sys

OUT = Path(__file__).resolve().parent
EXECUTION = OUT.parent
EVAL = EXECUTION/'dac_independent_evaluation_v2'
TRAIN_EXEC = EXECUTION/'dac_training_execution_v2'
PREPARED = EVAL/'preparations/fixed_three_seed/manifest.json'
REPORT = OUT/'ACTUAL_PREPARED_VERIFICATION_20260914_2023.json'
if REPORT.exists():
    raise RuntimeError('Unique audit output already exists; do not overwrite')
BLOCKED = {'torch', 'torchvision', 'numpy', 'PIL', 'cv2', 'timm', 'scipy', 'sklearn', 'albumentations', 'transformers', 'tensorboard'}
ATTEMPTS = []
sys.dont_write_bytecode = True
class NoScience(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in BLOCKED:
            ATTEMPTS.append(fullname)
            raise RuntimeError('Scientific import forbidden: '+fullname)
sys.meta_path.insert(0, NoScience())
def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()
def read(path):
    return json.loads(Path(path).read_bytes())
def require(ok, message):
    if not ok:
        raise AssertionError(message)

EXPECTED = {
    str(PREPARED): '9923839dbc3c2504588fed791ef0489047d30c585f3efefd40dfc3da07da64ca',
    str(EVAL/'PREPARATION_MANIFEST.json'): 'adb5521285ca50cb21db0c235c1a476c634643b44489ffb7692b500623a8cfe0',
    str(TRAIN_EXEC/'PREPARATION_MANIFEST.json'): '5088fe2d593009c187627ab1dbeec854d212dc4d67eb626044413735a6c36002',
    str(TRAIN_EXEC/'execution_spec.json'): '069c8531fd73de799b47d538ff95f11bedab9a720f29dc607bebe5d397b7d78e',
}
CHECKS = []
PROTECTED = dict(EXPECTED)
def checked(name, detail=None):
    CHECKS.append({'name': name, 'passed': True, 'detail': detail})
for path, digest in EXPECTED.items():
    require(sha(path) == digest, 'Task-pinned actual bytes changed: '+path)
checked('actual prepared, evaluation seal, executor seal and specification match externally supplied SHA', EXPECTED)

def package(root, manifest_name, expected_count):
    manifest = read(root/manifest_name)
    rows = manifest['files']
    require(len(rows) == expected_count and len({row['path'] for row in rows}) == expected_count, 'Payload count or uniqueness differs')
    for row in rows:
        path = (root/row['path']).resolve()
        require(path.is_relative_to(root) and path.is_file(), 'Manifest path escaped or missing')
        require(path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], 'Sealed payload changed: '+str(path))
        PROTECTED[str(path)] = row['sha256']
    return manifest, sum(row['bytes'] for row in rows)

execution_manifest, execution_bytes = package(TRAIN_EXEC, 'PREPARATION_MANIFEST.json', 11)
require(execution_manifest['payload_files'] == 11 and execution_manifest['payload_bytes'] == execution_bytes == 92501, 'Executor totals mismatch')
require(execution_manifest['spec_sha256'] == EXPECTED[str(TRAIN_EXEC/'execution_spec.json')], 'Executor spec differs')
checked('all eleven final executor payload files match actual bytes and SHA', {'files': 11, 'bytes': execution_bytes})
evaluation_manifest, evaluation_bytes = package(EVAL, 'PREPARATION_MANIFEST.json', 18)
checked('all eighteen frozen evaluation payload files match actual bytes and SHA', {'files': 18, 'bytes': evaluation_bytes})

external = read(TRAIN_EXEC/'EXTERNAL_REVIEW_REFERENCES.json')
for row in external['references']:
    require(sha(row['path']) == row['sha256'], 'External executor review changed')
    PROTECTED[row['path']] = row['sha256']
review = evaluation_manifest['independent_review']
require(sha(review['path']) == review['sha256'] and Path(review['path']).stat().st_size == review['bytes'], 'Sealed root evaluation review changed')
PROTECTED[review['path']] = review['sha256']
for name, digest in external['final_core_sources'].items():
    require(sha(TRAIN_EXEC/name) == digest, 'Independent final reviewed executor source differs')
checked('sealed external reviews and corrected final executor source match; ROOT_V2_RECHECK only read', {'root_review_sha256': review['sha256']})

# Import only after externally supplied package identity and every local payload
# have been verified. The frozen helper's normal read path is invoked unmocked.
sys.path.insert(0, str(EVAL))
import protocol as p
import run_evaluation as runner
with p.snapshot_scope():
    prepared = runner.read_prepared(PREPARED)
    require(p.input_artifact(PREPARED)['sha256'] == EXPECTED[str(PREPARED)], 'First-read actual prepared SHA differs')
    require(prepared['training_execution_package']['sha256'] == EXPECTED[str(TRAIN_EXEC/'PREPARATION_MANIFEST.json')], 'Prepared execution seal is wrong')
    p.verify_execution_package(prepared['training_execution_package'], EXPECTED[str(TRAIN_EXEC/'PREPARATION_MANIFEST.json')])
    require(p.membership_evidence() == prepared['membership'], 'Actual membership contract differs from frozen helper output')
    p.unchanged_inputs()
checked('unmocked frozen read_prepared and verify_execution_package accept actual prepared package')

pins = p.pins()
require(len(pins['files']) == 112, 'Frozen source pin count differs')
for path, digest in pins['files'].items():
    require(sha(path) == digest, 'Pinned scientific/control/input source differs')
    PROTECTED[path] = digest
require(prepared['sources'] == p.source_evidence(), 'Prepared source evidence differs')
checked('all 112 pinned source files and five adapter modules match actual prepared source evidence', {'source_files': 112, 'adapter_modules': len(prepared['sources']['adapter_files'])})

sys.path.insert(0, str(TRAIN_EXEC))
import dac6_contracts as d
require(d.own_manifest() == EXPECTED[str(TRAIN_EXEC/'PREPARATION_MANIFEST.json')], 'Frozen execution helper returned a different seal')
spec = d.spec_bound(TRAIN_EXEC/'execution_spec.json', EXPECTED[str(TRAIN_EXEC/'execution_spec.json')])
require([row['id'] for row in spec.value['jobs']] == d.ORDER, 'Six-stage fixed sequence differs')
checked('unmocked frozen own_manifest and spec_bound validate actual eleven-file executor and six stages', {'stage_order': d.ORDER})

require(prepared['seeds'] == [1, 2, 3] and len(prepared['training_plans']) == 3, 'Exact three seeds required')
plans = []
for item in prepared['training_plans']:
    plan = read(item['plan']['path'])
    require(p.validate_training_plan(plan, item['seed']) == Path(item['output_directory']), 'Declared exact seed plan differs')
    require(item['checkpoint_sha256'] is None and item['future_checkpoint'] == 'weights_end.pth', 'Future checkpoint was falsely bound')
    require('awaiting verified completed training' in item['checkpoint_binding_status'], 'Checkpoint pending status differs')
    for row in spec.value['jobs']:
        if row['seed'] == item['seed']:
            require(row['plan_path'] == item['plan']['path'] and row['plan_sha256'] == item['plan']['sha256'], 'Execution/evaluation seed binding differs')
    plans.append({'seed': item['seed'], 'plan_sha256': item['plan']['sha256'], 'checkpoint_sha256': None, 'output_directory': item['output_directory']})
require(prepared['status'] == 'prepared_waiting_for_training' and prepared['method'] == 'DAC', 'Prepared state falsely claims execution')
require(not any(key in prepared for key in ('training_completion', 'completion_sha256', 'binding', 'results', 'release')), 'Future completion or results injected')
checked('all three original plans match executor and all future checkpoint SHA values remain null', plans)

inventory_ref = prepared['membership']['inventory']
task_ref = prepared['membership']['tasks']
inventory = read(inventory_ref['path'])
tasks = read(task_ref['path'])
require(len(inventory) == len({row['key'] for row in inventory}) == 131062, 'Full unique inventory differs')
require(len(tasks) == 10 and len({task['name'] for task in tasks}) == 10 and prepared['task_count'] == len(tasks)*len(plans) == 30, 'Not exactly thirty seed/task pairs')
task_summary = []
expected_counts = [(37855, 951), (701, 51355)] + [(4000, 200), (80, 10000)]*4
for task, counts in zip(tasks, expected_counts):
    qi, gi = task['query_indices'], task['gallery_indices']
    require(all(type(k) is int and 0 <= k < len(inventory) for k in qi+gi), 'Task index out of bounds')
    require(len(qi) == len(set(qi)) == task['query_count'] == counts[0] and len(gi) == len(set(gi)) == task['gallery_count'] == counts[1], 'Query/gallery membership count differs')
    query = [inventory[k] for k in qi]
    gallery = [inventory[k] for k in gi]
    qids, gids = {r['label'] for r in query}, {r['label'] for r in gallery}
    require(qids < gids and len(qids) == task['query_identity_count'] and len(gids) == task['gallery_identity_count'], 'Full-gallery identities differ')
    require(len(gids-qids) == task['distractor_identity_count'] == (250 if task['name'].startswith('university') else 120), 'Distractor gallery changed')
    canonical = p.canonical({'query': [(r['key'], r['label']) for r in query], 'gallery': [(r['key'], r['label']) for r in gallery]})
    require(canonical == task['membership_sha256'], 'Ordered task membership SHA mismatch')
    task_summary.append({key: task[key] for key in ('name', 'query_count', 'gallery_count', 'distractor_identity_count', 'membership_sha256')})
PROTECTED[inventory_ref['path']] = inventory_ref['sha256']
PROTECTED[task_ref['path']] = task_ref['sha256']
checked('thirty tasks are exactly three seeds times ten full-gallery definitions; ordered member hashes recomputed', {'unique_images': 131062, 'tasks_per_seed': 10, 'total': 30, 'tasks': task_summary})

# Current interpreter is the exact registered environment. Distribution metadata
# is read without importing any of those installed distributions.
runtime = prepared['runtime']
observed = {'executable': sys.executable, 'python': sys.version, 'prefix': sys.prefix,
    'distributions': sorted([dist.metadata.get('Name', ''), dist.version] for dist in importlib.metadata.distributions()),
    'scientific_modules_imported': [name for name in ('torch', 'numpy', 'PIL', 'cv2', 'timm', 'albumentations') if name in sys.modules],
    'interpreter_sha256': sha(sys.executable), 'environment_type': runtime['environment_type']}
require(observed == runtime == prepared['membership']['runtime'], 'Actual stdlib interpreter/metadata differ from prepared locked environment')
checked('actual registered interpreter and installed distribution metadata match prepared runtime without scientific imports', {'interpreter_sha256': observed['interpreter_sha256'], 'distribution_count': len(observed['distributions'])})

future_paths = [TRAIN_EXEC/'runtime', EVAL/'runs', EVAL/'runtime', EVAL/'results']
for item in prepared['training_plans']:
    plan = read(item['plan']['path'])
    future_paths.extend(Path(plan[key]) for key in ('output_directory', 'profile_directory', 'profile_receipt_directory', 'training_receipt_directory'))
require(not any(path.exists() for path in future_paths), 'Unexpected actual future runtime/output exists; investigate before declaring unbound')
checked('all exact executor/evaluation runtime and twelve seed/profile/receipt directories remain absent', [str(path) for path in future_paths])
for path, digest in PROTECTED.items():
    require(sha(path) == digest, 'Read-only audit source changed during verification: '+path)
require(not ATTEMPTS and not BLOCKED.intersection(sys.modules), 'Scientific import attempted or loaded')
checked('all protected files including sealed ROOT_V2_RECHECK remain byte-identical; no science import', {'protected_files': len(PROTECTED), 'scientific_import_attempts': ATTEMPTS})

result = {'schema': 'dac-actual-prepared-independent-verification.v1', 'verified_utc': datetime.now(timezone.utc).isoformat(),
    'status': 'verified_prepared_waiting_for_training', 'passed': len(CHECKS), 'total': len(CHECKS), 'checks': CHECKS,
    'actual_prepared_path': str(PREPARED), 'actual_prepared_sha256': EXPECTED[str(PREPARED)],
    'prepared_payload_sha256': prepared['payload_sha256'], 'checkpoint_bindings_created': False,
    'checkpoints_bound': False, 'training_executed': False, 'evaluation_executed': False,
    'scientific_imports': [], 'gpu_called': False, 'subprocess_calls_by_audit': False,
    'sealed_or_author_files_modified': False, 'queue_or_release_edited': False,
    'validation_scope': 'actual frozen stdlib helper and file/ordered-membership verification; no image bytes, tensor contents, training, profile, bind, evaluate, or queue operations',
    'next_step': {'action': 'After all five admitted predecessor states actually complete and every owner exits, prepare the separately authorized immutable serial release and invoke the six-stage execution observer.',
        'not_ready_to_evaluate_now': True, 'required_future_inputs': ['actual DAC six-stage root release path and SHA', 'five exact completed predecessor status SHA/owner evidence', 'fresh shared GPU gate'],
        'interpreter': prepared['python'], 'entrypoint': str(TRAIN_EXEC/'run_six_stages.py'),
        'fixed_args': ['--spec', str(TRAIN_EXEC/'execution_spec.json'), '--spec-sha256', EXPECTED[str(TRAIN_EXEC/'execution_spec.json')]],
        'future_args_without_invented_values': ['--release-file <actual admitted root release>', '--release-sha256 <SHA of that real release>'],
        'execution_manifest_sha256_required_in_release': EXPECTED[str(TRAIN_EXEC/'PREPARATION_MANIFEST.json')],
        'after_training': 'Only after the real final completion and actual owner exits, use the frozen evaluation run/bind entry with an actual explicit controller release; the existing prepared manifest is already ready and must not be re-prepared in place.'}}
REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'report': str(REPORT), 'sha256': sha(REPORT), 'passed': len(CHECKS), 'total': len(CHECKS), 'checkpoints_bound': False}))
