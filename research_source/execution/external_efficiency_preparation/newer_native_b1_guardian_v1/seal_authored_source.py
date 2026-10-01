"""Bounded author-source packaging only; never import or execute guardian code."""
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EX = HERE.parents[1]
SCOPE = EX / 'b1_integrated_controller_scope_20260930_1343'
MAXIMUM = 256 * 1024


def read(path, maximum=MAXIMUM):
    before = path.stat()
    if before.st_size > maximum:
        raise RuntimeError('Oversize small source/report')
    raw = path.read_bytes()
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or len(raw) != before.st_size:
        raise RuntimeError('Active source writer rejected')
    return raw


def item(path, raw):
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def write_new(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()


def main():
    base_path = SCOPE / 'NEXT_INTEGRATION_SCOPE.json'
    base_raw = read(base_path)
    if hashlib.sha256(base_raw).hexdigest() != '73bb4b0a2f3f35c657c4e006f373aa7b010257753f3fd9a2a74784dba9870e3c':
        raise RuntimeError('Sealed scope report changed')
    clarification_path = SCOPE / 'RESOURCE_RELEASE_SCOPE_ADDENDUM.json'
    clarification_raw = read(clarification_path)
    if hashlib.sha256(clarification_raw).hexdigest() != 'b932db65950df891d2166b2fd8698bde9932bc12427a430af82eeee5372df3d2':
        raise RuntimeError('Sealed clarification changed')
    base = json.loads(base_raw)
    names = ('guardian.py', 'guardian_v2.py', 'guardian_v1_to_v2.patch',
             'derive_guardian_source_v2.py', 'SOURCE_DERIVATION.json',
             'SIX_SLOT_TEMPLATE.json', 'README.md', 'seal_authored_source.py')
    records = [item(HERE / name, read(HERE / name)) for name in names]
    # Full added-source delta from absent unit. This is text, not executed code.
    added = b''
    for name in ('guardian_v2.py', 'SIX_SLOT_TEMPLATE.json', 'README.md'):
        body = read(HERE / name).decode('utf-8')
        added += ''.join(difflib.unified_diff([], body.splitlines(True),
                     fromfile='/dev/null', tofile='newer_native_b1_guardian_v1/' + name)).encode('utf-8')
    patch_path = HERE / 'full_new_unit.patch'
    write_new(patch_path, added)
    records.append(item(patch_path, added))
    selected = next(value for value in records if Path(value['path']).name == 'guardian_v2.py')
    flags = {'source_authored': True, 'source_adopted': False,
             'independently_reviewed': False, 'syntax_or_pure_controls_executed': False,
             'guardian_imported_or_executed': False, 'execution_released': False,
             'native_venv_validated': False, 'scientific_environment_validated': False,
             'independent_execution_proven': False, 'measurement_admitted': False,
             'runnable_guardian_complete': False, 'real_release_intent_attempt_created': False,
             'GPU_memory_process_API_or_shared_lock_called': False,
             'original_scientific_sources_or_gates_modified': False}
    manifest = {'schema': 'newer-native-b1-guardian-source-manifest.v1',
                'selected_source': selected, 'files': records,
                'scope_report': item(base_path, base_raw),
                'clarification': item(clarification_path, clarification_raw),
                'inherited_source_descriptors_not_rehashed': base['source_bindings'],
                'helper_source_sha256_inherited': 'cc090bec1429ab429b556200597acedfa13c33e878627155b0cc9f8098c9f5d2',
                'proposed_order': [['CAMP', 1], ['CAMP', 2], ['CAMP', 3], ['DAC', 1], ['DAC', 2], ['DAC', 3]],
                'missing_hard_pins': ['reviewed_execution_authority', 'compatible_one_slot_IPC_bridge',
                                      'quiet_collector', 'external_guardian_observer'],
                'flags': flags}
    manifest_raw = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    manifest_path = HERE / 'SOURCE_MANIFEST.json'
    write_new(manifest_path, manifest_raw)
    report = {'schema': 'newer-native-b1-guardian-author-delivery.v1',
              'source_manifest': item(manifest_path, manifest_raw), 'selected_source': selected,
              'flags': flags, 'files': records,
              'scope': 'Author source bodies and immutable null plan only; no runtime or scientific completion',
              'material_gaps': [
                  'Historical primary independent exit and actual full upstream plus extra DAC adoption cannot be manufactured offline.',
                  'Adopted lifecycle/worker FIRST reject; no guardian IPC bridge/CLI version exists. No source override was used.',
                  'Actual native topology/bootstrap images and complete commands remain unknown and unvalidated.',
                  'Quiet descendant/science collector is absent; _quiet_snapshot explicitly rejects, not an accepted empty array.',
                  'External retained guardian observer is absent; return intent cannot prove its own actual exit.'
              ],
              'authoring_tool_receipt': {
                  'large_shell_attempt': {'outcome': 'CreateProcess refused before shell launch', 'win_error': 206,
                                          'reported_text': '文件名或扩展名太长。', 'source_written_by_attempt': False,
                                          'native_or_scientific_failure': False},
                  'source_derivation': {'actual_chunk_id': '4933fc', 'actual_tool_exit_code': 0,
                                        'wall_time_seconds': 0.17546,
                                        'scope': 'ordinary Python311 -I -S -B -X utf8 byte-source derivation, not guardian import/runtime or held exit proof'},
                  'patch_authoring': 'File patch tools created new sources; no previous source overwritten',
                  'current_sealer_actual_tool_outcome': 'not captured by self; parent must retain returned tool receipt'
              },
              'no_old_suite_replay': [50, 352, 91, 839],
              'no_rehash_scope': 'No weights, NPY/cache/images, scientific artifacts, old ZIP or adopted input source-suite reread',
              'next_action': 'Root full source/delta reading and independent static review. Pure new checks only after separately scoped authorization.'}
    report_raw = (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    report_path = HERE / 'AUTHOR_DELIVERY.json'
    write_new(report_path, report_raw)
    print(json.dumps({'selected_source': selected,
                      'source_manifest': item(manifest_path, manifest_raw),
                      'author_delivery': item(report_path, report_raw),
                      'full_new_unit_delta': item(patch_path, added)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
