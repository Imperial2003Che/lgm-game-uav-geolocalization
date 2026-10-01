"""Freeze only the reviewed v3 path-binding repair; never release or evaluate."""
import ast
import importlib.abc
from pathlib import Path
import sys
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
BLOCKED = {'torch', 'numpy', 'scipy', 'PIL', 'cv2', 'timm', 'albumentations', 'sklearn', 'matplotlib', 'pptx'}
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in BLOCKED:
            raise RuntimeError('Scientific imports forbidden in v3 metadata preparation: ' + fullname)
sys.meta_path.insert(0, Guard())
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
from protocol import *
from run_evaluation import read_prepared, validate_controller_release

path = HERE / 'preparations/frozen_three_seed_final_v3/manifest.json'
if sha(path) != '305c2b9b56fb6bde1781f459467a6718b9f7ed1df9779bcc7d4a209ca2244317':
    raise RuntimeError('v3 prepared contract hash changed')
for output in ('controller_release_template.json', 'QUEUE_HANDOFF.json', 'PREPARATION_MANIFEST.json', 'V3_BINDING_REVIEW.json'):
    if (HERE / output).exists():
        raise RuntimeError('Refusing to overwrite a v3 frozen artifact: ' + output)
if (HERE / 'controller_release.json').exists() or (HERE / 'results').exists() or (HERE / 'runs').exists():
    raise RuntimeError('v3 preparation must have no active release or execution results')
prepared = read_prepared(path)
prior = EXECUTION / 'camp_independent_evaluation'
old = load(prior / 'preparations/frozen_three_seed_final_v2/manifest.json')
checks = []
def check(name, value):
    if not value:
        raise RuntimeError(name)
    checks.append({'name': name, 'passed': True})

allowed = {'created_utc', 'payload_sha256', 'sources', 'training_plans', 'training_execution_plan'}
check('Only preparation provenance fields differ; all scientific settings, membership, runtime and selection rules identical',
      {k:v for k,v in old.items() if k not in allowed} == {k:v for k,v in prepared.items() if k not in allowed})
check('Original strict 395-state model loader is byte-identical',
      (HERE/'camp_independent_model.py').read_bytes() == (prior/'camp_independent_model.py').read_bytes())
check('No planned checkpoint hash assigned', all(x['checkpoint_sha256'] is None for x in prepared['training_plans']))
check('Exact seeds and task count retained', prepared['seeds'] == [1,2,3] and prepared['task_count'] == 30)
check('New train preparation and execution SHA bound', TRAIN_PREPARATION_SHA == '12747158ce2647474c6d24688ba3ebb872ac137118fab7aefd1c1e0ecfad40ec'
      and prepared['training_execution_plan']['sha256'] == 'd7ba4f15a076131b464cb39a04ec869444a8e4711348929c6233e8f083df0dc2')
for seed, item in zip(SEEDS, prepared['training_plans']):
    check('Seed '+str(seed)+' uses v2 input and unchanged future output',
          Path(item['plan']['path']) == EXECUTION/'camp_training_inputs_v2'/f'seed_{seed}_plan.json'
          and Path(item['output_directory']) == EXECUTION/'camp_independent_runs'/f'seed_{seed}')
derivation = load(HERE/'SOURCE_DERIVATION.json')
for item in derivation['files']:
    check(item['name'] + ' prior and derived bytes still pinned',
          sha(item['old_path']) == item['old_sha256'] and sha(item['new_path']) == item['new_sha256'])
    new_bytes = Path(item['new_path']).read_bytes()
    for change in reversed(item['replacement_counts']):
        new_bytes = new_bytes.replace(change['to'].encode(), change['from'].encode())
    check(item['name'] + ' reverse binding substitutions reconstruct exact original',
          new_bytes == Path(item['old_path']).read_bytes())
light = load(HERE/'LIGHTWEIGHT_REVIEW.json')
check('All inherited strict-schema/process/release mocks passed', light['check_count'] == 53 and light['status'] == 'passed_standard_library_only')
template = {'schema':CONTROLLER_RELEASE_SCHEMA, 'allow_cuda':False, 'prepared_sha256':sha(path),
            'latest_baseline_plan_sha256':prepared['latest_baseline_plan']['sha256'],
            'training_execution_plan_sha256':prepared['training_execution_plan']['sha256'],
            'binding_policy':BINDING_POLICY, 'seeds':list(SEEDS), 'task_count':30}
