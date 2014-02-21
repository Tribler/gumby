#!/bin/bash -x

EXPECTED_ARGS=2
if [ $# -ne $EXPECTED_ARGS ]
then
	echo "Usage: `basename $0` \"testcase command\" outputfile"
	exit 65
fi

TEST_COMMAND=$1
OUTPUT=$2
# TODO: Read the env variables to find out where stap is
STAPPATH=$VIRTUALENV_DIR/inst/bin

# Find the stp dir
SCRIPTDIR=$( dirname $(readlink -f "$0"))
if [ ! -d "$SCRIPTDIR" ]; then
    SCRIPTDIR=$( dirname $(readlink -f $(which "$0")))
fi
if [ ! -d "$SCRIPTDIR" ]; then
    echo "Couldn't find this script path, bailing out."
    exit 1
fi

ldd /home/jenkins/venv/inst/bin/python

$STAPPATH/stap "$SCRIPTDIR"/stp/log_io_writes.stp -I $VIRTUALENV_DIR/tapsets/ -DMAXMAPENTRIES=50000 -DSTP_NO_OVERLOAD -DMAXSTRINGLEN=4096 -DTRYLOCKDELAY=300 -DMAXSKIPPED=10000 -DMAXACTION=1000 -o $2 -c "env 'LD_LIBRARY_PATH=$LD_LIBRARY_PATH' $TEST_COMMAND"
