# Published-method baseline sources

This directory contains the project-owned adapters, frozen source registry,
integrity checks, and run manifests for the Transactions-scale comparison
experiments. Third-party code is never silently mixed with project code.

## Source policy

- `transactions_baseline_registry.json` pins every upstream repository to an
  exact commit, archive byte count, archive SHA-256, and canonical source-tree
  SHA-256.
- `transactions_weight_registry.json` pins every initialization file to its
  authoritative HTTPS source, exact byte count, SHA-256, and load contract.
- `transactions_environment_lock.json` records the two isolated interpreters,
  all installed distributions, complete `pip freeze --all` outputs, successful
  `pip check` results, compatibility disclosures, and the exact adapter and
  registry hashes. The large environments themselves are not bundled.
- QDFL is MIT licensed. Its license and notice must remain attached to any
  redistributed snapshot.
- MCCG and SHAA do not declare a repository license in the pinned snapshots.
  Their source is therefore kept outside the partner-delivery folder and is
  fetched only into a user-selected working directory.
- SHAA is not locally trained because the pinned official repository is
  incomplete: the training entry point imports four absent source trees. It
  remains a literature comparison only.
- Third-party source and weight files are kept in the separate reproducibility
  work directory. The partner package contains the adapters, registries,
  patch recipes, and verification commands, not unlicensed source snapshots
  or multi-gigabyte model weights.

## Audited compatibility layers

- QDFL patch plan `207fad54...1064` materializes a 108-file tree with SHA-256
  `99cd2ffe...06a3`. It parameterizes dataset and four initialization paths,
  narrows fitting-only imports, and does not change an architecture, loss,
  optimizer, or epoch schedule.
- MCCG patch plan `a7e40504...cf69` materializes a 54-file external tree with
  SHA-256 `b196be37...ccde`. It pins the random seed and ConvNeXt-T
  initialization, writes artifacts outside the source tree, disables cuDNN
  benchmarking, replaces training-loss checkpoint selection with the fixed
  final epoch, and records peak allocated GPU memory.
- QDFL and MCCG use separate Python environments. MCCG keeps its published
  `timm==0.5.4`; QDFL uses its own declared dependency line and the upstream
  standard-PyTorch attention fallback when the published xFormers build is
  ABI-incompatible with the Windows torch runtime.
- The environment lock file has SHA-256
  `3c2b176e8c1bd706e0afa0f9f0bd62d73669549e47f16b2f1338ce05a4e8a087`.
  Its internal payload SHA-256 is
  `54bf50de942ee9759f262a0b3fd9173a37752451f10ee0ed5529d9ab101beef6`.

## Experimental controls

The adapters must preserve the published architecture, loss, optimizer, and
epoch schedule unless a compatibility change is explicitly recorded. They
also enforce controls that the upstream scripts do not provide:

1. caller-specified seeds and paths;
2. no official-test access during fitting;
3. a pre-specified final-epoch checkpoint;
4. append-only run events and artifact hashes;
5. separate fit, official evaluation, and aggregation stages;
6. no overwrite of an inconsistent or partially complete run.
7. a content hash over all 41,214 fitting images from the `satellite`,
   `street`, and `drone` views; the auxiliary `google` view is rejected;
8. explicit byte-count and SHA-256 verification of every initialization;
9. a complete dependency and CUDA-device fingerprint before fitting.
10. QDFL resume only from a full checkpoint containing model, optimizer,
    scheduler, mixed-precision scaler, loop, callback history, and
    Python/NumPy/Torch RNG states;
11. MCCG epoch markers and metric rows paired in sequence, with the copied
    training/model sources hashed against the pinned external tree.

The extension runner is not frozen until its adapters, tests, registry, and
protocol all pass the preflight audit. A planned row is not a result, and a
failed or incomplete row cannot enter the manuscript.
