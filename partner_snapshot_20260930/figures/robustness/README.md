# Editable robustness research figures

This package contains 22 native vector research figures: 11 official retrieval tasks × R@1 and official trapezoidal mAP. The PowerPoint deliverable is `robustness_native_editable_22figures.pptx`; the vector-source ZIP is supplied separately. Each figure/page is 181.9 × 165 mm. The smallest figure text is 8 pt at that physical size. Resize without changing the aspect ratio; shrinking reduces the effective font size.

## Files and editing

- `native_svg/`: 22 SVGs with editable text and vector lines/markers; no raster images.
- `source_data/`: exact byte copies of the 22 adopted source CSVs, 60 rows each (1,320 plotted source rows). The adopted aggregate contains 3,960 rows; the other four metrics are not plotted here.
- `FIGURE_INDEX.json`: page/task/metric mapping, CSV and SVG hashes, clean values, captions and frozen severity parameters.
- `CAPTIONS.md`: complete captions, formula, units and limitations for every figure.
- `INPUT_PROVENANCE.json`: bound root adoption, original figure index/config and original/copy CSV descriptors.
- `previews/` in the local delivery directory: actual CPU renders of all 22 pages imported from the final PPTX. Previews are omitted from the source ZIP to avoid duplication.
- `code/` in the ZIP: the artifact-tool JavaScript producer, preserved two-page sample source, exact one-field filename-reporting diff and stdlib structural checker. The JavaScript binds the original workspace paths and needs the documented artifact-tool environment; it is reproducibility source, not a standalone installation bundle.

The PPTX contains 7,042 editable native shapes, including 2,102 text objects. Lines, axes and markers are individual objects with stable task/metric/element names. They are flat objects rather than grouped charts; there are no Excel chart workbooks or embedded chart images. Use the selection pane to select objects. The SVGs retain text and primitive IDs. No PowerPoint application was launched; the final PPTX was imported and rendered using artifact-tool on CPU.

## Meaning of the curves

The plotted vertical axis is **retained percentage = 100 × corrupted metric / the same variant's own clean metric**. It is not absolute accuracy and is not a percentage-point drop. Each plot visibly gives the Visual and Full absolute clean values to four decimal percentage places. Values above 100% are retained and are not clipped. Axes begin at zero; the maximum is shared by six panels within a figure but may differ between figures.

Severity 0 is a 100% clean reference only when that variant's clean metric is positive. A zero clean denominator would be undefined and left as a gap; all actual supplied clean denominators are positive. Severities 1–5 use the frozen parameter sequences in each caption, index and slide notes. Source metric fractions multiplied by 100 are percentages; `percentage_point_drop` is 100 × (clean fraction − corrupted fraction). Higher retention or a lower clean-to-corrupt drop does not imply higher absolute corrupted accuracy.

These are seed-1-only, descriptive, per-task curves. No pooling across tasks, conditions, severities, directions or heights, and no multi-seed SD, confidence interval or significance claim is made. Full evaluates clean CLIP evidence from cache and corrupted-query CLIP evidence online, so its curves include evidence-path changes as well as image corruption. The 64-sample clean diagnostic had no numerical equivalence gate and does not establish bitwise parity or negligible ranking effects.

## Source authority and limits

The numerical source is the root-adopted post-robustness result: `execution/pipeline_post_robustness_audit_20260929_1448/ROOT_POST_ROBUSTNESS_ADOPTION.json`, SHA-256 `f55b05559de3ca536170de4ea0be79988dd7c5cf0c822be5f3572eb31a57af0a`. This conversion changes no scientific source or result. Checkpoint/cache/image verification and historical evidence-chain limitations from the adopted upstream reports remain inherited; this task does not reread weights, images, caches or NPZs, recompute model inference/full rankings/AP, or complete efficiency experiments. Original scientific plots are retained in their original location.

All 22 final PPTX pages were actually rendered and visually inspected by the producer for labels, legends, axes, limits, clipping and overlap. The producer structural checker is not an independent review. An independent numerical/geometry/structure and visual review is stored separately under `execution/robustness_native_review_20260929_1650`; its final report bindings are in the delivery record. Root acceptance is a separate action.

## Build history

The requested two-page sample (pages 1 and 7) succeeded. Its report omitted the filename stem, resulting in sample preview filenames containing `undefined`; the exact executed sample source is retained. A single reporting-field addition supplied the stem before the first complete 22-page build. Data, formulas, layout and primitives did not change. The full build and the new bounded structural check each passed on their first execution. Old scientific/control suites were not rerun.
