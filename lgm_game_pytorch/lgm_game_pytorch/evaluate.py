from __future__ import annotations

import argparse
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from .data import CrossViewPairDataset, summarize_records
from .model import LGMGameModel
from .text_prompts import PromptVocabulary
from .train import evaluate
from .utils import choose_device, save_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate an LGM-GAME checkpoint.")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--dataset", choices=["sues200", "university1652"], default=None)
    parser.add_argument("--data-root", type=str, default=None)
    parser.add_argument("--split", choices=["train", "test"], default="test")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--image-size", type=int, default=None)
    parser.add_argument("--max-classes", type=int, default=64)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument("--output-json", type=str, default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    checkpoint = torch.load(args.checkpoint, map_location="cpu")
    saved_args = checkpoint["args"]
    dataset_name = args.dataset or saved_args["dataset"]
    data_root = args.data_root or saved_args["data_root"]
    image_size = args.image_size or saved_args["image_size"]
    vocab = PromptVocabulary.from_tokens(checkpoint["vocab_tokens"])
    device = choose_device(args.device)

    dataset = CrossViewPairDataset(
        root=data_root,
        dataset_name=dataset_name,
        split=args.split,
        image_size=image_size,
        max_classes=args.max_classes,
        samples_per_class=1,
        seed=saved_args.get("seed", 7),
        vocab=vocab,
        use_class_token=saved_args.get("use_class_token", False),
    )
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False, num_workers=args.num_workers)
    model = LGMGameModel(
        vocab_size=len(vocab),
        backbone=saved_args["backbone"],
        embed_dim=saved_args["embed_dim"],
        token_dim=saved_args["token_dim"],
        pretrained=False,
        content_weight=saved_args["content_weight"],
        style_suppression=saved_args["style_suppression"],
    ).to(device)
    model.load_state_dict(checkpoint["model"])
    metrics = evaluate(model, loader, device)
    payload = {"dataset": summarize_records(dataset.records), "metrics": metrics}
    print(payload)
    if args.output_json:
        save_json(Path(args.output_json), payload)


if __name__ == "__main__":
    main()
