#!/bin/bash -xe
# Note: runs on host (so not inside a container), used as tracker_cmd in gumby

WORKSPACE_DIR=$(readlink -f $WORKSPACE_DIR)
FILENAME=file_seed.tmp

if [ -z "$DEBUG_SWIFT" ]; then
	DEBUG_SWIFT=false

# note: use 0.0.0.0:2000 for listening as using only the port will result in ipv6 communication
# between the leechers (i.e., they can't connect to each other)


# start seeder
# @CONF_OPTION SEEDER_IP: Full IP of seeder (e.g., 192.168.1.110)
# @CONF_OPTION SEEDER_PORT: Port for the seeder (e.g., 2000)
# @CONF_OPTION BRIDGE_NAME: Name of the network bridge of the host (e.g., br0).
# @CONF_OPTION BRIDGE_IP: IP of the network bridge of the host (e.g., 192.168.1.20).
sudo /usr/bin/lxc-execute -n seeder \
	-s lxc.network.type=veth \
	-s lxc.network.flags=up \
	-s lxc.network.link=$BRIDGE_NAME \
	-s lxc.network.ipv4=$SEEDER_IP/24 \
	-s lxc.rootfs=$CONTAINER_DIR \
	-s lxc.pts=1024 \
	-- $WORKSPACE_DIR/$SEEDER_CMD $WORKSPACE_DIR/swift $OUTPUT_DIR $FILENAME $SEEDER_DELAY $SEEDER_PACKET_LOSS $WORKSPACE_DIR/gumby/scripts/process_guard.py $EXPERIMENT_TIME $BRIDGE_IP $SEEDER_PORT $OUTPUT_DIR $USER $SEEDER_RATE $SEEDER_RATE_UL $IPERF_TEST $DEBUG_SWIFT &


	#$SEEDER_CMD $REPOSITORY_DIR /$SRC_STORE $FILENAME $PROCESS_GUARD_CMD $DATE $EXPERIMENT_TIME $BRIDGE_IP $SEEDER_PORT &
