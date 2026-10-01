# Robustness figure captions

All figures are descriptive results for seed 1. Each figure is a separate task and metric.

## Figure 1: University-1652: Drone → satellite — r_at_1

University-1652: Drone → satellite. R@1 retained under six image corruptions, seed 1. Retained percentage is 100 × corrupted metric / that variant's own clean metric; severity 0 is the defined 100% clean reference only when clean > 0. Undefined clean-zero retention is left as a gap. Clean R@1 is Visual 38.5550% and Full 31.9060%. All official queries are evaluated against the clean full gallery. Curves are descriptive and task-specific: no pooling, multi-seed SD, confidence intervals or significance is implied. Higher retention or a smaller clean-to-corrupt drop does not imply greater absolute corrupted accuracy. Full's clean evidence is cached while corrupted-query CLIP evidence is computed online, so the comparison includes evidence-path changes and image corruption. The 64-sample clean diagnostic had no numerical equivalence threshold and does not prove bitwise parity or negligible ranking effects. R@1 and official trapezoidal mAP in the CSV are fractions; multiplied by 100 they are percentages. Clean-minus-corrupt absolute drops multiplied by 100 are percentage points, distinct from the relative retained percentage shown. Accepted upstream checkpoint/cache/image verification and historical evidence-chain limitations remain inherited.

Frozen severity 1–5 parameters:

- Gaussian noise: standard_deviation = [0.02, 0.04, 0.08, 0.12, 0.18]; fraction of the [0,1] RGB intensity range.
- Gaussian blur: radius = [0.5, 1, 2, 3, 4]; pixels in the decoded source image.
- Brightness: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow brightness factor.
- Contrast: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow contrast factor.
- Center occlusion: area_fraction = [0.05, 0.1, 0.2, 0.3, 0.4]; fraction of decoded source-image area.
- Rotation: magnitude = [2, 5, 10, 15, 20]; degrees.

Source CSV: `source_data/university1652_drone_to_satellite__r_at_1.csv`; SHA-256 `c5387f6c5f627eb07596cbdd5e0d7909954cefa12f3c6d152c368a91968c9e47`.

## Figure 2: University-1652: Drone → satellite — official_trapezoid_mAP

University-1652: Drone → satellite. Official mAP retained under six image corruptions, seed 1. Retained percentage is 100 × corrupted metric / that variant's own clean metric; severity 0 is the defined 100% clean reference only when clean > 0. Undefined clean-zero retention is left as a gap. Clean Official mAP is Visual 44.2404% and Full 38.1420%. All official queries are evaluated against the clean full gallery. Curves are descriptive and task-specific: no pooling, multi-seed SD, confidence intervals or significance is implied. Higher retention or a smaller clean-to-corrupt drop does not imply greater absolute corrupted accuracy. Full's clean evidence is cached while corrupted-query CLIP evidence is computed online, so the comparison includes evidence-path changes and image corruption. The 64-sample clean diagnostic had no numerical equivalence threshold and does not prove bitwise parity or negligible ranking effects. R@1 and official trapezoidal mAP in the CSV are fractions; multiplied by 100 they are percentages. Clean-minus-corrupt absolute drops multiplied by 100 are percentage points, distinct from the relative retained percentage shown. Accepted upstream checkpoint/cache/image verification and historical evidence-chain limitations remain inherited.

Frozen severity 1–5 parameters:

- Gaussian noise: standard_deviation = [0.02, 0.04, 0.08, 0.12, 0.18]; fraction of the [0,1] RGB intensity range.
- Gaussian blur: radius = [0.5, 1, 2, 3, 4]; pixels in the decoded source image.
- Brightness: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow brightness factor.
- Contrast: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow contrast factor.
- Center occlusion: area_fraction = [0.05, 0.1, 0.2, 0.3, 0.4]; fraction of decoded source-image area.
- Rotation: magnitude = [2, 5, 10, 15, 20]; degrees.

Source CSV: `source_data/university1652_drone_to_satellite__official_trapezoid_map.csv`; SHA-256 `a6176b909ce2a1673c1cdb56f977835ee8a12e226cc8343c11ec629ee17fa838`.

## Figure 3: University-1652: Satellite → drone — r_at_1

University-1652: Satellite → drone. R@1 retained under six image corruptions, seed 1. Retained percentage is 100 × corrupted metric / that variant's own clean metric; severity 0 is the defined 100% clean reference only when clean > 0. Undefined clean-zero retention is left as a gap. Clean R@1 is Visual 56.4907% and Full 45.9344%. All official queries are evaluated against the clean full gallery. Curves are descriptive and task-specific: no pooling, multi-seed SD, confidence intervals or significance is implied. Higher retention or a smaller clean-to-corrupt drop does not imply greater absolute corrupted accuracy. Full's clean evidence is cached while corrupted-query CLIP evidence is computed online, so the comparison includes evidence-path changes and image corruption. The 64-sample clean diagnostic had no numerical equivalence threshold and does not prove bitwise parity or negligible ranking effects. R@1 and official trapezoidal mAP in the CSV are fractions; multiplied by 100 they are percentages. Clean-minus-corrupt absolute drops multiplied by 100 are percentage points, distinct from the relative retained percentage shown. Accepted upstream checkpoint/cache/image verification and historical evidence-chain limitations remain inherited.

Frozen severity 1–5 parameters:

