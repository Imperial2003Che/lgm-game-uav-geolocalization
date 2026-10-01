"""One explicitly reviewed run of new pure stdlib metadata/closed-gate controls.

No subprocess, Windows API/helper, original module, CompletedInputs binder,
science, existing fixture/suite or complete fake scientific result tree is run.
All files below are small new synthetic metadata; the report grants no authority.
"""
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
OUT = HERE / 'source_controls_v1'
WORKER = HERE.parent / 'newer_native_b1_worker_v2' / 'reference_worker.py'
SCIENCE = {'numpy', 'torch', 'torchvision', 'cv2', 'timm', 'albumentations', 'PIL'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def new_bytes(path, raw):
    with path.open('xb') as f:
        f.write(raw); f.flush(); os.fsync(f.fileno())


def binding(path):
    raw = path.read_bytes()
    return {'path': str(path.resolve(strict=True)), 'bytes': len(raw), 'sha256': sha(raw)}


def load_source(name, path):
    # Candidate import initializes stdlib definitions only. Never instantiate API.
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    OUT.mkdir(exist_ok=False)
    results = []
    source_paths = [HERE / 'native_lifecycle.py', HERE / 'evidence_contract_v2.py', WORKER]
    before_sources = [binding(p) for p in source_paths]
    before_modules = set(sys.modules)
    n = load_source('_new_b1_control_native', source_paths[0])
    e = load_source('_new_b1_control_relation', source_paths[1])
    w = load_source('_new_b1_control_worker', source_paths[2])

    def good(name, function):
        function()
        results.append({'name': name, 'passed': True, 'case': 'accept valid synthetic metadata only'})

    def reject(name, function, expected=RuntimeError):
        try:
            function()
        except expected as error:
            results.append({'name': name, 'passed': True, 'case': 'reject invalid synthetic metadata',
                            'exception': type(error).__name__})
        else:
            raise RuntimeError('Expected rejection missing: ' + name)

    def assert_true(value):
        if not value:
            raise RuntimeError('New control assertion failed')

    good('canonical_json_distinguishes_integer_and_boolean',
         lambda: assert_true(n.canonical({'seed': 1}) != n.canonical({'seed': True})))
    reject('duplicate_json_key_rejected', lambda: n.parse(b'{"seed":1,"seed":2}'))
    reject('nonfinite_json_rejected', lambda: n.parse(b'{"value":NaN}'))
    reject('bool_descriptor_size_rejected', lambda: n.require_descriptor({'path': str(OUT / 'small.json'), 'bytes': True, 'sha256': '0'*64}))
    small = OUT / 'small.json'; new_bytes(small, b'{"synthetic":true}\n')
    small_record = binding(small)
    good('exact_small_control_bytes_read', lambda: assert_true(n.read_bound(small_record) == b'{"synthetic":true}\n'))
    bad_size = dict(small_record, bytes=small_record['bytes'] + 1)
    reject('actual_size_checked_before_bounded_read', lambda: n.read_bound(bad_size))
    reject('wrong_control_sha_rejected', lambda: n.read_bound(dict(small_record, sha256='0'*64)))

    nonce = 'a'*64; name = 'camp_seed1_' + nonce
    prepared = {'python': r'C:\synthetic\venv\Scripts\python.exe',
                'runtime': {'executable': r'C:\synthetic\venv\Scripts\python.exe', 'interpreter_sha256': '1'*64},
                'settings': {'batch_size': 16}}
    prepared['payload_sha256'] = sha(n.canonical(prepared))
    def synthetic_descriptor(path, digest='2'*64):
        return {'path': str(path), 'bytes': 1, 'sha256': digest}
    prep_record = synthetic_descriptor(OUT / 'unused_original_prepared.json')
    spec = {'schema': 'newer-native-b1-lifecycle-slot.v1', 'method': 'CAMP', 'seed': 1, 'nonce': nonce,
            'run_name': name, 'request': synthetic_descriptor(OUT / 'unused_request.json'),
            'prepared': prep_record, 'bootstrap': synthetic_descriptor(OUT / 'unused_bootstrap.json'),
            'handshake_directory': str(HERE / 'runs' / name / 'handshake'),
            'worker_control_directory': str(WORKER.parent / 'runs' / name),
            'native_directory': str(HERE.parent.parent / 'camp_independent_evaluation_v3' / 'b1_reference_runs' / name)}
    request = {'schema': 'newer-native-b1-request.v1', 'method': 'CAMP', 'seed': 1, 'prepared': prep_record}
    bootstrap = {'schema': 'newer-native-b1-bootstrap-candidate.v1', 'topology': 'distinct_native_redirector_child',
                 'launcher_image': synthetic_descriptor(prepared['python'], '1'*64),
                 'interpreter_image': synthetic_descriptor(r'C:\synthetic\base\python.exe'),
                 'controller_image': synthetic_descriptor(r'C:\synthetic\controller\python.exe'),
                 'controller_complete_command': 'synthetic controller complete command',
                 'launcher_complete_command': 'synthetic launcher complete command',
                 'interpreter_complete_command': 'synthetic interpreter complete command',
                 'worker_source': synthetic_descriptor(WORKER), 'controller_source': synthetic_descriptor(HERE / 'native_lifecycle.py'),
                 'process_helper_source': synthetic_descriptor(n.HELPER, n.HELPER_SHA)}
    good('valid_slot_is_consistency_and_never_permission', lambda: assert_true(
        n.validate_spec_data(spec, request, prepared, bootstrap)['execution_permission'] is False))
    bad = copy.deepcopy(spec); bad['seed'] = True
    reject('bool_seed_rejected', lambda: n.validate_spec_data(bad, request, prepared, bootstrap))
    bad = copy.deepcopy(spec); bad['native_directory'] = str(OUT / name)
    reject('wrong_original_native_parent_rejected', lambda: n.validate_spec_data(bad, request, prepared, bootstrap))
    bad = copy.deepcopy(bootstrap); bad['launcher_image']['sha256'] = '9'*64
    reject('launcher_sha_not_frozen_runtime_rejected', lambda: n.validate_spec_data(spec, request, prepared, bad))

    image_a, image_b = OUT / 'synthetic_image_a.bin', OUT / 'synthetic_image_b.bin'
    new_bytes(image_a, b'A'); new_bytes(image_b, b'B')
    ticks = e.FILETIME_TO_DOTNET_TICKS
    parent = {'pid': 10, 'creation_filetime_100ns': 100, 'creation_utc_ticks': ticks+100, 'image': str(image_a)}
    child = {'pid': 11, 'creation_filetime_100ns': 200, 'creation_utc_ticks': ticks+200, 'image': str(image_a)}
    obs = {**child, 'parent_pid': 10, 'command_line': 'synthetic exact full command',
           'held_now': dict(child), 'fresh_after': dict(child)}
    image_record = binding(image_a)
    good('two_saved_observations_relation_only', lambda: e.observations_relation([copy.deepcopy(obs), copy.deepcopy(obs)], child, parent, image_record, obs['command_line']))
    bad = copy.deepcopy(obs); bad['command_line'] = 'different complete command'
    reject('saved_complete_command_mismatch_rejected', lambda: e.observations_relation([bad, copy.deepcopy(bad)], child, parent, image_record, obs['command_line']))
    later_parent = dict(parent, creation_filetime_100ns=300, creation_utc_ticks=ticks+300)
    reject('child_predating_captured_parent_rejected', lambda: e.observations_relation([obs, copy.deepcopy(obs)], child, later_parent, image_record, obs['command_line']))
    other_identity = dict(child, image=str(image_b)); bad = copy.deepcopy(obs)
    bad['held_now'] = dict(other_identity); bad['fresh_after'] = dict(other_identity)
    reject('observation_image_not_retained_identity_rejected', lambda: e.observations_relation([bad, copy.deepcopy(bad)], other_identity, parent, image_record, obs['command_line']))
    bad_identity = dict(child, pid=True)
    reject('boolean_pid_rejected', lambda: e.identity_shape(bad_identity))
    exit_value = {'identity': dict(child), 'wait_result': 0, 'exit_code_unsigned_dword': 0, **child,
                  'exit_filetime_100ns': 400, 'exit_utc_ticks': ticks+400, 'same_retained_handle_pid_creation_verified': True}
    good('saved_exit_integer_relation_only', lambda: e.exit_relation(exit_value, child))
    reject('boolean_exit_code_rejected', lambda: e.exit_relation(dict(exit_value, exit_code_unsigned_dword=False), child))
    reject('exit_time_conversion_mismatch_rejected', lambda: e.exit_relation(dict(exit_value, exit_utc_ticks=ticks+401), child))

    snapshot = sorted(str(p) for p in HERE.parent.iterdir())
    runtime_names = [name for name in vars(n) if name.startswith('_') and callable(vars(n)[name]) and
                     name not in {'__loader__'} and name in {
                     '_closed_execution_admission', '_load_process_helper', '_read_runtime_spec', '_wait_control_file',
                     '_final_admission_before_ack', '_confirm_controller_live', '_worker_validate_ack_live',
                     '_cleanup_references', '_run_native_slot', '_worker_pre_science_handshake'}]
    by_module = [(n, runtime_names + ['run_reference', 'admit_reference', 'main']),
                 (w, ['_closed_execution_admission', '_import_pinned', '_load_sources_after_admission',
                      '_execute_original_reference', '_load_lifecycle_module', '_require_ack_before_original_import',
                      '_native_worker_main', 'run_reference', 'admit_reference']),
                 (e, ['_closed_admission', 'admit_reference', 'measure_task_ranking'])]
    for module, names in by_module:
        tree = ast.parse(Path(module.__file__).read_text(encoding='utf-8'))
        functions = {x.name: x for x in tree.body if isinstance(x, ast.FunctionDef)}
        for name in names:
            node = functions[name]
            required = len(node.args.args) - len(node.args.defaults)
            reject('first_closed_gate_' + module.__name__ + '_' + name,
                   lambda m=module, key=name, count=required: getattr(m, key)(*[None]*count), module.ClosedExecutionGate)
        cli = next(x for x in tree.body if isinstance(x, ast.If) and isinstance(x.test, ast.Compare)
                   and isinstance(x.test.left, ast.Name) and x.test.left.id == '__name__')
        good('cli_first_raise_' + module.__name__, lambda c=cli: assert_true(isinstance(c.body[0], ast.Raise)))
    good('closed_gates_create_no_runtime_directories', lambda: assert_true(snapshot == sorted(str(p) for p in HERE.parent.iterdir()) and
        not (HERE / 'runs').exists() and not (WORKER.parent / 'runs').exists()))
    good('no_process_helper_or_science_imported', lambda: assert_true(not any(k.split('.')[0] in SCIENCE for k in sys.modules) and
        not any('process_helper' in k for k in set(sys.modules) - before_modules)))
    good('final_sources_unchanged', lambda: assert_true(before_sources == [binding(p) for p in source_paths]))
    report = {'schema': 'newer-native-b1-new-pure-source-controls.v1', 'checks': results,
              'count': len(results), 'all_passed': True, 'source_bindings': before_sources,
              'synthetic_metadata_and_closed_gates_only': True, 'candidate_full_tree_or_original_validator_run': False,
              'windows_process_api_or_helper_executed': False, 'subprocess_or_native_venv_executed': False,
              'old_fixture_or_suite_repeated': False, 'original_binder_or_science_imported': False,
              'execution_released': False, 'native_venv_validated': False,
              'independent_execution_proven': False, 'measurement_admitted': False, 'full_t6_complete': False}
    new_bytes(OUT / 'NEW_SOURCE_CONTROLS.json', json.dumps(report, ensure_ascii=False, indent=2).encode('utf-8') + b'\n')
    print(json.dumps({'count': len(results), 'report': binding(OUT / 'NEW_SOURCE_CONTROLS.json')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
