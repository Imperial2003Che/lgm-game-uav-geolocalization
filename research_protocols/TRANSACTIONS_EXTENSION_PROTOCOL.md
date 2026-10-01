# Transactions-Scale Extension Experiment Protocol

Status: revision 9; T1 dual-dataset evaluator complete; execution gates pending  
Revision date: 2026-07-30  
Primary protocol: `FORMAL_EXPERIMENT_PROTOCOL.md`

## 1. Purpose

This addendum expands the evidence workload toward a top IEEE Transactions
study without changing the already frozen 36-run main matrix or six-run
sensitivity matrix. It adds strong published-method reproductions,
out-of-domain evaluation, altitude generalization, failure-mode stratification,
selective-retrieval analysis, and deployment cost measurements.

The extension is a separate experimental family. Results from this family must
not be merged into the primary matrix or presented as if they were selected
before the primary protocol was frozen.

## 2. Non-negotiable controls

1. Every training run uses a pre-specified final epoch. No official test metric
   may select a checkpoint, hyperparameter, random seed, or method.
2. Every reported test uses all official queries. Sampled-query results are
   diagnostic only and cannot enter the manuscript.
3. Training, official evaluation, and statistical aggregation are separate
   stages with immutable manifests and SHA-256 records.
4. Interrupted runs resume only when the upstream framework exposes a complete
   optimizer, scheduler, scaler, RNG, and model checkpoint. When it exposes
   model-only state, the failed attempt is preserved and the registered fit is
   restarted from epoch zero. A run with inconsistent artifacts is rejected
   rather than overwritten.
5. Published numbers, public checkpoints, and locally trained results remain
   separate columns. A quoted number cannot substitute for a local run.
6. Any required memory adaptation must preserve the effective optimizer batch
   size through gradient accumulation and be disclosed. Batch-local mining is
   still performed within each micro-batch, so such a fit is called a
   resource-adapted official-code reproduction, not an exact training-recipe
   reproduction.
7. Third-party source snapshots, licenses, revisions, local compatibility
   patches, commands, environments, and output hashes are recorded.
8. No extension result enters the paper until its block has status `complete`.

## 3. Formally published method anchors

The extension targets methods with completed journal records:

| Method | Publication | DOI | Role |
|---|---|---|---|
| QDFL | IEEE Transactions on Geoscience and Remote Sensing, 2025 | `10.1109/TGRS.2025.3558924` | modern query-driven DINOv2 baseline |
| MCCG | IEEE Transactions on Circuits and Systems for Video Technology, 2024 | `10.1109/TCSVT.2023.3296074` | complete ConvNeXt multi-classifier baseline |
| SHAA | IEEE Transactions on Circuits and Systems for Video Technology, 2025 | `10.1109/TCSVT.2025.3560637` | literature context; official repository incomplete |
| EAGLe | IEEE Transactions on Geoscience and Remote Sensing, 2025 | `10.1109/TGRS.2025.3582619` | robustness design context |
| CDM-Net | IEEE Transactions on Geoscience and Remote Sensing, 2025 | `10.1109/TGRS.2025.3594544` | multimodal design context |
| VLGeo | IEEE Transactions on Geoscience and Remote Sensing, 2026 | `10.1109/TGRS.2026.3680280` | vision-language design context |

Only methods with executable public code and a compatible protocol are locally
trained as baselines. A method used only as design context is not assigned a
fabricated local score.

## 4. Extension block T1: published-method local training

All T1 runs train on the official University-1652 training identities and the
same 41,214 images from the `satellite`, `street`, and `drone` views. The 8,977
auxiliary `google` images are excluded and the fitting content must match
SHA-256 `61852ee531d095ae4fd7507c12555fe9cac130df84a1308cacf00b2ca97bf3a6`.
The fitting adapters receive no University-1652 or SUES-200 test root.
Before any T1 fit, engineering registration may enumerate path names, byte
sizes, and the fixed SUES-200 identity manifest solely to lock task scale; it
does not decode an image, construct a model, extract a descriptor, or compute
a test outcome. Reading image bytes inside the registered runner is blocked
until all T1 fits are complete.

