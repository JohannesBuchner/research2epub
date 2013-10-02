#!/bin/bash
# 
# Takes pdf file and creates similarly named epub file
# SYNAPSIS: ./convert.sh my.pdf
# 
# Author: Johannes Buchner (C) 2013

infile=$1

outfile=${infile/.pdf/.epub}
outpdf=${infile/.pdf/.epub}
outhtml=${infile/.pdf/}
mkdir -p "${outhtml}"

rm -f "${outhtml}/"out-*
rm -f "${outhtml}/"segment*

pdftocairo -png -r 200 "$infile" "${outhtml}/out"

python findspaces.py "${outhtml}"/segments.json "${outhtml}/"out-*.png || exit 1

python rewrite.py "${outhtml}"/segments.json "$infile" "${outhtml}" || exit 1

python rewritepdf.py "${outhtml}"/segments.json "$infile" "${outpdf}"

#cp -r segments.html segment_*.png "${outhtml}"

ebook-convert "${outhtml}"/index.html "$outfile" || exit 1

ebook-viewer "$outfile" &

