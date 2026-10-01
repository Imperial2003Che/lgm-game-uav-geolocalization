# Transactions-scale experiment guide

This document maps the extension code, execution order, and evidence gates.
The governing design is `TRANSACTIONS_EXTENSION_PROTOCOL.md`; the frozen
42-fit primary design remains governed by `FORMAL_EXPERIMENT_PROTOCOL.md`.

## 1. Current state

| Block | Registered workload | Current state | Manuscript-result status |
|---|---:|---|---|
| Primary | 36 main fits + 6 sensitivity fits | frozen matrix running serially | incomplete |
| T1 | 7 published-method fits + 70 full task evaluations | dual-dataset evaluator and refreshed static audit complete; GPU resource profile pending | no fit or evaluation started |
| T2 | 24 leave-one-height-out fits | static membership audit complete; primary gate pending | no fit started |
| T3 | 12 bidirectional transfer evaluations | static design audit complete; source-checkpoint gate pending | no evaluation started |
| T4 | 462 clean query-level stratum rows | implementation complete; 12-source gate pending | not executed |
| T5 | 66 native rows + 132 paired coverage comparisons | implementation complete; 12-source gate pending | not executed |
| T6 | efficiency and gallery scaling | primary component implemented; source and combined-baseline gates pending | not executed |

Static audits, data inventories, model-construction checks, and resource
feasibility runs are engineering evidence. They are never experimental
outcomes and must not be copied into paper result tables.

## 2. Code map

### Primary frozen matrix

- Core: `lgm_game_pytorch/lgm_game_pytorch/formal_retrieval.py`
- Matrix runner:
  `lgm_game_pytorch/experiments/run_frozen_formal_matrix.py`
- Ledger:
  `lgm_game_pytorch/runs/frozen_formal_matrix_ledger.json`
- Statistical aggregation:
  `lgm_game_pytorch/experiments/aggregate_frozen_formal_results.py`

The core, primary protocol, and primary runner are frozen. Do not edit them
during the registered matrix.

### T1 published-method reproductions

- Seven-row matrix:
  `external_baselines/transactions_t1_matrix.json`
- Serialized runner:
  `external_baselines/run_transactions_t1_matrix.py`
- QDFL-family adapter: `external_baselines/qdfl_adapter.py`
- MCCG adapter: `external_baselines/mccg_adapter.py`
- Shared full-query evaluator:
  `external_baselines/official_descriptor_evaluation.py`
- QDFL/FSRA/SDPL/CCR official evaluator:
  `external_baselines/qdfl_official_evaluation.py`
- MCCG official evaluator:
  `external_baselines/mccg_official_evaluation.py`
- Source registry:
  `external_baselines/transactions_baseline_registry.json`
- Initialization registry:
  `external_baselines/transactions_weight_registry.json`
- Environment lock:
  `external_baselines/transactions_environment_lock.json`
- Resource template:
  `external_baselines/transactions_t1_resource_profile.template.json`
- Persisted non-result static audit:
  `external_baselines/audits/transactions_t1_static_audit.json`

The template contains null feasibility fields by design and blocks training.
After the primary GPU matrix finishes, each registered configuration receives
one declared feasibility procedure: model construction, one complete optimizer
step, peak-memory measurement, and no official-test access. Only then may
`transactions_t1_resource_profile.json` be frozen.

T1 fitting never reads an official test root. After all seven final-epoch fit
manifests pass, the runner writes an immutable all-fits gate and only then
freezes full content inventories for University-1652 test and SUES-200. Every
fit is evaluated on ten tasks:

1. University-1652 D2S and S2D with every query and the complete gallery.
2. SUES-200 150/200/250/300 m in both directions, using the fixed 80 test
   identities as queries and all 200 identities in each gallery.

The seven evaluation processes therefore create 70 task-level results
(14 University-1652 and 56 SUES-200 transfer tasks). Street2S is explicitly
unsupported for this comparison because the pinned public baseline entry
points implement only D2S and S2D; no zero placeholder is produced.

Each completed evaluation contains immutable configuration and completion
manifests, metrics JSON/CSV, descriptor fingerprints, and one auditable NPZ
array bundle for every query task. The validator recomputes aggregate metrics,
checks Top-1 semantics, and verifies every artifact hash. Descriptor extraction
is serialized by task pair and altitude to keep the full-data protocol within
bounded host memory.

Generated gates and outputs will be placed under:

