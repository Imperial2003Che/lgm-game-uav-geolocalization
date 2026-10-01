#!/usr/bin/env bash
set -euo pipefail

: "${SUES200_ROOT:?Set SUES200_ROOT to the SUES-200 dataset directory}"

cd "$(dirname "$0")/../.."

rm -f lgm_game_pytorch/prompt_cache/sues200_clip_first.jsonl

PYTHONPATH=lgm_game_pytorch python3 -m lgm_game_pytorch.build_prompts \
  --dataset sues200 \
  --data-root "$SUES200_ROOT" \
  --split train \
  --output-jsonl lgm_game_pytorch/prompt_cache/sues200_clip_first.jsonl \
  --prompt-backend clip \
  --max-classes 32 \
  --samples-per-class 1 \
  --prompt-device cpu

PYTHONPATH=lgm_game_pytorch python3 -m lgm_game_pytorch.build_prompts \
  --dataset sues200 \
  --data-root "$SUES200_ROOT" \
  --split test \
  --output-jsonl lgm_game_pytorch/prompt_cache/sues200_clip_first.jsonl \
  --prompt-backend clip \
  --max-classes 16 \
  --samples-per-class 1 \
  --prompt-device cpu
