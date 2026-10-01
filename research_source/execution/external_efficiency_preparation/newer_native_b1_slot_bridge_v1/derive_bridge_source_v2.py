"""Offline narrow source repair; v1 files remain immutable, no imports/tests."""
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINS = {'native_lifecycle_bridge.py': 'b1f855bd955799044eadc13fab30bccd4cdf6b75d708a7d152140a16c52d6369',
        'reference_worker_bridge.py': '30629566aef19633f0092283133c159dbb5ecbc051f054ef99444c38aa08c4d3',
        'guardian_exchange.py': 'b1b64af1388dbbd10cb16a5d5386eb8eed47bc4bc04b3a2c77ca6b6c268d8912'}


def replace(text, old, new):
    ending = '\r\n' if '\r\n' in text else '\n'
    old, new = old.replace('\n', ending), new.replace('\n', ending)
    if text.count(old) != 1:
        raise RuntimeError('Unique source block missing: ' + old[:100])
    return text.replace(old, new, 1)


def main():
    original = {}
    for name, expected in PINS.items():
        raw = (HERE / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise RuntimeError('Initial source pin differs')
        original[name] = raw.decode('utf-8')
    life, worker, exchange = (original[name] for name in PINS)
    for old, new in (('reference_worker_bridge.py', 'reference_worker_bridge_v2.py'),
                     ('native_lifecycle_bridge.py', 'native_lifecycle_bridge_v2.py'),
                     ('guardian_exchange.py', 'guardian_exchange_v2.py')):
        life = life.replace(old, new)
        worker = worker.replace(old, new)
        exchange = exchange.replace(old, new)
    exchange = replace(exchange,
        "release['authority_root'] == REVIEWED_EXECUTION_AUTHORITY_PIN and release['plan'] == root['plan'] and\n                release['slot_spec'] == spec_record and release['request'] == spec['request'] and release['bootstrap'] == spec['bootstrap'],",
        "release['scope'] == 'one_native_B1_slot_after_five_layers_and_extra_DAC' and\n                release['authority_root'] == REVIEWED_EXECUTION_AUTHORITY_PIN and release['plan'] == root['plan'] and\n                release['guardian_source'] == _read_exchange(spec)['guardian_source'] and\n                release['predecessors'] == root['predecessor_authorities'] and\n                release['slot_spec'] == spec_record and release['request'] == spec['request'] and release['bootstrap'] == spec['bootstrap'],")
    exchange = replace(exchange,
        "        for key in ('raw_gpu_stdout', 'raw_gpu_stderr', 'raw_memory_stdout', 'raw_memory_stderr'):\n            _read_bound(resource[key])\n",
        "        require(resource['schema'] == 'newer-native-b1-resource-candidate.v1' and\n                issued <= timestamp(resource['sampled_utc']) <= datetime.now(timezone.utc) < expires and\n                resource['commit_limit_bytes'] > 0 and resource['committed_bytes'] >= 0 and\n                resource['available_commit_bytes'] >= 0, 'Saved resource schema/time/integer ranges differ')\n        captured = {key: _read_bound(resource[key]) for key in\n                    ('raw_gpu_stdout', 'raw_gpu_stderr', 'raw_memory_stdout', 'raw_memory_stderr')}\n        require(type(resource['gpu_rows']) is list and\n                [line for line in captured['raw_gpu_stdout'].decode('utf-8', errors='strict').splitlines() if line.strip()] == [],\n                'Bound raw GPU stdout must itself be completely empty; no PID exemptions')\n        memory = parse(captured['raw_memory_stdout'])\n        require(set(memory) == {'boot_utc_ticks', 'commit_limit_bytes', 'committed_bytes'} and\n                all(type(value) is str and value.isdecimal() for value in memory.values()) and\n                all(int(memory[key]) == resource[key] for key in memory), 'Saved raw memory integer associations differ')\n")
    worker = replace(worker,
        '    return {"ack": handshake_record["ack"], "raw_request_sha256": digest(request_raw),\n',
        '    exchange = lifecycle._load_guardian_exchange(spec)\n    grant_raw = lifecycle.read_bound(ack["final_admission"])\n    exchange._check_authority(handshake_record["spec"], spec, lifecycle.parse(grant_raw))\n    require(lifecycle.read_bound(ack["final_admission"]) == grant_raw, "Guardian grant changed immediately before original imports")\n    return {"ack": handshake_record["ack"], "raw_request_sha256": digest(request_raw),\n')
    values = {'native_lifecycle_bridge_v2.py': life, 'reference_worker_bridge_v2.py': worker, 'guardian_exchange_v2.py': exchange}
    outputs = []
    for old_name, new_name in zip(PINS, values):
        raw = values[new_name].encode('utf-8')
        delta = ''.join(difflib.unified_diff(original[old_name].splitlines(True), values[new_name].splitlines(True),
                       fromfile=old_name, tofile=new_name)).encode('utf-8')
        for name, body in ((new_name, raw), (old_name.replace('.py', '_v1_to_v2.patch'), delta)):
            with (HERE / name).open('xb') as stream:
                stream.write(body)
                stream.flush()
            outputs.append({'path': str(HERE / name), 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()})
    report = {'schema': 'b1-bridge-v2-offline-source-derivation.v1',
              'inputs': [{'path': str(HERE / name), 'sha256': expected} for name, expected in PINS.items()],
              'outputs': outputs, 'source_module_import_or_execution': False,
              'OS_API_native_scientific_calls': False, 'old_files_mutated': False,
              'controls_or_old_suite_run': False,
              'scope': 'Only v2 file paths and exact proposed release/raw-resource association plus final worker pre-source grant/TTL reread'}
    body = (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    with (HERE / 'SOURCE_DERIVATION_V2.json').open('xb') as stream:
        stream.write(body)
        stream.flush()
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
