#!/bin/bash -xe
# Note: runs on host (so not inside a container), used as tracker_cmd in gumby

WORKSPACE_DIR=$(readlink -f $WORKSPACE_DIR)
FILENAME=file_seed.tmp

# note: use 0.0.0.0:2000 for listening as using only the port will result in ipv6 communication
# between the leechers (i.e., they can't connect to each other)
	
SWIFT_CMD="$WORKSPACE_DIR/swift/swift -l 0.0.0.0:$SEEDER_PORT -f $OUTPUT_DIR/$FILENAME -p -H -D $OUTPUT_DIR/src/seeder -L $OUTPUT_DIR/src/seeder_ledbat" 

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
	-- su $USER -c "$WORKSPACE_DIR/gumby/scripts/process_guard.py -c '${SWIFT_CMD}' -t $EXPERIMENT_TIME -o $OUTPUT_DIR/src &" || :
	#$SEEDER_CMD $REPOSITORY_DIR /$SRC_STORE $FILENAME $PROCESS_GUARD_CMD $DATE $EXPERIMENT_TIME $BRIDGE_IP $SEEDER_PORT &