- Gaussian noise: standard_deviation = [0.02, 0.04, 0.08, 0.12, 0.18]; fraction of the [0,1] RGB intensity range.
- Gaussian blur: radius = [0.5, 1, 2, 3, 4]; pixels in the decoded source image.
- Brightness: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow brightness factor.
- Contrast: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow contrast factor.
- Center occlusion: area_fraction = [0.05, 0.1, 0.2, 0.3, 0.4]; fraction of decoded source-image area.
- Rotation: magnitude = [2, 5, 10, 15, 20]; degrees.

Source CSV: `source_data/university1652_satellite_to_drone__r_at_1.csv`; SHA-256 `e3b7b23939b78260f18dc402b9badcd9da813d91e19a2113e9813e5a297ad29e`.

## Figure 4: University-1652: Satellite → drone — official_trapezoid_mAP

University-1652: Satellite → drone. Official mAP retained under six image corruptions, seed 1. Retained percentage is 100 × corrupted metric / that variant's own clean metric; severity 0 is the defined 100% clean reference only when clean > 0. Undefined clean-zero retention is left as a gap. Clean Official mAP is Visual 36.6366% and Full 29.2403%. All official queries are evaluated against the clean full gallery. Curves are descriptive and task-specific: no pooling, multi-seed SD, confidence intervals or significance is implied. Higher retention or a smaller clean-to-corrupt drop does not imply greater absolute corrupted accuracy. Full's clean evidence is cached while corrupted-query CLIP evidence is computed online, so the comparison includes evidence-path changes and image corruption. The 64-sample clean diagnostic had no numerical equivalence threshold and does not prove bitwise parity or negligible ranking effects. R@1 and official trapezoidal mAP in the CSV are fractions; multiplied by 100 they are percentages. Clean-minus-corrupt absolute drops multiplied by 100 are percentage points, distinct from the relative retained percentage shown. Accepted upstream checkpoint/cache/image verification and historical evidence-chain limitations remain inherited.

Frozen severity 1–5 parameters:

- Gaussian noise: standard_deviation = [0.02, 0.04, 0.08, 0.12, 0.18]; fraction of the [0,1] RGB intensity range.
- Gaussian blur: radius = [0.5, 1, 2, 3, 4]; pixels in the decoded source image.
- Brightness: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow brightness factor.
- Contrast: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow contrast factor.
- Center occlusion: area_fraction = [0.05, 0.1, 0.2, 0.3, 0.4]; fraction of decoded source-image area.
- Rotation: magnitude = [2, 5, 10, 15, 20]; degrees.

Source CSV: `source_data/university1652_satellite_to_drone__official_trapezoid_map.csv`; SHA-256 `17f81d49114e197b4a3e75b195c7980fb175b12000dfe9fcc9ada4f48a65d9a9`.

## Figure 5: University-1652: Street → satellite — r_at_1

University-1652: Street → satellite. R@1 retained under six image corruptions, seed 1. Retained percentage is 100 × corrupted metric / that variant's own clean metric; severity 0 is the defined 100% clean reference only when clean > 0. Undefined clean-zero retention is left as a gap. Clean R@1 is Visual 0.5428% and Full 0.9306%. All official queries are evaluated against the clean full gallery. Curves are descriptive and task-specific: no pooling, multi-seed SD, confidence intervals or significance is implied. Higher retention or a smaller clean-to-corrupt drop does not imply greater absolute corrupted accuracy. Full's clean evidence is cached while corrupted-query CLIP evidence is computed online, so the comparison includes evidence-path changes and image corruption. The 64-sample clean diagnostic had no numerical equivalence threshold and does not prove bitwise parity or negligible ranking effects. R@1 and official trapezoidal mAP in the CSV are fractions; multiplied by 100 they are percentages. Clean-minus-corrupt absolute drops multiplied by 100 are percentage points, distinct from the relative retained percentage shown. Accepted upstream checkpoint/cache/image verification and historical evidence-chain limitations remain inherited.

Frozen severity 1–5 parameters:

- Gaussian noise: standard_deviation = [0.02, 0.04, 0.08, 0.12, 0.18]; fraction of the [0,1] RGB intensity range.
- Gaussian blur: radius = [0.5, 1, 2, 3, 4]; pixels in the decoded source image.
- Brightness: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow brightness factor.
- Contrast: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow contrast factor.
- Center occlusion: area_fraction = [0.05, 0.1, 0.2, 0.3, 0.4]; fraction of decoded source-image area.
- Rotation: magnitude = [2, 5, 10, 15, 20]; degrees.

Source CSV: `source_data/university1652_street_to_satellite__r_at_1.csv`; SHA-256 `a013bcb71abeb6425b347f6f6c2249a14b5401552043d42a31892f6bbb55b40a`.

## Figure 6: University-1652: Street → satellite — official_trapezoid_mAP

University-1652: Street → satellite. Official mAP retained under six image corruptions, seed 1. Retained percentage is 100 × corrupted metric / that variant's own clean metric; severity 0 is the defined 100% clean reference only when clean > 0. Undefined clean-zero retention is left as a gap. Clean Official mAP is Visual 1.7087% and Full 2.1849%. All official queries are evaluated against the clean full gallery. Curves are descriptive and task-specific: no pooling, multi-seed SD, confidence intervals or significance is implied. Higher retention or a smaller clean-to-corrupt drop does not imply greater absolute corrupted accuracy. Full's clean evidence is cached while corrupted-query CLIP evidence is computed online, so the comparison includes evidence-path changes and image corruption. The 64-sample clean diagnostic had no numerical equivalence threshold and does not prove bitwise parity or negligible ranking effects. R@1 and official trapezoidal mAP in the CSV are fractions; multiplied by 100 they are percentages. Clean-minus-corrupt absolute drops multiplied by 100 are percentage points, distinct from the relative retained percentage shown. Accepted upstream checkpoint/cache/image verification and historical evidence-chain limitations remain inherited.

