"""Independent saved-ShapeSheet decoding and CPU preview; no Visio/producer import.

Preview geometry and labels come exclusively from saved VSDX document/page parts.
Original source SVG is used only by the separate parity checker. No scientific
statistics, scientific libraries, Office automation, or guarded runners.
"""
from pathlib import Path, PurePosixPath
import collections, datetime, hashlib, json, math, os, posixpath, re, struct, sys, zipfile
import xml.etree.ElementTree as ET

V = 'http://schemas.microsoft.com/office/visio/2012/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P = 'http://schemas.openxmlformats.org/package/2006/relationships'
CT = 'http://schemas.openxmlformats.org/package/2006/content-types'
NS = {'v': V}
MAX_PART = 4 * 1024 * 1024
COUNT = 0
INPUT = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\offline_native_visio_20260930_1030\INPUT_MANIFEST_v2.json')
REVIEW = Path(__file__).resolve().parent


def check(value, message):
    global COUNT
    COUNT += 1
    if not value:
        raise AssertionError(message)


def near(actual, expected, message, tolerance=1e-9):
    check(math.isfinite(actual) and math.isfinite(expected) and
          math.isclose(actual, expected, rel_tol=tolerance, abs_tol=tolerance), message)


def raw_file(path, limit=MAX_PART):
    path = Path(path)
    check(path.is_file() and 0 < path.stat().st_size <= limit, 'bounded file ' + str(path))
    raw = path.read_bytes()
    check(len(raw) <= limit, 'bounded read ' + str(path))
    return raw


def descriptor(path, raw=None):
    path = Path(path)
    if raw is None:
        raw = raw_file(path)
    return {'path': str(path.resolve()), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}


def xml(raw):
    check(b'<!DOCTYPE' not in raw.upper() and b'<!ENTITY' not in raw.upper(), 'no DTD/entity')
    return ET.fromstring(raw)


def local(element):
    return element.tag.split('}')[-1]


def sheet_order(element, shape=False):
    # Selected official Sheet/ShapeSheet sequence checking, not full XSD proof.
    phase=0
    orders={'Cell':0,'Trigger':1,'Section':2,'Shapes':3,'Text':4,'Data1':5,'Data2':6,'Data3':7,'ForeignData':8}
    for child in element:
        tag=local(child)
        check(tag in orders,'known Sheet child '+tag)
        check(orders[tag]>=phase,'saved Sheet child sequence '+tag)
        phase=orders[tag]
    if shape:
        allowed={'ID','OriginalID','Del','FillStyle','LineStyle','TextStyle','IsCustomName','IsCustomNameU','Master','MasterShape','Name','NameU','Type','UniqueID'}
        check(set(element.attrib)<=allowed,'2012 native Shape attributes; no invented OneD')
    for sec in element.findall('v:Section',NS):
        phase=0
        for child in sec:
            tag=local(child);idx={'Cell':0,'Trigger':1,'Row':2}[tag]
            check(idx>=phase,'saved Section child sequence');phase=idx


def cells(element):
    result = {}
    if element is None:
        return result
    for c in element.findall('v:Cell', NS):
        key = c.attrib['N']
        check(key not in result, 'unique Cell ' + key)
        check('E' not in c.attrib, 'no saved cell error ' + key)
        result[key] = c.attrib.get('V', c.text or '')
    return result


def number(c, key, default=None):
    if default is None:
        check(key in c, 'required native numeric cell ' + key)
    value = float(c.get(key, default))
    check(math.isfinite(value), 'finite native cell ' + key)
    return value


def section_rows(element, name):
    sec = element.find("v:Section[@N='" + name + "']", NS)
    if sec is None:
        return {}
    rows = {}
    for row in sec.findall('v:Row', NS):
        index = row.attrib.get('IX', row.attrib.get('N', '0'))
        check(index not in rows, 'unique section row ' + name)
        rows[index] = cells(row)
    return rows