| Family | Backbone/configuration | Epochs | Seeds | Full fits |
|---|---|---:|---|---:|
| QDFL | DINOv2 ViT-B/14 + QDFL official configuration | 160 | 1, 2, 3 | 3 |
| FSRA | ViT-FSRA official configuration | 120 | 1 | 1 |
| SDPL | SwinV2-B + SDPL official configuration | 160 | 1 | 1 |
| CCR | ConvNeXt-B + CCR official configuration | 200 | 1 | 1 |
| MCCG | ConvNeXt-Tiny + MCCG official configuration | 200 | 1 | 1 |

Total T1 training workload: seven complete fits.

Before the first T1 fit, the following external execution inputs must be
locked in the extension ledger:

- QDFL upstream commit `627296d5...`, compatibility patch plan
  `207fad544d5872ef41b4df8707982b99d712834127f3eea2242294550a021064`,
  and 108-file patched-tree SHA-256
  `99cd2ffe01f5e4faac28dd216a342674c90d08eaf529066f4954c5cf86ab06a3`;
- MCCG upstream commit `e1c51b01...`, compatibility patch plan
  `a7e40504f5fd3c154be23bb61aabc5e37e8311b036c27d8d6b3d44f34e1fcf69`,
  and 54-file patched-tree SHA-256
  `b196be3713b583daa69880952d1289e24ccdccc41e1afa998cb518266da8ccde`;
- all five initialization byte counts and SHA-256 values in
  `external_baselines/transactions_weight_registry.json`;
- the QDFL and MCCG adapter hashes, separate dependency-environment
  fingerprints, registered commands, and CUDA device identity.

The completed preflight pins the following local artifacts before any T1
training:

- source registry SHA-256
  `42445581a454a514f48de017ca6656059715fc3f83c58af4026adc85d9505e5a`;
- initialization registry SHA-256
  `4a01bd968118de1609b1653e3d2b3c4ba915b9ca808044880c44dd1993149f23`;
- QDFL adapter SHA-256
  `bb2b294853bb0450a7c8348abfd40f1ade820b63327ab2d8b4195b29d798d65b`;
- MCCG adapter SHA-256
  `2c928bdf226cda61a006211e3b2ddc29006904cb09bd4bd608633924a4af83d5`;
- environment-lock file SHA-256
  `3c2b176e8c1bd706e0afa0f9f0bd62d73669549e47f16b2f1338ce05a4e8a087`
  and payload SHA-256
  `54bf50de942ee9759f262a0b3fd9173a37752451f10ee0ed5529d9ab101beef6`.

Revision 9 also locks the executable T1 evaluation surface:

- seven-fit matrix SHA-256
  `430475beeef2c81efd613c4fa61c2ea307583e63e398774cb5c94221d648d8dd`;
- serialized train/evaluate runner SHA-256
  `865c8bdd61693007a3f73ce672408767617f4855228aaee2e3a5ef2310079cd7`;
- shared descriptor evaluator SHA-256
  `a2667a5ef803ce49c2d92f2b0c98f03185766f84fd673b02c3a409a5b51d0b7d`;
- QDFL-family official evaluator SHA-256
  `b313dadd8770b28e83be79e9ea35cad599840abc1de6cb10b64e1ff029677151`;
- MCCG official evaluator SHA-256
  `5f09ca925a76c544bd78884b234d47158764c3c41b756914d7358d95a35cc771`.

The final read-only adapter preflights independently reproduced the registered
41,214-file, 2,670,030,871-byte fitting inventory and content SHA-256
`61852ee531d095ae4fd7507c12555fe9cac130df84a1308cacf00b2ca97bf3a6`.
They also verified the patched source trees, the method-specific
initialization files, CUDA availability, and the absence of official-test
roots. These preflights are readiness checks, not experimental results.

The separate pre-fit test-protocol registration enumerated 131,062 path/size
rows and the fixed SUES-200 120/80 manifest without decoding images or running
a model. One engineering timing attempt to compute a complete test content
digest was terminated before producing a digest and created no result
artifact. It did not extract features, calculate a metric, or influence a
configuration. The only admissible complete content freeze is created by the
registered runner after the all-seven-fits gate.

The QDFL Windows environment explicitly selects the standard-PyTorch attention
fallback already present in the upstream DINOv2 implementation because the
repository-pinned xFormers build targets torch 2.1 and is ABI-incompatible with
the frozen Windows torch runtime. This compatibility choice and every
micro-batch setting are recorded per fit.

