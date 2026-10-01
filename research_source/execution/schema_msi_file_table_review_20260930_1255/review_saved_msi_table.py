"""Compare saved MSI/CAB table values only; never import producer or call SDK/API."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import hashlib, json, os

EX = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution')
HERE = EX / 'schema_msi_file_table_review_20260930_1255'
ROOT = EX / 'schema_package_research_20260930_1228'
INPUTS = []

def read(path, cap, expected):
    size = path.stat().st_size
    if not 0 <= size <= cap:
        raise ValueError('Named report/source bound before read')
    with path.open('rb') as stream:
        raw = stream.read(cap + 1)
    if len(raw) != size or len(raw) > cap:
        raise ValueError('Actual input bytes changed/exceed named bound')
    item = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    if expected is not None and item['sha256'] != expected:
        raise ValueError('Exact selected input binding changed: ' + str(path))
    INPUTS.append(item)
    return raw, item

raw_table, table_binding = read(ROOT / 'SDK_READONLY_FILE_TABLE_v2.json', 128 * 1024,
                               'df0fe3f9d594707336cd5fdf5c6f083822fc07a1c412643f4dca5a3760c17f77')
raw_cab, cab_binding = read(EX / 'offline_native_xsd_feasibility_20260930_1212' / 'SDK_INNER_CAB_REVIEW.json',
                           128 * 1024, 'ec588535780606784ed4bf301f1e01a493cf80a53e57cf25c84e510e5ac516b5')
raw_source, source_binding = read(ROOT / 'read_sdk_file_table_v2.py', 16 * 1024,
                                 'f4e48a61dc54911f6aa04e9e08873d4e124437e22fabf5b97613b4585628df27')
raw_checker, checker_binding = read(Path(__file__).resolve(), 16 * 1024, None)
table = json.loads(raw_table)
cab = json.loads(raw_cab)
rows = table['all_file_rows']
cab_rows = cab['actual_header_and_file_table']['entries']
closed = table['closed_native_database_handles']
checks = []

def check(name, result):
    checks.append({'name': name, 'passed': bool(result)})

check('actual_producer_source_matches_saved_descriptor', table['source'] == source_binding)
check('completed_v2_query_not_partial', table['schema'] == 'official-sdk-readonly-file-table.v2'
      and table['status'] == 'completed' and table['query_completed'] is True and 'partial_file_rows' not in table)
check('exact_236_saved_rows_both_inputs', len(rows) == table['file_row_count'] == len(cab_rows)
      == cab['actual_header_and_file_table']['file_count'] == 236)
row_keys = [r['file_key'] for r in rows]
cab_keys = [r['name'] for r in cab_rows]
check('unique_exact_and_casefold_file_keys_both_inputs', len(set(row_keys)) == len(set(map(str.casefold, row_keys))) == 236
      and len(set(cab_keys)) == len(set(map(str.casefold, cab_keys))) == 236)
msi_map = {r['file_key']: r['uncompressed_bytes'] for r in rows}
cab_map = {r['name']: r['uncompressed_bytes'] for r in cab_rows}
check('all_236_exact_key_and_uncompressed_size_pairs_equal', msi_map == cab_map)
mismatches = [{'file_key': key, 'msi_bytes': msi_map.get(key), 'saved_cab_bytes': cab_map.get(key)}
              for key in sorted(set(msi_map) | set(cab_map)) if msi_map.get(key) != cab_map.get(key)]
check('all_saved_sizes_nonnegative_integers_and_sequences_positive', all(type(r['uncompressed_bytes']) is int
      and r['uncompressed_bytes'] >= 0 and type(r['sequence']) is int and r['sequence'] > 0 for r in rows))
check('saved_FileName_alias_derivation_matches', all(r['installed_long_filename'] == r['file_name_field'].split('|')[-1]
      for r in rows))
aliases = [{'file_key': r['file_key'], 'FileName': r['file_name_field'],
            'installed_long_filename': r['installed_long_filename'], 'uncompressed_bytes': r['uncompressed_bytes']}
           for r in rows if r['file_key'] != r['installed_long_filename']]
named_schema = [r for r in rows if r['installed_long_filename'].lower().endswith('.xsd')
                or 'schema' in r['installed_long_filename'].lower()]
docs = [r for r in rows if r['installed_long_filename'].lower().endswith(('.chm', '.htm', '.html'))]
check('schema_named_rows_reconcile_to_saved_full_rows_and_empty', named_schema == table['schema_named_rows'] == [])
check('documentation_rows_reconcile_to_saved_full_rows_and_23', docs == table['documentation_rows'] and len(docs) == 23)
close_counts = dict(Counter(r['kind'] for r in closed))
check('238_saved_handle_close_results_with_236_records_view_database', len(closed) == 238
      and close_counts == {'record': 236, 'view': 1, 'database': 1})
check('all_saved_handle_close_codes_zero_no_API_call_error', all(type(r['handle']) is int and r['handle'] > 0
      and r.get('actual_returncode') == 0 and 'api_call_error' not in r for r in closed))
check('no_saved_primary_secondary_close_or_postread_error', table['primary_error'] is None
      and table['secondary_close_errors'] == [] and table['post_read_errors'] == [])
check('saved_before_after_database_descriptors_equal', table['database_before'] == table['database_after']
      and table['database_before']['bytes'] == 3063808
      and table['database_before']['sha256'] == '738282e60eb7e2470248cefb89389e6e73680ce4b3d9237f80e17a8259123462')
check('READONLY_and_only_expected_SELECT_recorded', table['database_mode'] == 'MSIDBOPEN_READONLY (null)'
      and table['native_system_dll'] == r'C:\Windows\System32\msi.dll'
      and table['sql_only'] == 'SELECT `File`, `FileName`, `FileSize`, `Sequence` FROM `File` ORDER BY `Sequence`')
check('no_installer_actions_COM_code_or_schema_validation_claimed', all(table[x] is False for x in
      ['installer_run', 'action_sequence_or_custom_action_run', 'Office_COM', 'downloaded_code_executed', 'schema_validation']))

report = {
 'schema': 'saved-sdk-msi-file-table-independent-review.v1',
 'created_utc': datetime.now(timezone.utc).isoformat(),
 'reviewer': 'Independent AI sub-agent /root/b1_integration_scope_0912; no human reviewer',
 'method': 'Read actual bytes of three saved small inputs plus this checker; compare only saved table values and source identity. No producer import/execution, CAB/MSI payload access/hash, SDK/native API, process holding, Office, scientific library or old-suite rerun.',
 'input_bindings': INPUTS, 'selected_field_checks': checks,
 'check_count': len(checks), 'all_selected_checks_pass': all(c['passed'] for c in checks),
 'saved_MSI_File_rows': len(rows), 'saved_CFFILE_entries': len(cab_rows),
 'exact_key_size_pair_matches': len(msi_map) if msi_map == cab_map else None,
 'key_size_mismatches': mismatches,
 'canonical_equal_key_size_map_sha256': hashlib.sha256(json.dumps(msi_map, sort_keys=True, separators=(',', ':')).encode('utf8')).hexdigest(),
 'saved_close_evidence': {'total': len(closed), 'kind_counts': close_counts,
      'all_reported_actual_returncodes_zero': all(r.get('actual_returncode') == 0 for r in closed),
      'scope': 'MSI database/view/record MSIHANDLE close return values saved by the root execution. The reviewer neither re-held these handles nor invoked the API, and these are not OS process exit handles.'},
 'database_before_after_binding_inherited_from_saved_query': table['database_before'],
 'database_hash_limit': 'Descriptor equality is read from the saved successful query; this reviewer did not reread current MSI bytes or compresssed CAB bytes.',
 'filename_aliases': {'exact_file_key_differs_from_installed_long_filename': len(aliases),
      'comparison_key': 'CAB CFFILE name equals MSI File primary key, not installed FileName.',
      'sample_saved_aliases': aliases[:8]},
 'schema_named_rows': named_schema,
 'documentation_rows': docs,
 'documentation_suffix_counts': dict(Counter(Path(r['installed_long_filename']).suffix.casefold() for r in docs)),
 'parent_forwarded_actual_tool': {'chunk': 'bfad3d', 'exit_code': 0, 'seconds': 0.2938667,
      'scope': 'Parent message evidence, not a fresh reviewer tool run or independently held exit.'},
 'limits': ['Only saved complete File-table rows/aliases/sizes are reconciled; CHM/HTML bodies and any embedded schemas were not read by this reviewer.',
      'No .xsd/schema-named installed filename in these 236 rows does not prove the SDK never distributed schemas or that CHM contains none.',
      'This confirms selected saved values, not full SDK/executable trust, complete XSD acquisition or validation, repair-free Visio opening/rendering/edit roundtrip or scientific completion.',
      'The v2 source was authored by this same AI sub-agent in a prior root-authorized step; this narrow runtime-value review is independent of the root actual execution, not an independent second source author.',
      'Original v1 remains unexecuted according to parent; neither v1 nor v2 was executed by this reviewer. Failure branches were inspected statically only and were not exercised by the successful query.'],
 'root_adoption_pending': True}
raw_report = (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode('utf8')
if len(raw_report) > 64 * 1024:
    raise ValueError('Small output bound before CreateNew')
path = HERE / 'SDK_SAVED_FILE_TABLE_REVIEW.json'
with path.open('xb') as stream:
    stream.write(raw_report)
    stream.flush()
    os.fsync(stream.fileno())
print(json.dumps({'report': {'path': str(path), 'bytes': len(raw_report),
      'sha256': hashlib.sha256(raw_report).hexdigest()}, 'passed': report['all_selected_checks_pass'],
      'field_check_count': len(checks), 'file_rows': len(rows), 'close_results': len(closed),
      'filename_aliases': len(aliases), 'documentation_suffix_counts': report['documentation_suffix_counts']}, ensure_ascii=False))
if not report['all_selected_checks_pass']:
    raise SystemExit(1)
