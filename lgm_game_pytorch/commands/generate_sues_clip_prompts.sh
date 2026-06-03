#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

rm -f lgm_game_pytorch/prompt_cache/sues200_clip_first.jsonl

PYTHONPATH=lgm_game_pytorch python3 -m lgm_game_pytorch.build_prompts \
  --dataset sues200 \
  --data-root /Users/chenche/Documents/dataset/SUES-200 \
  --split train \
  --output-jsonl lgm_game_pytorch/prompt_cache/sues200_clip_first.jsonl \
  --prompt-backend clip \
  --max-classes 32 \
  --samples-per-class 1 \
  --prompt-device cpu

PYTHONPATH=lgm_game_pytorch python3 -m lgm_game_pytorch.build_prompts \
  --dataset sues200 \
  --data-root /Users/chenche/Documents/dataset/SUES-200 \
  --split test \
  --output-jsonl lgm_game_pytorch/prompt_cache/sues200_clip_first.jsonl \
  --prompt-backend clip \
  --max-classes 16 \
  --samples-per-class 1 \
  --prompt-device cpu
