# Formal Experiment Protocol

Status: frozen before the first new formal training run  
Freeze date: 2026-07-27 (Asia/Shanghai)  
Scope: `LGM-GAME-Partner-Delivery-20260724` only

## Integrity constraints

- Only complete, locally executed runs on the real University-1652 and
  SUES-200 images may support manuscript claims.
- Debug, smoke, quick, toy, synthetic-score, and pair-conditioned prompt
  outputs are excluded from paper evidence.
- The official test sets are never evaluated during training or model
  selection. No reported checkpoint is selected by a test metric.
- CLIP evidence is generated independently for each image from pixels and a
  fixed class-agnostic vocabulary. Class IDs, labels, positive matches, and
  image pairs are not model inputs.
- Every evidence cache must pass a 100% coverage gate, contain zero failed,
  missing, or extra images, and match its declared SHA-256.
- A failed run is retained in the ledger. It may be resumed from its exact
  `last.pt`, but it is never silently removed because of an unfavorable
  result.

## Fixed data protocols

### University-1652

- Training identities: all 701 official training identities.
- Training query views: all official training drone and street images.
- Positive gallery view: the same-identity official training satellite image.
- Test tasks, evaluated only after fitting:
  - drone to satellite: all 37,855 queries, all 951 gallery images;
  - satellite to drone: all 701 queries, all 51,355 gallery images;
  - street to satellite: all official query and gallery images.

### SUES-200

- Identity split: the official fixed 120-train/80-test manifest distributed by
  the SUES-200 benchmark. Random identity splitting is prohibited.
- Training query views: all 24,000 UAV images belonging to the 120 training
  identities across 150, 200, 250, and 300 m.
- Positive gallery view: the same-identity satellite image.
- Test tasks: four altitudes in both directions. Queries use the 80 test
  identities; every gallery retains all 200 identities as prescribed by the
  benchmark.

## Frozen main training matrix

- Datasets: University-1652 and SUES-200.
- Variants:
  - `visual`
  - `content`
  - `style`
  - `visual_content`
  - `visual_style`
  - `full`
- Random seeds: 1, 2, and 3 for every dataset/variant combination.
- Main backbone: torchvision ResNet-18 initialized from
  `ResNet18_Weights.IMAGENET1K_V1`.
- Epochs: exactly 80.
- Validation fraction: 0.
- Early stopping: disabled.
- Every official training query is used at least once per epoch:
  `samples_per_class_per_epoch=0` and `steps_per_epoch=0`.
- Batch construction: 16 identities × 4 query instances per identity
  (64 query/satellite pairs per optimizer step).
- Image input: resize 256, crop 224.
- Embedding dimension: 512.
- Dropout: 0.20.
- AdamW learning rate: \(3\times10^{-4}\).
- Visual-backbone learning-rate multiplier: 0.10.
- Weight decay: \(10^{-4}\).
- Warm-up: 5 epochs, followed by cosine decay.
- Gradient-norm clipping: 5.0.
- Mixed precision: CUDA FP16 AMP.
- Positive satellite selection is deterministic from dataset path, epoch, and
  seed. Multi-positive symmetric InfoNCE is the sole training objective.

This gives 36 independently trained main runs. Hyperparameters are fixed
across variants; they will not be retuned after seeing official test results.

## Frozen sensitivity runs

- `full`, ResNet-50, seed 1, both datasets, otherwise identical settings.
- `full`, ResNet-18, seed 1, embedding dimensions 256 and 1024, both datasets,
  otherwise identical settings.

These six training runs are reported separately from the 36-run main matrix.

## Evaluation and statistics

- Each final checkpoint is evaluated once on every official full-query,
  full-gallery task for its dataset.
- Primary metrics: Recall@1/5/10/20 and the official trapezoidal mAP.
- Secondary diagnostic metrics: standard precision-at-positive AP, MRR, rank,
  top-1 margin, parameter count, FLOPs, peak memory, offline evidence time,
  online encoding time, and exact ranking time.
- The official public LPN/CA-HRS evaluator uses per-query CUDA float32
  `gallery @ query` scoring. Reproduced public-baseline tables use that exact
  operation and record the score backend.
- Main model results are summarized as mean ± sample standard deviation over
  the three frozen seeds, task by task. Aggregate scores only combine mutually
  exclusive tasks; an overall SUES row is never averaged together with its
  altitude subsets.
- Pairwise uncertainty uses 10,000 query-paired bootstrap samples.
- Top-1 comparisons use two-sided exact McNemar tests with Holm family-wise
  correction. Underflowed probabilities are reported as bounds, never as
  exact zero.

## Frozen image-level robustness matrix

After the seed-1 `visual` and `full` checkpoints are trained, the query images
are re-encoded from pixels while galleries remain clean. The following six
corruptions use five fixed severities each:

- Gaussian noise: standard deviation 0.02, 0.04, 0.08, 0.12, 0.18.
- Gaussian blur: radius 0.5, 1, 2, 3, 4 pixels.
- Brightness factor: 0.80, 0.65, 0.50, 0.35, 0.20.
- Contrast factor: 0.80, 0.65, 0.50, 0.35, 0.20.
- Center occlusion area fraction: 0.05, 0.10, 0.20, 0.30, 0.40.
- Rotation magnitude: 2, 5, 10, 15, 20 degrees.

Corruptions are deterministic and are applied to every official query image,
not a sampled subset. Clean full-gallery results remain the reference.

## Existing formal comparison block

The separate public-baseline block contains four fully trained University-1652
models, five controlled retrieval rules, all 15 non-empty equal-weight fusion
subsets, fixed-negative gallery scaling, repeated timing, 10,000 paired
bootstrap samples, and exact McNemar/Holm tests. It is reported as a controlled
comparison of existing trained features, not as an ablation of the new model
and not as MaxClique, Sinkhorn, or vector-map reasoning.

## Manuscript gate

Only artifacts with completed manifests, full logs, source/config/data hashes,
and independently verified metrics may enter the paper. The final manuscript
must not claim vector-map tokens, local text-token attention, Sinkhorn,
MaxClique, or any other module that is absent from the executable formal
pipeline.
