from pathlib import Path
import json,hashlib,datetime
base=Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\visio_full_xsd_research_20260930_1730')
expected={'CONTENT_EXTRACTION_RESEARCH.json':(15739,'b9a5fce676dcb2e0777b6fbba0e493c5470600012dc09410a63a036f7ed65a21'),'ASCII_EXTRACTION_SCOPE_REVIEW.json':(13270,'b64556edb1b3cd66d29a819005ece5ce2f82ae3b7f11372916bc6a1d3ceedf78')}
refs=[]
for name in ['CONTENT_EXTRACTION_RESEARCH.json','ASCII_EXTRACTION_SCOPE_REVIEW.json','REPORT_ACTUAL_TOOL_RETURN.json','ASCII_SCOPE_SEAL_ACTUAL_TOOL_RETURN.json','ASCII_REPAIR_PREPARATION_ACTUAL_TOOL_RETURN.json','EPISODE_COMPLETION.md','seal_delivery.py']:
 p=base/name;n=p.stat().st_size
 assert n<=65536
 raw=p.read_bytes();sha=hashlib.sha256(raw).hexdigest()
 if name in expected:assert (len(raw),sha)==expected[name]
 refs.append({'path':str(p),'bytes':len(raw),'sha256':sha})
delivery={'schema':'visio-full-xsd-bounded-research-delivery.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'report_references':refs,'scope':'Bounded official-schema availability research completed; no complete applicable2012/main XSD set or full nine-part dependencies obtained. Two separate actual system HH extraction attempts returned0 but produced0 member files, including ASCII os.path.samefile-confirmed hardlink input. Actual member content search not possible, no standalone-schema parse/full-XSD/app acceptance. Each original failure/source/attempt/runtime record retained.','binding_method':'Only7 new final report/receipt/summary/source bytes read in this delivery sealer; core22 and20 saved indexes inherited, not a rerun of their source scopes or any old scientific/control suite. ASCII repair-preparation actualreceipt supplied after sealed report as explicit additional edge.','not_proved':'No assertion all CHM contents lack XSD; no zero-output cause established; prior4312-name content gap remains. Ordinary HH Process actual exit not scientific launcher/interpreter dual exit or repair-free Visio open/render/edit/reopen.','no_further_actions':'No third HH, new SDK download, installation, CHM decoder, Windows API, HTML/JS execution, COM/user-app attach/close, VSDX write, science/GPU/model/weight/old bigZIP read or HANDOFF write.'}
raw=(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
with (base/'DELIVERY.json').open('xb') as f:f.write(raw)
print(json.dumps({'path':str(base/'DELIVERY.json'),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'local_final_binding_count':len(refs),'fullXSD_obtained':False,'application_acceptance':False},ensure_ascii=False))

