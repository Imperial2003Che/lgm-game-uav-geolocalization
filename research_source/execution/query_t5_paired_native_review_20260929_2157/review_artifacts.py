"""Independent paired-success figure audit of new CSV/SVG/native OOXML.

Only adopted small saved values; no producer import or scientific computation.
Native XML helper is text-derived from prior independent figure checks.
"""
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
import csv
import datetime
import hashlib
import json
import re
import struct
import traceback
import zipfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
WORK = HERE.parent.parent/'query_t5_paired_native_figures_20260929_2157'
OUT = WORK/'output'
ROOT_SHA = 'f55b05559de3ca536170de4ea0be79988dd7c5cf0c822be5f3572eb31a57af0a'
QUERY_SHA = '033b6eaea71b3084ca043902f6ba03b6487bf1762a9180963357103097d172cc'
CONTRACT_SHA = '43c3ce79fe7eea96cb1644c7db77f7c95abe89dfa6b9fc232968c713321f9451'
NS = {'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
COLORS = {'visual':'#0072B2','full':'#D55E00'}
FINAL_HEIGHT = 534
COUNT = 0


def check(v,m):
    global COUNT
    COUNT += 1
    if not v: raise AssertionError(m)


def near(a,b,tol=1e-8):
    check(abs(float(a)-float(b)) <= tol, f'Geometry {a} != {b}')


def bind(p):
    b=Path(p).read_bytes()
    return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def tag(e): return e.tag.rsplit('}',1)[-1]
def text(e): return ''.join(e.itertext())
def n(e,k): return float(e.get(k))


def pin(p,sha):
    b=bind(p);check(b['sha256']==sha,'Fixed pin '+str(p));return b


def title(task):
    if task.startswith('university1652_'):
        return 'University-1652: '+{'drone_to_satellite':'Drone → satellite','satellite_to_drone':'Satellite → drone','street_to_satellite':'Street → satellite'}[task.removeprefix('university1652_')]
    m=re.fullmatch(r'sues200_uav_(150|200|250|300)m_to_satellite',task)
    if m:return f'SUES-200: UAV {m[1]} m → satellite'
    m=re.fullmatch(r'sues200_satellite_to_uav_(150|200|250|300)m',task)
    check(m is not None,'Exact SUES direction/height')
    return f'SUES-200: Satellite → UAV {m[1]} m'


HEADERS=['dataset','task','seed','full_query_N','requested_coverage','realized_coverage','selected_queries_per_variant','visual_full_selected_query_overlap','visual_success_rate','full_success_rate','visual_success_percent','full_success_percent','realized_coverage_percent','full_query_membership_sha256','source_json_sha256']


def readcsv(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);check(reader.fieldnames==HEADERS,'Exact new display CSV schema');return list(reader)


def csv_values(rows,records):
    check(len(rows)==len(records),'All saved records carried in original task/seed/coverage order')
    for row,r in zip(rows,records):
        expected={k:r[k] for k in ('dataset','task','seed','requested_coverage','realized_coverage','selected_queries_per_variant','visual_full_selected_query_overlap')}
        expected.update(full_query_N=r['common_queries'],visual_success_rate=r['visual_rate'],full_success_rate=r['full_rate'],full_query_membership_sha256=r['query_membership_sha256'],source_json_sha256=QUERY_SHA)
        for k,v in expected.items():
            if k in ('dataset','task','full_query_membership_sha256','source_json_sha256'):
                check(row[k]==v,'Saved text exact '+k)
            else:check(Decimal(row[k])==Decimal(str(v)),'Saved scalar exact '+k)
        for k,source in (('visual_success_percent','visual_rate'),('full_success_percent','full_rate'),('realized_coverage_percent','realized_coverage')):
            check(abs(Decimal(row[k])-Decimal(r[source])*100)<=Decimal('1e-12'),'Only percent conversion float serialization tolerance '+k)


def fmt_percent(value):
    return format((Decimal(value)*100).quantize(Decimal('.001'),rounding=ROUND_HALF_UP),'.3f')


def check_visible_values(prefix,x0,pw,srows,texts):
    keys=set();head=prefix+'/success/heading';keys.add(head)
    check(text(texts[head])=='Success% at requested coverage','Visible value table separate nominal-coverage labels')
    near(n(texts[head],'x'),x0+pw/2);near(n(texts[head],'y'),381)
    for i,r in enumerate(srows):
        cov=format(Decimal(r['requested_coverage']).normalize(),'f');xx=x0+(i+.5)*pw/4
        hid=prefix+f'/success/cov-{cov}/heading';keys.add(hid)
        check(text(texts[hid])==str(int(Decimal(r['requested_coverage'])*100)),'Four existing nominal labels')
        near(n(texts[hid],'x'),xx);near(n(texts[hid],'y'),395)
        for variant,yy in (('visual',408),('full',421)):
            tid=prefix+f'/{variant}/success-cov-{cov}';keys.add(tid)
            check(text(texts[tid])==fmt_percent(r[variant+'_rate']),'Every stored success percentage three-decimal visible label')
            check(texts[tid].get('fill')==COLORS[variant],'Visible rate variant color');near(n(texts[tid],'x'),xx);near(n(texts[tid],'y'),yy)
    for variant,yy,label in (('visual',408,'V'),('full',421,'F')):
        tid=prefix+f'/{variant}/success-prefix';keys.add(tid)
        check(text(texts[tid])==label and texts[tid].get('fill')==COLORS[variant],'Explicit V/F value rows')
        near(n(texts[tid],'x'),x0-8);near(n(texts[tid],'y'),yy)
    return keys


def native_xml(z, ordinal, task, shapes, w, h):
    slide = ET.fromstring(z.read(f'ppt/slides/slide{ordinal}.xml'))
    for query in ('.//p:pic','.//a:blip','.//p:grpSp','.//p:graphicFrame'):
        check(not slide.findall(query,NS), 'Only flat native objects')
    native = slide.findall('p:cSld/p:spTree/p:sp',NS)
    mapped = {s.find('p:nvSpPr/p:cNvPr',NS).get('name'):s for s in native}
    check(len(mapped) == len(native) == len(shapes), 'One-to-one actual native shape count')
    check(set(mapped) == {task+'/'+k for k in shapes}, 'Exact stable selection names')
    for key, e in shapes.items():
        obj = mapped[task+'/'+key]
        xf = obj.find('p:spPr/a:xfrm',NS)
        off, ext = xf.find('a:off',NS), xf.find('a:ext',NS)
        x,y,cx,cy = map(float,(off.get('x'),off.get('y'),ext.get('cx'),ext.get('cy')))
        check(x >= -2 and y >= -2 and x+cx <= w*12700+2 and y+cy <= h*12700+2, 'Actual native bounds')
        geom = obj.find('p:spPr/a:prstGeom',NS).get('prst')
        if tag(e) == 'text':
            check(''.join(t.text or '' for t in obj.findall('.//a:t',NS)) == text(e), 'Editable exact text')
            runs = obj.findall('.//a:rPr',NS)
            check(bool(runs), 'Explicit native fonts')
            for rp in runs:
                near(float(rp.get('sz'))/100,n(e,'font-size'))
                check(int(rp.get('sz')) >= 800, 'Actual font8ptminimum')
                check(rp.find('a:latin',NS).get('typeface') == 'Arial', 'Native Arial')
                check(rp.find('a:solidFill/a:srgbClr',NS).get('val') == e.get('fill').lstrip('#'), 'Native text color')
            anchor = e.get('text-anchor')
            near(x+cx/2 if anchor == 'middle' else x+cx if anchor == 'end' else x,n(e,'x')*12700,2)
            near(y,(n(e,'y')-.92*n(e,'font-size'))*12700,2)
            check(not xf.get('rot') and not xf.get('flipV') and not xf.get('flipH'), 'Untransformed text')
        elif tag(e) == 'line':
            check(geom == 'line', 'Native line')
            x1,x2,y1,y2 = [n(e,k) for k in ('x1','x2','y1','y2')]
            for actual,wanted in zip((x,y,cx,cy),(min(x1,x2)*12700,min(y1,y2)*12700,abs(x2-x1)*12700,abs(y2-y1)*12700)):
                near(actual,wanted,2)
            check((xf.get('flipV') in ('1','true')) == ((x2-x1)*(y2-y1)<0), 'Actual line slope')
            check(not xf.get('rot') and xf.get('flipH') not in ('1','true'), 'No unexpected line transform')
            stroke = obj.find('p:spPr/a:ln',NS)
            near(stroke.get('w'),n(e,'stroke-width')*12700,2)
            check(stroke.find('a:solidFill/a:srgbClr',NS).get('val') == e.get('stroke').lstrip('#'), 'Native line color')
        else:
            if tag(e) == 'circle':
                check(geom == 'ellipse', 'Native circle')
                r = n(e,'r')
                box = (n(e,'cx')-r,n(e,'cy')-r,2*r,2*r)
            else:
                check(geom == 'rect', 'Native square')
                box = tuple(n(e,k) for k in ('x','y','width','height'))
            for actual,wanted in zip((x,y,cx,cy),box):
                near(actual,wanted*12700,2)
            if e.get('fill') == 'none':
                check(obj.find('p:spPr/a:noFill',NS) is not None and obj.find('p:spPr/a:solidFill',NS) is None, 'True transparent Full square fill')
            else:
                check(obj.find('p:spPr/a:solidFill/a:srgbClr',NS).get('val') == e.get('fill').lstrip('#'), 'White Visual circle interior')
            stroke = obj.find('p:spPr/a:ln',NS)
            near(stroke.get('w'),n(e,'stroke-width')*12700,2)
            check(stroke.find('a:solidFill/a:srgbClr',NS).get('val') == e.get('stroke').lstrip('#'), 'Actual outlined marker variant color')
    return len(native),min(int(rp.get('sz'))/100 for rp in slide.findall('.//a:rPr',NS))


def main():
    builder_sha = 'd2851e5de75e353b6aeba09ae121fd4f0215c02d0529cf39f1cd7724e1b14939'
    build_sha = '85595c5280ed37983b0fdb957ddc70bc927d2aafb5489117e8e3d683152cf0be'
    check(len(builder_sha)==len(build_sha)==64,'Fixed final source and receipt before first execution')
    bindings=[pin(HERE/'DATA_CONTRACT.json',CONTRACT_SHA),pin(WORK/'build/build_paired_v2.mjs',builder_sha),pin(WORK/'BUILD_REPORT.json',build_sha)]
    contract,build=load(HERE/'DATA_CONTRACT.json'),load(WORK/'BUILD_REPORT.json')
    check(build['mode']=='final' and build['figureCount']==11 and len(build['figures'])==11,'Fixed final11 scope')
    check(build['source']==bindings[1],'Receipt exact read source')
    for entry in [contract['inputs'][i] for i in (0,1,3,4)]:
        name=Path(entry['source']['path']).name
        copy=OUT/'source_data'/name if name.startswith('transactions_t5') else OUT/'provenance'/('UPSTREAM_'+name if name in ('README.md','REVIEW.json') else name)
        b=bind(copy);check(b['sha256']==entry['source']['sha256'] and b['bytes']==entry['source']['bytes'],'Exact adopted small source copy');bindings.append(b)
    bindings.append(pin(OUT/'provenance/ROOT_POST_ROBUSTNESS_ADOPTION.json',ROOT_SHA))
    records=contract['records'];allcsv=OUT/'source_data/PAIRED_SUCCESS_132.csv';allrows=readcsv(allcsv)
    csv_values(allrows,records);bindings.append(bind(allcsv))
    ppt=OUT/'t5_paired_native_editable_11figures.pptx'
    check(bind(ppt)==build['pptx'],'Fixed actual native deck');bindings.append(bind(ppt))
    figures=[];totals={'pages':0,'seed_panels':0,'points':0,'guide_segments':0,'table_rows':0,'visible_success_values':0,'native_shapes':0,'editable_texts':0}
    with zipfile.ZipFile(ppt) as z:
        names=z.namelist();check(z.testzip() is None,'PPT ZIP integrity')
        check({p for p in names if re.fullmatch(r'ppt/slides/slide\d+\.xml',p)}=={f'ppt/slides/slide{i}.xml' for i in range(1,12)},'Exactly eleven slides')
        check(not any(p.startswith(('ppt/media/','ppt/embeddings/','ppt/charts/')) for p in names),'No raster/workbook/chart substitutes')
        size=ET.fromstring(z.read('ppt/presentation.xml')).find('p:sldSz',NS)
        near(size.get('cx'),181.9*36000,1);near(size.get('cy'),FINAL_HEIGHT*12700,1)
        for ordinal,task in enumerate(contract['task_order'],1):
            svg=OUT/f'native_svg/t5_paired_{task}.svg';pagecsv=OUT/f'source_data/t5_{task}__paired_success.csv';png=OUT/f'previews/{ordinal:02d}_t5_paired_{task}.png'
            receipt=build['figures'][ordinal-1]
            check(receipt['task']==task and receipt['ordinal']==ordinal,'Page task/direction/height identity')
            for k,p in (('svg',svg),('sourceCSV',pagecsv),('preview',png)):
                b=bind(p);check(b==receipt[k],'Exact newly created artifact '+k);bindings.append(b)
            rr=[r for r in records if r['task']==task];rows=readcsv(pagecsv);csv_values(rows,rr)
            check(rows==[r for r in allrows if r['task']==task],'Exact twelve-row page subset')
            tree=ET.parse(svg).getroot();check(tag(tree)=='svg','Actual SVG')
            check(tree.get('width').endswith('mm') and tree.get('height').endswith('mm'),'Physical SVG dimensions')
            vx,vy,w,h=map(float,tree.get('viewBox').split());near(vx,0);near(vy,0);near(h,FINAL_HEIGHT)
            near(float(tree.get('width')[:-2]),181.9);near(float(tree.get('width')[:-2])*72/25.4/w,1);near(float(tree.get('height')[:-2])*72/25.4/h,1)
            for e in tree.iter():
                check(tag(e) in ('svg','title','desc','rect','circle','line','text'),'Native SVG primitives only')
                check(not any(k.rsplit('}',1)[-1] in ('transform','filter','clip-path','href','style') for k in e.attrib),'No hidden transform/raster/filter/clip')
            shapes={e.get('id'):e for e in tree if e.get('id') and e.get('id')!='background'}
            check(len(shapes)==len([e for e in tree if e.get('id') and e.get('id')!='background']),'Unique actual primitive IDs')
            texts={k:e for k,e in shapes.items() if tag(e)=='text'}
            fixed={'title':title(task),'subtitle':'Coverage-constrained success on the full query set','legend/visual/text':'Visual (V)','legend/full/text':'Full (F)',
                   'y-axis-label':'Selected AND Top-1 correct / full query N (%)','x-axis-label':'Realized selected coverage = k / N (%)',
                   'footnote-1':'Success uses all N queries as denominator, not accuracy among the selected k.',
                   'footnote-2':'Variants select their own queries by margin; equal k does not mean equal members.',
                   'footnote-3':'Overlap counts shared selected members, not shared correct predictions.',
                   'footnote-4':'Four saved coverage points only; connecting lines guide the eye. No added origin.',
                   'footnote-5':'Higher coverage admits more queries; rising success need not mean better ranking.',
                   'footnote-6':'Seeds/tasks stay separate. No pooled statistics, SD, CI, bootstrap or p-values shown.'}
            for key,value in fixed.items():check(text(texts[key])==value,'Exact public meaning '+key)
            for e in texts.values():
                check(e.get('font-family')=='Arial' and n(e,'font-size')>=8,'Physical Arial >=8pt')
                check(0<=n(e,'x')<=w and 0<=n(e,'y')<=h,'Visible text anchor within page')
            expected=set(fixed)|{'legend/visual/marker','legend/full/marker'};mapped=[]
            for seed in (1,2,3):
                prefix=f'{task}/seed-{seed}';srows=[r for r in rr if r['seed']==seed]
                x0,top,pw,ph=42+(seed-1)*158,99,126,128;bottom=top+ph
                head=prefix+'/heading';expected.add(head);check(text(texts[head])==f'Seed {seed}','Separate seed panel');near(n(texts[head],'x'),x0+pw/2);near(n(texts[head],'y'),86)
                for tick in (0,25,50,75,100):
                    grid,yl,xt,xl=[prefix+'/'+k+'-'+str(tick) for k in ('y-grid','y-label','x-tick','x-label')];expected.update((grid,yl,xt,xl))
                    check(text(texts[yl])==str(tick) and text(texts[xl])==str(tick),'0–100 percentage axes')
                    yy,xx=bottom-tick/100*ph,x0+tick/100*pw
                    for k,v in (('x1',x0),('x2',x0+pw),('y1',yy),('y2',yy)):near(n(shapes[grid],k),v)
                    near(n(texts[yl],'x'),x0-5);near(n(texts[yl],'y'),yy+2.7)
                    for k,v in (('x1',xx),('x2',xx),('y1',bottom),('y2',bottom+3)):near(n(shapes[xt],k),v)
                    near(n(texts[xl],'x'),xx);near(n(texts[xl],'y'),bottom+14)
                for key,coords in (('x-axis',(x0,bottom,x0+pw,bottom)),('y-axis',(x0,top,x0,bottom))):
                    eid=prefix+'/'+key;expected.add(eid)
                    for k,v in zip(('x1','y1','x2','y2'),coords):near(n(shapes[eid],k),v)
                for variant in ('visual','full'):
                    points=[]
                    for r in srows:
                        cov=format(Decimal(r['requested_coverage']).normalize(),'f');pid=prefix+f'/{variant}/point-cov-{cov}'
                        expected.add(pid);e=shapes[pid]
                        check(tag(e)==('circle' if variant=='visual' else 'rect'),'Native variant marker')
                        if variant=='visual':
                            px,py=n(e,'cx'),n(e,'cy');near(n(e,'r'),2.35);check(e.get('fill')=='#FFFFFF','Outlined white Visual circle')
                        else:
                            px,py=n(e,'x')+n(e,'width')/2,n(e,'y')+n(e,'height')/2;near(n(e,'width'),3.8);near(n(e,'height'),3.8);check(e.get('fill')=='none','Transparent Full square')
                        ex=x0+float(r['realized_coverage'])*pw;ey=bottom-float(r[variant+'_rate'])*ph
                        near(px,ex);near(py,ey);check(e.get('stroke')==COLORS[variant],'True variant color');near(n(e,'stroke-width'),.9)
                        check(x0<=px<=x0+pw and top<=py<=bottom,'All true existing points inside full axes')
                        points.append((ex,ey));mapped.append({'seed':seed,'variant':variant,'requested_coverage':r['requested_coverage'],'realized_coverage':r['realized_coverage'],'success_fraction':r[variant+'_rate'],'actual_x_pt':px,'actual_y_pt':py});totals['points']+=1
                    for i in range(1,4):
                        gid=prefix+f'/{variant}/guide-{i}-{i+1}';expected.add(gid);e=shapes[gid]
                        check(tag(e)=='line' and e.get('stroke')==COLORS[variant],'Only adjacent saved point guide')
                        for k,v in zip(('x1','y1','x2','y2'),(*points[i-1],*points[i])):near(n(e,k),v)
                        near(n(e,'stroke-width'),.9);totals['guide_segments']+=1
                nn=prefix+'/count/N';expected.add(nn);nq=srows[0]['common_queries']
                check(text(texts[nn])==f'Full query N = {nq:,}','Shared full denominator N');near(n(texts[nn],'x'),x0+pw/2);near(n(texts[nn],'y'),283)
                for key,val,xx in (('requested','Req%',x0+7),('kN','Actual k / N',x0+61),('overlap','Overlap',x0+111)):
                    eid=prefix+'/count/header/'+key;expected.add(eid);check(text(texts[eid])==val,'Explicit count headers');near(n(texts[eid],'x'),xx);near(n(texts[eid],'y'),300)
                rule=prefix+'/count/header/rule';expected.add(rule)
                for k,v in (('x1',x0-6),('x2',x0+pw+5),('y1',305),('y2',305)):near(n(shapes[rule],k),v)
                for i,r in enumerate(srows):
                    cov=format(Decimal(r['requested_coverage']).normalize(),'f');yy=316+i*14
                    for key,value,xx in (('requested',str(int(Decimal(r['requested_coverage'])*100)),x0+7),('kN',f'{r["selected_queries_per_variant"]}/{nq}',x0+61),('overlap',str(r['visual_full_selected_query_overlap']),x0+111)):
                        eid=prefix+f'/count/cov-{cov}/'+key;expected.add(eid);check(text(texts[eid])==value,'Exact stored nominal/count/overlap text');near(n(texts[eid],'x'),xx);near(n(texts[eid],'y'),yy)
                    totals['table_rows']+=1
                # Final visible saved success values are checked here after the
                # fixed producer layout/source is read, before first execution.
                expected.update(check_visible_values(prefix,x0,pw,srows,texts))
                totals['visible_success_values']+=8
                totals['seed_panels']+=1
            check(set(shapes)==expected,'No origin/unregistered point/selective rate/p/CI/extra guide')
            cnt,minfont=native_xml(z,ordinal,task,shapes,w,h)
            notes='\n'.join(t.text or '' for t in ET.fromstring(z.read(f'ppt/notesSlides/notesSlide{ordinal}.xml')).findall('.//a:t',NS))
            for phrase in (title(task),ROOT_SHA,QUERY_SHA,'common full query N','not the selected-subset accuracy','paired source row','stable query-order ties','same k is not proof','not the number jointly correct','visual guides','no additional origin','mechanically increase','seeds stay separate','No selective-accuracy difference','p-value','historical metadata-chain gaps'):
                check(phrase in notes,'Actual complete speaker note semantic '+phrase)
            for line in pagecsv.read_text(encoding='utf-8-sig').splitlines():check(line in notes,'Every exact twelve-row source CSV line in editable notes')
            pb=png.read_bytes();check(pb[:8]==b'\x89PNG\r\n\x1a\n' and pb[12:16]==b'IHDR','Real final PNG format');dims=list(struct.unpack('>II',pb[16:24]))
            figures.append({'ordinal':ordinal,'task':task,'title':title(task),'svg':bind(svg),'source_csv':bind(pagecsv),'png':bind(png),'png_dimensions':dims,'native_shapes':cnt,'editable_texts':len(texts),'min_font_pt':minfont,'mapped_points':mapped})
            totals['pages']+=1;totals['native_shapes']+=cnt;totals['editable_texts']+=len(texts)
    check(totals['pages']==11 and totals['seed_panels']==33 and totals['points']==264 and totals['guide_segments']==198 and totals['table_rows']==132 and totals['visible_success_values']==264,'Entire fixed display scope')
    report={'schema':'independent-t5-paired-native-artifact-review.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'accepted_with_stated_limits':True,'status':'passed_actual_CSV_SVG_PPT_mapping_fonts_notes','source':bind(Path(__file__)),'data_contract':bind(HERE/'DATA_CONTRACT.json'),'checks':COUNT,'totals':totals,'bindings':bindings,'figures':figures,
        'limits':['Saved small JSON/CSV values directly mapped. Raw fractions exact Decimal; percent serialization1e-12 absolute and geometry1e-8pt/XML2EMU are export-only tolerances.',
            'No query selection/success/overlap/ratio/p/CI/science or old-suite recomputation; no producer import. Native XML helper is reused source text, not re-execution of its old task.',
            'Y is selected AND correct over full N, not selected-subset accuracy. Same k can have different selected members; overlap counts selection only.',
            'Only four measured paired coverages;132 rows264 true points198 adjacent guide segments. No origin, fitted curve, interpolation result or area statistic.',
            'No pooling/SD/CI/Holm/p/significance claim. Margin is not a posterior. Higher coverage mechanically admits more queries.',
            'Upstream inherited SHA/chain/model/full-ranking/AP limits retained. Native individual objects, not groups or chart workbooks; actual previews reviewed separately.']}
    with (HERE/'ARTIFACT_REVIEW.json').open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'report':bind(HERE/'ARTIFACT_REVIEW.json'),'checks':COUNT,'totals':totals},ensure_ascii=False))


if __name__=='__main__':
    try:main()
    except Exception:
        with (HERE/('REJECTED_ARTIFACT_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S_%f')+'.json')).open('x',encoding='utf-8') as f:
            json.dump({'source':bind(Path(__file__)),'checks':COUNT,'error':traceback.format_exc()},f,indent=2)
        raise
