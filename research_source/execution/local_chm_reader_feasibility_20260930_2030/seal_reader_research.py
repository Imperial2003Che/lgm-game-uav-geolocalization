from pathlib import Path
import json,hashlib,datetime,ast,re
base=Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\local_chm_reader_feasibility_20260930_2030')
def binding(p,limit=262144):
 size=p.stat().st_size
 assert 0<=size<=limit
 raw=p.read_bytes()
 assert len(raw)==size
 return raw,{'path':str(p),'bytes':size,'sha256':hashlib.sha256(raw).hexdigest()}
names=['ACTUAL_INVENTORY_TOOL_RETURNS.json','INVENTORY_CALL_ARGUMENTS.json','seal_reader_research.py']
local=[binding(base/n)[1] for n in names]
installed_sources=[
 Path(r'C:\Users\17703\AppData\Local\Programs\Python\Python311\Lib\site-packages\fsspec\implementations\libarchive.py'),
 Path(r'C:\ProgramData\anaconda3\conda-meta\libarchive-3.8.2-h6c023e8_0.json'),
 Path(r'C:\ProgramData\anaconda3\Lib\site-packages\libarchive\ffi.py'),
 Path(r'C:\ProgramData\anaconda3\Lib\site-packages\libarchive\__init__.py'),
 Path(r'C:\ProgramData\anaconda3\Library\include\archive.h'),
 Path(r'C:\ProgramData\anaconda3\Library\share\man\man5\libarchive-formats.5'),
 Path(r'C:\ProgramData\anaconda3\Library\share\man\man3\archive_read_format.3'),
]
src={};bindings=[]
for p in installed_sources:
 raw,b= binding(p,65536)
 bindings.append(b);src[p.name]=raw.decode('utf-8',errors='replace')
ffi_tree=ast.parse(src['ffi.py'])
formats=[]
for node in ffi_tree.body:
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='READ_FORMATS' for t in node.targets):
  assert isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id=='set'
  formats=list(ast.literal_eval(node.value.args[0]))