Frozen severity 1–5 parameters:

- Gaussian noise: standard_deviation = [0.02, 0.04, 0.08, 0.12, 0.18]; fraction of the [0,1] RGB intensity range.
- Gaussian blur: radius = [0.5, 1, 2, 3, 4]; pixels in the decoded source image.
- Brightness: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow brightness factor.
- Contrast: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow contrast factor.
- Center occlusion: area_fraction = [0.05, 0.1, 0.2, 0.3, 0.4]; fraction of decoded source-image area.
- Rotation: magnitude = [2, 5, 10, 15, 20]; degrees.

Source CSV: `source_data/university1652_street_to_satellite__official_trapezoid_map.csv`; SHA-256 `2898b494b574a144bbb8a70ec22ca604f9374a90afa013c3965b3caa24562c89`.

## Figure 7: SUES-200: UAV 150 m → satellite — r_at_1

SUES-200: UAV 150 m → satellite. R@1 retained under six image corruptions, seed 1. Retained percentage is 100 × corrupted metric / that variant's own clean metric; severity 0 is the defined 100% clean reference only when clean > 0. Undefined clean-zero retention is left as a gap. Clean R@1 is Visual 34.0750% and Full 28.7000%. All official queries are evaluated against the clean full gallery. Curves are descriptive and task-specific: no pooling, multi-seed SD, confidence intervals or significance is implied. Higher retention or a smaller clean-to-corrupt drop does not imply greater absolute corrupted accuracy. Full's clean evidence is cached while corrupted-query CLIP evidence is computed online, so the comparison includes evidence-path changes and image corruption. The 64-sample clean diagnostic had no numerical equivalence threshold and does not prove bitwise parity or negligible ranking effects. R@1 and official trapezoidal mAP in the CSV are fractions; multiplied by 100 they are percentages. Clean-minus-corrupt absolute drops multiplied by 100 are percentage points, distinct from the relative retained percentage shown. Accepted upstream checkpoint/cache/image verification and historical evidence-chain limitations remain inherited.

Frozen severity 1–5 parameters:

- Gaussian noise: standard_deviation = [0.02, 0.04, 0.08, 0.12, 0.18]; fraction of the [0,1] RGB intensity range.
- Gaussian blur: radius = [0.5, 1, 2, 3, 4]; pixels in the decoded source image.
- Brightness: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow brightness factor.
- Contrast: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow contrast factor.
- Center occlusion: area_fraction = [0.05, 0.1, 0.2, 0.3, 0.4]; fraction of decoded source-image area.
- Rotation: magnitude = [2, 5, 10, 15, 20]; degrees.

Source CSV: `source_data/sues200_uav_150m_to_satellite__r_at_1.csv`; SHA-256 `c48e1326be92b725582f0439f79d12f5bda2c26717f3fc85a60bf6d5a4e3852a`.

## Figure 8: SUES-200: UAV 150 m → satellite — official_trapezoid_mAP

SUES-200: UAV 150 m → satellite. Official mAP retained under six image corruptions, seed 1. Retained percentage is 100 × corrupted metric / that variant's own clean metric; severity 0 is the defined 100% clean reference only when clean > 0. Undefined clean-zero retention is left as a gap. Clean Official mAP is Visual 42.5678% and Full 37.1579%. All official queries are evaluated against the clean full gallery. Curves are descriptive and task-specific: no pooling, multi-seed SD, confidence intervals or significance is implied. Higher retention or a smaller clean-to-corrupt drop does not imply greater absolute corrupted accuracy. Full's clean evidence is cached while corrupted-query CLIP evidence is computed online, so the comparison includes evidence-path changes and image corruption. The 64-sample clean diagnostic had no numerical equivalence threshold and does not prove bitwise parity or negligible ranking effects. R@1 and official trapezoidal mAP in the CSV are fractions; multiplied by 100 they are percentages. Clean-minus-corrupt absolute drops multiplied by 100 are percentage points, distinct from the relative retained percentage shown. Accepted upstream checkpoint/cache/image verification and historical evidence-chain limitations remain inherited.

Frozen severity 1–5 parameters:

- Gaussian noise: standard_deviation = [0.02, 0.04, 0.08, 0.12, 0.18]; fraction of the [0,1] RGB intensity range.
- Gaussian blur: radius = [0.5, 1, 2, 3, 4]; pixels in the decoded source image.
- Brightness: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow brightness factor.
- Contrast: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow contrast factor.
- Center occlusion: area_fraction = [0.05, 0.1, 0.2, 0.3, 0.4]; fraction of decoded source-image area.
- Rotation: magnitude = [2, 5, 10, 15, 20]; degrees.

Source CSV: `source_data/sues200_uav_150m_to_satellite__official_trapezoid_map.csv`; SHA-256 `d71573bcb39f59489fed67c2a26587faac870d13a8bb9a0fd1fd4b4628dc3a3a`.

## Figure 9: SUES-200: Satellite → UAV 150 m — r_at_1

