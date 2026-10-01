"""Independent saved-ShapeSheet decoding and CPU preview; no Visio/producer import.

Preview geometry and labels come exclusively from saved VSDX document/page parts.
Original source SVG is used only by the separate parity checker. No scientific
statistics, scientific libraries, Office automation, or guarded runners.
"""
from pathlib import Path, PurePosixPath
import datetime, hashlib, json, math, posixpath, re, sys, zipfile
import xml.etree.ElementTree as ET

V = 'http://schemas.microsoft.com/office/visio/2012/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P = 'http://schemas.openxmlformats.org/package/2006/relationships'
CT = 'http://schemas.openxmlformats.org/package/2006/content-types'
NS = {'v': V}
MAX_PART = 4 * 1024 * 1024
COUNT = 0


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
    check(settings is not None and settings.find('v:ProtectShapes',NS).text=='0','document shapes unprotected')
    styles={s.attrib['ID']:s for s in document.findall('v:StyleSheets/v:StyleSheet',NS)}
    native=[]; ids=set()
    shapes=page_root.findall('v:Shapes/v:Shape',NS)
    for shape in shapes:
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
        section=shape.find("v:Section[@N='Geometry']",NS)
        check(section is not None,'native Geometry section')
        gc=cells(section)
        check(number(gc,'NoShow',0)==0,'visible native geometry')
        rows=section.findall('v:Row',NS);check(rows,'native geometry rows')
        ellipses=[r for r in rows if r.attrib['T']=='Ellipse']
        if ellipses:
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
        textnode=shape.find('v:Text',NS);text=None
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
                       'text':text,'character':char.get('0'),'paragraph':para.get('0')})
    return {'vsdx':descriptor(path,raw),'page_width_in':width,'page_height_in':height,
            'native_shapes':native,'member_count':len(names),'parts':parts,
            'page_sheet':page_sheet,'page_name':page.attrib.get('NameU')}


def color(value):
    if value.lower() in ['white','black']:
        return value.lower()
    check(re.fullmatch('#[0-9a-fA-F]{6}',value) is not None,'literal RGB color')
    return value


def render_saved_native(decoded, dest, width_px=1375):
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
        ascent,descent=font.getmetrics();lineheight=(ascent+descent)/scale
        vertical=int(number(c,'VerticalAlign',0));check(vertical in [0,1,2],'native vertical alignment')
        offset=[0,(inner_height-lineheight)/2,inner_height-lineheight][vertical]
        baseline_y=top_y-offset-ascent/scale
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
            'pillow_version':pillow_version,'font_layout':'Pillow BASIC; pixel-size rounded at2x supersampling',
            'native_input_only':True,'source_svg_rendered':False,'visio_renderer':False,
            'text_bounds':texts,'clipped_text_count':sum(t['page_glyph_clipped'] for t in texts),
            'limits':['Visio application glyph metrics, kerning, wrapping, caps/joins and repair-free opening remain unvalidated.',
                      'Preview uses actual saved numeric ShapeSheet geometry and text formatting, not provenance/User/source SVG geometry.',
                      'Pillow raster behavior and text metrics approximate saved native layout; preview is not a Visio export.']}


def main():
    raise RuntimeError('Review driver not yet configured; no native file has been rendered by this source.')


if __name__=='__main__':main()
