"""Offline exact pinned source derivation; no module import/API/old tests."""
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREP = HERE.parent
LIFE = PREP / 'newer_native_b1_lifecycle_v1' / 'native_lifecycle.py'
WORK = PREP / 'newer_native_b1_worker_v2' / 'reference_worker.py'
PINS = {'lifecycle': '407eb2163451877e03578a91a3e496126d49be1141607855eb279d1641469d59',
        'worker': '313da5932a3b5c9f77eeeceb810fc741642a390b9672ca0d0f5726c2aa8ef2d7'}


def replace(text, old, new):
    ending = '\r\n' if '\r\n' in text else '\n'
    old, new = old.replace('\n', ending), new.replace('\n', ending)
    if text.count(old) != 1:
        raise RuntimeError('Unique exact source block not found: ' + old[:80])
    return text.replace(old, new, 1)


def replace_function(text, name, new):
    start = text.index('def ' + name + '(')
    ending = '\r\n' if '\r\n' in text else '\n'
    end = text.find(ending + ending + 'def ', start)
    if end < 0:
        raise RuntimeError('Function boundary missing')
    return replace(text, text[start:end].replace('\r\n', '\n'), new.rstrip('\n'))


def guard_function(text, name, signature, arguments):
    return replace(text, signature + '\n', signature + '\n    _closed_execution_admission(' + arguments + ')\n')


