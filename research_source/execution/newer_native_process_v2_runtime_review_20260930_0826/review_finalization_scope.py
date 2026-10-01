"""Independent local post-write finalization review, not runtime-suite replay."""
from datetime import datetime, timezone
import ast
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EX = HERE.parent
RUN = EX / 'newer_native_process_execution_v2_20260930_0820'
records = {}
checks = []

def check(condition, description):
    checks.append({'check': description, 'passed': bool(condition)})
    assert condition, description

def bind(path, cap=100000):
    path = Path(path)
    size = path.stat().st_size
    check(size < cap, 'Bounded local finalization file: ' + path.name)
    with path.open('rb') as stream:
        raw = stream.read(cap)
    check(len(raw) == size and len(raw) < cap, 'Actual bounded file read: ' + path.name)
    item = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    records[str(path)] = item
    return item, raw

def load(path, cap=100000):
    return json.loads(bind(path, cap)[1])

target = RUN / 'ROOT_CURRENT_HOST_CONTROL_ADOPTION.json'
report_binding, raw_report = bind(target, 250000)
report = json.loads(raw_report)
check(report_binding['bytes'] == 104883 and report_binding['sha256'] == '5ecd3ab4c1b04ab3b824ad89298c3dd77b0d6397c23a85731982bcf0cb41b29c',
      'The original persisted root report is exact and complete JSON; never rewritten')
failure = load(RUN / 'ROOT_SEAL_POSTWRITE_FAILURE.json')
transcript = load(RUN / 'ROOT_SEAL_TOOL_TRANSCRIPT.json')
check(transcript['schema'] == 'post-execution-root-sealer-tool-transcription.v1' and transcript['actual_exit_code'] == 1 and
      transcript['chunk_id'] == failure['actual_tool_chunk'], 'Actual visible tool transcription joins first root exit-one chunk')
check(failure['schema'] == 'root-adoption-postwrite-digest-failure.v1' and failure['actual_tool_exit'] == 1,
      'Root failure summary preserves actual first sealer tool exit one')
check(failure['root_fixture_replayed'] is False and failure['scientific_failure'] is False and failure['replay_of_original_sealer_authorized'] is False,
      'Failure summary is local post-write metadata failure, not scientific failure or replay grant')
check(failure['stage'] == 'save(target, report) wrote root report; subsequent bounded hash-return refused report size',
      'Failure summary identifies post-write hash-return stage')
source_binding, source_bytes = bind(RUN / 'prepare_adoption.py')
check(source_binding == report['source'], 'Original root report binds its exact unchanged writer source')
source_tree = ast.parse(source_bytes.decode('utf-8'))
functions = {node.name: node for node in source_tree.body if isinstance(node, ast.FunctionDef)}
bind_fn, save_fn = functions['bind'], functions['save']
check(isinstance(bind_fn.args.defaults[0], ast.Constant) and bind_fn.args.defaults[0].value == 100000,
      'Original bind uses strict default 100000-byte cap')
check(isinstance(bind_fn.body[2], ast.Assert) and isinstance(bind_fn.body[2].test, ast.Compare) and
      isinstance(bind_fn.body[2].test.ops[0], ast.Lt), 'Original bound is strict less-than before report read')
save_body = ast.get_source_segment(source_bytes.decode('utf-8'), save_fn)
check("with Path(path).open('xb') as f:" in save_body and 'f.write(raw);f.flush()' in save_body and
      save_body.index('f.write(raw);f.flush()') < save_body.index('return bind(path)[0]'),
      'CreateNew write and with-block close precede final return bind in original save')
check(isinstance(save_fn.body[-1], ast.Return) and isinstance(save_fn.body[-1].value, ast.Subscript),
      'Last save action is returned bounded digest, after write block')
check(report_binding['bytes'] >= 100000, 'Already-written 104883-byte report necessarily exceeds old digest-return bound')
source_lines = source_bytes.decode('utf-8').splitlines()
for line, fragment in [(182, 'saved=save(target,report)'), (36, 'return bind(path)[0]'), (21, 'assert size < limit, str(path)')]:
    check(source_lines[line - 1].strip() == fragment and f'line {line}' in transcript['output'] and fragment in transcript['output'],
          'Actual transcribed traceback line agrees with exact unchanged source line ' + str(line))
check(transcript['output'].endswith('AssertionError: ' + str(target) + '\r\n'), 'Full transcribed traceback terminates at actual already-written report path')
prior_binding, prior_raw = bind(RUN / 'ADOPTION_PREPARED_PRIOR.py.txt')
delta_binding, delta_raw = bind(RUN / 'ADOPTION_PREEXEC_DELTA.patch')
expected_delta = b''.join(difflib.diff_bytes(difflib.unified_diff, prior_raw.splitlines(keepends=True), source_bytes.splitlines(keepends=True),
                                         fromfile=b'ADOPTION_PREPARED_PRIOR.py.txt', tofile=b'prepare_adoption.py'))
check(delta_raw == expected_delta, 'Actual complete pre-execution source delta preserved')
finalization = load(RUN / 'ROOT_REPORT_FINALIZATION.json')
check(finalization['schema'] == 'root-benign-control-written-report-finalization.v1' and
      finalization['joins_without_modifying'] == report_binding and finalization['original_root_sealer_actual_exit'] == 1,
      'Separate finalization joins exact persisted report without converting original exit one')
