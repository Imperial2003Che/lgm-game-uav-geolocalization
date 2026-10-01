"""Independent byte/AST review only. Never imports any candidate or producer.

All outputs use exclusive creation. No scientific data, executable image, API,
candidate verifier, lifecycle fixture or producer control is executed here.
"""
import ast
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
EX = HERE.parent
PREP = EX / 'external_efficiency_preparation'
SOURCE = PREP / 'newer_native_b1_lifecycle_v1'
WORKER = PREP / 'newer_native_b1_worker_v2' / 'reference_worker.py'
MAX = 8 * 1024 * 1024
CHECKS = []
BINDINGS = {}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def read(path):
    path = Path(path).resolve(strict=True)
    if path.suffix.lower() in {'.pt', '.pth', '.npz', '.npy', '.zip', '.exe', '.dll'}:
        raise RuntimeError('Excluded scientific/binary data read: ' + str(path))
    before = path.stat()
    if before.st_size > MAX:
        raise RuntimeError('Oversize static input')
    with path.open('rb') as stream:
        raw = stream.read(MAX + 1)
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise RuntimeError('Static source changed during read')
    if len(raw) != after.st_size or len(raw) > MAX:
        raise RuntimeError('Static source length mismatch')
    BINDINGS[str(path)] = {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}
    return raw


def put(name, value):
    path = HERE / name
    raw = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8') + b'\n'
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}


def check(name, condition, detail):
    if not condition:
        raise RuntimeError('Independent static rejection: ' + name)
    CHECKS.append({'name': name, 'passed': True, 'detail': detail,
                   'method': 'independent byte/AST/text review; no candidate execution'})


def executable_body(node):
    body = list(node.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]
    return body


def call_name(node):
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
    return None


def first_guard(node, gate):
    first = executable_body(node)[0]
    if isinstance(first, ast.Expr):
        value = first.value
    elif isinstance(first, (ast.Assign, ast.AnnAssign)):
        value = first.value
    else:
        return False
    return isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == gate


def tree(path):
    raw = read(path)
    text = raw.decode('utf-8')
    parsed = ast.parse(text, filename=str(path))
    return raw, text, parsed, {n.name: n for n in parsed.body if isinstance(n, ast.FunctionDef)}


def source_of(text, node):
    return ast.get_source_segment(text, node)


def check_imports(label, parsed):
    allowed = {'copy', 'hashlib', 'importlib', 'json', 'os', 'pathlib', 'subprocess', 'sys',
               'time', 'traceback', 'contextlib', 'datetime', 'argparse'}
    for node in ast.walk(parsed):
        if isinstance(node, ast.Import):
            for alias in node.names:
                check(label + ':stdlib import ' + alias.name, alias.name.split('.')[0] in allowed,
                      {'line': node.lineno, 'name': alias.name})
        elif isinstance(node, ast.ImportFrom):
            check(label + ':stdlib from ' + str(node.module), node.level == 0 and node.module.split('.')[0] in allowed,
                  {'line': node.lineno, 'module': node.module})
    for node in parsed.body:
        check(label + ':safe module statement ' + str(node.lineno),
              isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef, ast.Assign, ast.Expr, ast.If)),
              {'line': node.lineno, 'node': type(node).__name__})
        if isinstance(node, ast.Expr):
            check(label + ':module expression is docstring', isinstance(node.value, ast.Constant) and isinstance(node.value.value, str),
                  {'line': node.lineno})
        if isinstance(node, ast.If):
            check(label + ':CLI first unconditional raise',
                  ast.unparse(node.test) in {"__name__ == '__main__'", "__name__ == \"__main__\""} and
                  isinstance(executable_body(node)[0], ast.Raise), {'line': node.lineno})


def find_calls(node, name):
    return [n for n in ast.walk(node) if isinstance(n, ast.Call) and call_name(n) == name]


