"""Bounded new VSDX editability/visibility check only, not geometry re-execution."""
from pathlib import Path
import datetime, hashlib, json, traceback, zipfile, xml.etree.ElementTree as E
W=Path(__file__).resolve().parent;N={'v':'http://schemas.microsoft.com/office/visio/2012/main'};checks=0
def d(p):
 b=Path(p).read_bytes();return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def ck(v,m):
 global checks
 checks+=1
 if not v:raise AssertionError(m)
def put(p,x):
 with p.open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')
def main():
 report=json.loads((W/'ARTIFACT_REVIEW.json').read_bytes());ck(d(W/'ARTIFACT_REVIEW.json')['sha256']=='e7e18313492ba36eab82503999c13d7f4a6e4df37dfdab70c45237ee55289278','fixed geometry review')
 results=[]
 for fig in report['figures']:
  ck(d(fig['vsdx']['path'])==fig['vsdx'],'same reviewed VSDX bytes')
  with zipfile.ZipFile(fig['vsdx']['path']) as z:
   doc=E.fromstring(z.read('visio/document.xml'));page=E.fromstring(z.read('visio/pages/page1.xml'))
   styles={s.attrib['ID']:s for s in doc.findall('.//v:StyleSheet',N)}
   def value(el,key,seen=()):
    c=el.find(f"v:Cell[@N='{key}']",N)
    if c is not None and c.attrib.get('F')!='Inh':return float(c.attrib['V'])
    sid=el.attrib.get('TextStyle');ck(sid in styles and sid not in seen,'explicit lock style chain')
    return value(styles[sid],key,seen+(sid,))
   shapes=page.findall('v:Shapes/v:Shape',N)
   locknames=['LockWidth','LockHeight','LockMoveX','LockMoveY','LockDelete','LockBegin','LockEnd','LockRotate','LockVtxEdit','LockTextEdit','LockFormat','LockSelect','NoObjHandles','NonPrinting','HideText']
   for sh in shapes:
    for k in locknames:ck(value(sh,k)==0,'unlocked/visible '+k+' '+sh.attrib['NameU'])
    for g in sh.findall("v:Section[@N='Geometry']",N):
     c=g.find("v:Cell[@N='NoShow']",N);ck(c is not None and c.attrib['V']=='0','geometry visible')
   ck(len(shapes)==fig['shapes'],'scope only reviewed shapes')
   results.append({'dataset':fig['dataset'],'vsdx':fig['vsdx'],'shapes':len(shapes),'checked_zero_properties':locknames,'geometry_NoShow_zero':True})
 result={'status':'passed_bounded_native_editability_xml_review','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':d(__file__),'artifact_review':d(W/'ARTIFACT_REVIEW.json'),'checks':checks,'figures':results,'limitations':['Only VSDX native lock/display property resolution, not an interactive user editing test.','No geometry suite rerun, no COM startup, no producer checker call, no old scientific input reads.']}
 put(W/'EDITABILITY_REVIEW.json',result);print(json.dumps({'report':d(W/'EDITABILITY_REVIEW.json'),'checks':checks}))
if __name__=='__main__':
 try:main()
 except Exception:
  put(W/'EDITABILITY_FAILURE.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':d(__file__),'checks':checks,'traceback':traceback.format_exc()});raise
