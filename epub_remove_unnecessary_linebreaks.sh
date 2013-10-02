#!/bin/bash
# 
# Rewrites an epub to not have unnecessary line breaks/paragraphs 
# introduced by e.g. pdf2epub conversion tools.
# SYNAPSIS: ./epub_remove_unnecessary_linebreaks <my.epub>
# 
# Makes a backup copy of the input file at <my.epub>.orig.
# 
# Author: Johannes Buchner (C) 2013

infile=$(realpath "$1")
cp --no-clobber "${infile}" "${infile}.orig"

mkdir -p temp
pushd temp || exit 1

unzip "$infile" || exit 1

for i in $(find -iname '*.htm' -or -iname '*.html'); do
	echo "rewriting $i..."
	sed -i "$i" \
		-e 's,<p class="MsoPlainText"><span>     </span>\(.*\),<p>\1,g' \
		-e 's_<p class="calibre1">\([^<>]\{65,\}\)</p>_\1_g' \
		-e 's_<p class="calibre1">\(.*\)</p>_\1<p>_g' \
		-e 's,<p class="MsoPlainText">\(.*\)</p>,\1,g' \
		-e 's,-$,,g' \
		-e 's,</p>,,g' \
		-e 's,\([^>]\) </span>,\1</span>,g' || exit 1
done

zip -r "${infile}" . || exit 1

popd

rm -r temp || exit 1

