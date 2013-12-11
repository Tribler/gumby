#!/bin/bash -xe
# %*% Starts a libswift leecher (from run_experiment.sh), connects to a seeder and downloads a file. Note: runs inside a container.
# %*% start_seeder.sh must be started first.


EXPECTED_ARGS=14
if [ $# -ne $EXPECTED_ARGS ]
then
	echo "Usage: `basename $0` repository_dir dst_store hash netem_delay netem_packet_loss process_guard_cmd experiment_time bridge_ip seeder_port logs_dir username netem_rate netem_rate_ul iperf_test"
	exit 65
fi

# TODO use getopts
REPOSITORY_DIR="$1"
DST_STORE="$2"
FILENAME="$3"
NETEM_DELAY="$4"
NETEM_PACKET_LOSS="$5"
PROCESS_GUARD_CMD="$6"
EXPERIMENT_TIME="$7"
BRIDGE_IP="$8"
SEEDER_PORT="${9}"
LOGS_DIR="${10}"
USERNAME="${11}"
NETEM_RATE_DL="${12}"
NETEM_RATE_UL="${13}"
IPERF_TEST="${14}"

# fix formatting for random variation
# @CONF_OPTION SEEDER_DELAY: Netem delay for the seeder. 
NETEM_DELAY=${NETEM_DELAY/'_'/' '}
# @CONF_OPTION SEEDER_RATE: Download rate limit for the seeder. Configure the rate as rate_burst, so e.g. seeder_rate="1mbit_100k" 
IFS='_' read -ra RATE_DL <<< "$NETEM_RATE_DL"
RATE_DL=${RATE_DL[0]}
BURST_DL=${RATE_DL[1]}
# @CONF_OPTION SEEDER_RATE_UL: Upload rate limit for the seeder. Configure the rate as rate_burst, so e.g. seeder_rate_ul="1mbit_100k"
IFS='_' read -ra RATE_UL <<< "$NETEM_RATE_UL"
RATE_UL=${RATE_UL[0]}
BURST_UL=${RATE_UL[1]}

# ----------------- works
# ingress traffic
tc qdisc add dev eth0 handle ffff: ingress
tc filter add dev eth0 parent ffff: protocol ip prio 50 \
   u32 match ip src 0.0.0.0/0 police rate $RATE_DL \
   burst $BURST_DL drop flowid :1

# egress traffic
tc qdisc add dev eth0 root handle 1: netem delay $NETEM_DELAY loss $NETEM_PACKET_LOSS

# add netem stuff
tc qdisc add dev eth0 parent 1: tbf rate $RATE_UL limit $BURST_UL burst $BURST_UL
   
# !--------------------

tc qdisc show

# useful for testing the network settings so let's leave this here TODO make configurable
# To measure loss => Server side : iperf -s -u -i 1 Client side : iperf -c 192.168.1.2 -u -b 10m
# To check bandwidth => Server Side : iperf -s Client Side : iperf -c 192.168.1.2 -r
# To measure the delay / latency, we just use ping

# @CONF_OPTION IPERF_TEST: Set to true to use iperf test, otherwise swift seeder is started.
if $IPERF_TEST;
then
	iperf -s -w 64k -u -b 200M &	
else
	# leech file
	SWIFT_CMD="$REPOSITORY_DIR/swift -l 0.0.0.0:$SEEDER_PORT -f $LOGS_DIR/$FILENAME -p -H -D $LOGS_DIR/src/seeder -L $LOGS_DIR/src/seeder_ledbat" 
	su $USERNAME -c "$PROCESS_GUARD_CMD -c '${SWIFT_CMD}' -t $EXPERIMENT_TIME -o $LOGS_DIR/src -m $LOGS_DIR/src &" #|| :
fi

