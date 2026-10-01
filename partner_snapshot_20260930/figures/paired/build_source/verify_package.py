"""Bounded author export check; no query-derived selection or success reconstruction."""
from pathlib import Path
import csv,datetime,difflib,hashlib,json,struct,xml.etree.ElementTree as ET,zipfile
W=Path(__file__).resolve().parent;NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'};SVG='{http://www.w3.org/2000/svg}'
checks=0
def check(v,m):
    global checks
    checks+=1
    if not v:raise AssertionError(m)
def desc(p):
    p=Path(p);b=p.read_bytes();return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def bound(d):check(desc(d['path'])==d,'SHA/size')
def near(a,b):check(abs(a-b)<=1.01,'EMU rounding')
def save(p,j):
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')
build=json.loads((W/'BUILD_REPORT.json').read_bytes());sample=json.loads((W/'BUILD_REPORT_SAMPLE.json').read_bytes());rev=json.loads((W/'SOURCE_REVISION.json').read_bytes())
for d in [build['source'],sample['source'],build['pptx'],build['inputProvenance'],rev['before'],rev['after'],rev['diff']]:bound(d)
diff=''.join(difflib.unified_diff(Path(rev['before']['path']).read_text(encoding='utf-8').splitlines(keepends=True),Path(rev['after']['path']).read_text(encoding='utf-8').splitlines(keepends=True),fromfile='build_paired.mjs',tofile='build_paired_v2.mjs'));check(diff==Path(rev['diff']['path']).read_text(encoding='utf-8'),'Complete revision diff')
check(build['figureCount']==11 and build['pairedRows']==132 and build['points']==264 and build['guides']==198 and build['panels']==33,'Exact new scope')
for old in sample['figures']:
    new=next(f for f in build['figures'] if f['task']==old['task']);check(old['panels']==new['panels'],'Sample data/points unchanged in v2');check(Path(old['sourceCSV']['path']).read_bytes()==Path(new['sourceCSV']['path']).read_bytes(),'Sample/final CSV unchanged')
prov=json.loads(Path(build['inputProvenance']['path']).read_bytes())
for d in prov['inputs']:
    b=Path(d['path']).read_bytes();check(hashlib.sha256(b).hexdigest()==d['sha256'] and len(b)==d['bytes'],'Small bound inputs')
source=next(d for d in prov['inputs'] if Path(d['path']).name=='transactions_t5_selective_calibration.json');copy=W/'output/source_data/transactions_t5_selective_calibration.json';check(copy.read_bytes()==Path(source['path']).read_bytes(),'Exact original JSON copy')
t5=json.loads(copy.read_bytes());raw={(r['task'],r['seed'],r['requested_coverage']):r for r in t5['paired_comparisons']};native={(r['task'],r['seed'],r['variant']):r for r in t5['native_rows']}
flat=list(csv.DictReader((W/'output/source_data/PAIRED_SUCCESS_132.csv').open(encoding='utf-8',newline='')));check(len(flat)==132,'132 flattened display rows')
for r in flat:
    old=raw[r['task'],int(r['seed']),float(r['requested_coverage'])];nv=native[r['task'],int(r['seed']),'visual'];nf=native[r['task'],int(r['seed']),'full']
    check(int(r['full_query_N'])==nv['risk_coverage']['queries']==nf['risk_coverage']['queries'],'Saved shared full N')
    check(r['full_query_membership_sha256']==nv['query_membership_sha256']==nf['query_membership_sha256'],'Saved full-query membership binding')
    for k in ['realized_coverage','selected_queries_per_variant','visual_full_selected_query_overlap']:check(float(r[k])==old[k],'Direct saved display field')
    for v in ['visual','full']:check(float(r[v+'_success_rate'])==old['coverage_constrained_success'][v+'_rate'] and float(r[v+'_success_percent'])==old['coverage_constrained_success'][v+'_rate']*100,'Saved utility fraction and×100 only')
    check(float(r['realized_coverage_percent'])==old['realized_coverage']*100,'Saved realized x scaling')
review=[]
with zipfile.ZipFile(build['pptx']['path']) as z:
    check(z.testzip() is None,'PPT CRC');check(not any(n.startswith(('ppt/media/','ppt/charts/','ppt/embeddings/')) for n in z.namelist()),'No embedded image/workbook substitution')
    pres=ET.fromstring(z.read('ppt/presentation.xml'));sz=pres.find('p:sldSz',NS);check(len(pres.findall('p:sldIdLst/p:sldId',NS))==11,'11 pages')
    for page,fig in enumerate(build['figures'],1):
        for k in ['svg','preview','sourceCSV']:bound(fig[k])
        check(sz.attrib=={'cx':str(round(fig['widthMm']*36000)),'cy':str(round(fig['heightMm']*36000))},'Physical dimensions')
        svg=ET.fromstring(Path(fig['svg']['path']).read_bytes());ids={e.get('id'):e for e in svg if e.get('id')}
        check(svg.get('width')=='181.9mm' and abs(float(svg.get('height').removesuffix('mm'))-fig['heightMm'])<1e-10,'SVG physical mm');check(list(map(float,svg.get('viewBox').split()))==[0,0,fig['widthPt'],fig['heightPt']],'Physical point coordinates');check(not svg.findall('.//'+SVG+'image'),'No rasterSVG');check(len(ids)==len(fig['primitives'])+1,'Unique SVG ids')
        xml=ET.fromstring(z.read(f'ppt/slides/slide{page}.xml'));shapes=xml.findall('.//p:sp',NS);check(not xml.findall('.//p:pic',NS) and len(shapes)==len(fig['primitives']),'Native object per primitive');fonts=[]
        for sh,p in zip(shapes,fig['primitives']):
            check(sh.find('p:nvSpPr/p:cNvPr',NS).get('name')==fig['task']+'/'+p['id'],'Stable object name');xf=sh.find('p:spPr/a:xfrm',NS);o=xf.find('a:off',NS);e=xf.find('a:ext',NS);x,y,cx,cy=map(int,[o.get('x'),o.get('y'),e.get('cx'),e.get('cy')]);check(x>=0 and y>=0 and x+cx<=int(sz.get('cx'))+1 and y+cy<=int(sz.get('cy'))+1,'Objects within page')
            if p['tag']=='text':
                actual=''.join(n.text or '' for n in sh.findall('p:txBody/a:p/a:r/a:t',NS));check(actual==p['text']==''.join(ids[p['id']].itertext()),'PPT/SVG exact text');rr=sh.findall('p:txBody/a:p/a:r/a:rPr',NS);check(len(rr)==1 and int(rr[0].get('sz'))==round(p['fontSize']*100)>=800,'OOXML physical font at least8pt');fonts.append(int(rr[0].get('sz')));check(rr[0].find('a:latin',NS).get('typeface')=='Arial' and float(ids[p['id']].get('font-size'))==p['fontSize']>=8,'Arial/SVG8pt');body=sh.find('p:txBody/a:bodyPr',NS);check(body.get('wrap')=='none' and body.find('a:noAutofit',NS) is not None,'No shrinking');near(x+(cx/2 if p['anchor']=='middle' else cx if p['anchor']=='end' else 0),p['x']*12700);near(y,(p['y']-p['fontSize']*.92)*12700)
            elif p['tag']=='line':
                near(x,min(p['x1'],p['x2'])*12700);near(y,min(p['y1'],p['y2'])*12700);near(cx,abs(p['x2']-p['x1'])*12700);near(cy,abs(p['y2']-p['y1'])*12700);check((xf.get('flipV','0')=='1')==((p['x2']-p['x1'])*(p['y2']-p['y1'])<0),'Line orientation');check(sh.find('p:spPr/a:prstGeom',NS).get('prst')=='line','Native line');near(int(sh.find('p:spPr/a:ln',NS).get('w')),p['width']*12700)
            else:
                near(x,(p['x']-p['r'])*12700);near(y,(p['y']-p['r'])*12700);near(cx,p['r']*25400);near(cy,p['r']*25400);check(sh.find('p:spPr/a:prstGeom',NS).get('prst')==('ellipse' if p['tag']=='circle' else 'rect'),'Native marker');ln=sh.find('p:spPr/a:ln',NS);near(int(ln.get('w')),p['width']*12700);check(ln.find('a:solidFill/a:srgbClr',NS).get('val')==p['stroke'].lstrip('#'),'Marker stroke');check(sh.find('p:spPr/a:noFill',NS) is not None if p['fill']=='none' else sh.find('p:spPr/a:solidFill/a:srgbClr',NS).get('val')==p['fill'].lstrip('#'),'Marker fill')
        note=ET.fromstring(z.read(f'ppt/notesSlides/notesSlide{page}.xml'));nt='\n'.join(n.text or '' for n in note.findall('.//a:t',NS)).replace('\r\n','\n');check(fig['caption'] in nt and Path(fig['sourceCSV']['path']).read_text(encoding='utf-8').strip() in nt,'Full caption and exact12-row notes')
        check(len(fig['panels'])==3,'Three seed panels')
        for panel in fig['panels']:
            px,py,pw,ph=[panel['plot'][k] for k in ['x','y','width','height']];check(panel['xRange']==panel['yRange']==[0,100],'0–100 axes');N=native[fig['task'],panel['seed'],'visual']['risk_coverage']['queries'];check(panel['queries']==N,'Saved N')
            for s in panel['series']:
                check([p['requested_coverage'] for p in s['points']]==[.5,.75,.9,1],'Exact four points; no fakeorigin')
                for p in s['points']:
                    r=raw[fig['task'],panel['seed'],p['requested_coverage']];rate=r['coverage_constrained_success'][s['variant']+'_rate'];check(p['success_rate']==rate and p['x']==px+r['realized_coverage']*pw and p['y']==py+ph-rate*ph,'Direct saved x/y');prefix=f"{fig['task']}/seed-{panel['seed']}";value=''.join(ids[f"{prefix}/{s['variant']}/success-cov-{p['requested_coverage']:g}"].itertext());check(abs(float(value)-rate*100)<=.000500001,'Three-decimal utility display')
            for r in panel['rows']:
                q=r['requested_coverage'];old=raw[fig['task'],panel['seed'],q];prefix=f"{fig['task']}/seed-{panel['seed']}/count/cov-{q:g}"
                check(''.join(ids[prefix+'/requested'].itertext())==str(int(q*100)),'Requested table percent');check(''.join(ids[prefix+'/kN'].itertext())==f"{old['selected_queries_per_variant']}/{N}",'Saved exact k/N text');check(''.join(ids[prefix+'/overlap'].itertext())==str(old['visual_full_selected_query_overlap']),'Saved overlap table')
        check(sum('/point-cov-' in p['id'] for p in fig['primitives'])==24 and sum('/guide-' in p['id'] for p in fig['primitives'])==18,'24 actual points and18guides')
        png=Path(fig['preview']['path']).read_bytes();check(png[:8]==b'\x89PNG\r\n\x1a\n','PNG');dims=struct.unpack('>II',png[16:24]);check(abs(dims[0]-fig['widthPt']*8/3)<2 and abs(dims[1]-fig['heightPt']*8/3)<2,'Actual imported PNG dimensions');review.append({'page':page,'task':fig['task'],'nativeShapes':len(shapes),'textObjects':len(fonts),'minFontHundredthsPt':min(fonts),'points':24,'guides':18,'PNGDimensions':dims,'preview':fig['preview']})
f=json.loads(Path(build['receipt']['path']).read_bytes());check(f['finalSha256']==build['pptx']['sha256'] and f['packageIntegrity']['status']=='pass' and f['presentationLayout']['exitCode']==0 and f['firstPartyImport']['passed'],'Finalizer passed')
j={'schema':'producer-t5-paired-package-review.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passed':True,'independent':False,'source':desc(__file__),'build':desc(W/'BUILD_REPORT.json'),'assertions':checks,'figures':review,'totalNativeShapes':sum(f['nativeShapes'] for f in review),'totalTexts':sum(f['textObjects'] for f in review),'points':264,'guides':198,'limits':['Producer export consistency, not independent acceptance.','Builder checks saved k=ceil(requested*N), realized=k/N and ranges only; no query-derived selection, utility, overlap, test or CI reconstruction.','Actual visual review documented separately.']};save(W/'PRODUCER_PACKAGE_REVIEW.json',j);print(json.dumps({'passed':True,'checks':checks,'nativeShapes':j['totalNativeShapes'],'texts':j['totalTexts'],'report':desc(W/'PRODUCER_PACKAGE_REVIEW.json')}))
