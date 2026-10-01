"""Stdlib source/control binding for seven native T1 workers; no launch at import."""
from __future__ import annotations
from functools import lru_cache
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent / 'external_t1_driver_v2'
NATIVE_SHA = '0b6e8383f4a57007e693e431c4d524f89856fad0fc7e3b4e6364a1304d030677'
LIFETIME = HERE.parents[1] / 'dac_training_control_v2'
LIFETIME_PINS = {'dac2_gates.py': '24a33671e5d680d271c04f0bf117d6a6923180f2ef8cec997b2fae064d87a228',
    'dac2_contracts.py': '5e527597e5bf2f41fef21d8ba8699c1c2ddd1323a8279447e049bc9f680a635c'}

@lru_cache(maxsize=1)
def runtime_helpers():
    path = NATIVE / 'SOURCE_MANIFEST.json'
    if hashlib.sha256(path.read_bytes()).hexdigest() != NATIVE_SHA:
        raise RuntimeError('Frozen native v2 manifest changed')
    source = json.loads(path.read_text(encoding='utf-8'))
    by_path = {Path(row['path']): row for row in source['files']}
    contract_path = NATIVE / 'driver_contract.py'
    if hashlib.sha256(contract_path.read_bytes()).hexdigest() != by_path[contract_path]['sha256']:
        raise RuntimeError('Frozen native contract changed')
    if 'driver_contract' in sys.modules and Path(sys.modules['driver_contract'].__file__).resolve() != contract_path:
        raise RuntimeError('Foreign driver_contract namespace')
    sys.path.insert(0, str(NATIVE))
    native = importlib.import_module('driver_contract')
    native.verify_sources()
    for name, expected in LIFETIME_PINS.items():
        target = LIFETIME / name
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            raise RuntimeError('Frozen Windows lifetime helper changed: ' + name)
        namespace = target.stem
        if namespace in sys.modules and Path(sys.modules[namespace].__file__).resolve() != target:
            raise RuntimeError('Foreign lifetime namespace')
    sys.path.insert(0, str(LIFETIME))
    life = importlib.import_module('dac2_gates')
    return native, native.common(), native.adapters()[0], life

def source_manifest():
    native, k, b, life = runtime_helpers()
    value = k.read(HERE / 'SOURCE_MANIFEST.json')
    k.require(value['scientific_execution_performed'] is False, 'Mislabelled source preparation')
    for item in value['files']:
        k.verify_record(item)
    return value

def no_science():
    runtime_helpers()[0].no_science_loaded()

def bound(path, expected=None):
    native, k, _, _ = runtime_helpers()
    value, artifact = native.read_bound_json(path)
    if expected is not None:
        k.require(artifact == expected, 'Captured control bytes changed')
    return value, artifact

def atomic_new_json(path, value):
    """Publish a closed complete JSON; Windows rename never overwrites a target."""
    _, k, _, _ = runtime_helpers()
    path = Path(path)
    pending = path.with_name(path.name + '.pending')
    k.require(not path.exists() and not pending.exists(), 'Atomic output must be new')
    k.write_new(pending, value)
    os.rename(pending, path)
    parsed, artifact = bound(path)
    k.require(parsed == value, 'Published bytes differ from intended object')
    return artifact

def native_driver():
    native, k, _, _ = runtime_helpers()
    path = NATIVE / 'driver.py'
    # Native source_manifest verifies its full declared source before import.
    native.verify_sources()
    spec = importlib.util.spec_from_file_location('external_t1_frozen_v2_driver', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

def admit(plan_path, release_path, expected_plan=None, expected_release=None):
    no_science()
    source_manifest()
    native, k, b, _ = runtime_helpers()
    plan, plan_record = bound(plan_path, expected_plan)
    release, release_record = bound(release_path, expected_release)
    ids = [row['run_id'] for row in b.slots()]
    k.require(release.get('allow_run') is True and release.get('plan') == plan_record and
              release.get('allowed_run_ids') == ids, 'Release must admit exactly the seven frozen slots in order')
    bindings = []
    for run_id in ids:
        verified_plan, binding = native.verify_plan(plan_path, run_id, expected_record=plan_record)
        k.require(verified_plan == plan, 'Different plan value across slots')
        bindings.append(binding)
    preceding, _ = native.admitted_predecessors()
    k.require(preceding == plan['predecessors'], 'Five predecessor bindings changed')
    for artifact in (plan_record, release_record):
        k.verify_record(artifact)
    return plan, release, plan_record, release_record, bindings

def before_slot(plan, binding, records):
    native, k, _, _ = runtime_helpers()
    no_science()
    source_manifest()
    for item in records:
        k.verify_record(item)
    preceding, owner = native.admitted_predecessors()
    k.require(preceding == plan['predecessors'], 'Five predecessor proofs changed before a slot')
    memory = native.resource_gate(binding)
    return {'actual_cim_controller_identity': owner, 'resource_gate': memory, 'predecessors': preceding}

def process_environment(seed):
    env = dict(os.environ)
    for key in ('PYTHONPATH', 'PYTHONHOME', 'CUDA_VISIBLE_DEVICES'):
        env.pop(key, None)
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8', PYTHONHASHSEED=str(seed),
        CUBLAS_WORKSPACE_CONFIG=':4096:8', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', XFORMERS_DISABLED='1')
    return env

def validate_identity(identity, request_record, parent, launcher):
    _, k, _, _ = runtime_helpers()
    k.require(identity['schema'] == 'external-t1-slot-identity.v1' and identity['request'] == request_record,
              'Actual worker handshake belongs to another request')
    lineage = identity['lineage']
    k.require(lineage and lineage[0]['pid'] == identity['pid'] and lineage[0]['started_utc'] == identity['started_utc'],
              'Actual worker is not first in lineage')
    k.require(lineage[-1]['pid'] == parent['pid'] and lineage[-1]['started_utc'] == parent['started_utc'], 'Wrong actual supervising parent')
    k.require(any(row['pid'] == launcher['pid'] and row['started_utc'] == launcher['started_utc'] for row in lineage), 'Popen launcher missing from actual lineage')
    k.require(len({row['pid'] for row in lineage}) == len(lineage), 'Repeated process in lineage')
    for child, owner in zip(lineage, lineage[1:]):
        k.require(child['parent_process_id'] == owner['pid'] and
            k.strict_timestamp(owner['started_utc']) <= k.strict_timestamp(child['started_utc']), 'Broken/reused parent PID lineage')
    k.require(identity['cim_identity']['ProcessId'] == identity['pid'], 'CIM and Win32 do not identify the same worker')
    return identity
