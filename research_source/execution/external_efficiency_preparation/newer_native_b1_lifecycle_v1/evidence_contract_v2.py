"""Bound saved-record association only; not an immutable execution/admission root.

This stdlib checker reads exact small control/source/image bytes and the four
fresh candidate artifacts. It does not run the original candidate validator,
parse NPY/ledger semantics, hold process handles, call APIs or prove that caller
records are trustworthy execution evidence. All admission/ranking stays closed.
"""
import copy
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREPARATION = HERE.parent
WORKER = PREPARATION / 'newer_native_b1_worker_v2' / 'reference_worker.py'
HELPER = PREPARATION / 'newer_native_process_evidence_v2' / 'windows_process_evidence.py'
HELPER_SHA = 'cc090bec1429ab429b556200597acedfa13c33e878627155b0cc9f8098c9f5d2'
MAX_CONTROL_BYTES = 8 * 1024 * 1024
ARTIFACT_NAMES = {'descriptors.npy', 'image_content_sha256.jsonl',
                  'strict_complete_final_load.json', 'runtime_actual.json'}
FILETIME_TO_DOTNET_TICKS = 504911232000000000


class ClosedExecutionGate(RuntimeError):
    pass


def _closed_admission(*args, **kwargs):
    raise ClosedExecutionGate('Saved-record relation cannot grant B1 execution, admission or ranking')


def require(value, message):
    if not value:
        raise RuntimeError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def parse(raw):
    def pairs(items):
        out = {}
        for key, item in items:
            require(key not in out, 'Duplicate JSON key')
            out[key] = item
        return out
    return json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(RuntimeError('Nonfinite JSON')))


def descriptor_shape(item):
    require(type(item) is dict and set(item) == {'path', 'bytes', 'sha256'}, 'Exact descriptor required')
    require(type(item['path']) is str and Path(item['path']).is_absolute(), 'Absolute path required')
    require(type(item['bytes']) is int and item['bytes'] >= 0, 'Exact nonnegative integer bytes required')
    require(type(item['sha256']) is str and len(item['sha256']) == 64 and
            all(c in '0123456789abcdef' for c in item['sha256']), 'Exact SHA256 required')


def read_bound_control(item):
    descriptor_shape(item)
    require(item['bytes'] <= MAX_CONTROL_BYTES, 'Oversize control/source/image')
    path = Path(item['path'])
    require(path == path.resolve(strict=True), 'Exact resolved path required')
    before = path.stat()
    require(before.st_size == item['bytes'], 'Actual size differs before control read')
    with path.open('rb') as f:
        raw = f.read(item['bytes'] + 1)
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'Control changed during read')
    require(len(raw) == item['bytes'] and sha(raw) == item['sha256'], 'Actual control bytes differ')
    return raw


def bind_fresh_candidate_artifact(item, native, expected_name):
    descriptor_shape(item)
    path = Path(item['path'])
    require(expected_name in ARTIFACT_NAMES and path == native / expected_name and
            path == path.resolve(strict=True), 'Only four exact fresh native candidate artifact paths allowed')
    before = path.stat()
    require(before.st_size == item['bytes'], 'Actual candidate artifact size differs before read')
    with path.open('rb') as f:
        actual = hashlib.file_digest(f, 'sha256').hexdigest()
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) and actual == item['sha256'],
            'Actual candidate artifact bytes differ')
    return {'actual_bytes_bound': True, 'scientific_artifact_semantics_revalidated': False}


def identity_shape(identity):
    require(type(identity) is dict and set(identity) == {
        'pid', 'creation_filetime_100ns', 'creation_utc_ticks', 'image'}, 'Exact retained identity fields required')
    for key in ('pid', 'creation_filetime_100ns', 'creation_utc_ticks'):
        require(type(identity[key]) is int and identity[key] > 0, 'Positive exact integer PID/time required')
    require(identity['creation_utc_ticks'] == identity['creation_filetime_100ns'] + FILETIME_TO_DOTNET_TICKS and
            type(identity['image']) is str and Path(identity['image']).is_absolute(), 'Exact identity time/image relation required')


def exit_relation(exit_value, identity):
    identity_shape(identity)
    require(type(exit_value) is dict and canonical(exit_value['identity']) == canonical(identity) and
            type(exit_value['wait_result']) is int and exit_value['wait_result'] == 0 and
            type(exit_value['exit_code_unsigned_dword']) is int and exit_value['exit_code_unsigned_dword'] == 0,
            'Saved same-identity signaled exit0 relation differs')
    require(type(exit_value['pid']) is int and exit_value['pid'] == identity['pid'] and
            type(exit_value['creation_filetime_100ns']) is int and
            exit_value['creation_filetime_100ns'] == identity['creation_filetime_100ns'] and
            type(exit_value['creation_utc_ticks']) is int and exit_value['creation_utc_ticks'] == identity['creation_utc_ticks'],
            'Saved exit identity creation differs')
    require(type(exit_value['exit_filetime_100ns']) is int and
            exit_value['exit_filetime_100ns'] >= identity['creation_filetime_100ns'] and
            type(exit_value['exit_utc_ticks']) is int and
            exit_value['exit_utc_ticks'] == exit_value['exit_filetime_100ns'] + FILETIME_TO_DOTNET_TICKS and
            exit_value['same_retained_handle_pid_creation_verified'] is True,
            'Saved raw integer exit-time relation differs')


