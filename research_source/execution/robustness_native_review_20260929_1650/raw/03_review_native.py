"""Independent actual SVG/PPT/CSV verification. No producer code is imported/run."""
from pathlib import Path
from decimal import Decimal,ROUND_CEILING
import csv,hashlib,json,math,re,zipfile,datetime,xml.etree.ElementTree as ET

HERE=Path(__file__).absolute().parent
WORK=HERE.parent.parent/'robustness_native_figures_20260929_1650'
OUT=WORK/'output'
CONTRACT=HERE/'DATA_CONTRACT.json'
EXPECTED_CONTRACT='23862cec0a5ff996cb34be45ab594d93a437b4bbbe09338d1978ae9def028dc4'
FAMILIES=['gaussian_noise','gaussian_blur','brightness','contrast','center_occlusion','rotation']
COLORS={'visual':'0072B2','full':'D55E00'}
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','s':'http://www.w3.org/2000/svg'}
COUNT=0
def check(ok,message):
    global COUNT
    COUNT+=1
    if not ok:raise AssertionError(message)
def near(a,b,tolerance=1e-7):check(abs(float(a)-float(b))<=tolerance,f'Geometry {a} != {b}')
def binding(path):
    raw=path.read_bytes();return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def text(element):return ''.join(element.itertext())
def csvrows(path):
    with path.open(encoding='utf-8-sig',newline='') as stream:return list(csv.DictReader(stream))
def label(task):
    names={'university1652_drone_to_satellite':'University-1652: Drone → satellite',
      'university1652_satellite_to_drone':'University-1652: Satellite → drone',
      'university1652_street_to_satellite':'University-1652: Street → satellite'}
    if task in names:return names[task]
    m=re.fullmatch(r'sues200_uav_(150|200|250|300)m_to_satellite',task)
    if m:return f'SUES-200: UAV {m[1]} m → satellite'
    m=re.fullmatch(r'sues200_satellite_to_uav_(150|200|250|300)m',task)
    check(m is not None,'Fixed task name');return f'SUES-200: Satellite → UAV {m[1]} m'
def xyz(shape):
    tr=shape.find('p:spPr/a:xfrm',NS);off=tr.find('a:off',NS);ext=tr.find('a:ext',NS)
    return tr,*[int(off.get(k)) for k in ('x','y')],*[int(ext.get(k)) for k in ('cx','cy')]

