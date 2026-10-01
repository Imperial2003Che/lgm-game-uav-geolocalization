# Adopted T3 transfer: three-seed descriptive results

Scope: 12 accepted transfer runs, 66 task-seed rows, 22 task-variant groups and 11 within-task contrasts.
Each cell is mean ± sample SD across seeds 1/2/3 (n−1 denominator). All three metrics below are multiplied by 100; the machine-readable files retain fractions.

| Source → target | Task | Variant | R@1 ×100 | mAP ×100 | MRR ×100 |
|---|---|---|---:|---:|---:|
| sues200 → university1652 | university1652_drone_to_satellite | visual | 11.0087 ± 0.1174 | 14.8614 ± 0.0630 | 18.7141 ± 0.0379 |
| sues200 → university1652 | university1652_drone_to_satellite | full | 8.1777 ± 0.6092 | 11.6551 ± 0.6996 | 15.1325 ± 0.8086 |
| sues200 → university1652 | university1652_satellite_to_drone | visual | 25.6776 ± 1.7530 | 9.5432 ± 0.4669 | 33.5487 ± 1.6668 |
| sues200 → university1652 | university1652_satellite_to_drone | full | 18.2596 ± 1.2436 | 6.9668 ± 0.4377 | 25.8850 ± 2.2712 |
| sues200 → university1652 | university1652_street_to_satellite | visual | 0.2585 ± 0.0976 | 0.7036 ± 0.1123 | 1.1487 ± 0.1419 |
| sues200 → university1652 | university1652_street_to_satellite | full | 0.2326 ± 0.0000 | 0.7434 ± 0.0454 | 1.2542 ± 0.0908 |
| university1652 → sues200 | sues200_satellite_to_uav_150m | visual | 19.5833 ± 4.0182 | 12.8024 ± 1.6706 | 25.4032 ± 3.8489 |
| university1652 → sues200 | sues200_satellite_to_uav_150m | full | 12.9167 ± 1.9094 | 9.0851 ± 0.7383 | 18.4877 ± 2.0942 |
| university1652 → sues200 | sues200_satellite_to_uav_200m | visual | 26.2500 ± 5.0000 | 16.8666 ± 3.3538 | 33.6653 ± 5.4160 |
| university1652 → sues200 | sues200_satellite_to_uav_200m | full | 15.4167 ± 1.4434 | 12.0971 ± 0.5583 | 21.4012 ± 1.8102 |
| university1652 → sues200 | sues200_satellite_to_uav_250m | visual | 30.0000 ± 3.7500 | 21.2939 ± 2.8945 | 36.8496 ± 3.1206 |
| university1652 → sues200 | sues200_satellite_to_uav_250m | full | 20.4167 ± 2.6021 | 15.2538 ± 0.3555 | 26.6577 ± 3.1452 |
| university1652 → sues200 | sues200_satellite_to_uav_300m | visual | 34.5833 ± 5.6366 | 24.4825 ± 2.5443 | 40.2417 ± 5.1207 |
| university1652 → sues200 | sues200_satellite_to_uav_300m | full | 19.5833 ± 1.9094 | 16.4768 ± 0.3712 | 26.0142 ± 0.6046 |
| university1652 → sues200 | sues200_uav_150m_to_satellite | visual | 19.1417 ± 2.3314 | 24.5367 ± 2.3951 | 29.9317 ± 2.4974 |
| university1652 → sues200 | sues200_uav_150m_to_satellite | full | 14.5917 ± 0.9268 | 19.6592 ± 0.6661 | 24.7266 ± 0.6632 |
| university1652 → sues200 | sues200_uav_200m_to_satellite | visual | 23.9000 ± 2.7185 | 29.5464 ± 2.7843 | 35.1928 ± 2.8833 |
| university1652 → sues200 | sues200_uav_200m_to_satellite | full | 16.0667 ± 0.7974 | 21.6247 ± 0.7075 | 27.1828 ± 0.6603 |
| university1652 → sues200 | sues200_uav_250m_to_satellite | visual | 27.2750 ± 2.3681 | 32.9749 ± 2.4630 | 38.6748 ± 2.5745 |
| university1652 → sues200 | sues200_uav_250m_to_satellite | full | 18.6083 ± 0.9856 | 24.3334 ± 0.7769 | 30.0584 ± 0.5976 |
| university1652 → sues200 | sues200_uav_300m_to_satellite | visual | 29.9500 ± 2.7915 | 35.6023 ± 2.9193 | 41.2547 ± 3.0591 |
| university1652 → sues200 | sues200_uav_300m_to_satellite | full | 19.5333 ± 1.1015 | 25.2737 ± 0.9710 | 31.0140 ± 0.8507 |

