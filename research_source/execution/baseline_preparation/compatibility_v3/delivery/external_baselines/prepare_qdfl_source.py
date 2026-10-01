#!/usr/bin/env python3
"""Materialize the pinned QDFL source with auditable path-only compatibility patches."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from external_baselines.fetch_and_verify_sources import IntegrityError
from external_baselines.source_patching import prepare_qdfl_source


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path(__file__).with_name("transactions_baseline_registry.json"),
    )
    args = parser.parse_args()
    try:
        manifest = prepare_qdfl_source(
            upstream_root=args.upstream_root,
            destination=args.destination,
            registry_path=args.registry,
        )
    except (IntegrityError, OSError, ValueError) as error:
        raise SystemExit(f"ERROR: {error}") from error
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
