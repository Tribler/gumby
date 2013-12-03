#!/bin/bash -xe
# Note: runs inside a container


EXPECTED_ARGS=14
if [ $# -ne $EXPECTED_ARGS ]
then
	echo "Usage: `basename $0` repository_dir dst_store hash netem_delay netem_packet_loss process_guard_cmd experiment_time bridge_ip seeder_ip seeder_port logs_dir leecher_id username"
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
USERNAME="${13}"
NETEM_RATE="${14}"

# fix formatting for random variation
NETEM_DELAY=${NETEM_DELAY/'_'/' '}


# fix path so libswift can find libevent
# export LD_LIBRARY_PATH=/usr/local/lib
tc qdisc add dev eth0 root handle 1: netem delay $NETEM_DELAY loss $NETEM_PACKET_LOSS
tc qdisc add dev eth0 parent 1: handle 10: tbf rate $NETEM_RATE limit 30k burst 30k

tc qdisc show
ifconfig
	

#wget http://download.thinkbroadband.com/200MB.zip

SWIFT_CMD="$REPOSITORY_DIR/swift -t $SEEDER_IP:$SEEDER_PORT -o $LOGS_DIR/dst/$LEECHER_ID -h $HASH -p -D $LOGS_DIR/dst/$LEECHER_ID/leecher_$LEECHER_ID -L $LOGS_DIR/dst/$LEECHER_ID/leecher_$LEECHER_ID_ledbat"

# leech file
su $USERNAME -c "mkdir -p $LOGS_DIR/dst/$LEECHER_ID"
su $USERNAME -c "$PROCESS_GUARD_CMD -c '${SWIFT_CMD}' -t $EXPERIMENT_TIME -o $LOGS_DIR/dst/$LEECHER_ID &"



