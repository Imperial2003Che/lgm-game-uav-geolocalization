"""New external source bindings only; no candidate import/API/controls."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def binding(name, expected=None):
    path = HERE / name
    before = path.stat()
    if before.st_size > 256 * 1024:
        raise RuntimeError('Bounded source/addendum only')
    raw = path.read_bytes()
    after = path.stat()
    sha = hashlib.sha256(raw).hexdigest()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or len(raw) != before.st_size:
        raise RuntimeError('Writer still active')
    if expected is not None and sha != expected:
        raise RuntimeError('Fixed saved source differs')
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha}


def main():
    selected = binding('guardian_v3.py', 'f2b355c93d1d3660edecece06304403dd64b06873fcf878be1cffb9f5e9a52fc')
    delta = binding('guardian_v2_to_v3.patch', 'b2ab05c7ecf0f9c3f72d8bf03a88ba38a9b3b243e9af0aa867b22c4068b88ba4')
    result = {'schema': 'newer-native-b1-guardian-source-v3-addendum.v1',
              'selected_source': selected, 'full_v2_to_v3_delta': delta,
              'unchanged_v2_manifest': binding('SOURCE_MANIFEST.json', 'ac1e711112f8225c81b634d392304e126463bcd878f71163e02cee64c632ab13'),
              'unchanged_v2_author_delivery': binding('AUTHOR_DELIVERY.json', '2fa813538733dac140f43f92e6db5a48e126bcbeb2c817510ebb46754102a6cf'),
              'other_bindings': [binding(name) for name in ('guardian_v2.py', 'README.md', 'SIX_SLOT_TEMPLATE.json',
                                 'derive_guardian_source_v3.py', 'SOURCE_DERIVATION_V3.json', 'seal_source_v3_addendum.py')],
              'scope_correction': 'V2 authored failure-retention logic was not complete: diagnostic write/API wait itself could escape. The preserved README safety description is a proposed boundary, not validated V2 runtime safety.',
              'actual_changes': [
                  'Move acquisition into setup catch, recording acquisition_started before the OS locking call. Partial acquisition errors do not imply no actual lock.',
                  'Setup partial-write/sleep failures retain owner/stream and in-memory unknown error instead of escaping a default unlock.',
                  'Per-actor wait/API/diagnostic/ledger/terminal-boundary/sleep failures remain in retention with bounded first64 detail storage plus failure counter.',
                  'No own streams are newly closed, unknown descendants are not cleared, and no quiet/exit result is manufactured.'
              ],
              'all_effect_entries_FIRST_closed': True,
              'material_interfaces_still_missing': ['upstream_adjudication_including_historical_primary_exit',
                  'compatible_reviewed_one_slot_IPC_bridge', 'complete_quiet_descendant_science_collector',
                  'external_held_guardian_observer', 'actual_native_venv_bootstrap_topology'],
              'source_adopted': False, 'independently_reviewed': False,
              'pure_controls_or_syntax_validation_run': False, 'guardian_imported_or_executed': False,
              'native_or_scientific_environment_validated': False, 'execution_released': False,
              'measurement_admitted': False, 'runnable_guardian_complete': False,
              'OS_API_resource_shared_lock_or_science_called': False,
              'old_source_gates_manifest_README_or_template_rewritten': False,
              'actual_offline_derivation_receipt': {'chunk_id': '809187', 'exit_code': 0, 'wall_time_seconds': 0.1757698,
                  'scope': 'ordinary Python311 source-text derivation; tool outcome not independently held process/guardian exit'},
              'source_sealer_v2_actual_receipt': {'chunk_id': '89f89a', 'exit_code': 0, 'wall_time_seconds': 0.1720654,
                  'scope': 'new source metadata/patch packaging only'},
              'hard_interrupt_limit': 'Host/guardian hard interruption releases OS locks; real residual-child incident audit still required. No runtime safety claim is made from unexecuted source.',
              'next': 'Root and independent complete static reading of V3 plus full source/delta chain; no replay/new controls or runtime without separately scoped authorization.'}
    path = HERE / 'SOURCE_REVIEW_ADDENDUM_V3.json'
    raw = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
    print(json.dumps({'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}, ensure_ascii=False))


if __name__ == '__main__':
    main()
