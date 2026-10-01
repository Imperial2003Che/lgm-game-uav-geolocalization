"""One-shot small-file delivery/journal append. No scientific process or lock action."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

EX = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution')
HERE = EX / 'b1_outer_observer_delivery_20260930_1834'
OBS = EX / 'heartbeat_observation_20260930_1834'
AUTHOR = EX / 'external_efficiency_preparation' / 'newer_native_b1_outer_observer_v1'
MAX = 1024 * 1024
EXPECTED_HANDOFF = (507873, '04fc3c0b8b5e364bf72d5f25e5260b67349ac605b77e33c5b872622366825f7f')
EXPECTED_ROOT = (16743, '610d9dcc13ff0c5c740089a5d7e353e8eb544275c756fae9c559930798683413')
EXPECTED_OBSERVATION = (21851, '9d3fbfb3452c7d42d6a2959a65d65f187f935e4fdd268a9b36afc8798ff49a08')
new_bindings, unchanged_bindings, new_raws = [], [], {}

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def read(path, expected=None):
    before = path.stat()
    if not 0 <= before.st_size <= MAX:
        raise ValueError('Bounded journal input too large: ' + str(path))
    with path.open('rb') as stream:
        raw = stream.read(before.st_size + 1)
        after = os.fstat(stream.fileno())
    if len(raw) != before.st_size or (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise ValueError('Journal input changed: ' + str(path))
    rec = {'path': str(path), 'bytes': len(raw), 'sha256': digest(raw)}
    if expected is not None and (rec['bytes'], rec['sha256']) != expected:
        raise ValueError('Exact journal input binding differs: ' + str(path))
    return raw, rec

def new_json(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(raw) > MAX:
        raise ValueError('Explicit one-MiB output cap exceeded')
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {'path': str(path), 'bytes': len(raw), 'sha256': digest(raw)}

def main():
    for name in ('DELIVERY.json', 'HANDOFF_ENTRY.md', 'HANDOFF_APPEND_RECEIPT.json'):
        if (HERE / name).exists():
            raise ValueError('Any journal/delivery output refuses replay: ' + name)
    root_raw, root_rec = read(HERE / 'ROOT_CLOSED_OUTER_SOURCE_PREPARATION_ADOPTION.json', EXPECTED_ROOT)
    observation_raw, observation_rec = read(OBS / 'ROOT_OBSERVATION_SEAL.json', EXPECTED_OBSERVATION)
    new_bindings.extend((root_rec, observation_rec))
    root = json.loads(root_raw)
    observation = json.loads(observation_raw)
    if root['source_preparation_adopted'] is not True or any(root[key] is not False for key in
            ('execution_released', 'B1_scientific_artifact_admitted', 'T6_complete', 'actual_observer_own_exit_proven')):
        raise ValueError('Closed source adoption scope differs')
    state_records = observation['unchanged_state_and_closed_log_files']
    if len(state_records) != 16:
        raise ValueError('Exactly sixteen unchanged scientific state/closed logs required')
    for record in state_records:
        _, actual = read(Path(record['path']), (record['bytes'], record['sha256']))
        unchanged_bindings.append(actual)
    carrier = observation['carrier']
    carrier_raw, carrier_rec = read(Path(carrier['path']), (carrier['bytes'], carrier['sha256']))
    if carrier_raw != b'0':
        raise ValueError('Persistent byte carrier differs')
    unchanged_bindings.append(carrier_rec)
    attempts = observation['attempts_absent_at_file_seal'] + [str(AUTHOR / 'runs')]
    if any(Path(path).exists() for path in attempts):
        raise ValueError('An original or new source-only runtime attempt exists; retain, do not replay')
    if Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\analysis\transactions_t6_formal').exists():
        raise ValueError('T6 output existence changed; fresh adjudication required')
    for path in (HERE / 'adopt_closed_outer_source.py', HERE / 'ACTUAL_ROOT_ADOPTION_TOOL_RETURN.json',
                 HERE / 'ACTUAL_ROOT_SOURCE_READ_TOOLS.json', HERE / 'ACTUAL_ROOT_INDEPENDENT_READ_TOOLS.json',
                 HERE / 'ACTUAL_ROOT_REVIEW_SEALER_READ_TOOL.json', OBS / 'ACTUAL_OBSERVATION_TOOLS.json',
                 Path(__file__).resolve(), HERE / 'HANDOFF_ENTRY_TEMPLATE.md'):
        raw, rec = read(path)
        new_bindings.append(rec)
        new_raws[str(path)] = raw
    root_receipt = json.loads(new_raws[str(HERE / 'ACTUAL_ROOT_ADOPTION_TOOL_RETURN.json')])
    if root_receipt['result']['chunk_id'] != '3cc3d3' or root_receipt['result']['exit_code'] != 0:
        raise ValueError('Actual root tool receipt differs')
    if json.loads(root_receipt['result']['output'])['root_adoption'] != root_rec:
        raise ValueError('Root publication actual output binding differs')
    timestamp = datetime.now(timezone.utc).isoformat()
    template = new_raws[str(HERE / 'HANDOFF_ENTRY_TEMPLATE.md')].decode('utf-8')
    if template.count('__APPEND_UTC__') != 1:
        raise ValueError('One actual append timestamp slot required')
    entry = template.replace('__APPEND_UTC__', timestamp).encode('utf-8')
    handoff = EX / 'HANDOFF.md'
    old_raw, old_rec = read(handoff, EXPECTED_HANDOFF)
    if len(old_raw) + len(entry) > MAX:
        raise ValueError('Updated HANDOFF exceeds explicit one-MiB cap')
    with (HERE / 'HANDOFF_ENTRY.md').open('xb') as stream:
        stream.write(entry)
        stream.flush()
        os.fsync(stream.fileno())
    entry_rec = {'path': str(HERE / 'HANDOFF_ENTRY.md'), 'bytes': len(entry), 'sha256': digest(entry)}
    new_bindings.append(entry_rec)
    delivery_rec = new_json(HERE / 'DELIVERY.json', {
        'schema': 'b1-outer-closed-source-and-readonly-observation-delivery.v1', 'utc': timestamp,
        'scope': 'New source preparation only and same non-admissible read-only observation; no science completion.',
        'root_adoption': root_rec, 'readonly_observation_seal': observation_rec,
        'local_new_bindings': new_bindings, 'local_new_binding_count': len(new_bindings),
        'source_graph_inherited_from_root_adoption': root['new_small_bindings'],
        'root_source_adoption_actual_tool': {'chunk_id': '3cc3d3', 'exit_code': 0,
            'new_small_bindings': 22, 'local_metadata_binding_checks': 21},
        'journal_actual_file_rechecks': unchanged_bindings, 'journal_actual_file_recheck_count': len(unchanged_bindings),
        'file_rechecks_are_not_current_OS_GPU_or_commit_admission': True,
        'carrier_creation_ticks_inherited_from_observation_only': carrier['creation_utc_ticks'],
        'runtime_attempts_absent_at_file_recheck': attempts,
        'GPU_empty_or_available_commit_admitted': False, 'execution_released': False,
        'scientific_T6_B1_or_new_figure_manuscript_Overleaf_delivery': False,
        'source_preparation_only': True,
        'historical_actual_exits_fabricated_or_passed_suites_replayed': False,
        'user_app_closed_attached_COM_or_resources_modified': False,
        'automatic_followup_deleted': False, 'notification_decision': 'DONT_NOTIFY',
        'old_handoff_binding': old_rec, 'append_entry': entry_rec,
        'append_semantics': 'Cooperative exact bytes before append and exact prefix/readback after. No arbitrary-writer atomicity or scientific lock claim.',
        'scientific_counts_negative_results_frozen_protocol_gates_and_remaining_delivery': 'Inherited unchanged from previous HANDOFF and cited adoption authorities.'
    })
    # Cooperative CAS, not a claim of atomicity against an arbitrary writer.
    # Any partial new entry/index/append is retained rather than rolled back.
    with handoff.open('r+b') as stream:
        current = stream.read(MAX + 1)
        if current != old_raw:
            raise ValueError('HANDOFF changed before append; new artifacts remain without rollback')
        stream.seek(0, os.SEEK_END)
        stream.write(entry)
        stream.flush()
        os.fsync(stream.fileno())
        stream.seek(0)
        final = stream.read(MAX + 1)
    if final != old_raw + entry:
        raise ValueError('HANDOFF append verification differs; retain partial incident')
    new_handoff = {'path': str(handoff), 'bytes': len(final), 'sha256': digest(final)}
    append_rec = new_json(HERE / 'HANDOFF_APPEND_RECEIPT.json', {
        'schema': 'b1-outer-preparation-cooperative-handoff-append-receipt.v1', 'utc': datetime.now(timezone.utc).isoformat(),
        'old_handoff': old_rec, 'entry': entry_rec, 'new_handoff': new_handoff,
        'delivery': delivery_rec, 'prefix_and_exact_append_verified': True,
        'arbitrary_writer_atomicity_or_scientific_exit_claim': False,
        'file_state_rechecks_only_not_new_resource_admission': True
    })
    print(json.dumps({'delivery': delivery_rec, 'append_receipt': append_rec, 'handoff': new_handoff,
        'local_new_bindings': len(new_bindings), 'unchanged_state_logs_and_carrier': len(unchanged_bindings),
        'source_preparation_only': True, 'execution_released': False, 'scientific_completion': False,
        'notification_decision': 'DONT_NOTIFY'}, ensure_ascii=True, indent=2))

if __name__ == '__main__':
    main()

