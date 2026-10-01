# Two main-result figures: native editable Visio

Open `formal_main_university1652_native_editable.vsdx` or
`formal_main_sues200_native_editable.vsdx` in Visio. These are newly drawn
native ShapeSheet objects, not an imported SVG, a raster or an OLE object.
The University page has 280 shapes and 73 text objects; SUES has 505 shapes
and 143 text objects. In total, 785 individual objects include the two white
background rectangles. There are no shape groups. Text, cells, error bars,
circles, polygon markers and lines can each be edited directly.

Page widths are exactly 181.9 mm; heights are 137.9 mm and 240.3 mm. Arial
font sizes are explicitly 8, 9 or 10 physical points, rather than assuming
SVG user coordinates are physical points. Reducing page size reduces final
font size. Source x and y coordinates are scaled separately by the original
SVG viewBox width and height to the page dimensions; Visio's upward y axis
is reversed. Text anchors use measured Arial text boxes. This is a native
conversion with visually checked alignment, not a pixel-identical rendering
claim. Each shape's NameU is SVG_0001 etc.; Data1 preserves the SVG ancestor
path, Data2 the primitive kind, and Data3 its ordinal. NATIVE_SHAPE_MAP and
CONVERSION_SPEC contain the full mapping. The actual VSDX has no page
ForeignData or embedded SVG/image/workbook; Visio's docProps/thumbnail.emf
is an application-generated package thumbnail, not page artwork.

## Scientific content and provenance

The exact accepted SVG v2, CSV, original captions, PPT v2 and root adoption
reports are copied in `sources/`. The figures retain all 66 R@1 mean/sample
SD cells and 66 official trapezoidal mAP mean/sample SD intervals. Summaries
use seeds 1, 2 and 3 within each task, with sample SD denominator 2; SD is not
a CI or significance finding. Tasks, heights and directions are not pooled.
SUES labels retain 150, 200, 250 and 300 m in both retrieval directions.

For a positive quantity below 0.05 percentage points, the accepted figure
shows <0.1 rather than zero. The lower line ± <0.1 is a small sample SD, not
a CI. Exact values remain in CSV and original SVG attributes. No statistics,
model inference, full ranking or all-positive-rank AP is recomputed here.
Full has lower three-seed mean R@1 and mAP than Visual in 10 of the 11
official tasks; the street-to-satellite exception has low absolute values.
The graphical conversion does not change those findings or establish a
general improvement. Inherited checkpoint/cache/image SHA authority and
historical evidence-chain gaps remain as documented in the adopted sources.
No NPZ, weight, cache or image bytes were read.

Original PPT v2 notes and exact per-figure values, followed by this batch's
scope, are stored in `notes/` and in the editable page ShapeSheet User.Notes
cell. Page User.SourceSVG_SHA256 and User.SourceCSV_SHA256 retain input pins.
The copied historical SVG captions include the then-current statement that
PPT/Visio was not delivered. That is a preserved historical source, not the
current status: the two PPT figures were adopted earlier, and this batch
adds only these two Visio figures. It does not complete all other Visio
figures, later experiments, the manuscript or Overleaf delivery.

## Actual Visio execution and limits

Installed VISIO.EXE was C:/Program Files/Microsoft Office/Root/Office16/
VISIO.EXE, file/product version 16.0.20326.20158. The successful COM run used
Visio 16.0, FullBuild 1073762150. It created a new invisible author instance,
saved and closed both VSDX documents, quit that instance, then created a
different invisible instance and reopened the saved documents read-only
to export PNG and PDF. Each process was bound by HWND-to-Windows-PID, full
CIM command, parentage and integer creation ticks, with held handles.
Both actual successful instances exited 0; the initial and final Visio
inventories were empty. No existing user application was closed. No Visio
global Settings, registry, add-ins or export preferences were changed.

The original-size PNGs were actually viewed individually by the producer.
All labels, low values, error bars, markers and footnotes were legible with
no visible clipping or text overlap. Default PNG export preferences were
retained. Each PDF is a single-page vector export from the reopened VSDX;
its MediaBox is rounded by Visio by less than 0.2 pt relative to the exact
VSDX page. PDF rendering was not used to substitute for native objects.
An auxiliary PyMuPDF import probe was unavailable; the PDF envelope was
instead inspected with stdlib, while the actual Visio PNGs were viewed.

The first bounded author export check passed 8,989 assertions. It checked
new VSDX package integrity, native structure, text/physical font size,
geometry bounds and line endpoints, editable notes, source pins, PNG/PDF
envelopes and the two real success paths. It is an author check, separate
from the independent review and subsequent root adoption. It is not a new
scientific evaluation or a test of every COM failure branch.

## Preserved preparation and execution history

The first input preparation mistakenly omitted both white backgrounds while
still asserting 785 shapes. It failed before COM execution; source and partial
output are retained. Preparation v2 restored both backgrounds and used this
new output_v2 directory. It passed with 785 shapes and 216 texts.

The first COM builder confused Visio's internal ProcessID with Windows PID,
and failed before Documents.Add. Its exact source/report are preserved.
The task's newly created invisible orphan was sealed by PID 18044, full
command/parentage and exact CIM/held creation identity, then only that held
process was forcibly ended; its actual exit was -1, not a natural exit 0.
COM builder v2 fixed HWND-to-Windows-PID mapping and completed both figures
and the independent reopen/export step. That executed source and full diff
are retained and remain the source of these delivered VSDX bytes.

Static review then identified two unexercised v2 error-branch risks: ownership
was marked before preexisting-PID rejection, and a second instance could
retain the previous handle before new identity was established. Neither
occurred in this batch's recorded successful paths. The separate v3 source
resets per-instance state, marks ownership only after identity checks, and
releases an unconfirmed reference without Quit. V3 is prepared and statically
reviewable but has NOT been executed; it did not create these figures and
is not claimed as tested against all failures. Successful figures were not
regenerated. No scientific state, GPU, model, PowerPoint, recovery, release,
lock, HANDOFF or automation operation was performed.

## Official API references

- [InvisibleApp](https://learn.microsoft.com/en-us/office/vba/api/visio.invisibleapp): creates a separate invisible automation instance.
- [ProcessID](https://learn.microsoft.com/en-us/office/vba/api/visio.application.processid): the internal identity is not the Windows process ID.
- [DrawRectangle](https://learn.microsoft.com/en-us/office/vba/api/visio.page.drawrectangle) and [DrawPolyline](https://learn.microsoft.com/en-us/office/vba/api/visio.shape.drawpolyline): native geometry in internal page units.
- [Page.Export](https://learn.microsoft.com/en-us/office/vba/api/visio.page.export) and [ExportAsFixedFormat](https://learn.microsoft.com/en-us/office/vba/api/visio.document.exportasfixedformat): reopened-document PNG and PDF exports.

The ZIP includes the two VSDX and vector PDFs, exact small sources, notes,
public captions, index, mapping/provenance and executed/prepared sources.
PNG previews remain beside the ZIP. Root-owned files are excluded.
