from pathlib import Path
import json,hashlib,re,datetime,xml.etree.ElementTree as ET
base=Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\visio_full_xsd_research_20260930_1730')
attempt=Path(r'C:\Users\17703\AppData\Local\Temp\LGM_GAME_CHM_20260930_1745_1730_ascii_v1')
dest=attempt/'decompiled_data'
result_path=attempt/'RESULT.json'
result_raw=result_path.read_bytes()
assert len(result_raw)<=65536
result=json.loads(result_raw)
assert result['process_exit_confirmed'] is True and type(result['process_exit_code']) is int and result['process_exit_code']==0
assert result['input_unchanged'] is True
assert result['os_path_samefile_after']['value']['samefile'] is True
files=sorted((p for p in dest.rglob('*') if p.is_file()),key=lambda p:p.relative_to(dest).as_posix())
assert len(files)==result['extracted_file_count'] and len(files)<=5000
total=sum(p.stat().st_size for p in files)
assert total==result['extracted_total_bytes'] and total<=104857600
patterns={
 '2012_main_namespace':re.compile(rb'schemas\.microsoft\.com/office/visio/2012/main',re.I),
 '2011_core_namespace':re.compile(rb'schemas\.microsoft\.com/office/visio/2011/1/core',re.I),
 'schema_XML_or_encoded_start':re.compile(rb'(?:<|&lt;)\s*(?:xs:|xsd:)?schema(?:\s|&gt;|>)',re.I),
 'targetNamespace':re.compile(rb'targetnamespace',re.I),
 'xsd_filename_or_extension':re.compile(rb'(?:[a-z0-9_.-]+\.xsd)',re.I),
 'VisioSchema15':re.compile(rb'visioschema15',re.I),
}
inventory=[];hits=[];standalone_schemas=[]
for p in files:
 assert not p.is_symlink()
 size=p.stat().st_size
 assert 0<=size<=2097152
 raw=p.read_bytes()
 assert len(raw)==size
 binding={'relative_path':p.relative_to(dest).as_posix(),'path':str(p),'bytes':size,'sha256':hashlib.sha256(raw).hexdigest()}
 inventory.append(binding)
 flags={}
 for key,pattern in patterns.items():
  ms=list(pattern.finditer(raw))
  if ms:
   flags[key]={'occurrences':len(ms),'bounded_raw_contexts':[raw[max(0,m.start()-80):min(len(raw),m.end()+180)].decode('utf-8',errors='replace') for m in ms[:3]]}
 if flags:hits.append({**binding,'matches':flags})
 if p.suffix.lower() in ('.xsd','.xml'):
  try:root=ET.fromstring(raw)
  except ET.ParseError:continue
  if root.tag=='{http://www.w3.org/2001/XMLSchema}schema':
   standalone_schemas.append({**binding,'targetNamespace':root.get('targetNamespace'),'version':root.get('version'),'imports_includes':[{'tag':c.tag,'namespace':c.get('namespace'),'schemaLocation':c.get('schemaLocation')} for c in root if c.tag in ('{http://www.w3.org/2001/XMLSchema}include','{http://www.w3.org/2001/XMLSchema}import','{http://www.w3.org/2001/XMLSchema}redefine')],'parsed_by_stdlib_XML_only':True,'not_compiled_or_validated':True})
old=base.parent/'schema_package_research_20260930_1228/chm_directory_attempt_v1/SDK_CHM_DIRECTORY_CANDIDATE.json'
old_size=old.stat().st_size
assert old_size<=2097152
directory=json.loads(old.read_bytes())
expected={}
for m in directory['members']:
 n=m['name']
 if n.startswith('/') and not n.endswith('/') and not n.startswith('/#') and not n.startswith('/$'):
  expected[n.lstrip('/').lower()]=m['declared_length']
