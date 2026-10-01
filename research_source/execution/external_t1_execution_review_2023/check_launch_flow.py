"""Actual parent control flow with explicitly synthetic subprocess science."""
from contextlib import ExitStack
import importlib.abc
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

OUT = Path(__file__).resolve().parent
SRC = OUT.parent / 'external_efficiency_preparation/external_t1_execution_v1'
FORBIDDEN = {'torch', 'numpy', 'PIL', 'torchvision', 'transformers', 'scipy', 'matplotlib'}
class NoScience(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in FORBIDDEN: raise AssertionError('Forbidden science import')
sys.meta_path.insert(0, NoScience()); sys.path.insert(0, str(SRC))
import execution_contract as c
import run_seven_slots as r
native, k, b, life = c.runtime_helpers()
checks = []
def check(name, value):
    checks.append({'name': name, 'passed': bool(value)})
    if not value: raise AssertionError(name)

def fixture(root, mode):
    plan_record = k.write_new(root / 'plan.json', {'fixture_only': True})
    release_record = k.write_new(root / 'release.json', {'fixture_only': True})
    source_record = k.write_new(root / 'source.json', {'fixture_only': True})
    row = b.slots()[0]
    binding = {'row': row, 'checkpoint': {'fixture_only': True}}
    parent = {'pid': 990000, 'started_utc': '2026-09-14T10:00:00+00:00'}
    handles = []
    class FakeProcess:
        def __init__(self, command, **kwargs):
            self.pid = 990001; self._handle = 1; self.finished = False
            self.stdout = kwargs['stdout']; self.stderr = kwargs['stderr']
            self.stdout.write(b'explicit stdlib flow fixture, no scientific process\n')
            control = root / 'slot_0'
            self.request, self.request_record = c.bound(control / 'request.json')
            self.identity = {'schema': 'external-t1-slot-identity.v1', 'request': self.request_record,
                'pid': 990002, 'started_utc': '2026-09-14T10:00:02+00:00', 'cim_identity': {'ProcessId': 990002},
                'lineage': [{'pid': 990002, 'started_utc': '2026-09-14T10:00:02+00:00', 'parent_process_id': 990001},
                    {'pid': 990001, 'started_utc': '2026-09-14T10:00:01+00:00', 'parent_process_id': parent['pid']},
                    {**parent, 'parent_process_id': 0}]}
            self.identity_record = c.atomic_new_json(control / 'worker_identity.json', self.identity)
            handles.append(self)
        def poll(self): return 0 if self.finished else None
        def wait(self):
            control = root / 'slot_0'
            check('parent acknowledged actual identity before wait ' + mode, (control / 'parent_observed.json').exists())
            self.finished = True
            output = Path(self.request['native_output']); output.mkdir(parents=True)
            result = {'status': 'completed_external_t1_slot_only', 'owner': self.identity['cim_identity'],
                'run_id': row['run_id'], 'task_count': 10, 'checkpoint': binding['checkpoint'], 'fixture_only': True}
            nr = c.atomic_new_json(output / 'result.json', result)
            c.atomic_new_json(control / 'return_intent.json', {'request': self.request_record, 'identity': self.identity_record,
                'return_intent': 0, 'native_result': nr})
            if mode == 'release_changed': (root / 'release.json').write_text('{"changed":true}', encoding='utf-8')
            return 0
    class FakeHandle:
        def __init__(self, pid, existing_handle=None):
            self.pid = pid
            self.started_utc = '2026-09-14T10:00:01+00:00' if pid == 990001 else '2026-09-14T10:00:02+00:00'
        def exit_code(self): return 7 if mode == 'worker_exit7' and self.pid == 990002 else 0
        def close(self): pass
    old_record = k.record
    observed_closed = []
    def closed_record(path):
        if Path(path).name in ('stdout.log', 'stderr.log'):
            assert handles[0].finished and handles[0].stdout.closed and handles[0].stderr.closed
            observed_closed.append(Path(path).name)
        return old_record(path)
    with ExitStack() as stack:
        stack.enter_context(patch.object(c, 'NATIVE', root / 'native'))
        stack.enter_context(patch.object(r, 'HERE', root))
        stack.enter_context(patch.object(c, 'before_slot', return_value={'fixture_only': True}))
        stack.enter_context(patch.object(b, 'native_environment', return_value={'executable': str(k.PYTHON)}))
        stack.enter_context(patch.object(r.subprocess, 'Popen', FakeProcess))
        stack.enter_context(patch.object(life, 'ProcessObservation', FakeHandle))
        stack.enter_context(patch.object(k, 'process_snapshot', return_value=[]))
        stack.enter_context(patch.object(k, 'no_foreign_python', return_value=None))
        stack.enter_context(patch.object(k, 'self_and_verified_ancestors', return_value={os.getpid()}))
        stack.enter_context(patch.object(k, 'gpu_idle', return_value=[]))
        stack.enter_context(patch.object(k, 'record', side_effect=closed_record))
        try:
            result = r.launch_slot(0, binding, {'fixture_only': True}, plan_record, release_record, parent, root, 'fixture', source_record)
        except k.GateError:
            result = None
        if mode == 'valid':
            check('positive full parent launch control passes', result is not None and result['status'] == 'completed')
            check('all eight closed control artifacts recorded', len(result['closed_control_artifacts']) == 8)
            check('stdout and stderr hashed only after wait and close', sorted(observed_closed) == ['stderr.log', 'stdout.log'])
            lifecycle = k.read(result['lifecycle']['path'])
            check('actual lifecycle carries both exit codes', lifecycle['launcher_exit_code'] == lifecycle['actual_worker_exit_code'] == 0)
        else:
            check('full parent control rejects ' + mode, result is None)
            check('failure evidence retained ' + mode, (root / 'slot_0/controller_failure.json').is_file())
            check('failure not marked complete ' + mode, not (root / 'slot_0/lifecycle.json').exists())
            check('failed logs not sealed as success ' + mode, not observed_closed)

with tempfile.TemporaryDirectory(prefix='lgm_t1_parent_flow_') as temp:
    base = Path(temp).resolve()
    assert base.parent == Path(tempfile.gettempdir()).resolve()
    for mode in ('valid', 'worker_exit7', 'release_changed'):
        root = base / mode; root.mkdir()
        fixture(root, mode)
check('no scientific imports or actual scientific subprocess', not FORBIDDEN.intersection(sys.modules))
report = {'status': 'passed', 'schema': 'external-t1-parent-flow-review.v1', 'checks': checks,
    'source_files': {str(p): k.sha(p) for p in SRC.glob('*.py')}, 'actual_launch_slot_control_exercised': True,
    'subprocess_and_resource_gates_stubbed': True, 'real_scientific_execution_performed': False, 'utc': k.now()}
record = k.write_new(OUT / 'PARENT_FLOW_REVIEW.json', report)
print(json.dumps({'checks_passed': len(checks), 'report': record}, ensure_ascii=True))