def transform(c, x, y):
    lx, ly = number(c, 'LocPinX'), number(c, 'LocPinY')
    dx, dy = x-lx, y-ly
    if number(c, 'FlipX', 0):
        dx = -dx
    if number(c, 'FlipY', 0):
        dy = -dy
    a = number(c, 'Angle', 0)
    return (number(c, 'PinX') + math.cos(a)*dx - math.sin(a)*dy,
            number(c, 'PinY') + math.sin(a)*dx + math.cos(a)*dy)


def relation_part(part):
    p = PurePosixPath(part)
    return str(p.parent / '_rels' / (p.name + '.rels'))


def decode_vsdx(path):
    raw = raw_file(path, 4 * 1024 * 1024)
    with zipfile.ZipFile(Path(path)) as archive:
        infos = archive.infolist()
        names = [i.filename for i in infos]
        check(len(names) == len(set(names)) and len(names) <= 32, 'unique bounded package members')
        check(all(not n.startswith('/') and '..' not in PurePosixPath(n).parts for n in names), 'safe part URIs')
        check(sum(i.file_size for i in infos) <= 16 * 1024 * 1024, 'bounded uncompressed package')
        check(all(0 < i.file_size <= MAX_PART for i in infos), 'bounded individual parts')
        check(archive.testzip() is None, 'new VSDX CRC')
        check(not any(n.startswith(('visio/media/', 'visio/embeddings/')) or n.endswith(('.bin','.svg')) for n in names), 'no page media/OLE/SVG')
        parts = {i.filename: archive.read(i) for i in infos}
    ct = xml(parts['[Content_Types].xml'])
    check(ct.tag == '{'+CT+'}Types', 'content types namespace')
    defaults = {e.attrib['Extension']: e.attrib['ContentType'] for e in ct if e.tag.endswith('Default')}
    overrides = {e.attrib['PartName'].lstrip('/'): e.attrib['ContentType'] for e in ct if e.tag.endswith('Override')}
    check(defaults.get('rels') == 'application/vnd.openxmlformats-package.relationships+xml', 'relationship MIME')
    for n in names:
        if n == '[Content_Types].xml':
            continue
        check(n in overrides or n.rsplit('.',1)[-1] in defaults, 'declared MIME '+n)
    relations = {}
    for n in names:
        if not n.endswith('.rels'):
            continue
        root = xml(parts[n]); check(root.tag == '{'+P+'}Relationships', 'relationship namespace')
        source = '' if n == '_rels/.rels' else str(PurePosixPath(n).parent.parent / PurePosixPath(n).name[:-5])
        ids = set(); edges = []
        for e in root:
            check(e.attrib.get('TargetMode','Internal') == 'Internal', 'no external relationship')
            check(e.attrib['Id'] not in ids, 'unique relationship Id')
            ids.add(e.attrib['Id'])
            target = posixpath.normpath(posixpath.join(posixpath.dirname(source), e.attrib['Target'])).lstrip('/')
            check(target in parts, 'relationship target exists '+target)
            edges.append({'id': e.attrib['Id'], 'type': e.attrib['Type'], 'target': target})
        relations[source] = edges
    def target(source, suffix):
        candidates = [e['target'] for e in relations.get(source, []) if e['type'] == 'http://schemas.microsoft.com/visio/2010/relationships/'+suffix]
        check(len(candidates) == 1, 'one native '+suffix+' relationship')
        return candidates[0]
    document_part = target('', 'document')
    pages_part = target(document_part, 'pages')
    document = xml(parts[document_part]); pages_root = xml(parts[pages_part])
    check(document.tag == '{'+V+'}VisioDocument', 'native document root')
    check(pages_root.tag == '{'+V+'}Pages', 'native Pages root')
    order={'DocumentSettings':0,'Colors':1,'FaceNames':2,'StyleSheets':3,'DocumentSheet':4,'EventList':5,'HeaderFooter':6,'PublishSettings':7}
    previous=-1
    for child in document:
        check(local(child) in order and order[local(child)]>previous,'selected native document element order')
        previous=order[local(child)]
    pages = pages_root.findall('v:Page', NS); check(len(pages)==1, 'single native page')
    page = pages[0]; page_sheet = page.find('v:PageSheet', NS); pc=cells(page_sheet)
    width,height = number(pc,'PageWidth'),number(pc,'PageHeight')
    check(width>0 and height>0, 'positive page dimensions')
    rel=page.find('v:Rel',NS); check(rel is not None,'page Rel')
    rid=rel.attrib['{'+R+'}id']
    candidates=[e['target'] for e in relations[pages_part] if e['id']==rid and e['type'].endswith('/page')]
    check(len(candidates)==1,'page Rel points to native page')
    page_part=candidates[0]; page_root=xml(parts[page_part])
    check(page_root.tag=='{'+V+'}PageContents','native PageContents root')
    check(not page_root.findall('.//v:ForeignData',NS),'no ForeignData')
    check(not page_root.findall('.//v:Shape[@Type="Group"]',NS),'no group replacement')
    fonts=document.find('v:FaceNames',NS)
    face_names=[f.attrib['NameU'] for f in fonts] if fonts is not None else []
    check('Arial' in face_names,'native Arial font definition')
    settings=document.find('v:DocumentSettings',NS)
    check(settings is not None,'DocumentSettings declared')
    protect=settings.find('v:ProtectShapes',NS)
    protect_value=protect.text if protect is not None else None
    check(protect_value in [None,'0','false'],'optional ProtectShapes not explicitly true')
    styles={s.attrib['ID']:s for s in document.findall('v:StyleSheets/v:StyleSheet',NS)}
    native=[]; ids=set()
    shapes=page_root.findall('v:Shapes/v:Shape',NS)
    for shape in shapes:
        sheet_order(shape,True)
        check(shape.attrib['Type']=='Shape','native Shape type')
        check(shape.attrib['ID'] not in ids,'unique shape ID');ids.add(shape.attrib['ID'])
        for style_key in ['LineStyle','FillStyle','TextStyle']:
            if style_key in shape.attrib:
                check(shape.attrib[style_key] in styles,'declared shape style '+style_key)
        # The new-file scope requires explicit geometry/format cells; no producer
        # defaults or raw-source metadata is used to generate previews.
        c=cells(shape)
        for key in ['LockWidth','LockHeight','LockMoveX','LockMoveY','LockTextEdit','LockSelect','LockDelete','LockFormat']:
            check(number(c,key,0)==0,'shape not protected '+key)
        textnode=shape.find('v:Text',NS)
        section=shape.find("v:Section[@N='Geometry']",NS)
        check(section is not None or textnode is not None,'native geometry or native editable text')
        gc=cells(section)
        check(number(gc,'NoShow',0)==0,'visible native geometry')
        rows=section.findall('v:Row',NS) if section is not None else []
        check(rows or textnode is not None,'native geometry rows for nontext shapes')
        ellipses=[r for r in rows if r.attrib['T']=='Ellipse']
        if not rows:
            check(number(c,'FillPattern',0)==0 and number(c,'LinePattern',0)==0,'native text-only shape has no geometry paint')
            kind='text';points=[]
        elif ellipses:
            check(len(rows)==len(ellipses)==1,'single native ellipse row')
            e=cells(ellipses[0]); center=(number(e,'X'),number(e,'Y'))
            axis1=(number(e,'A')-center[0],number(e,'B')-center[1])
            axis2=(number(e,'C')-center[0],number(e,'D')-center[1])
            points=[transform(c,center[0]+axis1[0]*math.cos(a)+axis2[0]*math.sin(a),center[1]+axis1[1]*math.cos(a)+axis2[1]*math.sin(a)) for a in [i*2*math.pi/128 for i in range(129)]]
            kind='ellipse'
        else:
            check(rows[0].attrib['T']=='MoveTo' and all(r.attrib['T']=='LineTo' for r in rows[1:]),'literal native MoveTo/LineTo geometry')
            points=[transform(c,number(cells(r),'X'),number(cells(r),'Y')) for r in rows]
            kind='line' if all(k in c for k in ['BeginX','BeginY','EndX','EndY']) else 'polygon'
        text=None
        char=section_rows(shape,'Character');para=section_rows(shape,'Paragraph')
        if textnode is not None:
            check(set(char)=={'0'} and set(para)=={'0'},'one explicit native character/paragraph row')
            check(textnode.find('v:cp',NS).attrib['IX']=='0' and textnode.find('v:pp',NS).attrib['IX']=='0','native text run indices')
            text=''.join(textnode.itertext())
            check(text.endswith('\n') and '\n' not in text[:-1],'one native text paragraph')
            text=text[:-1]
            check(char['0']['Font']=='Arial','native text Arial')
            check(number(char['0'],'Style') in [0,1],'native text normal/bold only')
            check(number(char['0'],'Size')*72>=8-1e-9,'minimum native text8pt')
        native.append({'id':shape.attrib['ID'],'name':shape.attrib.get('NameU'),
                       'cells':c,'geometry_cells':gc,'kind':kind,'points':points,
                       'text':text,'character':char.get('0'),'paragraph':para.get('0'),
                       'source_id':shape.find('v:Data1',NS).text,
                       'source_kind':shape.find('v:Data2',NS).text,
                       'geometry_rows':[{'type':r.attrib['T'],'cells':cells(r)} for r in rows],
                       'geometry_formulas':[{cc.attrib['N']:cc.attrib.get('F') for cc in r.findall('v:Cell',NS)} for r in rows]})
    return {'vsdx':descriptor(path,raw),'page_width_in':width,'page_height_in':height,
            'native_shapes':native,'member_count':len(names),'parts':parts,
            'page_sheet':page_sheet,'page_name':page.attrib.get('NameU'),
            'document_protect_shapes':protect_value}