SUES-200: Satellite → UAV 150 m. R@1 retained under six image corruptions, seed 1. Retained percentage is 100 × corrupted metric / that variant's own clean metric; severity 0 is the defined 100% clean reference only when clean > 0. Undefined clean-zero retention is left as a gap. Clean R@1 is Visual 53.7500% and Full 47.5000%. All official queries are evaluated against the clean full gallery. Curves are descriptive and task-specific: no pooling, multi-seed SD, confidence intervals or significance is implied. Higher retention or a smaller clean-to-corrupt drop does not imply greater absolute corrupted accuracy. Full's clean evidence is cached while corrupted-query CLIP evidence is computed online, so the comparison includes evidence-path changes and image corruption. The 64-sample clean diagnostic had no numerical equivalence threshold and does not prove bitwise parity or negligible ranking effects. R@1 and official trapezoidal mAP in the CSV are fractions; multiplied by 100 they are percentages. Clean-minus-corrupt absolute drops multiplied by 100 are percentage points, distinct from the relative retained percentage shown. Accepted upstream checkpoint/cache/image verification and historical evidence-chain limitations remain inherited.

Frozen severity 1–5 parameters:

- Gaussian noise: standard_deviation = [0.02, 0.04, 0.08, 0.12, 0.18]; fraction of the [0,1] RGB intensity range.
- Gaussian blur: radius = [0.5, 1, 2, 3, 4]; pixels in the decoded source image.
- Brightness: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow brightness factor.
- Contrast: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow contrast factor.
- Center occlusion: area_fraction = [0.05, 0.1, 0.2, 0.3, 0.4]; fraction of decoded source-image area.
- Rotation: magnitude = [2, 5, 10, 15, 20]; degrees.

Source CSV: `source_data/sues200_satellite_to_uav_150m__r_at_1.csv`; SHA-256 `5b19be3f2e54ee94ef1ac2c503edc71b1c0a8c5309b2faa16206247ed3cb3f7e`.

## Figure 10: SUES-200: Satellite → UAV 150 m — official_trapezoid_mAP

SUES-200: Satellite → UAV 150 m. Official mAP retained under six image corruptions, seed 1. Retained percentage is 100 × corrupted metric / that variant's own clean metric; severity 0 is the defined 100% clean reference only when clean > 0. Undefined clean-zero retention is left as a gap. Clean Official mAP is Visual 39.3597% and Full 34.2788%. All official queries are evaluated against the clean full gallery. Curves are descriptive and task-specific: no pooling, multi-seed SD, confidence intervals or significance is implied. Higher retention or a smaller clean-to-corrupt drop does not imply greater absolute corrupted accuracy. Full's clean evidence is cached while corrupted-query CLIP evidence is computed online, so the comparison includes evidence-path changes and image corruption. The 64-sample clean diagnostic had no numerical equivalence threshold and does not prove bitwise parity or negligible ranking effects. R@1 and official trapezoidal mAP in the CSV are fractions; multiplied by 100 they are percentages. Clean-minus-corrupt absolute drops multiplied by 100 are percentage points, distinct from the relative retained percentage shown. Accepted upstream checkpoint/cache/image verification and historical evidence-chain limitations remain inherited.

Frozen severity 1–5 parameters:

- Gaussian noise: standard_deviation = [0.02, 0.04, 0.08, 0.12, 0.18]; fraction of the [0,1] RGB intensity range.
- Gaussian blur: radius = [0.5, 1, 2, 3, 4]; pixels in the decoded source image.
- Brightness: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow brightness factor.
- Contrast: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow contrast factor.
- Center occlusion: area_fraction = [0.05, 0.1, 0.2, 0.3, 0.4]; fraction of decoded source-image area.
- Rotation: magnitude = [2, 5, 10, 15, 20]; degrees.

Source CSV: `source_data/sues200_satellite_to_uav_150m__official_trapezoid_map.csv`; SHA-256 `0199a000da56d9dcdb577a4a93cf111d86172ba9761012db1df92a18128ef75f`.

## Figure 11: SUES-200: UAV 200 m → satellite — r_at_1

SUES-200: UAV 200 m → satellite. R@1 retained under six image corruptions, seed 1. Retained percentage is 100 × corrupted metric / that variant's own clean metric; severity 0 is the defined 100% clean reference only when clean > 0. Undefined clean-zero retention is left as a gap. Clean R@1 is Visual 41.4500% and Full 33.1500%. All official queries are evaluated against the clean full gallery. Curves are descriptive and task-specific: no pooling, multi-seed SD, confidence intervals or significance is implied. Higher retention or a smaller clean-to-corrupt drop does not imply greater absolute corrupted accuracy. Full's clean evidence is cached while corrupted-query CLIP evidence is computed online, so the comparison includes evidence-path changes and image corruption. The 64-sample clean diagnostic had no numerical equivalence threshold and does not prove bitwise parity or negligible ranking effects. R@1 and official trapezoidal mAP in the CSV are fractions; multiplied by 100 they are percentages. Clean-minus-corrupt absolute drops multiplied by 100 are percentage points, distinct from the relative retained percentage shown. Accepted upstream checkpoint/cache/image verification and historical evidence-chain limitations remain inherited.

Frozen severity 1–5 parameters:

- Gaussian noise: standard_deviation = [0.02, 0.04, 0.08, 0.12, 0.18]; fraction of the [0,1] RGB intensity range.
- Gaussian blur: radius = [0.5, 1, 2, 3, 4]; pixels in the decoded source image.
- Brightness: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow brightness factor.
- Contrast: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow contrast factor.
- Center occlusion: area_fraction = [0.05, 0.1, 0.2, 0.3, 0.4]; fraction of decoded source-image area.
- Rotation: magnitude = [2, 5, 10, 15, 20]; degrees.

Source CSV: `source_data/sues200_uav_200m_to_satellite__r_at_1.csv`; SHA-256 `552b96d749a9379371a5f331657d6eecf33fa336ca8a1133c01c035cde7b5d65`.

## Figure 12: SUES-200: UAV 200 m → satellite — official_trapezoid_mAP

