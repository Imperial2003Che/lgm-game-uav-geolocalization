"""Seal only this independent Visio review and selected new/small sources.
Does not rerun passed display/geometry/editability checks or scientific work.
"""
from pathlib import Path
import csv, datetime, difflib, hashlib, json, struct, traceback
W=Path(__file__).resolve().parent;BASE=W.parent.parent
P=BASE/'formal_main_native_visio_20260929_2258';O=P/'output_v2'
SEM=W.parent/'formal_main_native_visio_scope_review_20260929_2258'
def d(p):
 b=Path(p).read_bytes();return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def load(p):return json.loads(Path(p).read_bytes())
def put(p,x):
 with Path(p).open('x',encoding='utf8',newline='\n') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')
def exact(p,h):
 x=d(p);assert x['sha256']==h,(p,x);return x
def main():
 data=load(W/'DATA_CONTRACT.json');art=load(W/'ARTIFACT_REVIEW.json');edit=load(W/'EDITABILITY_REVIEW.json');failure=load(W/'ARTIFACT_FAILURE.json');build=load(P/'BUILD_REPORT.json')
 exact(W/'DATA_CONTRACT.json','d474e39a9dcb90b7d43fa6d83030a15f44174e5d1950aa022afe83942f14380c')
 exact(W/'ARTIFACT_REVIEW.json','e7e18313492ba36eab82503999c13d7f4a6e4df37dfdab70c45237ee55289278')
 exact(W/'EDITABILITY_REVIEW.json','3ead2f5af7c325b6de637656c1c23191fecc574bbd092c3afb3c451f7b2334c9')
 exact(P/'BUILD_REPORT.json','cd6be22fe4adbb490422014d965b7ebf1ac89d224362cbf1ec931bd575a605ca')
 sem=exact(SEM/'REVIEW.json','5f21400c74515f1d0aa0cef0f09d7853f8bab15e80497dda35982d324db939aa')
 semv3=exact(SEM/'V3_ADDENDUM.json','0e26b6e02e5c3ff9adce3fe369f198bfd5c525dee8b2a213e8b7dd5f7004926d')
 assert (data['checks'],art['checks'],edit['checks'],failure['checks'])==(2663,22396,47890,27)
 for r in [data,art,edit,failure]:assert d(r['source']['path'])==r['source']
 old=(W/'review_vsdx.py').read_text(encoding='utf8');new=(W/'review_vsdx_v2.py').read_text(encoding='utf8')
 expected=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='review_vsdx.py',tofile='review_vsdx_v2.py'))
 assert (W/'REVIEW_V1_TO_V2.patch').read_text(encoding='utf8')==expected
 public=[O/'README.md',O/'CAPTIONS.md',O/'FIGURE_INDEX.csv']
 for p in public:assert p.is_file(),p
 # These public files are read by the reviewer before this sealing call; the
 # following are narrowly scoped closure assertions, not a new science test.
 readme=public[0].read_text(encoding='utf8')
 exact(public[0],'bd8f625ea0755772432068f1298bc2b8ce7d28e57dfc9f91ad536fd5ade895d8')
 assert '10 of the 11' in readme and 'sample SD' in readme and 'Visio' in readme
 idx=list(csv.DictReader(public[2].read_text(encoding='utf8').splitlines()));assert len(idx)==2
 for row,fig in zip(idx,art['figures']):
  assert row['dataset']==fig['dataset'] and int(row['native_shapes'])==fig['shapes'] and int(row['editable_texts'])==fig['texts']
  assert (O/row['vsdx']).resolve()==Path(fig['vsdx']['path']).resolve()
 now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 visuals=[]
 for fig in art['figures']:
  b=Path(fig['preview']['path']).read_bytes();assert hashlib.sha256(b).hexdigest()==fig['preview']['sha256'];assert b[:8]==b'\x89PNG\r\n\x1a\n'
  wh=struct.unpack('>II',b[16:24]);expected_wh=(1031,782) if fig['dataset']=='university1652' else (1031,1362);assert wh==expected_wh
  visuals.append({'dataset':fig['dataset'],'preview':fig['preview'],'dimensions_pixels':list(wh),'tool':'functions tools.view_image(detail=original)','actual_reviewed':True,'finding':'Both native Visio-reopened previews were actually viewed separately at original resolution. No visible clipping, overlap or missing legend/text. R@1 mean/SD cell labels, low-positive <0.1 and exact zero displays, all mAP intervals/marker variants, direction labels, SUES 150/200/250/300 m labels and SD/task-specific footnotes are legible.','not_claimed':'No interactive editing test, no PDF page rendering by this reviewer, and no scientific re-evaluation.'})
 put(W/'VISUAL_REVIEW.json',{'status':'passed_actual_two_original_visio_reopened_previews','utc_recorded':now,'sealing_source':d(__file__),'figures':visuals,'reviewer':'independent subagent sep29_eval_audit','scope':'Actual viewing is separate from numerical XML checking and from producer/root visual reviews.'})
 source_review={'status':'reviewed_bounded_display_and_native_conversion_sources','utc':now,'sealing_source':d(__file__),'sources_actually_read':[d(P/'prepare_inputs_v2.py'),d(P/'build_visio.ps1'),d(P/'BUILD_V1_TO_V2.patch'),d(P/'BUILD_V2_TO_V3_UNEXECUTED.patch'),d(P/'SOURCE_REVISION.json'),d(SEM/'REVIEW.md')],'executed_builder':build['source'],'static_review':sem,'findings':['Authoring uses native rectangles, straight lines, ovals, closed polylines and editable Shape.Text, with separate ordinal/tag/ancestor metadata; no SVG import as a foreign object.','Page axes convert SVG top-left coordinates to physical inch Y-up world coordinates. Numerical artifact checker uses actual ShapeSheet values, angles and native polyline rows; text actual Arial font and physical size checked.','Long page User.Notes has exact full text equality to each sidecar including its stored CSV values. Native strings may be in Cell body (long notes) or V attribute (short SHA).','Actual v2 reports two separate new instances (42148 and 36900), author SaveAs+close and fresh reopen+export; held exit0 is producer evidence, not independently held exit proof by this reviewer.','The two unexercised v2 ownership/handle failure branches remain limitations on reuse. v3 is a distinct unexecuted hardening source, not the source of these figure bytes.','Historical caption copy is preserved. Active public README/notes limit current native Visio delivery to these two main-result figures.','All six variants and eleven tasks remain, including Full lower than Visual in both saved means for ten tasks. No new significance or pooled performance claim.'],'not_performed':['No producer checker execution or import.','No COM, PowerPoint, GPU, scientific-library or model execution by this reviewer.','No old seed-statistics suite, query arrays, weights, cache or image-data reads.']}
 put(W/'SOURCE_REVIEW.json',source_review)
 history={'independent_contract':{'executions':1,'exit_code':0,'checks':2663},'independent_native_artifacts_v1':{'executions':1,'exit_code':1,'checks_at_refusal':27,'reason':'Incorrect independent parser assumption that all User string values are Cell body text; short exact SHA strings are V attributes. No artifact/scientific data failure.','preserved_source':d(W/'review_vsdx.py'),'failure':d(W/'ARTIFACT_FAILURE.json')},'independent_native_artifacts_v2':{'executions':1,'exit_code':0,'checks':22396,'change':'Only read V attribute when present, otherwise Cell text, and distinct failure-report filename.','source':d(W/'review_vsdx_v2.py'),'diff':d(W/'REVIEW_V1_TO_V2.patch')},'independent_editability':{'executions':1,'exit_code':0,'checks':47890,'scope':'Additional new lock/visibility concern only; did not rerun passed geometry.'},'producer_history':'prepare v1 background-count refusal and builder v1 incorrect Visio instance ID versus OS PID failure are retained by producer; v2 actual completed path accepted. Task-created orphan forced exit was separately handled, not a natural exit0. v3 source remains unexecuted.'}
 paths=[Path(x['path']) for x in data['input_bindings']]+[Path(x['path']) for x in art['artifact_bindings']]
 paths += [P/n for n in ['prepare_inputs.py','prepare_inputs_v2.py','PREPARE_V1_TO_V2.patch','build_visio.ps1','build_visio_v2.ps1','BUILD_V1_TO_V2.patch','BUILD_FAILURE.json','BUILD_REPORT.json','SOURCE_REVISION.json','UNEXECUTED_HARDENING.json','BUILD_V2_TO_V3_UNEXECUTED.patch','build_visio_v3_unexecuted.ps1','CONVERSION_SPEC.json','INPUT_PROVENANCE.json','NATIVE_SHAPE_MAP.json']]
 paths += public+[SEM/'REVIEW.json',SEM/'REVIEW.md',SEM/'V3_ADDENDUM.json',SEM/'V3_ADDENDUM.md']
 paths += [W/n for n in ['derive_contract.py','DATA_CONTRACT.json','review_vsdx.py','ARTIFACT_FAILURE.json','review_vsdx_v2.py','REVIEW_V1_TO_V2.patch','ARTIFACT_REVIEW.json','review_editability.py','EDITABILITY_REVIEW.json','SOURCE_REVIEW.json','VISUAL_REVIEW.json','seal_review.py']]
 unique=[];seen=set()
 for p in paths:
  key=str(p.resolve()).lower()
  if key not in seen:unique.append(p);seen.add(key)
 raw=W/'raw_final';raw.mkdir(exist_ok=False);bindings=[]
 for i,p in enumerate(unique,1):
  original=d(p);q=raw/(f'{i:03d}_'+p.name);q.write_bytes(p.read_bytes());snap=d(q);assert (original['sha256'],original['bytes'])==(snap['sha256'],snap['bytes']);bindings.append({'source':original,'snapshot':snap})
 limits=data['limits']+art['limits'][-4:]+edit['limitations']+['Actual COM save/reopen/Quit records are read producer evidence; no independent live process or held-exit audit was performed here.','Two v2 unexercised error paths prevent approving it as a general reusable controller; the later v3 source is unexecuted.','The SVG background rectangles are included in 785 total native shapes; counts are not substituted for per-shape checking.']
 metadata={'schema':'independent-native-visio-review.v1','utc':now,'accepted_with_stated_limits':True,'sealing_source':d(__file__),'scope':{'figures':2,'svg_primitives_native_shapes':785,'actual_text_shapes':216,'R1_cells':66,'mAP_intervals':66,'new_scientific_runs':0},'execution_history':history,'raw_evidence_bindings':bindings,'interpretation_limits':limits}
 put(W/'METADATA.json',metadata)
 (W/'README.md').write_text('Independent native Visio review: two main-result figures\n\nAccepted with stated limits. New display contract (2663 checks), actual VSDX geometry/text/provenance review (v2: 22396 checks), and a separate lock/visibility check (47890) passed. Both actual Visio-reopened PNGs were viewed at original resolution: University 1031x782 and SUES 1031x1362. The independent first artifact reader rejected after 27 checks because short User SHA fields are attributes, not long-string body content; its source, failure and complete v2 diff are retained. No old suite was rerun.\n\n785 native flat shapes include two backgrounds, with 216 editable Arial text shapes (8/9/10 pt), 66 R@1 cells and 66 mAP mean +/- sample-SD intervals. A document thumbnail EMF is a preview only; no page ForeignData, raster, embedded SVG or OLE exists. Notes and exact source SHA fields round-trip. Source CSV means/SD were copied, not scientifically recomputed.\n\nThree seeds per task; SD is not CI. Six variants and eleven tasks remain separate, with both SUES directions at four heights. Full remains lower than Visual in both means on ten tasks. Low absolute street performance is retained. No model, query, full ranking/AP, weight, cache, image or GPU work occurred. Original inherited evidence limitations persist. These two Visio figures do not complete the overall project.\n\nProducer v2 actual normal save/reopen path is the provenance of the artifacts. Its receipts are not our independently held process-exit proof. Prior producer prepare/COM failures remain preserved, and v3 hardened source was not executed. Native lock inspection is not an interactive edit test.\n',encoding='utf8')
 delivery={'schema':'independent-native-visio-delivery.v1','utc':now,'accepted_with_stated_limits':True,'source':d(__file__),'data_contract':d(W/'DATA_CONTRACT.json'),'artifact_review':d(W/'ARTIFACT_REVIEW.json'),'editability_review':d(W/'EDITABILITY_REVIEW.json'),'source_review':d(W/'SOURCE_REVIEW.json'),'visual_review':d(W/'VISUAL_REVIEW.json'),'metadata':d(W/'METADATA.json'),'readme':d(W/'README.md'),'separate_static_scope_review':sem,'independent_sources':[d(W/n) for n in ['derive_contract.py','review_vsdx.py','review_vsdx_v2.py','review_editability.py','seal_review.py']],'executions':history,'actual_artifacts':art['artifact_bindings'],'limitations':limits}
 delivery['separate_unexecuted_v3_static_addendum']=semv3
 put(W/'DELIVERY.json',delivery);print(json.dumps({'delivery':d(W/'DELIVERY.json'),'metadata':d(W/'METADATA.json'),'snapshot_count':len(bindings)}))
if __name__=='__main__':
 try:main()
 except Exception:
  put(W/'SEAL_FAILURE.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':d(__file__),'traceback':traceback.format_exc()});raise