## Full minus Visual

Each contrast is the mean of three same-number seed differences. Values below are 100 × the fraction difference: percentage points for R@1/mAP and scaled points for MRR. They are descriptive, without significance claims.

| Source → target | Task | ΔR@1 | ΔmAP | ΔMRR |
|---|---|---:|---:|---:|
| sues200 → university1652 | university1652_drone_to_satellite | -2.8310 | -3.2063 | -3.5816 |
| sues200 → university1652 | university1652_satellite_to_drone | -7.4180 | -2.5764 | -7.6636 |
| sues200 → university1652 | university1652_street_to_satellite | -0.0258 | +0.0398 | +0.1055 |
| university1652 → sues200 | sues200_satellite_to_uav_150m | -6.6667 | -3.7173 | -6.9156 |
| university1652 → sues200 | sues200_satellite_to_uav_200m | -10.8333 | -4.7694 | -12.2641 |
| university1652 → sues200 | sues200_satellite_to_uav_250m | -9.5833 | -6.0401 | -10.1919 |
| university1652 → sues200 | sues200_satellite_to_uav_300m | -15.0000 | -8.0057 | -14.2275 |
| university1652 → sues200 | sues200_uav_150m_to_satellite | -4.5500 | -4.8776 | -5.2051 |
| university1652 → sues200 | sues200_uav_200m_to_satellite | -7.8333 | -7.9217 | -8.0100 |
| university1652 → sues200 | sues200_uav_250m_to_satellite | -8.6667 | -8.6415 | -8.6164 |
| university1652 → sues200 | sues200_uav_300m_to_satellite | -10.4167 | -10.3286 | -10.2406 |

## Evidence and limits

Root adoption SHA256: `fb7588357afa3e225b67088437233db397c067131fb8bc6adf97ce9ccbdd3bdd`. Transfer review SHA256: `b0627920c9e8ab1da0dbc6d2d48795b3abe68cf3b79f7d7dba7afa9bba3847c7`.

- No checkpoint bytes loaded or rehashed; historical inherited SHA plus stable stat does not prove current bytes.
- University visual sources retain original first12 inventory historical whole-file SHA edge gap; no new historical provenance invented.
- Original source checkpoint loading/full-state inspection and producer source gate were not independently re-executed.
- Full cache and image-content SHA inherited; actual metadata and memberships checked, not full cache/image-content rehash.
- Stored AP/RR/margin aggregation checked; no model inference/full ranking/AP recomputation from all positive ranks.
- Original subprocess.run child return0 and parent pipeline Popen exit0 plus current stage PID observation; no independent launcher/interpreter exit handles.
- Actual NumPy runtime not imported; original completion functions ran in bounded stdlib compatibility environment.
- This aggregation reads only adopted sealed metrics; it does not rerun any completion gate, query audit, model, ranking or AP computation.
- Each group contains seed 1/2/3 equally weighted. Sample SD has denominator n-1=2; it is not SE or a confidence interval.
- Full-minus-Visual is descriptive within each identical transfer direction/task only, paired by seed number. No hypothesis test or significance claim.
- No pooling across retrieval tasks, altitudes, directions, datasets or query counts. Metrics remain fractions in machine-readable tables.
- Displayed R@1/mAP differences x100 are percentage points; MRR differences x100 are scaled MRR points, not relative percentage gains.
