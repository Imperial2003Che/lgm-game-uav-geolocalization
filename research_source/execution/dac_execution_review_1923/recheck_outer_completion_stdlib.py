"""Focused independent DAC6 outer-completion recheck; stdlib and process mocks only."""
import argparse
from contextlib import ExitStack
from copy import deepcopy
import importlib.abc
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument('--runner-sha256', required=True)
args = parser.parse_args()
OUT = Path(__file__).resolve().parent
SOURCE = OUT.parent / 'dac_training_execution_v2'
FIX = OUT / 'recheck_fixtures'
FIX.mkdir(exist_ok=True)
BLOCKED = {'torch', 'torchvision', 'numpy', 'PIL', 'cv2', 'timm', 'scipy', 'sklearn', 'albumentations', 'transformers', 'tensorboard'}
ATTEMPTS = []
sys.dont_write_bytecode = True
class NoScience(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in BLOCKED:
            ATTEMPTS.append(fullname)
            raise RuntimeError('Scientific import forbidden: ' + fullname)
sys.meta_path.insert(0, NoScience())
sys.path.insert(0, str(SOURCE))
import dac6_contracts as d
import run_six_stages as run

CHECKS = []
def require(value, message='Independent assertion failed'):
    if not value:
        raise AssertionError(message)
def check(name, fn):
    try:
        CHECKS.append({'name': name, 'passed': True, 'detail': fn()})
    except BaseException as error:
        CHECKS.append({'name': name, 'passed': False, 'error': repr(error)})

CORE_EXPECTED = {
    'dac6_contracts.py': 'e35c59ec784a96062cafe905dcf15943d7d23780e98c296b0f9fd5523d38a6e3',
    'run_six_stages.py': args.runner_sha256,
    'stage_entry.py': '1fa5f47623a1341b0c3637fc2b2f161e38a8816e614ec04648a6cdea05322232',
    'execution_spec.json': '069c8531fd73de799b47d538ff95f11bedab9a720f29dc607bebe5d397b7d78e',
}
INITIAL = {name: d.sha(SOURCE / name) for name in CORE_EXPECTED}
require(INITIAL == CORE_EXPECTED, 'Do not test a different candidate')
REAL_SPEC = d.spec_bound(SOURCE / 'execution_spec.json', CORE_EXPECTED['execution_spec.json'])

def outer_case(kind='valid', actual_code=0, launcher_code=0):
    root = FIX / (kind + '_' + d.c.utc().replace(':', '').replace('.', ''))
    root.mkdir()
    stamp = '2026-09-14T00:00:00+00:00'
    rows = deepcopy(REAL_SPEC.value['jobs'])
    fake_spec = SimpleNamespace(path=root/'test_spec.json', sha256='a'*64,
        value={'jobs': rows, 'status_path': str(root/'runtime/status.json'),
               'completion_path': str(root/'runtime/completion_manifest.json')}, unchanged=lambda: None)
    release_path = root/'test_root_release.json'
    d.c.write(release_path, {'test_contract_only': True, 'not_a_release': True})
    release = d.c.Bound.load(release_path, d.sha(release_path))
    verified = []
    events = []
    verifications = {row['id']: {'mock_artifact_result': row['id'], 'not_scientific_evidence': True} for row in rows}
    class Process:
        def __init__(self, *args, **kwargs):
            self.pid = 101
            self._handle = 1
            self.returncode = None
            request = d.c.read(root/'runtime/coordinator_request.json')
            identity = {'schema': 'dac-actual-worker-identity.v2', 'pid': 202, 'started_utc': stamp,
                'plan_sha256': fake_spec.sha256, 'release_sha256': release.sha256,
                'lineage': [{'pid': 202, 'started_utc': stamp, 'parent_process_id': 101},
                    {'pid': 101, 'started_utc': stamp, 'parent_process_id': request['parent_pid']},
                    {'pid': request['parent_pid'], 'started_utc': stamp, 'parent_process_id': 999}]}
            d.c.write(root/'runtime/coordinator_identity.json', identity)
        def poll(self):
            return self.returncode
        def wait(self):
            events.append('launcher_wait_returned')
            self.returncode = launcher_code
            records = [{**row, 'status': 'completed', 'exit_code': 0,
                'controller_pid': 202, 'controller_started_utc': stamp,
                'control_receipt_sha256': str(i+1)*64,
                'artifact_verification': deepcopy(verifications[row['id']])} for i, row in enumerate(rows)]
            state = {'schema': 'dac-six-stage-execution-status.v2', 'status': 'completed', 'exit_code': 0,
                'controller_pid': 202, 'controller_started_utc': stamp,
                'finished_utc': '2026-09-14T00:01:00+00:00',
                'execution_spec_path': str(fake_spec.path), 'execution_spec_sha256': fake_spec.sha256,
                'execution_manifest_sha256': 'c'*64, 'root_release_path': str(release.path),
                'root_release_sha256': release.sha256, 'jobs': records}
            seeds = [{'seed': row['seed'], 'plan_path': row['plan_path'], 'plan_sha256': row['plan_sha256'],
                'output_directory': row['output_directory'], 'control_receipt_path': record['control_receipt_path'],
                'control_receipt_sha256': record['control_receipt_sha256'],
                'artifacts': deepcopy(verifications[row['id']])}
                for row, record in zip(rows, records) if row['stage'] == 'train']
            if kind == 'truncated_five_jobs':
                state['jobs'] = records[:5]
            elif kind == 'wrong_job_order':
                state['jobs'] = records[1:] + records[:1]
            elif kind == 'wrong_status_schema':
                state['schema'] = 'wrong-schema'
            elif kind == 'wrong_state_release':
                state['root_release_sha256'] = 'f'*64
            elif kind == 'wrong_state_spec':
                state['execution_spec_sha256'] = 'f'*64
            elif kind == 'wrong_state_controller':
                state['controller_pid'] = 303
            d.c.write(root/'runtime/status.json', state)
            candidate = {'schema': 'dac-six-stage-completion.v2', 'execution_spec_sha256': fake_spec.sha256,
                'execution_manifest_sha256': 'c'*64, 'status_sha256': d.sha(root/'runtime/status.json'),
                'training_artifacts': seeds}
            if kind == 'empty_artifacts':
                candidate['training_artifacts'] = []
            elif kind == 'wrong_candidate_manifest':
                candidate['execution_manifest_sha256'] = 'f'*64
            elif kind == 'altered_seed_artifact':
                candidate['training_artifacts'][2]['artifacts'] = {'wrong_artifact': True}
            elif kind == 'extra_candidate_field':
                candidate['unexpected'] = True
            d.c.write(root/'runtime/candidate_completion.json', candidate)
            return launcher_code
    class Handle:
        def __init__(self, pid, existing_handle=None):
            self.pid = pid
            self.started_utc = stamp
        def exit_code(self):
            events.append('actual_worker_exit_checked')
            return actual_code
        def close(self):
            pass
    def verify_stage(row, record):
        verified.append([row['id'], record['id']])
        if kind == 'status_mutates_during_verify' and len(verified) == 6:
            state = d.c.read(root/'runtime/status.json')
            state['post_admission_mutation'] = True
            d.c.write(root/'runtime/status.json', state)
        return deepcopy(verifications[row['id']])
    with ExitStack() as stack:
        for obj, name, value in ((d, 'HERE', root), (d, 'spec_bound', lambda *a: fake_spec),
            (d, 'release_bound', lambda *a: release), (d, 'own_manifest', lambda: 'c'*64),
            (d.g, 'ProcessObservation', Handle), (run.subprocess, 'Popen', Process),
            (d, 'verify_stage', verify_stage),
            (d.g, 'process_started', lambda pid: stamp if pid == run.os.getpid() else None)):
            stack.enter_context(patch.object(obj, name, value))
        error = None
        try:
            run.supervise_coordinator(str(fake_spec.path), fake_spec.sha256, str(release.path), release.sha256)
        except BaseException as caught:
            error = repr(caught)
    completion_path = root/'runtime/completion_manifest.json'
    lifecycle = d.c.read(root/'runtime/controller_lifecycle.json')
    result = {'case': kind, 'actual_code': actual_code, 'launcher_code': launcher_code,
        'completion_written': completion_path.exists(), 'lifecycle_status': lifecycle['status'],
        'verification_calls': verified, 'events': events, 'error': error,
        'candidate_retained': (root/'runtime/candidate_completion.json').exists(),
        'fixture_directory': str(root), 'all_processes_and_stage_artifacts_mocked': True}
    if completion_path.exists():
        result['final_training_seed_ids'] = [x['seed'] for x in d.c.read(completion_path)['training_artifacts']]
    return result

def positive():
    result = outer_case()
    require(result['completion_written'] and result['lifecycle_status'] == 'completed' and len(result['verification_calls']) == 6)
    require(result['final_training_seed_ids'] == [1, 2, 3] and result['error'] is None)
    return result
def negative(kind, actual=0, launcher=0):
    result = outer_case(kind, actual, launcher)
    require(not result['completion_written'] and result['lifecycle_status'] == 'failed' and result['candidate_retained'])
    return result

check('complete producer-shaped outer candidate reaches final seal after two actual exit0 observations', positive)
for kind in ('truncated_five_jobs', 'empty_artifacts', 'wrong_job_order', 'wrong_status_schema',
             'wrong_state_release', 'wrong_state_spec', 'wrong_state_controller',
             'wrong_candidate_manifest', 'altered_seed_artifact', 'extra_candidate_field', 'status_mutates_during_verify'):
    check('outer refuses ' + kind, lambda kind=kind: negative(kind))
check('outer still refuses actual coordinator exit7 with launcher exit0', lambda: negative('valid', 7, 0))
check('outer still refuses actual coordinator exit0 with launcher exit7', lambda: negative('valid', 0, 7))
FINAL = {name: d.sha(SOURCE/name) for name in CORE_EXPECTED}
check('core bytes unchanged throughout recheck', lambda: require(FINAL == INITIAL))
check('no science import or real executor runtime', lambda: require(not ATTEMPTS and not BLOCKED.intersection(sys.modules) and not (SOURCE/'runtime').exists()))
report = {'schema': 'dac-six-stage-independent-outer-recheck.v1', 'generated_utc': d.c.utc(),
    'passed': sum(x['passed'] for x in CHECKS), 'total': len(CHECKS), 'checks': CHECKS,
    'core_source_before': INITIAL, 'core_source_after': FINAL,
    'previous_checks_path': str(OUT/'CANDIDATE_REVIEW_CHECKS.json'),
    'previous_checks_sha256': d.sha(OUT/'CANDIDATE_REVIEW_CHECKS.json'),
    'unchanged_science_control_inputs_checks_reused': True,
    'science_import_attempts': ATTEMPTS, 'actual_scientific_execution': False,
    'actual_processes_or_GPU_launched': False, 'active_release_created': False,
    'author_files_modified': False, 'real_runtime_created': False}
d.c.write(OUT/'OUTER_COMPLETION_RECHECK.json', report)
print(json.dumps({'passed': report['passed'], 'total': report['total'], 'failures': [c for c in CHECKS if not c['passed']]}))
raise SystemExit(0 if report['passed'] == report['total'] else 1)