SUES-200: UAV 200 m → satellite. Official mAP retained under six image corruptions, seed 1. Retained percentage is 100 × corrupted metric / that variant's own clean metric; severity 0 is the defined 100% clean reference only when clean > 0. Undefined clean-zero retention is left as a gap. Clean Official mAP is Visual 50.1874% and Full 41.4650%. All official queries are evaluated against the clean full gallery. Curves are descriptive and task-specific: no pooling, multi-seed SD, confidence intervals or significance is implied. Higher retention or a smaller clean-to-corrupt drop does not imply greater absolute corrupted accuracy. Full's clean evidence is cached while corrupted-query CLIP evidence is computed online, so the comparison includes evidence-path changes and image corruption. The 64-sample clean diagnostic had no numerical equivalence threshold and does not prove bitwise parity or negligible ranking effects. R@1 and official trapezoidal mAP in the CSV are fractions; multiplied by 100 they are percentages. Clean-minus-corrupt absolute drops multiplied by 100 are percentage points, distinct from the relative retained percentage shown. Accepted upstream checkpoint/cache/image verification and historical evidence-chain limitations remain inherited.

Frozen severity 1–5 parameters:

- Gaussian noise: standard_deviation = [0.02, 0.04, 0.08, 0.12, 0.18]; fraction of the [0,1] RGB intensity range.
- Gaussian blur: radius = [0.5, 1, 2, 3, 4]; pixels in the decoded source image.
- Brightness: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow brightness factor.
- Contrast: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow contrast factor.
- Center occlusion: area_fraction = [0.05, 0.1, 0.2, 0.3, 0.4]; fraction of decoded source-image area.
- Rotation: magnitude = [2, 5, 10, 15, 20]; degrees.

Source CSV: `source_data/sues200_uav_200m_to_satellite__official_trapezoid_map.csv`; SHA-256 `26ff6595885baedb4352feb24683bd5eefb4402cb4f83e412712bd59ae7d08bf`.

## Figure 13: SUES-200: Satellite → UAV 200 m — r_at_1

SUES-200: Satellite → UAV 200 m. R@1 retained under six image corruptions, seed 1. Retained percentage is 100 × corrupted metric / that variant's own clean metric; severity 0 is the defined 100% clean reference only when clean > 0. Undefined clean-zero retention is left as a gap. Clean R@1 is Visual 61.2500% and Full 61.2500%. All official queries are evaluated against the clean full gallery. Curves are descriptive and task-specific: no pooling, multi-seed SD, confidence intervals or significance is implied. Higher retention or a smaller clean-to-corrupt drop does not imply greater absolute corrupted accuracy. Full's clean evidence is cached while corrupted-query CLIP evidence is computed online, so the comparison includes evidence-path changes and image corruption. The 64-sample clean diagnostic had no numerical equivalence threshold and does not prove bitwise parity or negligible ranking effects. R@1 and official trapezoidal mAP in the CSV are fractions; multiplied by 100 they are percentages. Clean-minus-corrupt absolute drops multiplied by 100 are percentage points, distinct from the relative retained percentage shown. Accepted upstream checkpoint/cache/image verification and historical evidence-chain limitations remain inherited.

Frozen severity 1–5 parameters:

- Gaussian noise: standard_deviation = [0.02, 0.04, 0.08, 0.12, 0.18]; fraction of the [0,1] RGB intensity range.
- Gaussian blur: radius = [0.5, 1, 2, 3, 4]; pixels in the decoded source image.
- Brightness: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow brightness factor.
- Contrast: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow contrast factor.
- Center occlusion: area_fraction = [0.05, 0.1, 0.2, 0.3, 0.4]; fraction of decoded source-image area.
- Rotation: magnitude = [2, 5, 10, 15, 20]; degrees.

Source CSV: `source_data/sues200_satellite_to_uav_200m__r_at_1.csv`; SHA-256 `2857b17c085a550306136d31ddfcff9f3876b0e054897e2c7e3574506a2cd771`.

## Figure 14: SUES-200: Satellite → UAV 200 m — official_trapezoid_mAP

SUES-200: Satellite → UAV 200 m. Official mAP retained under six image corruptions, seed 1. Retained percentage is 100 × corrupted metric / that variant's own clean metric; severity 0 is the defined 100% clean reference only when clean > 0. Undefined clean-zero retention is left as a gap. Clean Official mAP is Visual 48.7702% and Full 40.2459%. All official queries are evaluated against the clean full gallery. Curves are descriptive and task-specific: no pooling, multi-seed SD, confidence intervals or significance is implied. Higher retention or a smaller clean-to-corrupt drop does not imply greater absolute corrupted accuracy. Full's clean evidence is cached while corrupted-query CLIP evidence is computed online, so the comparison includes evidence-path changes and image corruption. The 64-sample clean diagnostic had no numerical equivalence threshold and does not prove bitwise parity or negligible ranking effects. R@1 and official trapezoidal mAP in the CSV are fractions; multiplied by 100 they are percentages. Clean-minus-corrupt absolute drops multiplied by 100 are percentage points, distinct from the relative retained percentage shown. Accepted upstream checkpoint/cache/image verification and historical evidence-chain limitations remain inherited.

Frozen severity 1–5 parameters:

- Gaussian noise: standard_deviation = [0.02, 0.04, 0.08, 0.12, 0.18]; fraction of the [0,1] RGB intensity range.
- Gaussian blur: radius = [0.5, 1, 2, 3, 4]; pixels in the decoded source image.
- Brightness: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow brightness factor.
- Contrast: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow contrast factor.
- Center occlusion: area_fraction = [0.05, 0.1, 0.2, 0.3, 0.4]; fraction of decoded source-image area.
- Rotation: magnitude = [2, 5, 10, 15, 20]; degrees.

