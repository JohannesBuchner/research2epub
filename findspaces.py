#!/usr/bin/env python
"""
Analyses input png pages for their structure, and writes out a json file
SYNAPSIS: findspaces.py <outfile.json> <infile1.png> ...

Author: Johannes Buchner (C) 2013
"""

import sys, os
import numpy
from numpy import log, exp, log10, logical_and, logical_or
from PIL import Image
import joblib
import json


def multi_and(part0, *parts):
	for p in parts:
		part0 = logical_and(part0, p)
	return part0

debug = False

pages = []
size = None
shape = None
outfile = sys.argv[1]
infiles = sys.argv[2:]

cachedir = outfile + '.cache'
if not os.path.isdir(cachedir): os.mkdir(cachedir)
mem = joblib.Memory(cachedir=cachedir, verbose=False)

for f in infiles:
	im = Image.open(f).convert('L')#.resize((612, 792))
	print im.size
	im = im.resize((im.size[0]/2, im.size[1]/2))
	print im.size
	#a = numpy.array(list(im.getdata())).reshape(im.size)
	a = numpy.array(im).transpose()
	assert shape == None or im.size == shape
	shape = im.size
	b = a < 255
	#print b.shape, b
	size = b.size
	pages.append(b)

this_run = dict(infiles=infiles, shape=list(shape))
try:
	last_run = json.load(open(cachedir + '/last_run.json'))
	if this_run != last_run:
		print this_run
		print last_run
		print 'different run; clearing cache'
		mem.clear()
except IOError:
	print 'new run; clearing cache'
	mem.clear()
json.dump(this_run, file(cachedir + '/last_run.json', 'w'), indent=4)

cache = mem.cache
cache = lambda x: x
# compute overlap / similarities among pages
@cache
def similar(pages, selection):
	assert selection.any()
	parts = [p[selection] for p in pages]
	first = parts[0]
	odd   = parts[1::2]
	even  = parts[2::2]
	diffs = []
	diffs += [(o != odd[0]).sum() for o in odd[1:]]
	assert not numpy.isnan(diffs).any(), diffs
	diffs += [(e != even[0]).sum() for e in even[1:]]
	assert not numpy.isnan(diffs).any(), diffs
	#print 'similar:', sum(diffs), 'of', selection.size, 'across %d pages' % (len(pages))
	return numpy.mean(diffs) * 1. / size

# find common stuff along borders

# narrow in from all sides, maximize the amount, 
# while keeping the differences to a minimum

indices = numpy.indices(shape)
import matplotlib.pyplot as plt

@cache
def find_borders(pages):
	lrtb = [0, 0, 0, 0]
	v0 = 0
	plt.figure(figsize=(10, 5))
	region = indices[0] < 0 # empty region
	for dim in 0, 1, 2, 3:
		last_v = None
		last_flat_i = 0
		print 'constraint for %d: ' % dim + ('indices[%d] >= shape[%d] - i' % (dim/2, dim/2) if dim % 2 == 1 else 'indices[%d] <= i' % (dim/2))
		values = []
		for i in range(shape[0] / 2):
			assert i < shape[0] / 3
			region_add = indices[dim/2] >= shape[dim/2] - i if dim % 2 == 1 else indices[dim/2] <= i
			region_next = numpy.logical_or(region, region_add)
			v = similar(pages, region_next)
			print i, v, v - v0, region_next.sum() * 1. / region_next.size
			values.append([i, v - v0])
			if last_v is None or last_v == v:
				last_flat_i = i
			last_v = v
			if v - v0 > 0.001: # cut at 10% tops
				print 'in dim %d, stopping at %d; reverting back to %d' % (dim, i, last_flat_i)
				i = last_flat_i
				lrtb[dim] = i
				region_add = indices[dim/2] >= shape[dim/2] - i if dim % 2 == 1 else indices[dim/2] <= i
				region = numpy.logical_or(region, region_add)
				v0 = similar(pages, region)
				break
		values = numpy.array(values)
		plt.plot(values[:,0], values[:,1], 'x-', label='dim=%d' % dim)
	plt.legend(loc='best', ncol=2)
	if debug:
		plt.savefig('borders.pdf', bbox_inches='tight')
	plt.close()
	return lrtb, region

