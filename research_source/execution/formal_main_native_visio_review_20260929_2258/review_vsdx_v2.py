"""Independent review of final Visio package against adopted SVG primitives.
Only standard library. Never imports or executes producer code or scientific code.
"""
from pathlib import Path
import datetime, hashlib, json, math, re, traceback, zipfile
import xml.etree.ElementTree as E
W=Path(__file__).resolve().parent;BASE=W.parent.parent
PROD=BASE/'formal_main_native_visio_20260929_2258'
VN={'v':'http://schemas.microsoft.com/office/visio/2012/main'}
checks=0
STYLES={}
def ck(v,m):
 global checks
 checks+=1
 if not v:raise AssertionError(m)
def near(x,y,m,tol=2e-8):ck(abs(float(x)-float(y))<=tol,m+f': {x} versus {y}')
def desc(p):
 b=Path(p).read_bytes();return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def load(p):return json.loads(Path(p).read_bytes())
def save(p,x):
 with Path(p).open('x',encoding='utf-8',newline='\n') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')
def bound(d):ck(desc(d['path'])==d,'exact artifact binding '+d['path'])
def cells(el):return {c.attrib['N']:c.attrib for c in el.findall('v:Cell',VN)}
def inherited(el,n,family='TextStyle',sec=None,seen=()):
 if sec is None:c=cells(el)
 else:
  s=section(el,sec);row=s.find('v:Row',VN) if s is not None else None;c=cells(row) if row is not None else {}
 if n in c and c[n].get('V')!='Themed' and c[n].get('F')!='Inh':return c[n]
 sid=el.attrib.get(family)
 ck(sid is not None and sid in STYLES and sid not in seen,'explicit inherited style chain '+n)
 return inherited(STYLES[sid],n,family,sec,seen+(sid,))
def val(el,n):
 family='LineStyle' if n in ['BeginArrow','EndArrow'] else 'TextStyle'
 return float(inherited(el,n,family)['V'])
def section(el,n):return el.find(f"v:Section[@N='{n}']",VN)
def rowcells(el,n):
 sec=section(el,n);ck(sec is not None,'section '+n)
 return cells(sec.find('v:Row',VN))
def color(cell,colors):
 v=cell['V'];f=cell.get('F','')
 if re.fullmatch(r'#[a-fA-F0-9]{6}',v):return v.lower()
 if v.isdigit() and int(v) in colors:return colors[int(v)].lower()
 m=re.fullmatch(r'RGB\((\d+),(\d+),(\d+)\)',f)
 if m:return '#'+''.join(f'{int(q):02x}' for q in m.groups())
 raise AssertionError('unhandled actual color '+repr(cell))
def svgcolor(v):return {'white':'#ffffff','black':'#000000'}.get(v,v.lower())
def world(sh,x,y):
 c=cells(sh);w=float(c['Width']['V']);h=float(c['Height']['V']);xx=x-float(c['LocPinX']['V']);yy=y-float(c['LocPinY']['V'])
 if float(c.get('FlipX',{'V':'0'})['V']):xx=-xx
 if float(c.get('FlipY',{'V':'0'})['V']):yy=-yy
 a=float(c.get('Angle',{'V':'0'})['V']);ca=math.cos(a);sa=math.sin(a)
 return (float(c['PinX']['V'])+xx*ca-yy*sa,float(c['PinY']['V'])+xx*sa+yy*ca)
def geometry(sh):
 return [(r.attrib.get('T'),cells(r)) for sec in sh.findall("v:Section[@N='Geometry']",VN) for r in sec.findall('v:Row',VN) if r.attrib.get('Del')!='1']
def point_near(p,q,msg):
 near(p[0],q[0],msg+' x');near(p[1],q[1],msg+' y')