def main():
    check(binding(CONTRACT)['sha256']==EXPECTED_CONTRACT,'Fixed independent data contract')
    contract=read(CONTRACT);cards=contract['figures']
    check(len(cards)==22,'Fixed figure count')
    deck=OUT/'robustness_native_editable_22figures.pptx'
    z=zipfile.ZipFile(deck);names=z.namelist()
    slides=sorted([n for n in names if re.fullmatch(r'ppt/slides/slide\d+.xml',n)],key=lambda n:int(re.search(r'(\d+)\.xml',n).group(1)))
    check(len(slides)==22,'Actual PPT22 slides')
    check(not any(n.startswith('ppt/media/') or n.startswith('ppt/embeddings/') or n.startswith('ppt/charts/') for n in names),'No embedded raster/SVG/media/chart workbook')
    presentation=ET.fromstring(z.read('ppt/presentation.xml'));size=presentation.find('p:sldSz',NS)
    width,height=int(size.get('cx')),int(size.get('cy'))
    check((width,height)==(round(181.9*36000),round(165*36000)),'Actual PPT physical size')
    check(len(list((OUT/'native_svg').glob('*.svg')))==22,'Exactly22 newSVG files')
    reports=[];total_markers=0;total_segments=0;total_texts=0;total_shapes=0;bindings=[binding(CONTRACT),binding(deck)]
    for ordinal,(card,slidepath) in enumerate(zip(cards,slides),1):
        task,metric=card['task'],card['metric'];stem=task+'__'+metric.lower()
        original=Path(card['csv']['path']);check(binding(original)==card['csv'],'Adopted CSV pin')
        copied=OUT/'source_data'/f'{stem}.csv'
        check(copied.read_bytes()==original.read_bytes(),'Exact source CSV copy')
        rows=csvrows(copied);lookup={(r['variant'],r['corruption'],int(r['severity_index'])):r for r in rows}
        check(len(lookup)==60,'Source mapping unique60')
        svg=OUT/'native_svg'/f'{stem}.svg';root=ET.parse(svg).getroot()
        check(root.get('width')=='181.9mm' and root.get('height')=='165mm','SVG declared dimensions')
        vx,vy,vw,vh=map(float,root.get('viewBox').split());near(vx,0);near(vy,0)
        sx=181.9*72/25.4/vw;sy=165*72/25.4/vh;near(sx,sy)
        ids={e.get('id'):e for e in root if e.get('id')};check(len(ids)==sum(bool(e.get('id')) for e in root),'Unique SVG identifiers')
        allowed={'svg','title','desc','rect','circle','line','text'}
        check(all(e.tag.split('}')[-1] in allowed for e in root.iter()),'Native SVG primitives only')
        check(not any(any(k in e.attrib for k in ('clip-path','transform','filter','style','href')) for e in root.iter()),'No hidden clipping/transform/external/raster')
        primitives={key:value for key,value in ids.items() if key!='background'}
        texts={key:value for key,value in primitives.items() if value.tag.endswith('}text')}
        check(text(texts['title'])==label(task),'Direction/height/dataset title')
        ml='R@1' if metric=='r_at_1' else 'Official mAP'
        check(text(texts['metric-title'])==f'{ml} retention under image corruption','Metric title')
        baseline=f'Clean {ml} (%): Visual {100*float(card["own_clean_fraction"]["visual"]):.4f}; Full {100*float(card["own_clean_fraction"]["full"]):.4f}'
        check(text(texts['clean-baselines'])==baseline,'Absolute own clean labels from adopted CSV')
        for phrase in ['Seed 1 only.','Higher retention does not imply higher absolute corrupted accuracy.',
                       'cached CLIP for clean queries and online CLIP for corrupted queries.',
                       'evidence-path differences as well as image corruption.']:
            check(phrase in '\n'.join(text(e) for e in texts.values()),'Visible limitation '+phrase)
        for name,e in texts.items():
            size_pt=float(e.get('font-size'))*sx
            check(size_pt>=8-1e-9 and e.get('font-family')=='Arial','Physical SVG font >=8pt')
            x,y=float(e.get('x')),float(e.get('y'))
            check(0<=x<=vw and 0<y<=vh,'Text anchor in page')
        ymax=int((max(Decimal('110'),Decimal(card['retention_max'])*Decimal('1.05'))/20).to_integral_value(rounding=ROUND_CEILING))*20
        markers=0;segments=0
        for family in FAMILIES:
            yax=ids[f'panel-{family}-axis-y'];xax=ids[f'panel-{family}-axis-x']
            x0=float(yax.get('x1'));top=float(yax.get('y1'));bottom=float(yax.get('y2'));right=float(xax.get('x2'))
            near(yax.get('x2'),x0);near(xax.get('x1'),x0);near(xax.get('y1'),bottom);near(xax.get('y2'),bottom)
            check(right>x0 and bottom>top,'Positive plot extent')
            for tick in range(0,ymax+1,20):
                grid=ids[f'panel-{family}-grid-{tick}'];ty=bottom-tick/ymax*(bottom-top)
                near(grid.get('y1'),ty);near(grid.get('y2'),ty)
                check(text(ids[f'panel-{family}-ytick-{tick}'])==str(tick),'Y tick value includeszero and fullrange')
            for variant in ('visual','full'):
                points=[]
                for severity in range(6):
                    retained=100.0 if severity==0 else float(lookup[(variant,family,severity)]['retained_percent_of_clean'])
                    expected=(x0+severity/5*(right-x0),bottom-retained/ymax*(bottom-top))
                    e=ids[f'{family}-{variant}-severity-{severity}']
                    check(e.get('fill')=='#'+COLORS[variant],'Marker variant color')
                    check(e.get('data-source-task')==task and e.get('data-source-metric')==metric,'Marker task metric binding')
                    if variant=='visual':
                        check(e.tag.endswith('}circle'),'Visual native circle');center=(float(e.get('cx')),float(e.get('cy')));radius=float(e.get('r'))
                    else:
                        check(e.tag.endswith('}rect'),'Full native square');radius=float(e.get('width'))/2;near(e.get('height'),2*radius);center=(float(e.get('x'))+radius,float(e.get('y'))+radius)
                    near(center[0],expected[0]);near(center[1],expected[1]);near(e.get('data-retention'),retained)
                    check(0<=center[0]-radius<center[0]+radius<=vw and 0<=center[1]-radius<center[1]+radius<=vh,'Unclipped marker inside page')
                    check(top-1e-8<=center[1]<=bottom+1e-8,'Marker full retention within0-based axis')
                    points.append(expected);markers+=1
                for j in range(1,6):
                    e=ids[f'{family}-{variant}-segment-{j-1}-{j}']
                    for field,expected in zip(('x1','y1','x2','y2'),[*points[j-1],*points[j]]):near(e.get(field),expected)
                    check(e.get('stroke')=='#'+COLORS[variant],'Segment variant color');segments+=1
        slide=ET.fromstring(z.read(slidepath));tree=slide.find('p:cSld/p:spTree',NS)
        shapes=tree.findall('p:sp',NS)
        check(len(shapes)==len(primitives),'Every SVG primitive has a native PPTshape')
        check(not slide.findall('.//p:pic',NS) and not slide.findall('.//a:blip',NS) and not tree.findall('p:grpSp',NS),'No picture or SVG/raster replacement in slide')
        shape_names={e.find('p:nvSpPr/p:cNvPr',NS).get('name'):e for e in shapes}
        prefix=task+'/'+metric+'/'
        check(set(shape_names)=={prefix+k for k in primitives},'Exact one-to-one semantic primitive names')
        for identifier,e in primitives.items():
            shape=shape_names[prefix+identifier];tr,x,y,cx,cy=xyz(shape);tag=e.tag.split('}')[-1]
            check(x>=-1 and y>=-1 and x+cx<=width+1 and y+cy<=height+1,'PPT primitive bbox inside page')
            geometry=shape.find('p:spPr/a:prstGeom',NS).get('prst')
            if tag=='text':
                check(''.join(t.text or '' for t in shape.findall('.//a:t',NS))==text(e),'Exact editable PPT text')
                fs=float(e.get('font-size'))*sx
                props=shape.findall('.//a:rPr',NS)+shape.findall('.//a:defRPr',NS)
                check(bool(props),'PPT text has explicit font sizes')
                for prop in props:
                    check(int(prop.get('sz'))>=800,'Actual PPT XML font>=800')
                    near(int(prop.get('sz'))/100,fs,1e-6)
                    check(prop.find('a:latin',NS).get('typeface')=='Arial','PPTfont Arial')
                anchor=e.get('text-anchor');anchor_x=x if anchor=='start' else x+cx/2 if anchor=='middle' else x+cx
                near(anchor_x,float(e.get('x'))*12700,2)
                near(y,(float(e.get('y'))-float(e.get('font-size'))*.92)*12700,2)
            elif tag=='line':
                check(geometry=='line','PPT actual native line');a,b,d,f=[float(e.get(k)) for k in ('x1','y1','x2','y2')]
                for got,expected in zip((x,y,cx,cy),(min(a,d)*12700,min(b,f)*12700,abs(d-a)*12700,abs(f-b)*12700)):near(got,expected,2)
                check((tr.get('flipV')=='1')==((d-a)*(f-b)<0),'PPT line direction slope retained')
                stroke=shape.find('p:spPr/a:ln/a:solidFill/a:srgbClr',NS)
                check(stroke.get('val')==e.get('stroke').lstrip('#'),'PPT line color')
            else:
                if tag=='circle':
                    check(geometry=='ellipse','Editable PPT ellipse');radius=float(e.get('r'));a=float(e.get('cx'))-radius;b=float(e.get('cy'))-radius;d=f=2*radius
                else:
                    check(geometry=='rect','Editable PPTsquare');a,b,d,f=[float(e.get(k)) for k in ('x','y','width','height')]
                for got,expected in zip((x,y,cx,cy),(a*12700,b*12700,d*12700,f*12700)):near(got,expected,2)
                check(shape.find('p:spPr/a:solidFill/a:srgbClr',NS).get('val')==e.get('fill').lstrip('#'),'PPTmarkercolor')
        notes=ET.fromstring(z.read(f'ppt/notesSlides/notesSlide{ordinal}.xml'))
        note_text='\n'.join(t.text or '' for t in notes.findall('.//a:t',NS))
        check(card['csv']['sha256'] in note_text and card['csv']['path'] in note_text,'Notes exact sourceCSV binding')
        for phrase in ('no pooling, multi-seed SD, confidence intervals or significance','percentage points, distinct','64-sample clean diagnostic','no numerical equivalence threshold'):
            check(phrase in note_text,'Notes scientific limitation '+phrase)
        for line in original.read_text(encoding='utf-8-sig').splitlines():check(line in note_text,'All60 exactCSV rows retained innotes')
        for family,sequence in card['parameter_sequences'].items():
            expected=f'{sequence[0]["parameter"]}=[{", ".join(format(float(row["value"]),"g") for row in sequence)}]; {sequence[0]["units"]}.'
            check(expected in note_text,'Exact frozen parameter/units sequence')
        check(markers==72 and segments==60,'Six panels each2x6markers/2x5segments')
        total_markers+=markers;total_segments+=segments;total_texts+=len(texts);total_shapes+=len(shapes)
        for path in (original,copied,svg):bindings.append(binding(path))
        reports.append({'ordinal':ordinal,'task':task,'metric':metric,'source':card['csv'],'svg':binding(svg),
            'y_range':[0,ymax],'markers_from_original_csv':markers,'segments':segments,'svg_editable_texts':len(texts),
            'native_PPT_shapes':len(shapes),'physical_min_font_pt':min(float(e.get('font-size'))*sx for e in texts.values()),
            'actual_PPT_xml_min_font_pt':min(int(p.get('sz'))/100 for p in slide.findall('.//a:rPr',NS)),
            'retention_over100_preserved':card['retention_over_100_rows'],'geometry_font_numeric_checks':'passed'})
    report={'schema':'independent-native-robustness-artifact-review.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'status':'passed_actual_SVG_PPT_CSV_structure_geometry_values','source':binding(Path(__file__)),
      'data_contract':binding(CONTRACT),'producer_source_read':binding(WORK/'build/build_robustness.mjs'),
      'assertions':COUNT,'figures':reports,'bindings':bindings,'totals':{'figures':22,'markers':total_markers,'segments':total_segments,'texts':total_texts,'native_shapes':total_shapes},
      'limits':['Independent stdlib parses actual final artifacts and CSV inputs; no author checker or build code was imported/executed.',
        'Original 5350 data-contract assertions and6600 CSV formulas were not rerun; exact adopted CSV bindings were checked for current geometry mapping.',
        'Geometry/structure checks alone are not visual inspection. Separate visual report lists actually viewed final PPT renders.',
        'Editable flat shapes and text, not Excel charts/workbooks; grouping is not asserted.',
        'Seed1-only/no pooling/SD/CI/significance; Full cached-clean/online-corrupt pathways and all upstream inheritance limitations remain.']}
    target=HERE/'ARTIFACT_REVIEW.json'
    with target.open('x',encoding='utf-8') as stream:json.dump(report,stream,ensure_ascii=False,indent=2);stream.write('\n')
    print(json.dumps({'assertions':COUNT,'report':binding(target),'totals':report['totals']},ensure_ascii=False))
if __name__=='__main__':main()
