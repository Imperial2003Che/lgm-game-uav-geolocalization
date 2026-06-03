MAIN = main
TEXBIN ?= $(HOME)/.local/texlive/2026/bin/universal-darwin

.PHONY: all clean

all:
	PATH="$(TEXBIN):$$PATH" latexmk -pdf $(MAIN).tex

clean:
	PATH="$(TEXBIN):$$PATH" latexmk -C $(MAIN).tex
	rm -f $(MAIN).bbl $(MAIN).blg $(MAIN).synctex.gz
