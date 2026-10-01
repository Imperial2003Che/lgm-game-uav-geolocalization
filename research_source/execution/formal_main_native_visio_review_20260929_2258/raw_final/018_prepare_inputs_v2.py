"""Read only adopted small figure sources; create a bounded Visio conversion spec."""
from pathlib import Path
import datetime,hashlib,json,zipfile,xml.etree.ElementTree as E
W=Path(__file__).resolve().parent;OUT=W.parent;S=OUT/'formal_results_native_20260929';P=OUT/'formal_main_native_ppt_20260929_1548';O=W/'output_v2'
def d(p):
 b=Path(p).read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def save(p,j):
 with p.open('x',encoding='utf8') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')
def bind(p,h):
 v=d(p);assert v['sha256']==h,(p,v);return v
roots=[bind(S/'ROOT_NATIVE_SVG_REVIEW.json','ac010cc27c27fa94a9fdd3e860af84c330a8e4cc6efa3c66b2e6a8000d6253ca'),bind(S/'INDEPENDENT_NATIVE_SVG_REVIEW.json','9dbcc7f38df2057e900f8a13571b00eadb867d2e890e8948f3eea6e1f6501977'),bind(P/'ROOT_DELIVERY_ADOPTION.json','4d01ad9310e8d726e7a0b5e9852142a51f56a079a30e386d814161f8b328787b'),bind(S/'PRIMARY_CLAIM_REVIEW.json','0e29cdb0412b148100788b02276e9a9ef4a7aed4a1f5d892fb088a0ff184cdb6'),bind(S/'v2/CAPTIONS.md','2dd6fef4c13f2348256b68ede5e099e51ae307b65b93b0ead3afcc88cd3697a9')]
sr=json.loads(Path(roots[0]['path']).read_bytes());pr=json.loads(Path(roots[2]['path']).read_bytes());pb={x['path']:x for x in pr['bindings']}
O.mkdir(exist_ok=True)
for sub in ['sources','previews','notes']: (O/sub).mkdir(exist_ok=True)
inputs=list(roots);figs=[]
limitations='Only these two main-result figures are converted to native Visio. Three-seed task-specific means and sample SD (not CI); no pooling or significance. Low positive <0.1 labels and exact CSV values are preserved. Full is lower than Visual for both mean R@1 and mAP in 10 of 11 official tasks; the street-to-satellite exception has low absolute performance. No scientific evaluation, query, model, full ranking, AP, checkpoint, cache or image reread. Inherited checkpoint/cache/image SHA authority and historical metadata-chain gaps remain. Other Visio figures and the whole project are not complete.'
for f in sr['figures']:
 ds=f['dataset'];sv=bind(Path(f['svg']['path']),f['svg']['sha256']);cv=bind(Path(f['source']['path']),f['source']['sha256']);ppt=P/f'output/formal_main_{ds}_native_editable_v2.pptx';pv=bind(ppt,pb[str(ppt)]['sha256']);inputs.extend([sv,cv,pv])
 tree=E.fromstring(Path(sv['path']).read_bytes());vb=list(map(float,tree.attrib['viewBox'].split()));width=float(tree.attrib['width'][:-2]);height=float(tree.attrib['height'][:-2]);primitives=[]
 def walk(el,anc):
  tag=el.tag.rsplit('}',1)[-1];anc=anc+([el.attrib['id']] if 'id' in el.attrib else [])
  if tag in ['rect','line','circle','polygon','text']:
   assert 'transform' not in el.attrib
   primitives.append({'ordinal':len(primitives)+1,'name':'SVG_'+str(len(primitives)+1).zfill(4),'tag':tag,'ancestors':anc,'attrs':el.attrib,'text':''.join(el.itertext()) if tag=='text' else None})
  elif tag not in ['svg','g','title','desc']:raise AssertionError(tag)
  for child in el:walk(child,anc)
 walk(tree,[])
 with zipfile.ZipFile(ppt) as z:
  xml=E.fromstring(z.read('ppt/notesSlides/notesSlide1.xml'));ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main'};notes='\n'.join(x.text or '' for x in xml.findall('.//a:t',ns))
 notes+='\n\nCurrent Visio conversion scope: '+limitations
 np=O/'notes'/f'{ds}_NOTES.txt';np.write_text(notes,encoding='utf8')
 figs.append({'dataset':ds,'widthMm':width,'heightMm':height,'viewBox':vb,'svg':sv,'csv':cv,'pptx':pv,'notes':d(np),'primitives':primitives,'expectedShapes':len(primitives),'expectedTexts':sum(x['tag']=='text' for x in primitives)})
for i in inputs:
 src=Path(i['path']);name=src.name
 if (O/'sources'/name).exists():raise AssertionError(name)
 (O/'sources'/name).write_bytes(src.read_bytes())
spec={'schema':'native-visio-conversion-spec.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':d(Path(__file__)),'inputs':inputs,'figures':figs,'limitations':limitations,'geometry':'SVG x/viewBoxWidth*pageWidth(in); Y=(viewBoxHeight-y)/viewBoxHeight*pageHeight(in); native DrawRectangle/DrawLine/DrawOval/closed DrawPolyline; text anchors preserved, Arial8/9/10 exact physical pt. White SVG background is also one native rectangle.','notesStorage':'Original PPT v2 notes plus current scope in exact sidecar and page User.Notes in VSDX.'}
assert sum(f['expectedTexts'] for f in figs)==216 and sum(f['expectedShapes'] for f in figs)==785
save(W/'INPUT_PROVENANCE.json',{'inputs':inputs,'source':spec['source'],'figures':[{'dataset':f['dataset'],'notes':f['notes']} for f in figs]});save(W/'CONVERSION_SPEC.json',spec)
print(json.dumps({'spec':d(W/'CONVERSION_SPEC.json'),'shapes':785,'texts':216}))
