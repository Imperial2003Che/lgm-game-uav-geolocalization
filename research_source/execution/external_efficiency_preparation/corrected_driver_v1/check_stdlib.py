"""Only standard-library/AST/mock checks. No checkpoint/model/NumPy/GPU execution."""
from __future__ import annotations

import ast
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import contract as k
import driver
import science

checks = []

def ok(name, value):
    if not value:
        raise AssertionError(name)
    checks.append({'check': name, 'passed': True})

def refuses(name, function):
    try:
        function()
    except (k.GateError, FileExistsError, ValueError, KeyError):
        ok(name, True)
    else:
        raise AssertionError('Did not refuse: ' + name)

def main():
    trees = {}
    for path in sorted(HERE.glob('*.py')):
        trees[path.name] = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        compile(trees[path.name], str(path), 'exec')
    ok('all new Python sources parse and compile without executing code', True)
    forbidden = {'torch', 'numpy', 'PIL', 'matplotlib', 'transformers', 'torchvision', 'scipy'}
    ok('import contract/driver/science does not load any scientific module', not forbidden.intersection(sys.modules))
    for filename in ('contract.py', 'driver.py'):
        imports = [node for node in ast.walk(trees[filename]) if isinstance(node, (ast.Import, ast.ImportFrom))]
        names = {alias.name.split('.')[0] for node in imports if isinstance(node, ast.Import) for alias in node.names}
        names |= {node.module.split('.')[0] for node in imports if isinstance(node, ast.ImportFrom) and node.module}
        ok(filename + ' contains no scientific imports even inside functions', not names.intersection(forbidden))
    worker = next(n for n in trees['driver.py'].body if isinstance(n, ast.FunctionDef) and n.name == 'worker')
    import_line = next(n.lineno for n in ast.walk(worker) if isinstance(n, ast.ImportFrom) and n.module == 'science')
    for guard in ('verify_plan', 'predecessors', 'resource_gate', 'gpu_idle', 'no_foreign_python', 'verify_release'):
        lines = [n.lineno for n in ast.walk(worker) if isinstance(n, ast.Call)
                 and ((isinstance(n.func, ast.Attribute) and n.func.attr == guard)
                      or (isinstance(n.func, ast.Name) and n.func.id == guard))]
        ok('worker ' + guard + ' precedes science import', lines and max(lines) < import_line)
    source = (HERE / 'science.py').read_text(encoding='utf-8')
    for requirement in ('local_files_only=True', 'use_safetensors=False', 'output_loading_info=True',
                        'validate_completed_run', '_verify_full_gallery_metrics', 'load_model(valid, device)',
                        'core.encode_records', 'core.rank_task', 'probability_parity', 'actual_online_query_descriptor.npy'):
        ok('scientific implementation contains real path: ' + requirement, requirement in source)
    ok('does not call old autograd-enabled benchmark', 'helpers.benchmark_' not in source)
    ok('corrected_v1 byte pin preserved', k.sha(k.COMPONENTS / 'measurement_components.py') == k.COMPONENT_SHA)
    ok('four cases have fixed dataset/variant/seed selection', k.CASES == (
        ('university1652', 'visual'), ('university1652', 'full'), ('sues200', 'visual'), ('sues200', 'full')))
    with tempfile.TemporaryDirectory(prefix='t6_stdlib_', dir=HERE) as temporary:
        temp = Path(temporary)
        artifact = k.write_new(temp / 'truth.json', {'actual': 1})
        ok('immutable artifact verifies', k.verify_record(artifact) == artifact)
        refuses('immutable output overwrite fails', lambda: k.write_new(temp / 'truth.json', {'actual': 2}))
        (temp / 'truth.json').write_text('{}', encoding='utf-8')
        refuses('source tampering fails', lambda: k.verify_record(artifact))
        plan = k.write_new(temp / 'plan.json', {'case': 'not executed'})
        k.write_new(temp / 'inactive.json', {'allow_run': False, 'plan': plan})
        refuses('inactive release cannot execute', lambda: driver.verify_release(temp / 'inactive.json', temp / 'plan.json'))
        k.write_new(temp / 'wrong.json', {'allow_run': True, 'plan': {**plan, 'sha256': '0' * 64}})
        refuses('wrong plan SHA cannot execute', lambda: driver.verify_release(temp / 'wrong.json', temp / 'plan.json'))
        k.write_new(temp / 'active.json', {'allow_run': True, 'plan': plan})
        ok('exact explicit release binding can pass a mock plan only', driver.verify_release(temp / 'active.json', temp / 'plan.json')['allow_run'])
        refuses('output traversal rejected', lambda: k.scoped_new(temp, '../escape'))
        k.scoped_new(temp, 'fresh')
        refuses('existing output directory rejected', lambda: k.scoped_new(temp, 'fresh'))
        class ParityError(Exception):
            evidence = {'passed': False, 'different_element_count': 3, 'mock_test_only': True}
        try:
            raise ParityError('mock parity mismatch, not scientific data')
        except ParityError as error:
            driver.fail(temp / 'failure_fixture', error, 'mock_only')
        failed = k.read(temp / 'failure_fixture' / 'failure.json')
        ok('failure preserves actual exception evidence without changing parity', failed['actual_scientific_failure_evidence'] == ParityError.evidence)
    body = {'x': 1}
    sealed = {**body, 'payload_sha256': k.canonical(body)}
    k.verify_seal(sealed)
    ok('canonical seal accepts unchanged payload', True)
    refuses('canonical seal rejects changed payload', lambda: k.verify_seal({**sealed, 'x': 2}))
    rows = [{'ProcessId': 11, 'ParentProcessId': 1, 'Name': 'python.exe', 'CreatedUtc': '2026-09-14T09:00:00+00:00', 'ExecutablePath': 'fixed'},
            {'ProcessId': 12, 'ParentProcessId': 11, 'Name': 'python.exe', 'CreatedUtc': '2026-09-14T09:00:01+00:00', 'ExecutablePath': 'fixed'}]
    ok('absent predecessor PID is exited', k.exited(55, '2026-09-14T09:00:00+00:00', rows))
    ok('live predecessor owner is rejected', not k.exited(11, '2026-09-14T09:00:00+00:00', rows))
    ok('slow spawn cannot be mistaken for PID reuse', not k.exited(11, '2026-09-14T08:00:00+00:00', rows))
    ok('new PID creation after completed task end distinguishes reuse', k.exited(11, '2026-09-14T08:00:00+00:00', rows, '2026-09-14T08:59:00+00:00'))
    refuses('missing process start cannot be treated as exit', lambda: k.exited(55, None, rows))
    refuses('boolean PID rejected', lambda: k.exited(True, '2026-09-14T09:00:00+00:00', rows))
    refuses('naive timestamp rejected', lambda: k.exited(55, '2026-09-14T09:00:00', rows))
    refuses('unknown orphan Python process rejected', lambda: k.no_foreign_python(rows, {11}))
    k.no_foreign_python(rows, {11, 12})
    ok('only actual allowed process identities can pass global Python check', True)
    refuses('nested live surviving child prevents exit', lambda: k.assert_nested_owners_exited(
        {'started_utc': '2026-09-14T09:00:00+00:00', 'nested': {'surviving_child_pid': 11}}, rows))
    expected = [{'id': 'a', 'command': ['fixed.py'], 'source_sha256': {'fixed.py': 'abc'}}]
    observed = [{**expected[0], 'status': 'completed', 'exit_code': 0}]
    k.check_job_definitions(observed, expected)
    ok('exact completed job binding accepted', True)
    for label, change in (('nonzero exit', {'exit_code': 2}), ('bool exit', {'exit_code': False}),
                          ('pending', {'status': 'pending'}), ('changed command', {'command': ['other.py']}),
                          ('changed source', {'source_sha256': {}})):
        refuses('job rejects ' + label, lambda change=change: k.check_job_definitions([{**observed[0], **change}], expected))
    refuses('duplicate job registry rejected', lambda: k.check_job_definitions(observed * 2, expected))
    fixture_plan = {'cases': [{'evaluation_dir': 'mock-only', 'variant': 'full',
        'checkpoint': {'bytes': 1000}}], 'clip': {'files': [{'path': 'pytorch_model.bin', 'bytes': 2000}]}}
    with patch.object(k, 'read', return_value={'results': {'task': {'queries': 2, 'gallery': 3}}}):
        budget = k.resource_budget(fixture_plan, 0)
    ok('resource estimate derives exact known arrays and archive copies',
       budget['host_required_available_bytes'] == 2000 + 4000 + 3 * 5 * 512 * 4 + 8 * 6 + 1024**3)
    ok('resource estimate is feasible on 16 GiB test host', budget['host_required_available_bytes'] < 16 * 1024**3)
    ok('single-process extraction prevents eight cache replicas', budget['descriptor_extraction_workers'] == 0)
    with patch.object(k, 'frozen_sources', return_value={}), patch.object(k, 'process_snapshot', return_value=[]), \
         patch.object(k, 'predecessors', side_effect=k.GateError('unfinished fixture')), \
         patch.object(k, 'actual_case_files') as checkpoint_binding:
        refuses('unfinished predecessor stops preparation before checkpoint binding', lambda: k.prepare('mock_no_output'))
        ok('no future checkpoint binding after blocked predecessor', not checkpoint_binding.called)
    with patch.dict(os.environ, {'CUDA_VISIBLE_DEVICES': '1', 'PYTHONPATH': 'untrusted', 'PYTHONHOME': 'untrusted'}):
        env = driver.clean_environment()
        ok('child clears Python and CUDA remapping inheritance', all(x not in env for x in ('PYTHONPATH', 'PYTHONHOME', 'CUDA_VISIBLE_DEVICES')))
        ok('child forces offline model resolution', env['HF_HUB_OFFLINE'] == env['TRANSFORMERS_OFFLINE'] == '1')
    ok('no scientific library imported after all checks', not forbidden.intersection(sys.modules))
    report = {'schema': 'corrected-primary-driver-stdlib-review.v1', 'created_utc': k.now(),
        'checks': checks, 'passed': len(checks), 'failed': 0, 'scientific_imports': [],
        'scientific_execution_performed': False, 'GPU_or_model_test_performed': False,
        'mock_values_are_test_fixtures_not_measurements': True,
        'source_files': [k.record(p) for p in sorted(HERE.glob('*.py'))]}
    k.write_new(HERE / 'STDLIB_REVIEW.json', report)
    print(json.dumps({'passed': len(checks), 'failed': 0, 'scientific_execution': False}))

if __name__ == '__main__':
    main()
