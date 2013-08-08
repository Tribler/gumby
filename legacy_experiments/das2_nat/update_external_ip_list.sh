#!/bin/bash

set -e

mkdir -p temp
parallel-ssh  -o temp/ -p 40 -h hostlist.txt 'lynx --dump http://ipecho.net/plain'
sort -u temp/*  | awk '{ print $1  }'> node_ip_list.txt
rm -fR temp