Source CSV: `source_data/sues200_satellite_to_uav_200m__official_trapezoid_map.csv`; SHA-256 `bbff07dcf1d46c2dc694718afc88159305affa85dcb0af636ea6fa67ab09555a`.

## Figure 15: SUES-200: UAV 250 m → satellite — r_at_1

SUES-200: UAV 250 m → satellite. R@1 retained under six image corruptions, seed 1. Retained percentage is 100 × corrupted metric / that variant's own clean metric; severity 0 is the defined 100% clean reference only when clean > 0. Undefined clean-zero retention is left as a gap. Clean R@1 is Visual 48.1000% and Full 35.9750%. All official queries are evaluated against the clean full gallery. Curves are descriptive and task-specific: no pooling, multi-seed SD, confidence intervals or significance is implied. Higher retention or a smaller clean-to-corrupt drop does not imply greater absolute corrupted accuracy. Full's clean evidence is cached while corrupted-query CLIP evidence is computed online, so the comparison includes evidence-path changes and image corruption. The 64-sample clean diagnostic had no numerical equivalence threshold and does not prove bitwise parity or negligible ranking effects. R@1 and official trapezoidal mAP in the CSV are fractions; multiplied by 100 they are percentages. Clean-minus-corrupt absolute drops multiplied by 100 are percentage points, distinct from the relative retained percentage shown. Accepted upstream checkpoint/cache/image verification and historical evidence-chain limitations remain inherited.

Frozen severity 1–5 parameters:

- Gaussian noise: standard_deviation = [0.02, 0.04, 0.08, 0.12, 0.18]; fraction of the [0,1] RGB intensity range.
- Gaussian blur: radius = [0.5, 1, 2, 3, 4]; pixels in the decoded source image.
- Brightness: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow brightness factor.
- Contrast: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow contrast factor.
- Center occlusion: area_fraction = [0.05, 0.1, 0.2, 0.3, 0.4]; fraction of decoded source-image area.
- Rotation: magnitude = [2, 5, 10, 15, 20]; degrees.

Source CSV: `source_data/sues200_uav_250m_to_satellite__r_at_1.csv`; SHA-256 `bf0d79837d97a24ac130362b55e2ccd429fcf615313d9ba10f24d601046ad729`.

## Figure 16: SUES-200: UAV 250 m → satellite — official_trapezoid_mAP

SUES-200: UAV 250 m → satellite. Official mAP retained under six image corruptions, seed 1. Retained percentage is 100 × corrupted metric / that variant's own clean metric; severity 0 is the defined 100% clean reference only when clean > 0. Undefined clean-zero retention is left as a gap. Clean Official mAP is Visual 55.9603% and Full 44.4342%. All official queries are evaluated against the clean full gallery. Curves are descriptive and task-specific: no pooling, multi-seed SD, confidence intervals or significance is implied. Higher retention or a smaller clean-to-corrupt drop does not imply greater absolute corrupted accuracy. Full's clean evidence is cached while corrupted-query CLIP evidence is computed online, so the comparison includes evidence-path changes and image corruption. The 64-sample clean diagnostic had no numerical equivalence threshold and does not prove bitwise parity or negligible ranking effects. R@1 and official trapezoidal mAP in the CSV are fractions; multiplied by 100 they are percentages. Clean-minus-corrupt absolute drops multiplied by 100 are percentage points, distinct from the relative retained percentage shown. Accepted upstream checkpoint/cache/image verification and historical evidence-chain limitations remain inherited.

Frozen severity 1–5 parameters:

- Gaussian noise: standard_deviation = [0.02, 0.04, 0.08, 0.12, 0.18]; fraction of the [0,1] RGB intensity range.
- Gaussian blur: radius = [0.5, 1, 2, 3, 4]; pixels in the decoded source image.
- Brightness: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow brightness factor.
- Contrast: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow contrast factor.
- Center occlusion: area_fraction = [0.05, 0.1, 0.2, 0.3, 0.4]; fraction of decoded source-image area.
- Rotation: magnitude = [2, 5, 10, 15, 20]; degrees.

Source CSV: `source_data/sues200_uav_250m_to_satellite__official_trapezoid_map.csv`; SHA-256 `7510ef6d868d58a6c737e64bf9704a91fad4a5b3800820798d788cd0a59f021e`.

## Figure 17: SUES-200: Satellite → UAV 250 m — r_at_1

SUES-200: Satellite → UAV 250 m. R@1 retained under six image corruptions, seed 1. Retained percentage is 100 × corrupted metric / that variant's own clean metric; severity 0 is the defined 100% clean reference only when clean > 0. Undefined clean-zero retention is left as a gap. Clean R@1 is Visual 68.7500% and Full 60.0000%. All official queries are evaluated against the clean full gallery. Curves are descriptive and task-specific: no pooling, multi-seed SD, confidence intervals or significance is implied. Higher retention or a smaller clean-to-corrupt drop does not imply greater absolute corrupted accuracy. Full's clean evidence is cached while corrupted-query CLIP evidence is computed online, so the comparison includes evidence-path changes and image corruption. The 64-sample clean diagnostic had no numerical equivalence threshold and does not prove bitwise parity or negligible ranking effects. R@1 and official trapezoidal mAP in the CSV are fractions; multiplied by 100 they are percentages. Clean-minus-corrupt absolute drops multiplied by 100 are percentage points, distinct from the relative retained percentage shown. Accepted upstream checkpoint/cache/image verification and historical evidence-chain limitations remain inherited.