header_functions=sorted(set(re.findall(r'archive_read_support_format_[a-zA-Z0-9_]+',src['archive.h'])))
format_sections=re.findall(r'^\.Ss (.+)$',src['libarchive-formats.5'],flags=re.M)
assert formats
report={
 'schema':'local-chm-reader-feasibility-research.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer':'AI subagent /root/visio_full_xsd_1730','local_new_report_source_receipts':local,'installed_source_bindings':bindings,
 'prior_authority_read_this_turn':[
 {'path':str(base.parent/'HANDOFF.md'),'scope':'Actual latest tail80 read first, including19:13:28.644136+00:00 CAMP/DAC manuscript delivery; no journal hash/write.'},
 {'path':str(base.parent/'visio_full_xsd_research_20260930_1730/CONTENT_EXTRACTION_RESEARCH.json'),'bytes':15739,'sha256':'b9a5fce676dcb2e0777b6fbba0e493c5470600012dc09410a63a036f7ed65a21','scope':'Actual saved report read; SHA inherited, no current CHM hash or old extraction replay.'},
 {'path':str(base.parent/'visio_full_xsd_research_20260930_1730/ASCII_EXTRACTION_SCOPE_REVIEW.json'),'bytes':13270,'sha256':'b64556edb1b3cd66d29a819005ece5ce2f82ae3b7f11372916bc6a1d3ceedf78','scope':'Actual saved report read; SHA inherited, ordinary HH0/0files remains unresolved content gap.'}],
 'actual_inventory':{
  'PATH_names_checked':['7z','7za','7zz','7zFM','chmextract','extract_chmLib','archmage','dumpchm','unar','bsdtar','tar','cabextract','hhc','python'],
  'PATH_results':'Only tar.exe at C:/Windows/system32 and Python311/WindowsApps aliases matched; the named non-HH CHM/7zip tools were absent from current PATH. No alias interpreter launched.',
  'installation_roots':'Immediate matching directories of C:/Program Files, C:/Program Files (x86), and user Local/Programs, selected uninstall registry roots, plus filenames beneath Git, bundled dependencies, user Python root; no all-computer traversal.',
  'package_manager_scopes':'User scoop/apps, ProgramData/chocolatey and user WinGet/Packages did not exist in saved checks.',
  'Python_package_scopes':'Matching immediate package items absent in user Python311 and bundled Python sites; Anaconda root discovered from saved uninstall DisplayIcon/UninstallString, no uninstaller invoked.',
  'Anaconda':'C:/ProgramData/anaconda3 base environment has libarchive-c5.1, library3.8.2 and archive.dll; no environment directories returned in saved immediate envs enumeration.',
  'filenames_not_tool_evidence':'rg wildcard hits such as chmod.exe, benchmark files, attachment assets and DefSchm.tcl were not adopted as CHM readers; scientific-package filenames were incidental enumeration only, no such source read/import.',
  'scope_limit':'Absence applies only to these named PATH/registry/installed-root/package/name scopes. Portable tools, other paths/users/drives and arbitrary library modules were not exhaustively searched.'},
 'installed_archive_tools':[
 {'path':r'C:\Windows\system32\tar.exe','actual_help_version':'a752f7 tool exit0; help/version stdout identifies bsdtar/libarchive3.8.8. Individual --help exit was not separately saved; wrapper final result alone does not establish it.','SDK_archive_read_attempted':False,'CHM_support_confirmed':False,'why':'Help documents generic list/extract but does not name CHM; no installed matching3.8.8 C-source/full-format table independently inspected.'},
 {'path':r'C:\ProgramData\anaconda3\Library\bin\bsdtar.exe','saved_bytes_stat':1241416,'actual_help_version':'bbfee3 tool exit0; both native --help and --version LASTEXITCODE0 explicitly saved; identifies bsdtar/libarchive3.8.2.','SDK_archive_read_attempted':False,'CHM_support_confirmed':False,'why':'Installed3.8.2 header, ffi source and man-page list support other formats but no CHM; CAB/7zip support does not imply CHM container parsing.'},
 {'path':r'C:\ProgramData\anaconda3\Library\bin\archive.dll','saved_bytes_stat':1216840,'loaded_by_custom_DLL_or_API_call':False,'scope':'No custom DLL load, export query or API experiment. Ordinary bsdtar help/version executes its existing installed runtime only; manual ctypes wrapper imports not executed.'}],
 'installed_source_findings':{
  'ffi_READ_FORMATS_literal':formats,'source_ast_scope':'One pure static extraction of saved installed Python source literal using ast.literal_eval; no libarchive import, ctypes DLL load or function execution.',
  'native_header_declared_read_format_functions':header_functions,'man_supported_format_sections':format_sections,
  'READ_FORMATS_contains_CHM':any('chm' in f.lower() for f in formats),'header_CHM_read_function_declared':any('chm' in f.lower() for f in header_functions),'man_CHM_section':any('chm' in f.lower() for f in format_sections),
  'raw_limitation':'Installed archive_read_format.3 states raw treats an arbitrary stream as one data entry and is excluded by all. That does not parse CHM directories or decompress its LZX members. No raw invocation performed.',
  'fsspec_wrapper':'User Python fsspec libarchive.py imports libarchive/libarchive.ffi and documents generic supported archive formats including CAB/7zip; it is a wrapper, not a CHM decoder. Corresponding package absent in that user site; presence in Anaconda does not add CHM support to its documented list.',
  'limitations':'Static installed header/wrapper/docs and native help/version are finite capability evidence, not an actual DLL supported-format introspection or proof no undocumented/runtime variation exists.'},
 'conclusion':{
  'verified_installed_CHM_decoder_found':False,'ready_bounded_complete_SDK_XSD_extraction_command':None,'full_official_2012_main_or_nine_part_XSD_obtained':False,'member_payload_read_this_turn':False,'full_XSD_validation':False,'native_Visio_application_acceptance':False,
  'finding':'No verified CHM-capable data reader was found within the examined local scopes. The actually present generic libarchive tools do not advertise/declaratively expose CHM in inspected local3.8.2 sources/docs; current system3.8.8 CHM support was not tested. No complete-XSD extraction is ready to execute from this evidence.',
  'no_global_claim':'This does not prove all installed tools lack CHM support, nor that the SDK/CHM contains no complete XSD. Earlier4312-name member-content gap remains.'},
 'unexecuted_optional_root_only_probe':{
  'why_optional':'If root decides a narrow installed-native format-detection observation adds value despite current documentation, a bounded read-only listing could determine whether one generic reader recognizes this exact CHM. This is not a verified extraction方案 or executable release.',
  'argv':[r'C:\Windows\system32\tar.exe','-tf',r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\schema_package_research_20260930_1228\sdk_chm_data\VISSDK.CHM'],
  'not_executed':True,'constraints':'Root decision first; no -x/write/copy/current-HH replay, no raw-format fallback; ≤60s bounded ordinary process with actual stdout/stderr+exit captured; preserve any failure/partial output and do not infer full members from generic return0. Prior CHM hash inherited, not repeated. Actual list success would still require another separately reviewed bounded member-read method and complete dependencies before XSD acceptance.'},
 'no_actions':'No third HH, SDK/CHM copy/hash/content read, archive -tf/-x/input command, install/download, Python library import/DLL API experiment, CHM decoder run, HTML/JS, Office COM, user app attach/close/cleanup, native figures/science source/model/GPU/weights/old bigZIP or HANDOFF/old-root write.',
 'method':'AI source/tool reading only, no human review. Ordinary help/version/tool returns are not scientific held dual exits or schema/application acceptance.'
}
raw=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
assert len(raw)<=65536
out=base/'LOCAL_READER_FEASIBILITY_REVIEW.json'
with out.open('xb') as f:f.write(raw)
print(json.dumps({'path':str(out),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'local_receipt_source_edges':len(local),'installed_source_edges':len(bindings),'verified_CHM_decoder':False,'SDK_read_or_hash':False,'HH':False},ensure_ascii=False))

