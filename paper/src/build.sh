#!/bin/sh
# Rebuild the figures and render ../paper.pdf and ../conjecture.pdf.
# Needs Python 3 and one of: tectonic (https://tectonic-typesetting.github.io), latexmk, pdflatex.
set -e
cd "$(dirname "$0")"
python3 ../../make_figures.py
(cd ../.. && python3 trapped_ball.py --figure)
if command -v tectonic >/dev/null 2>&1; then
    tectonic --outdir .. paper.tex
    tectonic --outdir .. conjecture.tex
elif command -v latexmk >/dev/null 2>&1; then
    latexmk -pdf -interaction=nonstopmode paper.tex conjecture.tex && cp paper.pdf conjecture.pdf .. && latexmk -C
else
    pdflatex -interaction=nonstopmode paper.tex && pdflatex -interaction=nonstopmode paper.tex
    pdflatex -interaction=nonstopmode conjecture.tex && pdflatex -interaction=nonstopmode conjecture.tex
    mv paper.pdf conjecture.pdf .. && rm -f paper.aux paper.log paper.out conjecture.aux conjecture.log conjecture.out
fi
echo "wrote $(cd .. && pwd)/paper.pdf and conjecture.pdf"
