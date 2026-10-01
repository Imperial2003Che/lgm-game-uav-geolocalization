#!/usr/bin/env bash
set -euo pipefail

: "${UNIVERSITY1652_ROOT:?Set UNIVERSITY1652_ROOT to the University-1652 dataset directory}"

cd "$(dirname "$0")/../.."

PYTHONPATH=lgm_game_pytorch python3 -m lgm_game_pytorch.train \
  --dataset university1652 \
  --data-root "$UNIVERSITY1652_ROOT" \
  --output-dir lgm_game_pytorch/runs/university1652_smoke \
  --epochs 1 \
  --batch-size 2 \
  --image-size 128 \
  --max-classes 8 \
  --eval-max-classes 8 \
  --max-steps 2 \
  --prompt-backend metadata \
  --num-workers 0 \
  --device cpu
