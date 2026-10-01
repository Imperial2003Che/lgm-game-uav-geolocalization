"""Independently bind prepared T3 inputs to a separately derived display contract."""
from pathlib import Path
import json,hashlib,datetime as dt,difflib
B=Path(__file__).resolve().parent
W=B.parent.parent/'transfer_native_visio_20260930_0006'
checks=0;bindings={}
def ck(x,n):
 global checks
 checks+=1
 if not x:raise AssertionError(n)
def desc(p):
 p=Path(p);b=p.read_bytes();v=dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b));bindings[str(p)]=v;return v
def bind(v):
 got=desc(v['path']);ck(got==v,'bound bytes '+v['path']);return got
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
mine=read(B/'DATA_CONTRACT.json');cpu=read(W/'CPU_STATIC_CONTRACT.json');spec=read(W/'CONVERSION_SPEC.json');prov=read(W/'INPUT_PROVENANCE.json')
for p in [B/'DATA_CONTRACT.json',B/'POWERSHELL_PARSE.json',B/'PREEXEC_SOURCE_FINDING.json',W/'CPU_STATIC_CONTRACT.json',W/'SOURCE_DERIVATION.json']:desc(p)
ck(mine['passed'] and cpu['passed'] and cpu['COMExecuted'] is False,'prepared data, no actual COM claim')
for v in [cpu['spec'],cpu['inputProvenance'],cpu['derivation'],cpu['powershellParse']]+cpu['preparedSources']:bind(v)
ck(desc(W/'build_visio.ps1')['sha256']=='21b292f980dbb62e208f492ef731bfce7d0541bdabce709eaa54a19d8a01a5a6','exact reviewed builder')
ck(not read(B/'POWERSHELL_PARSE.json')['errors'],'independent static PowerShell syntax')
for v in spec['inputs']:bind(v)
ck(spec['inputs']==prov['inputs'],'spec input identities agree')
ck(len(spec['inputs'])==20 and len(prov['copies'])==20,'20 exact selected inputs')
for pair in prov['copies']:
 a=bind(pair['source']);b=bind(pair['copy']);ck((a['sha256'],a['bytes'])==(b['sha256'],b['bytes']),'exact prepared copy')
for f,m in zip(spec['figures'],mine['figures']):
 ck(f['dataset']==m['id'],'figure identity and order')
 for k in ['widthMm','heightMm','viewBox']:ck(f[k]==m[k],'physical page '+k)
 ck(f['expectedShapes']==m['expectedNativeShapes'] and f['expectedTexts']==m['expectedTexts'],'native object contract')
 ck(len(f['primitives'])==len(m['primitives']),'primitive count')
 for p,e in zip(f['primitives'],m['primitives']):
  ck(p['ordinal']==e['ordinal'] and p['tag']==e['tag'] and p['attrs']==e['attrs'],'primitive geometry/style ordinal')
  ck(p['name']=='SVG_'+str(e['ordinal']).zfill(4) and p['ancestors']==[e['attrs']['id']],'primitive source identity')
  if p['tag']=='text':ck(p['text']==e['text'],'exact editable text')
 bind(f['notes']);bind(f['svg']);bind(f['csv']);bind(f['pptx'])
 original=Path(m['notes']['path']).read_text(encoding='utf-8');notes=Path(f['notes']['path']).read_text(encoding='utf-8')
 ck(f['originalNotesSHA256']==hashlib.sha256(original.encode('utf-8')).hexdigest(),'original note identity')
 ck(f['originalNotesCharacters']==len(original),'original note count')
 ck(notes==original+'\n\nCurrent T3 Visio conversion scope: '+spec['limitations'],'notes exact preserved plus stated new scope')
ck(spec['scope']['nativeShapes']==487 and spec['scope']['editableTexts']==144,'overall 487/144')
current=(W/'build_visio.ps1').read_text(encoding='utf-8-sig');old=(B/'BUILD_SOURCE_PREEXEC_BLOCKED.ps1.txt').read_text(encoding='utf-8-sig')
diff=''.join(difflib.unified_diff(old.splitlines(True),current.splitlines(True),fromfile='reviewer_actual_first_read',tofile='reviewed_current_builder'))
with (B/'REVIEWER_FIRST_TO_APPROVED.diff').open('x',encoding='utf-8',newline='\n') as f:f.write(diff)
desc(B/'REVIEWER_FIRST_TO_APPROVED.diff')
decisions=[
 'The initially observed missing executable/regex backslashes and wrong preview prefix are corrected in the pinned final source; no actual COM failure is attributed to that pre-execution finding.',
 'Initial and immediately-before-create Visio inventories must be empty. Each NewOwnedApp resets app, owned and held process. HWND-derived real OS PID, CIM name, held/CIM creation ticks, creation-call time window, exact current parent PID, expected full executable/automation command and invisible empty document state all precede owned=true.',
 'Quit is restricted to confirmed task ownership; unknown references are only released, with no Kill or user-application setting mutation. The failure receipt is now written after finally, with cleanup events and explicit unknown-exit limitations. Actual handle exit and fresh-instance outcomes remain runtime obligations.',
 'Each prepared input/source/spec/notes binding is rechecked before COM. New output/report refusal guards preserve earlier deliverables. Native primitives reverse SVG y and preserve physical point scaling. Arial sizes remain 8/9/10pt; all original labels and source identifiers are preserved.',
 'Saved native VSDX documents are closed and the author application is quit before a separately created application opens the VSDX read-only and exports actual PNG/PDF. This is an intended source path, not proof of executed reopening/export or artifact acceptance.'
]
report=dict(schema='independent-t3-visio-preexecution-review.v1',utc=dt.datetime.now(dt.timezone.utc).isoformat(),passed=True,decision='ACCEPT_PINNED_SOURCE_FOR_ONE_BOUNDED_T3_COM_EXECUTION_BY_PRODUCER_AFTER_ROOT_CONFIRMATION',checks=checks,producerBuilder=desc(W/'build_visio.ps1'),source=desc(Path(__file__)),bindings=list(bindings.values()),manualReview=decisions,scope=dict(figures=2,nativeShapes=487,nativeTexts=144),COMExecutedByReviewer=False,producerCheckerInvoked=False,scientificExecution=False,limits=['Static only: no claim of Windows failure-branch execution, artifact success, process exit, visual acceptance or current scientific admission.','Do not reuse old boot or numeric process IDs; the root reports a new current boot and an unrelated reused numeric PID.','An unconfirmed COM reference may leave an instance; release is not proof of exit and provides no blanket process termination permission.','Producer pre-review snapshot 13924 bytes is an intermediate snapshot with added guards; reviewer retained the actually observed initial 12907-byte source separately.','Artifact XML/worldgeometry/text/data/font/edit-lock review and two original-resolution PNG reviews remain pending.'])
with (B/'PREEXEC_SOURCE_REVIEW.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(passed=True,checks=checks,report=desc(B/'PREEXEC_SOURCE_REVIEW.json')),ensure_ascii=False))
