from __future__ import annotations

import argparse
import json
from pathlib import Path


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def count_images(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*") if item.suffix.lower() in IMAGE_EXTS)


def exists(path: Path) -> bool:
    return path.exists()


def university_1652(root: Path) -> dict:
    paths = {
        "train_drone": root / "train" / "drone",
        "train_satellite": root / "train" / "satellite",
        "test_query_drone": root / "test" / "query_drone",
        "test_gallery_satellite": root / "test" / "gallery_satellite",
        "test_query_satellite": root / "test" / "query_satellite",
        "test_gallery_drone": root / "test" / "gallery_drone",
    }
    return {
        "dataset": "University-1652",
        "detected": all(exists(path) for path in paths.values()),
        "counts": {name: count_images(path) for name, path in paths.items()},
    }


def sues_200(root: Path) -> dict:
    paths = {
        "training": root / "Dataset" / "Training",
        "testing": root / "Dataset" / "Testing",
        "raw_training": root / "Training",
        "raw_testing": root / "Testing",
    }
    detected = (
        exists(paths["training"]) and exists(paths["testing"])
    ) or (
        exists(paths["raw_training"]) and exists(paths["raw_testing"])
    )
    return {
        "dataset": "SUES-200",
        "detected": detected,
        "counts": {name: count_images(path) for name, path in paths.items()},
    }


def geotext_1652(root: Path) -> dict:
    paths = {
        "train": root / "train",
        "test_query": root / "test" / "query(701)",
        "test_gallery": root / "test" / "gallery_no_train(250)",
        "train_json": root / "train.json",
        "test_json": root / "test_951_version.json",
    }
    return {
        "dataset": "GeoText-1652",
        "detected": exists(paths["train"]) and exists(paths["test_query"]),
        "counts": {
            name: (count_images(path) if path.is_dir() else int(path.exists()))
            for name, path in paths.items()
        },
    }


def uav_visloc(root: Path) -> dict:
    numbered = [
        item for item in root.iterdir()
        if item.is_dir() and item.name.isdigit() and len(item.name) == 2
    ] if root.exists() else []
    counts = {}
    for item in numbered:
        counts[f"{item.name}_drone"] = count_images(item / "drone")
        counts[f"{item.name}_satellite"] = count_images(item)
    return {
        "dataset": "UAV-VisLoc",
        "detected": exists(root / "satellite_coordinates_range.csv") and bool(numbered),
        "counts": counts,
    }


def scan_dataset(root: Path) -> list[dict]:
    return [
        university_1652(root),
        sues_200(root),
        geotext_1652(root),
        uav_visloc(root),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Check real UAV geo-localization dataset layouts.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("datasets"),
        help="Dataset root, e.g. datasets/University-1652",
    )
    args = parser.parse_args()
    report = {
        "root": str(args.root.resolve()),
        "exists": args.root.exists(),
        "candidates": scan_dataset(args.root),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