- `external_baselines/runs/transactions_t1/transactions_t1_all_fits_gate.json`
- `external_baselines/runs/transactions_t1/transactions_t1_official_test_inventory_gate.json`
- `external_baselines/runs/transactions_t1/evaluations/<config>/seed_<n>/`

Third-party snapshots and initialization weights are kept outside the partner
folder and are identified by exact revision, file count, byte count, and
SHA-256 in the registries. This avoids silently redistributing unlicensed or
large upstream assets while preserving exact reproducibility.

### T2 leave-one-height-out training

- 24-row matrix:
  `lgm_game_pytorch/experiments/transactions_t2_heldout_matrix.json`
- Held-out adapter:
  `lgm_game_pytorch/experiments/run_sues_heldout_fit.py`
- Serialized runner:
  `lgm_game_pytorch/experiments/run_transactions_t2_heldout_matrix.py`

For each held-out altitude, only UAV fitting records at that altitude are
removed. All 120 official fitting identities and their satellite images remain.
The adapter records included/excluded memberships and writes them into the full
checkpoint. The runner blocks until the complete 42-fit primary gate passes.

### T3 cross-dataset transfer

- 12-row matrix:
  `lgm_game_pytorch/experiments/transactions_t3_transfer_matrix.json`
- Single-evaluation adapter:
  `lgm_game_pytorch/experiments/run_cross_dataset_evaluation.py`
- Serialized runner:
  `lgm_game_pytorch/experiments/run_transactions_t3_transfer_matrix.py`
- Persisted non-result audit:
  `lgm_game_pytorch/audits/transactions_t3_static_audit.json`

Each University-1652 `visual`/`full` source checkpoint is evaluated on all
eight SUES-200 tasks, and each SUES-200 source checkpoint is evaluated on the
three University-1652 tasks. Seeds are 1, 2, and 3. There is no target-dataset
fitting, selection, thresholding, or calibration.

The T3 completion validator requires complete query-level arrays and
independently checks:

1. exact task and query coverage;
2. source checkpoint identity and final-epoch provenance;
3. Top-1 label/correctness/reciprocal-rank semantic agreement;
4. Recall@1/5/10/20, official trapezoidal mAP, MRR, and mean-margin
   recomputation;
5. exact JSON/CSV agreement and artifact SHA-256 values.

### T4/T5 query-level analyses

- Auditable primitives:
  `lgm_game_pytorch/experiments/transactions_query_analysis.py`
- Complete-gate runner:
  `lgm_game_pytorch/experiments/run_transactions_query_analysis.py`
- Real output location after all 12 sources complete:
  `lgm_game_pytorch/analysis/transactions_t4_t5/`

The runner validates the complete primary training and official-evaluation
manifests for both datasets, `visual` and `full`, and all three seeds before it
creates an output directory. It then aligns every paired array by canonical
query path and path-derived identity.

T4 generates content-entropy, style-entropy, visual-margin, and
visual/semantic-agreement strata. T5 generates native risk--coverage,
fixed-margin calibration, and paired coverage-constrained comparisons. Exact
definitions, the 100-query inference threshold, 10,000 paired bootstrap
resamples, and Holm families are frozen in
`TRANSACTIONS_EXTENSION_PROTOCOL.md`.

These files are code only at present. There is no T4/T5 result artifact until
the source gate passes and the runner completes.

### T6 efficiency and gallery scaling

- Auditable primitives:
  `lgm_game_pytorch/experiments/transactions_efficiency_analysis.py`
- Primary-model component runner:
  `lgm_game_pytorch/experiments/run_transactions_formal_efficiency.py`
- Component output location after its four-source gate passes:
  `lgm_game_pytorch/analysis/transactions_t6_formal/`

The component measures seed-1 `visual` and `full` on both datasets with the
same exclusive RTX 4060 Laptop GPU. It checks exact parameter/MAC counts,
batch-1 encoding latency and peak memory, complete score-plus-ranking latency,
descriptor storage, and positive-preserving gallery scaling. Complete-gallery
metrics must reproduce the previously completed official evaluation.

This component is deliberately withheld from manuscript use even after a real
run. Its manifest remains `manuscript_result=false` and
`full_t6_complete=false` until the locally trained T1 methods are measured with
the same timing harness and the combined T6 audit passes.

## 3. Required execution order

1. Finish and audit all 42 frozen primary fits.
2. Run official primary evaluation and complete statistical aggregation.
3. Run the 12 T3 transfer evaluations from the completed source checkpoints.
4. With the GPU otherwise idle, perform the registered T1 feasibility
   procedures and freeze the resource profile.
