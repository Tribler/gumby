#!/bin/bash -xe

EXPECTED_ARGS=6
if [ $# -ne $EXPECTED_ARGS ]
then
	echo "Usage: `basename $0` repository_dir src_store filename process_guard_cmd date experiment_time"
	exit 65
fi

REPOSITORY_DIR="$1"
SRC_STORE="$2"
FILENAME="$3"
PROCESS_GUARD_CMD="$4"
DATE="$5"
LOGS_DIR="/home/logs/$DATE"
EXPERIMENT_TIME="$6"
mkdir -p "$LOGS_DIR/src"

# fix path so libswift can find libevent
export LD_LIBRARY_PATH=/usr/local/lib

# start eth0 and set gateway
ifconfig eth0 up 
route add default gw 192.168.1.20

# create file to seed
# TODO: hardcoded now

# seed file
$PROCESS_GUARD_CMD -c "taskset -c 1 $REPOSITORY_DIR/swift -l 1337 -f $SRC_STORE/$FILENAME -p -H  " -t $(($EXPERIMENT_TIME-5)) -m $LOGS_DIR/src -o $LOGS_DIR/src &
#$REPOSITORY_DIR/swift -l 1337 -f $SRC_STORE/$FILENAME -p -H &
# $REPOSITORY_DIR/swift -l 1337 -f $SRC_STORE/$FILENAME -p -H > $SRC_STORE/