def main():
    raw_life, raw_work = LIFE.read_bytes(), WORK.read_bytes()
    if hashlib.sha256(raw_life).hexdigest() != PINS['lifecycle'] or hashlib.sha256(raw_work).hexdigest() != PINS['worker']:
        raise RuntimeError('Original adopted source pin differs')
    original_life, original_work = raw_life.decode('utf-8'), raw_work.decode('utf-8')
    life, work = original_life, original_work
    literal_here = "HERE = Path(r'C:\\OneDrive\\文档\\LGM-GAME\\outputs\\paper_evidence_rebuild_20260914\\execution\\external_efficiency_preparation\\newer_native_b1_slot_bridge_v1')"
    life = replace(life, 'HERE = Path(__file__).resolve().parent', literal_here)
    life = replace(life, "WORKER = PREPARATION / 'newer_native_b1_worker_v2' / 'reference_worker.py'", "WORKER = HERE / 'reference_worker_bridge.py'")
    life = replace(life, "'bootstrap', 'handshake_directory', 'worker_control_directory', 'native_directory'},", "'bootstrap', 'handshake_directory', 'worker_control_directory', 'native_directory', 'guardian_exchange'},")
    life = replace(life, "spec['schema'] == 'newer-native-b1-lifecycle-slot.v1'", "spec['schema'] == 'newer-native-b1-guardian-slot-candidate.v1'")
    life = replace(life, "for name in ('request', 'prepared', 'bootstrap'):", "for name in ('request', 'prepared', 'bootstrap', 'guardian_exchange'):")
    life = replace(life, "'worker_source', 'controller_source', 'process_helper_source'},", "'worker_source', 'controller_source', 'process_helper_source', 'guardian_exchange_source'},")
    life = replace(life, "bootstrap['schema'] == 'newer-native-b1-bootstrap-candidate.v1'", "bootstrap['schema'] == 'newer-native-b1-guardian-bootstrap-candidate.v1'")
    life = replace(life, "    handshake = Path(spec['handshake_directory'])\n    body = Path(spec['worker_control_directory'])", "    require_descriptor(bootstrap['guardian_exchange_source'])\n    require(bootstrap['guardian_exchange_source']['path'] == str(HERE / 'guardian_exchange.py'), 'Exact new exchange source required')\n    handshake = Path(spec['handshake_directory'])\n    body = Path(spec['worker_control_directory'])")
    life = replace(life, "Path(bootstrap['controller_source']['path']) == Path(__file__).resolve()", "Path(bootstrap['controller_source']['path']) == HERE / 'native_lifecycle_bridge.py'")
    life = replace(life, "require(body.parent == WORKER.parent / 'runs'", "require(body.parent == WORKER.parent / 'worker_runs'")
    for name, signature, arguments in (
        ('read_bound', 'def read_bound(record):', 'record'),
        ('file_descriptor', 'def file_descriptor(path):', 'path'),
        ('write_new_json', 'def write_new_json(path, value):', 'path, value'),
        ('read_unbound_small', 'def read_unbound_small(path):', 'path')):
        life = guard_function(life, name, signature, arguments)
    life = replace(life, "for name in ('launcher_image', 'interpreter_image', 'controller_image', 'worker_source', 'controller_source', 'process_helper_source'):\n        read_bound(bootstrap[name])\n    require(os.path.samefile", "for name in ('launcher_image', 'interpreter_image', 'controller_image', 'worker_source', 'controller_source', 'process_helper_source'):\n        read_bound(bootstrap[name])\n    exchange = _load_guardian_exchange()\n    exchange._read_exchange(spec)\n    require(os.path.samefile")
    life = replace_function(life, '_final_admission_before_ack', '''def _load_guardian_exchange(specification):
    _closed_execution_admission(specification)
    path = HERE / 'guardian_exchange.py'
    bootstrap = parse(read_bound(specification['bootstrap']))
    require_descriptor(bootstrap['guardian_exchange_source'])
    require(bootstrap['guardian_exchange_source']['path'] == str(path), 'Exact declared exchange module required')
    read_bound(bootstrap['guardian_exchange_source'])
    spec = importlib.util.spec_from_file_location('_new_b1_guardian_exchange', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(Path(module.__file__).resolve() == path.resolve(strict=True), 'Exact new guardian exchange source required')
    return module


def _final_admission_before_ack(spec_record, spec, bootstrap, h, api, ledger, me, launcher, interpreter):
    _closed_execution_admission(spec_record, spec, bootstrap, h, api, ledger, me, launcher, interpreter)
    exchange = _load_guardian_exchange(spec)
    return exchange._controller_preack(h, api, ledger, me, launcher, interpreter, spec_record, spec, bootstrap)
''')
    life = replace_function(life, 'final_admission_relation', '''def final_admission_relation(record, value, spec_record, spec, identities):
    """Pure association of NEW proposed grant, still no execution authority."""
    require_descriptor(record)
    require(type(value) is dict and set(value) == {
        'schema', 'spec', 'request', 'bootstrap', 'nonce', 'release', 'authority_root',
        'guardian_identity', 'controller_identity', 'launcher_identity', 'interpreter_identity',
        'resource', 'actual_retained_lock_identity', 'execute_original_reference', 'measurement_admitted', 'scope'},
        'Exact distinct guardian proposed grant keys required; old eight-field candidate rejected')
    require(value['schema'] == 'newer-native-b1-guardian-preack-grant-proposal.v1' and
            value['spec'] == spec_record and value['request'] == spec['request'] and
            value['bootstrap'] == spec['bootstrap'] and value['nonce'] == spec['nonce'] and
            value['execute_original_reference'] is True and value['measurement_admitted'] is False,
            'Proposed grant saved association differs')
    for name in ('controller', 'launcher', 'interpreter'):
        require(value[name + '_identity'] == identities[name], 'Proposed grant captured identity differs')
    for name in ('release', 'authority_root', 'resource'):
        require_descriptor(value[name])
    return {'reference_consistency_only': True, 'execution_permission': False,
            'actual_guardian_and_issuer_validation_required': True}
''')
    life = replace(life, "        ledger.emit('worker_post_ack_live_chain_and_bytes_confirmed'", "        exchange = _load_guardian_exchange()\n        exchange._worker_validate_grant(h, api, ledger, me, spec_record, spec, bootstrap, ack['final_admission'])\n        ledger.emit('worker_post_ack_live_chain_and_bytes_confirmed'")
    life = replace(life, "        controller_observations = _confirm_controller_live(me, bootstrap)\n", "        controller_observations = _confirm_controller_live(me, bootstrap)\n        exchange = _load_guardian_exchange()\n        exchange._initial_controller_check(h, api, ledger, me, spec_record, spec, bootstrap)\n")
    life = replace(life, "        final_admission = _final_admission_before_ack(spec_record, {\n            'controller': me.identity, 'launcher': launcher.identity, 'interpreter': interpreter.identity})", "        final_admission = _final_admission_before_ack(spec_record, spec, bootstrap, h, api, ledger, me, launcher, interpreter)")
    life = replace(life, "'schema': 'newer-native-b1-external-ack.v1', 'nonce': spec['nonce'],", "'schema': 'newer-native-b1-guardian-external-ack-proposal.v1', 'nonce': spec['nonce'],\n            'guardian_exchange': spec['guardian_exchange'],")
    life = replace(life, "ack['schema'] == 'newer-native-b1-external-ack.v1'", "ack['schema'] == 'newer-native-b1-guardian-external-ack-proposal.v1' and\n                ack['guardian_exchange'] == spec['guardian_exchange']")
    # The worker ready/schema still represents candidate identity, not an issuer.
    life = replace(life, 'def main(*args, **kwargs):\n    _closed_execution_admission(*args, **kwargs)', '''def _bridge_cli(arguments=None):
    _closed_execution_admission(arguments)
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--guardian-slot-spec', required=True)
    parser.add_argument('--guardian-control-directory', required=True)
    args = parser.parse_args(arguments)
    spec_raw, spec = read_unbound_small(args.guardian_slot_spec)
    spec_record = file_descriptor(args.guardian_slot_spec)
    require(read_bound(spec_record) == spec_raw, 'Discovered CLI spec bytes changed')
    exchange = _load_guardian_exchange()
    declaration = exchange._read_exchange(spec)
    require(args.guardian_control_directory == declaration['guardian_control_directory'], 'Guardian control directory differs')
    return_record = _run_native_slot(spec_record)
    returned = parse(read_bound(return_record))
    candidate = parse(read_bound(returned['candidate']))
    require(candidate['spec'] == spec_record and candidate['request'] == spec['request'] and
            candidate['measurement_admitted'] is False, 'Preserved slot candidate differs')
    write_new_json(Path(args.guardian_control_directory) / 'slot_candidate.json', candidate)
    # This is only return intent; outer guardian must independently observe exit.
    return 0


def main(*args, **kwargs):
    _closed_execution_admission(*args, **kwargs)
    return _bridge_cli(*args, **kwargs)''')
    life = replace(life, "    raise ClosedExecutionGate('Source-only native B1 lifecycle v1; no CLI execution or admission')", "    raise ClosedExecutionGate('Source-only guardian one-slot bridge; no runtime or scientific admission')\n    raise SystemExit(_bridge_cli())")
    if life.count('_load_guardian_exchange()') != 4:
        raise RuntimeError('Four known new exchange call sites required')
    life = life.replace('_load_guardian_exchange()', '_load_guardian_exchange(spec)')
    work = replace(work, 'HERE = Path(__file__).resolve().parent', literal_here)
    work = replace(work, 'path = PREPARATION / "newer_native_b1_lifecycle_v1" / "native_lifecycle.py"', 'path = HERE / "native_lifecycle_bridge.py"')
    work = replace(work, 'control.parent == HERE / "runs"', 'control.parent == HERE / "worker_runs"')
    work = replace(work, 'ack["schema"] == "newer-native-b1-external-ack.v1"', 'ack["schema"] == "newer-native-b1-guardian-external-ack-proposal.v1" and\n            ack["guardian_exchange"] == spec["guardian_exchange"]')
    for signature, arguments in (('def descriptor(path):', 'path'), ('def read_control(record):', 'record'), ('def write_new_json(path, value):', 'path, value')):
        work = guard_function(work, '', signature, arguments)
    outputs = [('native_lifecycle_bridge.py', life.encode('utf-8')),
               ('reference_worker_bridge.py', work.encode('utf-8')),
               ('lifecycle_original_to_bridge.patch', ''.join(difflib.unified_diff(original_life.splitlines(True), life.splitlines(True),
                    fromfile=str(LIFE), tofile='native_lifecycle_bridge.py')).encode('utf-8')),
               ('worker_original_to_bridge.patch', ''.join(difflib.unified_diff(original_work.splitlines(True), work.splitlines(True),
                    fromfile=str(WORK), tofile='reference_worker_bridge.py')).encode('utf-8'))]
    for name, raw in outputs:
        with (HERE / name).open('xb') as stream:
            stream.write(raw)
            stream.flush()
    report = {'schema': 'b1-bridge-offline-source-derivation.v1',
              'inputs': [{'path': str(path), 'bytes': len(raw), 'sha256': PINS[key]}
                         for key, path, raw in (('lifecycle', LIFE, raw_life), ('worker', WORK, raw_work))],
              'outputs': [{'path': str(HERE / name), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} for name, raw in outputs],
              'source_module_import_or_execution': False, 'OS_API_native_scientific_calls': False,
              'old_files_mutated': False, 'old_suite_replay': False,
              'scope': 'Full byte-derived one-slot/controller and worker source with guardian IPC wiring; all runtime guards remain unconditional'}
    raw = (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    with (HERE / 'SOURCE_DERIVATION.json').open('xb') as stream:
        stream.write(raw)
        stream.flush()
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