The initially considered SHAA fit was replaced before any T1 training began.
The pinned SHAA repository contains only seven files and omits the
`datasets`, `losses`, `models`, and `optimizers` trees imported by its training
entry point. Treating that snapshot as executable would be misleading. MCCG
has a complete official training tree and a completed Transactions record, so
it occupies the unchanged seventh-fit budget. SHAA remains a cited literature
comparison without a fabricated local score.

Evaluation is registered as ten complete retrieval tasks for every one of the
seven locally fitted models:

- University-1652 D2S uses all 37,855 query-drone images against all 951
  gallery-satellite images.
- University-1652 S2D uses all 701 query-satellite images against all 51,355
  gallery-drone images.
- SUES-200 zero-shot transfer uses the fixed 80 test identities as eligible
  queries and retains all 200 identities in each gallery. At each of 150, 200,
  250, and 300 m, UAV-to-satellite has 4,000 queries and 200 gallery images,
  while satellite-to-UAV has 80 queries and 10,000 gallery images. No
  SUES-200 image, label, metric, or threshold is used for T1 fitting,
  checkpoint selection, or configuration selection.

This yields `7 x (2 + 8) = 70` full task evaluations: 14 on University-1652
and 56 zero-shot transfer tasks on SUES-200. Street2S is explicitly
unsupported for this T1 comparison because the pinned public QDFL-framework
and MCCG evaluation entry points implement only D2S and S2D. It is omitted, not
serialized as zero and not inferred from another method.

Every evaluation uses the method's registered image size: QDFL 280,
FSRA 256, SDPL 256, CCR 384, and MCCG 256 pixels square. Horizontal-flip
augmentation reproduces the corresponding public extractor. QDFL-framework
descriptors use float32 squared-L2 ranking; MCCG uses float32 inner-product
ranking. Ties preserve the frozen gallery order. Results retain
Recall@1/5/10/20, official trapezoidal mAP, MRR, top-1 margin, descriptor
fingerprints, and complete per-query arrays.

Official-test access is fail-closed. After every final-epoch fit validator
passes, the runner first writes an immutable all-seven-fits gate. Only then
does it read and content-hash the two test datasets. The registered path/size
inventory contains:

| Dataset | Images | Bytes | Path/size membership SHA-256 |
|---|---:|---:|---|
| University-1652 test | 90,862 | 5,704,769,123 | `19c26d413c79b77785ca05c02962ed30135c9e2c43a712a3db52c8dda59ff6b7` |
| SUES-200 | 40,200 | 5,693,433,493 | `dc6742e45599231b53f16730771cb5eab45d5b0ef6aed8d1663324207a15f706` |
| Combined | 131,062 | 11,398,202,616 | recorded as the two ordered dataset inventories |

The post-fit gate freezes full content hashes as well as these path/size
memberships. Each evaluation recomputes both inventories and must match the
gate exactly. Feature extraction is serialized by task pair and altitude so
that completed full-data evaluation does not depend on holding both datasets'
descriptors in memory at once.

A public trained QDFL checkpoint is not used as a substitute for any local
fit. If a separately licensed and hash-verified trained release is evaluated,
it must appear as an additional checkpoint-reproduction row outside the
registered 70 task evaluations.

## 5. Extension block T2: altitude-held-out generalization

For SUES-200, each UAV height is held out from fitting in turn. Satellite
training images remain available; UAV training images from the held-out height
are excluded. Evaluation is performed only after all T2 fitting is complete.

| Factor | Values |
|---|---|
| Held-out height | 150, 200, 250, 300 m |
| Variant | `visual`, `full` |
| Seed | 1, 2, 3 |
| Training schedule | the same fixed 80 epochs as the primary protocol |
| Checkpoint | pre-specified final epoch |

Total T2 training workload: 4 heights x 2 variants x 3 seeds = 24 complete
fits. Results are reported separately for the held-out height and for the three
seen heights. The primary all-height SUES matrix remains the main in-domain
result.

The T2 adapter leaves the frozen primary training file unchanged. It filters
the protocol-derived training records before model construction, records the
included and excluded path-set hashes, and embeds the held-out-altitude
membership hash in the full final checkpoint. The static design audit is
explicitly marked as non-result evidence and does not construct a model or
execute an optimizer step. It registered the following content inventories:

