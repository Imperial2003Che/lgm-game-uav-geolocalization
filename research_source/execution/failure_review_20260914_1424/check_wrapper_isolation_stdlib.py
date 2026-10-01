"""Independent static and mocked lifecycle review; no real subprocesses/imports."""
import ast
import copy
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'continue_formal_matrix.py'
BACKUP = HERE.parent / 'memory_recovery_20260914_1424' / 'controllers' / 'continue_formal_matrix.py'
if not BACKUP.exists():
    manifest = json.loads((HERE.parent / 'memory_recovery_20260914_1424' / 'backup_manifest.json').read_text(encoding='utf-8'))
    def find(value):
        if isinstance(value, dict):
            if str(value.get('source', '')).endswith('continue_formal_matrix.py'):
                return Path(value['backup'])
            for child in value.values():
                result = find(child)
                if result: return result
        elif isinstance(value, list):
            for child in value:
                result = find(child)
                if result: return result
    BACKUP = find(manifest)
    assert BACKUP and BACKUP.is_file()

def dump(value): return ast.dump(value, include_attributes=False)
def fn(tree, name): return next(x for x in ast.walk(tree) if isinstance(x, ast.FunctionDef) and x.name == name)
old, new = [ast.parse(p.read_text(encoding='utf-8-sig')) for p in (BACKUP, SOURCE)]
checks=[]
def check(name, value):
    assert value, name
    checks.append(name)
for name in ('verify_training_environment', 'sha', 'save', 'utc', 'resource_command', 'monitored_run'):
    check(name + '_AST_unchanged', dump(fn(old, name)) == dump(fn(new, name)))
main=fn(new,'main')
locking_line=next(x.lineno for x in ast.walk(main) if isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr=='locking')
probe_line=next(x.lineno for x in ast.walk(main) if isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id=='verify_training_environment_isolated')
check('matrix_lock_before_import_probe', locking_line < probe_line)
def legacy_tail(tree):
    body=fn(tree,'main').body
    begin=next(i for i,n in enumerate(body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ledger' for t in n.targets))
    return [dump(n) for n in body[begin:] if not (isinstance(n,ast.If) and isinstance(n.test,ast.Call) and isinstance(n.test.func,ast.Name) and n.test.func.id=='scientific_modules')]
check('all_original_legacy_execution_tail_unchanged', legacy_tail(old)==legacy_tail(new))
legacy=ast.parse(Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\experiments\run_frozen_formal_matrix.py').read_text(encoding='utf-8-sig'))
imports=[alias.name.split('.')[0] for n in ast.walk(legacy) if isinstance(n,ast.Import) for alias in n.names]
imports += [n.module.split('.')[0] for n in ast.walk(legacy) if isinstance(n,ast.ImportFrom) and n.module]
check('legacy_only_stdlib_imports', all(n in sys.stdlib_module_names or n=='__future__' for n in imports))
spec=importlib.util.spec_from_file_location('reviewed_wrapper',SOURCE)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
check('import_wrapper_has_no_scientific_modules', not m.scientific_modules())
m.EXPECTED_PYTHON=Path(sys.executable)
fixture_root=HERE/'mock_fixtures'
fixture_root.mkdir(exist_ok=True)
m.HERE=fixture_root

def run_case(name, changes=None, corruption=None, exit_code=0, expect_error=False, before=None):
    visited={'waited':False,'launched':False}
    baseline={'PATH':'initial'} if before is None else before
    class Child:
        pid=12345
        def __init__(self, command, **kwargs):
            visited['launched']=True
            self.report_path=Path(command[-1])
            check(name+'_uses_current_python', Path(command[0])==Path(sys.executable))
            assert command[-2]=='--environment-report'
            assert 'env' not in kwargs
        def wait(self):
            visited['waited']=True
            if exit_code: return exit_code
            now=m.utc()
            report={'schema':'formal-environment-subprocess.v1','pid':23456,'started_utc':now,'finished_utc':now,
                'source_sha256':m.sha(SOURCE),
                'runtime_provenance':{'python':sys.version,'executable':str(m.EXPECTED_PYTHON),'packages':m.EXPECTED_PACKAGES.copy(),'cuda_initialized_by_guard':False},
                'import_environment_changes':copy.deepcopy(changes or {})}
            if corruption: corruption(report)
            m.save(self.report_path,report)
            return exit_code
    failed=False
    with patch.dict(os.environ,baseline,clear=True), patch.object(m.subprocess,'Popen',Child):
        try:
            result=m.verify_training_environment_isolated()
        except (RuntimeError, KeyError, TypeError, ValueError):
            failed=True
        if not failed:
            check(name+'_wait_completed_before_accept', visited['waited'] and result['isolation']['exit_code']==0)
            check(name+'_distinct_launcher_interpreter_pid_recorded', result['isolation']['launcher_pid']==12345 and result['isolation']['interpreter_pid']==23456)
            for key,change in (changes or {}).items(): check(name+'_preserves_'+key,os.environ.get(key)==change['after'])
    check(name+'_expected_outcome', failed==expect_error)

run_case('successful_probe')
run_case('preserved_import_delta', changes={'PATH':{'before':'initial','after':'dll;initial'},'DISABLE_CUPTI_LAZY_REINIT':{'before':None,'after':'1'},'TEARDOWN_CUPTI':{'before':None,'after':'0'}})
run_case('removed_environment_key',changes={'TEARDOWN_CUPTI':{'before':'0','after':None}},before={'PATH':'initial','TEARDOWN_CUPTI':'0'})
run_case('child_failure',exit_code=1,expect_error=True)
run_case('invalid_schema',corruption=lambda r:r.update(schema='wrong'),expect_error=True)
run_case('zero_interpreter_pid',corruption=lambda r:r.update(pid=0),expect_error=True)
run_case('bool_interpreter_pid',corruption=lambda r:r.update(pid=True),expect_error=True)
run_case('wrong_source',corruption=lambda r:r.update(source_sha256='0'*64),expect_error=True)
run_case('wrong_packages',corruption=lambda r:r['runtime_provenance'].update(packages={}),expect_error=True)
run_case('cuda_initialized',corruption=lambda r:r['runtime_provenance'].update(cuda_initialized_by_guard=True),expect_error=True)
run_case('unsupported_environment_key',changes={'OMP_NUM_THREADS':{'before':None,'after':'1'}},expect_error=True)
run_case('parent_environment_drift',changes={'PATH':{'before':'different','after':'dll;different'}},expect_error=True)
run_case('backward_timing',corruption=lambda r:r.update(started_utc='2000-01-01T00:00:00+00:00'),expect_error=True)
check('all_checks_still_no_scientific_imports',not m.scientific_modules())
report={'schema':'formal-wrapper-independent-review.v1','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source':str(SOURCE),'source_sha256':m.sha(SOURCE),'old_source':str(BACKUP),'old_source_sha256':m.sha(BACKUP),
    'passed':len(checks),'checks':checks,'findings':[],
    'limitations':['Popen and report publication mocked; actual native-interpreter exit and commitment reduction require root real preflight evidence.'],
    'scientific_imports':[],'actual_subprocesses_started':0,'actual_training_started':False}
(HERE/'WRAPPER_ISOLATION_INDEPENDENT_REVIEW.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':len(checks),'source_sha256':report['source_sha256'],'findings':[]},ensure_ascii=True))
