#!/usr/bin/env bash
set -euo pipefail

: "${SUES200_ROOT:?Set SUES200_ROOT to the SUES-200 dataset directory}"

cd "$(dirname "$0")/../.."

PYTHONPATH=lgm_game_pytorch python3 -m lgm_game_pytorch.train \
  --dataset sues200 \
  --data-root "$SUES200_ROOT" \
  --output-dir lgm_game_pytorch/runs/sues200_vlgeo_smoke \
  --epochs 1 \
  --batch-size 2 \
  --image-size 128 \
  --max-classes 8 \
  --eval-max-classes 8 \
  --max-steps 2 \
  --prompt-backend vlgeo \
  --prompt-cache lgm_game_pytorch/prompt_cache/sues200_vlgeo_train.jsonl \
  --num-workers 0 \
  --device cpu \
  --prompt-device cpu
