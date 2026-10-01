from pathlib import Path
import json,hashlib,datetime
base=Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\visio_full_xsd_research_20260930_1730')
attempt=Path(r'C:\Users\17703\AppData\Local\Temp\LGM_GAME_CHM_20260930_1745_1730_ascii_v1')
def bounded(p):
 n=p.stat().st_size
 assert 0<=n<=65536
 r=p.read_bytes()
 assert len(r)==n
 return r,{'path':str(p),'bytes':n,'sha256':hashlib.sha256(r).hexdigest()}
entry_raw,entry_binding=bounded(attempt/'ENTRY.json')
result_raw,result_binding=bounded(attempt/'RESULT.json')
entry=json.loads(entry_raw);result=json.loads(result_raw)
assert result['process_exit_confirmed'] is True
assert type(result['process_exit_code']) is int and result['process_exit_code']==0
assert result['input_unchanged'] is True
assert entry['os_path_samefile_before']['value']['samefile'] is True
assert result['os_path_samefile_after']['value']['samefile'] is True
for v in [entry['input'],entry['original_input'],result['input_after'],result['original_input_after']]:
 assert v['bytes']==6764354 and v['sha256']=='19a74be23751db246fdf047d49a187187074113ad9095febd0cb640dba465a4a'
assert result['extracted_file_count']==0 and result['extracted_total_bytes']==0
dest=attempt/'decompiled_data'
assert dest.is_dir()
actual=list(dest.rglob('*'))
assert len(actual)==0
newbindings=[entry_binding,result_binding]
for p in [attempt/'ATTEMPT_DECLARATION.json',attempt/'LIVE_PROCESS_IDENTITY.json',attempt/'hh.stdout.log',attempt/'hh.stderr.log']:
 newbindings.append(bounded(p)[1])
names=['decompile_sdk_chm_ascii_candidate.ps1','decompile_v3_to_ascii_candidate.patch','ASCII_CANDIDATE_SOURCE_CONTRACT.json','derive_ascii_candidate.py','derive_ascii_candidate_v2.py','prepare_ascii_derivation_v2.py','ascii_derivation_v1_to_v2.patch','ASCII_DERIVATION_FAILED_TOOL_RETURN.json','ASCII_DERIVATION_V2_ACTUAL_TOOL_RETURN.json','ASCII_HH_ACTUAL_TOOL_RETURN.json','CONTENT_EXTRACTION_RESEARCH.json','REPORT_ACTUAL_TOOL_RETURN.json','search_ascii_extracted_content.py','seal_ascii_scope.py']
for name in names:newbindings.append(bounded(base/name)[1])
entry_critical={'argument_vector':entry['argument_vector'],'alias_binding_at_entry':entry['input'],'original_binding_at_entry':entry['original_input'],'samefile_before':entry['os_path_samefile_before']}
actual_critical={k:result[k] for k in ['started_utc','events','process_exit_code','process_exit_confirmed','process_exit_utc','process_exit_utc_ticks','stdout','stderr','streams_read_after_signalled_process','input_after','original_input_after','os_path_samefile_after','input_unchanged','extracted_file_count','extracted_total_bytes','completed_utc','returned_process_object_disposed_after_exit']}
report={'schema':'visio-full-xsd-ascii-extraction-scope.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer':'AI subagent /root/visio_full_xsd_1730','new_small_bindings':newbindings,'task_root_review_start_decision':'Root actual aa1d51 read complete8281B candidate,6270B full v3 delta and contract; subsequent explicit one new ASCII HH/hardlink data extraction approval. This ordinary tool message is scoped authorization, not scientific release.','actual_tool':'790e1c exit0/0.5256342s ran candidate once; full actual args/return in bound ASCII_HH_ACTUAL_TOOL_RETURN.json','entry_critical':entry_critical,'actual_critical':actual_critical,'fresh_destination_read':{'path':str(dest),'exists':True,'recursive_files':0,'recursive_directories':0,'actual_member_data_available':False},'content_scope':{'member_content_search_actually_performed':False,'reason':'Both ordinary HH attempts returned0 but produced no extracted member files. No actual content is available to search; no standalone schema parsing occurred.','prepared_search_source_executed':False,'prepared_search_source':'search_ascii_extracted_content.py was written before ASCII execution and remains unexecuted. Do not treat its potential algorithms/inventory outputs as actual evidence.','earlier_directory_names_content_gap_resolved':False,'cannot_claim':'No assertion that all CHM contents have no applicable XSD or that all4312 directory members were read. Original CHM member contents remain unextracted.','correct_complete_official_2012_main_XSD_obtained':False,'complete_nine_part_dependency_XSD_set_obtained':False,'full_XSD_compilation_validation_done':False,'Office_application_native_VSDX_acceptance_done':False,'new_scientific_results_or_figures':0},'cause_limit':'No cause established for either zero-output outcome. An ASCII hardlink with os.path.samefile=true and exact before/after CHM bytes also produced0 files; neither invocation establishes Unicode handling, policy, archive integrity, forwarding, OS mode or any other cause.','source_failure_history':'Offline ASCII derivation v1 substring assertion failed d7a1d3 exit1 before candidate output/Temp mkdir/HH; source and actual receipt retained. The separately derived v2 anchored semicolon only and tool160fa9 exit0 produced candidate/full delta. This is not SCI/COM failure, and old source was not replayed.','single_use':{'old_v1_powershell_source':'Used/preENTRY cmdlet-not-found; no HH actor or attempt from v1','old_v2_powershell_source':'Unexecuted','old_v3_HH_attempt':'Consumed; original Unicode-path attempt retained with actual ordinaryexit0/0 files','ASCII_HH_attempt':'Consumed; declaration/ENTRY/hardlink/RESULT and logs retained. No third HH, fallback copy, deletion, replay or cleanup.'},'further_scope':'No more HH/package-download/installer expansion in this bounded research task. Current materials do not enable applicable complete-XSD native-file validation. Parent coordinates future application/complete-XSD acceptance under separately satisfied conditions.','research_reference':'Prior bounded Microsoft primary-source availability findings and limitations are inherited from bound CONTENT_EXTRACTION_RESEARCH.json, not new complete XSD availability proof.','no_effects':'No SDK/MSI/downloaded code executed, no default help viewer requested or HTML/JS run, no Visio COM/user app attach/close, no native68 files modified/reopened, no scientific source/model/GPU/weights/old big ZIP accessed, no HANDOFF or sealed old roots rewritten.','method_limit':'Ordinary same returned System.Diagnostics.Process object identity/actual exit plus closed redirected streams. Not a scientific launcher/interpreter two-handle proof, full genealogy proof, independent root process exit, human review or repair-free Office open/render/export/edit/reopen acceptance.'}
raw=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
assert len(raw)<=65536
out=base/'ASCII_EXTRACTION_SCOPE_REVIEW.json'
with out.open('xb') as f:f.write(raw)
print(json.dumps({'report':{'path':str(out),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},'new_small_bindings':len(newbindings),'actualHH_exit0':True,'actual_extracted_files':0,'member_content_search_done':False,'fullXSD_obtained':False,'no_third_HH':True},ensure_ascii=False))

