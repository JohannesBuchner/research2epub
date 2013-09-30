#!/usr/bin/env python3
"""
Updates the pdf files linked in JabRef to have the same title and author as
the corresponding bibtex entry, if they do not have any title/author set.

SYNAPSIS: bibtex2pdftitles.py <library.bib> <pdfdir>

Author: Johannes Buchner (C) 2013
"""

import sys, os
import subprocess
import io
from bibtexparser.bparser import BibTexParser

pdfdir = sys.argv[2]

filehandler = io.open(sys.argv[1], 'r', encoding='latin-1')
content = filehandler
parser = BibTexParser(content)
bib = parser.get_entry_list()

def unbibtexify(s):
	return s.replace('{', '').replace('}', '').replace('~', ' ').replace("\n", ' ')

def updatepdf(filename, key, value):
	outfilename = filename + '~'
	args = ('pdftk', filename, 'update_info', '-', 'output', outfilename)
	p = subprocess.Popen(args, stdin=subprocess.PIPE)
	out, err = p.communicate(input=bytes("""InfoKey: %s
InfoValue: %s
""" % (key, value), 'UTF-8'))
	p.stdin.close()
	if p.wait() != 0:
		raise Exception('return value of pdftk non-zero: %s/%s' % (out, err))
	# Overriding original file
	os.rename(outfilename, filename)
	print('UPDATED %s!' % outfilename)

def getpdfinfo(filename):
	args = ('pdftk', filename, 'dump_data')
	p = subprocess.Popen(args, stdout=subprocess.PIPE)
	lines = [l for l in p.stdout.readlines()]
	if p.wait() != 0:
		raise Exception('return value of pdftk non-zero')
	keys = [l.replace(b'InfoKey: ', b'').strip() for l in lines if l.startswith(b'InfoKey: ')]
	vals = [l.replace(b'InfoValue: ', b'').strip() for l in lines if l.startswith(b'InfoValue: ')]
	info = dict(zip(keys, vals))
	return info

def update_info(filename, entry):
	print(filename, ' should have TITLE:', unbibtexify(entry['title']), 'BY:', unbibtexify(entry['author']))
	if os.path.exists(pdfdir + filename):
		#origfile = PdfFileReader(open(pdfdir + filename, 'rb'))
		#info = dict(author=origfile.documentInfo.get('/Author', ''),
		#	title=origfile.documentInfo.get('/Title', ''))
		info = getpdfinfo(pdfdir + filename)
		if len(info.get('Author', b'')) == 0:
			updatepdf(pdfdir + filename, key='Author', value=entry['author'])
		if len(info.get('Title', b'')) == 0:
			updatepdf(pdfdir + filename, key='Title', value=entry['title'])
		info = getpdfinfo(pdfdir + filename)
		print('new pdf info:', info)

for entry in bib:
	if 'file' not in entry: continue
	#print(entry['id'], entry['file'])
	files = entry['file'].split(';')
	for f in files:
		name, filename, filetype = f.split(':')
		if filetype.upper() != 'PDF':
			continue
		update_info(filename, entry)
	print()