def color(value):
    if value.lower() in ['white','black']:
        return '#FFFFFF' if value.lower()=='white' else '#000000'
    check(re.fullmatch('#[0-9a-fA-F]{6}',value) is not None,'literal RGB color')
    return value


def bound_read(d,limit=MAX_PART):
    check(set(d)=={'path','bytes','sha256'} and type(d['bytes']) is int,'exact typed descriptor')
    check(Path(d['path']).is_absolute() and 0<d['bytes']<=limit,'bounded absolute descriptor')
    raw=raw_file(d['path'],limit)
    check(descriptor(d['path'],raw)==d,'actual bound input bytes '+d['path'])
    return raw


def ttf_vertical_metrics(path):
    # Independent minimal sfnt reader: only units/em and signed hhea metrics.
    # No producer font class/import or source SVG metrics feed the preview.
    raw=raw_file(path)
    check(raw[:4]==b'\x00\x01\x00\x00','installed TrueType sfnt')
    table_count=struct.unpack_from('>H',raw,4)[0]
    tables={}
    for i in range(table_count):
        at=12+16*i;tag=raw[at:at+4].decode('ascii')
        offset,length=struct.unpack_from('>II',raw,at+8)
        check(offset+length<=len(raw),'font table bounded')
        tables[tag]=(offset,length)
    head=tables['head'][0];hhea=tables['hhea'][0]
    em=struct.unpack_from('>H',raw,head+18)[0]
    asc,desc=struct.unpack_from('>hh',raw,hhea+4)
    check(em>0 and asc>0 and desc<0,'independent font hhea metrics')
    return {'descriptor':descriptor(path,raw),'em':em,'ascender':asc,'descender':desc}