def sorted_points(ps):return sorted((round(x,8),round(y,8)) for x,y in ps)
def polygon_vertices(sh,gg):
 w=val(sh,'Width');h=val(sh,'Height');points=[]
 for typ,c in gg:
  if typ=='RelMoveTo':points.append(world(sh,float(c['X']['V'])*w,float(c['Y']['V'])*h))
  elif typ in ['MoveTo','LineTo']:points.append(world(sh,float(c['X']['V']),float(c['Y']['V'])))
  elif typ=='PolylineTo':
   f=c['A']['V'];ck(re.fullmatch(r'POLYLINE\([0-9eE+., \-]+\)',f) is not None,'native polyline formula')
   a=[float(x) for x in f[len('POLYLINE('):-1].split(',')]
   ck(a[:2]==[0,0] and len(a)%2==0,'observed normalized polyline X/Y type')
   for i in range(2,len(a),2):points.append(world(sh,a[i]*w,a[i+1]*h))
   points.append(world(sh,float(c['X']['V']),float(c['Y']['V'])))
  else:raise AssertionError('unhandled polygon geometry '+typ)
 return points

def main():
 global STYLES
 contract=load(W/'DATA_CONTRACT.json');ck(desc(W/'DATA_CONTRACT.json')['sha256']=='d474e39a9dcb90b7d43fa6d83030a15f44174e5d1950aa022afe83942f14380c','fixed independent contract')
 ck(desc(PROD/'BUILD_REPORT.json')['sha256']=='cd6be22fe4adbb490422014d965b7ebf1ac89d224362cbf1ec931bd575a605ca','fixed final producer build')
 build=load(PROD/'BUILD_REPORT.json');ck(build['passed'] is True and build['scientificExecution'] is False,'producer saved report, not scientific execution')
 for d in [build['source'],build['spec'],build['shapeMap']]:bound(d)
 for d in contract['input_bindings']:bound(d)
 rows={x['dataset']:x for x in build['figures']};ck(set(rows)=={'university1652','sues200'},'two final figures')
 mapping=load(build['shapeMap']['path'])['shapes'];out=[];artifact_bindings=[]
 for fig in contract['figures']:
  ds=fig['dataset'];r=rows[ds]
  for key in ['vsdx','preview','pdf','notes']:bound(r[key]);artifact_bindings.append(r[key])
  note=Path(r['notes']['path']).read_text(encoding='utf-8')
  wi=fig['width_mm']/25.4;hi=fig['height_mm']/25.4;sx=wi/fig['viewbox'][2];sy=hi/fig['viewbox'][3]
  conv=lambda x,y:(float(x)*sx,hi-float(y)*sy)
  with zipfile.ZipFile(r['vsdx']['path']) as z:
   ck(z.testzip() is None,'VSDX ZIP CRC')
   names=z.namelist();ck(len(names)==len(set(names)),'unique ZIP member names')
   pn=[n for n in names if re.fullmatch(r'visio/pages/page\d+\.xml',n)];ck(pn==['visio/pages/page1.xml'],'single native page')
   page=E.fromstring(z.read(pn[0]));document=E.fromstring(z.read('visio/document.xml'));pages=E.fromstring(z.read('visio/pages/pages.xml'))
   colors={int(x.attrib['IX']):x.attrib['RGB'] for x in document.findall('.//v:ColorEntry',VN)}
   fonts={x.attrib['NameU'] for x in document.findall('.//v:FaceName',VN)}
   STYLES={x.attrib['ID']:x for x in document.findall('.//v:StyleSheet',VN)}
   ps=pages.find('.//v:PageSheet',VN);near(val(ps,'PageWidth'),wi,'page width');near(val(ps,'PageHeight'),hi,'page height')
   usr=section(ps,'User');ck(usr is not None,'page User provenance')
   uc={x.attrib['N']:(lambda c: c.attrib['V'] if 'V' in c.attrib else c.text)(x.find("v:Cell[@N='Value']",VN)) for x in usr.findall('v:Row',VN)}
   ck(uc['Notes']==note,'entire User.Notes equals UTF-8 sidecar (including exact CSV)')
   ck(uc['SourceSVG_SHA256']==fig['svg']['sha256'] and uc['SourceCSV_SHA256']==fig['csv']['sha256'],'actual page source SHA')
   shp=page.findall('v:Shapes/v:Shape',VN);ck(len(shp)==fig['shapes'],'all source primitive count')
   ck(not page.findall('.//v:ForeignData',VN),'no page ForeignData')
   ck(not page.findall('.//v:Shape[@Type="Foreign"]',VN),'no Foreign shape')
   ck(not page.findall('.//v:Shapes/v:Shape/v:Shapes',VN),'flat editable objects')
   forbidden=[n for n in names if re.search(r'(^|/)(media|embeddings|oleobjects)(/|$)',n,re.I) or n.lower().endswith('.svg')]
   ck(not forbidden,'no raster/embedded SVG/OLE page payload')
   thumbs=[n for n in names if n.lower().startswith('docprops/thumbnail.')]
   by={s.attrib.get('NameU'):s for s in shp};ck(len(by)==len(shp),'unique NameU')
   mn={x['nameU']:x for x in mapping if x['dataset']==ds};ck(set(mn)==set(by),'producer map names matched actual only as extra evidence')
   text_count=0;geometry_count=0
   for p in fig['primitives']:
    nm=p['shape_name'];ck(nm in by,'independent ordinal identity');sh=by[nm];a=p['attrs'];sc=cells(sh);tag=p['tag']
    ck(sh.attrib.get('Type')=='Shape','native Shape type')
    for key,expected in [('Data1','/'.join(p['ancestors'])),('Data2',tag),('Data3',str(p['ordinal']))]:
     el=sh.find('v:'+key,VN);ck(el is not None and (el.text or '')==expected,'actual native '+key)
    ck(str(mn[nm]['shapeID'])==sh.attrib['ID'],'map ID matches actual (not geometry authority)')
    gg=geometry(sh);ck(bool(gg),'native Geometry exists');geometry_count+=1
    if tag=='text':
     text_count+=1;te=sh.find('v:Text',VN);actual=''.join(te.itertext()) if te is not None else None
     ck(actual==p['text']+'\n','editable text exact plus Visio terminal paragraph newline')
     ch=rowcells(sh,'Character');ck(ch['Font']['V']=='Arial' and 'Arial' in fonts,'resolved font is Arial')
     sz=float(ch['Size']['V'])*72;near(sz,float(a['font-size']),'exact native font pt');ck(sz>=8-1e-8,'native font >=8pt')
     ck(int(ch.get('Style',{'V':'0'})['V'])==(1 if a.get('font-weight')=='bold' else 0),'bold/plain text')
     ck(color(ch['Color'],colors)==svgcolor(a['fill']),'text color')
     near(val(sh,'FillPattern'),0,'text transparent fill');near(val(sh,'LinePattern'),0,'text transparent outline')
     near(val(sh,'Angle'),0,'unrotated SVG text')
     w=val(sh,'Width');h=val(sh,'Height');near(h,float(a['font-size'])*1.4/72,'text native height')
     left=val(sh,'PinX')-val(sh,'LocPinX');bottom=val(sh,'PinY')-val(sh,'LocPinY')
     anchor=left+({'middle':.5,'end':1}.get(a.get('text-anchor'),0))*w
     near(anchor,float(a['x'])*sx,'SVG text anchor to native box')
     near(bottom,hi-float(a['y'])*sy-float(a['font-size'])*.35/72,'SVG baseline placement formula')
     for q in ['LeftMargin','RightMargin','TopMargin','BottomMargin']:near(val(sh,q),0,'zero text margins')
     near(val(sh,'VerticalAlign'),1,'text vertical centre')
     near(inherited(sh,'HorzAlign','TextStyle','Paragraph')['V'],1,'text horizontal centre')
    else:
     fill=a.get('fill','none');stroke=a.get('stroke','none')
     near(val(sh,'FillPattern'),0 if fill=='none' else 1,'fill enabled')
     if fill!='none':ck(color(sc['FillForegnd'],colors)==svgcolor(fill),'native fill color')
     near(val(sh,'LinePattern'),0 if stroke=='none' else 1,'line enabled')
     if stroke!='none':
      ck(color(sc['LineColor'],colors)==svgcolor(stroke),'native line color');near(val(sh,'LineWeight'),float(a['stroke-width'])*sx,'stroke physical width')
     near(val(sh,'BeginArrow'),0,'no begin arrow');near(val(sh,'EndArrow'),0,'no end arrow')
     if tag=='line':
      points=[world(sh,float(c['X']['V']),float(c['Y']['V'])) for typ,c in gg if typ in ['MoveTo','LineTo']]
      ck(len(points)==2,'native line endpoints');point_near(points[0],conv(a['x1'],a['y1']),'line start');point_near(points[1],conv(a['x2'],a['y2']),'line end')
     elif tag=='rect':
      points=[world(sh,float(c['X']['V']),float(c['Y']['V'])) for typ,c in gg if typ in ['MoveTo','LineTo']]
      x,y,ww,hh=[float(a[k]) for k in ['x','y','width','height']]
      exp=[conv(x,y),conv(x+ww,y),conv(x+ww,y+hh),conv(x,y+hh)]
      ck(len(points)==5,'rectangle native corner count')
      for pt,eq in zip(sorted(points[:-1]),sorted(exp)):point_near(pt,eq,'rectangle native corner')
      point_near(points[0],points[-1],'closed rectangle')
     elif tag=='polygon':
      points=polygon_vertices(sh,gg)
      exp=[conv(*q.split(',')) for q in a['points'].split()]
      ck(len(points)==len(exp)+1,'polygon vertex count')
      for i,pt in enumerate(exp):point_near(points[i],pt,'polygon vertex')
      point_near(points[-1],points[0],'closed polygon')
     elif tag=='circle':
      ell=[c for typ,c in gg if typ=='Ellipse'];ck(len(ell)==1,'native ellipse primitive');ec=ell[0]
      point_near(world(sh,float(ec['X']['V']),float(ec['Y']['V'])),conv(a['cx'],a['cy']),'ellipse centre')
      center=conv(a['cx'],a['cy']);rx=float(a['r'])*sx;ry=float(a['r'])*sy
      ea=world(sh,float(ec['A']['V']),float(ec['B']['V']));eb=world(sh,float(ec['C']['V']),float(ec['D']['V']))
      near(abs(ea[0]-center[0]),rx,'ellipse x radius');near(ea[1],center[1],'ellipse radius x y');near(eb[0],center[0],'ellipse radius y x');near(abs(eb[1]-center[1]),ry,'ellipse y radius')
     else:raise AssertionError(tag)
   ck(text_count==fig['texts'],'all editable text');ck(geometry_count==fig['shapes'],'all native geometry')
   out.append({'dataset':ds,'vsdx':r['vsdx'],'preview':r['preview'],'pdf':r['pdf'],'notes':r['notes'],'shapes':len(shp),'texts':text_count,'page_mm':[fig['width_mm'],fig['height_mm']],'thumbnail_parts_not_page_shapes':thumbs,'no_page_foreign_or_raster':True})
 result={'status':'passed_independent_native_visio_artifact_review','accepted_with_stated_limits':True,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':desc(__file__),'checks':checks,'contract':desc(W/'DATA_CONTRACT.json'),'build_report':desc(PROD/'BUILD_REPORT.json'),'producer_source_bindings':[build['source'],build['spec'],build['shapeMap']],'artifact_bindings':artifact_bindings,'figures':out,'limits':contract['limits']+['Visio text baseline follows measured Arial textbox placement; numerical anchor/font/geometry verification is separate from actual reopened-export visual review.','Author COM events document SaveAs/close/reopen/Export; this independent script reads resulting ZIP/XML and never starts COM or calls producer checker.','Document thumbnail previews are allowed; no page ForeignData, embedded SVG/raster/OLE shape is accepted.','No automatic data-linked chart claim: editable flat native geometry and text.']}
 save(W/'ARTIFACT_REVIEW.json',result);print(json.dumps({'report':desc(W/'ARTIFACT_REVIEW.json'),'checks':checks}))
if __name__=='__main__':
 try:main()
 except Exception:
  save(W/'ARTIFACT_FAILURE_V2.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':desc(__file__),'checks':checks,'traceback':traceback.format_exc()});raise