check(finalization['root_control_adoption_finalized'] is True and finalization['scientific_execution_released'] is False and
      finalization['replay_authorized'] is False, 'Finalization is limited metadata completion only')
for item in finalization['bindings']:
    check(bind(item['path'], 250000)[0] == item, 'New local finalization edge matches exact actual file ' + Path(item['path']).name)
check(len(finalization['bindings']) == 6, 'Exactly six local finalization bindings; not 273 runtime-input replay')
finalizer_binding, finalizer_bytes = bind(RUN / 'finalize_written_report.py')
finalizer_tree = ast.parse(finalizer_bytes.decode('utf-8'))
finalizer_functions = {node.name: node for node in finalizer_tree.body if isinstance(node, ast.FunctionDef)}
check(finalizer_functions['bind'].args.defaults[0].value == 250000, 'Separate finalizer raises bound for existing report only to 250KB')
check('report_binding,raw=bind(target)' in finalizer_bytes.decode('utf-8') and
      "for name in ['ADOPTION_PREPARED_PRIOR.py.txt','ADOPTION_PREEXEC_DELTA.patch']:" in finalizer_bytes.decode('utf-8'),
      'Finalizer reads existing report, failure and six local edges only')
import_modules = []
for node in ast.walk(finalizer_tree):
    if isinstance(node, ast.Import):
        import_modules.extend(alias.name.split('.')[0] for alias in node.names)
    elif isinstance(node, ast.ImportFrom):
        import_modules.append(node.module.split('.')[0])
check(set(import_modules) <= {'pathlib', 'datetime', 'json', 'hashlib'}, 'Finalizer imports only ordinary standard-library data/file modules')
check(len(report['inputs']) == len({item['path'] for item in report['inputs']}) == finalization['root_input_binding_count'] == 273,
      'Complete persisted root index has 273 unique paths; no indexed input byte is reread')
check(report['schema'] == 'root-adopted-current-host-benign-process-control.v2' and report['source_adopted'] is True and
      report['current_host_two_case_benign_control_passed'] is True, 'Original report retains narrow actual current-host CPU-control scope')
for key in ['original_scientific_environment_validated', 'scientific_execution_released', 'b1_worker_or_ranking_admitted',
            'outer_independent_held_exit_captured', 'replay_authorized']:
    check(report[key] is False, 'Original report keeps ' + key + ' false')
check(report['scientific_results'] == report['new_figures'] == 0, 'Scientific/new-figure counters unchanged at zero')
check(len(report['actual_external_held_exits']) == 5 and report['total_saved_exit_observed_records'] == 7 and report['closed_log_count'] == 10,
      'Existing adopted CPU evidence counts remain five actors/seven saved exits/ten logs')
check(report['outer_tool_exit_code'] == 0 and report['outer_independent_held_exit_captured'] is False,
      'Outer forwarded tool exit remains distinct from independent held outer exit')
bind(HERE / 'FINALIZATION_SCOPE_PREPARED.md')
bind(HERE / 'FINALIZATION_REVIEW_BEFORE_TRANSCRIPT.py.txt')
bind(HERE / 'FINALIZATION_REVIEW_PREEXEC_DELTA.patch')
bind(__file__)
out = {
    'schema': 'independent-local-root-report-finalization-scope-review.v1',
    'reviewed_utc': datetime.now(timezone.utc).isoformat(),
    'reviewer': 'Independent AI; local source/data/AST and exact existing report bytes only',
    'local_finalization_scope_passed': True,
    'joins_original_report': report_binding,
    'joins_separate_finalization': bind(RUN / 'ROOT_REPORT_FINALIZATION.json')[0],
    'original_root_sealer_actual_exit': 1,
    'original_root_sealer_exit_converted_to_zero': False,
    'postwrite_diagnosis': 'Exact writer source closes completed CreateNew report before returned default<100000B bind. Actual valid JSON is104883B; root recorded exit1 at that return.',
    'diagnostic_method': 'Exact original source/control-flow plus root complete visible-tool traceback transcription; source lines182/36/21 and actual root report path independently agree. The tool transcription is post-execution, not a held process capture.',
    'root_input_index_unique_count': 273,
    'old_1877_runtime_checks_replayed': False, 'root_273_indexed_inputs_rehashed': False,
    'producer_fixture_or_winapi_executed': False, 'scientific_execution_or_admission': False,
    'checks': checks, 'bindings': list(records.values()),
    'limits': [
        'The root stated the separate finalizer actual tool exit0; this review independently validates its persisted record/source/byte edges, not a held process exit.',
        'All original source/runtime/log adoption checks completed by the actual first-writer code path is an inference from unchanged straight-line source, valid written report and exact post-write traceback; those content checks are never rerun here.',
        'This limited review reads root index metadata only and does not recheck its273 original scientific/control inputs or the1877 accepted runtime diagnostics.',
        'Original first root sealer exit1 remains. Separate metadata finalization neither reruns the sealer nor alters the104883-byte report.',
        'Benign current-host CPU-control validation remains distinct from B1, original scientific environment, T6, release/resource/lock/predecessor and full fresh scientific execution.'
    ]}
target_out = HERE / 'FINALIZATION_SCOPE_REVIEW.json'
raw = (json.dumps(out, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode('utf-8')
with target_out.open('xb') as stream:
    stream.write(raw)
print(json.dumps({'path': str(target_out), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                  'checks': len(checks), 'bindings': len(records)}, ensure_ascii=False))
