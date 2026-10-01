"""New T4 margin artifact review; direct adopted-table to actual SVG/PPT geometry.

Only stdlib and small/new files. No producer import/execution, old science tests,
NPZ, weights/cache/image content, means, memberships or quantiles recomputed.
"""
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
import csv, datetime, hashlib, json, re, struct, traceback, zipfile
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
WORK=HERE.parent.parent/'query_t4_margin_native_figures_20260929_1952'
OUT=WORK/'output'
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
COLORS={'visual':'#0072B2','full':'#D55E00'}
ROOT_SHA='f55b05559de3ca536170de4ea0be79988dd7c5cf0c822be5f3572eb31a57af0a'
T4_SHA='42090c4ffdafedbfffd8ed2439e1e59756f0876e2c7ae612a87031a574b28cc8'
CSV_SHA='bc1725e7d5a1ce298f2de579240d65ced823b57d0d2af8bcb077a9d697d66530'
METRICS=['r_at_1','official_trapezoid_mAP','MRR']
HEADERS=['dataset','task','seed','factor','level','quartile','queries','performance_claim_eligible',
         'minimum_queries_for_claim','membership_sha256','cutpoint_25','cutpoint_50','cutpoint_75']
for metric in METRICS:
    HEADERS += [f'visual_{metric}',f'visual_{metric}_x100',f'full_{metric}',f'full_{metric}_x100',f'full_minus_visual_{metric}']
HEADERS += ['source_json_sha256']
COUNT=0

def check(v,m):
    global COUNT
    COUNT+=1
    if not v:raise AssertionError(m)
