#!/bin/bash -xe

EXPECTED_ARGS=11
if [ $# -ne $EXPECTED_ARGS ]
then
	echo "Usage: `basename $0` repository_dir dst_store hash netem_delay  process_guard_cmd date experiment_time bridge_ip seeder_ip seeder_port logs_dir"
	exit 65
fi

REPOSITORY_DIR="$1"
DST_STORE="$2"
HASH="$3"
NETEM_DELAY="$4"
PROCESS_GUARD_CMD="$5"
DATE="$6"
EXPERIMENT_TIME="$7"
BRIDGE_IP="$8"
SEEDER_IP="$9"
SEEDER_PORT="${10}"
LOGS_DIR="${11}"
mkdir -p "$LOGS_DIR/dst"

# fix path so libswift can find libevent
# export LD_LIBRARY_PATH=/usr/local/lib

tc qdisc add dev eth0 root netem delay $NETEM_DELAY

# leech file
#$PROCESS_GUARD_CMD -c "$REPOSITORY_DIR/swift -t $SEEDER_IP:$SEEDER_PORT -o $DST_STORE/ -h $HASH -p " -t $EXPERIMENT_TIME -m $LOGS_DIR/dst -o $LOGS_DIR/dst &
$PROCESS_GUARD_CMD -c "$REPOSITORY_DIR/swift -t $SEEDER_IP:$SEEDER_PORT -o $DST_STORE/ -h $HASH -p " -t $EXPERIMENT_TIME -o $LOGS_DIR/dst &

# remove leeched file
rm -rf $DST_STORE/*

