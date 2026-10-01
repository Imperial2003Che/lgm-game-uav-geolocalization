"""Bounded author export check of the new T4 figures; not an independent audit."""
from pathlib import Path
import csv,datetime,hashlib,io,json,struct,xml.etree.ElementTree as ET,zipfile
W=Path(__file__).resolve().parent
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
SVG='{http://www.w3.org/2000/svg}'
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
build=json.loads((W/'BUILD_REPORT.json').read_bytes());sample=json.loads((W/'BUILD_REPORT_SAMPLE.json').read_bytes())
bound(build['source']);bound(build['pptx']);bound(build['inputProvenance'])
check(build['source']==sample['source'],'Unchanged source between sample and first full build')
check(build['figureCount']==11 and build['numericPoints']==792 and build['plottedStrata']==132 and build['metricPanels']==99,'Exact final scope')
prov=json.loads(Path(build['inputProvenance']['path']).read_bytes())
for d in prov['inputs']:
    b=Path(d['path']).read_bytes();check(hashlib.sha256(b).hexdigest()==d['sha256'] and len(b)==d['bytes'],'Small input SHA/size')
for name in ['transactions_t4_strata.json','transactions_t4_strata.csv']:
    copies=W/'output/source_data'/name
    source=next(d for d in prov['inputs'] if Path(d['path']).name==name)
    check(copies.read_bytes()==Path(source['path']).read_bytes(),'Exact original source copy')
t4=json.loads((W/'output/source_data/transactions_t4_strata.json').read_bytes())
raw={(r['task'],r['seed'],r['level']):r for r in t4['rows'] if r['factor']=='visual_margin_quartile'}
check(len(raw)==132 and sum(not r['summary']['performance_claim_eligible'] for r in raw.values())==48,'132 margin /48 ineligible')
flat=list(csv.DictReader((W/'output/source_data/MARGIN_STRATA_132.csv').open(encoding='utf-8',newline='')))
check(len(flat)==132,'Exact flattened stratum count')
for r in flat:
    old=raw[r['task'],int(r['seed']),r['level']]
    check(r['membership_sha256']==old['membership_sha256'] and int(r['queries'])==old['summary']['queries'],'Saved membership and N')
    check(r['performance_claim_eligible']==str(old['summary']['performance_claim_eligible']).lower(),'Saved exact eligibility')
    for metric in ['r_at_1','official_trapezoid_mAP','MRR']:
        for variant in ['visual','full']:
            n=old['summary']['metrics'][metric][variant]
            check(float(r[f'{variant}_{metric}'])==n and float(r[f'{variant}_{metric}_x100'])==n*100,'Direct fields×100 only')
