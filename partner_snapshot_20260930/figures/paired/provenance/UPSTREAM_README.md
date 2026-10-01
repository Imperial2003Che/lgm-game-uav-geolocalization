# Independent bounded review of post-robustness outputs

The joint review consists of the unchanged `REVIEW.json` and
`adopted_inputs_v2/RECONCILIATION.json`. The main review was conditional on the
fourth run's root adoption. The annex was executed only after the root adopted
SUES Full with SHA `abe0d740103c44792f134ac69816030e40947170f2c245c0e6e37efda0190596`.
It resolves that specific input-adoption condition; root acceptance of this
joint package remains a separate decision.

## Actual work and provenance

`capture_once.py` executed once, preserving 184 inputs with their original path,
snapshot path, SHA-256 and size in `a1/CAPTURE.json`. These include the newly
completed aggregate/query trees, frozen source/configuration and logs, and 66
explicitly authorized, previously adopted official per-query NPZ files. Their
original path/SHA/size were found in the explicit inherited root adoption chain.
Six authority metadata nodes were read; `REVIEW.json` separately records any
extra metadata snapshots. No checkpoint, cache or image bytes were read.

`review_post.py` first execution exited 0: 219,452 assertions and 49,292 numeric
comparisons. It imports only Python's standard library and executes no producer
or scientific module. Its source and passed report were not subsequently edited
or rerun. The main audit found all 66 input bindings, no missing bindings and all
12 official run identifiers accepted. The annex additionally makes these three
facts a mandatory admission condition rather than a diagnostic-only return.

The annex first version rejected before numerical source reconciliation because
it directly indexed a resolved producer path against the root's existing junction
alias path. Its source, stdout/stderr and partial `adopted_inputs/` are retained.
The final v2 uses two exact fixed absolute paths and `os.path.samefile` for each
of the four manifests; equal contents in different files are not accepted. This
identity check is not a current-content hash. Actual numerical bytes are read
from the SHA-bound, root-adopted sealed snapshots. The first v2 generator used a
non-raw Python string and produced Windows-path control characters. That source
was inspected before execution and never run; all four preparation files remain
under `annex_v2_preexecution_invalid/`. The raw-string correction preceded v2's
first and only execution, which exited 0. The complete v1-to-final-v2 diff is
`ANNEX_V2_FROM_REJECTED_V1.patch`; `ANNEX_PREPARATION_REJECTION.json` records both
preparation events. Neither event is a scientific failure.

The successful annex made 131,538 assertions over 141 explicit input bindings:
the main report/capture, three captured aggregate files, four root reports, four
run manifests, four run configurations and 124 metrics JSON files. The original
and sealed manifest descriptors are matched through the same-file alias proof.
All 22 clean task records and all 660 corrupted task records, including every
metric/degradation dictionary field, exactly equal the four adopted run inputs.
All 3,960 CSV rows' source identifiers, task scales and corruption parameters
match those adopted sources. It does not rerun the main review or reopen NPZ.

## Aggregate scope and figure limitations

The aggregate contains four seed-1 runs (University/SUES, Visual/Full), 22 run-task
combinations, six corruption families with five severities, and six metrics:
3,960 flat source rows. The main audit checked complete unique keys, nested JSON
versus CSV values, arithmetic for clean-minus-corrupt drops, relative drops and
retention, all 94 manifest artifacts' actual SHA/size, 22 figure source CSVs and
both LaTeX tables. All task/direction/height/condition/severity results stay
separate. There is no pooled accuracy, multi-seed SD or significance claim.

The 22 SVGs contain native text and no raster image nodes. Plot coordinates,
rendered geometry and page layout were not independently reviewed. Their source
uses 6- and 7-point text, below the intended 8-point final-paper minimum. They
are bound producer figures, not final editable paper/PPT/Visio delivery.

For Full, clean query/gallery CLIP evidence is cached whereas corrupted queries
use online CLIP. These comparisons include both pixel corruption and evidence
path differences. The 64-sample diagnostic has no numerical tolerance gate; it
does not establish bitwise/cache-online parity or negligible ranking effects.
Small drops or high retention do not imply high absolute corrupted accuracy.

## Query-analysis scope

T4 has 462 strata records; T5 has 66 native records and 132 paired coverage
records for 33 task-seed pairs. Frozen keys, CSV/JSON serialization, manifest
hashes/configuration/source bindings, thresholds and missing-value rules were
checked. All 66 stored NPZ files were actually decoded by a typed stdlib reader.
The audit verifies exact NPZ field sets, shapes, finite values, unique normalized
query paths, path/label alignment and correctness consistency.

For all 66 native T5 records, the audit independently computes the stable
descending-margin ordering after Full is aligned to Visual order, all-prefix
risk AURC, exact ceil coverage sizes, membership digests, accuracy/risk, and the
15 fixed bins for margin/2 confidence calibration and ECE. For all 132 paired
coverage records it recomputes selected sets, overlap, selected-and-correct
utility, discordance counts, differences, McNemar and the declared Holm family.

For the 132 T4 visual-margin strata it independently computes linear quartile
thresholds, lower-interval boundary ties, membership digests, counts, saved-value
R@1/mAP/MRR means and correctness discordances. For the other 330 T4
entropy/semantic strata it checks the stored aggregate summaries, arithmetic,
CSV agreement, eligibility and declared inferential-family bookkeeping. It does
not recompute those memberships or summaries because no cache bytes are read.
The 284 eligible T4 Holm-family McNemar probabilities are independently evaluated
from saved discordance counts, but only visual-margin strata have a fresh query
recount. The other counts retain producer-level evidence.

No bootstrap resampling is performed. Confidence intervals remain producer
values; only eligibility, nulls and finite bound ordering are checked. They are
not independently validated inference. Exact binomial integer sums replace the
producer's lgamma/logsumexp evaluation, with log10 agreement tolerance 2e-8.
Ordinary means/AURC/ECE use scalar binary64 `math.fsum` within 2e-12. These are
numerical agreement checks, not bitwise NumPy reductions.

Stored AP/RR/margin values are accepted inputs; the audit does not recompute
models, full rankings or all-positive-rank AP. Current checkpoint/cache/image
bytes and historical metadata-chain gaps remain inherited from the named prior
adoptions. `manuscript_result` in a producer manifest is not independent final
paper acceptance. Original stage-parent exit 0 is retained as a source event,
not an independently captured launcher/interpreter dual-handle exit proof.

All work is read-only against scientific inputs. No live state, source, queue,
release, recovery, HANDOFF or automation is changed; no prior science suite was
rerun. Initial anticipated counts were corrected to the actual frozen source
before the first audit execution and are not scientific failures. This package
does not establish T6 completion or resolve its separate GPU admission failure.
