# Real Data Guide

This repository currently contains a runnable research prototype, not a
trainable deep model. To produce publishable real-data experiments, download at
least one public UAV/satellite benchmark and add a real feature extractor,
retrieval evaluator, and local matching evaluator.

## Recommended Datasets

### 1. University-1652

Best first dataset for a standard paper baseline.

- Official repo: https://github.com/layumi/University1652-Baseline
- Access: dataset link is provided upon request by the maintainers.
- Scope: drone, satellite, and street-view images for 1,652 buildings.
- Standard task for this project: Drone -> Satellite retrieval.
- Expected structure:

```text
datasets/
  University-1652/
    train/
      drone/
      satellite/
      street/
    test/
      query_drone/
      gallery_satellite/
      query_satellite/
      gallery_drone/
```

Start here if you want comparable Recall@1, Recall@5, Recall@10, AP, and
ranking visualizations.

### 2. SUES-200

Good second dataset for UAV height and scene variation.

- Official repo: https://github.com/Reza-Zhu/SUES-200-Benchmark
- Access: Google Drive and Baidu links; academic research only.
- Scope: UAV and satellite cross-view matching across multiple heights.
- Useful experiments: height-specific retrieval, cross-height robustness,
  snow/fog/uncertainty perturbation, and ablations.

### 3. GeoText-1652

Useful for the language-guided part of LGM-GAME.

- Official repo: https://github.com/MultimodalGeo/GeoText-1652
- Access: Google Drive and Hugging Face Hub.
- Scope: images plus global descriptions and bbox text annotations.
- Useful experiments: text-anchor ablation, language-guided matching, and
  spatial relation consistency.

### 4. UAV-VisLoc

Useful for coordinate-level localization and trajectory-style evaluation.

- Official repo: https://github.com/IntelliSensing/UAV-VisLoc
- Access: Google Drive/Baidu in the repo; an example subset is provided.
- Scope: drone images, satellite maps, GPS/coordinate metadata.
- Useful metrics: median localization error, percent within meter thresholds,
  retrieval-to-coordinate refinement.

### 5. UAV-GeoLoc / World-UAV

Good for a stronger recent robustness section.

- Project page: https://ringowrw.github.io/GeoLoc-UAV/
- Access: Hugging Face and Baidu links on the project page.
- Scope: large-vocabulary scene categories and geometric transformations.
- Useful experiments: rotation/scale robustness and scene-category
  generalization.

## Practical Experiment Ladder

1. **Minimum real experiment**
   - Download University-1652.
   - Train or reuse a public baseline model.
   - Report Drone -> Satellite Recall@1/@5/@10, AP, and MRR.

2. **Stronger journal experiment**
   - Add SUES-200.
   - Report height-specific and weather/uncertainty robustness.
   - Add ablations: visual only, +geometry, +text, +map, +Sinkhorn, +graph.

3. **Paper-aligned experiment**
   - Add GeoText-1652 for text anchors.
   - Add vector-map primitives from OSM or use dataset coordinate metadata when
     available.
   - Report text/style/map ablations and qualitative matching figures.

4. **Coordinate localization experiment**
   - Add UAV-VisLoc or ALTO-like trajectory data.
   - Convert top-k retrieved satellite candidates to coordinates.
   - Report median error and percent within fixed thresholds.

## What This Repo Should Add Next

- A dataset scanner that validates folder layouts and counts query/gallery
  images.
- A feature extraction backend, initially using a pretrained model such as
  ResNet, DINOv2, CLIP, or a University-1652 baseline checkpoint.
- Retrieval metrics: Recall@K, AP, mAP, MRR, median rank.
- Local matching metrics: match precision, inlier ratio, geometric residual.
- Plotting scripts that generate IEEE-style PDF figures for the LaTeX paper.

The controlled benchmark in `lgm_game_prototype/experiments` is only for
pipeline validation and figure prototyping. Do not report it as real benchmark
performance.
