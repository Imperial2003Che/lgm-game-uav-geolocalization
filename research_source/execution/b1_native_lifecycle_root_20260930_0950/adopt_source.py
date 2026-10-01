"""Local source adoption only. No producer import, API, experiment or release."""
import ast
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
EX = HERE.parent
PREP = EX / 'external_efficiency_preparation'
LIFE = PREP / 'newer_native_b1_lifecycle_v1'
WORKER = PREP / 'newer_native_b1_worker_v2'
MAX = 512 * 1024
bindings = {}
checks = []


def check(name, condition):
    checks.append({'name': name, 'passed': bool(condition)})
    if not condition:
        raise RuntimeError(name)


def read(path, expected=None):
    if Path(path).absolute() == LIFE / 'ROOT_SOURCE_ADOPTION.json':
        raise RuntimeError('This adoption output must not be a self-referential input')
    path = Path(path).resolve(strict=True)
    check('small-file-in-execution:' + path.name, path.is_relative_to(EX) and path.stat().st_size <= MAX)
    before = path.stat()
    with path.open('rb') as f:
        raw = f.read(MAX + 1)
    after = path.stat()
    check('stable-read:' + path.name, (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
          (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) and len(raw) == before.st_size)
    item = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    if expected is not None:
        check('exact-binding:' + path.name, item == expected)
    prior = bindings.get(str(path))
    check('unique-byte-binding:' + path.name, prior is None or prior == item)
    bindings[str(path)] = item
    return raw, item


def bound(item):
    check('exact-descriptor', type(item) is dict and set(item) == {'path', 'bytes', 'sha256'} and
          type(item['path']) is str and type(item['bytes']) is int and item['bytes'] >= 0 and
          type(item['sha256']) is str and len(item['sha256']) == 64)
    return read(item['path'], item)[0]


def first_action(fn):
    body = fn.body
    if isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]
    return body[0]


def guarded(tree, names, gate):
    fns = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    for name in names:
        action = first_action(fns[name])
        value = action.value if isinstance(action, (ast.Assign, ast.Expr)) else None
        check('first-unconditional-gate:' + name, isinstance(value, ast.Call) and
              isinstance(value.func, ast.Name) and value.func.id == gate)
    check('gate-unconditional-raise:' + gate, isinstance(first_action(fns[gate]), ast.Raise))
    guards = [node for node in tree.body if isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
              and isinstance(node.test.left, ast.Name) and node.test.left.id == '__name__']
    check('cli-first-raise', len(guards) == 1 and isinstance(guards[0].body[0], ast.Raise))


