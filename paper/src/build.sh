#!/bin/sh
# Rebuild the figures and render ../paper.pdf.
# Needs Python 3 and one of: tectonic (https://tectonic-typesetting.github.io), latexmk, pdflatex.
set -e
cd "$(dirname "$0")"
python3 ../../make_figures.py
if command -v tectonic >/dev/null 2>&1; then
    tectonic --outdir .. paper.tex
elif command -v latexmk >/dev/null 2>&1; then
    latexmk -pdf -interaction=nonstopmode paper.tex && cp paper.pdf .. && latexmk -C
else
    pdflatex -interaction=nonstopmode paper.tex && pdflatex -interaction=nonstopmode paper.tex
    mv paper.pdf .. && rm -f paper.aux paper.log paper.out
fi
echo "wrote $(cd .. && pwd)/paper.pdf"
