#!/usr/bin/env python3
"""Create an immutable, auditable software-environment lock for T1 baselines."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


SCHEMA = "lgm-game.transactions-environment-lock.v1"
SELECTED_PACKAGES = (
    "albumentations",
    "einops",
    "h5py",
    "matplotlib",
    "numpy",
    "opencv-python",
    "opencv-python-headless",
    "pandas",
    "pillow",
    "pytorch-lightning",
    "pytorch-metric-learning",
    "pyyaml",
    "scikit-image",
    "scikit-learn",
    "timm",
    "tokenizers",
    "torch",
    "torchmetrics",
    "torchvision",
    "transformers",
)


def canonical_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def canonical_object_sha256(payload: Any) -> str:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_checked(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed ({completed.returncode}): {command}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed.stdout


def inspect_environment(python: Path) -> dict[str, Any]:
    python = python.resolve(strict=True)
    probe = r"""
import importlib.metadata as metadata
import json
import platform
import sys

rows = sorted({
    (
        str(distribution.metadata.get("Name", "")).strip().lower(),
        distribution.version,
    )
    for distribution in metadata.distributions()
    if str(distribution.metadata.get("Name", "")).strip()
})
print(json.dumps({
    "executable": sys.executable,
    "python": sys.version,
    "platform": platform.platform(),
    "distributions": rows,
}, sort_keys=True))
"""
    raw = run_checked([str(python), "-I", "-c", probe]).strip()
    payload = json.loads(raw)
    distributions = [list(row) for row in payload.pop("distributions")]
    by_name = {name: version for name, version in distributions}
    freeze_lines = [
        line.strip()
        for line in run_checked(
            [str(python), "-m", "pip", "freeze", "--all"]
        ).splitlines()
        if line.strip()
    ]
    pip_check = run_checked([str(python), "-m", "pip", "check"]).strip()
    return {
        **payload,
        "interpreter_path": str(python),
        "interpreter_bytes": python.stat().st_size,
        "selected_packages": {
            name: by_name.get(name, "ABSENT") for name in SELECTED_PACKAGES
        },
        "installed_distributions": {
            "count": len(distributions),
            "sha256": canonical_object_sha256(distributions),
            "rows": distributions,
        },
        "pip_freeze": {
            "line_count": len(freeze_lines),
            "sha256": canonical_object_sha256(freeze_lines),
            "lines": freeze_lines,
        },
        "pip_check": {
            "status": "passed",
            "stdout": pip_check,
        },
    }


def artifact(path: Path) -> dict[str, Any]:
    path = path.resolve(strict=True)
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def atomic_write(path: Path, payload: Any, replace: bool) -> None:
    serialized = canonical_bytes(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() == serialized:
            return
        if not replace:
            raise RuntimeError(
                f"Existing environment lock differs; pass --replace explicitly: {path}"
            )
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        raise RuntimeError(f"Refusing to overwrite stale temporary file: {temporary}")
    temporary.write_bytes(serialized)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qdfl-python", type=Path, required=True)
    parser.add_argument("--mccg-python", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    payload = {
        "schema_version": SCHEMA,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": (
            "Freeze the non-bundled local runtimes used by the registered "
            "Transactions T1 official-code baseline reproductions."
        ),
        "environments": {
            "qdfl_framework": inspect_environment(args.qdfl_python),
            "mccg": inspect_environment(args.mccg_python),
        },
        "compatibility_disclosures": {
            "qdfl_framework": [
                (
                    "The local Windows runtime uses torch 2.11.0+cu126 and "
                    "torchvision 0.26.0+cu126 instead of the upstream torch "
                    "2.1/torchvision 0.16 pair."
                ),
                (
                    "xFormers is disabled because the upstream pinned build is "
                    "not ABI-compatible with this runtime; the upstream "
                    "standard-PyTorch attention fallback is used."
                ),
                (
                    "OpenCV 4.13 is retained to maintain the NumPy 2.2 ABI; "
                    "the upstream requirement file contains mutually "
                    "incompatible OpenCV pins."
                ),
            ],
            "mccg": [
                (
                    "The local Windows runtime uses torch 2.11.0+cu126 and "
                    "torchvision 0.26.0+cu126 while retaining the official "
                    "timm 0.5.4 dependency."
                ),
                (
                    "Deterministic algorithms are requested with warn_only=True; "
                    "any emitted nondeterminism warnings remain in stderr."
                ),
            ],
        },
        "registered_artifacts": {
            "qdfl_adapter": artifact(root / "qdfl_adapter.py"),
            "mccg_adapter": artifact(root / "mccg_adapter.py"),
            "source_patching": artifact(root / "source_patching.py"),
            "source_registry": artifact(
                root / "transactions_baseline_registry.json"
            ),
            "weight_registry": artifact(
                root / "transactions_weight_registry.json"
            ),
        },
    }
    payload["payload_sha256"] = canonical_object_sha256(payload)
    atomic_write(args.output.resolve(), payload, args.replace)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