| Held-out height | Fit identities | UAV fit images | Satellite fit images | Excluded held-out UAV images | Training files | Training bytes | Content SHA-256 |
|---:|---:|---:|---:|---:|---:|---:|---|
| 150 m | 120 | 18,000 | 120 | 6,000 | 18,120 | 2,553,922,754 | `1bdf68640ec01621108e315d5ae558113c3d0454106985083ee7973c2c3e7099` |
| 200 m | 120 | 18,000 | 120 | 6,000 | 18,120 | 2,565,020,379 | `669022d8d8cc731ec50925421a330cb095a41158f1f1e98710206382f6fbaa8a` |
| 250 m | 120 | 18,000 | 120 | 6,000 | 18,120 | 2,569,665,447 | `76116b879c59771dcda204d470b3ab9e9469d0331155f3a48ec2766e4078f883` |
| 300 m | 120 | 18,000 | 120 | 6,000 | 18,120 | 2,574,942,224 | `6e69c44af8ef546c42046f0ca977572e0685c2776b77a357d28a675cf0ef772f` |

The 24-row T2 matrix SHA-256 at this audit is
`85d7f195cf80c5ba948931060c6e9d6349abbb42e6f9d5c13f3f373f9deaf958`.
The catalog contains 24,120 official-training files with catalog SHA-256
`eabad2dc86b98a1b2629714f2c8eb39adea0a467cd8a049d9c362d0159940537`.
These readiness hashes are recomputed and ledger-locked after the primary
42-fit gate passes and before the first T2 model starts.

## 6. Extension block T3: bidirectional cross-dataset transfer

No new fitting is performed in T3.

- University-1652-trained `visual` and `full` checkpoints, seeds 1--3, are
  evaluated zero-shot on all eight SUES-200 tasks.
- SUES-200-trained `visual` and `full` checkpoints, seeds 1--3, are evaluated
  zero-shot on University-1652 D2S, S2D, and Street2S.

Total T3 workload: 12 checkpoint-transfer evaluations. Target-dataset labels
are used only by the evaluator, never by the encoder or a calibration step.

The registered T3 matrix is the exact Cartesian product of two transfer
directions, two source variants, and three seeds. Each source must be a
complete primary 80-epoch checkpoint with identical `best.pt` and `last.pt`
files and no official-test access during fitting. Evaluation is blocked until
all 12 source checkpoints pass that completion gate. The target dataset is
never used for fitting, checkpoint selection, threshold selection, or
calibration.

The T3 adapter evaluates every official query against the complete official
gallery and stores query paths, labels, top-1 gallery identities, correctness,
top-1 margins, per-query official trapezoidal AP, and reciprocal ranks. The
completion validator independently recomputes Recall@1/5/10/20,
`mAP_trap`, MRR, and mean margin from those arrays, verifies the semantic
agreement of Top-1 labels, correctness, and reciprocal ranks, and checks that
the CSV and JSON metrics agree exactly.

The non-result static audit registered:

- 12 transfer rows; matrix SHA-256
  `4608df2075ab1bfd4f38c949935a4e0c2ca6516c9716b87376f39b1b951d4bf3`;
- University-1652 target protocol: three tasks, membership SHA-256
  `c271b8b342a9642a8ee7bd767ace06f9d934cd58a4c83885d51db2e7b94221df`;
- SUES-200 target protocol: eight tasks, membership SHA-256
  `1f543fb48416204dacfb5ac48b3bbf3ce4080ce164e75e7a86be748e3d798772`;
- University-1652 evidence/cache metadata SHA-256 values
  `8a2333d58dbb0ca56c5d5829159a32f294e11e686bb6b91d05098d4b170c2bc3`
  and
  `3731072d3a1c8a3b9fe8d880fd791dfbe7eb82f2d93be85b82be229ff8512dbf`;
- SUES-200 evidence/cache metadata SHA-256 values
  `6c3a82fdcf59e401f5da4ed0f3d9dca99fdcbab0a46aa66fb47a055c832cdabd`
  and
  `3dc42892bbff9339d058fc0d6abaf2fd9e92cc94f9f9b7fd58ed0ae725b57dca`;
- cross-dataset adapter SHA-256
  `29cccd4ff3e975571b578288f7a691ceccaf4a8ed7ab9483812b68edbc4f5ed8`;
