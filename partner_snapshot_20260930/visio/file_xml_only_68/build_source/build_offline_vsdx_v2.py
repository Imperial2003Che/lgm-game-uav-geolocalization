"""Translate accepted flat SVG objects into editable native Visio OPC XML.

No COM, Office, scientific import, GPU call, source statistic, or SVG renderer.
Application opening/repair/render/edit/roundtrip validation remains pending.
Each output directory is a single-use CreateNew attempt; failures are retained.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import xml.etree.ElementTree as ET
import zipfile

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
V = "http://schemas.microsoft.com/office/visio/2012/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
SVG = "http://www.w3.org/2000/svg"
MAX_INPUT = 2 * 1024 * 1024
MAX_FONT = 4 * 1024 * 1024
ET.register_namespace("", V)
ET.register_namespace("r", R)

ATTRIBUTES = {
    "svg": {"width", "height", "viewBox", "role"},
    "title": set(), "desc": set(),
    "rect": {"id", "x", "y", "width", "height", "fill", "stroke", "stroke-width"},
    "circle": {"id", "cx", "cy", "r", "fill", "stroke", "stroke-width"},
    "line": {"id", "x1", "y1", "x2", "y2", "stroke", "stroke-width"},
    "text": {"id", "x", "y", "fill", "font-family", "font-size", "font-weight", "text-anchor"},
}
DATA_ATTRIBUTES = {
    "data-clean-fraction", "data-corrupt-fraction", "data-family", "data-kind",
    "data-parameter", "data-parameter-value", "data-retention", "data-severity",
    "data-source-metric", "data-source-task", "data-units", "data-variant",
    "data-x", "data-y", "data-from-severity", "data-to-severity",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def strict_json(raw):
    def pairs(xs):
        d = {}
        for k, v in xs:
            require(k not in d, "duplicate JSON key")
            d[k] = v
        return d
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def bounded(path, limit=MAX_INPUT):
    p = Path(path)
    size = p.stat().st_size
    require(size <= limit, f"input too large: {p}")
    with p.open("rb") as f:
        raw = f.read(limit + 1)
    require(len(raw) == size and len(raw) <= limit, "input size changed/limit")
    return raw


def descriptor(path, raw=None):
    p = Path(path).resolve()
    raw = bounded(p) if raw is None else raw
    return {"path": str(p), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def bound_read(d, limit=MAX_INPUT):
    require(type(d) is dict and set(d) == {"path", "bytes", "sha256"}, "exact descriptor fields")
    require(type(d["bytes"]) is int and 0 <= d["bytes"] <= limit, "descriptor integer size")
    require(type(d["path"]) is str and Path(d["path"]).is_absolute(), "absolute descriptor path")
    require(type(d["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", d["sha256"]), "SHA256")
    raw = bounded(d["path"], limit)
    require(len(raw) == d["bytes"] and hashlib.sha256(raw).hexdigest() == d["sha256"], "bound bytes changed")
    return raw


def create(path, raw):
    with Path(path).open("xb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())


def dump(data):
    return (json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")


def number(value):
    require(type(value) is str and re.fullmatch(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", value), "SVG number")
    n = float(value)
    require(math.isfinite(n), "finite geometry")
    return n


def colour(value, allow_none=True):
    require(value == "white" or re.fullmatch(r"#[0-9a-fA-F]{6}", value) or (allow_none and value == "none"), "unsupported colour")
    return "#FFFFFF" if value == "white" else value


def validate_svg(raw):
    require(b"<!DOCTYPE" not in raw.upper() and b"<!ENTITY" not in raw.upper(), "DTD/entities refused")
    root = ET.fromstring(raw)
    require(root.tag == f"{{{SVG}}}svg", "SVG namespace")
    require(set(root.attrib) <= ATTRIBUTES["svg"], "SVG root effect/attribute")
    require(root.get("role", "img") == "img", "SVG role")
    dimensions = []
    for key in ("width", "height"):
        require(root.get(key, "").endswith("mm"), "SVG physical dimensions in mm")
        dimensions.append(number(root.attrib[key][:-2]))
    require(abs(dimensions[0] - 181.9) <= 1e-10 and dimensions[1] > 0, "frozen 181.9mm width")
    vb = [number(x) for x in root.attrib["viewBox"].split()]
    require(len(vb) == 4 and vb[:2] == [0, 0] and vb[2] > 0 and vb[3] > 0, "viewBox")
    sx, sy = dimensions[0] / 25.4 / vb[2], dimensions[1] / 25.4 / vb[3]
    require(abs(sx - sy) <= 1e-12, "nonuniform viewBox scale refused")
    ids, counts, sizes = set(), collections.Counter(), []
    require(root.text is None or not root.text.strip(), "root text")
    for e in root:
        require(e.tag.startswith("{" + SVG + "}"), "foreign XML namespace")
        tag = e.tag.split("}", 1)[1]
        require(tag in ATTRIBUTES and tag != "svg", "unsupported SVG tag/effect")
        require(len(e) == 0, "SVG child/tspan/group refused")
        require(set(e.attrib) <= ATTRIBUTES[tag] | (DATA_ATTRIBUTES if tag in ("rect", "circle", "line", "text") else set()), "unsupported inherited/style/effect attribute")
        require(e.tail is None or not e.tail.strip(), "nonwhitespace SVG tail")
        counts[tag] += 1
        if tag in ("title", "desc"):
            continue
        require(type(e.get("id")) is str and e.get("id") not in ids, "unique object id")
        ids.add(e.get("id"))
        if tag == "text":
            require(e.get("font-family") == "Arial", "exact Arial")
            require(e.get("font-weight", "normal") in ("normal", "bold"), "font weight")
            require(e.get("text-anchor", "start") in ("start", "middle", "end"), "text anchor")
            require(type(e.text) is str and "\n" not in e.text and "\r" not in e.text, "single-line actual text")
            size = number(e.attrib["font-size"]) * sx * 72
            require(size >= 8 - 1e-10, "font below 8 physical pt")
            sizes.append(size)
            colour(e.attrib["fill"], False)
            number(e.attrib["x"]); number(e.attrib["y"])
        else:
            require(e.text is None or not e.text.strip(), "geometry text")
            if tag == "rect":
                for k in ("x", "y", "width", "height"): number(e.attrib[k])
                require(number(e.attrib["width"]) >= 0 and number(e.attrib["height"]) >= 0, "rect size")
                colour(e.attrib["fill"])
            elif tag == "circle":
                for k in ("cx", "cy", "r"): number(e.attrib[k])
                require(number(e.attrib["r"]) > 0, "radius")
                colour(e.attrib["fill"])
            else:
                for k in ("x1", "y1", "x2", "y2"): number(e.attrib[k])
                require(e.get("stroke") is not None, "explicit line stroke")
            if "stroke" in e.attrib: colour(e.attrib["stroke"])
            if "stroke-width" in e.attrib: require(number(e.attrib["stroke-width"]) >= 0, "stroke width")
    require(counts["title"] == counts["desc"] == 1 and sizes, "one title/desc and text")
    return root, {"width_mm": dimensions[0], "height_mm": dimensions[1], "viewBox": vb,
                  "scale_inch_per_svg_unit": sx, "counts": dict(counts), "minimum_font_pt": min(sizes)}


class ArialMetrics:
    """Bound installed Arial TTF hmtx/cmap/legacy-kern, no font/Office API.

    Advances define an explicit initial textbox, not proof of native layout.
    GPOS/shaping and Visio kerning, baseline/wrapping remain unvalidated.
    """
    def __init__(self, raw):
        self.raw = raw
        require(raw[:4] in (b"\x00\x01\x00\x00", b"true"), "TrueType sfnt")
        def u16(off): return struct.unpack_from(">H", raw, off)[0]
        def i16(off): return struct.unpack_from(">h", raw, off)[0]
        def u32(off): return struct.unpack_from(">I", raw, off)[0]
        self.tables = {}
        for i in range(u16(4)):
            o = 12 + 16 * i; tag = raw[o:o+4].decode("ascii")
            start, size = u32(o + 8), u32(o + 12)
            require(start + size <= len(raw), "TTF table bound")
            self.tables[tag] = (start, size)
        head, _ = self.tables["head"]; hhea, _ = self.tables["hhea"]
        maxp, _ = self.tables["maxp"]; hmtx, _ = self.tables["hmtx"]
        self.em, self.ascender, self.descender = u16(head + 18), i16(hhea + 4), i16(hhea + 6)
        ng, nh = u16(maxp + 4), u16(hhea + 34)
        require(self.em > 0 and self.ascender > 0 and self.descender < 0 and 0 < nh <= ng, "font metrics")
        self.advances = [u16(hmtx + 4 * i) for i in range(nh)]
        self.advances.extend([self.advances[-1]] * (ng - nh))
        cm, _ = self.tables["cmap"]
        candidates = []
        for i in range(u16(cm + 2)):
            o = cm + 4 + 8 * i; plat, enc, sub = u16(o), u16(o + 2), cm + u32(o + 4)
            fmt = u16(sub)
            if (plat == 3 and enc in (1, 10)) or plat == 0:
                if fmt in (4, 12): candidates.append((fmt, sub))
        require(candidates, "Unicode cmap")
        self.fmt, self.cmap = max(candidates)
        self.u16, self.i16, self.u32 = u16, i16, u32
        self.kerning = {}
        if "kern" in self.tables:
            k, size = self.tables["kern"]
            if u16(k) == 0:
                off = k + 4
                for _ in range(u16(k + 2)):
                    length, coverage = u16(off + 2), u16(off + 4)
                    require(length >= 6 and off + length <= k + size, "kern bounds")
                    if coverage == 1:
                        for i in range(u16(off + 6)):
                            p = off + 14 + 6 * i
                            self.kerning[(u16(p), u16(p + 2))] = i16(p + 4)
                    off += length

    def glyph(self, char):
        code, o = ord(char), self.cmap
        if self.fmt == 12:
            for i in range(self.u32(o + 12)):
                p = o + 16 + 12 * i
                lo, hi, first = self.u32(p), self.u32(p+4), self.u32(p+8)
                if lo <= code <= hi: return first + code - lo
        elif code <= 65535:
            count = self.u16(o+6) // 2
            end = o+14; start = end+2*count+2; delta = start+2*count; ro = delta+2*count
            for i in range(count):
                if self.u16(start+2*i) <= code <= self.u16(end+2*i):
                    d, r = self.i16(delta+2*i), self.u16(ro+2*i)
                    if r == 0: return (code+d) & 65535
                    g = self.u16(ro+2*i+r+2*(code-self.u16(start+2*i)))
                    return ((g+d) & 65535) if g else 0
        return 0

    def measure(self, text, size_inch):
        gs = [self.glyph(c) for c in text]
        require(all(g > 0 and g < len(self.advances) for g in gs), "missing Arial glyph")
        units = sum(self.advances[g] for g in gs) + sum(self.kerning.get(pair, 0) for pair in zip(gs, gs[1:]))
        return units * size_inch / self.em


def element(name, parent=None, **attrib):
    node = ET.Element("{" + V + "}" + name, {k: str(v) for k, v in attrib.items()})
    if parent is not None: parent.append(node)
    return node


def cell(parent, name, value, unit=None, formula=None):
    args = {"N": name, "V": format(value, ".17g") if type(value) in (float, int) else value}
    if unit: args["U"] = unit
    if formula: args["F"] = formula
    return element("Cell", parent, **args)


def user(parent, name, text):
    section = next((s for s in parent.findall("{"+V+"}Section") if s.get("N") == "User"), None)
    if section is None:
        section = element("Section", None, N="User")
        # ShapeSheet sequence: Cell*, Section*, Text?, Data1?, Data2?, Data3?.
        # PageSheet has no Text/Data, so append its User section after cells.
        index = next((i for i, child in enumerate(parent)
                      if child.tag.split("}")[-1] in ("Text", "Data1", "Data2", "Data3")), len(parent))
        parent.insert(index, section)
    row = element("Row", section, N=name)
    cell(row, "Value", text, "STR")
    cell(row, "Prompt", "")


def shape_base(shapes, ordinal, x, y, width, height):
    s = element("Shape", shapes, ID=ordinal, NameU=f"Native_{ordinal:05d}", Name=f"Native_{ordinal:05d}",
                IsCustomNameU="1", IsCustomName="1", Type="Shape", LineStyle="0", FillStyle="0", TextStyle="0")
    for key, value in (("PinX", x+width/2), ("PinY", y+height/2), ("Width", width), ("Height", height),
                       ("LocPinX", width/2), ("LocPinY", height/2), ("Angle", 0), ("FlipX", 0), ("FlipY", 0),
                       ("ResizeMode", 0), ("ShdwPattern", 0), ("LockTextEdit", 0), ("LockFormat", 0),
                       ("LockMoveX", 0), ("LockMoveY", 0), ("LockWidth", 0), ("LockHeight", 0), ("LockVtxEdit", 0)):
        cell(s, key, value, "IN" if key in ("PinX", "PinY", "Width", "Height", "LocPinX", "LocPinY") else None,
             "Width*0.5" if key == "LocPinX" else "Height*0.5" if key == "LocPinY" else None)
    return s


def geometry(s, fill):
    g = element("Section", s, N="Geometry", IX="0")
    for key, value in (("NoFill", 0 if fill else 1), ("NoLine", 0), ("NoShow", 0), ("NoSnap", 0), ("NoQuickDrag", 0)):
        cell(g, key, value)
    return g


def polygon(g, width, height):
    for i, (x, y) in enumerate(((0,0), (width,0), (width,height), (0,height), (0,0)), 1):
        row = element("Row", g, T="MoveTo" if i == 1 else "LineTo", IX=i)
        cell(row, "X", x, "IN", "Width*1" if x else "Width*0")
        cell(row, "Y", y, "IN", "Height*1" if y else "Height*0")


def stroke(s, e, scale):
    paint = e.get("stroke", "none")
    cell(s, "LinePattern", 0 if paint == "none" else 1)
    # Microsoft documents 1 as "Square" and 2 as "Extended". Native butt
    # appearance is not inferred from names; cap parity awaits Visio rendering.
    cell(s, "LineCap", 1)
    cell(s, "BeginArrow", 0); cell(s, "EndArrow", 0)
    cell(s, "LineColorTrans", 0)
    if paint != "none":
        cell(s, "LineColor", colour(paint, False))
        cell(s, "LineWeight", number(e.get("stroke-width", "1"))*scale, "IN")


def native_object(shapes, e, ordinal, height, scale, metrics):
    tag = e.tag.split("}")[1]
    n = lambda k: number(e.attrib[k]) * scale
    if tag == "rect":
        w, h = n("width"), n("height")
        s = shape_base(shapes, ordinal, n("x"), height-n("y")-h, w, h)
        paint = colour(e.attrib["fill"])
        cell(s, "FillPattern", 0 if paint == "none" else 1)
        cell(s, "FillForegnd", "#FFFFFF" if paint == "none" else paint)
        cell(s, "FillForegndTrans", 0); stroke(s, e, scale)
        polygon(geometry(s, paint != "none"), w, h)
    elif tag == "circle":
        r = n("r"); w = h = 2*r
        s = shape_base(shapes, ordinal, n("cx")-r, height-n("cy")-r, w, h)
        paint = colour(e.attrib["fill"])
        cell(s, "FillPattern", 0 if paint == "none" else 1)
        cell(s, "FillForegnd", "#FFFFFF" if paint == "none" else paint)
        cell(s, "FillForegndTrans", 0); stroke(s, e, scale)
        row = element("Row", geometry(s, paint != "none"), T="Ellipse", IX=1)
        for k, value, formula in (("X",r,"Width*0.5"), ("Y",r,"Height*0.5"), ("A",w,"Width*1"),
                                   ("B",r,"Height*0.5"), ("C",r,"Width*0.5"), ("D",h,"Height*1")):
            cell(row, k, value, "IN", formula)
    elif tag == "line":
        x1,y1,x2,y2 = n("x1"), height-n("y1"), n("x2"), height-n("y2")
        length = math.hypot(x2-x1, y2-y1)
        s = shape_base(shapes, ordinal, (x1+x2)/2-length/2, (y1+y2)/2, length, 0)
        # Native local horizontal geometry is rotated through the actual XForm.
        for c in list(s):
            if c.tag != "{"+V+"}Cell": continue
            name = c.get("N")
            if name == "PinX": c.set("F", "(BeginX+EndX)/2")
            elif name == "PinY": c.set("F", "(BeginY+EndY)/2")
            elif name == "Width": c.set("F", "SQRT((EndX-BeginX)^2+(EndY-BeginY)^2)")
            elif name == "Angle":
                c.set("V", format(math.atan2(y2-y1,x2-x1), ".17g"))
                c.set("F", "ATAN2(EndY-BeginY,EndX-BeginX)")
        for k,value in (("BeginX",x1),("BeginY",y1),("EndX",x2),("EndY",y2)): cell(s,k,value,"IN")
        cell(s,"FillPattern",0); stroke(s,e,scale)
        g=geometry(s,False)
        for i,x in ((1,0),(2,length)):
            row=element("Row",g,T="MoveTo" if i==1 else "LineTo",IX=i)
            cell(row,"X",x,"IN","Width*0" if i==1 else "Width*1");cell(row,"Y",0,"IN")
    else:
        text, anchor = e.text, e.get("text-anchor", "start")
        size = number(e.attrib["font-size"]) * scale
        font = metrics[e.get("font-weight", "normal")]
        advance = font.measure(text, size)
        # SVG has no text-box width. Reserve 0.2em to reduce accidental wrapping;
        # keep the actual anchor fixed. This is an initial box, not native parity.
        w, h = max(advance + 0.2*size, 0.2*size), (font.ascender-font.descender)*size/font.em
        x = n("x") - (0 if anchor == "start" else w/2 if anchor == "middle" else w)
        bottom = height - n("y") + font.descender*size/font.em
        s = shape_base(shapes, ordinal, x, bottom, w, h)
        for k,v in (("FillPattern",0),("LinePattern",0),("LeftMargin",0),("RightMargin",0),("TopMargin",0),
                    ("BottomMargin",0),("VerticalAlign",2),("TextDirection",0),("HideText",0)):
            cell(s,k,v,"IN" if k.endswith("Margin") else None)
        ch=element("Section",s,N="Character");cr=element("Row",ch,IX=0)
        cell(cr,"Font","Arial",formula='FONT("Arial")');cell(cr,"Color",colour(e.attrib["fill"],False))
        cell(cr,"Style",1 if e.get("font-weight","normal")=="bold" else 0);cell(cr,"Size",size,"PT")
        cell(cr,"Pos",0);cell(cr,"FontScale",1);cell(cr,"Case",0);cell(cr,"ColorTrans",0)
        pa=element("Section",s,N="Paragraph");pr=element("Row",pa,IX=0)
        cell(pr,"HorzAlign",{"start":0,"middle":1,"end":2}[anchor]);cell(pr,"IndFirst",0,"IN")
        cell(pr,"IndLeft",0,"IN");cell(pr,"IndRight",0,"IN");cell(pr,"SpBefore",0,"IN");cell(pr,"SpAfter",0,"IN")
        t=element("Text",s);element("cp",t,IX=0);pp=element("pp",t,IX=0);pp.tail=text+"\n"
    element("Data1",s).text=e.attrib["id"]
    element("Data2",s).text=tag
    element("Data3",s).text=str(ordinal)
    # Provenance only; a native consumer must use native cells, not this record.
    user(s,"SourceObject",json.dumps({"tag":tag,"attributes":dict(e.attrib),"text":e.text if tag=="text" else None},ensure_ascii=False,sort_keys=True))
    return s


def xml(raw_element):
    return ET.tostring(raw_element, encoding="utf-8", xml_declaration=True)


def relationships(entries):
    root=ET.Element("{"+REL+"}Relationships")
    for ident,typ,target in entries: ET.SubElement(root,"{"+REL+"}Relationship",Id=ident,Type=typ,Target=target)
    return xml(root)


def package(svg_root, info, font_metrics, notes, title, source_descriptor, root_descriptor):
    W,H=info["width_mm"]/25.4,info["height_mm"]/25.4
    contents=element("PageContents");contents.set("{http://www.w3.org/XML/1998/namespace}space","preserve")
    shapes=element("Shapes",contents)
    ordinal=0
    for e in svg_root:
        if e.tag.split("}")[1] in ("title","desc"): continue
        ordinal+=1;native_object(shapes,e,ordinal,H,info["scale_inch_per_svg_unit"],font_metrics)
    pages=element("Pages");pg=element("Page",pages,ID=0,NameU=title,Name=title,IsCustomNameU=1,IsCustomName=1)
    ps=element("PageSheet",pg)
    for k,v in (("PageWidth",W),("PageHeight",H),("PageScale",1),("DrawingScale",1),
                ("PageLeftMargin",0),("PageRightMargin",0),("PageTopMargin",0),("PageBottomMargin",0)):
        cell(ps,k,v,"IN")
    user(ps,"Notes",notes);user(ps,"SourceSVG_SHA256",source_descriptor["sha256"])
    user(ps,"AcceptedFigureRoot",json.dumps(root_descriptor,ensure_ascii=False,sort_keys=True))
    element("Rel",pg,**{"{"+R+"}id":"rId1"})
    document=element("VisioDocument");document.set("{http://www.w3.org/XML/1998/namespace}space","preserve")
    settings=element("DocumentSettings",document,DefaultTextStyle=0,DefaultLineStyle=0,DefaultFillStyle=0,DefaultGuideStyle=0)
    element("GlueSettings",settings).text="0";element("SnapSettings",settings).text="0"
    faces=element("FaceNames",document)
    element("FaceName",faces,NameU="Arial",UnicodeRanges="-536858881 -1073711013 9 0",CharSets="1073742335 -65536",Panose="2 11 6 4 2 2 2 2 2 4",Flags=325)
    styles=element("StyleSheets",document);style=element("StyleSheet",styles,ID=0,NameU="Offline native explicit",Name="Offline native explicit",IsCustomName=1,IsCustomNameU=1)
    for k,v in (("EnableLineProps",1),("EnableFillProps",1),("EnableTextProps",1),("LineWeight",0.5/72),
                ("LineColor","#222222"),("LinePattern",1),("FillPattern",0),("ShdwPattern",0),
                ("LeftMargin",0),("RightMargin",0),("TopMargin",0),("BottomMargin",0),("VerticalAlign",2),
                ("LockTextEdit",0),("LockFormat",0),("LockMoveX",0),("LockMoveY",0),("LockWidth",0),("LockHeight",0),("LockVtxEdit",0)):
        cell(style,k,v)
    ds=element("DocumentSheet",document,NameU="TheDoc",Name="TheDoc")
    user(ds,"Scope","Native OPC/XML editable shape files. Not Visio-open/render/roundtrip validated. No scientific recomputation.")
    types=ET.Element("{"+CT+"}Types")
    ET.SubElement(types,"{"+CT+"}Default",Extension="rels",ContentType="application/vnd.openxmlformats-package.relationships+xml")
    ET.SubElement(types,"{"+CT+"}Default",Extension="xml",ContentType="application/xml")
    for pn,content in (("/visio/document.xml","application/vnd.ms-visio.drawing.main+xml"),
                       ("/visio/pages/pages.xml","application/vnd.ms-visio.pages+xml"),
                       ("/visio/pages/page1.xml","application/vnd.ms-visio.page+xml"),
                       ("/docProps/core.xml","application/vnd.openxmlformats-package.core-properties+xml"),
                       ("/docProps/app.xml","application/vnd.openxmlformats-officedocument.extended-properties+xml")):
        ET.SubElement(types,"{"+CT+"}Override",PartName=pn,ContentType=content)
    cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties";dc="http://purl.org/dc/elements/1.1/"
    core=ET.Element("{"+cp+"}coreProperties");ET.SubElement(core,"{"+dc+"}title").text=title
    ET.SubElement(core,"{"+dc+"}creator").text="LGM-GAME offline native XML authoring"
    ET.SubElement(core,"{"+dc+"}description").text="Intermediate native files; Visio application opening/render/edit/roundtrip pending."
    ep="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties";app=ET.Element("{"+ep+"}Properties")
    ET.SubElement(app,"{"+ep+"}Application").text="Offline OPC/XML author (not Visio application)"
    return {
        "[Content_Types].xml":xml(types),
        "_rels/.rels":relationships([("rId1","http://schemas.microsoft.com/visio/2010/relationships/document","visio/document.xml"),
                                     ("rId2",REL+"/metadata/core-properties","docProps/core.xml"),
                                     ("rId3",R+"/extended-properties","docProps/app.xml")]),
        "visio/document.xml":xml(document),
        "visio/_rels/document.xml.rels":relationships([("rId1","http://schemas.microsoft.com/visio/2010/relationships/pages","pages/pages.xml")]),
        "visio/pages/pages.xml":xml(pages),
        "visio/pages/_rels/pages.xml.rels":relationships([("rId1","http://schemas.microsoft.com/visio/2010/relationships/page","page1.xml")]),
        "visio/pages/page1.xml":xml(contents),"docProps/core.xml":xml(core),"docProps/app.xml":xml(app),
    },ordinal


def build(input_manifest, mode):
    require(mode in ("sample_t3","full68"),"build mode")
    raw=bounded(input_manifest);manifest=strict_json(raw)
    require(manifest["schema"]=="offline-native-visio-inputs.v1" and manifest["figure_count"]==68,"input manifest scope")
    require(Path(input_manifest).resolve()==HERE/"INPUT_MANIFEST_v2.json","fixed manifest path")
    require(manifest["builder"]==descriptor(__file__),"builder binding")
    attempt=HERE/("sample_t3" if mode=="sample_t3" else "output68")
    require(not attempt.exists(),"any existing output attempt refuses replay")
    # Re-read all listed adopted small bytes before any artifact output.
    source_bytes={}
    for d in manifest["bindings"]: source_bytes[d["path"]]=bound_read(d)
    metrics={}
    for style,d in manifest["fonts"].items(): metrics[style]=ArialMetrics(bound_read(d,MAX_FONT))
    selected=[x for x in manifest["figures"] if mode=="full68" or x["family"]=="transfer"]
    require(len(selected)==(68 if mode=="full68" else 2),"selected count")
    attempt.mkdir()
    create(attempt/"ATTEMPT.json",dump({"schema":"offline-native-visio-attempt.v1","mode":mode,
          "input_manifest":descriptor(input_manifest,raw),"builder":descriptor(__file__),
          "COM_or_Office_invoked":False,"scientific_execution":False}))
    reports=[]
    try:
        for fig in selected:
            src=bound_read(fig["svg"]);root,info=validate_svg(src)
            require(info==fig["inventory"],"source SVG inventory changed")
            family_dir=attempt/fig["family"];family_dir.mkdir(exist_ok=True)
            source_dir=family_dir/"sources";source_dir.mkdir(exist_ok=True)
            for d in fig["source_files"]:
                rel=Path(d["path"]).relative_to(Path(fig["source_directory"]))
                dst=source_dir/rel;dst.parent.mkdir(parents=True,exist_ok=True)
                if dst.exists(): require(bounded(dst)==source_bytes[d["path"]],"shared source copy mismatch")
                else:create(dst,source_bytes[d["path"]])
            # Exact adopted notes/captions/index/source CSV are retained separately.
            # Full family captions intentionally carry every source caveat.
            captions=source_bytes[fig["captions"]["path"]].decode("utf-8-sig")
            notes=("Offline native conversion scope: source shapes/data/text copied from already-adopted figures; "
                   "no scientific recomputation. Native Visio file opening, repair-free parsing, font layout, "
                   "application rendering, GUI editing and roundtrip are not validated. SVG lines use default butt caps; "
                   "native LineCap=1 is documented as Square, and cap appearance parity is unvalidated.\n\n"
                   +"Source SVG descriptor: "+json.dumps(fig["svg"],ensure_ascii=False,sort_keys=True)
                   +"\nAccepted figure root: "+json.dumps(fig["root"],ensure_ascii=False,sort_keys=True)
                   +"\nSource data descriptors: "+json.dumps(fig["data"],ensure_ascii=False,sort_keys=True)
                   +"\n\nExact original family CAPTIONS.md text follows:\n"+captions)
            title=root.find("{"+SVG+"}title").text
            parts,count=package(root,info,metrics,notes,title,fig["svg"],fig["root"])
            target=family_dir/(Path(fig["svg"]["path"]).stem+"__native_editable.vsdx")
            with target.open("xb") as f:
                with zipfile.ZipFile(f,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
                    for name,part in parts.items():
                        entry=zipfile.ZipInfo(name,(2026,9,30,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED
                        z.writestr(entry,part)
                f.flush();os.fsync(f.fileno())
            # Independent validation is a separate reviewer; these are author checks.
            with zipfile.ZipFile(target) as z:
                require(z.testzip() is None and set(z.namelist())==set(parts),"saved ZIP CRC/9parts")
                require(all(z.read(n)==b for n,b in parts.items()),"saved part bytes")
                saved=ET.fromstring(z.read("visio/pages/page1.xml"))
                ss=saved.find("{"+V+"}Shapes")
                require(len(ss)==count and all(s.get("Type")=="Shape" for s in ss),"actual native shape count")
                require(not any(n.tag.split("}")[-1] in ("ForeignData","Shapes") for s in ss for n in s.iter()),"no raster/embedded/group proxies")
            reports.append({"family":fig["family"],"source_svg":fig["svg"],"output":descriptor(target,bounded(target,8*1024*1024)),
                            "native_objects":count,"native_texts":info["counts"]["text"],"inventory":info,
                            "part_count":9,"author_zip_crc_and_xml_checks":True,"visio_open_validated":False})
        report={"schema":"offline-native-visio-build.v1","mode":mode,"source_manifest":descriptor(input_manifest,raw),
                "figures":reports,"figure_count":len(reports),"native_shape_files_created":True,
                "visio_open_validated":False,"visio_roundtrip_pending":True,"native_application_render_validated":False,
                "CPU_XML_preview_validated":False,"independent_xml_checks":False,"scientific_execution":False,
                "limits":["Actual native files are an intermediate deliverable; application opening/rendering/editing pending.",
                          "Text boxes use bound installed Arial cmap/hmtx/ascent/descent and legacy kern. GPOS/shaping/native kerning may differ.",
                          "SVG lines have default butt caps. Native LineCap=1 cap appearance parity is not Visio-validated.",
                          "All accepted captions/source data and negative-result/evidence limitations remain unchanged."]}
        create(attempt/"BUILD_REPORT.json",dump(report))
        print(json.dumps({"report":descriptor(attempt/"BUILD_REPORT.json"),"figures":len(reports)},ensure_ascii=False))
    except BaseException as exc:
        create(attempt/"BUILD_FAILURE.json",dump({"schema":"offline-native-visio-build-failure.v1","error":repr(exc),
               "completed_file_records":reports,"partial_outputs_retained":True,"replay_allowed":False,
               "scientific_execution":False,"COM_or_Office_invoked":False}))
        raise


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--inputs",required=True);parser.add_argument("--mode",choices=("sample_t3","full68"),required=True)
    a=parser.parse_args();build(a.inputs,a.mode)


if __name__=="__main__":main()
