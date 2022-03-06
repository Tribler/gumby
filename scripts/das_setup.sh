#!/bin/bash -x
# %*% This script takes care of setting everything up to run an IPv8/Tribler experiment on the DAS4.

# Check that we are actually running on one of the DAS4 head nodes
if [ ! -z $(hostname |grep ^fs[0-9]$) ]; then
    # Let SGE clean after us
    grep -q "^export SGE_KEEP_TMPFILES" ~/.bashrc || echo "export SGE_KEEP_TMPFILES=no" >> ~/.bashrc
fi

quota -q
if [ $? -ne 0 ]; then
    echo 'Quota exceeded!'
    echo "Aborting experiment."
    exit 1
fi

set -e

build_virtualenv.sh

find -iname *.py[oc] -delete

pycompile.py .