- T3 matrix runner SHA-256
  `50e681a17bd21188ec059112a77653e04f0cd716a95f4e1c0dfbb486375cc84c`.

The persisted static audit is
`lgm_game_pytorch/audits/transactions_t3_static_audit.json`. It must retain
`manuscript_result=false`, `model_constructed=false`, and
`evaluation_executed=false`; it is readiness evidence and cannot be cited as
an experimental outcome.

## 7. Extension block T4: semantic evidence and failure strata

T4 reuses complete per-query outputs and frozen CLIP probabilities. It does not
fit a model.

Each official task is stratified before inspecting retrieval correctness by:

1. geographic-content entropy quartile;
2. acquisition-style entropy quartile;
3. agreement between visual and semantic nearest-neighbour identities;
4. clean top-1 margin quartile;
5. corruption family and severity for the robustness subset.

For every stratum, report query count, Recall@1, `mAP_trap`, MRR, and the
full-minus-visual paired difference. No stratum with fewer than 100 queries is
used for a performance claim; it is retained in source data with a warning.

The clean-query strata are fixed before execution as follows:

- content and style uncertainty are normalized Shannon entropies
  `-sum(p log p) / log(K)` over the registered 11-way content and 10-way style
  probability vectors;
- quartile cutpoints use linear 25%, 50%, and 75% quantiles within each
  official task; a value equal to a cutpoint enters the lower interval;
- the semantic-only nearest neighbour uses cosine similarity between
  concatenated content/style blocks after each block is L2-normalized, giving
  the two semantic blocks equal weight; ties follow the frozen gallery order;
- the clean-margin quartiles are anchored to the `visual` model for the same
  task and seed, so `visual` and `full` are compared on identical strata;
- visual--semantic agreement compares the visual Top-1 identity with that
  semantic-only Top-1 identity and does not inspect retrieval correctness.

Across 11 official tasks and three seeds, the clean design expands to exactly
`11 x 3 x (4 + 4 + 4 + 2) = 462` retained stratum rows. Eligible rows use
10,000 paired query bootstrap resamples for 95% confidence intervals and the
two-sided exact McNemar test for Recall@1. Holm correction is applied once
across all eligible T4 stratum Recall@1 comparisons. Rows below 100 queries
retain descriptive point estimates but withhold confidence intervals,
hypothesis tests, and performance claims.

Corruption-family/severity strata are generated separately from the completed
full-query robustness manifests and are not imputed by the clean-query runner.
The clean T4/T5 primitive and runner SHA-256 values are respectively
`4cf500c09aef5f81c192e0975b024aea1da7c90bfba2c3a70b99632574608221`
and
`0592c3c1859d38b3cea542d6a5afd8e27bc2b5836dcc83103f4f239db363f561`.
They are implementation evidence only until the 12 complete source-evaluation
gate passes.

## 8. Extension block T5: selective retrieval and calibration

For every complete official task and seed:

- confidence is the cosine top-1 margin, fixed before outcome inspection;
- report risk--coverage curves at 10% coverage increments;
- report area under the risk--coverage curve;
- report top-1 expected calibration error with fixed 15 equal-width bins;
- report selective Recall@1 at 50%, 75%, 90%, and 100% coverage;
- compare `visual` and `full` on identical query order.

Calibration plots are descriptive. No test-set threshold is transferred back
into training or used to alter the headline full-coverage metrics.

Native selective curves rank queries by decreasing raw cosine Top-1 margin
with stable official-query-order tie breaking. The discrete AURC is the mean
cumulative risk over every non-empty prefix. Requested coverage uses
`ceil(coverage x query_count)` and records the realized coverage.

For the 15-bin diagnostic, the theoretical cosine-margin range `[0, 2]` is
mapped without fitting to
`confidence_fixed = clip((top1 - top2) / 2, 0, 1)`. This quantity is reported
as fixed-margin `ECE`, not as a learned probability calibration. Empty bins
are retained.

The runner produces 66 native rows
(`11 tasks x 3 seeds x 2 variants`) and 132 pre-registered paired coverage
comparisons (`11 x 3 x {50%, 75%, 90%, 100%}`). Because the two variants may
select different queries at the same coverage, the exact paired test uses the
coverage-constrained binary outcome `selected AND Top-1-correct` over the
common complete query set. Conditional selective Recall@1 and selected-set
overlap are reported separately. Holm correction is applied once across the
132 coverage-constrained comparisons.

