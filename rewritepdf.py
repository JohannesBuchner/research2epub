#!/usr/bin/env python
"""
Uses structure json file (from findspaces.py) to generate a linearized 
pdf of a pdf file.
SYNAPSIS: rewrite.py <input.pdf> <segmentsfile.json> <output.pdf>

Caveats: Some readers do not support pages of varying widths well. So avoid
segments of varying width.

Author: Johannes Buchner (C) 2013
"""

import sys, os
from PIL import Image
import json
import copy
import progressbar
from PyPDF2 import PdfFileReader, PdfFileWriter

input = json.load(open(sys.argv[1]))
origfile = sys.argv[2]
outfile = sys.argv[3]
pages_sub_segments = input['segments']
#infiles = input['files']
shape = input['shape']

j = 0
parts = []

print 'reading file ...'
pdf = PdfFileReader(open(origfile, 'rb'))
pages = [pdf.getPage(i) for i in range(0, pdf.getNumPages())]

colwidths = []
for segments in pages_sub_segments:
	colwidths += [seg_info['segment']['right'] - seg_info['segment']['left'] 
		for seg_info in segments if seg_info['iscolumn']]
if len(colwidths) == 0:
	colwidth = shape[0] / 2
else:
	colwidth = max(colwidths)

def crop(page, section):
	#print 'page dimensions', page.mediaBox, page.mediaBox.upperLeft, page.mediaBox.upperRight
	assert page.mediaBox.lowerLeft == (0, 0), page.mediaBox.lowerLeft
	q = copy.copy(page)
	qbox = copy.deepcopy(page.mediaBox)
	(w, h) = page.mediaBox.upperRight
	width, height = float(w), float(h)
	# lower left, upper right
	# 0 0, w h -> left, 1-bottom, right 1-top
	qbox.lowerLeft = (section['left'] * width / shape[0], 
		height - section['bottom'] * height / shape[1])
	qbox.upperRight = (section['right'] * width / shape[0], 
		height - section['top'] * height / shape[1])
	q.mediaBox = qbox
	return q

def join(parts, outfile):
	output = PdfFileWriter()
	for p in parts:
		output.addPage(p)
	output.write(file(outfile, 'w'))

pbar = progressbar.ProgressBar(
	widgets=[progressbar.Percentage(), progressbar.Counter('%5d'),
	progressbar.Bar(), progressbar.ETA()],
	maxval=len(pages)).start()

for i, (segments, page) in enumerate(zip(pages_sub_segments, pages)):
	for seg_info in segments:
		seg = seg_info['segment']
		is_col = seg_info['iscolumn']
		j += 1
		
		width = seg['right'] - seg['left']
		height = seg['bottom'] - seg['top']
		
		rotate = False
		scale = 1.
		if not is_col:
			# scale to width
			scale = width * 1. / colwidth
			# if it happens that something is wider (by a factor of 2)
			# but also has a height comparable to colwidth
			# rotate it
			if width > colwidth * 1.2 and height > colwidth * 0.8:
				print 'will rotate segment %d' % j
				scale = height * 1. / colwidth
				rotate = True
		
		cropped_page = crop(page=page, section=seg)
		if rotate:
			cropped_page.rotateCounterClockwise(90)
		cropped_page.scaleBy(scale)
		
		parts.append(cropped_page)
	pbar.update(pbar.currval + 1)
pbar.finish()

print 'joining...'
join(parts=parts, outfile=outfile)



