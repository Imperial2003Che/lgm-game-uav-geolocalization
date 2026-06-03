from __future__ import annotations

import argparse
from pathlib import Path

from .data import build_pair_records
from .text_prompts import PromptProvider


"""Compatibility CLI for building VLM prompt caches.

Prefer `generate_prompts.py` for the documented workflow. This module keeps the
older `--output-jsonl` spelling as a small convenience wrapper.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build VLM content/style prompt cache for LGM-GAME.")
    parser.add_argument("--dataset", choices=["sues200", "university1652"], default="sues200")
    parser.add_argument("--data-root", type=str, default="/Users/chenche/Documents/dataset/SUES-200")
    parser.add_argument("--split", choices=["train", "test"], default="train")
    parser.add_argument("--output-jsonl", type=str, required=True)
    parser.add_argument("--prompt-backend", choices=["vlgeo", "blip", "clip", "blip_clip", "llava", "metadata"], default="vlgeo")
    parser.add_argument("--max-classes", type=int, default=32)
    parser.add_argument("--samples-per-class", type=int, default=1)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--caption-model", type=str, default="Salesforce/blip-image-captioning-base")
    parser.add_argument("--clip-model", type=str, default="openai/clip-vit-base-patch32")
    parser.add_argument("--llava-model", type=str, default="llava")
    parser.add_argument("--llava-endpoint", type=str, default="http://localhost:11434/api/generate")
    parser.add_argument("--prompt-device", type=str, default="auto")
    parser.add_argument("--allow-prompt-fallback", action="store_true")
    parser.add_argument("--use-class-token", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = Path(args.output_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    provider = PromptProvider(
        backend=args.prompt_backend,
        cache_path=output_path,
        caption_model=args.caption_model,
        clip_model=args.clip_model,
        llava_model=args.llava_model,
        llava_endpoint=args.llava_endpoint,
        device=args.prompt_device,
        allow_fallback=args.allow_prompt_fallback,
    )
    records = build_pair_records(
        root=Path(args.data_root),
        dataset_name=args.dataset,
        split=args.split,
        max_classes=args.max_classes,
        samples_per_class=args.samples_per_class,
        seed=args.seed,
        use_class_token=args.use_class_token,
        prompt_provider=provider,
    )

    print(f"[done] split={args.split} backend={args.prompt_backend} records={len(records)} cache={output_path}")
    if records:
        print(f"[sample] content={records[0].content_text}")
        print(f"[sample] style={records[0].style_text}")


if __name__ == "__main__":
    main()
