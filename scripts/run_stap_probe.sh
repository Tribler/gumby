#!/bin/bash

EXPECTED_ARGS=2
if [ $# -ne $EXPECTED_ARGS ]
then
	echo "Usage: `basename $0` \"testcase command\" outputfile"
	exit 65
fi

TESTCASE=$1
OUTPUT=$2

stap stp/log_io_writes.stp -DMAXMAPENTRIES=10000 -DSTP_NO_OVERLOAD -DMAXSTRINGLEN=4096 -DTRYLOCKDELAY=300 -DMAXSKIPPED=10000 -DMAXACTION=1000 -c "env 'LD_LIBRARY_PATH=$LD_LIBRARY_PATH' $TESTCASE" -o $2
