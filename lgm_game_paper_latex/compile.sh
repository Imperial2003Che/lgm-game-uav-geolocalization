#!/usr/bin/env sh
set -eu

export PATH="$HOME/.local/texlive/2026/bin/universal-darwin:$PATH"
latexmk -pdf -interaction=nonstopmode main.tex
