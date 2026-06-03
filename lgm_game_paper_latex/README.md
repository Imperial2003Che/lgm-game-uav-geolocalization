# LGM-GAME LaTeX Draft

This folder contains a preliminary IEEE-style LaTeX manuscript for:

`LGM-GAME: Language- and Vector-Map-Guided Geometric Sparse Transformer for UAV-View Geo-Localization`

## Folder

```text
lgm_game_paper_latex/
  main.tex
  refs.bib
  Makefile
  figures/
    README.md
```

## Compile

TeX Live 2026 has been installed locally at:

```text
/Users/chenche/.local/texlive/2026
```

To compile, run:

```bash
cd /Users/chenche/Documents/New\ project/lgm_game_paper_latex
make
```

or run `latexmk` directly with the local TeX Live path:

```bash
cd /Users/chenche/Documents/New\ project/lgm_game_paper_latex
PATH="$HOME/.local/texlive/2026/bin/universal-darwin:$PATH" latexmk -pdf main.tex
```

The source tries to use `IEEEtran.cls` when available. If it is not installed, it falls back to a simple two-column `article` layout so the draft remains editable.

## Notes

- The current manuscript is a layout-ready research draft, not a completed paper.
- References in `refs.bib` are preliminary placeholders based on the local paper filenames and should be replaced with exact author, volume, issue, pages, DOI, and year before submission.
- Figure boxes are placeholders. Replace them with real framework diagrams from `figures/`.
