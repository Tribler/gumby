#!/bin/bash

# This script can be called from outside gumby to avoid the egg-chicken situation where
# gumby's dependencies are not available, so let's find the scripts dir and add it to $PATH
SCRIPTDIR=$( dirname $(readlink -f "$0"))
if [ ! -d "$SCRIPTDIR" ]; then
    SCRIPTDIR=$( dirname $(readlink -f $(which "$0")))
fi
if [ ! -d "$SCRIPTDIR" ]; then
    echo "Couldn't find this script path, bailing out."
    exit 1
fi

export PATH=$PATH:$SCRIPTDIR

if [ ! -z "$VIRTUALENV_DIR" ]; then
    VENV=$VIRTUALENV_DIR
else
    VENV=$HOME/venv3
fi

if [ ! -e $VENV/bin/python ]; then
  python3 -m venv --system-site-packages --clear $VENV
  $VENV/bin/easy_install --upgrade pip
fi

mkdir -p $VENV/src

source $VENV/bin/activate

python -m pip install psutil py-solc-x web3
