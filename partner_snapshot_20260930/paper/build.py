"""Build both IEEEtran documents with an installed TeX distribution."""
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent
for document in ("main", "supplementary"):
    commands = [
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", document + ".tex"],
        ["bibtex", document],
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", document + ".tex"],
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", document + ".tex"],
    ]
    for command in commands:
        subprocess.run(command, cwd=ROOT, check=True)
