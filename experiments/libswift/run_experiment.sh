#!/bin/bash -xe

EXPERIMENT_DIR=$( dirname $(readlink -f "$0"))
if [ ! -d "$EXPERIMENT_DIR" ]; then
    EXPERIMENT_DIR=$( dirname $(readlink -f $(which "$0")))
fi
if [ ! -d "$EXPERIMENT_DIR" ]; then
    echo "Couldn't figure out where the experiment is, bailing out."
    exit 1
fi

# get full path, easier for use in container
WORKSPACE_DIR=$(readlink -f $WORKSPACE_DIR) 
FILENAME=file_$FILE_SIZE.tmp

# Set defaults for config variables ---------------------------------------------------
# Override these on Jenkins before running the script.
[ -z $EXPERIMENT_TIME ] && EXPERIMENT_TIME=30
[ -z $FILE_SIZE ] && FILE_SIZE="10MB"
[ -z $NO_OF_LEECHERS ] && NO_OF_LEECHERS="1"
# ------------------------------------------------------------------------------

echo "Running swift processes for $EXPERIMENT_TIME seconds"
echo "Workspace: $WORKSPACE_DIR"
echo "Output dir: $OUTPUT_DIR"

# wait for the hash to be generated - note that this happens in the container fs
while [ ! -f $CONTAINER_DIR/$OUTPUT_DIR/$FILENAME.mbinmap ] ;
do
      sleep 2
done

HASH=$(cat $CONTAINER_DIR/$OUTPUT_DIR/$FILENAME.mbinmap | grep hash | cut -d " " -f 3)

for (( i = 1 ; i < $NO_OF_LEECHERS+1; i++ ))
do
	LEECHER_IP=$NETWORK_IP_RANGE.$(($LEECHER_ID+$i))
sudo /usr/bin/lxc-execute -n leecher_$i \
		-s lxc.network.type=veth \
		-s lxc.network.flags=up \
		-s lxc.network.link=$BRIDGE_NAME \
		-s lxc.network.ipv4=$LEECHER_IP/24 \
		-s lxc.rootfs=$CONTAINER_DIR \
		-s lxc.pts=1024 \
		-- $WORKSPACE_DIR/$LEECHER_CMD $WORKSPACE_DIR/$REPOSITORY_DIR $OUTPUT_DIR $HASH $NETEM_DELAY $NETEM_PACKET_LOSS $WORKSPACE_DIR/$PROCESS_GUARD_CMD $EXPERIMENT_TIME $BRIDGE_IP $SEEDER_IP $SEEDER_PORT $OUTPUT_DIR $(($LEECHER_ID+$i)) &
done


wait

# ------------- LOG PARSING -------------

# copy logs back from containers
cp -R $CONTAINER_DIR/$OUTPUT_DIR/src $OUTPUT_DIR
cp -R $CONTAINER_DIR/$OUTPUT_DIR/dst $OUTPUT_DIR

# TODO: parsing very broken at the moment
# TODO: tmp preprocess because process_guard.py in gumby now adds a first line to the resource_usage.log files
if $GENERATE_PLOTS; then


	tail -n +2 $LOGS_DIR/src/resource_usage.log > $LOGS_DIR/src/resource_usage.log.tmp
	# remove the (sh) process
	sed '/(sh)/d' $LOGS_DIR/src/resource_usage.log.tmp > $LOGS_DIR/src/resource_usage.log
	tail -n +2 $LOGS_DIR/dst/resource_usage.log > $LOGS_DIR/dst/resource_usage.log.tmp
	sed '/(sh)/d' $LOGS_DIR/dst/resource_usage.log.tmp > $LOGS_DIR/dst/resource_usage.log

	$WORKSPACE_DIR/gumby/experiments/libswift/parse_logs.py $LOGS_DIR/src
	$WORKSPACE_DIR/gumby/experiments/libswift/parse_logs.py $LOGS_DIR/dst

	# ------------- PLOTTING -------------
	gnuplot -e "logdir='$LOGS_DIR/src';peername='src';plotsdir='$PLOTS_DIR'" $WORKSPACE_DIR/gumby/experiments/libswift/resource_usage.gnuplot
	gnuplot -e "logdir='$LOGS_DIR/dst';peername='dst';plotsdir='$PLOTS_DIR'" $WORKSPACE_DIR/gumby/experiments/libswift/resource_usage.gnuplot

	gnuplot -e "logdir='$LOGS_DIR';plotsdir='$PLOTS_DIR'" $WORKSPACE_DIR/gumby/experiments/libswift/speed.gnuplot

	rm -f $PLOTS_DIR_LAST/*
	cp $PLOTS_DIR/* $PLOTS_DIR_LAST/
fi

# umount the union filesystem
#sudo umount $CONTAINER_DIR
#rmdir $CONTAINER_DIR
