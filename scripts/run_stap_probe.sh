#!/bin/bash -x

EXPECTED_ARGS=2
if [ $# -ne $EXPECTED_ARGS ]
then
	echo "Usage: `basename $0` \"testcase command\" outputfile"
	exit 65
fi

TESTCASE=$1
OUTPUT=$2
STAPPATH=/home/jenkins/venv/inst/bin

# Find the stp dir
SCRIPTDIR=$( dirname $(readlink -f "$0"))
if [ ! -d "$SCRIPTDIR" ]; then
    SCRIPTDIR=$( dirname $(readlink -f $(which "$0")))
fi
if [ ! -d "$SCRIPTDIR" ]; then
    echo "Couldn't find this script path, bailing out."
    exit 1
fi

$STAPPATH/stap "$SCRIPTDIR"/stp/log_io_writes.stp -I $SCRIPTDIR/stp/tapsets/ -DMAXMAPENTRIES=10000 -DSTP_NO_OVERLOAD -DMAXSTRINGLEN=4096 -DTRYLOCKDELAY=300 -DMAXSKIPPED=10000 -DMAXACTION=1000 -c "env 'LD_LIBRARY_PATH=$LD_LIBRARY_PATH' $TESTCASE" -o $2