Frozen severity 1–5 parameters:

- Gaussian noise: standard_deviation = [0.02, 0.04, 0.08, 0.12, 0.18]; fraction of the [0,1] RGB intensity range.
- Gaussian blur: radius = [0.5, 1, 2, 3, 4]; pixels in the decoded source image.
- Brightness: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow brightness factor.
- Contrast: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow contrast factor.
- Center occlusion: area_fraction = [0.05, 0.1, 0.2, 0.3, 0.4]; fraction of decoded source-image area.
- Rotation: magnitude = [2, 5, 10, 15, 20]; degrees.

Source CSV: `source_data/sues200_satellite_to_uav_250m__r_at_1.csv`; SHA-256 `18150152356d786b9d2b66b3042e7d7912666bef0aa769fc38da543375a1c5bb`.

## Figure 18: SUES-200: Satellite → UAV 250 m — official_trapezoid_mAP

SUES-200: Satellite → UAV 250 m. Official mAP retained under six image corruptions, seed 1. Retained percentage is 100 × corrupted metric / that variant's own clean metric; severity 0 is the defined 100% clean reference only when clean > 0. Undefined clean-zero retention is left as a gap. Clean Official mAP is Visual 52.8418% and Full 43.9953%. All official queries are evaluated against the clean full gallery. Curves are descriptive and task-specific: no pooling, multi-seed SD, confidence intervals or significance is implied. Higher retention or a smaller clean-to-corrupt drop does not imply greater absolute corrupted accuracy. Full's clean evidence is cached while corrupted-query CLIP evidence is computed online, so the comparison includes evidence-path changes and image corruption. The 64-sample clean diagnostic had no numerical equivalence threshold and does not prove bitwise parity or negligible ranking effects. R@1 and official trapezoidal mAP in the CSV are fractions; multiplied by 100 they are percentages. Clean-minus-corrupt absolute drops multiplied by 100 are percentage points, distinct from the relative retained percentage shown. Accepted upstream checkpoint/cache/image verification and historical evidence-chain limitations remain inherited.

Frozen severity 1–5 parameters:

- Gaussian noise: standard_deviation = [0.02, 0.04, 0.08, 0.12, 0.18]; fraction of the [0,1] RGB intensity range.
- Gaussian blur: radius = [0.5, 1, 2, 3, 4]; pixels in the decoded source image.
- Brightness: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow brightness factor.
- Contrast: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow contrast factor.
- Center occlusion: area_fraction = [0.05, 0.1, 0.2, 0.3, 0.4]; fraction of decoded source-image area.
- Rotation: magnitude = [2, 5, 10, 15, 20]; degrees.

Source CSV: `source_data/sues200_satellite_to_uav_250m__official_trapezoid_map.csv`; SHA-256 `3a29e393e64e4e2c5bec7ba74569f5c7096c510c61d9364caa46c3c97b95289a`.

## Figure 19: SUES-200: UAV 300 m → satellite — r_at_1

SUES-200: UAV 300 m → satellite. R@1 retained under six image corruptions, seed 1. Retained percentage is 100 × corrupted metric / that variant's own clean metric; severity 0 is the defined 100% clean reference only when clean > 0. Undefined clean-zero retention is left as a gap. Clean R@1 is Visual 49.6750% and Full 38.7750%. All official queries are evaluated against the clean full gallery. Curves are descriptive and task-specific: no pooling, multi-seed SD, confidence intervals or significance is implied. Higher retention or a smaller clean-to-corrupt drop does not imply greater absolute corrupted accuracy. Full's clean evidence is cached while corrupted-query CLIP evidence is computed online, so the comparison includes evidence-path changes and image corruption. The 64-sample clean diagnostic had no numerical equivalence threshold and does not prove bitwise parity or negligible ranking effects. R@1 and official trapezoidal mAP in the CSV are fractions; multiplied by 100 they are percentages. Clean-minus-corrupt absolute drops multiplied by 100 are percentage points, distinct from the relative retained percentage shown. Accepted upstream checkpoint/cache/image verification and historical evidence-chain limitations remain inherited.

Frozen severity 1–5 parameters:

- Gaussian noise: standard_deviation = [0.02, 0.04, 0.08, 0.12, 0.18]; fraction of the [0,1] RGB intensity range.
- Gaussian blur: radius = [0.5, 1, 2, 3, 4]; pixels in the decoded source image.
- Brightness: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow brightness factor.
- Contrast: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow contrast factor.
- Center occlusion: area_fraction = [0.05, 0.1, 0.2, 0.3, 0.4]; fraction of decoded source-image area.
- Rotation: magnitude = [2, 5, 10, 15, 20]; degrees.

Source CSV: `source_data/sues200_uav_300m_to_satellite__r_at_1.csv`; SHA-256 `7679482275b54c94e3adce3a2fc10008c71665157c294c599011947cdf1416e6`.

## Figure 20: SUES-200: UAV 300 m → satellite — official_trapezoid_mAP

