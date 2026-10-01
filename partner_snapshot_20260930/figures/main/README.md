# Native editable main-result figures

Use the two `output/*_native_editable_v2.pptx` files. Each contains one scientific
figure on its own physical canvas, without a cover. University-1652 is
181.9 × 137.9 mm; SUES-200 is 181.9 × 240.3 mm. The adjacent PNGs are actual
renders obtained by importing these final PPTX files with artifact-tool.

Every original visible SVG primitive is a native PPTX object: 280 objects for
University and 505 for SUES. All 216 text objects retain their exact text and
Arial 8, 9 or 10 point sizes. Cells, color-scale segments, grid lines, error bars,
caps and markers are individually editable shapes. There is no embedded image,
SVG or Excel chart object. The selection names preserve the original SVG group
hierarchy. The exported API's `noGrp` lock remains, so this delivery establishes
individual object editability rather than preservation of SVG group editing.

All 66 heatmap cells and 66 mAP intervals retain the accepted source values and
geometry. Source CSV copies accompany the figures and their full exact contents
also appear in slide notes with SHA-256 provenance. Error bars and the lower cell
line show sample SD over seeds 1, 2 and 3, not confidence intervals. Small positive
values displayed as `<0.1` retain the source caption's meaning. The four SUES
altitudes remain 150, 200, 250 and 300 m. Tasks and altitudes are separate.

`build/build_native_v2.mjs` is the JavaScript artifact-tool authoring source.
`build/*.validation_v2.json` records the successful required finalizer structural,
layout, explicit Arial and import checks. `verify_native.py` reads the PPTX ZIP
and XML using stdlib only; its first execution passed 11,311 assertions, comparing
every source primitive, text, font, point size, geometry, color and stroke and
both tables' exact CSV mean/SD origin. `NATIVE_PPTX_REVIEW.json` records this
producing agent check. No additional independent agent review is claimed.

The final v2 renders were visually inspected at full figure size. Both preserve
the accepted layout, legible cell values and complete labels, without clipping
or unintended overlap. Close mAP markers remain close because the original
measurements are close on the same 0–100 scale. This is not a scientific change.
PowerPoint was not opened; application-specific edit/save behavior has not been
tested. Rendering and all authoring used CPU processes, without launching a
PowerPoint UI or a scientific/GPU job.

Build history is retained. The first attempt stopped at the finalizer's import
subprocess because the required `RUNTIME_NODE_MODULES` environment variable was
missing. The initial candidate, preview and logs remain under
`build/first_attempt/`. Supplying the documented runtime environment allowed the
same builder to finish. Its initial final files remain under `output/` without
the `_v2` suffix. V2 changes only notes selection and output filenames: it keeps
the relevant individual caption and scientific limitations while removing the
historical source-caption claim that a PPT had not yet been delivered. The visible
data and layout are unchanged. These earlier files are retained evidence, not the
recommended deliverables. The two JS versions and their complete diff are kept.

This is a format conversion of the accepted official result figures. It does not
rerun scientific evaluation, recompute seed statistics, amend conclusions or
resolve inherited checkpoint/cache/image evidence limitations. The original
SVG/CSV/captions and all scientific files, state, plans, releases, HANDOFF and
automation are unchanged. It completes these two PowerPoint figures, not the
whole project, final manuscript or remaining figure set.
