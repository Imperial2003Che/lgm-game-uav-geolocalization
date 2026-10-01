"""Bounded author export checks only; no original ECE/query statistics recomputed."""
from pathlib import Path
import csv,datetime,difflib,hashlib,json,struct,xml.etree.ElementTree as ET,zipfile
W=Path(__file__).resolve().parent
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'};SVG='{http://www.w3.org/2000/svg}'
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
diff=''.join(difflib.unified_diff(Path(rev['before']['path']).read_text(encoding='utf-8').splitlines(keepends=True),Path(rev['after']['path']).read_text(encoding='utf-8').splitlines(keepends=True),fromfile='build_reliability.mjs',tofile='build_reliability_v2.mjs'))
check(diff==Path(rev['diff']['path']).read_text(encoding='utf-8'),'Full exact revision diff')
check(build['figureCount']==11 and build['nativeRecords']==66 and build['binRecords']==990 and build['occupiedBins']==140 and build['emptyBins']==850 and build['savedECEValues']==66,'Exact new figure scope')
for old in sample['figures']:
    new=next(f for f in build['figures'] if f['task']==old['task'])
    check(old['panels']==new['panels'],'All saved sample data and plot coordinates unchanged')
    check(Path(old['sourceCSV']['path']).read_bytes()==Path(new['sourceCSV']['path']).read_bytes(),'Sample/final table identical')
prov=json.loads(Path(build['inputProvenance']['path']).read_bytes())
for d in prov['inputs']:
    b=Path(d['path']).read_bytes();check(hashlib.sha256(b).hexdigest()==d['sha256'] and len(b)==d['bytes'],'Small input SHA/size')
source=next(d for d in prov['inputs'] if Path(d['path']).name=='transactions_t5_selective_calibration.json')
copy=W/'output/source_data/transactions_t5_selective_calibration.json';check(copy.read_bytes()==Path(source['path']).read_bytes(),'Exact source JSON copy')
t5=json.loads(copy.read_bytes());raw={(r['task'],r['seed'],r['variant']):r for r in t5['native_rows']}
flat=list(csv.DictReader((W/'output/source_data/RELIABILITY_BINS_990.csv').open(encoding='utf-8',newline='')));check(len(flat)==990,'990 flattened bins')
for r in flat:
    old=raw[r['task'],int(r['seed']),r['variant']];b=old['calibration']['reliability_bins'][int(r['bin'])-1]
    check(int(r['count'])==b['count'] and int(r['queries'])==old['risk_coverage']['queries'],'Saved populations/N')
    check(float(r['ECE'])==old['calibration']['ECE'],'Saved ECE copied, no computation')
    check(r['query_membership_sha256']==old['query_membership_sha256'],'Saved full-query membership SHA')
    for k in ['lower_inclusive','upper_inclusive_only_for_last_bin','accuracy','mean_fixed_normalized_margin_confidence','weighted_absolute_gap']:
        check((r[k]=='null' if b[k] is None else float(r[k])==b[k]),'Exact stored bin field or literal null')
review=[]
with zipfile.ZipFile(build['pptx']['path']) as z:
    check(z.testzip() is None,'PPT CRC');check(not any(n.startswith(('ppt/media/','ppt/charts/','ppt/embeddings/')) for n in z.namelist()),'No raster/workbook substitutions')
    pres=ET.fromstring(z.read('ppt/presentation.xml'));sz=pres.find('p:sldSz',NS);check(len(pres.findall('p:sldIdLst/p:sldId',NS))==11,'11 final pages')
    for page,fig in enumerate(build['figures'],1):
        for k in ['svg','preview','sourceCSV']:bound(fig[k])
        check(sz.attrib=={'cx':str(round(fig['widthMm']*36000)),'cy':str(round(fig['heightMm']*36000))},'Physical slide size')
        svg=ET.fromstring(Path(fig['svg']['path']).read_bytes());ids={e.get('id'):e for e in svg if e.get('id')}
        check(svg.get('width')=='181.9mm' and abs(float(svg.get('height').removesuffix('mm'))-fig['heightMm'])<1e-10,'SVG physical mm')
        check(list(map(float,svg.get('viewBox').split()))==[0,0,fig['widthPt'],fig['heightPt']],'SVG physical-point coords')
        check(not svg.findall('.//'+SVG+'image'),'No raster SVG');check(len(ids)==len(fig['primitives'])+1,'Unique native SVG ids')
        xml=ET.fromstring(z.read(f'ppt/slides/slide{page}.xml'));shapes=xml.findall('.//p:sp',NS)
        check(not xml.findall('.//p:pic',NS) and len(shapes)==len(fig['primitives']),'One native object per primitive')
        fonts=[]
        for sh,p in zip(shapes,fig['primitives']):
            check(sh.find('p:nvSpPr/p:cNvPr',NS).get('name')==fig['task']+'/'+p['id'],'Stable editable object name')
            xf=sh.find('p:spPr/a:xfrm',NS);o=xf.find('a:off',NS);e=xf.find('a:ext',NS);x,y,cx,cy=map(int,[o.get('x'),o.get('y'),e.get('cx'),e.get('cy')])
            check(x>=0 and y>=0 and x+cx<=int(sz.get('cx'))+1 and y+cy<=int(sz.get('cy'))+1,'Object frames within page')
            if p['tag']=='text':
                actual=''.join(n.text or '' for n in sh.findall('p:txBody/a:p/a:r/a:t',NS));check(actual==p['text']==''.join(ids[p['id']].itertext()),'PPT/SVG exact text')
                rr=sh.findall('p:txBody/a:p/a:r/a:rPr',NS);check(len(rr)==1 and int(rr[0].get('sz'))==round(p['fontSize']*100)>=800,'PPT real font at least8pt');fonts.append(int(rr[0].get('sz')))
                check(rr[0].find('a:latin',NS).get('typeface')=='Arial' and float(ids[p['id']].get('font-size'))==p['fontSize']>=8,'Arial / SVG physicalfont')
                body=sh.find('p:txBody/a:bodyPr',NS);check(body.get('wrap')=='none' and body.find('a:noAutofit',NS) is not None,'No shrink/wrap')
                near(x+(cx/2 if p['anchor']=='middle' else cx if p['anchor']=='end' else 0),p['x']*12700);near(y,(p['y']-p['fontSize']*.92)*12700)
            elif p['tag']=='line':
                near(x,min(p['x1'],p['x2'])*12700);near(y,min(p['y1'],p['y2'])*12700);near(cx,abs(p['x2']-p['x1'])*12700);near(cy,abs(p['y2']-p['y1'])*12700)
                check((xf.get('flipV','0')=='1')==((p['x2']-p['x1'])*(p['y2']-p['y1'])<0),'Line orientation');check(sh.find('p:spPr/a:prstGeom',NS).get('prst')=='line','Native line');near(int(sh.find('p:spPr/a:ln',NS).get('w')),p['width']*12700)
            else:
                near(x,(p['x']-p['r'])*12700);near(y,(p['y']-p['r'])*12700);near(cx,p['r']*25400);near(cy,p['r']*25400);check(sh.find('p:spPr/a:prstGeom',NS).get('prst')==('ellipse' if p['tag']=='circle' else 'rect'),'Native marker shape')
                ln=sh.find('p:spPr/a:ln',NS);near(int(ln.get('w')),p['width']*12700);check(ln.find('a:solidFill/a:srgbClr',NS).get('val')==p['stroke'].lstrip('#'),'Marker outline color')
                if p['fill']=='none':check(sh.find('p:spPr/a:noFill',NS) is not None,'Transparent Full square')
                else:check(sh.find('p:spPr/a:solidFill/a:srgbClr',NS).get('val')==p['fill'].lstrip('#'),'White Visual circle')
        note=ET.fromstring(z.read(f'ppt/notesSlides/notesSlide{page}.xml'));nt='\n'.join(n.text or '' for n in note.findall('.//a:t',NS)).replace('\r\n','\n')
        check(fig['caption'] in nt and Path(fig['sourceCSV']['path']).read_text(encoding='utf-8').strip() in nt,'Full caption and90 exact records in notes')
        check('Lower fixed-score ECE does not imply higher retrieval accuracy or better calibration.' in [''.join(e.itertext()) for e in svg.findall('.//'+SVG+'text')],'Visible interpretation limitation')
        check(len(fig['panels'])==3,'Three separate seed panels')
        for panel in fig['panels']:
            px,py,pw,ph=[panel['plot'][k] for k in ['x','y','width','height']];check(panel['xRange']==panel['yRange']==[0,1],'0–1 fraction axes')
            for series in panel['series']:
                r=raw[fig['task'],panel['seed'],series['variant']];bins=r['calibration']['reliability_bins'];check(series['ECE']==r['calibration']['ECE'],'Saved ECE unchanged')
                check(len(series['allBins'])==15 and len(series['points'])==sum(b['count']>0 for b in bins),'15 populations; only occupied markers')
                for i,b in enumerate(bins,1):
                    prefix=f"{fig['task']}/seed-{panel['seed']}";pid=f"{prefix}/{series['variant']}/bin-{i}/point"
                    check(''.join(ids[f"{prefix}/population/bin-{i}/{series['variant']}"].itertext())==str(b['count']),'Visible saved bin count')
                    if b['count']==0:check(pid not in ids,'No fake empty point');continue
                    p=next(p for p in series['points'] if p['bin']==i)
                    check(p['accuracy']==b['accuracy'] and p['mean_fixed_normalized_margin_confidence']==b['mean_fixed_normalized_margin_confidence'],'Saved occupied fields')
                    check(p['x']==px+b['mean_fixed_normalized_margin_confidence']*pw and p['y']==py+ph-b['accuracy']*ph,'True unjittered coordinates')
                ece_text=''.join(ids[f"{fig['task']}/seed-{panel['seed']}/{series['variant']}/ECE"].itertext());check(abs(float(ece_text.split('=')[1])-series['ECE'])<=.0000500001,'Four-decimal fraction display')
        check(not any('/segment-' in p['id'] for p in fig['primitives']),'No bin-to-bin connecting curves')
        markers=[p for p in fig['primitives'] if p['id'].endswith('/point')];check(len(markers)==fig['occupiedBins'],'Occupied point count')
        png=Path(fig['preview']['path']).read_bytes();check(png[:8]==b'\x89PNG\r\n\x1a\n','PNG');dims=struct.unpack('>II',png[16:24]);check(abs(dims[0]-fig['widthPt']*8/3)<2 and abs(dims[1]-fig['heightPt']*8/3)<2,'Final imported render dimensions')
        review.append({'page':page,'task':fig['task'],'nativeShapes':len(shapes),'textObjects':len(fonts),'minFontHundredthsPt':min(fonts),'occupiedBins':fig['occupiedBins'],'emptyBins':fig['emptyBins'],'PNGDimensions':dims,'preview':fig['preview']})
finalizer=json.loads(Path(build['receipt']['path']).read_bytes());check(finalizer['finalSha256']==build['pptx']['sha256'] and finalizer['packageIntegrity']['status']=='pass' and finalizer['presentationLayout']['exitCode']==0 and finalizer['firstPartyImport']['passed'],'Finalizer passed')
result={'schema':'producer-t5-reliability-package-review.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passed':True,'independent':False,'source':desc(__file__),'build':desc(W/'BUILD_REPORT.json'),'assertions':checks,'figures':review,'totalNativeShapes':sum(f['nativeShapes'] for f in review),'totalTexts':sum(f['textObjects'] for f in review),'occupiedPoints':140,'emptyBinsNoPoint':850,'savedECE':66,'limits':['Producer export consistency check; independent/source/root acceptance separate.','No original bin assignments/accuracy/ECE/gap/NPZ/model/scientific control recomputation.','Actual visual inspection documented separately.']}
save(W/'PRODUCER_PACKAGE_REVIEW.json',result)
print(json.dumps({'passed':True,'checks':checks,'nativeShapes':result['totalNativeShapes'],'texts':result['totalTexts'],'report':desc(W/'PRODUCER_PACKAGE_REVIEW.json')}))