with patch('run_evaluation.load', return_value=template):
    try:
        validate_controller_release(prepared, path, HERE/'not_an_active_release.json')
    except RuntimeError:
        check('False release template cannot authorize evaluation', True)
    else:
        raise RuntimeError('False release template was accepted')
check('No scientific modules imported by v3 preparation', not any(x.split('.')[0] in BLOCKED for x in sys.modules))
save(HERE/'V3_BINDING_REVIEW.json', {
    'schema':'camp-independent-evaluation-v3-binding-review.v1', 'status':'passed_standard_library_only',
    'created_utc':utc(), 'checks':checks, 'check_count':len(checks), 'inherited_check_count':53,
    'prepared':artifact(path), 'old_prepared':artifact(prior/'preparations/frozen_three_seed_final_v2/manifest.json'),
    'model_loaded':False, 'GPU_executed':False, 'evaluation_results_created':False, 'active_release_created':False})
save(HERE/'controller_release_template.json', template)
source_paths = [Path(x['path']) for x in prepared['sources']['files']]
source_paths += [path, Path(prepared['training_execution_plan']['path']), Path(prepared['latest_baseline_plan']['path'])]
source_paths += [Path(x['plan']['path']) for x in prepared['training_plans']]
source_paths += [Path(prepared['membership'][key]['path']) for key in ('source_manifest','inventory','tasks')]
source_paths += [HERE/name for name in ('check_lightweight.py','LIGHTWEIGHT_REVIEW.json','SOURCE_DERIVATION.json','SOURCE_DERIVATION.patch','V3_BINDING_REVIEW.json')]
command = [prepared['python'],'-B',str(HERE/'run_evaluation.py'),'run','--prepared',str(path),
           '--training-completion',str(EXECUTION/'camp_training_execution_v2/status.json'),
           '--controller-release',str(HERE/'controller_release.json'),
           '--output-directory',str(HERE/'runs/registered_three_seed_final')]
job = {'id':'camp_independent_3seed_full_gallery_30tasks', 'command':command, 'cwd':str(HERE),
       'source_sha256':{str(p.resolve()):sha(p) for p in source_paths}}
save(HERE/'QUEUE_HANDOFF.json', {
    'schema':'camp-independent-evaluation-handoff.v1','status':'prepared_not_registered','created_utc':utc(),
    'prepared':artifact(path),'job':job,'missing_release_to_create_and_pin':str(HERE/'controller_release.json'),
    'template':artifact(HERE/'controller_release_template.json'),
    'checkpoint_hashes':'No future weight hashes assigned; bind only actual all-three completed and exited training outputs',
    'execution_gate':'Both latest author jobs, all three independent complete final fits and actual process exits required',
    'scientific_imports_during_preparation':[],'GPU_executed':False,'evaluation_results_created':False,
    'repair':'Only training v2 path/hash binding; official model and all strict evaluation science unchanged'})
names = ('protocol.py','camp_independent_model.py','run_evaluation.py','check_lightweight.py','finalize_handoff_v3.py',
         'README.md','LIGHTWEIGHT_REVIEW.json','V3_BINDING_REVIEW.json','SOURCE_DERIVATION.json',
         'SOURCE_DERIVATION.patch','controller_release_template.json','QUEUE_HANDOFF.json')
freeze = seal({'schema':'camp-independent-evaluation-source-freeze.v1','created_utc':utc(),'status':'prepared_not_registered',
               'files':[artifact(HERE/n) for n in names],'prepared':artifact(path),'source_evidence':source_evidence(),
               'check_count':53+len(checks),'scientific_imports':[],'GPU_executed':False,'active_release_created':False})
save(HERE/'PREPARATION_MANIFEST.json', freeze)
print(__import__('json').dumps({'prepared_sha256':sha(path),'handoff_sha256':sha(HERE/'QUEUE_HANDOFF.json'),
      'preparation_manifest_sha256':sha(HERE/'PREPARATION_MANIFEST.json'),'new_check_count':len(checks),'total_check_count':53+len(checks)},ensure_ascii=True))
