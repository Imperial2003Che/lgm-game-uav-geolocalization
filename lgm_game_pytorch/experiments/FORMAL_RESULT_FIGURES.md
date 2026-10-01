# Formal result figure pipeline

`plot_frozen_formal_results.py` is the CPU-only publication figure stage for
the frozen 36+6 experiment matrix. It does not train or evaluate a model.

## Evidence gate

The plotter accepts input only when all of the following are true:

- `aggregate_manifest.json` has `status: completed` and a valid payload hash;
- all 36 main runs, 6 sensitivity runs, and 33 task-by-seed pairwise tests are
  marked complete;
- every required aggregate CSV matches the SHA-256 and byte count recorded in
  the aggregate manifest;
- the raw 198 main-result rows exactly reproduce all means and sample SDs in
  the 66 task-by-variant summary rows;
- University-1652 contains exactly three official tasks and SUES-200 exactly
  eight altitude/direction tasks;
- all bootstrap rows use 10,000 path-paired queries and all McNemar tests
  belong to the completed 33-test Holm family;
- no macro average or duplicate overall-plus-subset row is present.

`partial_audit_only` input is rejected before an output directory is created.
Missing values are never estimated, interpolated, or replaced by examples.

## Formal command

Run after the completed aggregation command:

```powershell
& 'C:\项目\.venvs\lgm-baselines\Scripts\python.exe' `
  'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\experiments\plot_frozen_formal_results.py' `
  --aggregate-dir 'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\results\formal_matrix_aggregate' `
  --output-dir 'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_paper_latex\figures\formal_results'
```

Formal PNG export is fixed at 600 dpi. PDF and SVG use editable text.

## Generated bundle

Each figure has PDF, SVG, PNG, and an independent source CSV:

1. `formal_main_university1652_variants`: R@1 mean ± sample SD heatmap and
   official-mAP mean ± sample SD point plot for all three tasks and six
   variants.
2. `formal_main_sues200_variants`: the same task-specific view for all eight
   SUES altitude/direction tasks.
3. `formal_visual_vs_full_forest`: all 33 seed-specific full-minus-visual R@1
   effects with 10,000-query paired 95% intervals; marker fill reflects the
   exact McNemar result after one 33-test Holm correction.
4. `formal_sues_altitude_curves`: four-altitude curves in both directions for
   R@1 and official mAP, with all six variants and three-seed sample SD.
5. `formal_sensitivity`: task-specific seed-1 backbone/dimension sensitivity.
   If a complete measured complexity column exists, the figure also adds
   task-specific accuracy–complexity panels. If none exists, the complexity
   panels are explicitly omitted; complexity is never inferred from model
   names.

`formal_figure_manifest.json` records source hashes, script hash, figure
contracts, statistics definitions, export QA, and whether a measured
complexity field was available.

## Planned `main.tex` connection

Do not include any figure until `formal_figure_manifest.json` has
`status: completed`. Once that gate passes, the PDF assets can be connected
without conversion. Suggested placements are:

```latex
% Main ablation block, immediately after the formal main-result table.
\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth]
    {figures/formal_results/formal_main_university1652_variants.pdf}
  \caption{Task-specific formal results on University-1652.}
  \label{fig:formal-main-university}
\end{figure*}

% SUES task and altitude block.
\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth]
    {figures/formal_results/formal_main_sues200_variants.pdf}
  \caption{Task-specific formal results on SUES-200.}
  \label{fig:formal-main-sues}
\end{figure*}

\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth]
    {figures/formal_results/formal_sues_altitude_curves.pdf}
  \caption{Altitude-dependent performance in both retrieval directions.}
  \label{fig:formal-sues-altitude}
\end{figure*}

% Statistical comparison and sensitivity blocks.
\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth]
    {figures/formal_results/formal_visual_vs_full_forest.pdf}
  \caption{Query-paired visual-to-full effects across tasks and seeds.}
  \label{fig:formal-paired-effects}
\end{figure*}

\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth]
    {figures/formal_results/formal_sensitivity.pdf}
  \caption{Task-specific backbone and embedding-dimension sensitivity.}
  \label{fig:formal-sensitivity}
\end{figure*}
```

The final manuscript captions should be expanded from the corresponding
figure-contract entries in `formal_figure_manifest.json`, including `n=3`
seeds for main curves, sample SD definitions, the 10,000-query bootstrap,
exact McNemar/Holm family, and the seed-1-only limitation of sensitivity
runs. This file documents the connection only; it does not edit `main.tex`.

## Synthetic CPU test

```powershell
& 'C:\项目\.venvs\lgm-baselines\Scripts\python.exe' `
  'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\tests\test_plot_frozen_formal_results.py' `
  -v
```

The test creates a temporary synthetic 36+6 aggregation, exercises all five
figures and all three export formats, verifies editable SVG text and source
CSV row counts, confirms that partial input writes no figures, and checks both
the measured-complexity and no-complexity branches. Synthetic values remain in
the operating-system temporary directory and are not publication evidence.
