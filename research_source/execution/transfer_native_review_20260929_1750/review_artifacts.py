"""Audit only new T3 figure artifacts, with geometry derived from adopted tables.

The producer module/checker is never imported or executed. Mean/SD remain the
already accepted values. XML geometry and native objects are inspected directly.
"""
from pathlib import Path
import datetime
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import math
import re
import struct
import xml.etree.ElementTree as ET
import zipfile

HERE=Path(__file__).resolve().parent
WORK=HERE.parent.parent/'transfer_native_figures_20260929_1750'
CONTRACT=HERE/'DATA_CONTRACT.json'
ROOT_SHA='a8867a9ebdf01061a55d143b79eff91196571c2275f4379902131a69dd4ce80c'
METRICS=('r_at_1','official_trapezoid_mAP','MRR')
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
COLORS={'visual':'#0072B2','full':'#D55E00'}
COUNT=0

def check(value,message):
    global COUNT
    COUNT+=1
    if not value:raise AssertionError(message)

def near(actual,expected,tolerance=1e-8):
    check(abs(float(actual)-float(expected))<=tolerance,f'Geometry {actual} != {expected}')

def bind(path):
    data=Path(path).read_bytes()
    return {'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def number(e,name):return float(e.get(name))
def tag(e):return e.tag.rsplit('}',1)[-1]
def text(e):return ''.join(e.itertext())
def fmt(value):return format(Decimal(value).quantize(Decimal('.001'),rounding=ROUND_HALF_UP),'.3f')

def inspect():
    check(bind(CONTRACT)['sha256']=='89645c62dc3b8cd0710afc78abb3cdef0597dde8f50d94160cd192439e28ea62','Independent contract pin')
    check(bind(WORK/'build/build_transfer.mjs')['sha256']=='24616ec1dcb78b26d4dfbd9148ed44e22082e5056cb4be5a3bf3db66eec90ffc','Producer source actually read pin')
    check(bind(WORK/'BUILD_REPORT.json')['sha256']=='6d60bb61aeaa10b1b589d7c297dc49ef721c62c2738a55c36d44fa4508d84095','Producer build receipt pin')
    contract=load(CONTRACT)
    build=load(WORK/'BUILD_REPORT.json')
    check(len(build['figures'])==2 and build['figureCount']==2,'Exactly2 actual output figures')
    bindings=[bind(CONTRACT),bind(WORK/'build/build_transfer.mjs'),bind(WORK/'BUILD_REPORT.json')]
    # Only byte binding of the already accepted six small table copies here;
    # no second mean/SD computation or old formula-suite invocation.
    for entry in contract['adopted_small_tables']:
        for path in (Path(entry['source']['path']), WORK/'output/source_data'/Path(entry['source']['path']).name):
            pin=bind(path)
            check(pin['sha256']==entry['source']['sha256'] and pin['bytes']==entry['source']['bytes'],'Exact adopted table/copy')
            bindings.append(pin)
    directions=[('university_to_sues','university1652','sues200',
        'Trained on University-1652 → evaluated on SUES-200',
        [task for h in (150,200,250,300) for task in (f'sues200_uav_{h}m_to_satellite',f'sues200_satellite_to_uav_{h}m')]),
        ('sues_to_university','sues200','university1652',
        'Trained on SUES-200 → evaluated on University-1652',
        ['university1652_drone_to_satellite','university1652_satellite_to_drone','university1652_street_to_satellite'])]
    totals={'figures':0,'metric_cells':0,'mean_markers':0,'SD_intervals':0,'SD_caps':0,'numeric_labels':0,'native_shapes':0,'editable_texts':0}
    results=[]
    for ordinal,(direction,source,target,title,tasks) in enumerate(directions,1):
        svg=WORK/f'output/native_svg/transfer_{direction}.svg'
        ppt=WORK/f'output/transfer_{direction}_native_editable.pptx'
        png=WORK/f'output/previews/transfer_{direction}.png'
        receipt=build['figures'][ordinal-1]
        for key,path in (('svg',svg),('pptx',ppt),('preview',png)):
            actual=bind(path)
            check(actual['sha256']==receipt[key]['sha256'] and actual['bytes']==receipt[key]['bytes'],'Final receipt binds actual'+key)
            bindings.append(actual)
        root=ET.parse(svg).getroot()
        check(tag(root)=='svg','SVG root')
        check(root.get('width').endswith('mm') and root.get('height').endswith('mm'),'Physical SVG dimensions')
        width_mm=float(root.get('width')[:-2]);height_mm=float(root.get('height')[:-2])
        vx,vy,width,height=map(float,root.get('viewBox').split())
        near(width_mm,181.9);near(vx,0);near(vy,0)
        sx=width_mm*72/25.4/width;sy=height_mm*72/25.4/height
        near(sx,1);near(sy,1)
        for e in root.iter():
            check(tag(e) in ('svg','title','desc','rect','circle','line','text'),'SVG native element only')
            check(not any(k.rsplit('}',1)[-1] in ('transform','filter','clip-path','href','style') for k in e.attrib),'No hidden geometry/external raster')
        shapes={e.get('id'):e for e in root if e.get('id') and e.get('id')!='background'}
        check(len(shapes)==len([e for e in root if e.get('id') and e.get('id')!='background']),'Unique semantic SVG IDs')
        texts={k:e for k,e in shapes.items() if tag(e)=='text'}
        check(text(texts['training-evaluation-direction'])==title,'Train/eval direction explicit exact')
        check(text(texts['study-title'])=='Zero-shot cross-dataset retrieval','Cross-dataset title')
        check(text(texts['statistical-summary'])=='Mean ± sample SD; seeds 1, 2, 3','Visible mean/sampleSD3seeds')
        footnotes={
            'footnote/sd':'Bars are sample SD (n − 1 = 2), not confidence intervals or significance tests.',
            'footnote/tasks':'Each retrieval task is separate; no pooling across heights, directions or datasets.',
            'footnote/units':'R@1 and mAP are percentages; MRR × 100 is scaled MRR, not an accuracy percentage.',
            'footnote/numerics':'Labels show mean ± sample SD; exact fractions and all seed values are in the source tables.'}
        for key,wanted in footnotes.items():check(text(texts[key])==wanted,'Exact visible limit'+key)
        for e in texts.values():
            check(number(e,'font-size')*sx>=8-1e-10,'Actual SVG physical font>=8pt')
            check(e.get('font-family')=='Arial','Consistent font family')
            check(0<=number(e,'x')<=width and 0<number(e,'y')<height,'Text anchor inside page')
        cardrows=[g for g in contract['groups'] if g['source_dataset']==source and g['target_dataset']==target]
        check(len(cardrows)==2*len(tasks),'Independent page group membership')
        mapped={ (g['task'],g['variant']):g for g in cardrows}
        cells=[]
        for metric,heading in zip(METRICS,('R@1 (%)','Official mAP (%)','MRR × 100')):
            check(text(texts[metric+'/heading'])==heading,'Separate metric/unit column')
            if metric=='official_trapezoid_mAP':check(text(texts[metric+'/semantics'])=='Trapezoidal AP','Official AP semantics')
            axis=shapes[metric+'/axis'];check(tag(axis)=='line','Actual axis geometry')
            x0=number(axis,'x1');x1=number(axis,'x2');ay=number(axis,'y1')
            near(number(axis,'y2'),ay);check(x1>x0,'Positive axiswidth')
            tickkeys={int(k.rsplit('/',1)[1]):e for k,e in texts.items() if k.startswith(metric+'/tick-label/')}
            check(0 in tickkeys,'Explicit zero starts')
            maxv=max(tickkeys)
            expectedmax=math.ceil(max(float(m['upper_x100']) for g in cardrows for m in g['metrics'] if m['metric']==metric)/10)*10
            check(maxv==expectedmax and set(tickkeys)==set(range(0,maxv+1,10)),'Full accepted interval coverage and honest ticks')
            for value,e in tickkeys.items():
                check(text(e)==str(value),'Tick numeric label')
                near(number(e,'x'),x0+value/maxv*(x1-x0))
                grid=shapes[f'{metric}/grid/{value}'];near(number(grid,'x1'),number(e,'x'));near(number(grid,'x2'),number(e,'x'))
            for ti,task in enumerate(tasks):
                for vi,variant in enumerate(('visual','full')):
                    group=mapped[(task,variant)]
                    values=next(m for m in group['metrics'] if m['metric']==metric)
                    prefix=f'{task}/{variant}/{metric}/'
                    marker=shapes[prefix+'mean'];bar=shapes[prefix+'sd-line']
                    check(tag(marker)==('circle' if variant=='visual' else 'rect'),'Variant marker distinguishable')
                    if variant=='visual':px=number(marker,'cx');py=number(marker,'cy')
                    else:px=number(marker,'x')+number(marker,'width')/2;py=number(marker,'y')+number(marker,'height')/2
                    mean,sd,lo,hi=[float(values[k]) for k in ('mean_x100','sample_sd_x100','lower_x100','upper_x100')]
                    near(px,x0+mean/maxv*(x1-x0));near(number(bar,'x1'),x0+lo/maxv*(x1-x0));near(number(bar,'x2'),x0+hi/maxv*(x1-x0))
                    near(number(bar,'y1'),py);near(number(bar,'y2'),py)
                    check(0<=lo<=mean<=hi<=maxv,'SD interval not clipped')
                    check(marker.get('fill')==COLORS[variant] and bar.get('stroke')==COLORS[variant],'Series colors')
                    for side,key in (('left','x1'),('right','x2')):
                        cap=shapes[prefix+'sd-cap-'+side]
                        near(number(cap,'x1'),number(bar,key));near(number(cap,'x2'),number(bar,key));near((number(cap,'y1')+number(cap,'y2'))/2,py)
                        check(number(cap,'y1')<py<number(cap,'y2') and cap.get('stroke')==COLORS[variant],'Native SD cap')
                    label=texts[prefix+'value'];wanted=fmt(values['mean_x100'])+' ± '+fmt(values['sample_sd_x100'])
                    check(text(label)==wanted,'Actual numeric mean±SD label')
                    near(number(label,'x'),(x0+x1)/2);check(number(label,'y')>py,'Value below corresponding point')
                    near(py,116+46*ti+20*vi)
                    cells.append({'task':task,'variant':variant,'metric':metric,'mean_x100':values['mean_x100'],'sample_sd_x100':values['sample_sd_x100'],'label':wanted,'actual_marker_x':px,'axis_max':maxv,'zero_sd':sd==0})
        for task in tasks:
            if target=='university1652':
                want={'university1652_drone_to_satellite':'Drone → satellite','university1652_satellite_to_drone':'Satellite → drone','university1652_street_to_satellite':'Street → satellite'}[task]
                check(text(texts[task+'/label/0'])==want,'University retrieval direction')
            else:
                h=re.search(r'(150|200|250|300)m',task).group(1)
                check(text(texts[task+'/label/0'])==('UAV → satellite' if '_uav_' in task and '_to_satellite' in task else 'Satellite → UAV'),'SUES retrieval direction')
                check(text(texts[task+'/label/1'])==h+' m','Exact SUESheight')
        with zipfile.ZipFile(ppt) as z:
            names=z.namelist()
            check(z.testzip() is None,'PPT CRC')
            check([n for n in names if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)]==['ppt/slides/slide1.xml'],'Exactly1 nativepage')
            check(not any(n.startswith(('ppt/media/','ppt/embeddings/','ppt/charts/')) for n in names),'No raster/image/charts/embedded workbook')
            presentation=ET.fromstring(z.read('ppt/presentation.xml'));sz=presentation.find('p:sldSz',NS)
            near(sz.get('cx'),width_mm*36000,1);near(sz.get('cy'),height_mm*36000,1)
            slide=ET.fromstring(z.read('ppt/slides/slide1.xml'))
            check(not slide.findall('.//p:pic',NS) and not slide.findall('.//a:blip',NS) and not slide.findall('.//p:grpSp',NS),'Nativeflat objects, no pictures/groups')
            native=slide.findall('p:cSld/p:spTree/p:sp',NS)
            byname={s.find('p:nvSpPr/p:cNvPr',NS).get('name'):s for s in native}
            check(len(byname)==len(native)==len(shapes),'One-to-one actualnativeobjects toSVG')
            check(set(byname)=={direction+'/'+k for k in shapes},'Exact semantic objectnames')
            for key,e in shapes.items():
                obj=byname[direction+'/'+key];xf=obj.find('p:spPr/a:xfrm',NS);off=xf.find('a:off',NS);ext=xf.find('a:ext',NS)
                x,y,cx,cy=map(float,(off.get('x'),off.get('y'),ext.get('cx'),ext.get('cy')))
                near(max(0,-x),0,2);near(max(0,-y),0,2);check(x+cx<=width*12700+2 and y+cy<=height*12700+2,'Actual PPTobject bounds')
                geom=obj.find('p:spPr/a:prstGeom',NS).get('prst')
                if tag(e)=='text':
                    actualtext=''.join(t.text or '' for t in obj.findall('.//a:t',NS))
                    check(actualtext==text(e),'Actual PPTeditable text')
                    rprs=obj.findall('.//a:rPr',NS);check(bool(rprs),'Text has explicit run style')
                    for rp in rprs:
                        near(float(rp.get('sz'))/100,number(e,'font-size'),1e-8);check(int(rp.get('sz'))>=800,'Actual PPT XMLfont >=8pt')
                        check(rp.find('a:latin',NS).get('typeface')=='Arial','Actual PPT font')
                    expectedx=number(e,'x')*12700
                    near(x+cx/2 if e.get('text-anchor')=='middle' else x,expectedx,2)
                    near(y,(number(e,'y')-.92*number(e,'font-size'))*12700,2)
                elif tag(e)=='line':
                    check(geom=='line','Native PPTline')
                    x1_,x2_,y1_,y2_=[number(e,k) for k in ('x1','x2','y1','y2')]
                    for actual,expected in zip((x,y,cx,cy),(min(x1_,x2_)*12700,min(y1_,y2_)*12700,abs(x2_-x1_)*12700,abs(y2_-y1_)*12700)):near(actual,expected,2)
                    check(obj.find('p:spPr/a:ln/a:solidFill/a:srgbClr',NS).get('val')==e.get('stroke').lstrip('#'),'Actual linecolor')
                    near(obj.find('p:spPr/a:ln',NS).get('w'),number(e,'stroke-width')*12700,2)
                else:
                    if tag(e)=='circle':
                        check(geom=='ellipse','Nativecircle');r=number(e,'r');box=(number(e,'cx')-r,number(e,'cy')-r,2*r,2*r)
                    else:check(geom=='rect','Nativesquare');box=tuple(number(e,k) for k in ('x','y','width','height'))
                    for actual,expected in zip((x,y,cx,cy),box):near(actual,expected*12700,2)
                    check(obj.find('p:spPr/a:solidFill/a:srgbClr',NS).get('val')==e.get('fill').lstrip('#'),'Actual native markercolor')
            note=ET.fromstring(z.read('ppt/notesSlides/notesSlide1.xml'));notes='\n'.join(t.text or '' for t in note.findall('.//a:t',NS))
            for phrase in (title,ROOT_SHA,'denominator n−1=2','neither a confidence interval nor a significance test','MRR ×100 is a scaled MRR value','All inherited checkpoint/cache/image SHA and historical evidence-chain limitations'):
                check(phrase in notes,'Notes exact interpretation/source '+phrase)
            for stem in ('THREE_SEED_SUMMARY','SEED_RESULTS'):
                for line in (WORK/f'output/source_data/{stem}.csv').read_text(encoding='utf-8-sig').splitlines():check(line in notes,'Every adopted smallsource CSV row innotes')
            minfont=min(int(rp.get('sz'))/100 for rp in slide.findall('.//a:rPr',NS))
        b=png.read_bytes();check(b[:8]==b'\x89PNG\r\n\x1a\n' and b[12:16]==b'IHDR','ActualPNG')
        dims=list(struct.unpack('>II',b[16:24]))
        for key,amount in [('figures',1),('metric_cells',len(cells)),('mean_markers',len(cells)),('SD_intervals',len(cells)),('SD_caps',2*len(cells)),('numeric_labels',len(cells)),('native_shapes',len(native)),('editable_texts',len(texts))]:totals[key]+=amount
        results.append({'ordinal':ordinal,'direction':direction,'title':title,'source_dataset':source,'target_dataset':target,'task_order':tasks,
                        'svg':bind(svg),'pptx':bind(ppt),'png':bind(png),'png_dimensions':dims,'cells':cells,'native_shapes':len(native),'editable_texts':len(texts),
                        'svg_min_physical_font_pt':min(number(e,'font-size')*sx for e in texts.values()),'ppt_min_font_pt':minfont,'actual_geometry_numeric_and_native_checks':'passed'})
    check(totals['metric_cells']==66 and totals['SD_caps']==132,'All66 mean/SDcells included')
    report={'schema':'independent-transfer-native-artifact-review.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'status':'passed_actual_SVG_PPT_CSV_geometry_fonts_units_native_objects','source':bind(Path(__file__)),'data_contract':bind(CONTRACT),
            'checks':COUNT,'figures':results,'totals':totals,'bindings':bindings,
            'limits':['No author code/checker was imported or executed; new geometry was computed independently from pinned adopted small tables.',
                      'No old2699 or new708 contract suite was repeated. Adopted means/SD were not recomputed; only display x100 and geometry mappings were checked.',
                      'Editable flat vector shapes and text are not Excel chart/workbook objects; Microsoft PowerPoint not opened.',
                      'Geometry checking is separate from actual visual inspection, recorded separately. All upstream source inheritance/ranking/AP/cache limits remain.',
                      'Mean±sampleSD of seeds1/2/3 is descriptive, not CI/SE/significance; no task/height/direction pooling. R@1/mAP percentages versus MRR×100 remain distinct.']}
    with (HERE/'ARTIFACT_REVIEW.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,ensure_ascii=False,indent=2);stream.write('\n')
    print(json.dumps({'report':bind(HERE/'ARTIFACT_REVIEW.json'),'checks':COUNT,'totals':totals},ensure_ascii=False))

if __name__=='__main__':inspect()
