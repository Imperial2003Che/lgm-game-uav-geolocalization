#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

PYTHONPATH=lgm_game_pytorch python3 -m lgm_game_pytorch.train \
  --dataset sues200 \
  --data-root /Users/chenche/Documents/dataset/SUES-200 \
  --output-dir lgm_game_pytorch/runs/sues200_clip_first \
  --epochs 1 \
  --batch-size 4 \
  --image-size 128 \
  --max-classes 32 \
  --eval-max-classes 16 \
  --max-steps 10 \
  --prompt-backend cache \
  --prompt-cache lgm_game_pytorch/prompt_cache/sues200_clip_first.jsonl \
  --num-workers 0 \
  --device cpu \
  --prompt-device cpu \
  --log-interval 2