def observations_relation(values, identity, parent_identity, image, command):
    require(type(values) is list and len(values) == 2 and canonical(values[0]) == canonical(values[1]),
            'Exactly two equal complete observations required')
    for observed in values:
        require(type(observed) is dict and all(type(observed[key]) is int for key in
                ('pid', 'parent_pid', 'creation_filetime_100ns', 'creation_utc_ticks')) and
                observed['pid'] == identity['pid'] and
                observed['creation_filetime_100ns'] == identity['creation_filetime_100ns'] and
                observed['creation_utc_ticks'] == identity['creation_utc_ticks'] and
                observed['creation_utc_ticks'] >= parent_identity['creation_utc_ticks'] and
                observed['command_line'] == command and observed['parent_pid'] == parent_identity['pid'] and
                canonical(observed['held_now']) == canonical(identity) and
                canonical(observed['fresh_after']) == canonical(identity) and
                os.path.samefile(observed['image'], image['path']) and
                os.path.samefile(observed['image'], identity['image']), 'Saved dual observation/parent/image/command relation differs')


def controller_observations_relation(values, identity, image, command):
    require(type(values) is list and len(values) == 2 and canonical(values[0]) == canonical(values[1]),
            'Exactly two equal complete controller observations required')
    for observed in values:
        require(type(observed) is dict and all(type(observed[key]) is int for key in
                ('pid', 'parent_pid', 'creation_filetime_100ns', 'creation_utc_ticks')) and
                observed['pid'] == identity['pid'] and
                observed['creation_filetime_100ns'] == identity['creation_filetime_100ns'] and
                observed['creation_utc_ticks'] == identity['creation_utc_ticks'] and
                observed['command_line'] == command and canonical(observed['held_now']) == canonical(identity) and
                canonical(observed['fresh_after']) == canonical(identity) and
                os.path.samefile(observed['image'], image['path']) and
                os.path.samefile(observed['image'], identity['image']), 'Saved controller live command/image/creation relation differs')


