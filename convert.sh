#!/bin/bash
# 
# Takes pdf file and creates similarly named epub file
# SYNAPSIS: ./convert.sh my.pdf
# 
# Author: Johannes Buchner (C) 2013

infile=$1

outfile=${infile/.pdf/.epub}
outhtml=${infile/.pdf/}
mkdir -p "${outhtml}"

rm -f "${outhtml}/"out_*
rm -f "${outhtml}/"segment*

convert -units PixelsPerInch -density 200 "$infile" "${outhtml}/out_%04d.png"

j=0
for i in "${outhtml}/"out_*.png; do 
	echo $i
	convert $i -background white -flatten -alpha off $i &
	((j++))
	if [ $j == 3 ]; then
		wait
		j=0
	fi
done
wait

python findspaces.py "${outhtml}"/segments.json "${outhtml}/"out_*.png || exit 1

python rewrite.py "${outhtml}"/segments.json "$infile" "${outhtml}" || exit 1

#cp -r segments.html segment_*.png "${outhtml}"

ebook-convert "${outhtml}"/index.html "$outfile" || exit 1

ebook-viewer "$outfile" &

