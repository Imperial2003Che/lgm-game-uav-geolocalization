from pathlib import Path
import json,hashlib,datetime
base=Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\visio_full_xsd_research_20260930_1730')
selected=['decompile_sdk_chm_once.ps1','decompile_sdk_chm_once_v2.ps1','decompile_sdk_chm_once_v3.ps1','decompile_sdk_chm_v1_to_v2.patch','decompile_sdk_chm_v2_to_v3.patch','derive_decompile_v2.py','derive_decompile_v3.py','DECOMPILE_V2_DERIVATION.json','DECOMPILE_V3_DERIVATION.json','PREPARE_ACTUAL_TOOL_RETURN.json','FAILED_PREENTRY_ACTUAL_TOOL_RETURN.json','V2_DERIVATION_ACTUAL_TOOL_RETURN.json','V3_DERIVATION_ACTUAL_TOOL_RETURN.json','ROOT_STATIC_BOOLEAN_SCOPE_ADDENDUM.json','HH_ACTUAL_TOOL_RETURN.json','EMPTY_OUTPUT_OBSERVATION_ACTUAL_TOOL_RETURN.json','hh_decompile_attempt_v1/ENTRY.json','hh_decompile_attempt_v1/LIVE_PROCESS_IDENTITY.json','hh_decompile_attempt_v1/RESULT.json','hh_decompile_attempt_v1/hh.stdout.log','hh_decompile_attempt_v1/hh.stderr.log','save_research_report.py']
bindings=[]
for name in selected:
 p=base/name
 size=p.stat().st_size
 assert 0<=size<=65536
 raw=p.read_bytes()
 assert len(raw)==size
 bindings.append({'path':str(p),'bytes':size,'sha256':hashlib.sha256(raw).hexdigest()})