def near(a,b,t=1e-8):check(abs(float(a)-float(b))<=t,f'Geometry {a}!={b}')
def bind(p):
    b=Path(p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def tag(e):return e.tag.rsplit('}',1)[-1]
def text(e):return ''.join(e.itertext())
def n(e,k):return float(e.get(k))
def exactpin(p,sha):
    d=bind(p);check(d['sha256']==sha,'Exact pin '+str(p));return d
def readcsv(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:
        r=csv.DictReader(f);check(r.fieldnames==HEADERS,'Direct table schema');return list(r)
def title(task):
    if task.startswith('university1652_'):
        return 'University-1652: '+{'drone_to_satellite':'Drone → satellite','satellite_to_drone':'Satellite → drone','street_to_satellite':'Street → satellite'}[task.removeprefix('university1652_')]
    match=re.fullmatch(r'sues200_uav_(150|200|250|300)m_to_satellite',task)
    if match:return f'SUES-200: UAV {match[1]} m → satellite'
    match=re.fullmatch(r'sues200_satellite_to_uav_(150|200|250|300)m',task)
    check(match is not None,'SUES task identity');return f'SUES-200: Satellite → UAV {match[1]} m'

def check_csv(rows,records,original):
    check(len(rows)==len(records),'Exact derived table length')
    strings={'dataset','task','factor','level','membership_sha256','source_json_sha256'}
    for row,record in zip(rows,records):
        wanted={k:record[k] for k in ('dataset','task','seed','factor','level','queries','performance_claim_eligible','minimum_queries_for_claim','membership_sha256')}
        wanted['quartile']=record['quartile_index'];wanted['source_json_sha256']=T4_SHA
        for i,key in enumerate(('cutpoint_25','cutpoint_50','cutpoint_75')):wanted[key]=record['quartile_cutpoints'][i]
        for metric in METRICS:
            for variant in ('visual','full'):
                val=next(m for m in record['metrics'] if m['metric']==metric and m['variant']==variant)
                wanted[variant+'_'+metric]=val['fraction'];wanted[variant+'_'+metric+'_x100']=val['display_x100']
            wanted['full_minus_visual_'+metric]=original[(record['task'],record['seed'],record['level'])]['summary']['metrics'][metric]['full_minus_visual']
        check(set(wanted)==set(row),'Exact CSV columns')
        for key,value in wanted.items():
            if key in strings:check(row[key]==value,'CSV exact string '+key)
            elif type(value) is bool:check(row[key]==str(value).lower(),'CSV exact boolean')
            elif key.endswith('_x100'):
                # JS binary64 multiplication serialized into CSV: display-only
                # absolute tolerance2e-14 percentage/scale units, not science means.
                check(abs(Decimal(row[key])-Decimal(str(value)))<=Decimal('2e-14'),'CSV ×100 display roundoff '+key)
            else:check(Decimal(row[key])==Decimal(str(value)),'CSV exact saved numeric '+key)

def native_xml(archive,ordinal,task,shapes,width,height):
    slide=ET.fromstring(archive.read(f'ppt/slides/slide{ordinal}.xml'))
    for query in ('.//p:pic','.//a:blip','.//p:grpSp','.//p:graphicFrame'):
        check(not slide.findall(query,NS),'Actual flat native objects only')
    native=slide.findall('p:cSld/p:spTree/p:sp',NS)
    mapped={s.find('p:nvSpPr/p:cNvPr',NS).get('name'):s for s in native}
    check(len(mapped)==len(native)==len(shapes),'One-to-one native shape count')
    check(set(mapped)=={task+'/'+k for k in shapes},'Exact stable native names')
    for key,e in shapes.items():
        obj=mapped[task+'/'+key];xf=obj.find('p:spPr/a:xfrm',NS);off=xf.find('a:off',NS);ext=xf.find('a:ext',NS)
        x,y,cx,cy=map(float,(off.get('x'),off.get('y'),ext.get('cx'),ext.get('cy')))
        check(x>=-2 and y>=-2 and x+cx<=width*12700+2 and y+cy<=height*12700+2,'Actual native object page bounds')
        geom=obj.find('p:spPr/a:prstGeom',NS).get('prst')
        if tag(e)=='text':
            check(''.join(t.text or '' for t in obj.findall('.//a:t',NS))==text(e),'Editable exact text')
            runs=obj.findall('.//a:rPr',NS);check(bool(runs),'Explicit font settings')
            for rp in runs:
                near(float(rp.get('sz'))/100,n(e,'font-size'));check(int(rp.get('sz'))>=800,'Actual font >=8pt')
                check(rp.find('a:latin',NS).get('typeface')=='Arial','Actual Arial')
                check(rp.find('a:solidFill/a:srgbClr',NS).get('val')==e.get('fill').lstrip('#'),'Actual text color/variant link')
            anchor=e.get('text-anchor');near(x+cx/2 if anchor=='middle' else x+cx if anchor=='end' else x,n(e,'x')*12700,2)
            near(y,(n(e,'y')-.92*n(e,'font-size'))*12700,2)
            check(not xf.get('rot') and not xf.get('flipV') and not xf.get('flipH'),'Text no hidden transforms')
        elif tag(e)=='line':
            check(geom=='line','Native line');x1,x2,y1,y2=[n(e,k) for k in ('x1','x2','y1','y2')]
            for actual,wanted in zip((x,y,cx,cy),(min(x1,x2)*12700,min(y1,y2)*12700,abs(x2-x1)*12700,abs(y2-y1)*12700)):near(actual,wanted,2)
            check((xf.get('flipV') in ('1','true'))==((x2-x1)*(y2-y1)<0),'Actual segment slope orientation')
            check(not xf.get('rot') and xf.get('flipH') not in ('1','true'),'No unexpected line transform')
            stroke=obj.find('p:spPr/a:ln',NS);near(stroke.get('w'),n(e,'stroke-width')*12700,2)
            check(stroke.find('a:solidFill/a:srgbClr',NS).get('val')==e.get('stroke').lstrip('#'),'Native stroke color')
        else:
            if tag(e)=='circle':
                check(geom=='ellipse','Native circle');r=n(e,'r');box=(n(e,'cx')-r,n(e,'cy')-r,2*r,2*r)
            else:check(geom=='rect','Native square');box=tuple(n(e,k) for k in ('x','y','width','height'))
            for actual,wanted in zip((x,y,cx,cy),box):near(actual,wanted*12700,2)
            check(obj.find('p:spPr/a:solidFill/a:srgbClr',NS).get('val')==e.get('fill').lstrip('#'),'Native marker color')
    return len(native),min(int(rp.get('sz'))/100 for rp in slide.findall('.//a:rPr',NS))

def main():
    bindings=[exactpin(HERE/'DATA_CONTRACT.json','bf1d5a1c96e59924ab3169dadd6857794b757175d4ebf0c345892807268dc43e'),
              exactpin(WORK/'build/build_t4.mjs','635d4449a2ae2270a6218fe270cb7ac21a605e1f9a3fd8b6a2182812ac0a4eb3')]
    contract=load(HERE/'DATA_CONTRACT.json');build=load(WORK/'BUILD_REPORT.json');bindings.append(exactpin(WORK/'BUILD_REPORT.json','0a3e4c2e55ce867e2ea35ca5221e8902a0bc0128e8d217dcc1fd9a3d58ff86a5'))
    check(build['mode']=='final' and build['figureCount']==11 and len(build['figures'])==11,'Final11 not sample')
    check(build['source']==bindings[1],'Build bound to actual completely read source')
    for entry in contract['inputs'][:5]:
        name=Path(entry['source']['path']).name
        copy=OUT/'source_data'/name if name.startswith('transactions_t4') else OUT/'provenance'/('UPSTREAM_'+name if name in ('README.md','REVIEW.json') else name)
        actual=bind(copy);check(actual['sha256']==entry['source']['sha256'] and actual['bytes']==entry['source']['bytes'],'Exact adopted smallinput copy');bindings.append(actual)
    bindings.append(exactpin(OUT/'provenance/ROOT_POST_ROBUSTNESS_ADOPTION.json',ROOT_SHA))
    original_json=json.loads((HERE/'raw/transactions_t4_strata.json').read_text(encoding='utf-8-sig'),parse_float=Decimal)
    original={(r['task'],r['seed'],r['level']):r for r in original_json['rows'] if r['factor']=='visual_margin_quartile'}
    records=contract['records'];allcsv=OUT/'source_data/MARGIN_STRATA_132.csv';allrows=readcsv(allcsv)
    check_csv(allrows,records,original);bindings.append(bind(allcsv))
    ppt=OUT/'t4_margin_native_editable_11figures.pptx';actual=bind(ppt);check(actual==build['pptx'],'Final deck actual binding');bindings.append(actual)
    totals={'pages':0,'seed_metric_panels':0,'points':0,'guide_segments':0,'numeric_labels':0,'stratum_N_labels':0,'ineligible_daggers':0,'native_shapes':0,'editable_texts':0}
    figures=[]
    with zipfile.ZipFile(ppt) as z:
        names=z.namelist();check(z.testzip() is None,'PPT ZIP CRC')
        check({s for s in names if re.fullmatch(r'ppt/slides/slide\d+\.xml',s)}=={f'ppt/slides/slide{i}.xml' for i in range(1,12)},'All11 slides')
        check(not any(s.startswith(('ppt/media/','ppt/charts/','ppt/embeddings/')) for s in names),'No raster/chart/embeddedworkbook')
        size=ET.fromstring(z.read('ppt/presentation.xml')).find('p:sldSz',NS);near(size.get('cx'),181.9*36000,1);near(size.get('cy'),607*12700,1)
        for ordinal,task in enumerate(contract['task_order'],1):
            svg=OUT/f'native_svg/t4_{task}.svg';csvpath=OUT/f'source_data/t4_{task}__margin_strata.csv';png=OUT/f'previews/{ordinal:02d}_t4_{task}.png'
            receipt=build['figures'][ordinal-1];check(receipt['task']==task and receipt['ordinal']==ordinal,'Page/task mapping')
            for key,path in (('svg',svg),('sourceCSV',csvpath),('preview',png)):
                b=bind(path);check(b==receipt[key],'Actual newartifact '+key);bindings.append(b)
            rr=[r for r in records if r['task']==task];page=readcsv(csvpath);check_csv(page,rr,original)
            check(page==[r for r in allrows if r['task']==task],'Exact page subset')
            indexed={(r['seed'],r['quartile_index']):r for r in rr}
            tree=ET.parse(svg).getroot();check(tag(tree)=='svg','Actual SVGroot')
            check(tree.get('width').endswith('mm') and tree.get('height').endswith('mm'),'Physical dimensions')
            vx,vy,w,h=map(float,tree.get('viewBox').split());near(vx,0);near(vy,0);near(h,607)
            sx=float(tree.get('width')[:-2])*72/25.4/w;sy=float(tree.get('height')[:-2])*72/25.4/h;near(sx,1);near(sy,1)
            for e in tree.iter():
                check(tag(e) in ('svg','title','desc','rect','circle','line','text'),'Native SVG only')
                check(not any(k.rsplit('}',1)[-1] in ('transform','filter','clip-path','href','style') for k in e.attrib),'No hidden geometry/raster')
            shapes={e.get('id'):e for e in tree if e.get('id') and e.get('id')!='background'}
            check(len(shapes)==len([e for e in tree if e.get('id') and e.get('id')!='background']),'Unique SVG IDs')
            texts={k:e for k,e in shapes.items() if tag(e)=='text'}
            fixed={'title':title(task),'subtitle':'Performance within shared Visual-margin quartiles','legend/visual/text':'Visual (V)','legend/full/text':'Full (F)',
                   'legend/values':'Values below plots: V then F, to three decimals',
                   'footnote-1':'Q1–Q4: low to high Visual margin, defined separately for each task and seed.',
                   'footnote-2':'Linear quartile cutpoints; boundary ties enter the lower interval. Members are shared.',
                   'footnote-3':'† N < 100: performance_claim_eligible=false; descriptive only. N is per quartile.',
                   'footnote-4':'Eligible strata imply no significance. No pooling, SD, CI, bootstrap or p-values shown.',
                   'footnote-5':'Segments guide categorical groups, not continuous margins. Margin is not a posterior.'}
            for k,v in fixed.items():check(text(texts[k])==v,'Actual visible label/limit '+k)
            expected=set(fixed)|{'legend/visual/marker','legend/full/marker'}
            for e in texts.values():
                check(n(e,'font-size')*sx>=8-1e-10 and e.get('font-family')=='Arial','Physical text >=8ptArial')
                check(0<=n(e,'x')<=w and 0<n(e,'y')<h,'Text anchor bounds')
            for seed in (1,2,3):
                for k,v in ((f'seed-{seed}/heading',f'Seed {seed}'),(f'seed-{seed}/N-label','N')):
                    expected.add(k);check(text(texts[k])==v,'Seed/N header')
                for q in (1,2,3,4):
                    r=indexed[(seed,q)];k=f'seed-{seed}/quartile-{q}'
                    expected.update((k+'/N-heading',k+'/N-value'))
                    check(text(texts[k+'/N-heading'])==f'Q{q}','Actual quartet N identity')
                    check(text(texts[k+'/N-value'])==str(r['queries'])+('' if r['performance_claim_eligible'] else '†'),'Exact N+eligibility dagger')
                    totals['stratum_N_labels']+=1;totals['ineligible_daggers']+=not r['performance_claim_eligible']
            cell_rows=[]
            for mi,(metric,heading) in enumerate(zip(METRICS,('R@1 (%)','Official trapezoidal mAP (%)','MRR × 100 (scaled MRR)'))):
                expected.add(metric+'/row-heading');check(text(texts[metric+'/row-heading'])==heading,'Metric definition and unit')
                for seed in (1,2,3):
                    pre=f'{task}/seed-{seed}/{metric}';xa=shapes[pre+'/x-axis'];ya=shapes[pre+'/y-axis'];expected.update((pre+'/x-axis',pre+'/y-axis'))
                    x0,x1,top,bottom=n(xa,'x1'),n(xa,'x2'),n(ya,'y1'),n(ya,'y2')
                    near(x0,42+(seed-1)*158);near(x1-x0,126);near(top,128+mi*135);near(bottom-top,77)
                    near(n(xa,'y1'),bottom);near(n(xa,'y2'),bottom);near(n(ya,'x1'),x0);near(n(ya,'x2'),x0)
                    for value in (0,25,50,75,100):
                        expected.update((pre+f'/y-grid-{value}',pre+f'/y-label-{value}'))
                        grid=shapes[pre+f'/y-grid-{value}'];label=texts[pre+f'/y-label-{value}'];yy=bottom-value/100*(bottom-top)
                        check(text(label)==str(value),'Honest full0–100ticks');near(n(grid,'x1'),x0);near(n(grid,'x2'),x1);near(n(grid,'y1'),yy);near(n(grid,'y2'),yy)
                        near(n(label,'x'),x0-5);near(n(label,'y'),yy+2.7)
                    for q in (1,2,3,4):
                        xt=pre+f'/x-tick-Q{q}';xl=pre+f'/x-label-Q{q}';expected.update((xt,xl));xx=x0+(q-.5)*(x1-x0)/4
                        check(text(texts[xl])==f'Q{q}','Categorical low-high labels');near(n(texts[xl],'x'),xx);near(n(texts[xl],'y'),bottom+12)
                        near(n(shapes[xt],'x1'),xx);near(n(shapes[xt],'x2'),xx);near(n(shapes[xt],'y1'),bottom);near(n(shapes[xt],'y2'),bottom+3)
                        near(n(texts[f'seed-{seed}/quartile-{q}/N-value'],'x'),xx)
                    for variant in ('visual','full'):
                        pts=[]
                        for q in (1,2,3,4):
                            r=indexed[(seed,q)];m=next(m for m in r['metrics'] if m['variant']==variant and m['metric']==metric)
                            point=pre+f'/{variant}/point-Q{q}';value=pre+f'/{variant}/value-Q{q}';expected.update((point,value));mark=shapes[point]
                            check(tag(mark)==('circle' if variant=='visual' else 'rect'),'Variant marker')
                            if variant=='visual':px,py=n(mark,'cx'),n(mark,'cy');near(n(mark,'r'),1.85)
                            else:px,py=n(mark,'x')+n(mark,'width')/2,n(mark,'y')+n(mark,'height')/2;near(n(mark,'width'),3.7);near(n(mark,'height'),3.7)
                            near(px,x0+(q-.5)*(x1-x0)/4);near(py,bottom-float(m['fraction'])*(bottom-top));check(mark.get('fill')==COLORS[variant],'Marker color')
                            check(top-1e-8<=py<=bottom+1e-8,'Source value not clipped')
                            displayed=format(Decimal(m['display_x100']).quantize(Decimal('.001'),rounding=ROUND_HALF_UP),'.3f')
                            check(text(texts[value])==displayed,'Actual saved ×100 numeric label');near(n(texts[value],'x'),px);near(n(texts[value],'y'),bottom+(25 if variant=='visual' else 36))
                            check(texts[value].get('fill')==COLORS[variant],'Numeric row color')
                            pts.append((px,py));cell_rows.append({'seed':seed,'metric':metric,'variant':variant,'quartile':q,'fraction':m['fraction'],'display_x100':displayed,'actual_x':px,'actual_y':py})
                            totals['points']+=1;totals['numeric_labels']+=1
                        for q in (1,2,3):
                            key=pre+f'/{variant}/segment-Q{q}-Q{q+1}';expected.add(key);line=shapes[key]
                            check(tag(line)=='line' and line.get('stroke')==COLORS[variant],'Categoricalguide line')
                            for field,val in zip(('x1','y1','x2','y2'),pts[q-1]+pts[q]):near(n(line,field),val)
                            near(n(line,'stroke-width'),.9);totals['guide_segments']+=1
                        key=pre+f'/{variant}/value-prefix';expected.add(key);check(text(texts[key])==('V' if variant=='visual' else 'F'),'Separate V/F visible numericrow')
                    totals['seed_metric_panels']+=1
            check(set(shapes)==expected,'Exact expected native identities; no CI/band/anonymousextra')
            native_count,minfont=native_xml(z,ordinal,task,shapes,w,h)
            note=ET.fromstring(z.read(f'ppt/notesSlides/notesSlide{ordinal}.xml'));notes='\n'.join(t.text or '' for t in note.findall('.//a:t',NS))
            for phrase in (title(task),ROOT_SHA,T4_SHA,CSV_SHA,'MRR×100 is scaled MRR, not accuracy percent','Full queries were aligned to Visual',
                           'same Visual-defined membership mask','Exactly48 of the132 selected strata are ineligible','not causal/mechanistic attribution',
                           'other330 entropy/semantic strata','Upstream bootstrap intervals were not independently resampled','No new means, quantiles, memberships'):
                check(phrase in notes,'Actual notes semantics/source '+phrase)
            for line in csvpath.read_text(encoding='utf-8-sig').splitlines():check(line in notes,'Exact pageCSV in actual notes')
            pb=png.read_bytes();check(pb[:8]==b'\x89PNG\r\n\x1a\n' and pb[12:16]==b'IHDR','PNG signature');dims=list(struct.unpack('>II',pb[16:24]))
            figures.append({'ordinal':ordinal,'task':task,'title':title(task),'svg':bind(svg),'source_csv':bind(csvpath),'png':bind(png),'png_dimensions':dims,
                            'native_shapes':native_count,'editable_texts':len(texts),'min_font_pt':minfont,'mapped_values':cell_rows,'ineligible_strata':sum(not r['performance_claim_eligible'] for r in rr)})
            totals['pages']+=1;totals['native_shapes']+=native_count;totals['editable_texts']+=len(texts)
    check(totals['pages']==11 and totals['seed_metric_panels']==99 and totals['points']==totals['numeric_labels']==792 and totals['guide_segments']==594,'All plotted scope')
    check(totals['stratum_N_labels']==132 and totals['ineligible_daggers']==48,'All exact N and48visible ineligible flags')
    result={'schema':'independent-t4-margin-native-artifact-review.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'passed_actual_SVG_PPT_CSV_geometry_numeric_labels_units_fonts','accepted_with_stated_limits':True,
        'source':bind(Path(__file__)),'data_contract':bind(HERE/'DATA_CONTRACT.json'),'checks':COUNT,'totals':totals,'bindings':bindings,'figures':figures,
        'limits':['Only new artifacts checked; no producer/checker imported/executed or oldT4/66NPZ/means/quantiles/membership/bootstrap scientific suite repeated.',
                  'Source fractions/N/eligibility are adopted small values. ×100 CSV serialization allows2e-14 absolute display-unit roundoff; geometry1e-8pt/XML2EMU. No new scientific comparison tolerance.',
                  'Same Visual-defined member stratum, anchored on Visual margin; not causal/calibrated/mechanistic or significance evidence.84 eligible means countgateonly;48N20 flagged descriptiveonly.',
                  'No pooling/SD/CI/p-values;330otherstrata not plotted. Storedmodel/ranking/AP/cache/SHAchain limitations inherited.',
                  'Nativeflat shapes/text, not Excelcharts; PowerPoint not opened. Actual visualinspection is recorded separately.']}
    with (HERE/'ARTIFACT_REVIEW.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'report':bind(HERE/'ARTIFACT_REVIEW.json'),'checks':COUNT,'totals':totals},ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except Exception:
        with (HERE/('REJECTED_ARTIFACT_ATTEMPT_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S_%f')+'.json')).open('x',encoding='utf-8') as f:
            json.dump({'source':bind(Path(__file__)),'checks':COUNT,'error':traceback.format_exc()},f,indent=2)
        raise
