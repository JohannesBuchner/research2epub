#!/bin/bash

url=$1
de_url=$(echo "$url" | sed 's,://arxiv.org/,://de.arxiv.org/,')
name=$(echo "$url" | sed 's,.*/,,g').pdf

wget $de_url -w 10 --random-wait -U 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)' -nc --continue -O $name

bash convert.sh $name

cp -v ${name/.pdf/.epub} /run/media/user/KOBOeReader/
firefox ${name/.pdf/}/index.html