def compare_saved_native_to_svg(decoded,fig,fontmetrics):
    # Source SVG enters this comparison only. Renderer gets decoded native data.
    source=xml(bound_read(fig['svg']))
    check(source.tag=='{http://www.w3.org/2000/svg}svg','source SVG namespace')
    expected_width=float(source.attrib['width'][:-2])/25.4
    expected_height=float(source.attrib['height'][:-2])/25.4
    near(decoded['page_width_in'],expected_width,'native page width matches accepted source')
    near(decoded['page_height_in'],expected_height,'native page height matches accepted source')
    near(expected_width*25.4,181.9,'native width181.9mm')
    vb=[float(v) for v in source.attrib['viewBox'].split()]
    scale=expected_width/vb[2];near(scale,expected_height/vb[3],'uniform physical source scale')
    primitives=[e for e in source if local(e) in ['rect','circle','line','text']]
    check(len(primitives)==len(decoded['native_shapes']),'one flat native shape per accepted source primitive')
    counts=collections.Counter();font_sizes=collections.Counter()
    for e,s in zip(primitives,decoded['native_shapes']):
        kind=local(e);counts[kind]+=1;c=s['cells']
        check(s['source_id']==e.attrib['id'] and s['source_kind']==kind,'native data provenance ordinal/id/tag')
        def sn(k):return float(e.attrib[k])*scale
        def coord(actual,expected,label):
            near(actual[0],expected[0],label+'x');near(actual[1],expected[1],label+'y')
        if kind=='rect':
            check(s['kind']=='polygon' and len(s['points'])==5,'native closed rectangle geometry')
            x,y,w,h=sn('x'),expected_height-sn('y')-sn('height'),sn('width'),sn('height')
            for p,q in zip(s['points'],[(x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y)]):coord(p,q,'native rect/source ')
        elif kind=='circle':
            check(s['kind']=='ellipse','native ellipse row for original circle')
            g=s['geometry_rows'][0]['cells'];center=transform(c,number(g,'X'),number(g,'Y'))
            coord(center,(sn('cx'),expected_height-sn('cy')),'native circle/source center ')
            near(number(c,'Width'),2*sn('r'),'native circle diameter x');near(number(c,'Height'),2*sn('r'),'native circle diameter y')
            for k in ['X','C']:near(number(g,k),sn('r'),'native ellipse half width')
            for k in ['Y','B']:near(number(g,k),sn('r'),'native ellipse half height')
            near(number(g,'A'),2*sn('r'),'native ellipse outerx');near(number(g,'D'),2*sn('r'),'native ellipse outery')
        elif kind=='line':
            check(s['kind']=='line' and len(s['points'])==2,'native endpoint line geometry')
            a=(sn('x1'),expected_height-sn('y1'));b=(sn('x2'),expected_height-sn('y2'))
            coord(s['points'][0],a,'native source line start ');coord(s['points'][1],b,'native source line end ')
            coord((number(c,'BeginX'),number(c,'BeginY')),a,'native Begin ');coord((number(c,'EndX'),number(c,'EndY')),b,'native End ')
            near(number(c,'PinX'),(a[0]+b[0])/2,'line PinX cache');near(number(c,'PinY'),(a[1]+b[1])/2,'line PinY cache')
            near(number(c,'Width'),math.dist(a,b),'line length cache');near(number(c,'Height'),0,'native1D height0')
            near(number(c,'Angle'),math.atan2(b[1]-a[1],b[0]-a[0]),'line angle cache')
        else:
            check(s['kind']=='text' and s['text']==e.text,'editable actual native text content')
            ch,pa=s['character'],s['paragraph'];size=sn('font-size')
            near(number(ch,'Size'),size,'physical native text font size')
            check(number(ch,'Style')==(1 if e.get('font-weight','normal')=='bold' else 0),'native text bold style')
            check(ch['Font']=='Arial','actual font name Arial')
            check(color(ch['Color']).upper()==color(e.attrib['fill']).upper(),'native/source text color')
            align={'start':0,'middle':1,'end':2}[e.get('text-anchor','start')]
            check(number(pa,'HorzAlign')==align,'native text anchor alignment')
            near(number(c,'VerticalAlign'),2,'native text bottom alignment')
            for k in ['LeftMargin','RightMargin','TopMargin','BottomMargin']:near(number(c,k),0,'zero native text margin')
            left,bottom=transform(c,0,0);box_width=number(c,'Width');box_height=number(c,'Height')
            anchor=left+[0,box_width/2,box_width][align]
            near(anchor,sn('x'),'actual native textbox anchor/source x')
            fm=fontmetrics['bold' if number(ch,'Style') else 'normal']
            near(box_height,(fm['ascender']-fm['descender'])/fm['em']*size,'actual box/font hhea height')
            near(bottom-fm['descender']/fm['em']*size,expected_height-sn('y'),'saved native hhea baseline/source y')
            check(box_width>=0.2*size,'nonzero native text box')
            font_sizes[round(size*72,6)]+=1
        if kind!='text':
            stroke=e.get('stroke','none')
            near(number(c,'LinePattern'),0 if stroke=='none' else 1,'source/native stroke visibility')
            if stroke!='none':
                check(color(c['LineColor']).upper()==color(stroke).upper(),'source/native line RGB')
                near(number(c,'LineWeight'),float(e.get('stroke-width','1'))*scale,'source/native line physical width')
                near(number(c,'LineCap'),1,'native LineCap1; application parity pending')
            fill=e.get('fill','none');near(number(c,'FillPattern'),0 if fill=='none' else 1,'source/native fill visibility')
            if fill!='none':check(color(c['FillForegnd']).upper()==color(fill).upper(),'source/native fill RGB')
        for row,forms in zip(s['geometry_rows'],s['geometry_formulas']):
            for key,formula in forms.items():
                if formula is None:continue
                m=re.fullmatch(r'(Width|Height)\*(0|0\.5|1)',formula)
                check(m is not None,'selected simple geometry formula only')
                near(number(row['cells'],key),number(c,m.group(1))*float(m.group(2)),'geometry formula numeric cache')
    notes=section_rows(decoded['page_sheet'],'User')
    check(notes['SourceSVG_SHA256']['Value']==fig['svg']['sha256'],'native page bound original source SHA')
    check(json.loads(notes['AcceptedFigureRoot']['Value'])==fig['root'],'native page accepted root descriptor')
    captions=bound_read(fig['captions']).decode('utf8-sig')
    check(captions in notes['Notes']['Value'],'complete accepted family captions in native page Notes')
    check('not validated' in notes['Notes']['Value'] and 'no scientific recomputation' in notes['Notes']['Value'],'native page truthful scope')
    for d in fig['data']:
        check(json.dumps(d,ensure_ascii=False,sort_keys=True) in notes['Notes']['Value'],'native notes source data descriptor')
    return {'source_svg':fig['svg'],'accepted_figure_root':fig['root'],'native_counts':dict(counts),
            'native_font_pt_counts':dict(font_sizes),'source_parity':'Numeric saved geometry/text/font/style/anchor/colors/stroke/notes comparison only; no scientific statistic recomputation.',
            'margin_font_calculation':'Independent hhea table reads only; actual Visio baseline and glyph layout remain pending.'}