actual={b['relative_path'].lower():b['bytes'] for b in inventory}
missing=sorted(n for n in expected if n not in actual)
unexpected=sorted(n for n in actual if n not in expected)
size_mismatch=[{'relative_path':n,'declared_bytes':expected[n],'actual_bytes':actual[n]} for n in expected.keys()&actual.keys() if expected[n]!=actual[n]]
def write(name,obj):
 raw=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
 assert len(raw)<=4194304
 p=base/name
 with p.open('xb') as f:f.write(raw)
 return {'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
inv=write('ASCII_EXTRACTED_MEMBER_CONTENT_BINDINGS.json',{'schema':'actual-sdk-chm-member-content-bindings.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Each actual extracted member was read as data only once for bounded raw content search/SHA, including binary data. No HTML/JS executed. Not original whole CHM content coverage unless internal excluded streams are also accounted.','member_count':len(inventory),'total_bytes':total,'members':inventory})
hit=write('ASCII_SCHEMA_CONTENT_HITS.json',{'schema':'actual-sdk-chm-schema-content-hits.v1','scope':'Raw byte string hits within actual extracted members; HTML-encoded schema text and XML standalone roots are distinguished. Hits/fragments do not prove a complete applicable official schema closure.','matching_members':len(hits),'hits':hits,'standalone_XSD_schema_roots':standalone_schemas})
report={'schema':'actual-sdk-chm-ascii-content-search-research.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer':'AI subagent /root/visio_full_xsd_1730','result_binding':{'path':str(result_path),'bytes':len(result_raw),'sha256':hashlib.sha256(result_raw).hexdigest()},'ordinary_HH_exit_code':0,'actual_file_count':len(files),'actual_total_bytes':total,'member_content_bindings':inv,'content_hits':hit,'raw_search_reads':'Every actual extracted file read with size<=2MiB and aggregate<=100MiB; bounded context excerpts stored. No member payload executed. XML parses limited to standalone .xml/.xsd roots; no schema adaptation or assembly.','saved_directory_comparison':{'source_path':str(old),'source_scope':'Inherited old adopted directory report, read saved member names/declared sizes only. No original CHM parse/decoder suite repeated. Only public slash paths excluding #/$ internal control objects compared.','all_saved_members':directory['member_count'],'compared_noninternal_file_paths':len(expected),'missing':missing,'unexpected':unexpected,'declared_size_mismatch':size_mismatch,'noninternal_name_size_set_matches':not(missing or unexpected or size_mismatch),'cannot_prove':'CHM internal control streams and directory members excluded above were not extracted/read. Saved declared sizes and current raw bytes are not a full CHM codec authenticity proof.'},'category_matching_file_counts':{k:sum(k in h['matches'] for h in hits) for k in patterns},'standalone_schema_count':len(standalone_schemas),'standalone_2012_main_schema_candidates':[s for s in standalone_schemas if s['targetNamespace']=='http://schemas.microsoft.com/office/visio/2012/main'],'full_2012_schema_dependency_closure_obtained':False,'full_XSD_validation_done':False,'application_VSDX_acceptance_done':False,'new_scientific_result':False,'cause_of_old_zero_output':'Not established. New ASCII extraction outcome does not prove the prior zero-output cause.','conclusion':'Applicable full official 2012/main XSD collection remains unadopted. Any raw standalone applicable candidate needs complete dependencies/root coordination before full-XSD compilation or native-file validation. HTML schema references/fragments alone do not close this gap.','single_use':'Both original and ASCII attempts retained; no third HH invocation, no replay or cleanup.','scope':'No geometry/source scientific suite repeat, no Visio COM/app attach/close, no native VSDX change, no SDK installer or downloaded binary run, no old weights/big ZIP read, no HANDOFF modification.'}
binding=write('ASCII_CONTENT_SEARCH_REVIEW.json',report)
print(json.dumps({'report':binding,'inventory':inv,'hits':hit,'actual_files':len(files),'actual_bytes':total,'standalone_2012_candidates':len(report['standalone_2012_main_schema_candidates']),'counts':report['category_matching_file_counts'],'noninternal_name_size_set_matches':report['saved_directory_comparison']['noninternal_name_size_set_matches']},ensure_ascii=False))