def has_text(label, text, fragments):
    for fragment in fragments:
        check(label + ':' + fragment, fragment in text, {'source_fragment': fragment})


def verify_complete_patch(path):
    raw = read(path)
    lines = raw.decode('utf-8').splitlines(keepends=True)
    check('complete patch header ' + path.name, len(lines) > 2 and lines[0].startswith('--- ') and lines[1].startswith('+++ '), path.name)
    old_name, new_name = lines[0][4:].rstrip('\r\n'), lines[1][4:].rstrip('\r\n')
    pairs = {
        'COMPLETE_WORKER_V1_TO_V2.patch': (SOURCE / 'PRIOR_WORKER_V1.py.txt', WORKER),
        'COMPLETE_INITIAL_TO_FINAL_LIFECYCLE.patch': (SOURCE / 'INITIAL_PRE_REVIEW_native_lifecycle.py.txt', SOURCE / 'native_lifecycle.py'),
        'COMPLETE_INITIAL_TO_FINAL_EVIDENCE.patch': (SOURCE / 'INITIAL_PRE_REVIEW_evidence_contract.py.txt', SOURCE / 'evidence_contract.py'),
        'COMPLETE_OFFLINE_DERIVER_DELTA.patch': (SOURCE / 'INITIAL_PRE_REVIEW_prepare_worker_source_offline.py.txt', SOURCE / 'prepare_worker_source_offline.py'),
        'COMPLETE_CLEANUP_DELTA.patch': (SOURCE / 'PRE_CLEANUP_REVIEW_native_lifecycle.py.txt', SOURCE / 'native_lifecycle.py'),
        'COMPLETE_EVIDENCE_V1_TO_V2.patch': (SOURCE / 'evidence_contract.py', SOURCE / 'evidence_contract_v2.py'),
    }
    if path.name not in pairs:
        raise RuntimeError('Unknown full patch name: ' + path.name)
    old_file, new_file = pairs[path.name]
    old_raw, new_raw = read(old_file), read(new_file)
    expected = ''.join(difflib.unified_diff(old_raw.decode('utf-8').splitlines(keepends=True),
                        new_raw.decode('utf-8').splitlines(keepends=True), fromfile=old_name, tofile=new_name)).encode('utf-8')
    check('complete patch exact ' + path.name, raw == expected,
          {'prior': BINDINGS[str(old_file.resolve())], 'final': BINDINGS[str(new_file.resolve())],
           'diff': BINDINGS[str(path.resolve())], 'no_patch_applied_or_candidate_executed': True})


