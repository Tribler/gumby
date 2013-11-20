#!/bin/bash -xe

EXPECTED_ARGS=8
if [ $# -ne $EXPECTED_ARGS ]
then
	echo "Usage: `basename $0` repository_dir src_store filename process_guard_cmd date experiment_time bridge_ip seeder_port"
	exit 65
fi

REPOSITORY_DIR="$1"
SRC_STORE="$2"
FILENAME="$3"
PROCESS_GUARD_CMD="$4"
DATE="$5"
LOGS_DIR="/home/logs/$DATE"
EXPERIMENT_TIME="$6"
BRIDGE_IP="$7"
SEEDER_PORT="$8"
mkdir -p "$LOGS_DIR/src"

# fix path so libswift can find libevent
export LD_LIBRARY_PATH=/usr/local/lib

# start eth0 and set gateway
ifconfig eth0 up 
route add default gw $BRIDGE_IP

# seed file
#$PROCESS_GUARD_CMD -c "$REPOSITORY_DIR/swift -l $SEEDER_PORT -f $SRC_STORE/$FILENAME -p -H  " -t $EXPERIMENT_TIME -m $LOGS_DIR/src -o $LOGS_DIR/src &
$PROCESS_GUARD_CMD -c "$REPOSITORY_DIR/swift -l $SEEDER_PORT -f $SRC_STORE/$FILENAME -p -H  " -t $EXPERIMENT_TIME -o $LOGS_DIR/src &
#$REPOSITORY_DIR/swift -l 1337 -f $SRC_STORE/$FILENAME -p -H &
# $REPOSITORY_DIR/swift -l 1337 -f $SRC_STORE/$FILENAME -p -H > $SRC_STORE/
