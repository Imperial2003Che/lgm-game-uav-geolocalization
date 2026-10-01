"""GPU capacity probe for choosing a non-OOM formal training batch.

This is explicitly a configuration probe, not an experiment result.  It uses
synthetic tensors only to measure peak memory and optimizer-step throughput for
the exact model/loss code before any test data are evaluated.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time

import torch

from lgm_game_pytorch.formal_retrieval import (
    CONTENT_DIM,
    STYLE_DIM,
    FormalRetrievalModel,
    make_grad_scaler,
    symmetric_multi_positive_loss,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backbone", choices=("resnet18", "resnet50"), required=True)
    parser.add_argument(
        "--variant",
        choices=(
            "visual",
            "content",
            "style",
            "visual_content",
            "visual_style",
            "full",
        ),
        default="full",
    )
    parser.add_argument("--identities", type=int, required=True)
    parser.add_argument("--instances", type=int, required=True)
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--embed-dim", type=int, default=512)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--iterations", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.identities < 2 or args.instances < 2:
        raise ValueError("At least two identities and two instances are required.")
    if not torch.cuda.is_available():
        raise RuntimeError("This capacity probe requires CUDA.")

    device = torch.device("cuda")
    pairs = args.identities * args.instances
    model = FormalRetrievalModel(
        variant=args.variant,
        backbone=args.backbone,
        embed_dim=args.embed_dim,
        dropout=0.2,
        pretrained=False,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)
    scaler = make_grad_scaler(True)

    labels = torch.arange(args.identities, device=device).repeat_interleave(
        args.instances
    )
    generator = torch.Generator(device="cuda")
    generator.manual_seed(20260727)
    query_images = torch.randn(
        pairs,
        3,
        args.image_size,
        args.image_size,
        device=device,
        generator=generator,
    )
    gallery_images = torch.randn(
        pairs,
        3,
        args.image_size,
        args.image_size,
        device=device,
        generator=generator,
    )
    query_content = torch.softmax(
        torch.randn(pairs, CONTENT_DIM, device=device, generator=generator), dim=1
    )
    gallery_content = torch.softmax(
        torch.randn(pairs, CONTENT_DIM, device=device, generator=generator), dim=1
    )
    query_style = torch.softmax(
        torch.randn(pairs, STYLE_DIM, device=device, generator=generator), dim=1
    )
    gallery_style = torch.softmax(
        torch.randn(pairs, STYLE_DIM, device=device, generator=generator), dim=1
    )

    elapsed: list[float] = []
    torch.cuda.reset_peak_memory_stats(device)
    for iteration in range(args.warmup + args.iterations):
        torch.cuda.synchronize(device)
        started = time.perf_counter()
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(device_type="cuda", dtype=torch.float16):
            query_embeddings = model.encode_image(
                query_images, query_content, query_style
            )
            gallery_embeddings = model.encode_image(
                gallery_images, gallery_content, gallery_style
            )
            loss = symmetric_multi_positive_loss(
                model, query_embeddings, gallery_embeddings, labels
            )
        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        scaler.step(optimizer)
        scaler.update()
        torch.cuda.synchronize(device)
        duration = time.perf_counter() - started
        if iteration >= args.warmup:
            elapsed.append(duration)

    median = statistics.median(elapsed)
    print(
        json.dumps(
            {
                "purpose": "configuration_probe_not_experiment_evidence",
                "device": torch.cuda.get_device_name(device),
                "backbone": args.backbone,
                "variant": args.variant,
                "identities_per_batch": args.identities,
                "instances_per_identity": args.instances,
                "pairs_per_step": pairs,
                "images_per_step": pairs * 2,
                "image_size": args.image_size,
                "embed_dim": args.embed_dim,
                "iterations": args.iterations,
                "median_step_seconds": median,
                "median_images_per_second": pairs * 2 / median,
                "peak_allocated_bytes": torch.cuda.max_memory_allocated(device),
                "peak_reserved_bytes": torch.cuda.max_memory_reserved(device),
                "last_loss": float(loss.detach().cpu()),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