review=[]
with zipfile.ZipFile(build['pptx']['path']) as z:
    check(z.testzip() is None,'PPT ZIP CRC');check(not any(n.startswith(('ppt/media/','ppt/charts/','ppt/embeddings/')) for n in z.namelist()),'No media or workbook substitutions')
    pres=ET.fromstring(z.read('ppt/presentation.xml'));sz=pres.find('p:sldSz',NS)
    check(len(pres.findall('p:sldIdLst/p:sldId',NS))==11,'11 pages')
    for page,fig in enumerate(build['figures'],1):
        for k in ['svg','preview','sourceCSV']:bound(fig[k])
        check(sz.attrib=={'cx':str(round(fig['widthMm']*36000)),'cy':str(round(fig['heightMm']*36000))},'Actual physical dimensions')
        svg=ET.fromstring(Path(fig['svg']['path']).read_bytes());ids={e.get('id'):e for e in svg if e.get('id')}
        check(svg.get('width')=='181.9mm' and abs(float(svg.get('height').removesuffix('mm'))-fig['heightMm'])<1e-10,'SVG physical mm')
        check(list(map(float,svg.get('viewBox').split()))==[0,0,fig['widthPt'],fig['heightPt']],'SVG physical-point coordinates')
        check(not svg.findall('.//'+SVG+'image'),'No raster SVG');check(len(ids)==len(fig['primitives'])+1,'Unique SVG ids')
        xml=ET.fromstring(z.read(f'ppt/slides/slide{page}.xml'));shapes=xml.findall('.//p:sp',NS)
        check(not xml.findall('.//p:pic',NS),'No picture shapes');check(len(shapes)==len(fig['primitives']),'Native object per primitive')
        fonts=[]
        for sh,p in zip(shapes,fig['primitives']):
            check(sh.find('p:nvSpPr/p:cNvPr',NS).get('name')==fig['task']+'/'+p['id'],'Stable object names')
            xf=sh.find('p:spPr/a:xfrm',NS);o=xf.find('a:off',NS);e=xf.find('a:ext',NS);x,y,cx,cy=map(int,[o.get('x'),o.get('y'),e.get('cx'),e.get('cy')])
            check(x>=0 and y>=0 and x+cx<=int(sz.get('cx'))+1 and y+cy<=int(sz.get('cy'))+1,'Object frames inside page')
            if p['tag']=='text':
                actual=''.join(n.text or '' for n in sh.findall('p:txBody/a:p/a:r/a:t',NS));check(actual==p['text']==''.join(ids[p['id']].itertext()),'Exact PPT/SVG text')
                rr=sh.findall('p:txBody/a:p/a:r/a:rPr',NS);check(len(rr)==1 and int(rr[0].get('sz'))==round(p['fontSize']*100)>=800,'Actual XML >=8pt');fonts.append(int(rr[0].get('sz')))
                check(rr[0].find('a:latin',NS).get('typeface')=='Arial','Arial');check(float(ids[p['id']].get('font-size'))==p['fontSize']>=8,'SVG >=8 physical pt')
                body=sh.find('p:txBody/a:bodyPr',NS);check(body.get('wrap')=='none' and body.find('a:noAutofit',NS) is not None,'No shrinking or wrapping')
                near(x+(cx/2 if p['anchor']=='middle' else cx if p['anchor']=='end' else 0),p['x']*12700);near(y,(p['y']-p['fontSize']*.92)*12700)
            elif p['tag']=='line':
                near(x,min(p['x1'],p['x2'])*12700);near(y,min(p['y1'],p['y2'])*12700);near(cx,abs(p['x2']-p['x1'])*12700);near(cy,abs(p['y2']-p['y1'])*12700)
                check((xf.get('flipV','0')=='1')==((p['x2']-p['x1'])*(p['y2']-p['y1'])<0),'Actual segment orientation');check(sh.find('p:spPr/a:prstGeom',NS).get('prst')=='line','Native line');near(int(sh.find('p:spPr/a:ln',NS).get('w')),p['width']*12700)
            else:
                near(x,(p['x']-p['r'])*12700);near(y,(p['y']-p['r'])*12700);near(cx,p['r']*25400);near(cy,p['r']*25400);check(sh.find('p:spPr/a:prstGeom',NS).get('prst')==('ellipse' if p['tag']=='circle' else 'rect'),'Native marker')
        note=ET.fromstring(z.read(f'ppt/notesSlides/notesSlide{page}.xml'));nt='\n'.join(t.text or '' for t in note.findall('.//a:t',NS)).replace('\r\n','\n')
        check(fig['caption'] in nt and Path(fig['sourceCSV']['path']).read_text(encoding='utf-8').strip() in nt,'Full caption and exact12-row table in notes')
        check(len(fig['panels'])==9,'Nine metric×seed panels')
        for panel in fig['panels']:
            x0,y0,pw,ph=[panel['plot'][k] for k in ['x','y','width','height']]
            check(panel['yRange']==[0,100] and panel['xCategories']==['q1_low','q2_mid_low','q3_mid_high','q4_high'],'Zero-based scale and categorical quartiles')
            for series in panel['series']:
                check(len(series['points'])==4,'Four categories per series')
                for p in series['points']:
                    r=raw[fig['task'],panel['seed'],p['level']];value=r['summary']['metrics'][panel['metric']][series['variant']]
                    check(p['fraction']==value and p['scaledValue']==value*100,'Point equals saved adopted value')
                    check(p['queries']==r['summary']['queries'] and p['performance_claim_eligible']==r['summary']['performance_claim_eligible'],'Point N/flag')
                    check(p['x']==x0+(p['quartile']-.5)*pw/4 and p['y']==y0+ph-value*ph,'Categorical x and metric y')
                    pid=f"{fig['task']}/seed-{panel['seed']}/{panel['metric']}/{series['variant']}/value-Q{p['quartile']}"
                    check(float(''.join(ids[pid].itertext()))-value*100<0.000500001 and abs(float(''.join(ids[pid].itertext()))-value*100)<=0.000500001,'Three-decimal visible point value')
        markers=[p for p in fig['primitives'] if '/point-' in p['id']];segments=[p for p in fig['primitives'] if '/segment-' in p['id']]
        check(len(markers)==72 and len(segments)==54,'72 points and54 categorical guides')
        png=Path(fig['preview']['path']).read_bytes();check(png[:8]==b'\x89PNG\r\n\x1a\n','PNG');dims=struct.unpack('>II',png[16:24]);check(abs(dims[0]-fig['widthPt']*8/3)<2 and abs(dims[1]-fig['heightPt']*8/3)<2,'Imported PNG dimensions')
        review.append({'page':page,'task':fig['task'],'nativeShapes':len(shapes),'textObjects':len(fonts),'minFontHundredthsPt':min(fonts),'nativePoints':72,'guideSegments':54,'PNGDimensions':dims,'preview':fig['preview']})
finalizer=json.loads(Path(build['receipt']['path']).read_bytes());check(finalizer['finalSha256']==build['pptx']['sha256'] and finalizer['packageIntegrity']['status']=='pass' and finalizer['presentationLayout']['exitCode']==0 and finalizer['firstPartyImport']['passed'],'Finalizer pass')
result={'schema':'producer-native-t4-margin-package-review.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passed':True,'source':desc(__file__),'build':desc(W/'BUILD_REPORT.json'),'assertions':checks,'figures':review,'totalNativeShapes':sum(x['nativeShapes'] for x in review),'totalTexts':sum(x['textObjects'] for x in review),'nativePoints':792,'guideSegments':594,'independent':False,'limits':['Author export consistency check, not independent acceptance.','No old T4 query/quantile/membership/mean/NPZ/model statistics rerun.','Actual visual inspection documented separately.']}
save(W/'PRODUCER_PACKAGE_REVIEW.json',result)
print(json.dumps({'passed':True,'checks':checks,'nativeShapes':result['totalNativeShapes'],'texts':result['totalTexts'],'report':desc(W/'PRODUCER_PACKAGE_REVIEW.json')}))