## 9. Extension block T6: efficiency and scaling

Measure each locally trained method on the same RTX 4060 Laptop GPU:

- trainable and total parameters;
- multiply--accumulate operations for one query image;
- peak allocated GPU memory;
- median and interquartile-range encoding latency over at least 100 timed
  repetitions after 20 warm-up repetitions;
- descriptor dimension and stored bytes per image;
- full-gallery ranking latency and throughput;
- Recall@1 and `mAP_trap` versus gallery size using the fixed
  positive-preserving negative subsets from the primary protocol.

Timing runs are serialized. Background GPU jobs are prohibited.

The primary-model T6 component is pre-registered for the seed-1 `visual` and
`full` checkpoints on both datasets. It is blocked until all four training and
official-evaluation manifests are complete and valid. Its completed component
manifest must retain `manuscript_result=false` and `full_t6_complete=false`
until the locally trained T1 baseline rows have been measured on the same GPU
and a combined T6 audit is complete.

The primary component uses:

- one fixed real official query per model for batch-1 online encoding;
- CUDA AMP, 20 warm-up repetitions, and 100 CUDA-event timed encoding
  repetitions;
- model-resident batch-1 peak allocated and reserved GPU memory;
- exact total/trainable parameter counts;
- Conv2d/Linear multiply--accumulate counts, with normalization, activation,
  pooling, elementwise fusion, and descriptor normalization explicitly listed
  as excluded operations;
- float32 complete cosine-score construction followed by stable full argsort,
  with 5 warm-up and 20 timed ranking repetitions per official task;
- descriptor dimension and float32 storage bytes per image.

Gallery scaling uses seed `20260727`, retains every positive, and adds negatives
in the existing BLAKE2b path-hash order. Requested sizes are
100, 250, 500, 1,000, 5,000, and 10,000 when smaller than the task gallery,
followed by the complete gallery. Equal-score ties preserve the frozen gallery
order. Every recomputed complete-gallery Recall@1/5/10/20, `mAP_trap`, and MRR
must reproduce the completed official evaluation before any scaling row is
accepted.

The T6 primitive and primary-component runner SHA-256 values are respectively
`e5704eb5f8681d7a73386c9b787f68e4f6638703c547a8e671e803b319a99853`
and
`063a2c2a7bddfc4fd4b4063683f6147dc8cab24b54deaf4d3095abb7e14f8615`.
No T6 timing or scaling result currently exists.

## 10. Statistics

1. Three-seed results use mean and sample standard deviation.
2. Query-paired differences use 10,000 bootstrap resamples with a fixed seed.
3. Top-1 correctness uses the two-sided exact McNemar test.
4. Holm correction is applied once within each declared comparison family:
   T1 published baselines, T2 held-out heights, T3 transfer tasks, T4 strata,
   and T5 coverage points.
5. Effect sizes and confidence intervals are reported with adjusted
   probabilities. Numerical underflow is serialized as a bound, never zero.
6. Query paths and labels must match exactly before a paired test is allowed.

## 11. Workload accounting

The complete training workload becomes:

- primary matrix: 36 fits;
- primary sensitivity: 6 fits;
- published-method extension T1: 7 fits;
- altitude-held-out extension T2: 24 fits.

Total: 73 complete model fits, plus 12 cross-dataset transfer evaluations,
70 T1 full-query task evaluations, full-query image robustness at six
corruption families and five severities, exact public-baseline reproduction,
semantic/failure stratification, selective retrieval, and efficiency scaling.

This count describes executed work only after every corresponding manifest is
complete. Planned, failed, interrupted, debug, and feasibility runs are listed
separately and are excluded from the count.

## 12. Freeze and manuscript gate

Before the first T1 or T2 fit starts, the extension runner, compatibility
adapters, external-source registry, and this protocol are SHA-256 locked in an
append-only ledger. After that point, a change to any locked item requires a
new extension version and rerunning every affected fit.

Generated manuscript tables and figures must verify:

- complete block status;
- expected run/evaluation counts;
- source and code hashes;
- per-query array hashes;
- absence of official-test use during fitting;
- exact agreement between aggregate metrics and recomputed query arrays.
