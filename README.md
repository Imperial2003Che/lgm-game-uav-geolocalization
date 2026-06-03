# LGM-GAME Research Draft

This repository contains an early research prototype and IEEE-style manuscript draft for:

**LGM-GAME: Text-Style and Vector-Map Guided Geometric Alignment for Robust UAV-View Geo-Localization**

The project is built around a new paper idea that extends geometric-aware sparse Transformer matching with:

- vision-language semantic anchors,
- text-derived style prompts for weather, season, illumination, and sensor style,
- vector-map topology tokens,
- text-style-map guided geometric sparse cross-view attention,
- Sinkhorn optimal transport matching with a dustbin mechanism,
- graph-consistency filtering inspired by maximal clique optimization.

## Contents

```text
.
├── 新论文创新思路.md
├── lgm_game_prototype/
│   ├── run_demo.py
│   └── lgm_game/
├── lgm_game_pytorch/
│   ├── README.md
│   ├── commands/
│   └── lgm_game_pytorch/
└── lgm_game_paper_latex/
    ├── main.tex
    ├── refs.bib
    ├── main.pdf
    ├── Makefile
    └── compile.sh
```

## Run the Prototype

```bash
cd lgm_game_prototype
python3 run_demo.py
```

The demo simulates language-map-geometry guided sparse matching and prints semantic anchors, sparse attention edges, Sinkhorn matches, and final consistent matches.

## Train the PyTorch Model

The trainable PyTorch engineering version is in:

```text
lgm_game_pytorch/
```

It implements VLM-generated content/style text prompts, content/style text encoders, a ResNet visual encoder, a style-suppressed matching head, SUES-200 / University-1652 dataset loaders, training, checkpointing, and retrieval evaluation.

Quick SUES-200 smoke test:

```bash
bash lgm_game_pytorch/commands/train_sues_smoke.sh
```

First runnable SUES-200 experiment:

```bash
PYTHONPATH=lgm_game_pytorch python3 -m lgm_game_pytorch.train \
  --dataset sues200 \
  --data-root /Users/chenche/Documents/dataset/SUES-200 \
  --output-dir lgm_game_pytorch/runs/sues200_first \
  --epochs 1 \
  --batch-size 4 \
  --image-size 128 \
  --max-classes 32 \
  --eval-max-classes 16 \
  --max-steps 10 \
  --prompt-backend cache \
  --prompt-cache lgm_game_pytorch/prompt_cache/sues200_clip_first.jsonl \
  --num-workers 0
```

## Compile the Paper Draft

TeX Live was installed locally during setup at:

```text
/Users/chenche/.local/texlive/2026
```

Compile the manuscript with:

```bash
cd lgm_game_paper_latex
make
```

The compiled PDF is:

```text
lgm_game_paper_latex/main.pdf
```

## Notes

- The original `lgm_game_prototype/` remains a lightweight logic demo.
- The trainable PyTorch code is in `lgm_game_pytorch/`; VLM prompt generation is in `lgm_game_pytorch/lgm_game_pytorch/text_prompts.py`.
- Bibliographic entries in `refs.bib` are preliminary and should be replaced with official metadata before submission.
- The local `.codex_analysis/` cache is intentionally excluded because it contains extracted text from local papers.
