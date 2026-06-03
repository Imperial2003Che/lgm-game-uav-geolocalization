# LGM-GAME Research Draft

This repository contains an early research prototype and IEEE-style manuscript draft for:

**LGM-GAME: Language- and Vector-Map-Guided Geometric Sparse Transformer for UAV-View Geo-Localization**

The project is built around a new paper idea that extends geometric-aware sparse Transformer matching with:

- vision-language semantic anchors,
- vector-map topology tokens,
- geometric sparse cross-view attention,
- Sinkhorn optimal transport matching with a dustbin mechanism,
- graph-consistency filtering inspired by maximal clique optimization.

## Contents

```text
.
├── 新论文创新思路.md
├── lgm_game_prototype/
│   ├── run_demo.py
│   └── lgm_game/
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

- This is a research planning draft, not a complete trainable model.
- Bibliographic entries in `refs.bib` are preliminary and should be replaced with official metadata before submission.
- The local `.codex_analysis/` cache is intentionally excluded because it contains extracted text from local papers.