def main():
    read(__file__)
    read(HERE / 'INITIAL_PRE_RUN_review_lifecycle_static.py.txt')
    read(HERE / 'COMPLETE_PRE_RUN_REVIEW_DELTA.patch')
    read(HERE / 'PRE_FINAL_BINDING_review_lifecycle_static.py.txt')
    read(HERE / 'COMPLETE_FINAL_REVIEW_PREPARATION.patch')
    lc_raw, lc, lc_tree, lcf = tree(SOURCE / 'native_lifecycle.py')
    ec_raw, ec, ec_tree, ecf = tree(SOURCE / 'evidence_contract_v2.py')
    w_raw, worker, w_tree, wf = tree(WORKER)
    check_imports('controller', lc_tree)
    check_imports('saved relation', ec_tree)
    check_imports('worker', w_tree)
    guarded_lc = ['_load_process_helper', '_read_runtime_spec', '_wait_control_file',
                  '_final_admission_before_ack', '_confirm_controller_live', '_worker_validate_ack_live',
                  '_cleanup_references', '_run_native_slot', '_worker_pre_science_handshake',
                  'run_reference', 'admit_reference', 'main']
    guarded_w = ['_import_pinned', '_load_sources_after_admission', '_execute_original_reference',
                 'run_reference', 'admit_reference', '_load_lifecycle_module',
                 '_require_ack_before_original_import', '_native_worker_main']
    for label, functions, names, gate in [('controller', lcf, guarded_lc, '_closed_execution_admission'),
                                        ('worker', wf, guarded_w, '_closed_execution_admission'),
                                        ('saved relation', ecf, ['admit_reference', 'measure_task_ranking'], '_closed_admission')]:
        for name in names:
            check(label + ':FIRST closed ' + name, name in functions and first_guard(functions[name], gate),
                  {'line': functions[name].lineno, 'first_statement': ast.unparse(executable_body(functions[name])[0])})
        gate_node = functions[gate]
        check(label + ':gate unconditional raise', isinstance(executable_body(gate_node)[0], ast.Raise),
              {'line': gate_node.lineno})
    dangerous = {'WinAPI', 'HeldProcess', 'Popen', 'exec_module', 'spec_from_file_location',
                 'module_from_spec', 'snapshot', 'confirm_twice', 'wait', 'seal_closed_log',
                 'encode_seed', 'bind_completed', 'open_original_package'}
    inventory = []
    for label, functions, names in [('controller', lcf, guarded_lc), ('worker', wf, guarded_w)]:
        for name, node in functions.items():
            calls = [c for c in ast.walk(node) if isinstance(c, ast.Call) and call_name(c) in dangerous]
            if calls:
                check(label + ':all API/import/spawn/science call sites guarded ' + name, name in names,
                      {'function': name, 'line': node.lineno, 'call_sites': [{'name': call_name(c), 'line': c.lineno} for c in calls]})
                inventory.extend({'file': label, 'function': name, 'name': call_name(c), 'line': c.lineno} for c in calls)
    check('saved relation has no API/dynamic import/spawn/science call sites',
          not any(call_name(n) in dangerous for n in ast.walk(ec_tree) if isinstance(n, ast.Call)),
          'Only bounded saved-control/source/image reads and future designated four-artifact hashing remain available.')
    final_hook = lcf['_final_admission_before_ack']
    check('final issuer explicitly absent', len(executable_body(final_hook)) == 1 and not find_calls(final_hook, 'callback') and
          not any(isinstance(n, ast.Return) for n in ast.walk(final_hook)),
          'First closed; no callback, record or authority is returned by this version.')
    argv = source_of(lc, lcf['worker_argv'])
    check('native argv only -B and exact spec-binding path', "'-B'" in argv and "'-I'" not in argv and "'-S'" not in argv and
          'spec_binding.json' in argv, argv)
    has_text('strict spec', source_of(lc, lcf['validate_spec_data']), [
        "'distinct_native_redirector_child'", "prepared['runtime']['executable'] == prepared['python']",
        "bootstrap['launcher_image']['sha256'] == prepared['runtime']['interpreter_sha256']",
        "'camp_independent_evaluation_v3'", "'dac_independent_evaluation_v2'", "'b1_reference_runs'",
        "bootstrap['process_helper_source']['sha256'] == HELPER_SHA", "'execution_permission': False"])
    has_text('raw declaration', source_of(lc, lcf['_read_runtime_spec']), [
        "canonical(spec) + b'\\n'", "canonical(request) + b'\\n'", "canonical(bootstrap) + b'\\n'",
        "subprocess.list2cmdline(worker_argv(spec, bootstrap)) == bootstrap['launcher_complete_command']"])
    has_text('external strict chain', source_of(lc, lcf['_run_native_slot']), [
        'proc = subprocess.Popen', 'creationflags=subprocess.CREATE_NO_WINDOW', 'close_fds=True',
        "environment.update(prepared['settings']['thread_environment'])", 'proc.pid', "ready['pid'] != proc.pid",
        "'native_launcher_external'", "'native_interpreter_external'", "ready['self_snapshot'] == observations[-1]",
        "'controller_observations': controller_observations", "'final_admission': final_admission",
        'lexit = launcher.wait(WAIT_MS)', 'iexit = interpreter.wait(WAIT_MS)',
        "lexit['exit_code_unsigned_dword'] == 0 and iexit['exit_code_unsigned_dword'] == 0",
        'h.seal_closed_log(api, attempt / name, [launcher, interpreter], streams)',
        "'controller_self_exit_proven': False", "'controller_actual_exit_unknown_here': True",
        "guardian_must_retain_locks_and_review_all_unobserved_descendants=True"])
    run = source_of(lc, lcf['_run_native_slot'])
    check('ACK before held waits; two exits before streams/log/candidates',
          run.index("write_new_json(handshake / 'controller.ack.json'") < run.index('lexit = launcher.wait') <
          run.index('iexit = interpreter.wait') < run.index('stream.close()') < run.index('h.seal_closed_log') <
          run.index("candidates = {name: file_descriptor"), 'Source statement order only; no waits or seals executed.')
    live = source_of(lc, lcf['_worker_validate_ack_live'])
    has_text('post ACK live chain', live, [
        "ack['controller_identity']['pid']", "controller.identity == ack['controller_identity']",
        "_confirm_controller_live(controller, bootstrap)", "ack['launcher_identity']['pid']",
        "launcher.identity == ack['launcher_identity']", "launcher.confirm_twice(bootstrap['launcher_complete_command']",
        "me.confirm_twice(bootstrap['interpreter_complete_command']", "read_bound(bootstrap[name])",
        "read_bound(spec_record) == raw", "read_bound(spec['request']) == request_raw",
        "final_admission_relation(ack['final_admission']", "for parent in reversed(parents):", "except BaseException as error:",
        'cleanup_does_not_prove_exit=True', 'lock_release_authorized=False'])
    check('post ACK all captured parent closes attempted',
          any(isinstance(n, ast.For) and any(isinstance(b, ast.Try) for b in n.body) for n in ast.walk(lcf['_worker_validate_ack_live'])),
          'No unknown process termination; cleanup errors persist and reject completion.')
    handshake = source_of(lc, lcf['_worker_pre_science_handshake'])
    has_text('worker before science', handshake, [
        "not Path(spec['worker_control_directory']).exists() and not Path(spec['native_directory']).exists()",
        'not sys.flags.isolated and not sys.flags.no_site and sys.dont_write_bytecode',
        "'original_source_or_science_imported': False", "'self_report_is_not_external_identity_proof': True",
        '_worker_validate_ack_live(', 'ack_received_before_original_source_or_scientific_import'])
    original = wf['_execute_original_reference']
    body_calls = [call_name(n.value) if isinstance(n, ast.Expr) else None for n in executable_body(original)]
    check('new ACK statement immediately before original source loader',
          body_calls[1] == '_require_ack_before_original_import' and
          isinstance(executable_body(original)[2], ast.Assign) and
          call_name(executable_body(original)[2].value) == '_load_sources_after_admission',
          {'line': original.lineno, 'rest_of_scientific_body_delegated_to_separate_bound_worker_delta_review': True})
    main = source_of(worker, wf['_native_worker_main'])
    check('native worker future return intent is integer0 after original body',
          main.index('_execute_original_reference(') < main.index('return 0'), main)
    has_text('saved evidence strict association', ec, [
        'controller_observations_relation(', "bootstrap['controller_complete_command']",
        "prepared['runtime']['interpreter_sha256']", 'HELPER_SHA',
        "'creation_filetime_100ns'", "'exit_filetime_100ns'", 'FILETIME_TO_DOTNET_TICKS',
        "type(exit_value['exit_code_unsigned_dword']) is int", "'same_retained_handle_pid_creation_verified'",
        "'npy_or_ledger_semantics_revalidated': False", "'process_apis_or_handles_executed_by_this_checker': False",
        "'immutable_independent_execution_root_implemented': False", "'independent_execution_proven': False",
        "'execution_permission': False", "'measurement_admitted': False", "'full_t6_complete': False"])
    has_text('final selected saved relation v2 narrow corrections', ec, [
        "observed['creation_utc_ticks'] >= parent_identity['creation_utc_ticks']",
        "os.path.samefile(observed['image'], identity['image'])", "request['schema'] == 'newer-native-b1-request.v1'"])
    patches = list(SOURCE.glob('COMPLETE_*.patch'))
    check('new source six full patches published', len(patches) == 6, [p.name for p in patches])
    for path in sorted(patches):
        verify_complete_patch(path)
    for name in ('prepare_worker_source_offline.py', 'WORKER_BODY_DERIVATION.json', 'README.md',
                 'SOURCE_MANIFEST.json', 'SOURCE_INDEX.json', 'SOURCE_REVIEW_ADDENDUM.md',
                 'SOURCE_REVIEW_MANIFEST.json', 'seal_source_candidate_offline.py',
                 'seal_final_review_sources_offline.py', 'check_new_source_controls.py',
                 'seal_controls_delivery.py', 'DELIVERY.json'):
        read(SOURCE / name)
    producer_delivery = json.loads((SOURCE / 'DELIVERY.json').read_text(encoding='utf-8'))
    check('producer delivery explicit source/pure-controls status',
          producer_delivery['source_adopted'] is False and producer_delivery['execution_released'] is False and
          producer_delivery['new_pure_control_count'] == 50 and producer_delivery['api_native_scientific_execution'] is False,
          BINDINGS[str((SOURCE / 'DELIVERY.json').resolve())])
    for record in producer_delivery['files']:
        read(record['path'])
        check('producer delivery current small binding ' + Path(record['path']).name,
              record == BINDINGS[record['path']], record)
    manifests = [json.loads((SOURCE / name).read_text(encoding='utf-8'))
                 for name in ('SOURCE_MANIFEST.json', 'SOURCE_REVIEW_MANIFEST.json')]
    for name in ('README.md', 'SOURCE_MANIFEST.json'):
        read(WORKER.parent / name)
    controls_path = SOURCE / 'source_controls_v1' / 'NEW_SOURCE_CONTROLS.json'
    controls_raw = read(controls_path)
    controls = json.loads(controls_raw)
    check('producer 50 new controls bound but not rerun by independent reviewer',
          sha(controls_raw) == '115c2c2af569f10fb87441d49c5a4467f9cea614fbc6ad37a72be7ef650895f7' and
          controls['count'] == 50 and controls['all_passed'] is True and
          controls['windows_process_api_or_helper_executed'] is False and
          controls['subprocess_or_native_venv_executed'] is False and
          controls['original_binder_or_science_imported'] is False and controls['execution_released'] is False,
          {'saved_report': BINDINGS[str(controls_path.resolve())],
           'producer_imported_stdlib_candidate_definitions_for_pure_controls': True,
           'independent_reviewer_did_not_import_candidates_or_call_these_controls': True})
    # Every descriptor occurrence referring to our current source set must match
    # independently read bytes; old dependency lists are not bulk reread.
    def descriptors(value):
        if isinstance(value, dict):
            if set(value) == {'path', 'bytes', 'sha256'}:
                yield value
            for item in value.values():
                yield from descriptors(item)
        elif isinstance(value, list):
            for item in value:
                yield from descriptors(item)
    matched = []
    for manifest in manifests:
        for record in descriptors(manifest):
            if record['path'] in BINDINGS:
                check('producer manifest current source edge ' + Path(record['path']).name,
                      record == BINDINGS[record['path']], record)
                matched.append(record['path'])
    for record in controls['source_bindings']:
        check('producer controls bound final source bytes ' + Path(record['path']).name,
              record['path'] in BINDINGS and record == BINDINGS[record['path']], record)
    check('producer manifest actually binds current controller worker evidence source',
          all(str(p.resolve()) in matched for p in (SOURCE / 'native_lifecycle.py', SOURCE / 'evidence_contract.py',
              SOURCE / 'evidence_contract_v2.py', WORKER)), matched)
    read(EX / 'b1_integration_scope_20260930_0912' / 'INTEGRATION_SCOPE.json')
    read(EX / 'b1_integration_scope_20260930_0912' / 'SOURCE_BLOCKS.json')
    worker_review = EX / 'b1_worker_body_delta_review_20260930_0930'
    worker_delivery_raw = read(worker_review / 'DELIVERY.json')
    worker_delivery = json.loads(worker_delivery_raw)
    for path in sorted(worker_review.glob('*.json')):
        if path.name != 'DELIVERY.json':
            read(path)
    worker_report = json.loads((worker_review / 'DELTA_REVIEW.json').read_text(encoding='utf-8'))
    check('joint narrow worker report explicit static acceptance only',
          worker_report['result'] == 'passed narrow source correspondence and first closed guards' and
          worker_report['check_count'] == 91 and worker_report['execution_released'] is False and
          worker_report['native_worker_validated'] is False and worker_report['controller_fully_validated'] is False,
          {'joint_report': BINDINGS[str((worker_review / 'DELTA_REVIEW.json').resolve())],
           'not_called_or_repeated_by_this_checker': True})
    for record in worker_delivery['inputs'] + worker_delivery['outputs']:
        if record['path'] in BINDINGS:
            check('joint worker exact existing report/source edge ' + Path(record['path']).name,
                  record == BINDINGS[record['path']], record)
    # Do not infer worker status from file existence. Scope binding is explicit;
    # root must read the linked narrow review together with this whole review.
    prior_worker = read(PREP / 'newer_native_b1_worker_v1' / 'reference_worker.py')
    check('prior worker v1 kept exact adopted bytes', sha(prior_worker) == 'eed9b25b1204edbcf5172ea2fb24e272b7ff39103f98448e554a3dae779b7f46', 'No original source edited.')
    helper = read(PREP / 'newer_native_process_evidence_v2' / 'windows_process_evidence.py')
    check('prior helper reviewed bytes unchanged', sha(helper) == 'cc090bec1429ab429b556200597acedfa13c33e878627155b0cc9f8098c9f5d2',
          'This reviewer authored prior helper v2, not current lifecycle/worker/contract.')
    sources = list(BINDINGS.values())
    checks_record = put('STATIC_SOURCE_CHECKS.json', {'schema': 'independent-native-b1-static-checks.v1',
                        'actual_scope': 'byte/AST/text source only', 'checks': CHECKS,
                        'candidate_or_producer_imported': False, 'candidate_functions_or_controls_called': False,
                        'windows_or_scientific_apis_called': False, 'runtime_or_native_venv_tested': False})
    inputs_record = put('INPUT_BINDINGS.json', {'schema': 'independent-native-b1-static-inputs.v1',
                        'unique_count': len(sources), 'files': sources})
    report = {
        'schema': 'independent-native-b1-lifecycle-source-review.v1',
        'completed_utc': datetime.now(timezone.utc).isoformat(),
        'reviewer': 'independent AI subagent; no human review',
        'independence_scope': {'current_lifecycle_worker_evidence_author': False,
                               'prior_windows_process_helper_v2_author': True,
                               'prior_helper_new_independent_runtime_review_claimed': False},
        'decision': 'accepted_closed_source_only', 'source_review_accepted': True,
        'source_adopted': False,
        'execution_released': False, 'runtime_validated': False,
        'native_venv_validated': False, 'measurement_admitted': False,
        'independent_execution_proven': False, 'full_t6_complete': False,
        'science_or_ranking_gate_changed': False, 'human_review': False,
        'scope': ['Full current controller and saved evidence contract source read, byte/AST guards and declaration/data associations.',
                  'Current worker full source read; only ACK/native edge reviewed here; exact frozen scientific-body/PINS delta is a separate narrow AI review.',
                  'Initial failures and complete source corrections are preserved and byte-bound.',
                  'Prior helper current-host control accepted elsewhere applies only to ordinary Python, not registered scientific venv.'],
        'selected_reference_checker': BINDINGS[str((SOURCE / 'evidence_contract_v2.py').resolve())],
        'historical_base_checker': BINDINGS[str((SOURCE / 'evidence_contract.py').resolve())],
        'producer_new_controls': {'record': BINDINGS[str(controls_path.resolve())],
                                 'reported_count': 50, 'performed_by_this_reviewer': False,
                                 'pure_metadata_and_first_closed_only': True,
                                 'native_windows_or_scientific_validation': False},
        'producer_delivery': BINDINGS[str((SOURCE / 'DELIVERY.json').resolve())],
        'resolved_source_defects': [
            'Worker postACK now independently opens actual controller and launcher held identities, checks two live image/full-command/parent observations, current interpreter and all six source/image bytes, and final descriptor relation.',
            'Prepared runtime executable/interpreter SHA and registered method native output root are now strict associations.',
            'Each captured worker-side parent close is attempted separately, errors persisted; no cleanup is an exit or lock release grant.',
            'Saved-record checker now associates controller observations, exact source roots/helper pin/prepared seal/runtime/nonce/request, strict integer observations and two saved exits.',
            'Offline worker derivation removes the actual unique ACK AST statement, while future worker returns integer0 only after original body.'],
        'missing_authority_and_limits': [
            'Every native/API/import/spawn/handshake/admit/CLI FIRST entry remains unconditional rejection. Caller objects, paths, expected candidates and saved flags confer no permission.',
            'Final preACK issuer is deliberately absent: predecessor actual independent exits, current boot/state/source/release TTL/resource gates and continuously retained shared GPU locks are not implemented by this source.',
            'No scientific venv/base interpreter bootstrap, current native site/startup behavior, real redirector topology or native two-handle runtime was validated.',
            'Source stdlib/current sys.modules gates do not establish all historical native startup imports; separately reviewed native bootstrap remains required.',
            'No new attempt/ready/ACK/exit/log/result/NPY/ledger was generated or read by this review. Saved relation checker was not called and cannot prove saved records trustworthy.',
            'Four future designated artifact SHA/size association is not original NPY/ledger/loader semantic independent validation, full fresh gallery/ranking/parity/timing or fullonlineCLIP.',
            'CreateNew/fsync/read-sharing are cooperative; undocumented class60/current Toolhelp parentage and unobserved descendants retain existing scope limits.',
            'Controller return intent does not prove its own exit; shared lock release requires actual guardian/descendant review in a separately released version.'],
        'checks': checks_record, 'inputs': inputs_record, 'check_count': len(CHECKS),
        'api_import_spawn_science_guarded_callsite_inventory': inventory,
        'joint_worker_delta_delivery': BINDINGS[str((worker_review / 'DELIVERY.json').resolve())],
        'worker_delta_delivery_status_read_as_source_data': worker_delivery,
        'no_old_scientific_or_control_suite_repeated': True,
    }
    review_record = put('SOURCE_REVIEW.json', report)
    delivery = put('DELIVERY.json', {'schema': 'independent-native-b1-lifecycle-static-delivery.v1',
                   'completed_utc': datetime.now(timezone.utc).isoformat(), 'source_review': review_record,
                   'checks': checks_record, 'inputs': inputs_record,
                   'review_source': BINDINGS[str(Path(__file__).resolve())],
                   'joint_worker_delta_delivery': report['joint_worker_delta_delivery'],
                   'source_only': True, 'execution_released': False, 'runtime_validated': False,
                   'measurement_admitted': False, 'human_review': False})
    print(json.dumps({'source_review': review_record, 'delivery': delivery,
                      'check_count': len(CHECKS), 'unique_input_bindings': len(sources)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
