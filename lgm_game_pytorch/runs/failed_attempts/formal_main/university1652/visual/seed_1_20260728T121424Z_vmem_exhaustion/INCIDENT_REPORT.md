# Formal-run incident report

## Scope

- Registered run: `formal_main/university1652/visual/seed_1/resnet18/dim_512`
- Attempt start: 2026-07-28 12:14:24 UTC
- Attempt end: 2026-07-28 12:18:32 UTC
- Frozen runner return code: `3221226505` (`0xC0000409`)
- Admissible training artifact produced: no

## Evidence

The first Python exception was:

`RuntimeError: cuDNN error: CUDNN_STATUS_EXECUTION_FAILED`

During DataLoader cleanup, Python also reported:

`RuntimeError: can't start new thread`

Windows Resource Exhaustion Detector event 2004 at
2026-07-28 12:17:38 UTC recorded:

- system commit charge: 65,680,232,448 bytes;
- system commit limit: 65,732,542,464 bytes;
- physical memory usage: 15,994,658,816 of 16,340,418,560 bytes;
- training process PID 249000 commit charge: 7,373,770,752 bytes;
- Python child PID 243420 commit charge: 1,862,656,000 bytes;
- Python child PID 235328 commit charge: 1,861,771,264 bytes.

No contemporaneous NVIDIA display-driver reset or WHEA hardware-error event was
found. Windows Error Reporting subsequently recorded the Python fast-fail in
`ucrtbase.dll`; this is the final abort path, not the initiating error.

## Determination

The attempt failed because the host exhausted system commit/virtual memory while
the CUDA training process and spawned DataLoader workers were active. The run
did not reach epoch completion and created no checkpoint or run manifest.
Therefore none of this attempt's outputs are eligible for analysis.

## Preservation and recovery rule

The original four files are retained unchanged in this directory. Their
SHA-256 digests are:

- `process_stderr.log`: `8b69a58bd5c6e7b0d0dbfd3d1dd63885b3ae86bbf7a01cfd744cb0f8042523fe`
- `process_stdout.log`: `e9b625c9e40886e06f81161632cd29c8534d9353f2f8eb97b1975fd6767538c3`
- `run.log`: `336c41782695234142deb111996df79a025a0a9fbb708f9197d296486bfcfdd5`
- `run_config.json`: `7d9e4c26e559d39c1665a07afe1f7b41bab053cec6163039664a74a819a05009`

The registered output path was cleared only by moving this complete failed
attempt to the present archive. A new attempt may start from epoch zero under
the unchanged frozen protocol and code. The frozen ledger retains the failed
event and will append the subsequent attempt rather than replacing its history.
