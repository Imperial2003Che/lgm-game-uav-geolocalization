# Frozen 36+6 result aggregation

`aggregate_frozen_formal_results.py` is the CPU-only evidence gate for the
formal experiment matrix in `FORMAL_EXPERIMENT_PROTOCOL.md`.

## Final aggregation

Run this only after the matrix runner has completed all training and official
evaluation jobs:

```powershell
& 'C:\项目\.venvs\lgm-baselines\Scripts\python.exe' `
  'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\experiments\aggregate_frozen_formal_results.py' `
  --delivery-root 'C:\项目\LGM-GAME-Partner-Delivery-20260724'
```

The default is fail-closed. It accepts exactly 36 main runs and 6 sensitivity
runs with completed manifests, 80 training epochs, matching frozen
configuration/code/checkpoint/artifact hashes, and exact official task sets.
It recomputes R@1/5/10/20, official trapezoidal mAP, MRR, and mean top-1
margin from every per-query array before aggregation.

## Progress audit

During training, an explicitly non-final audit can be generated with:

```powershell
& 'C:\项目\.venvs\lgm-baselines\Scripts\python.exe' `
  'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\experiments\aggregate_frozen_formal_results.py' `
  --delivery-root 'C:\项目\LGM-GAME-Partner-Delivery-20260724' `
  --allow-partial
```

Partial output is labelled `partial_audit_only`; missing cells are left empty,
never imputed. Holm-adjusted inference is withheld until all 33 planned
visual-versus-full task-by-seed comparisons exist.

## Final outputs

The default output directory is
`lgm_game_pytorch/results/formal_matrix_aggregate/`.

- `run_audit.csv` and `matrix_completeness_audit.json`: all 42 expected runs
  and their evidence-gate status.
- `main_metrics_by_seed.csv`: task-level raw metrics for all main runs.
- `main_three_seed_mean_sample_sd.csv`: mean and sample SD over seeds 1, 2,
  and 3 for each dataset/task/variant.
- `sensitivity_metrics.csv` and `sensitivity_with_main_reference.csv`: the six
  frozen sensitivity runs, with the main full seed-1 setting as a clearly
  labelled reference in the latter file.
- `visual_vs_full_paired_bootstrap.csv`: 10,000 path-paired query bootstrap
  samples for R@1 differences, separately for every official task and seed.
- `visual_vs_full_exact_mcnemar_holm.csv`: two-sided exact McNemar tests. The
  complete output uses one Holm family across all 33 task-by-seed tests.
  Probabilities are retained in log10 space and underflow is printed as
  `<1e-300`, never as zero.
- `input_artifact_sha256.csv`, `aggregate_results.json`, and
  `aggregate_manifest.json`: traceability and machine-readable results.
- `*.tex`: task-level manuscript table fragments. University-1652 has three
  separate tasks and SUES-200 has eight separate altitude/direction tasks.
  No macro row or duplicate overall-plus-subset average is generated.

## CPU-only synthetic test

```powershell
& 'C:\项目\.venvs\lgm-baselines\Scripts\python.exe' `
  'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\tests\test_aggregate_frozen_formal_results.py' `
  -v
```

The test constructs a complete synthetic 36+6 directory, validates all 66
task-by-variant three-seed summary rows and 33 pairwise tests, checks
underflow-safe p-value formatting, and exercises both fail-closed and explicit
partial modes. Synthetic fixture values are temporary test data and are never
written to the delivery result directory.
