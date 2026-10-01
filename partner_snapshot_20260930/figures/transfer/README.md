# Editable T3 transfer research figures

Two figures report the adopted cross-dataset transfer results: University-1652-trained models evaluated on the eight SUES-200 target tasks, and SUES-200-trained models evaluated on the three University-1652 target tasks. Both Visual and Full are shown for every task and every metric. The title gives training/evaluation dataset direction; the left column gives retrieval direction and target height. These are different concepts.

## Delivered files

- `transfer_university_to_sues_native_editable.pptx`: one page, 181.9 × 195.086111 mm, 16 task-variant groups and 48 metric summaries.
- `transfer_sues_to_university_native_editable.pptx`: one page, 181.9 × 113.947222 mm, 6 task-variant groups and 18 metric summaries.
- `native_svg/`: corresponding SVGs with editable text, mean markers, SD lines/caps, axes and labels; no raster images.
- `source_data/`: six exact adopted CSV/JSON files: three-seed summaries, all 66 individual seed-task rows, and task-specific Full-minus-Visual differences.
- `provenance/`: exact root adoption, original result delivery, analysis and source README.
- `FIGURE_INDEX.json`, `INPUT_PROVENANCE.json`, `CAPTIONS.md`: figure mapping, source hashes, exact values and complete captions.
- `previews/`: local PNGs actually rendered after importing each final PPTX. These preview duplicates are omitted from the ZIP.
- `code/` in the ZIP: JavaScript producer and stdlib package checker/packager. Reproduction requires the artifact-tool environment and the original bound workspace paths; this is not an installation bundle.

`transfer_native_editable_and_sources.zip` includes both small PPTX files, SVGs, exact tables, documentation/provenance and source code. Every ZIP member is read back and checked byte for byte against its source.

## Editing and physical size

The two PPTX files contain 485 native shapes, including 144 editable text objects. Each object has a stable direction/task/variant/metric name; mean markers and SD lines/caps remain separate editable objects. The objects are flat rather than grouped or native Excel chart workbooks. No figure image or SVG image is embedded in the slides. Arial is used throughout, with actual XML sizes of 8, 9 and 10 pt. The SVG coordinate system uses physical points, with a minimum of 8 pt at the supplied page dimensions. Shrinking a figure reduces its effective font size. All figures were built and rendered on CPU; Microsoft PowerPoint was not opened.

## Numbers, intervals and interpretation

All 22 task-variant groups and all 66 group-metric summaries appear in the figures. Every group weights seeds 1, 2 and 3 equally. Points show the adopted mean; horizontal bars and numerical ± values show **sample SD with denominator n−1=2**, not standard error, confidence intervals, or significance tests. All intervals are retained in full on axes starting at zero; each metric uses its own visible scale. A zero SD remains an actual zero SD. Numeric labels use three decimal places; original full-precision fractions and every seed value are preserved in the source tables and slide notes.

Both mean and SD are multiplied by 100 for display. R@1 and official trapezoidal mAP means are percentages; their SD values have corresponding percentage-point units. MRR ×100 is scaled mean reciprocal rank, not an accuracy percentage. mAP retains the frozen official trapezoidal AP definition. The included Full-minus-Visual table is descriptive: R@1/mAP differences ×100 are percentage points; MRR differences ×100 are scaled MRR points, not relative percentage gains.

No pooling across tasks, heights, directions, datasets or query counts is performed. Full has lower mean R@1 in all 11 tasks. Mean mAP and MRR are also lower except the small positive SUES→University street→satellite differences. The low absolute street results remain visible numerically. These observations establish neither statistical significance nor a mechanism or universal superiority.

## Authority and verification limits

The source authority is `execution/transfer_results_20260929/ROOT_AGGREGATION_ADOPTION.json`, SHA-256 `a8867a9ebdf01061a55d143b79eff91196571c2275f4379902131a69dd4ce80c`. The conversion reads only that adoption and its adopted small summary/provenance tables. It does not read or rehash the original run metrics, weights, caches, images or NPZs; run scientific libraries/GPU/model inference; or repeat any scientific experiment, full ranking, AP recomputation, old control suite or aggregation audit. Inherited checkpoint/cache/image SHA limitations and historical evidence-chain gaps remain.

Both finalized one-page PPTX files were actually imported and CPU-rendered by artifact-tool. The producer inspected both final PNGs at original resolution and found no clipping or label overlap. The producer's 4,147 structural checks compare exports with authored primitives and are distinct from the independent reviewer, which checks original summary values against actual SVG/PPT geometry and views the final images. Independent delivery and later root figure adoption are separately bound in the delivery record.

The two-page generation and the new bounded producer structural check each passed on first execution. No executed source revision or failed scientific attempt occurred in this figure conversion. Original scientific outputs and earlier figure deliverables remain unchanged. This figure delivery does not complete the remaining experiments, final manuscript or Overleaf delivery.
