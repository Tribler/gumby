#!/bin/bash -xe
# Note: runs on host (so not inside a container), used as tracker_cmd in gumby

WORKSPACE_DIR=$(readlink -f $WORKSPACE_DIR)
FILENAME=file_$FILE_SIZE.tmp

# start seeder
sudo /usr/bin/lxc-execute -n seeder \
	-s lxc.network.type=veth \
	-s lxc.network.flags=up \
	-s lxc.network.link=$BRIDGE_NAME \
	-s lxc.network.ipv4=$SEEDER_IP/24 \
	-s lxc.rootfs=$CONTAINER_DIR \
	-s lxc.pts=1024 \
	-- $WORKSPACE_DIR/$PROCESS_GUARD_CMD -c "$WORKSPACE_DIR/$REPOSITORY_DIR/swift -l $SEEDER_PORT -f $OUTPUT_DIR/file_$FILE_SIZE.tmp -p -H -D $OUTPUT_DIR/src/seeder  " -t $EXPERIMENT_TIME -o $OUTPUT_DIR/src &
	#$SEEDER_CMD $REPOSITORY_DIR /$SRC_STORE $FILENAME $PROCESS_GUARD_CMD $DATE $EXPERIMENT_TIME $BRIDGE_IP $SEEDER_PORT &