saved=json.loads((base/'hh_decompile_attempt_v1/RESULT.json').read_text(encoding='utf-8'))
assert saved['process_exit_confirmed'] is True and type(saved['process_exit_code']) is int and saved['process_exit_code']==0
assert saved['input_unchanged'] is True
assert saved['extracted_file_count']==0 and saved['extracted_total_bytes']==0
actual_files=list((base/'hh_decompile_attempt_v1/decompiled_data').rglob('*'))
assert len(actual_files)==0
report={
 'schema':'visio-full-xsd-content-research.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer':'Independent task AI subagent /root/visio_full_xsd_1730','scope':'Necessary attempt to obtain official complete 2012/main Visio and nine-part dependency XSD set from already downloaded SDK documentation. No native VSDX/old scientific packages reopened.',
 'new_small_bindings':bindings,
 'prior_read_authority':[
  {'path':str(base.parent/'offline_native_xsd_feasibility_20260930_1212/XSD_FEASIBILITY_REVIEW.json'),'bytes':19965,'sha256':'542af1d70509ccbe9a2da9f90501e49526381ce7b1cbd9247010c0e397f56cc9','binding_scope':'Inherited existing adopted byte descriptor; actual report read, not full dependency/old result rehash'},
  {'path':str(base.parent/'schema_package_research_20260930_1228/SDK_READONLY_FILE_TABLE_v2.json'),'bytes':79425,'sha256':'df0fe3f9d594707336cd5fdf5c6f083822fc07a1c412643f4dca5a3760c17f77','binding_scope':'Inherited existing adopted byte descriptor; keys and selected saved fields inspected, not repeated msi.dll/CAB API'},
  {'path':str(base.parent/'schema_package_research_20260930_1228/chm_directory_attempt_v1/SDK_CHM_DIRECTORY_CANDIDATE.json'),'bytes':1566445,'sha256':'2d9a44834e240e4ea8df4dfc608396e599f0557ad227fac33fa6245ca7b39ab1','binding_scope':'Inherited descriptor; parsed saved keys/first eight member descriptors and filename candidates only, no CHM reparse/LZX or full directory-validation suite'},
  {'path':str(base.parent/'schema_package_research_20260930_1228/SDK_SINGLE_CHM_DATA_EXTRACTION.json'),'bytes':2463,'sha256':'d456c43573525ac4379ea55f3e428f5011c687ffecd5bd7551b376bf51da6a2b','binding_scope':'Actual report read; source descriptor inherited, new actual CHM SHA before/after HH belongs to fresh extraction safety check below'}],
 'actual_execution':{
  'v1':'b89001 exit1/1.0881496s: bare true in ENTRY constructor was treated as command; failed before attempt/ENTRY/HH startup. 29726e exit0/0.1932494s Test-Path=False. Original source and actual failure preserved; not replayed.',
  'v2':'9a4255 exit0/0.1738273s offline bytes: all20 bare Boolean constants repaired; no HH. v2 PS source unexecuted.',
  'v3':'09d727 exit0/0.1717342s offline delta: finally requires Boolean type and true. Task root read whole v3/two patches and expressly allowed one exact new HH data extraction.',
  'hh_tool':'1db907 exit0/0.4005627s running v3 once; HH PID35520 Process handle2192, creation639263832718115732; same returned object WaitForExit60000 returned true; actual exit0 at639263832718407619; redirected stdout/stderr both0B read after process signalled. Process object disposed only after actual confirmed exit.',
  'input_before_after':saved['input_after'],'input_unchanged':True,'output_directory':str(base/'hh_decompile_attempt_v1/decompiled_data'),'actual_extracted_files':0,'actual_extracted_total_bytes':0,
  'later_read_only_check':'01aa42 exit0/0.2346814s: still0 recursive files and0 recursive directories; destination creation/lastwrite both2026-09-30T16:41:11.7939676Z; CHM stream enumeration lists only :$DATA. Stream listing does not prove all policies/status/causes.'},
 'fresh_official_web_observations':[
  {'url':'https://learn.microsoft.com/en-us/previous-versions/windows/desktop/htmlhelp/to-decompile-a-compiled-help-file-from-the-command-line','read':'Actual direct primary web read this task','locator':'lines31-40','finding':'Documents hh.exe -decompile destination-folder CHM and says no HTML Help Workshop installation is required.'},
  {'url':'https://learn.microsoft.com/en-us/previous-versions/windows/desktop/htmlhelp/decompiling-a-help-file','read':'Actual direct primary web read this task','locator':'lines32,40','finding':'Defines decompilation as copying embedded source files while keeping the compiled help file unchanged. Does not promise a validated schema set or prove this actual zero-output run succeeded.'},
  {'url':'https://learn.microsoft.com/en-us/previous-versions/windows/desktop/htmlhelp/using-command-line-switches','read':'Actual primary search-tool source result this task','finding':'Distinguishes decompile from viewer/display switches; table lists no API equivalent for decompile.'},
  {'url':'https://learn.microsoft.com/en-us/office/client-developer/visio/schema-mapvisio-xml','read':'Actual direct primary web read header/relevant blocks this task','locator':'lines38,168,189','finding':'Displayed full-schema text still has targetNamespace2011/1/core and XSD1.1 assert/alternative. It is not a correct 2012/main collection; no namespace edit, constraint removal or fragment assembly done.'},
  {'url':'https://www.microsoft.com/en-us/download/details.aspx?id=51221','read':'Actual direct official download-page reading this task; no package downloaded','locator':'lines39-54,71-72','finding':'Visio2016 SDK page describes XML Schema Reference and lists 2016,7/15/2024 and two EXE names. A reference description is not an obtained full XSD dependency closure. No further SDK download under root limited scope.'},
  {'url':'https://www.microsoft.com/en-us/download/details.aspx?id=30425','read':'Actual direct official URL result this task','finding':'Returned404; a Microsoft Q&A reply naming this as Office schema candidate is not used as authoritative schema availability.'},
  {'url':'https://www.microsoft.com/en-us/download/details.aspx?id=49030','read':'Actual direct official URL this task','locator':'lines11-13,45-57','finding':'Actual current download is Office administrative templates ADMX/ADML, not complete Visio XSD. Candidate excluded without package download.'}],
 'web_timing_limit':'Fresh accesses occurred during this task before HH start2026-09-30T16:41:11.7951328Z. Per-request actual UTC timestamps were not captured; no exact times manufactured. Public schema header refresh is research, not a repeated validator suite.',
 'conclusion':{
  'actual_HH_process_exited_zero':True,'successful_member_extraction_proven':False,'extracted_members_content_search_possible':False,'zero_output_cause':'Unknown. Neither Unicode-path handling, safe-mode/policy, archive integrity, broker forwarding nor any other cause was established. Ordinary return0 is insufficient.',
  'correct_official_2012_main_full_schema_obtained':False,'complete_nine_part_dependency_closure_obtained':False,'full_XSD_compiled_or_validated':False,'native_VSDX_application_acceptance':False,'new_scientific_result':False,
  'scope_statement':'This single HH data extraction attempt produced no member files, so it did not resolve the earlier4312-name-only content gap. Do not say all CHM content contains no XSD: member content remains unread. No applicable complete official2012 schema collection was obtained from this attempt or bounded official web research.',
  'conditional_next_step':'No ready full-XSD validation can be authorized from current materials. A separately reviewed new extraction/data-path diagnostic could be prepared under a new root decision, preserving this consumed attempt; it must not replay this invocation, fabricate complete extraction, adapt the2011 namespace or assemble documentation fragments. Root coordinates any independent validation only after exact official schemas and all imports/includes/other nine-part dependencies are genuinely obtained.'},
 'no_actions':{'SDK_EXE_MSI_or_payload_code_run':True,'HTML_JS_execution':True,'Office_COM_viewer_attach_userapp_Quit_Kill_cleanup':True,'native68_reopen_change_or_old_suite_repeat':True,'science_GPU_weights_old_bigZIP':True,'full_XSD_validation':True,'HANDOFF_or_sealed_old_root_rewrite':True},'no_actions_encoding':'true means named action was NOT done.',
 'single_use':'v1 PS invocation used/failed preentry; v2 PS unexecuted; v3 HH attempt exists/consumed and must never be deleted or replayed. No retry/cleanup performed.',
 'method_limit':'AI source/report/tool reading; no human review. System.Diagnostics.Process capture only proves the recorded ordinary HH child exit; not scientific launcher/interpreter dual held identities or Visio data repair-free render/edit acceptance.'}
raw=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
assert len(raw)<=65536
out=base/'CONTENT_EXTRACTION_RESEARCH.json'
with out.open('xb') as f:f.write(raw)
print(json.dumps({'path':str(out),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'HH_exit0':True,'extracted_files':0,'fullXSD_obtained':False,'new_small_bindings':len(bindings)},ensure_ascii=False))