def write_new(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(raw) > MAX:
        raise RuntimeError('Report exceeds checked pre-create byte bound')
    with path.open('xb') as f:
        f.write(raw); f.flush(); os.fsync(f.fileno())
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    config_raw, config_item = read(HERE / 'INPUT_CONTRACT.json')
    config = json.loads(config_raw)
    values = {}
    for role, item in config['inputs'].items():
        raw = bound(item)
        values[role] = json.loads(raw) if str(item['path']).endswith('.json') else raw
    for role in ('lifecycle_manifest', 'worker_manifest'):
        manifest = values[role]
        check('source-only-manifest:' + role, manifest['execution_released'] is False and
              manifest['native_venv_validated'] is False and manifest['measurement_admitted'] is False)
        for item in manifest['files']:
            bound(item)
        for item in manifest.get('worker_files', []):
            bound(item)
    for role in config.get('additional_descriptor_tables', []):
        for item in values[role].get('files', []) + list(values[role].get('roles', {}).values()):
            bound(item)
    for role in config['review_delivery_roles']:
        for item in values[role].get('inputs', []) + values[role].get('outputs', []):
            bound(item)
    for role in config['passed_review_roles']:
        report = values[role]
        check('review-not-execution:' + role, report['execution_released'] is False)
        stored_checks = report['checks']
        if type(stored_checks) is dict:
            stored_checks = json.loads(bound(stored_checks))['checks']
        count = report.get('check_count', report.get('count'))
        check('actual-stored-checks:' + role, count == len(stored_checks) and
              all(item['passed'] is True for item in stored_checks))
    for item in config['extra_source_bindings']:
        bound(item)
    native_raw, _ = read(LIFE / 'native_lifecycle.py')
    native_tree = ast.parse(native_raw)
    guarded(native_tree, config['native_closed_functions'], '_closed_execution_admission')
    worker_raw, _ = read(WORKER / 'reference_worker.py')
    worker_tree = ast.parse(worker_raw)
    guarded(worker_tree, ['_import_pinned', '_load_sources_after_admission', '_execute_original_reference',
            'run_reference', 'admit_reference', '_load_lifecycle_module',
            '_require_ack_before_original_import', '_native_worker_main'], '_closed_execution_admission')
    checker_raw = bound(values['final_source_manifest']['roles']['selected_reference_checker'])
    guarded(ast.parse(checker_raw), ['admit_reference', 'measure_task_ranking'], '_closed_admission')
    hook = next(n for n in native_tree.body if isinstance(n, ast.FunctionDef) and n.name == '_final_admission_before_ack')
    check('missing-issuer-not-implemented', len(hook.body) == 1 and isinstance(first_action(hook), ast.Expr))
    observation = values['observation_seal']
    check('saved-known-gpu-block', observation['gpu_gate_satisfied'] is False and
          observation['execution_released'] is False and observation['cleanup_authorized'] is False)
    check('snapshot-not-claimed-current-admission', config['os_snapshot_is_not_future_permission'] is True)
    for item in observation['unchanged_state_and_closed_log_files']:
        bound(item)
    carrier_raw = bound({k: observation['carrier'][k] for k in ('path', 'bytes', 'sha256')})
    check('carrier-byte-only', carrier_raw == b'0')
    for path in observation['attempts_absent_at_seal']:
        check('attempt-still-absent:' + Path(path).parent.name, not Path(path).exists())
    for path in (LIFE / 'runs', WORKER / 'runs'):
        check('new-source-no-live-run:' + path.parent.name, not path.exists())
    check('t6-output-still-absent', not Path(config['t6_output']).exists())
    read(Path(__file__))
    report = {
        'schema': 'root-newer-native-b1-lifecycle-source-adoption.v1',
        'adopted_utc': datetime.now(timezone.utc).isoformat(),
        'source_adopted': True, 'execution_released': False,
        'native_venv_validated': False, 'scientific_environment_validated': False,
        'scientific_execution_performed': False, 'independent_execution_proven': False,
        'measurement_admitted': False, 'full_t6_complete': False, 'manuscript_result': False,
        'root_method': 'Root AI read complete new source/deltas/producer and independent checkers; this sealer reads only bounded source/review/current small state bytes and parses AST. No candidate import or tests repeated.',
        'scientific_body_correspondence_review': config['inputs']['worker_delta_review'],
        'lifecycle_static_review': config['inputs']['lifecycle_review'],
        'new_pure_controls': config['inputs']['pure_controls'],
        'prior_cpu_control_scope_inherited': config['prior_cpu_control_scope'],
        'saved_os_observation': config['inputs']['observation_seal'],
        'small_state_and_log_bytes_rechecked_at_adoption': True,
        'no_new_os_gpu_or_available_commit_measurement_at_adoption': True,
        'check_count': len(checks), 'checks': checks,
        'unique_bindings': len(bindings), 'inputs': list(bindings.values()),
        'limitations': config['limitations'],
    }
    result = write_new(LIFE / 'ROOT_SOURCE_ADOPTION.json', report)
    print(json.dumps({'source_adopted_only': True, 'execution_released': False,
                      'unique_bindings': report['unique_bindings'], 'check_count': report['check_count'],
                      'root': result}, ensure_ascii=False))


if __name__ == '__main__':
    main()
