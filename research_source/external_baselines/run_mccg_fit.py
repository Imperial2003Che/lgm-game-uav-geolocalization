#!/usr/bin/env python3
"""Run one full MCCG fit with a final-epoch and no-test-access gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from external_baselines.fetch_and_verify_sources import IntegrityError
from external_baselines.mccg_adapter import (
    add_fit_arguments,
    build_run_config,
    run_fit,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_fit_arguments(parser)
    args = parser.parse_args()
    try:
        run_config = build_run_config(args)
        if args.preflight_only:
            print(json.dumps(run_config, indent=2, sort_keys=True))
            return 0
        manifest = run_fit(args, run_config)
    except (IntegrityError, OSError, ValueError) as error:
        raise SystemExit(f"ERROR: {error}") from error
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