SUES-200: UAV 300 m → satellite. Official mAP retained under six image corruptions, seed 1. Retained percentage is 100 × corrupted metric / that variant's own clean metric; severity 0 is the defined 100% clean reference only when clean > 0. Undefined clean-zero retention is left as a gap. Clean Official mAP is Visual 57.6093% and Full 47.1076%. All official queries are evaluated against the clean full gallery. Curves are descriptive and task-specific: no pooling, multi-seed SD, confidence intervals or significance is implied. Higher retention or a smaller clean-to-corrupt drop does not imply greater absolute corrupted accuracy. Full's clean evidence is cached while corrupted-query CLIP evidence is computed online, so the comparison includes evidence-path changes and image corruption. The 64-sample clean diagnostic had no numerical equivalence threshold and does not prove bitwise parity or negligible ranking effects. R@1 and official trapezoidal mAP in the CSV are fractions; multiplied by 100 they are percentages. Clean-minus-corrupt absolute drops multiplied by 100 are percentage points, distinct from the relative retained percentage shown. Accepted upstream checkpoint/cache/image verification and historical evidence-chain limitations remain inherited.

Frozen severity 1–5 parameters:

- Gaussian noise: standard_deviation = [0.02, 0.04, 0.08, 0.12, 0.18]; fraction of the [0,1] RGB intensity range.
- Gaussian blur: radius = [0.5, 1, 2, 3, 4]; pixels in the decoded source image.
- Brightness: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow brightness factor.
- Contrast: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow contrast factor.
- Center occlusion: area_fraction = [0.05, 0.1, 0.2, 0.3, 0.4]; fraction of decoded source-image area.
- Rotation: magnitude = [2, 5, 10, 15, 20]; degrees.

Source CSV: `source_data/sues200_uav_300m_to_satellite__official_trapezoid_map.csv`; SHA-256 `e4ed5d92ecc81daf9ac42d513c045712754bb7793131c1cf1d7f56f4c63ef368`.

## Figure 21: SUES-200: Satellite → UAV 300 m — r_at_1

SUES-200: Satellite → UAV 300 m. R@1 retained under six image corruptions, seed 1. Retained percentage is 100 × corrupted metric / that variant's own clean metric; severity 0 is the defined 100% clean reference only when clean > 0. Undefined clean-zero retention is left as a gap. Clean R@1 is Visual 70.0000% and Full 60.0000%. All official queries are evaluated against the clean full gallery. Curves are descriptive and task-specific: no pooling, multi-seed SD, confidence intervals or significance is implied. Higher retention or a smaller clean-to-corrupt drop does not imply greater absolute corrupted accuracy. Full's clean evidence is cached while corrupted-query CLIP evidence is computed online, so the comparison includes evidence-path changes and image corruption. The 64-sample clean diagnostic had no numerical equivalence threshold and does not prove bitwise parity or negligible ranking effects. R@1 and official trapezoidal mAP in the CSV are fractions; multiplied by 100 they are percentages. Clean-minus-corrupt absolute drops multiplied by 100 are percentage points, distinct from the relative retained percentage shown. Accepted upstream checkpoint/cache/image verification and historical evidence-chain limitations remain inherited.

Frozen severity 1–5 parameters:

- Gaussian noise: standard_deviation = [0.02, 0.04, 0.08, 0.12, 0.18]; fraction of the [0,1] RGB intensity range.
- Gaussian blur: radius = [0.5, 1, 2, 3, 4]; pixels in the decoded source image.
- Brightness: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow brightness factor.
- Contrast: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow contrast factor.
- Center occlusion: area_fraction = [0.05, 0.1, 0.2, 0.3, 0.4]; fraction of decoded source-image area.
- Rotation: magnitude = [2, 5, 10, 15, 20]; degrees.

Source CSV: `source_data/sues200_satellite_to_uav_300m__r_at_1.csv`; SHA-256 `3ca6a7476fb536a47bef82f45da07fa99d91dce38b6d7eb443a8181a09218caa`.

## Figure 22: SUES-200: Satellite → UAV 300 m — official_trapezoid_mAP

SUES-200: Satellite → UAV 300 m. Official mAP retained under six image corruptions, seed 1. Retained percentage is 100 × corrupted metric / that variant's own clean metric; severity 0 is the defined 100% clean reference only when clean > 0. Undefined clean-zero retention is left as a gap. Clean Official mAP is Visual 54.8446% and Full 45.2476%. All official queries are evaluated against the clean full gallery. Curves are descriptive and task-specific: no pooling, multi-seed SD, confidence intervals or significance is implied. Higher retention or a smaller clean-to-corrupt drop does not imply greater absolute corrupted accuracy. Full's clean evidence is cached while corrupted-query CLIP evidence is computed online, so the comparison includes evidence-path changes and image corruption. The 64-sample clean diagnostic had no numerical equivalence threshold and does not prove bitwise parity or negligible ranking effects. R@1 and official trapezoidal mAP in the CSV are fractions; multiplied by 100 they are percentages. Clean-minus-corrupt absolute drops multiplied by 100 are percentage points, distinct from the relative retained percentage shown. Accepted upstream checkpoint/cache/image verification and historical evidence-chain limitations remain inherited.

Frozen severity 1–5 parameters:

- Gaussian noise: standard_deviation = [0.02, 0.04, 0.08, 0.12, 0.18]; fraction of the [0,1] RGB intensity range.
- Gaussian blur: radius = [0.5, 1, 2, 3, 4]; pixels in the decoded source image.
- Brightness: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow brightness factor.
- Contrast: factor = [0.8, 0.65, 0.5, 0.35, 0.2]; multiplicative Pillow contrast factor.
- Center occlusion: area_fraction = [0.05, 0.1, 0.2, 0.3, 0.4]; fraction of decoded source-image area.
- Rotation: magnitude = [2, 5, 10, 15, 20]; degrees.

Source CSV: `source_data/sues200_satellite_to_uav_300m__official_trapezoid_map.csv`; SHA-256 `5b4f9d5a536b557dbc6e82ed776ca66761f7c741c9ac52874231471e0363dadd`.

