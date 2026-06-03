from __future__ import annotations

import argparse
from pathlib import Path

from .data import CrossViewPairDataset, summarize_records
from .text_prompts import PromptVocabulary
from .utils import save_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate and cache VLM content/style prompts.")
    parser.add_argument("--dataset", choices=["sues200", "university1652"], default="sues200")
    parser.add_argument("--data-root", type=str, default="/Users/chenche/Documents/dataset/SUES-200")
    parser.add_argument("--split", choices=["train", "test"], default="train")
    parser.add_argument("--prompt-backend", choices=["vlgeo", "blip", "clip", "blip_clip", "llava", "metadata"], default="vlgeo")
    parser.add_argument("--prompt-cache", type=str, default="lgm_game_pytorch/prompt_cache/sues200_vlgeo.jsonl")
    parser.add_argument("--caption-model", type=str, default="Salesforce/blip-image-captioning-base")
    parser.add_argument("--clip-model", type=str, default="openai/clip-vit-base-patch32")
    parser.add_argument("--llava-model", type=str, default="llava")
    parser.add_argument("--llava-endpoint", type=str, default="http://localhost:11434/api/generate")
    parser.add_argument("--prompt-device", type=str, default="auto")
    parser.add_argument("--max-classes", type=int, default=16)
    parser.add_argument("--samples-per-class", type=int, default=1)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--use-class-token", action="store_true")
    parser.add_argument("--allow-prompt-fallback", action="store_true")
    parser.add_argument("--summary-json", type=str, default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    vocab = PromptVocabulary.default()
    dataset = CrossViewPairDataset(
        root=args.data_root,
        dataset_name=args.dataset,
        split=args.split,
        image_size=224,
        max_classes=args.max_classes,
        samples_per_class=args.samples_per_class,
        seed=args.seed,
        vocab=vocab,
        use_class_token=args.use_class_token,
        prompt_backend=args.prompt_backend,
        prompt_cache=args.prompt_cache,
        caption_model=args.caption_model,
        clip_model=args.clip_model,
        llava_model=args.llava_model,
        llava_endpoint=args.llava_endpoint,
        prompt_device=args.prompt_device,
        allow_prompt_fallback=args.allow_prompt_fallback,
    )
    payload = {
        "prompt_cache": args.prompt_cache,
        "prompt_backend": args.prompt_backend,
        "dataset": summarize_records(dataset.records),
        "vocab_size": len(vocab),
    }
    print(payload)
    if args.summary_json:
        save_json(Path(args.summary_json), payload)


if __name__ == "__main__":
    main()
