# T5 selective-risk figures — final v2

Use only this `output_v2` delivery. Eleven task-specific figures show seeds 1, 2 and 3 in separate panels, with blue-circle Visual and orange-square Full series. All 66 native rows and all 660 saved native points are shown. These are **clean official-query** results, not image-corruption robustness results.

## Files

- `t5_selective_native_editable_11figures_v2.pptx`: an 11-page native editable figure deck, with no cover slide.
- `native_svg/`: 11 corresponding SVGs with editable text and geometric objects, no raster images.
- `source_data/transactions_t5_selective_calibration.json`: exact 744,943-byte adopted input JSON, containing native and paired records plus calibration fields.
- `source_data/transactions_t5_selective_comparisons.csv`: exact 20,814-byte adopted paired-comparison CSV. Its 132 comparisons, requested coverages 0.5/0.75/0.9/1.0, and inferential fields are preserved but not plotted.
- `source_data/NATIVE_POINTS_660.csv` and 11 per-task CSVs: direct flattening of saved native fields, without statistical recomputation. Counts, fractions, membership SHA references and saved all-prefix AURC are retained.
- `provenance/`: exact root adoption and capture metadata. `INPUT_PROVENANCE.json` binds the small input and output tables; no referenced large scientific files were read.
- `CAPTIONS.md`, `FIGURE_INDEX.json`: complete scope, caveats, file mapping and saved AURC values.
- `previews/`: actual CPU renders after importing the finalized v2 PPTX. The preview PNGs are omitted from the ZIP to avoid duplication.
- `code/` in the ZIP: the preserved executed v1 producer, final v2 producer, exact full source diff, revision record, bounded export checker and packaging source.

The ZIP `t5_native_editable_and_sources_v2.zip` includes final PPTX, SVGs, all small source tables/provenance, captions/index/README and source code. All members are read back and verified byte for byte.

## Coordinates and interpretation

Each native series contains the ten saved requested coverage levels 0.1 through 1.0 in steps of 0.1. The plot uses **realized coverage = selected_queries / N ×100** on the horizontal axis. The selected count is ceil(requested coverage × N), so actual coverage can differ from the nominal request. No nominal request is substituted for the stored actual fraction. The vertical axis is saved selective risk = 1 − R@1 among selected queries, multiplied by 100. Both axes span 0–100; zero risk, risks near 100%, and nonmonotonic values remain intact. No marker is invented at zero coverage.

Visual and Full independently select their own margin-ranked subsets. At equal coverage, selected memberships may differ. This risk plot describes accuracy conditional on each selected subset; it does not plot the separate paired coverage-constrained success statistic.

Selection ranks the raw cosine Top-1 minus Top-2 margin in descending order; ties preserve original query order. Margin is a ranking score, not a calibrated posterior probability. Markers are only the ten registered observations; the 594 connecting segments are visual guides and do not form an observed curve over all query-selection prefixes. Interpolated values or integrals from these segments are not claimed.

The 66 displayed **all-prefix AURC** numbers are saved upstream `AURC_discrete_all_prefixes` fractions, rounded to four decimals. They are not a trapezoidal area computed from the ten plotted points. Their full precision is retained in JSON and per-task CSV/slide notes. This conversion does not recompute AURC or query statistics.

Seeds, tasks, heights and retrieval directions remain separate. No pooling, mean/SD across seeds, confidence intervals, bootstrap intervals, p-values or significance annotations are shown. Calibration/ECE/reliability bins are retained in the original input JSON but are outside this figure scope. Paired 75% points are not inserted into the native ten-point curves.

## Physical size and editability

Every page/SVG is 181.9 × 135.113889 mm. The SVG viewBox uses physical points; final PPT XML text is at least 8 pt, with Arial 8/9/10 pt. Shrinking the figure reduces the effective font size. The PPTX contains 2,244 native shapes including 572 editable text objects, 660 data markers and 594 guide segments. Axes, labels, markers and lines are separate objects with stable task/seed/variant names. They are flat shapes, not grouped or Excel chart workbooks. No image/SVG substitute is embedded. PowerPoint was not opened; artifact-tool rendered on CPU.

## Authority and bounded verification

Root numerical adoption: `execution/pipeline_post_robustness_audit_20260929_1448/ROOT_POST_ROBUSTNESS_ADOPTION.json`, SHA-256 `f55b05559de3ca536170de4ea0be79988dd7c5cf0c822be5f3572eb31a57af0a`. Capture SHA-256: `473d5fba90c3fc0d044733ffb19e1f2955f08df96f89d4c643ad54d6ff15ca09`. Original T5 JSON SHA-256: `033b6eaea71b3084ca043902f6ba03b6487bf1762a9180963357103097d172cc`; original comparison CSV SHA-256: `2dc5b6bf9fba1edbde657427f516e0b539b310fb93f49511444a2061e598b40e`.

T5 query recomputation was performed upstream under the adopted bounded audit. This figure conversion reads only the small saved JSON/CSV and authority metadata. It does not read NPZs, caches, images or checkpoints, run scientific libraries/GPU/model inference, reconstruct full rankings/AP, repeat old controls, or resample bootstrap intervals. Saved-value limits, inherited checkpoint/cache/image SHA and historical evidence-chain gaps remain.

The first v1 build completed but its inter-panel gap allowed the next panel's 100% y-axis label to intrude on the previous street curve endpoint. V1's actual source, report and all outputs remain untouched at their original paths and are not deliverables. V2 changes only panel spacing (step155→158pt; plot width140→126pt) plus explicit v2 output/report paths. All 660 saved point values, 66 saved AURC values, captions and source CSV bytes were checked unchanged. V2 was rebuilt/rendered once because all 11 layouts were affected. This was a figure-layout correction, not a scientific failure.

The first bounded producer final export check passed 19,020 assertions and is distinct from independent review. All 11 final v2 imported-PPTX PNGs were actually inspected at original resolution by the producer; root also independently viewed all 11. The independent reviewer checks source JSON against actual SVG/PPT geometry and separately views every final PNG. Its report and later root artifact adoption are separately bound. No scientific queue, release, state, HANDOFF or automation was changed.
