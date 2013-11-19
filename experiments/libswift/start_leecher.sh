#!/bin/bash -xe

EXPECTED_ARGS=7
if [ $# -ne $EXPECTED_ARGS ]
then
	echo "Usage: `basename $0` repository_dir dst_store hash netem_delay  process_guard_cmd date experiment_time"
	exit 65
fi

REPOSITORY_DIR="$1"
DST_STORE="$2"
HASH="$3"
NETEM_DELAY="$4"
PROCESS_GUARD_CMD="$5"
DATE="$6"
LOGS_DIR="/home/logs/$DATE"
EXPERIMENT_TIME="$7"
mkdir -p "$LOGS_DIR/dst"

# fix path so libswift can find libevent
export LD_LIBRARY_PATH=/usr/local/lib

# start eth0 and set gateway
ifconfig eth0 up 
route add default gw 192.168.1.20

tc qdisc add dev eth0 root netem delay $NETEM_DELAY

# leech file
$PROCESS_GUARD_CMD -c "taskset -c 1 $REPOSITORY_DIR/swift -t 192.168.1.110:1337 -o $DST_STORE/ -h $HASH -p " -t $(($EXPERIMENT_TIME-5)) -m $LOGS_DIR/dst -o $LOGS_DIR/dst &
#$REPOSITORY_DIR/swift -t 192.168.1.110:1337 -o $DST_STORE/ -h $HASH -p 


# remove leeched file
rm -rf $DST_STORE/*