def render_saved_native(decoded, dest, fontmetrics, width_px=1375):
    from PIL import Image,ImageDraw,ImageFont,__version__ as pillow_version
    dest=Path(dest);check(not dest.exists(),'exclusive native preview destination')
    width,height=decoded['page_width_in'],decoded['page_height_in']
    supersample=2;scale=width_px/width*supersample
    canvas=Image.new('RGB',(width_px*supersample,round(height*scale)),'white')
    draw=ImageDraw.Draw(canvas);fontcache={};texts=[]
    def pixel(point):return (point[0]*scale,(height-point[1])*scale)
    for shape in decoded['native_shapes']:
        c,gc=shape['cells'],shape['geometry_cells'];points=[pixel(p) for p in shape['points']]
        fill=None;stroke=None
        if number(c,'FillPattern',0)!=0 and number(gc,'NoFill',0)==0:
            fill=color(c['FillForegnd'])
        if number(c,'LinePattern',0)!=0 and number(gc,'NoLine',0)==0:
            check(number(c,'LinePattern')==1,'solid native line pattern')
            stroke=color(c['LineColor'])
            check(number(c,'LineCap',1)==1,'native nonextended LineCap1 candidate')
        if fill is not None:
            draw.polygon(points,fill=fill)
        if stroke is not None:
            weight=max(1,round(number(c,'LineWeight')*scale))
            # Pillow uses its own raster cap/join behavior. This does not prove
            # the application's native LineCap1 appearance equals SVG butt.
            draw.line(points,fill=stroke,width=weight)
        if shape['text'] is None:continue
        check(number(c,'Angle',0)==0 and number(c,'FlipX',0)==0 and number(c,'FlipY',0)==0,'unrotated explicit native text block')
        ch,pa=shape['character'],shape['paragraph']
        size=number(ch,'Size');bold=int(number(ch,'Style'))
        ttf=Path(r'C:\Windows\Fonts\arialbd.ttf' if bold else r'C:\Windows\Fonts\arial.ttf')
        key=(size,bold)
        if key not in fontcache:
            fontcache[key]=ImageFont.truetype(str(ttf),max(1,round(size*scale)),layout_engine=ImageFont.Layout.BASIC)
        font=fontcache[key]
        tw,th=number(c,'TxtWidth',number(c,'Width')),number(c,'TxtHeight',number(c,'Height'))
        tx,ty=number(c,'TxtPinX',number(c,'Width')/2),number(c,'TxtPinY',number(c,'Height')/2)
        tlx,tly=number(c,'TxtLocPinX',tw/2),number(c,'TxtLocPinY',th/2)
        bottomleft=transform(c,tx-tlx,ty-tly)
        top_y=bottomleft[1]+th-number(c,'TopMargin',0)
        inner_left=bottomleft[0]+number(c,'LeftMargin',0)
        inner_width=tw-number(c,'LeftMargin',0)-number(c,'RightMargin',0)
        inner_height=th-number(c,'TopMargin',0)-number(c,'BottomMargin',0)
        fm=fontmetrics['bold' if bold else 'normal']
        ascent=fm['ascender']/fm['em']*size;descent=-fm['descender']/fm['em']*size
        lineheight=ascent+descent
        vertical=int(number(c,'VerticalAlign',0));check(vertical in [0,1,2],'native vertical alignment')
        offset=[0,(inner_height-lineheight)/2,inner_height-lineheight][vertical]
        baseline_y=top_y-offset-ascent
        advance=font.getlength(shape['text'])/scale
        horizontal=int(number(pa,'HorzAlign'));check(horizontal in [0,1,2],'native horizontal alignment')
        text_x=inner_left+[0,(inner_width-advance)/2,inner_width-advance][horizontal]
        px,py=pixel((text_x,baseline_y));fill_text=color(ch['Color'])
        glyph_bbox=draw.textbbox((px,py),shape['text'],font=font,anchor='ls')
        draw.text((px,py),shape['text'],font=font,fill=fill_text,anchor='ls')
        texts.append({'id':shape['id'],'font_pt':size*72,'style':bold,
                      'box_in':[bottomleft[0],bottomleft[1],tw,th],
                      'Pillow_baseline_in':[text_x,baseline_y],
                      'glyph_bbox_px':[v/supersample for v in glyph_bbox],
                      'page_glyph_clipped':glyph_bbox[0]<0 or glyph_bbox[1]<0 or glyph_bbox[2]>canvas.width or glyph_bbox[3]>canvas.height})
    canvas=canvas.resize((width_px,round(height/width*width_px)),Image.Resampling.LANCZOS)
    canvas.save(dest,format='PNG');canvas.close()
    return {'preview':descriptor(dest),'dimensions':[width_px,round(height/width*width_px)],
            'renderer':'Independent native ShapeSheet reader + installed Pillow/FreeType Arial',
            'pillow_version':pillow_version,'font_layout':'Independent TTF hhea block baseline + Pillow BASIC glyphs; pixel-size rounded at2x supersampling',
            'native_input_only':True,'source_svg_rendered':False,'visio_renderer':False,
            'text_bounds':texts,'clipped_text_count':sum(t['page_glyph_clipped'] for t in texts),
            'limits':['Visio application glyph metrics, kerning, wrapping, caps/joins and repair-free opening remain unvalidated.',
                      'Preview uses actual saved numeric ShapeSheet geometry and text formatting, not provenance/User/source SVG geometry.',
                      'Pillow raster behavior and text metrics approximate saved native layout; preview is not a Visio export.']}


