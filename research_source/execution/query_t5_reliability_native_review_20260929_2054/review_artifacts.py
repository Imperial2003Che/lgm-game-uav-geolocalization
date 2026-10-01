"""New T5 reliability SVG/PPT/CSV audit from independently bound small values.

No producer imports or scientific suites. Native OOXML checks derive from prior
independent flat-object checks, adapted for outlined/transparent markers.
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
WORK = HERE.parent.parent/'query_t5_reliability_native_figures_20260929_2054'
OUT = WORK/'output'
ROOT_SHA = 'f55b05559de3ca536170de4ea0be79988dd7c5cf0c822be5f3572eb31a57af0a'
QUERY_SHA = '033b6eaea71b3084ca043902f6ba03b6487bf1762a9180963357103097d172cc'
CONTRACT_SHA = '33af44ed731e9a951d0514a11a4cf51c86f1694deadb20888cf5628ad61874c4'
NS = {'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
COLORS = {'visual':'#0072B2','full':'#D55E00'}
HEADERS = ['dataset','task','seed','variant','queries','bin','count','lower_inclusive','upper_inclusive_only_for_last_bin','accuracy','mean_fixed_normalized_margin_confidence','weighted_absolute_gap','ECE','query_membership_sha256','source_json_sha256']
COUNT = 0


def check(v, m):
    global COUNT
    COUNT += 1
    if not v:
        raise AssertionError(m)


def near(a, b, tol=1e-8):
    check(abs(float(a)-float(b)) <= tol, f'Geometry {a} != {b}')


def bind(p):
    b = Path(p).read_bytes()
    return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def tag(e):
    return e.tag.rsplit('}',1)[-1]


def text(e):
    return ''.join(e.itertext())


def n(e, k):
    return float(e.get(k))


def pin(p, sha):
    d = bind(p)
    check(d['sha256'] == sha, 'Exact pin '+str(p))
    return d


def readcsv(p):
    with Path(p).open(encoding='utf-8-sig', newline='') as f:
        r = csv.DictReader(f)
        check(r.fieldnames == HEADERS, 'Actual derived CSV schema')
        return list(r)


def title(task):
    if task.startswith('university1652_'):
        return 'University-1652: '+{'drone_to_satellite':'Drone → satellite','satellite_to_drone':'Satellite → drone','street_to_satellite':'Street → satellite'}[task.removeprefix('university1652_')]
    m = re.fullmatch(r'sues200_uav_(150|200|250|300)m_to_satellite', task)
    if m:
        return f'SUES-200: UAV {m[1]} m → satellite'
    m = re.fullmatch(r'sues200_satellite_to_uav_(150|200|250|300)m', task)
    check(m is not None, 'Exact SUES direction/height')
    return f'SUES-200: Satellite → UAV {m[1]} m'


def csv_values(rows, records):
    flat = [b for r in records for b in r['bins']]
    check(len(rows) == len(flat), 'All saved bin records carried')
    strings = {'dataset','task','variant','query_membership_sha256','source_json_sha256'}
    for actual, b in zip(rows, flat):
        expected = {k:b[k] for k in ('dataset','task','seed','variant','queries','bin','count','lower_inclusive','accuracy','mean_fixed_normalized_margin_confidence','weighted_absolute_gap','query_membership_sha256')}
        expected.update(upper_inclusive_only_for_last_bin=b['upper_bound'], ECE=b['ECE_fraction'], source_json_sha256=QUERY_SHA)
        check(set(actual) == set(expected), 'Exact carried CSV fields')
        for k, v in expected.items():
            if v is None:
                check(actual[k] == 'null', 'Empty-bin null retained, not0')
            elif k in strings:
                check(actual[k] == v, 'CSV exact saved text '+k)
            else:
                check(Decimal(actual[k]) == Decimal(str(v)), 'CSV exact saved numeric '+k)


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
    # Fixed final pins are set after reading the actual v2 receipt, before this
    # new checker is first executed. Placeholder refusal prevents accidental use.
    builder_sha = '4dfcb86b379719e564d224682cb23b23e36231c4f51ce8e5d2590db1ab79d779'
    build_sha = 'ad72763e388795c521dba217e3e1b19935aeaca509b1f0cb832c6c2e4ac8176c'
    check(len(builder_sha) == len(build_sha) == 64, 'Final source/receipt fixed before execution')
    bindings = [pin(HERE/'DATA_CONTRACT.json',CONTRACT_SHA),pin(WORK/'build/build_reliability_v2.mjs',builder_sha),pin(WORK/'BUILD_REPORT.json',build_sha)]
    contract, build = load(HERE/'DATA_CONTRACT.json'), load(WORK/'BUILD_REPORT.json')
    check(build['mode'] == 'final' and build['figureCount'] == 11 and len(build['figures']) == 11, 'Final full11')
    check(build['source'] == bindings[1], 'Receipt refers to fixed read builder')
    for entry in contract['inputs'][:4]:
        name = Path(entry['source']['path']).name
        copy = OUT/'source_data'/name if name.startswith('transactions_t5') else OUT/'provenance'/('UPSTREAM_'+name if name in ('README.md','REVIEW.json') else name)
        b = bind(copy)
        check(b['sha256'] == entry['source']['sha256'] and b['bytes'] == entry['source']['bytes'], 'Exact adopted small-source copies')
        bindings.append(b)
    bindings.append(pin(OUT/'provenance/ROOT_POST_ROBUSTNESS_ADOPTION.json',ROOT_SHA))
    records = contract['records']
    allcsv = OUT/'source_data/RELIABILITY_BINS_990.csv'
    allrows = readcsv(allcsv)
    csv_values(allrows,records)
    bindings.append(bind(allcsv))
    ppt = OUT/'t5_reliability_native_editable_11figures.pptx'
    check(bind(ppt) == build['pptx'], 'Final actual PPT byte pin')
    bindings.append(bind(ppt))
    totals = {'pages':0,'seed_panels':0,'occupied_points':0,'empty_bins_not_plotted':0,'population_values':0,'saved_ECE_labels':0,'numeric_equality_references':0,'native_shapes':0,'editable_texts':0}
    figures = []
    with zipfile.ZipFile(ppt) as z:
        names = z.namelist()
        check(z.testzip() is None, 'PPT ZIP integrity')
        check({n for n in names if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)} == {f'ppt/slides/slide{i}.xml' for i in range(1,12)}, 'Exactly11 slides')
        check(not any(n.startswith(('ppt/media/','ppt/embeddings/','ppt/charts/')) for n in names), 'No image/workbook/chart substitutes')
        size = ET.fromstring(z.read('ppt/presentation.xml')).find('p:sldSz',NS)
        near(size.get('cx'),181.9*36000,1)
        near(size.get('cy'),604*12700,1)
        for ordinal, task in enumerate(contract['task_order'],1):
            svg = OUT/f'native_svg/t5_reliability_{task}.svg'
            csvpath = OUT/f'source_data/t5_{task}__reliability_bins.csv'
            png = OUT/f'previews/{ordinal:02d}_t5_reliability_{task}.png'
            receipt = build['figures'][ordinal-1]
            check(receipt['task'] == task and receipt['ordinal'] == ordinal, 'Actual page/direction/height mapping')
            for key,path in (('svg',svg),('sourceCSV',csvpath),('preview',png)):
                b = bind(path)
                check(b == receipt[key], 'Actual artifact receipt '+key)
                bindings.append(b)
            rr = [r for r in records if r['task'] == task]
            page = readcsv(csvpath)
            csv_values(page,rr)
            check(page == [r for r in allrows if r['task'] == task], 'Exact90-bin page subset')
            keyed = {(r['seed'],r['variant']):r for r in rr}
            tree = ET.parse(svg).getroot()
            check(tag(tree) == 'svg', 'Actual SVG')
            check(tree.get('width').endswith('mm') and tree.get('height').endswith('mm'), 'Physical units')
            vx,vy,w,h = map(float,tree.get('viewBox').split())
            near(vx,0);near(vy,0);near(h,604)
            near(float(tree.get('width')[:-2]),181.9)
            near(float(tree.get('width')[:-2])*72/25.4/w,1)
            near(float(tree.get('height')[:-2])*72/25.4/h,1)
            for e in tree.iter():
                check(tag(e) in ('svg','title','desc','rect','circle','line','text'), 'Native vector only')
                check(not any(k.rsplit('}',1)[-1] in ('transform','filter','clip-path','href','style') for k in e.attrib), 'No hidden raster/transform/clip')
            shapes = {e.get('id'):e for e in tree if e.get('id') and e.get('id') != 'background'}
            check(len(shapes) == len([e for e in tree if e.get('id') and e.get('id') != 'background']), 'Unique IDs')
            texts = {k:e for k,e in shapes.items() if tag(e) == 'text'}
            fixed = {'title':title(task),'subtitle':'Fixed margin-score reliability diagnostic',
                'legend/visual/text':'Visual (V)','legend/full/text':'Full (F)',
                'legend/equality/text':'y = x: numerical equality reference',
                'y-axis-label':'Empirical R@1 (fraction)','x-axis-label':'Mean fixed margin score (fraction)',
                'footnote-1':'Score = clip((cosine Top-1 − Top-2 margin) / 2, 0, 1); fixed, not a posterior.',
                'footnote-2':'Each variant assigns queries to its own 15 equal-width bins; members can differ.',
                'footnote-3':'Only occupied bins have markers. N = 0 retains null mean/accuracy, not zero.',
                'footnote-4':'Gray y = x shows numerical equality only. No fitted calibration or connecting curve.',
                'footnote-5':'Stored ECE fractions rounded to four decimals. No seed/task pooling, SD, CI or p-values.'}
            for key,value in fixed.items():
                check(text(texts[key]) == value, 'Public exact semantics '+key)
            check('footnote-6' in texts and text(texts['footnote-6']) == 'Lower fixed-score ECE does not imply higher retrieval accuracy or better calibration.', 'Visible lower-ECE interpretation limit')
            for e in texts.values():
                check(e.get('font-family') == 'Arial' and n(e,'font-size') >= 8, 'Physical Arial >=8pt')
                check(0 <= n(e,'x') <= w and 0 <= n(e,'y') <= h, 'SVG text anchor page bounds')
            expected = set(fixed)|{'footnote-6','legend/visual/marker','legend/full/marker','legend/equality/line'}
            mapped_points = []
            for seed in (1,2,3):
                pre = f'{task}/seed-{seed}'
                x0, top, pw, ph = 42+(seed-1)*158,95,126,116
                bottom = top+ph
                seedid = pre+'/seed-heading'
                expected.add(seedid)
                check(text(texts[seedid]) == f'Seed {seed}', 'Separate seed heading')
                near(n(texts[seedid],'x'),x0+pw/2);near(n(texts[seedid],'y'),82)
                for value in (0,.25,.5,.75,1):
                    suffix = str(value)
                    grid,yl,xt,xl = [pre+'/'+k+'-'+suffix for k in ('y-grid','y-label','x-tick','x-label')]
                    expected.update((grid,yl,xt,xl))
                    check(text(texts[yl]) == suffix and text(texts[xl]) == suffix, 'Full0–1 fraction ticks')
                    yy,xx = bottom-value*ph,x0+value*pw
                    for k,v in (('x1',x0),('x2',x0+pw),('y1',yy),('y2',yy)):
                        near(n(shapes[grid],k),v)
                    near(n(texts[yl],'x'),x0-5);near(n(texts[yl],'y'),yy+2.7)
                    near(n(shapes[xt],'x1'),xx);near(n(shapes[xt],'x2'),xx)
                    near(n(shapes[xt],'y1'),bottom);near(n(shapes[xt],'y2'),bottom+3)
                    near(n(texts[xl],'x'),xx);near(n(texts[xl],'y'),bottom+14)
                for key,coords in (('x-axis',(x0,bottom,x0+pw,bottom)),('y-axis',(x0,top,x0,bottom)),('reference-equality',(x0,bottom,x0+pw,top))):
                    eid = pre+'/'+key
                    expected.add(eid)
                    for k,v in zip(('x1','y1','x2','y2'),coords):near(n(shapes[eid],k),v)
                    if key == 'reference-equality':check(shapes[eid].get('stroke') == '#ABB3BB', 'Gray numerical reference only')
                totals['numeric_equality_references'] += 1
                for variant in ('visual','full'):
                    rec = keyed[(seed,variant)]
                    eid = pre+'/'+variant+'/ECE'
                    expected.add(eid)
                    ece_text = format(Decimal(rec['ECE_fraction']).quantize(Decimal('.0001'),rounding=ROUND_HALF_UP),'.4f')
                    check(text(texts[eid]) == ('V' if variant == 'visual' else 'F')+' ECE = '+ece_text, 'Saved ECE fraction rounded only')
                    near(n(texts[eid],'x'),x0+pw/2);near(n(texts[eid],'y'),265+(13 if variant == 'full' else 0))
                    check(texts[eid].get('fill') == COLORS[variant], 'ECE variant color')
                    totals['saved_ECE_labels'] += 1
                    for b in rec['bins']:
                        pointid = pre+f'/{variant}/bin-{b["bin"]}/point'
                        if not b['occupied']:
                            check(pointid not in shapes, 'Empty null bin has no artificial0 point')
                            totals['empty_bins_not_plotted'] += 1
                            continue
                        expected.add(pointid)
                        e = shapes[pointid]
                        check(tag(e) == ('circle' if variant == 'visual' else 'rect'), 'Outlined variant marker')
                        if variant == 'visual':
                            px,py = n(e,'cx'),n(e,'cy');near(n(e,'r'),2.35)
                            check(e.get('fill') == '#FFFFFF', 'Visual white circle fill')
                        else:
                            px,py = n(e,'x')+n(e,'width')/2,n(e,'y')+n(e,'height')/2
                            near(n(e,'width'),3.8);near(n(e,'height'),3.8)
                            check(e.get('fill') == 'none', 'Full transparent square')
                        near(px,x0+float(b['mean_fixed_normalized_margin_confidence'])*pw)
                        near(py,bottom-float(b['accuracy'])*ph)
                        check(e.get('stroke') == COLORS[variant], 'Marker stroke variant')
                        near(n(e,'stroke-width'),.9)
                        check(x0-1e-8 <= px <= x0+pw+1e-8 and top-1e-8 <= py <= bottom+1e-8, 'True fraction coordinates retained')
                        mapped_points.append({'seed':seed,'variant':variant,'bin':b['bin'],'count':b['count'],'mean_score':b['mean_fixed_normalized_margin_confidence'],'accuracy':b['accuracy'],'actual_x':px,'actual_y':py})
                        totals['occupied_points'] += 1
                nn = pre+'/population/N'
                expected.add(nn)
                check(text(texts[nn]) == f'N = {keyed[(seed,"visual")]["queries"]:,}; bin populations', 'Whole-task population N')
                near(n(texts[nn],'x'),x0+pw/2);near(n(texts[nn],'y'),300)
                for key,val,x in (('bin','Bin',x0+8),('visual','V count',x0+58),('full','F count',x0+108)):
                    eid = pre+'/population/header/'+key
                    expected.add(eid);check(text(texts[eid]) == val, 'Population column header')
                    near(n(texts[eid],'x'),x);near(n(texts[eid],'y'),318)
                rule = pre+'/population/header/rule'
                expected.add(rule)
                for k,v in (('x1',x0-5),('x2',x0+pw+4),('y1',323),('y2',323)):near(n(shapes[rule],k),v)
                for bi in range(1,16):
                    yy = 333+(bi-1)*11
                    lab = pre+f'/population/bin-{bi}/label'
                    expected.add(lab);check(text(texts[lab]) == str(bi), 'All15 bin labels including empty')
                    near(n(texts[lab],'x'),x0+8);near(n(texts[lab],'y'),yy)
                    for variant,xx in (('visual',x0+58),('full',x0+108)):
                        key = pre+f'/population/bin-{bi}/'+variant
                        expected.add(key)
                        count = keyed[(seed,variant)]['bins'][bi-1]['count']
                        check(text(texts[key]) == str(count), 'Exact visible bin population')
                        check(texts[key].get('fill') == (COLORS[variant] if count else '#737B83'), 'Count0 shown gray, not missing')
                        near(n(texts[key],'x'),xx);near(n(texts[key],'y'),yy)
                        totals['population_values'] += 1
                totals['seed_panels'] += 1
            check(set(shapes) == expected, 'Exact identities; no bin-center substitutes/extra0points/inter-bin lines/CI')
            count,minfont = native_xml(z,ordinal,task,shapes,w,h)
            notes = '\n'.join(t.text or '' for t in ET.fromstring(z.read(f'ppt/notesSlides/notesSlide{ordinal}.xml')).findall('.//a:t',NS))
            for phrase in (title(task),ROOT_SHA,QUERY_SHA,'stored mean fixed normalized margin score','both fractions on0–1 axes','Markers are not connected',
                           'left-closed/right-open','equal bin numbers do not imply shared bin members','Empty bins retain null','not recomputed',
                           'small counts','No pooled','historical metadata-chain gaps'):
                check(phrase in notes, 'Actual notes semantic '+phrase)
            check('lower' in notes.lower() and 'ECE' in notes and 'retrieval accuracy' in notes, 'Actual lower-ECE caveat')
            for line in csvpath.read_text(encoding='utf-8-sig').splitlines():check(line in notes, 'Exact90bin rows in speaker notes')
            pb = png.read_bytes()
            check(pb[:8] == b'\x89PNG\r\n\x1a\n' and pb[12:16] == b'IHDR', 'PNG format')
            dims = list(struct.unpack('>II',pb[16:24]))
            figures.append({'ordinal':ordinal,'task':task,'title':title(task),'svg':bind(svg),'source_csv':bind(csvpath),'png':bind(png),'png_dimensions':dims,
                            'native_shapes':count,'editable_texts':len(texts),'min_font_pt':minfont,'mapped_points':mapped_points,
                            'empty_bins':sum(not b['occupied'] for r in rr for b in r['bins'])})
            totals['pages'] += 1;totals['native_shapes'] += count;totals['editable_texts'] += len(texts)
    check(totals['pages'] == 11 and totals['seed_panels'] == 33 and totals['occupied_points'] == 140 and totals['empty_bins_not_plotted'] == 850, 'Entire fixed scope')
    check(totals['population_values'] == 990 and totals['saved_ECE_labels'] == 66 and totals['numeric_equality_references'] == 33, 'All saved count/ECE/reference displays')
    report = {'schema':'independent-t5-reliability-native-artifact-review.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'status':'passed_actual_saved_CSV_to_SVG_PPT_geometry_fonts_notes','accepted_with_stated_limits':True,
              'source':bind(Path(__file__)),'data_contract':bind(HERE/'DATA_CONTRACT.json'),'checks':COUNT,'totals':totals,'bindings':bindings,'figures':figures,
              'limits':['Only new figure artifacts and saved small fields; no producer/science import, oldNPZ/query/means/bin assignment/ECE/bootstrap recomputation.',
                        'Exact Decimal saved CSV values; display rounding4decimal for ECE only. Geometry1e-8pt/XML2EMU tolerance is export-only.',
                        '140 occupied markers and850 absent empty-bin observations; all990 populations including0 are visible. Reference y=x is numerical equality only.',
                        'Score is fixed margin transformation, not a calibrated posterior. Lower fixed-score ECE does not establish higher retrieval accuracy or calibration improvement.',
                        'Same whole queries but variant-specific bin members; no pooling/CI/SD/inferential claims. Inherited upstream SHA/chain/model/full-ranking/AP limits remain.',
                        'Flat native objects checked; Microsoft PowerPoint not opened. Actual visual inspection separately recorded.']}
    with (HERE/'ARTIFACT_REVIEW.json').open('x',encoding='utf-8') as stream:
        json.dump(report,stream,ensure_ascii=False,indent=2);stream.write('\n')
    print(json.dumps({'report':bind(HERE/'ARTIFACT_REVIEW.json'),'checks':COUNT,'totals':totals},ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        with (HERE/('REJECTED_ARTIFACT_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S_%f')+'.json')).open('x',encoding='utf-8') as stream:
            json.dump({'source':bind(Path(__file__)),'checks':COUNT,'error':traceback.format_exc()},stream,indent=2)
        raise