lrtb, region = find_borders(pages)
print lrtb
l, r, t, b = lrtb

def totaldiff(region):
	return numpy.mean([p[region].sum() for p in pages]) * 1. / size

# centrally, at (l + r) / 2, there is a white band of a certain size.
mid = (l + shape[0] - r) / 2

# determine how wide it is
values = []
for i in range(shape[0] / 10):
	region_band = multi_and(indices[0] >= mid - i, 
			indices[0] <= mid + i, -region)
	v = totaldiff(region_band)
	values.append([i, v])
	print 'band', i, v
	if v > 0.001:
		break
bw = i
values = numpy.array(values)
plt.figure(figsize=(10, 5))
plt.plot(values[:,0], values[:,1], 'x-')
if debug:
	plt.savefig('width.pdf', bbox_inches='tight')
plt.close()


region_band = numpy.logical_and(indices[0] >= mid - bw, indices[0] <= mid + bw)
region_band = numpy.logical_and(-region, region_band)

# then determine for each page whether it is 
#   (a) from top to bottom
#   (b) from top to somewhere
#   (c) from somewhere to bottom
# split pages into columns and wide-panel segments

def rect_region(top, left, right, bottom):
	#return slice(seg['left'], seg['right']+1), slice(seg['top'], seg['bottom'] + 1)
	return multi_and(
		indices[0] <= right, 
		indices[0] >= left, 
		indices[1] <= bottom, 
		indices[1] >= top)
def rect_around_region(top, left, right, bottom):
	a = multi_and(
		indices[0] <= right, indices[0] >= left,
		indices[1] <= bottom, indices[1] >= top)
	b = multi_and(
		indices[0] < right, indices[0] > left,
		indices[1] < bottom, indices[1] > top)
	c =  numpy.logical_and(a, -b)
	#print a.sum(), b.sum()
	#print c.sum(), (top - bottom) * 2 + (right - left) * 2 - 2
	return c

@cache
def find_segments(p):
	segments = []
	if not p[multi_and(-region, indices[0] == mid)].any():
		print '  full page!'
		#segments.append(dict(top=t, left=l, right=shape[0] - r, bottom=shape[1] - b))
		segments.append(dict(top=t, left=l, right=mid, bottom=shape[1] - b))
		segments.append(dict(top=t, left=mid, right=shape[0] - r, bottom=shape[1] - b))
	else:
		last_top = 0
		last_bottom = 0
		for i in range((shape[1] - t - b) / 6, shape[1] - t - b):
			acceptable = False
			# there should be a horizontal separating space
			# try top to somewhere
			if not p[multi_and(
				#indices[0] >= mid - bw / 2,
				#indices[0] <= mid + bw / 2,
				indices[0] == mid,
				indices[1] <= t + i, 
				-region)].any():
				print '  top to %d' % i
				acceptable = True
				if not p[multi_and(
					indices[1] >= t + i,
					indices[1] <= t + i + bw,
					-region)].any():
					print '    found separator of height %d!' % (bw)
					last_top = i
			
			# try bottom to somewhere
			if not p[multi_and(
				#indices[0] >= mid - bw / 2,
				#indices[0] <= mid + bw / 2,
				indices[0] == mid,
				indices[1] >= shape[1] - b - i, 
				-region)].any():
				print '  bottom to %d' % i
				acceptable = True
				if not p[multi_and(
					indices[1] >= shape[1] - b - i - bw,
					indices[1] <= shape[1] - b - i,
					-region)].any():
					print '    found separator of height %d!' % (bw)
					last_bottom = i
			
			if not acceptable:
				break
		
		ptop = t
		# topcol, wide, bottomcol
		segments.append(dict(top=t, left=l, right=mid, bottom=t + last_top))
		segments.append(dict(top=t, left=mid, right=shape[0] - r, bottom=t + last_top))
		segments.append(dict(top=t + last_top, left=l, right=shape[0] - r, bottom=shape[1] - b - last_bottom))
		segments.append(dict(top=shape[1] - b - last_bottom, left=l, right=mid, bottom=shape[1] - b))
		segments.append(dict(top=shape[1] - b - last_bottom, left=mid, right=shape[0] - r, bottom=shape[1] - b))
		# potentially, some segments are of height zero. 
		# we will weed those out below
	# remove zero segments
	segments = [s for s in segments if s['top'] != s['bottom'] and s['left'] != s['right']]
	return segments

