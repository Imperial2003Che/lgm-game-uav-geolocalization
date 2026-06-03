from __future__ import annotations

import argparse
from pathlib import Path
from time import time

import torch
from torch.utils.data import DataLoader

from .data import CrossViewPairDataset, summarize_records
from .losses import symmetric_contrastive_loss, text_decorrelation_loss
from .metrics import AverageMeter, recall_at_k
from .model import LGMGameModel
from .text_prompts import PromptVocabulary
from .utils import choose_device, save_json, seed_everything


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train LGM-GAME PyTorch prototype.")
    parser.add_argument("--dataset", choices=["sues200", "university1652"], default="sues200")
    parser.add_argument("--data-root", type=str, default="/Users/chenche/Documents/dataset/SUES-200")
    parser.add_argument("--output-dir", type=str, default="lgm_game_pytorch/runs/sues200_first")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--max-classes", type=int, default=64)
    parser.add_argument("--eval-max-classes", type=int, default=32)
    parser.add_argument("--samples-per-class", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=0, help="0 means no limit.")
    parser.add_argument("--backbone", type=str, default="resnet18")
    parser.add_argument("--embed-dim", type=int, default=256)
    parser.add_argument("--token-dim", type=int, default=128)
    parser.add_argument("--pretrained", action="store_true", help="Use torchvision pretrained weights if available online/cache.")
    parser.add_argument("--content-weight", type=float, default=0.25)
    parser.add_argument("--style-suppression", type=float, default=0.20)
    parser.add_argument("--decor-weight", type=float, default=0.05)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument("--log-interval", type=int, default=10)
    parser.add_argument("--use-class-token", action="store_true", help="Add place_<id> pseudo content tokens for ablation only.")
    parser.add_argument("--no-eval", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    seed_everything(args.seed)
    device = choose_device(args.device)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    vocab = PromptVocabulary.default()
    train_set = CrossViewPairDataset(
        root=args.data_root,
        dataset_name=args.dataset,
        split="train",
        image_size=args.image_size,
        max_classes=args.max_classes,
        samples_per_class=args.samples_per_class,
        seed=args.seed,
        vocab=vocab,
        use_class_token=args.use_class_token,
    )
    train_loader = DataLoader(
        train_set,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=device.type == "cuda",
    )

    eval_set = None
    eval_loader = None
    if not args.no_eval:
        eval_set = CrossViewPairDataset(
            root=args.data_root,
            dataset_name=args.dataset,
            split="test",
            image_size=args.image_size,
            max_classes=args.eval_max_classes,
            samples_per_class=1,
            seed=args.seed,
            vocab=vocab,
            use_class_token=args.use_class_token,
        )
        eval_loader = DataLoader(
            eval_set,
            batch_size=args.batch_size,
            shuffle=False,
            num_workers=args.num_workers,
            pin_memory=device.type == "cuda",
        )

    model = LGMGameModel(
        vocab_size=len(vocab),
        backbone=args.backbone,
        embed_dim=args.embed_dim,
        token_dim=args.token_dim,
        pretrained=args.pretrained,
        content_weight=args.content_weight,
        style_suppression=args.style_suppression,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)

    run_info = {
        "args": vars(args),
        "device": str(device),
        "vocab_size": len(vocab),
        "train": summarize_records(train_set.records),
        "eval": summarize_records(eval_set.records) if eval_set is not None else None,
    }
    save_json(output_dir / "run_config.json", run_info)
    print(f"[config] device={device} train_pairs={len(train_set)} eval_pairs={len(eval_set) if eval_set else 0}")
    print(f"[config] first_query={run_info['train']['first_query']}")

    history: list[dict] = []
    start = time()
    for epoch in range(1, args.epochs + 1):
        train_metrics = train_one_epoch(model, train_loader, optimizer, device, args, epoch)
        eval_metrics = evaluate(model, eval_loader, device) if eval_loader is not None else {}
        epoch_metrics = {"epoch": epoch, **train_metrics, **{f"eval_{k}": v for k, v in eval_metrics.items()}}
        history.append(epoch_metrics)
        save_checkpoint(output_dir / "checkpoint_last.pt", model, optimizer, args, vocab, epoch_metrics)
        save_json(output_dir / "metrics.json", {"history": history, "seconds": time() - start})
        print(_format_metrics("[epoch]", epoch_metrics))

    print(f"[done] saved checkpoint: {output_dir / 'checkpoint_last.pt'}")
    print(f"[done] saved metrics: {output_dir / 'metrics.json'}")


def train_one_epoch(model: LGMGameModel, loader: DataLoader, optimizer: torch.optim.Optimizer, device: torch.device, args: argparse.Namespace, epoch: int) -> dict:
    model.train()
    loss_meter = AverageMeter()
    contrast_meter = AverageMeter()
    decor_meter = AverageMeter()

    for step, batch in enumerate(loader, start=1):
        batch = move_to_device(batch, device)
        outputs = model(
            batch["query_image"],
            batch["ref_image"],
            batch["content_ids"],
            batch["content_mask"],
            batch["style_ids"],
            batch["style_mask"],
        )
        contrast_loss = symmetric_contrastive_loss(outputs["logits"])
        decor_loss = text_decorrelation_loss(outputs["content_text"], outputs["style_text"])
        loss = contrast_loss + args.decor_weight * decor_loss

        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()

        n = batch["query_image"].size(0)
        loss_meter.update(loss.item(), n)
        contrast_meter.update(contrast_loss.item(), n)
        decor_meter.update(decor_loss.item(), n)

        if step % args.log_interval == 0 or step == 1:
            with torch.no_grad():
                batch_recall = recall_at_k(outputs["logits"].detach(), batch["label"], batch["label"], ks=(1, min(5, n)))
            print(
                f"[train] epoch={epoch} step={step}/{len(loader)} "
                f"loss={loss_meter.avg:.4f} contrast={contrast_meter.avg:.4f} decor={decor_meter.avg:.4f} "
                f"r@1={batch_recall.get('r@1', 0):.3f}"
            )

        if args.max_steps and step >= args.max_steps:
            break

    return {
        "train_loss": loss_meter.avg,
        "train_contrast": contrast_meter.avg,
        "train_decor": decor_meter.avg,
    }


@torch.no_grad()
def evaluate(model: LGMGameModel, loader: DataLoader | None, device: torch.device) -> dict:
    if loader is None:
        return {}
    model.eval()
    query_embeds: list[torch.Tensor] = []
    ref_embeds: list[torch.Tensor] = []
    query_labels: list[torch.Tensor] = []
    ref_labels: list[torch.Tensor] = []

    for batch in loader:
        batch = move_to_device(batch, device)
        outputs = model(
            batch["query_image"],
            batch["ref_image"],
            batch["content_ids"],
            batch["content_mask"],
            batch["style_ids"],
            batch["style_mask"],
        )
        query_embeds.append(outputs["query_embed"].cpu())
        ref_embeds.append(outputs["ref_embed"].cpu())
        query_labels.append(batch["label"].cpu())
        ref_labels.append(batch["label"].cpu())

    query = torch.cat(query_embeds, dim=0)
    ref = torch.cat(ref_embeds, dim=0)
    q_labels = torch.cat(query_labels, dim=0)
    r_labels = torch.cat(ref_labels, dim=0)
    logits = query @ ref.t()
    metrics = recall_at_k(logits, q_labels, r_labels, ks=(1, 5, 10))
    metrics["pairs"] = float(query.size(0))
    return metrics


def move_to_device(batch: dict, device: torch.device) -> dict:
    moved = {}
    for key, value in batch.items():
        moved[key] = value.to(device, non_blocking=True) if torch.is_tensor(value) else value
    return moved


def save_checkpoint(path: Path, model: LGMGameModel, optimizer: torch.optim.Optimizer, args: argparse.Namespace, vocab: PromptVocabulary, metrics: dict) -> None:
    torch.save(
        {
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "args": vars(args),
            "vocab_tokens": vocab.tokens,
            "metrics": metrics,
        },
        path,
    )


def _format_metrics(prefix: str, metrics: dict) -> str:
    formatted = " ".join(f"{key}={value:.4f}" if isinstance(value, float) else f"{key}={value}" for key, value in metrics.items())
    return f"{prefix} {formatted}"


if __name__ == "__main__":
    main()
