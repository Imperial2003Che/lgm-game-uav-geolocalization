"""Actual source checks and bounded command/control regression for the addendum."""
import ast
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch
import compatibility as c

HERE = Path(__file__).resolve().parent
EXPECTED = '0c4217fefb33d6550bda2300bc201f1c869da0b8d5ff02d45ae7af45b7ef6d70'

def main():
    tests = []
    def check(name, operation):
        operation()
        tests.append({'name': name, 'status': 'passed'})
    def reject(operation):
        try:
            operation()
        except (RuntimeError, FileNotFoundError, KeyError):
            return
        raise AssertionError('Expected rejection')
    a = c.Addendum(EXPECTED)
    check('all_11_actual_addendum_sources', a.verify_sources)
    check('wrong_addendum_hash_rejected', lambda: reject(lambda: c.Addendum('0' * 64)))
    for family in ('latest', 'independent'):
        plan = a.plan(family).value()
        check(family + '_original_plan_and_controller', lambda: a.check_plan(family, plan, a.registry['controllers'][family]['path']))
        changed = copy.deepcopy(plan)
        changed['jobs'][0]['command'].append('--unregistered')
        check(family + '_changed_plan_rejected', lambda: reject(lambda: a.check_plan(family, changed, a.registry['controllers'][family]['path'])))
        for job in plan['jobs']:
            actual = a.command(family, job)
            roles = [r for r, row in a.registry['roles'].items() if row['family'] == family and row['job_id'] == job['id']]
            if roles:
                assert actual[:2] == [job['command'][0], '-B']
                assert actual[2:] == [str(HERE / 'run_evaluator.py'), '--role', roles[0], '--addendum-sha256', EXPECTED]
            else:
                assert actual == job['command']
        tests.append({'name': family + '_all_exact_launch_commands', 'status': 'passed'})
        source = Path(a.registry['controllers'][family]['path']).read_text(encoding='utf-8')
        original = Path(a.registry['controllers'][family]['original_path']).read_text(encoding='utf-8')
        old_ast, new_ast = ast.parse(original), ast.parse(source)
        old_functions = {n.name: ast.dump(n) for n in old_ast.body if isinstance(n, ast.FunctionDef)}
        new_functions = {n.name: ast.dump(n) for n in new_ast.body if isinstance(n, ast.FunctionDef)}
        changed_functions = {name for name in old_functions if old_functions[name] != new_functions[name]}
        assert changed_functions == {'main', 'check_plan'}
        assert "Popen(job['execution_command']" in source
        assert source.index("job['execution_command'] =") < source.index('save(path, state)', source.index("job['execution_command'] =")) < source.index("Popen(job['execution_command']")
        tests.append({'name': family + '_predecessor_process_resource_state_helpers_AST_unchanged', 'status': 'passed'})
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / 'snapshot.json'
        path.write_bytes(b'\xef\xbb\xbf{\r\n"x": 1\r\n}\r\n')
        snap = c.Snapshot(path, c.sha(path))
        assert snap.value() == {'x': 1}
        path.write_bytes(b'{"x":1}')
        check('same_JSON_different_raw_bytes_rejected', lambda: reject(snap.unchanged))
    with patch.dict(sys.modules, {'torch': object()}):
        check('scientific_namespace_rejected', lambda: reject(c.no_science))
    actual_rows = []
    # Native isolated subprocesses perform actual source reading but never call evaluation.
    python = a.role_job('camp_author')[1]['command'][0]
    for role in ('camp_author', 'dac_author', 'camp_independent'):
        result = subprocess.run([python, '-B', '-X', 'utf8', str(HERE / 'run_evaluator.py'),
                '--role', role, '--addendum-sha256', EXPECTED, '--check-sources'],
                capture_output=True, text=True, encoding='utf-8', check=True, timeout=120,
                creationflags=subprocess.CREATE_NO_WINDOW)
        row = json.loads(result.stdout)
        assert row['check_sources_only'] is True and len(row['aliases']) == 2
        actual_rows.append(row)
        tests.append({'name': role + '_actual_native_original_source_read_two_aliases', 'status': 'passed'})
    for family in ('latest', 'independent'):
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', a.registry['controllers'][family]['path'],
                '--plan', str(a.plan(family).path), '--addendum-sha256', EXPECTED, '--check-plan'],
                capture_output=True, text=True, encoding='utf-8', check=True, timeout=120,
                creationflags=subprocess.CREATE_NO_WINDOW)
        row = json.loads(result.stdout)
        assert row['plan_sha256'] == a.plan(family).digest
        tests.append({'name': family + '_actual_controller_checks_all_queued_sources_and_native_runtime_metadata', 'status': 'passed'})
    c.no_science()
    report = {'status': 'source_control_checks_passed_no_scientific_execution', 'addendum_sha256': EXPECTED,
              'tests': tests, 'test_count': len(tests), 'actual_entry_preflights': actual_rows,
              'scientific_results_created': False, 'registered': False, 'launched': False,
              'review_independence': 'root self review; no independent agent available'}
    output = HERE / 'ADDENDUM_REVIEW.json'
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'report': str(output), 'sha256': c.sha(output), 'test_count': len(tests)}))

if __name__ == '__main__':
    main()