segments_pages = []
for k, p in enumerate(pages):
	print 'segmenting page %d' % k
	# try full
	segments = find_segments(p)
	print '  segments:', segments
	segments_pages.append(segments)

@cache
def get_line_filled(p, seg):
	values = []
	for j in range(seg['top'], seg['bottom'] + 1):
		seg_line = dict(seg)
		seg_line['top'] = j
		seg_line['bottom'] = j
		values.append(p[rect_region(**seg_line)].any())
	return numpy.array(values)
@cache
def get_line_filled2(p, seg):
	# add up horizontally
	rect = p[slice(seg['left'], seg['right']+1), slice(seg['top'], seg['bottom'] + 1)]
	assert rect.shape == (seg['right'] - seg['left'] + 1, seg['bottom'] - seg['top'] + 1)
	add = rect.sum(axis=0)
	add.shape == seg['top'] - seg['bottom'] + 1
	values2 = add != 0
	if False:
		values = get_line_filled(p, seg)
		assert values.shape == values2.shape
		assert (values == values2).all()
		print 'get_line_filled2 worked'
	return values2

@cache
def get_empty_spaces(values):
	j = 0
	k = 0
	coords = []
	while True:
		if values[j:k+1].any():
			# end of empty space
			if k - 1 >= j:
				coords.append([j, k - 1])
			j = k + 1
			k = k + 1
		else:
			# is empty, extend to bottom
			k = k + 1
		if k == len(values):
			break
	return numpy.array(coords)

heights = []
page_coords = []
print 'finding breaking spaces in segments ...'

# count empty spaces of height i in s
for i, (p, segments) in enumerate(zip(pages, segments_pages)):
	seg_coords = []
	print ' breaking spaces for page %d (%d segments)' % (i, len(segments))
	for seg in segments:
		# determine if row is empty
		# go through each row, reset counter to 0 if not empty
		values = get_line_filled2(p, seg)
		coords = get_empty_spaces(values)
		if len(coords) > 0:
			heights += (coords[:,1] - coords[:,0]).tolist()
		seg_coords.append(coords)
	page_coords.append(seg_coords)

print 'finding characteristic height...'
plt.figure(figsize=(10, 5))
heights = numpy.array(heights)
plt.hist(heights, bins=range(20) + [20, 40, 60, 80])
plt.hist(heights, bins=range(heights.max()), cumulative=True, histtype='step')
if debug:
	plt.savefig('heights.pdf', bbox_inches='tight')
plt.close()# find flat bits in cumulative distributions

vals, bins = numpy.histogram(heights, bins=range(heights.max()))
flats = vals == 0
i = 0
# ^^^___^^^^
# ______^^^^
#       1 take that one
# ignore first few flat, wait for non-flat, take first flat then
for i, v in enumerate(vals):
	if v > 0:
		break
print 'non-flat starting', i
for j, v in enumerate(vals):
	if j <= i:
		continue
	if v == 0:
		break
print 'flat starting', j
flat_heights = bins[flats]
print 'flat heights:', flat_heights
h = bins[j]

print 'characteristic height:', h

# detect breaks by characteristic height
# split all segments
pages_sub_segments = []

