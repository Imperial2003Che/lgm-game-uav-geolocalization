"""Inspect new T5 v2 figure bytes independently from the pinned display contract.

Only Python standard library; no producer code/checker is imported or executed.
The old query-array, ranking, bootstrap and AURC suites are never repeated.
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
import xml.etree.ElementTree as ET
import zipfile

HERE = Path(__file__).resolve().parent
WORK = HERE.parent.parent / 'query_t5_native_figures_20260929_1856'
OUT = WORK / 'output_v2'
CONTRACT = HERE / 'DATA_CONTRACT.json'
ROOT_SHA = 'f55b05559de3ca536170de4ea0be79988dd7c5cf0c822be5f3572eb31a57af0a'
T5_SHA = '033b6eaea71b3084ca043902f6ba03b6487bf1762a9180963357103097d172cc'
CSV_SHA = '2dc5b6bf9fba1edbde657427f516e0b539b310fb93f49511444a2061e598b40e'
NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
COLORS = {'visual': '#0072B2', 'full': '#D55E00'}
HEADERS = ['dataset','task','seed','variant','queries','point_index','requested_coverage',
           'selected_queries','realized_coverage','selective_r_at_1','selective_risk',
           'AURC_discrete_all_prefixes','query_membership_sha256',
           'selection_index_membership_sha256','source_json_sha256']
COUNT = 0

def check(value, message):
    global COUNT
    COUNT += 1
    if not value:
        raise AssertionError(message)

def near(actual, expected, tolerance=1e-8):
    check(abs(float(actual)-float(expected)) <= tolerance, f'{actual} != {expected}')

def bind(path):
    path = Path(path)
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def tag(e):
    return e.tag.rsplit('}', 1)[-1]

def text(e):
    return ''.join(e.itertext())

def num(e, key):
    return float(e.get(key))

def pin(path, sha):
    actual = bind(path)
    check(actual['sha256'] == sha, 'Exact pin ' + str(path))
    return actual

def csv_rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        check(reader.fieldnames == HEADERS, 'Exact native point CSV schema')
        return list(reader)

def expected_rows(records):
    rows = []
    for record in records:
        for i, point in enumerate(record['points'], 1):
            rows.append({
                'dataset': record['dataset'], 'task': record['task'], 'seed': record['seed'],
                'variant': record['variant'], 'queries': record['queries'], 'point_index': i,
                'requested_coverage': point['requested_fraction'],
                'selected_queries': point['selected_queries'],
                'realized_coverage': point['realized_fraction'],
                'selective_r_at_1': point['selective_r_at_1_fraction'],
                'selective_risk': point['risk_fraction'],
                'AURC_discrete_all_prefixes': record['AURC_discrete_all_prefixes_fraction'],
                'query_membership_sha256': record['query_membership_sha256'],
                'selection_index_membership_sha256': point['selection_index_membership_sha256'],
                'source_json_sha256': T5_SHA})
    return rows

def check_rows(actual, expected):
    check(len(actual) == len(expected), 'All and only expected rows')
    words = {'dataset', 'task', 'variant', 'query_membership_sha256',
             'selection_index_membership_sha256', 'source_json_sha256'}
    for row, wanted in zip(actual, expected):
        for key in HEADERS:
            if key in words:
                check(row[key] == wanted[key], 'CSV direct source string ' + key)
            else:
                check(Decimal(row[key]) == Decimal(str(wanted[key])), 'CSV direct numeric source ' + key)

def title_for(task):
    if task.startswith('university1652_'):
        direction = {'drone_to_satellite': 'Drone → satellite',
                     'satellite_to_drone': 'Satellite → drone',
                     'street_to_satellite': 'Street → satellite'}[task.removeprefix('university1652_')]
        return 'University-1652: ' + direction
    m = re.fullmatch('sues200_uav_(150|200|250|300)m_to_satellite', task)
    if m:
        return f'SUES-200: UAV {m[1]} m → satellite'
    m = re.fullmatch('sues200_satellite_to_uav_(150|200|250|300)m', task)
    check(m is not None, 'Exact SUES height/direction contract')
    return f'SUES-200: Satellite → UAV {m[1]} m'

def inspect():
    bindings = [pin(CONTRACT, 'f206b96dd669daf93cc849b91e29e78c036ca351ecbd539d43c06490d5ac2af2'),
                pin(WORK/'build/build_t5_v2.mjs', '6dd7e413b7681abc54a886f12e99a6652e3e6d7eb7d9ad5d98d521ef282fd76b'),
                pin(WORK/'BUILD_REPORT_V2.json', 'ba4fe7e0feb13b289dbb09975662484e6fafb7e62ab44a2260ed4bf1b3b6533b'),
                pin(OUT/'t5_selective_native_editable_11figures_v2.pptx', 'cb1f3db130cfe7e047fbaae04c74895e73a78d6d141fcfe6a2aedab469c16210')]
    contract = load(CONTRACT)
    report = load(WORK/'BUILD_REPORT_V2.json')
    check(report['figureCount'] == 11 and len(report['figures']) == 11, 'Actual eleven-page candidate')
    records = contract['records']
    check(len(records) == 66 and len(contract['task_order']) == 11, 'Pinned independent scope')
    mapped = {(r['task'], r['seed'], r['variant']): r for r in records}
    for entry in contract['inputs']:
        name = Path(entry['source']['path']).name
        if name in ('transactions_t5_selective_calibration.json','transactions_t5_selective_comparisons.csv'):
            actual = bind(OUT/'source_data'/name)
            check(actual['sha256'] == entry['source']['sha256'] and actual['bytes'] == entry['source']['bytes'], 'Exact inherited small-source copy')
            bindings.append(actual)
        if name == 'CAPTURE.json':
            actual = bind(OUT/'provenance'/name)
            check(actual['sha256'] == entry['source']['sha256'] and actual['bytes'] == entry['source']['bytes'], 'Exact captured adoption metadata copy')
            bindings.append(actual)
    bindings.append(pin(OUT/'provenance/ROOT_POST_ROBUSTNESS_ADOPTION.json', ROOT_SHA))
    all_csv = OUT/'source_data/NATIVE_POINTS_660.csv'
    all_rows = csv_rows(all_csv)
    check_rows(all_rows, expected_rows(records))
    bindings.append(bind(all_csv))
    check(len(all_rows) == 660, 'Exactly 660 native source-mapped point rows')
    ppt = OUT/'t5_selective_native_editable_11figures_v2.pptx'
    totals = {'figures': 0, 'seed_panels': 0, 'native_series': 0, 'point_markers': 0,
              'guide_segments': 0, 'saved_AURC_labels': 0, 'native_shapes': 0, 'editable_texts': 0}
    figures = []
    with zipfile.ZipFile(ppt) as archive:
        names = archive.namelist()
        check(archive.testzip() is None, 'Actual PPT ZIP CRC')
        pages = [n for n in names if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)]
        check(set(pages) == {f'ppt/slides/slide{i}.xml' for i in range(1,12)}, 'Eleven native PPT slides')
        check(not any(n.startswith(('ppt/media/','ppt/charts/','ppt/embeddings/')) for n in names), 'No raster, chart screenshot, embedded workbook')
        presentation = ET.fromstring(archive.read('ppt/presentation.xml'))
        size = presentation.find('p:sldSz', NS)
        near(size.get('cx'), 181.9*36000, 1)
        near(size.get('cy'), 383*12700, 1)
        for ordinal, task in enumerate(contract['task_order'], 1):
            svg = OUT/f'native_svg/t5_{task}.svg'
            csv_path = OUT/f'source_data/t5_{task}__native_points.csv'
            png = OUT/f'previews/{ordinal:02d}_t5_{task}.png'
            receipt = report['figures'][ordinal-1]
            check(receipt['ordinal'] == ordinal and receipt['task'] == task, 'Receipt page identity')
            for key, path in (('svg', svg), ('sourceCSV', csv_path), ('preview', png)):
                actual = bind(path)
                check(actual['sha256'] == receipt[key]['sha256'] and actual['bytes'] == receipt[key]['bytes'], 'Actual new candidate bytes '+key)
                bindings.append(actual)
            wanted_records = [r for r in records if r['task'] == task]
            check_rows(csv_rows(csv_path), expected_rows(wanted_records))
            check(csv_rows(csv_path) == [r for r in all_rows if r['task'] == task], 'Exact complete page subset and row order')
            tree = ET.parse(svg).getroot()
            check(tag(tree) == 'svg', 'SVG root')
            check(tree.get('width').endswith('mm') and tree.get('height').endswith('mm'), 'Physical SVG units')
            width_mm = float(tree.get('width')[:-2]); height_mm = float(tree.get('height')[:-2])
            vx, vy, width, height = map(float, tree.get('viewBox').split())
            near(width_mm, 181.9); near(vx, 0); near(vy, 0); near(height, 383)
            sx = width_mm*72/25.4/width; sy = height_mm*72/25.4/height
            near(sx, 1); near(sy, 1)
            for e in tree.iter():
                check(tag(e) in ('svg','title','desc','rect','circle','line','text'), 'Native SVG element only')
                check(not any(k.rsplit('}',1)[-1] in ('transform','filter','clip-path','href','style') for k in e.attrib), 'No hidden transform, clipping or raster references')
            shapes = {e.get('id'): e for e in tree if e.get('id') and e.get('id') != 'background'}
            check(len(shapes) == len([e for e in tree if e.get('id') and e.get('id') != 'background']), 'Unique native SVG identities')
            texts = {k:e for k,e in shapes.items() if tag(e) == 'text'}
            count_queries = wanted_records[0]['queries']
            wanted_title = title_for(task)
            check(text(texts['title']) == wanted_title, 'Exact visible dataset/task/height/direction')
            check(text(texts['subtitle']) == f'Selective risk by margin-ranked coverage; N = {count_queries:,} queries', 'Visible accepted task N')
            fixed_text = {
                'legend/visual/text': 'Visual', 'legend/full/text': 'Full',
                'risk-axis-label': 'Selective risk = 1 − R@1 among selected queries (%)',
                'coverage-axis-label': 'Realized coverage = selected queries / N (%)',
                'footnote-1': 'Selection: top k = ceil(requested coverage × N), ranked by raw cosine Top-1 margin.',
                'footnote-2': 'Margin is not a calibrated probability. Ties retain the source query order.',
                'footnote-3': 'Points: ten registered coverage levels; connecting segments are visual guides only.',
                'footnote-4': 'Seeds and tasks stay separate. No CI or significance shown; AURC uses all prefixes.'}
            for key, value in fixed_text.items():
                check(text(texts[key]) == value, 'Actual visible definition/limit '+key)
            for e in texts.values():
                check(num(e,'font-size')*sx >= 8-1e-10, 'Actual SVG physical font >= 8pt')
                check(e.get('font-family') == 'Arial', 'Consistent actual typeface')
                check(0 <= num(e,'x') <= width and 0 < num(e,'y') < height, 'Text anchor within page')
            expected_ids = {'title','subtitle','legend/visual/marker','legend/visual/text',
                            'legend/full/marker','legend/full/text','risk-axis-label','coverage-axis-label',
                            'footnote-1','footnote-2','footnote-3','footnote-4'}
            geometry = []
            for seed in (1,2,3):
                prefix = f'seed-{seed}'
                heading = prefix+'/heading'
                expected_ids.add(heading)
                check(text(texts[heading]) == f'Seed {seed}', 'Separate true seed panel')
                xaxis = shapes[prefix+'/x-axis']; yaxis = shapes[prefix+'/y-axis']
                expected_ids.update((prefix+'/x-axis', prefix+'/y-axis'))
                x0, x1 = num(xaxis,'x1'), num(xaxis,'x2')
                top, bottom = num(yaxis,'y1'), num(yaxis,'y2')
                near(num(xaxis,'y1'), bottom); near(num(xaxis,'y2'), bottom)
                near(num(yaxis,'x1'), x0); near(num(yaxis,'x2'), x0)
                check(x1 > x0 and bottom > top, 'Positive actual panel geometry')
                near(x0, 42+(seed-1)*158); near(x1-x0,126)
                near(top,99); near(bottom,235)
                near(num(texts[heading],'x'), (x0+x1)/2)
                for value in (0,25,50,75,100):
                    keys = [prefix+f'/y-grid-{value}',prefix+f'/y-label-{value}',
                            prefix+f'/x-tick-{value}',prefix+f'/x-label-{value}']
                    expected_ids.update(keys)
                    grid,ylab,xtick,xlab = [shapes[k] for k in keys]
                    yy = bottom-value/100*(bottom-top); xx=x0+value/100*(x1-x0)
                    check(text(ylab) == text(xlab) == str(value), 'Actual 0–100 tick labels')
                    near(num(grid,'x1'),x0);near(num(grid,'x2'),x1)
                    near(num(grid,'y1'),yy);near(num(grid,'y2'),yy)
                    near(num(ylab,'x'),x0-5);near(num(ylab,'y'),yy+2.7)
                    near(num(xtick,'x1'),xx);near(num(xtick,'x2'),xx)
                    near(num(xtick,'y1'),bottom);near(num(xtick,'y2'),bottom+3)
                    near(num(xlab,'x'),xx);near(num(xlab,'y'),bottom+14)
                for variant in ('visual','full'):
                    record = mapped[(task,seed,variant)]
                    check(record['queries'] == count_queries, 'Per-seed task N')
                    actual_points=[]
                    for i, point in enumerate(record['points'], 1):
                        key = f'{task}/seed-{seed}/{variant}/point-{i}'
                        expected_ids.add(key); marker = shapes[key]
                        check(tag(marker) == ('circle' if variant == 'visual' else 'rect'), 'Distinct native series marker')
                        if variant == 'visual':
                            px,py=num(marker,'cx'),num(marker,'cy');near(num(marker,'r'),1.85)
                        else:
                            px=num(marker,'x')+num(marker,'width')/2
                            py=num(marker,'y')+num(marker,'height')/2
                            near(num(marker,'width'),3.7);near(num(marker,'height'),3.7)
                        near(px,x0+float(point['realized_fraction'])*(x1-x0))
                        near(py,bottom-float(point['risk_fraction'])*(bottom-top))
                        check(x0-1e-8 <= px <= x1+1e-8 and top-1e-8 <= py <= bottom+1e-8, 'All source risk/realized points within truthful axes')
                        check(marker.get('fill') == COLORS[variant], 'Consistent variant point color')
                        actual_points.append((px,py))
                        totals['point_markers']+=1
                    for i in range(1,10):
                        key=f'{task}/seed-{seed}/{variant}/segment-{i}-{i+1}'
                        expected_ids.add(key); segment=shapes[key]
                        check(tag(segment)=='line' and segment.get('stroke') == COLORS[variant], 'Adjacent guide segment native/color')
                        near(num(segment,'stroke-width'),1)
                        for k,val in zip(('x1','y1','x2','y2'),actual_points[i-1]+actual_points[i]):near(num(segment,k),val)
                        totals['guide_segments']+=1
                    aurc_key=prefix+f'/{variant}/AURC';expected_ids.add(aurc_key)
                    saved=record['AURC_discrete_all_prefixes_fraction']
                    rounded=format(Decimal(saved).quantize(Decimal('.0001'),rounding=ROUND_HALF_UP),'.4f')
                    check(text(texts[aurc_key]) == variant.title()+' '+rounded, 'Saved all-prefix AURC rounded label only; no recompute')
                    near(num(texts[aurc_key],'x'),(x0+x1)/2)
                    check(texts[aurc_key].get('fill') == COLORS[variant], 'AURC legend linkage')
                    totals['saved_AURC_labels']+=1;totals['native_series']+=1
                    geometry.append({'seed':seed,'variant':variant,'saved_AURC_fraction':saved,'display_AURC':rounded,
                                     'actual_point_count':len(actual_points),'axis':[x0,top,x1,bottom],
                                     'first_actual_point':actual_points[0],'last_actual_point':actual_points[-1]})
                key=prefix+'/AURC-label';expected_ids.add(key)
                check(text(texts[key]) == 'All-prefix AURC (fraction)', 'Visible AURC fraction semantics')
                totals['seed_panels']+=1
            check(set(shapes) == expected_ids, 'No missing, extra, paired, error-band or anonymous figure marks')
            slide = ET.fromstring(archive.read(f'ppt/slides/slide{ordinal}.xml'))
            check(not slide.findall('.//p:pic',NS) and not slide.findall('.//a:blip',NS)
                  and not slide.findall('.//p:grpSp',NS) and not slide.findall('.//p:graphicFrame',NS), 'Flat editable native objects only')
            native=slide.findall('p:cSld/p:spTree/p:sp',NS)
            byname={s.find('p:nvSpPr/p:cNvPr',NS).get('name'):s for s in native}
            check(len(byname)==len(native)==len(shapes), 'One-to-one actual native objects with SVG')
            check(set(byname)=={task+'/'+key for key in shapes}, 'All PPT native semantic names')
            for key,e in shapes.items():
                obj=byname[task+'/'+key]
                transform=obj.find('p:spPr/a:xfrm',NS)
                off=transform.find('a:off',NS); ext=transform.find('a:ext',NS)
                x,y,cx,cy=map(float,(off.get('x'),off.get('y'),ext.get('cx'),ext.get('cy')))
                check(x>=-2 and y>=-2 and x+cx<=width*12700+2 and y+cy<=height*12700+2, 'Actual object bounds on page')
                geom=obj.find('p:spPr/a:prstGeom',NS).get('prst')
                if tag(e)=='text':
                    actual_text=''.join(t.text or '' for t in obj.findall('.//a:t',NS))
                    check(actual_text==text(e), 'Exact editable text')
                    rprs=obj.findall('.//a:rPr',NS);check(bool(rprs),'Explicit actual text styling')
                    for rp in rprs:
                        near(float(rp.get('sz'))/100,num(e,'font-size'))
                        check(int(rp.get('sz'))>=800,'Actual XML font >=8pt')
                        check(rp.find('a:latin',NS).get('typeface')=='Arial','Native Arial font')
                    anchor=e.get('text-anchor')
                    actual_anchor=x+cx/2 if anchor=='middle' else x+cx if anchor=='end' else x
                    near(actual_anchor,num(e,'x')*12700,2)
                    near(y,(num(e,'y')-.92*num(e,'font-size'))*12700,2)
                    check(not transform.get('rot') and not transform.get('flipH') and not transform.get('flipV'), 'No unexpected text transform')
                elif tag(e)=='line':
                    check(geom=='line','Native line geometry')
                    x1,x2,y1,y2=[num(e,k) for k in ('x1','x2','y1','y2')]
                    wanted=(min(x1,x2)*12700,min(y1,y2)*12700,abs(x2-x1)*12700,abs(y2-y1)*12700)
                    for actual,val in zip((x,y,cx,cy),wanted):near(actual,val,2)
                    actual_flip=transform.get('flipV') in ('1','true')
                    check(actual_flip==((x2-x1)*(y2-y1)<0), 'Actual diagonal line orientation')
                    check(transform.get('flipH') not in ('1','true') and not transform.get('rot'), 'No unexpected line rotation')
                    stroke=obj.find('p:spPr/a:ln',NS)
                    near(stroke.get('w'),num(e,'stroke-width')*12700,2)
                    check(stroke.find('a:solidFill/a:srgbClr',NS).get('val')==e.get('stroke').lstrip('#'),'Actual stroke color')
                else:
                    if tag(e)=='circle':
                        check(geom=='ellipse','Native circle');r=num(e,'r')
                        box=(num(e,'cx')-r,num(e,'cy')-r,2*r,2*r)
                    else:
                        check(geom=='rect','Native square');box=tuple(num(e,k) for k in ('x','y','width','height'))
                    for actual,val in zip((x,y,cx,cy),box):near(actual,val*12700,2)
                    check(obj.find('p:spPr/a:solidFill/a:srgbClr',NS).get('val')==e.get('fill').lstrip('#'),'Actual marker color')
            # Actual native object spacing after v1 layout rejection: a 100% point
            # must not touch the next panel's tick-label native text boxes.
            for seed in (1,2):
                point_names=[task+f'/{task}/seed-{seed}/{v}/point-10' for v in ('visual','full')]
                label_names=[task+f'/seed-{seed+1}/y-label-{v}' for v in (0,25,50,75,100)]
                for point_name in point_names:
                    pxf=byname[point_name].find('p:spPr/a:xfrm',NS)
                    po=pxf.find('a:off',NS);pe=pxf.find('a:ext',NS)
                    point_right=int(po.get('x'))+int(pe.get('cx'))
                    for label_name in label_names:
                        lo=byname[label_name].find('p:spPr/a:xfrm/a:off',NS)
                        check(int(lo.get('x'))-point_right>8*12700, 'V2 cross-panel marker-to-y-label horizontal clearance >8pt')
            note=ET.fromstring(archive.read(f'ppt/notesSlides/notesSlide{ordinal}.xml'))
            notes='\n'.join(t.text or '' for t in note.findall('.//a:t',NS))
            for phrase in (wanted_title, ROOT_SHA, T5_SHA, CSV_SHA, f'N={count_queries}.',
                           'not the nominal request when ceiling changes the fraction',
                           'not a calibrated posterior probability', 'not a trapezoidal integral of these ten plotted points',
                           'No seed/task/direction/height pooling', '132 paired comparisons',
                           '75% requests', 'Calibration/ECE/reliability bins are also not plotted',
                           'inherited checkpoint/cache/image SHA and historical evidence-chain gaps'):
                check(phrase in notes,'Actual notes definition/limit/source '+phrase)
            for line in csv_path.read_text(encoding='utf-8-sig').splitlines():
                check(line in notes,'Every exact page CSV row in actual PPT notes')
            image_bytes=png.read_bytes()
            check(image_bytes[:8]==b'\x89PNG\r\n\x1a\n' and image_bytes[12:16]==b'IHDR','Actual PNG signature')
            dimensions=list(struct.unpack('>II',image_bytes[16:24]))
            min_font=min(int(rp.get('sz'))/100 for rp in slide.findall('.//a:rPr',NS))
            figures.append({'ordinal':ordinal,'task':task,'title':wanted_title,'queries':count_queries,
                            'svg':bind(svg),'source_csv':bind(csv_path),'png':bind(png),'png_dimensions':dimensions,
                            'svg_physical_font_min_pt':min(num(e,'font-size')*sx for e in texts.values()),
                            'ppt_actual_font_min_pt':min_font,'native_shapes':len(native),'editable_texts':len(texts),
                            'series':geometry,'actual_geometry_mapping':'passed'})
            totals['figures']+=1;totals['native_shapes']+=len(native);totals['editable_texts']+=len(texts)
    check(totals['figures']==11 and totals['seed_panels']==33 and totals['native_series']==66,'Exact page/panel/series scope')
    check(totals['point_markers']==660 and totals['guide_segments']==594 and totals['saved_AURC_labels']==66,'Exact data-to-native display counts')
    result={'schema':'independent-t5-native-artifact-review.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'status':'passed_actual_v2_SVG_PPT_CSV_geometry_units_fonts_and_native_objects','accepted_with_stated_limits':True,
            'source':bind(Path(__file__)),'data_contract':bind(CONTRACT),'checks':COUNT,'totals':totals,
            'bindings':bindings,'figures':figures,
            'limitations':[
                'Only new v2 artifacts checked. V1 layout candidate is retained and is not accepted as the deliverable.',
                'No producer source/checker imported/executed. Actual geometry expectations derive from the independent pinned small-source display contract, not producer panel geometry.',
                'Original 66 query NPZ and scientific/ranking/selection/AURC/bootstrap computations were not repeated. Saved all-prefix AURC labels only mapped and rounded.',
                'Paired132 data preserved byte-exact but not plotted or newly inferred; paired75% distinct from native ten requested levels.',
                'Native flat editable objects/text are not Excel charts. Microsoft PowerPoint not opened. This report is not visual inspection; actual PNG visual inspection is separately recorded.',
                'Seeds/tasks/directions/heights kept separate. No pooling/SD/CI/bootstrap/p-values/significance displayed. Margin is not a calibrated posterior.',
                'All upstream inherited checkpoint/cache/image SHA, historical evidence-chain and saved-value/full-ranking/AP limitations remain.']}
    target=HERE/'ARTIFACT_REVIEW.json'
    with target.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2);stream.write('\n')
    print(json.dumps({'report':bind(target),'checks':COUNT,'totals':totals},ensure_ascii=False))

if __name__=='__main__':
    try:
        inspect()
    except Exception:
        error=traceback.format_exc()
        target=HERE/('REJECTED_ARTIFACT_ATTEMPT_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S_%f')+'.json')
        with target.open('x',encoding='utf-8') as stream:
            json.dump({'source':bind(Path(__file__)),'checks_before_failure':COUNT,'error':error},stream,indent=2)
        print(error)
        raise
