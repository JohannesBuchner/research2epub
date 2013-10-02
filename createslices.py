#!/usr/bin/env python
"""
Writes similar output as findspaces. Crops a pdf file by the margins
defined in marginsfile, splits the page horizontally and vertically once.

SYNAPSIS: createslices.py <input.pdf> <marginsfile.json> <segmentsoutfile.json>

Example margins json file: 
{
	"left": 0.07,
	"right": 0.1,
	"top": 0.07,
	"bottom": 0.09,
	"oddshift": 0.023,
	"split": 0.49,
	"splitwidth": 0.01
}

Author: Johannes Buchner (C) 2013
"""

import sys, os
import json
from PyPDF2 import PdfFileReader

pages = []
size = None
shape = None
infile = sys.argv[1]
margins = json.load(open(sys.argv[2]))
outfile = sys.argv[3]

shape = (10000, 10000)
print 'reading', infile
pdf = PdfFileReader(open(infile, 'rb'))
npages = pdf.getNumPages()
pages = [None] * npages
infiles = [infile] * npages

pages_segments = []
for i, p in enumerate(pages):
	shift = (i % 2) * margins['oddshift'] * shape[0]
	top = margins['top'] * shape[1]
	bottom = (1. - margins['bottom']) * shape[1]
	middle = (top + bottom) / 2.
	left = dict(
		left=margins['left'] * shape[0] + shift,
		right=(margins['split'] - margins['splitwidth']) * shape[0] + shift,
		top=top,
		bottom=middle,
		)
	left2 = dict(left)
	left2['top'] = middle
	left2['bottom'] = bottom
	right = dict(
		left=(margins['split'] + margins['splitwidth']) * shape[0] + shift,
		right=(1. - margins['right']) * shape[0] + shift,
		top=top,
		bottom=middle,
		)
	right2 = dict(right)
	right2['top'] = middle
	right2['bottom'] = bottom
	segments = [left, left2, right, right2]
	pages_segments.append([dict(segment=seg, iscolumn=True) for seg in segments])

print 'writing output...'
j = 0
json.dump(dict(segments=pages_segments, shape=shape, files=infiles), 
	file(outfile, 'w'), indent=4)