for i, (p, segments, seg_coords) in enumerate(zip(pages, segments_pages, page_coords)):
	sub_segments = []
	print 'splitting segments for page %d' % i
	assert len(seg_coords) == len(segments)
	for seg, coords in zip(segments, seg_coords):
		# split into sub-segments if they are smaller than h
		splitters = [(lo, hi) for lo, hi in coords if hi - lo > h]
		# parts are between splitters
		tops = [seg['top'] + hi for lo, hi in splitters] + [seg['bottom']]
		lows = [seg['top']] + [seg['top'] + lo for lo, hi in splitters]
		tops2 = []
		lows2 = []
		for i, (low, top) in enumerate(zip(lows, tops)):
			# if height would be very large (>=1/3 shape[1]),
			#  split again with smaller-than h
			# only split the found columns, not wide figures
			while top - low > shape[1] / 3 and (seg['right'] == mid or seg['left'] == mid):
				#print 'current segment', seg, 'height:', top - low
				split = False
				for lo, hi in coords:
					split_lo = lo + seg['top']
					split_hi = hi + seg['top']
					#print '   coord:', split_lo, split_hi, lo, hi, split_lo > low + shape[1] / 8, split_lo < top, shape[1] / 8
					if split_lo > low + shape[1] / 8 and split_lo < top:
						lows2.append(low)
						tops2.append(split_lo)
						low = split_hi
						print '  split at', split_lo, split_hi
						split = True
						break
				if not split:
					print 'WARNING: no splitting possible for segment!'
					break
			
			tops2.append(top)
			lows2.append(low)
		lows, tops = lows2, tops2
		sub_sub_segments = [dict(left=seg['left'], right=seg['right'],
			top=low, bottom=top) for low, top in zip(lows, tops)]
		print 'segment', seg, 
		print '   becomes'
		print '   ', lows
		print '   ', tops
		print '   ', sub_sub_segments
		sub_segments += sub_sub_segments
	print ' :: %d segments' % len(sub_segments), [(s['left'], p[rect_region(**s)].any()) for s in sub_segments]
	pages_sub_segments.append(sub_segments)
del p

@cache
def trim_side(p, seg, side, size, direction):
	n = p[rect_region(**seg)].sum()
	# apply bi-partition
	lo = 0
	hi = size
	#print 'trimming', side, 'starting from', seg[side]
	while True: # find highest point, where n2 == n
		middle = (lo + hi) / 2
		seg2 = dict(seg)
		seg2[side] = seg[side] + middle * direction
		n2 = p[rect_region(**seg2)].sum()
		#print n, n2, middle, lo, hi, seg2[side], seg2
		if n2 == n:
			lo = middle
		else:
			hi = middle
		if hi - lo < 2:
			#print ' stopping at', lo, seg[side] + lo * direction
			return seg[side] + lo * direction

def trim(p, seg):
	print 'trimming', seg
	seg = dict(seg)
	s = trim_side(p, seg, 'top', seg['bottom'] - seg['top'], 1)
	seg['top'] = s
	s = trim_side(p, seg, 'bottom', seg['bottom'] - seg['top'], -1)
	seg['bottom'] = s
	s = trim_side(p, seg, 'left', seg['right'] - seg['left'], 1)
	seg['left'] = s
	s = trim_side(p, seg, 'right', seg['right'] - seg['left'], -1)
	seg['right'] = s
	print '    --> ', seg
	return seg

print 'trimming...'

pages_sub_segments = [[dict(iscolumn=seg['left'] == mid or seg['right'] == mid,
	segment=trim(p, seg))
		for seg in segments if p[rect_region(**seg)].any()]
	for p, segments in zip(pages, pages_sub_segments)]
print 'trimming done.'
for i, sub_segments in enumerate(pages_sub_segments):
	print 'page %d has %d segments:' % (i, len(sub_segments)), [s['segment']['left'] for s in sub_segments]


print 'writing output...'
j = 0
json.dump(dict(segments=pages_sub_segments, shape=shape, files=infiles), 
	file(outfile, 'w'), indent=4)

for i, (f, p, segments0, segments) in enumerate(zip(infiles, pages, segments_pages, pages_sub_segments)):
	im = Image.open(f) # resize((240/2, 316/2)).
	a = numpy.array(im.convert('L').resize(shape)).transpose()
	a[:] = 255
	a[p] = 0
	print 'page %d' % i
	a[region] = a[0,0]
	a[region] = 230
	#a[region_band] = 150
	
	for seg in segments0:
		segment_region = rect_around_region(**seg)
		a[segment_region] = 200
	for seg_info in segments:
		seg = seg_info['segment']
		print '  ', seg
		segment_region = rect_around_region(**seg)
		a[segment_region] = 100
		#a[segment_region] *= 0.8 + 40
	if debug:
		imout = Image.fromarray(a.transpose()) #, mode='L')
		imout.save('parts_%04d.png' % i)

# tb
#for i in range(size[1] / 2):
#	assert i < size[1] / 3
	
	
	


