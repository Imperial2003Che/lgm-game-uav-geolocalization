# T3 transfer descriptive analysis

The verified results are in `result_20260929_061052_519928`. This directory is an analysis of the 12 adopted T3 runs, not another experimental run. Its 66 seed-task rows produce 22 task-variant groups and 11 Full-minus-Visual contrasts. All groups use seeds 1, 2 and 3 with equal weights; sample SD uses denominator 2.

In `ANALYSIS.md`, **mAP means the official trapezoidal mAP used by the frozen University-1652/SUES evaluator**, specifically the `official_trapezoid_mAP` field. It is not a redefinition of AP. R@1 and mAP multiplied by 100 are percentages; differences in those quantities are percentage points. MRR is a fraction and its displayed difference is 100 times the MRR difference. Machine-readable results preserve the fraction units.

`source_dataset` and `target_dataset` identify the cross-dataset training/evaluation direction. The separate `task` identifies retrieval direction and, for SUES, altitude within the target dataset. No overall score combines these different tasks.

Descriptively, Full has a lower three-seed mean R@1 than Visual on each of the 11 target tasks. For University-trained models evaluated on SUES, all eight task-specific mean R@1, official trapezoidal mAP and MRR differences are negative. For SUES-trained models evaluated on University, drone-to-satellite and satellite-to-drone differences are negative for all three metrics; street-to-satellite has a negative R@1 difference but small positive mAP and MRR differences. These are three-seed observations under the adopted protocol and inherited evidence limits. They do not establish statistical significance, a mechanism, or general superiority of either variant beyond these tasks.

`REPORT.json` and `DELIVERY.json` bind the aggregation source, root adoption, original transfer audit, 12 sealed metrics and all seven generated data/analysis artifacts. This companion README clarifies interpretation without modifying any of those sealed files. The inherited checkpoint and cache/image-content SHA limitations, historical inventory edge gap, bounded validator runtime and absence of a new model/full-ranking/AP computation remain in force.
