#!/usr/bin/env python
"""
Uses structure json file (from findspaces.py) to generate linearized 
html view of pdf file. 
SYNAPSIS: rewrite.py <outfile.json> <input.pdf> <htmloutdir>

Author: Johannes Buchner (C) 2013
"""

import sys, os
from PIL import Image
import json
from math import floor, ceil

#info = json.load(open(sys.argv[2]))
from PyPDF2 import PdfFileWriter, PdfFileReader
origfile = PdfFileReader(open(sys.argv[2], 'rb'))
info = dict(author=origfile.documentInfo['/Author'],
	title=origfile.documentInfo['/Title'],
	date=origfile.documentInfo['/CreationDate'])
if len(info['title']) == 0:
	info['title'] = os.path.basename(sys.argv[2]).replace('.pdf', '')

input = json.load(open(sys.argv[1]))
outdir = sys.argv[3]
pages_sub_segments = input['segments']
infiles = input['files']
shape = input['shape']

assert os.path.isdir(outdir), 'third argument must be an existing directory: "%s"' % outdir
	

out = file(outdir + '/index.html', 'w')
out.write("""
<html>
<head>
<title>%(title)s</title>
<meta name="author" content="%(author)s">
<meta name="DC.date" content="%(date)s" />
<style>
img {display:block; border: 0; margin-bottom: 1em;}
</style>
</head>
<body>
""" % info)
j = 0
colwidths = []
images = []
imsize = None
for f, segments in zip(infiles, pages_sub_segments):
	#im = Image.open(f)
	im = Image.open(f).convert('L')#.resize((612, 792))
	# write out sequence of images
	colwidths += [seg_info['segment']['right'] - seg_info['segment']['left'] 
		for seg_info in segments if seg_info['iscolumn']]
	images.append(im)
	assert imsize is None or im.size == imsize
	imsize = im.size
	hscale = imsize[0] * 1. / shape[0]
	vscale = imsize[1] * 1. / shape[1]

if len(colwidths) == 0:
	colwidth = shape[0] / 2
else:
	colwidth = max(colwidths)
for f, im, segments in zip(infiles, images, pages_sub_segments):
	for seg_info in segments:
		seg = seg_info['segment']
		is_col = seg_info['iscolumn']
		j += 1
		# some segments are really high and should be split if possible
		# segments should have the same width unless they are 
		#   short in height, in which case they should not be rescaled
		
		bbox = floor(seg['left'] * hscale - 1), floor(seg['top'] * vscale - 1), ceil(seg['right'] * hscale + 1), ceil(seg['bottom'] * vscale + 1)
		bbox = [int(x) for x in bbox]
		im_segment = im.crop(bbox)
		# scale to same width -- if very wide
		width = seg['right'] - seg['left']
		height = seg['bottom'] - seg['top']
		bbox_width = (bbox[2] - bbox[0])
		bbox_height = (bbox[3] - bbox[1])
		scale = 1.
		rotate = False
		if not is_col:
			# scale to width
			scale = max(width * 1. / colwidth, 1)
			# if it happens that something is wider (by a factor of 2)
			# but also has a height comparable to colwidth
			# rotate it
			if width > colwidth * 1.2 and height > colwidth * 0.8:
				print 'will rotate segment %d' % j
				im_segment = im_segment.rotate(90)
				scale = max(height * 1. / colwidth, 1)
				bbox_width, bbox_height = bbox_height, bbox_width
		
		width = bbox_width / scale
		height = bbox_height / scale
		im_segment.save(outdir + '/segment_%04d.png' % j, optimize=True)

		out.write("""<img src="segment_%04d.png"/ width="%d" height="%d"><!-- %f -->\n""" % (j, width, height, scale))
		#out.write("""<img src="segment_%04d.png"/ width="%d" height="%d">\n""" % (j, width, height))
	

