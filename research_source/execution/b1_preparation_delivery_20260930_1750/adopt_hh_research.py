"""One root adoption of finite SDK data research; no extraction/API/validator calls."""
from pathlib import Path
from datetime import datetime, timezone
import json, hashlib, os
HERE = Path(__file__).resolve().parent
EX = HERE.parent
R = EX / 'visio_full_xsd_research_20260930_1730'
CAP = 262144
records, saved = {}, {}
def bind(path, expected=None):
    path = Path(path)
    key = str(path)
    if key not in records:
        before = path.stat()
        assert 0 <= before.st_size <= CAP, key
        with path.open('rb') as f:
            raw = f.read(before.st_size + 1)
            after = os.fstat(f.fileno())
        assert len(raw) == before.st_size and (before.st_size, before.st_mtime_ns, before.st_ino) == (after.st_size, after.st_mtime_ns, after.st_ino)
        saved[key] = raw
        records[key] = dict(path=key, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    value = records[key]
    if expected is not None: assert value == expected, key
    return value
def load(path):
    bind(path)
    return json.loads(saved[str(Path(path))])
content_path = R / 'CONTENT_EXTRACTION_RESEARCH.json'
ascii_path = R / 'ASCII_EXTRACTION_SCOPE_REVIEW.json'
delivery_path = R / 'DELIVERY.json'
for p,n,s in [(content_path,15739,'b9a5fce676dcb2e0777b6fbba0e493c5470600012dc09410a63a036f7ed65a21'),(ascii_path,13270,'b64556edb1b3cd66d29a819005ece5ce2f82ae3b7f11372916bc6a1d3ceedf78'),(delivery_path,3407,'dc6e31909e56c7d86a1627bde1ff8a0db906d7bc994a6595eae810da3ed155e6')]:
    bind(p,dict(path=str(p),bytes=n,sha256=s))
content, ascii_report, delivery = load(content_path), load(ascii_path), load(delivery_path)
for report in (content, ascii_report):
    for edge in report['new_small_bindings']: bind(edge['path'], edge)
for edge in delivery['report_references']: bind(edge['path'], edge)
bind(R / 'DELIVERY_ACTUAL_TOOL_RETURN.json')
bind(__file__)
original_path = R / 'hh_decompile_attempt_v1/RESULT.json'
ascii_result_path = Path(r'C:\Users\17703\AppData\Local\Temp\LGM_GAME_CHM_20260930_1745_1730_ascii_v1\RESULT.json')
original, ascii_result = load(original_path), load(ascii_result_path)
entry = load(ascii_result_path.parent / 'ENTRY.json')
for result in (original,ascii_result):
    assert result['process_exit_confirmed'] is True and type(result['process_exit_code']) is int and result['process_exit_code'] == 0
    assert result['input_unchanged'] is True and result['extracted_file_count'] == 0 and result['extracted_total_bytes'] == 0
    assert result['streams_read_after_signalled_process'] is True
    assert result['stdout']['bytes'] == result['stderr']['bytes'] == 0
    assert result['returned_process_object_disposed_after_exit'] is True
    assert result['error'] is None and result['science'] is False and result['Office_COM'] is False
assert entry['os_path_samefile_before']['value']['samefile'] is True and ascii_result['os_path_samefile_after']['value']['samefile'] is True
for x in (entry['input'],entry['original_input'],ascii_result['input_after'],ascii_result['original_input_after']):
    assert x['bytes'] == 6764354 and x['sha256'] == '19a74be23751db246fdf047d49a187187074113ad9095febd0cb640dba465a4a'
assert ascii_report['content_scope']['member_content_search_actually_performed'] is False
assert ascii_report['content_scope']['prepared_search_source_executed'] is False
assert content['conclusion']['correct_official_2012_main_full_schema_obtained'] is False
for p in (original_path.parent / 'decompiled_data', ascii_result_path.parent / 'decompiled_data'):
    assert p.is_dir() and not any(p.rglob('*')), str(p)
original_receipt = load(R / 'HH_ACTUAL_TOOL_RETURN.json')
ascii_receipt = load(R / 'ASCII_HH_ACTUAL_TOOL_RETURN.json')
assert original_receipt['schema'] == 'visio-chm-hh-data-extraction-actual-tool.v1'
assert ascii_receipt['schema'] == 'ordinary-HH-ascii-tool-receipt.v1'
hh_actual_returns = [original_receipt['result'], ascii_receipt['actual_return']]
assert [x['chunk_id'] for x in hh_actual_returns] == ['1db907','790e1c']
assert all(x['exit_code'] == 0 for x in hh_actual_returns)
report = {
 'schema':'root-finite-sdk-schema-research-adoption.v1',
 'utc':datetime.now(timezone.utc).isoformat(),
 'source':records[str(Path(__file__).resolve())],
 'research_reports_adopted':True,'successful_member_extraction_adopted':False,
 'correct_full_2012_main_schema_collection_obtained':False,
 'nine_part_XSD_dependency_closure_obtained':False,
 'full_XSD_validation_or_native_application_acceptance_adopted':False,
 'new_scientific_or_figure_result':False,
 'producer_reports':[records[str(content_path)],records[str(ascii_path)],records[str(delivery_path)]],
 'new_small_local_bindings':list(records.values()),
 'binding_count':len(records),
 'actual_data_attempts':[
   dict(result=records[str(p)],actual_tool_chunk=x['chunk_id'],ordinary_process_identity=result['events'][0]['value'],ordinary_actual_exit=result['process_exit_code'],ordinary_exit_ticks=result['process_exit_utc_ticks'],extracted_files=0,extracted_bytes=0)
   for p,x,result in zip((original_path,ascii_result_path),hh_actual_returns,(original,ascii_result))],
 'samefile_before_after_verified_from_saved_actual_results':True,
 'root_did_not_rehash_original_CHM_or_recall_samefile_API':True,
 'root_did_not_hold_HH_handles_or_independently_reobserve_exited_processes':True,
 'root_method':'AI full v3 source/two Boolean deltas, ASCII source/full delta/contract, both producer scope reports/sealers/delivery and actual HH receipts/RESULT reading. Local bounded byte bindings and saved actual result association; two output directories remain empty at adoption. No old SCI/control tests, CHM decoder, search source, extraction, SDK/MSI/Office/native calls.',
 'interpretation_limits':[
  'Original PS v1 failed bare true cmdlet-not-found before ENTRY/attempt/HH. Root earlier string-value inference was wrong; external correction retained. v2 PS is unexecuted; distinct v3 is consumed.',
  'ASCII offline derivation v1 failed before candidate/output/Temp/HH, and distinct v2 semicolon anchor produced the source. Actual failures retained, no replay.',
  'Both ordinary HH children exited0 on the same returned Process objects and closed redirects, but output0 files. This is not extraction success, scientific dual launcher/interpreter exits, genealogy evidence or Office acceptance.',
  'ASCII hardlink before/after samefile and exact input bytes were recorded. Neither attempt establishes a Unicode, policy, archive, forwarding or OS-mode cause.',
  'No actual member content search or standalone schema parse occurred. Earlier4312 names still lack content evidence. Do not assert the CHM contents contain no XSD.',
  'Current primary Microsoft schema-map text2011/1/core with XSD1.1 is not an obtained official2012/main collection. No namespace edit, constraints removal, fragment assembly or full validation.',
  'Seven final delivery edges supplement inherited22/20 report edges.8359b0 repair-preparation receipt was transcribed after the core with stdout JSON normalization; it is not a new execution or held exit. Actual HH receipts preserve their complete actual tool returns.',
  'No third HH, replay, fallback copy, cleanup, user app attachment/closure or new SDK expansion in this finite research episode. Both attempt directories and the hardlink remain.',
  '68 file-only VSDX still require applicable complete-XSD and genuine repair-free open/render/export/edit/reopen acceptance under independently satisfied conditions.'
 ],
 'science_release_intent_native_training_probe_COM_or_shared_lock_action':False,
 'all_task_deliveries_complete':False,'automation_retained':True
}
target = HERE / 'ROOT_HH_RESEARCH_ADOPTION.json'
body = (json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
assert len(body) <= CAP
with target.open('xb') as f: f.write(body); f.flush(); os.fsync(f.fileno())
print(json.dumps(dict(path=str(target),bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),binding_count=len(records)),ensure_ascii=False))
