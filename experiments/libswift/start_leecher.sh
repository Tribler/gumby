#!/bin/bash -xe
# Note: runs inside a container

EXPECTED_ARGS=12
if [ $# -ne $EXPECTED_ARGS ]
then
	echo "Usage: `basename $0` repository_dir dst_store hash netem_delay netem_packet_loss process_guard_cmd experiment_time bridge_ip seeder_ip seeder_port logs_dir leecher_id"
	exit 65
fi

# TODO use getopts
REPOSITORY_DIR="$1"
DST_STORE="$2"
HASH="$3"
NETEM_DELAY="$4"
NETEM_PACKET_LOSS="$5"
PROCESS_GUARD_CMD="$6"
EXPERIMENT_TIME="$7"
BRIDGE_IP="$8"
SEEDER_IP="${9}"
SEEDER_PORT="${10}"
LOGS_DIR="${11}"
LEECHER_ID="${12}"

mkdir -p "$LOGS_DIR/dst/$LEECHER_ID"

# fix path so libswift can find libevent
# export LD_LIBRARY_PATH=/usr/local/lib

tc qdisc add dev eth0 root netem delay $NETEM_DELAY loss $NETEM_PACKET_LOSS
tc qdisc show
ifconfig

# leech file
$PROCESS_GUARD_CMD -c "$REPOSITORY_DIR/swift -t $SEEDER_IP:$SEEDER_PORT -o $LOGS_DIR/dst/$LEECHER_ID -h $HASH -p -D $LOGS_DIR/dst/$LEECHER_ID/leecher_$LEECHER_ID " -t $EXPERIMENT_TIME -o $LOGS_DIR/dst/$LEECHER_ID &