def check_saved_candidate_relation(candidate_record):
    """Available pure association check; never execution/admission authority."""
    candidate_raw = read_bound_control(candidate_record)
    candidate = parse(candidate_raw)
    require(candidate['schema'] == 'newer-native-b1-lifecycle-candidate.v1', 'Wrong lifecycle candidate schema')
    spec_raw = read_bound_control(candidate['spec']); spec = parse(spec_raw)
    require(type(spec) is dict and set(spec) == {
        'schema', 'method', 'seed', 'nonce', 'run_name', 'request', 'prepared',
        'bootstrap', 'handshake_directory', 'worker_control_directory', 'native_directory'}, 'Exact slot field set required')
    require(spec['schema'] == 'newer-native-b1-lifecycle-slot.v1' and candidate['nonce'] == spec['nonce'] and
            candidate['request'] == spec['request'] and candidate['bootstrap'] == spec['bootstrap'], 'Slot association differs')
    require(spec['method'] in ('CAMP', 'DAC') and type(spec['seed']) is int and spec['seed'] in (1, 2, 3), 'One fixed slot required')
    require(type(spec['nonce']) is str and len(spec['nonce']) == 64 and
            all(c in '0123456789abcdef' for c in spec['nonce']), 'Exact declared nonce required')
    expected_run = spec['method'].lower() + '_seed' + str(spec['seed']) + '_' + spec['nonce']
    require(spec['run_name'] == expected_run, 'Exact run-name association differs')
    attempt = HERE / 'runs' / spec['run_name']
    handshake = attempt / 'handshake'
    body = WORKER.parent / 'runs' / spec['run_name']
    original = {'CAMP': 'camp_independent_evaluation_v3', 'DAC': 'dac_independent_evaluation_v2'}[spec['method']]
    native = PREPARATION.parent / original / 'b1_reference_runs' / spec['run_name']
    require(Path(candidate_record['path']) == attempt / 'lifecycle_candidate.json' and
            Path(spec['handshake_directory']) == handshake and Path(spec['worker_control_directory']) == body and
            Path(spec['native_directory']) == native, 'Exact separate registered lifecycle/body/native roots required')
    request_raw = read_bound_control(spec['request']); request = parse(request_raw)
    require(request['schema'] == 'newer-native-b1-request.v1' and
            request_raw == canonical(request) + b'\n' and spec_raw == canonical(spec) + b'\n' and
            request['method'] == spec['method'] and type(request['seed']) is int and request['seed'] == spec['seed'] and
            request['prepared'] == spec['prepared'] and candidate['request_raw_sha256'] == sha(request_raw),
            'Raw canonical request/slot association differs')
    prepared = parse(read_bound_control(spec['prepared']))
    require(type(prepared) is dict, 'Original prepared mapping required')
    seal_body = dict(prepared)
    original_seal = seal_body.pop('payload_sha256', None)
    require(type(original_seal) is str and sha(canonical(seal_body)) == original_seal and
            type(prepared['settings']['batch_size']) is int and prepared['settings']['batch_size'] == 16,
            'Original prepared payload seal/batch16 relation differs')
    bootstrap_raw = read_bound_control(spec['bootstrap']); bootstrap = parse(bootstrap_raw)
    require(bootstrap_raw == canonical(bootstrap) + b'\n', 'Canonical bootstrap bytes required')
    require(type(bootstrap) is dict and set(bootstrap) == {
        'schema', 'topology', 'launcher_image', 'interpreter_image', 'controller_image',
        'controller_complete_command', 'launcher_complete_command', 'interpreter_complete_command',
        'worker_source', 'controller_source', 'process_helper_source'} and
        bootstrap['schema'] == 'newer-native-b1-bootstrap-candidate.v1', 'Exact bootstrap field set/schema required')
    for name in ('launcher_image', 'interpreter_image', 'controller_image', 'worker_source', 'controller_source', 'process_helper_source'):
        read_bound_control(bootstrap[name])
    require(Path(bootstrap['worker_source']['path']) == WORKER and
            Path(bootstrap['controller_source']['path']) == HERE / 'native_lifecycle.py' and
            Path(bootstrap['process_helper_source']['path']) == HELPER and
            bootstrap['process_helper_source']['sha256'] == HELPER_SHA and
            bootstrap['launcher_image']['path'] == prepared['python'] == prepared['runtime']['executable'] and
            bootstrap['launcher_image']['sha256'] == prepared['runtime']['interpreter_sha256'] and
            bootstrap['launcher_image']['path'] != bootstrap['interpreter_image']['path'],
            'Saved source paths/pin and original runtime image/SHA relation differ')
    for name in ('controller_complete_command', 'launcher_complete_command', 'interpreter_complete_command'):
        require(type(bootstrap[name]) is str and bootstrap[name] and '\x00' not in bootstrap[name], 'Complete predeclared command required')
    require(bootstrap['topology'] == 'distinct_native_redirector_child', 'Saved strict native topology required')
    ready_raw = read_bound_control(candidate['ready']); ready = parse(ready_raw)
    ack_raw = read_bound_control(candidate['ack']); ack = parse(ack_raw)
    require(ready['schema'] == 'newer-native-b1-worker-ready.v1' and
            ack['schema'] == 'newer-native-b1-external-ack.v1' and
            Path(candidate['ready']['path']) == handshake / 'worker.ready.json' and
            Path(candidate['ack']['path']) == handshake / 'controller.ack.json' and
            ack['ready'] == candidate['ready'] and ack['spec'] == ready['spec'] == candidate['spec'] and
            ack['bootstrap'] == spec['bootstrap'] and ack['nonce'] == ready['nonce'] == spec['nonce'] and
            ack['request'] == ready['request'] == spec['request'] and
            ack['spec_raw_sha256'] == ready['spec_raw_sha256'] == sha(spec_raw) and
            ack['request_raw_sha256'] == ready['request_raw_sha256'] == sha(request_raw), 'ACK/raw-source/request/nonce relation differs')
    identities = {role: candidate[role + '_identity'] for role in ('controller', 'launcher', 'interpreter')}
    for role, identity in identities.items():
        identity_shape(identity)
        require(canonical(identity) == canonical(ack[role + '_identity']), 'ACK captured identity differs')
    require(len({item['pid'] for item in identities.values()}) == 3 and
            type(ready['pid']) is int and ready['pid'] == identities['interpreter']['pid'] and
            canonical(ready['identity']) == canonical(identities['interpreter']) and
            ready['original_source_or_science_imported'] is False and
            ack['candidate_consistency_is_not_execution_authority'] is True,
            'Distinct three actors and worker os.getpid relation required')
    controller_observations_relation(ack['controller_observations'], identities['controller'],
                                    bootstrap['controller_image'], bootstrap['controller_complete_command'])
    observations_relation(ack['launcher_observations'], identities['launcher'], identities['controller'],
                          bootstrap['launcher_image'], bootstrap['launcher_complete_command'])
    observations_relation(ack['interpreter_observations'], identities['interpreter'], identities['launcher'],
                          bootstrap['interpreter_image'], bootstrap['interpreter_complete_command'])
    require(ready['self_snapshot'] == ack['interpreter_observations'][-1], 'Ready full snapshot differs')
    exit_relation(candidate['launcher_exit'], identities['launcher'])
    exit_relation(candidate['interpreter_exit'], identities['interpreter'])
    require(type(candidate['separate_popen_exit_code']) is int and candidate['separate_popen_exit_code'] == 0,
            'Separate saved Popen0 required; it never replaces held exits')
    final_raw = read_bound_control(ack['final_admission']); final = parse(final_raw)
    require(final['schema'] == 'newer-native-b1-pre-ack-final-admission-candidate.v1' and
            final['spec'] == candidate['spec'] and final['request'] == spec['request'] and
            final['bootstrap'] == spec['bootstrap'] and final['nonce'] == spec['nonce'] and
            canonical(final['actual_identities']) == canonical(identities) and final['measurement_admitted'] is False and
            final['candidate_consistency_is_not_execution_authority'] is True, 'Saved final-admission association differs')
    require(type(candidate['closed_logs']) is list and len(candidate['closed_logs']) == 2, 'Exactly two parent-owned redirected logs required')
    expected_logs = {str(attempt / name) for name in ('worker.stdout.log', 'worker.stderr.log')}
    require({item['path'] for item in candidate['closed_logs']} == expected_logs, 'Saved log paths differ')
    for item in candidate['closed_logs']:
        record = {key: item[key] for key in ('path', 'bytes', 'sha256')}
        read_bound_control(record)
        require(item['read_lock_denied_write_delete'] is True and item['controller_streams_closed'] is True,
                'Saved closed-stream/read-sharing flags differ; this checker does not execute the API')
    require(set(candidate['worker_candidates']) == {'candidate.json', 'candidate_consistency.json', 'return_intent.json'},
            'Exact worker candidate record set required')
    records, values = {}, {}
    for name, record in candidate['worker_candidates'].items():
        require(Path(record['path']) == body / name, 'Worker candidate path differs')
        records[name] = record; values[name] = parse(read_bound_control(record))
    wc = values['candidate.json']; consistency = values['candidate_consistency.json']; intent = values['return_intent.json']
    require(wc['schema'] == 'newer-native-b1-candidate.v1' and wc['method'] == spec['method'] and
            type(wc['seed']) is int and wc['seed'] == spec['seed'] and
            wc['request_canonical_sha256'] == sha(canonical(request)) and
            canonical(wc['source_recipe']) == canonical(request['source_recipe']) and
            canonical(wc['derivation']) == canonical(request['derivation']), 'Original worker candidate/request relation differs')
    require(set(wc['artifacts']) == ARTIFACT_NAMES, 'Exactly four original candidate artifacts required')
    for name, record in wc['artifacts'].items():
        bind_fresh_candidate_artifact(record, native, name)
    require(consistency['candidate_artifact_consistency'] is True and intent['candidate'] == records['candidate.json'] and
            intent['consistency'] == records['candidate_consistency.json'] and intent['request'] == spec['request'] and
            type(intent['return_intent']) is int and intent['return_intent'] == 0 and
            intent['actual_process_exit_not_yet_observed'] is True,
            'Saved original consistency/return intent relation differs; these are not independent scientific validation')
    for value in (wc, consistency, intent, candidate):
        require(value['measurement_admitted'] is False and value['full_t6_complete'] is False and
                value['manuscript_result'] is False, 'Saved candidate must not claim admission/T6/manuscript completion')
    return {'schema': 'newer-native-b1-saved-reference-consistency.v1', 'candidate': copy.deepcopy(candidate_record),
            'saved_record_associations_verified': True, 'actual_four_artifact_sha_size_bound': True,
            'original_scientific_candidate_validator_called': False, 'npy_or_ledger_semantics_revalidated': False,
            'process_apis_or_handles_executed_by_this_checker': False,
            'immutable_independent_execution_root_implemented': False, 'independent_execution_proven': False,
            'execution_permission': False, 'measurement_admitted': False,
            'fresh_full_gallery_proven': False, 'full_dataset_online_accuracy_proven': False,
            'full_t6_complete': False, 'manuscript_result': False}


def admit_reference(*args, **kwargs):
    _closed_admission(*args, **kwargs)


def measure_task_ranking(*args, **kwargs):
    _closed_admission(*args, **kwargs)


if __name__ == '__main__':
    raise ClosedExecutionGate('Saved-record consistency source only; no execution or admission CLI')