5. Freeze the extension ledger.
6. Run all seven T1 fits and all 24 T2 fits serially. A failed run is preserved
   and diagnosed; the runner never silently retries it.
7. After the seven-fit T1 gate passes, freeze both official-test content
   inventories and run all 70 T1 task evaluations serially.
8. Run official T2 evaluations, T4/T5 query-level analyses, and T6 timing.
9. Generate paper tables and figures only from complete manifests.

No second Python GPU process may overlap any registered fit, evaluation, or
timing run.

## 4. Read-only audit commands

Run these from PowerShell. They validate registered inputs but do not start a
fit.

### T1

```powershell
& 'C:\项目\.venvs\lgm-transactions\Scripts\python.exe' -B `
  'C:\项目\LGM-GAME-Partner-Delivery-20260724\external_baselines\run_transactions_t1_matrix.py' `
  --delivery-root 'C:\项目\LGM-GAME-Partner-Delivery-20260724' `
  --train-root 'C:\项目\IMTMN\datasets\University-1652\train' `
  --external-work-root 'C:\项目\LGM-GAME-External-Baseline-Work' `
  --qdfl-python 'C:\项目\.venvs\lgm-transactions\Scripts\python.exe' `
  --mccg-python 'C:\项目\.venvs\lgm-mccg\Scripts\python.exe' `
  --stage audit
```

### T2

```powershell
& 'C:\项目\.venvs\lgm-baselines\Scripts\python.exe' -B `
  'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\experiments\run_transactions_t2_heldout_matrix.py' `
  --delivery-root 'C:\项目\LGM-GAME-Partner-Delivery-20260724' `
  --university-root 'C:\项目\IMTMN\datasets\University-1652' `
  --sues-root 'C:\项目\IMTMN\datasets\SUES-200' `
  --python 'C:\项目\.venvs\lgm-baselines\Scripts\python.exe' `
  --stage audit
```

### T3

```powershell
& 'C:\项目\.venvs\lgm-baselines\Scripts\python.exe' -B `
  'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\experiments\run_transactions_t3_transfer_matrix.py' `
  --delivery-root 'C:\项目\LGM-GAME-Partner-Delivery-20260724' `
  --university-root 'C:\项目\IMTMN\datasets\University-1652' `
  --sues-root 'C:\项目\IMTMN\datasets\SUES-200' `
  --python 'C:\项目\.venvs\lgm-baselines\Scripts\python.exe' `
  --stage audit `
  --audit-output 'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\audits\transactions_t3_static_audit.json'
```

The T3 audit must report
`static_design_verified_source_gate_pending`, `manuscript_result=false`,
`model_constructed=false`, and `evaluation_executed=false` until its 12 source
checkpoints are complete.

## 5. Future serialized T1 execution

Do not run this command while the primary matrix or another GPU process is
active. It also requires the completed feasibility procedures and a frozen
`transactions_t1_resource_profile.json`.

```powershell
& 'C:\项目\.venvs\lgm-transactions\Scripts\python.exe' -B `
  'C:\项目\LGM-GAME-Partner-Delivery-20260724\external_baselines\run_transactions_t1_matrix.py' `
  --delivery-root 'C:\项目\LGM-GAME-Partner-Delivery-20260724' `
  --train-root 'C:\项目\IMTMN\datasets\University-1652\train' `
  --test-root 'C:\项目\IMTMN\datasets\University-1652\test' `
  --sues-root 'C:\项目\IMTMN\datasets\SUES-200' `
  --sues-manifest 'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\manifests\sues200_official_train_ids.yaml' `
  --external-work-root 'C:\项目\LGM-GAME-External-Baseline-Work' `
  --qdfl-python 'C:\项目\.venvs\lgm-transactions\Scripts\python.exe' `
  --mccg-python 'C:\项目\.venvs\lgm-mccg\Scripts\python.exe' `
  --resource-profile 'C:\项目\LGM-GAME-Partner-Delivery-20260724\external_baselines\transactions_t1_resource_profile.json' `
  --stage all
```

## 6. Result-admission checklist

A number may enter the manuscript only when all applicable checks pass:

- the registered row has a completed ledger event;
- source, code, data, environment, command, and checkpoint hashes match;
- the output manifest and every referenced artifact hash validate;
- all official queries and complete galleries were used;
- no official-test outcome affected fitting or checkpoint selection;
- aggregate values recompute from retained per-query arrays;
- the declared comparison family has its confidence interval, effect size,
  exact paired test where applicable, and Holm correction;
- no debug, feasibility, partial, failed, or interrupted attempt is counted.