def exclusive_json(path,data):
    raw=(json.dumps(data,ensure_ascii=False,allow_nan=False,indent=2)+'\n').encode('utf8')
    with Path(path).open('xb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    return descriptor(path,raw)


def main():
    check(len(sys.argv)==2 and sys.argv[1] in ['sample_t3','full68'],'explicit sample or full review mode')
    mode=sys.argv[1];dest=REVIEW/('sample_t3_review' if mode=='sample_t3' else 'full68_review')
    check(not dest.exists(),'single-use new review directory; no replay')
    manifest_raw=raw_file(INPUT);manifest=json.loads(manifest_raw)
    check(hashlib.sha256(manifest_raw).hexdigest()=='506aa8f9bee244714e61ec610a21345ecbdd89b91cf816d57db1c9c490b10bdd','fixed new input manifest actual SHA')
    producer_dir=INPUT.parent/('sample_t3' if mode=='sample_t3' else 'output68')
    build_raw=raw_file(producer_dir/'BUILD_REPORT.json');build=json.loads(build_raw)
    check(build['native_shape_files_created']==True and build['figure_count']==(2 if mode=='sample_t3' else 68),'actual producer written native output report scope')
    fontmetrics={key:ttf_vertical_metrics(value['path']) for key,value in manifest['fonts'].items()}
    for key in fontmetrics:check(fontmetrics[key]['descriptor']==manifest['fonts'][key],'actual preview installed font binding')
    selected=[f for f in manifest['figures'] if mode=='full68' or f['family']=='transfer']
    check(len(selected)==(68 if mode=='full68' else 2),'expected written file scope')
    dest.mkdir();exclusive_json(dest/'REVIEW_ENTRY.json',{'mode':mode,'reviewer':descriptor(__file__),'input_manifest':descriptor(INPUT,manifest_raw),'producer_report':descriptor(producer_dir/'BUILD_REPORT.json',build_raw),'preview_native_input_only':True,'COM_or_Office_invoked':False,'scientific_execution':False})
    figures=[]
    try:
        for fig in selected:
            stem=Path(fig['svg']['path']).stem
            vp=producer_dir/fig['family']/(stem+'__native_editable.vsdx')
            decoded=decode_vsdx(vp)
            parity=compare_saved_native_to_svg(decoded,fig,fontmetrics)
            png=dest/(fig['family']+'__'+stem+'__native_xml_cpu.png')
            preview=render_saved_native(decoded,png,fontmetrics)
            figures.append({'family':fig['family'],'vsdx':decoded['vsdx'],'member_count':decoded['member_count'],
                            'page_mm':[decoded['page_width_in']*25.4,decoded['page_height_in']*25.4],
                            'document_protect_shapes':decoded['document_protect_shapes'],
                            'parity':parity,'preview':preview})
        report={'schema':'offline-native-visio-independent-artifact-review.v1','passed':True,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mode':mode,'check_count':COUNT,'figure_count':len(figures),'figures':figures,'font_metrics':fontmetrics,'reviewer':descriptor(__file__),'input_manifest':descriptor(INPUT,manifest_raw),'producer_report':descriptor(producer_dir/'BUILD_REPORT.json',build_raw),'native_opc_shape_text_files_reviewed':True,'selected_schema_structure_reviewed':True,'complete_XSD_validation':False,'CPU_XML_derived_previews_written':True,'source_svg_used_only_for_separate_numeric_comparison':True,'Visio_renderer_used':False,'visio_open_repair_render_GUI_edit_roundtrip_validated':False,'scientific_recomputation':False,'old_accepted_suite_replayed':False,'limits':['Selected documented element/relationship/order constraints and explicit cached values were read; this is not complete XSD or application opening verification.','Default settings omitted by the producer, including ProtectShapes, are reported and are not treated as explicit native0 values.','Pillow/FreeType BASIC glyph widths and independently read hhea baseline are a CPU interpretation of saved native cells; actual Visio typography/kerning/wrapping/caps/joins remains pending.','Source figures retain all previously adopted negative results, units, denominators, seed scope and evidence limitations; none are newly recomputed.']}
        rd=exclusive_json(dest/'ARTIFACT_REVIEW.json',report)
        print(json.dumps({'review':rd,'figure_count':len(figures),'check_count':COUNT,'clipped_text_counts':[f['preview']['clipped_text_count'] for f in figures]},ensure_ascii=False))
    except BaseException as error:
        exclusive_json(dest/'REVIEW_FAILURE.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mode':mode,'check_count':COUNT,'error':repr(error),'completed_figures':figures,'replay_allowed':False,'producer_rerun_allowed':False})
        raise


if __name__=='__main__':main()
