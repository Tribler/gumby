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
LOGS_ARCHIVE_DIR=$(readlink -f $LOGS_ARCHIVE_DIR)

# Initialize filesystem for container
CONTAINER_DIR="$LXC_CONTAINERS_DIR/$LXC_CONTAINER_NAME"

if [ ! -d "$CONTAINER_DIR" ]; then
	echo "Initializing LXC container in $CONTAINER_DIR..."
	# sudo cp $WORKSPACE_DIR/gumby/experiments/libswift/lxc-debian-libswift /usr/share/lxc/templates/lxc-debian-libswift
	# sudo chmod +x $EXPERIMENT_DIR/lxc-debian-libswift
	# sudo /usr/bin/lxc-create -n $LXC_CONTAINER_NAME -t $EXPERIMENT_DIR/lxc-debian-libswift -B dir --dir $CONTAINER_DIR
	# create union filesystem
	mkdir -p $CONTAINER_DIR
	mkdir -p /tmp/container
	sudo mount -t tmpfs none /tmp/container/
	sudo mount -t aufs -o br=/tmp/container:/ none $CONTAINER_DIR
	#sudo echo -e "#!/bin/sh -e\n ifconfig eth0 up \n route add default gw $BRIDGE_IP\n echo nameserver 8.8.8.8 >> /etc/resolv.conf" | sudo tee $CONTAINER_DIR/etc/rc.local
fi


# Set defaults for config variables ---------------------------------------------------
# Override these on Jenkins before running the script.
[ -z $EXPERIMENT_TIME ] && EXPERIMENT_TIME=30
[ -z $FILE_SIZE ] && FILE_SIZE="10MB"
# ------------------------------------------------------------------------------

echo "Running swift processes for $EXPERIMENT_TIME seconds"
echo "Workspace: $WORKSPACE_DIR"
echo "Output dir: $OUTPUT_DIR"

# Define and create storage locations
SRC_STORE=$WORKSPACE_DIR/src/store
DST_STORE=$WORKSPACE_DIR/dst/store

SRC_LXC_STORE=$WORKSPACE_DIR/$CONTAINER_DIR/$WORKSPACE_DIR/src/store
DST_LXC_STORE=$WORKSPACE_DIR/$CONTAINER_DIR/$WORKSPACE_DIR/dst/store


mkdir -p $SRC_LXC_STORE $DST_LXC_STORE

# logging
DATE=$(date +'%F-%H-%M')
LOGS_DIR=$LOGS_ARCHIVE_DIR/$DATE
PLOTS_DIR=$OUTPUT_DIR/plots/$DATE
PLOTS_DIR_LAST=$OUTPUT_DIR/plots/last
mkdir -p $LOGS_DIR $PLOTS_DIR $PLOTS_DIR_LAST
mkdir -p $LOGS_DIR/src
mkdir -p $LOGS_DIR/dst

# create data file
FILENAME=file_$FILE_SIZE.tmp
truncate -s $FILE_SIZE $SRC_LXC_STORE/$FILENAME

# copy startup scripts
INIT_LXC_CMD="init.sh"
SEEDER_LXC_CMD="start_seeder.sh"
LEECHER_LXC_CMD="start_leecher.sh"

PROCESS_GUARD_CMD="$WORKSPACE_DIR/gumby/scripts/process_guard.py"
INIT_CMD="$EXPERIMENT_DIR/$INIT_LXC_CMD"
SEEDER_CMD="$EXPERIMENT_DIR/$SEEDER_LXC_CMD"
LEECHER_CMD="$EXPERIMENT_DIR/$LEECHER_LXC_CMD"

#sudo cp $EXPERIMENT_DIR/init.sh $INIT_CMD
#sudo cp $EXPERIMENT_DIR/start_seeder.sh $SEEDER_CMD
#sudo cp $EXPERIMENT_DIR/start_leecher.sh $LEECHER_CMD
#sudo chmod +x $EXPERIMENT_DIR/*.sh

# init lxc config files
# replace some variables first
#sed -e 's|\${rootfs}|'`pwd`/$CONTAINER_DIR/rootfs'|g' $EXPERIMENT_DIR/seeder_config > $EXPERIMENT_DIR/seeder_config.conf
#sed -i 's|\${bridge_name}|'$BRIDGE_NAME'|g' $EXPERIMENT_DIR/seeder_config.conf
#sed -i 's|\${seeder_ip}|'$SEEDER_IP'|g' $EXPERIMENT_DIR/seeder_config.conf

#sed -e 's|\${rootfs}|'`pwd`/$CONTAINER_DIR/rootfs'|g' $EXPERIMENT_DIR/leecher_config > $EXPERIMENT_DIR/leecher_config.conf
#sed -i 's|\${bridge_name}|'$BRIDGE_NAME'|g' $EXPERIMENT_DIR/leecher_config.conf
#sed -i 's|\${leecher_ip}|'$LEECHER_IP'|g' $EXPERIMENT_DIR/leecher_config.conf

# fix setup commands for lxc container


# setup container (build libevent, libswift etc if necessary)
#sudo lxc-execute -n $LXC_CONTAINER_NAME \
#	-s lxc.network.type=veth \
#	-s lxc.network.link=$BRIDGE_NAME \
#	-s lxc.network.ipv4=$SEEDER_IP/24 \
#	-s lxc.rootfs=$CONTAINER_DIR \
#	-s lxc.pts=1024 \
#	$EXPERIMENT_DIR/$INIT_LXC_CMD $REPOSITORY_DIR $REPOSITORY_URL $BRIDGE_IP
# TODO download gumby on container so we can use process_guard.py
#sudo cp $WORKSPACE_DIR/gumby/scripts/process_guard.py $CONTAINER_DIR/home/$LXC_CONTAINER_NAME/$PROCESS_GUARD_CMD

# directly build stuff on the host
#if [ ! -d "$WORKSPACE_DIR/libevent-2.0.21-stable" ]; then
#	wget https://github.com/downloads/libevent/libevent/libevent-2.0.21-stable.tar.gz --no-check-certificate
#	tar -xvf libevent-2.0.21-stable.tar.gz
#	cd $WORKSPACE_DIR/libevent-2.0.21-stable
#	./configure && make install
#fi


svn co $REPOSITORY_URL $REPOSITORY_DIR
cd $REPOSITORY_DIR
make
cd -

# start seeder
#sudo lxc-execute -n seeder -f $EXPERIMENT_DIR/seeder_config.conf $SEEDER_LXC_CMD $REPOSITORY_DIR /$SRC_LXC_STORE $FILENAME  $PROCESS_GUARD_CMD $DATE $EXPERIMENT_TIME $BRIDGE_IP $SEEDER_PORT &
sudo /usr/bin/lxc-execute -n seeder \
	-s lxc.network.type=veth \
	-s lxc.network.flags=up \
	-s lxc.network.link=$BRIDGE_NAME \
	-s lxc.network.ipv4=$SEEDER_IP/24 \
	-s lxc.rootfs=$CONTAINER_DIR \
	-s lxc.pts=1024 \
	-- $PROCESS_GUARD_CMD -c "$REPOSITORY_DIR/swift -l $SEEDER_PORT -f $SRC_STORE/$FILENAME -p -H  " -t $EXPERIMENT_TIME -o $LOGS_DIR/src &
	#$SEEDER_CMD $REPOSITORY_DIR /$SRC_STORE $FILENAME $PROCESS_GUARD_CMD $DATE $EXPERIMENT_TIME $BRIDGE_IP $SEEDER_PORT &

# wait for the hash to be generated - note that this happens in the container fs
while [ ! -f $SRC_LXC_STORE/$FILENAME.mbinmap ] ;
do
      sleep 2
done

HASH=$(cat $SRC_LXC_STORE/$FILENAME.mbinmap | grep hash | cut -d " " -f 3)

# start destination swift
# sudo lxc-execute -n leecher -f $EXPERIMENT_DIR/leecher_config.conf $LEECHER_LXC_CMD $REPOSITORY_DIR /$DST_LXC_STORE $HASH $NETEM_DELAY $PROCESS_GUARD_CMD $DATE $EXPERIMENT_TIME $BRIDGE_IP $SEEDER_IP $SEEDER_PORT
sudo lxc-execute -n leecher \
	-s lxc.network.type=veth \
	-s lxc.network.flags=up \
	-s lxc.network.link=$BRIDGE_NAME \
	-s lxc.network.ipv4=$LEECHER_IP/24 \
	-s lxc.rootfs=$CONTAINER_DIR \
	-s lxc.pts=1024 \
	-- $LEECHER_CMD $REPOSITORY_DIR $DST_STORE $HASH $NETEM_DELAY $PROCESS_GUARD_CMD $DATE $EXPERIMENT_TIME $BRIDGE_IP $SEEDER_IP $SEEDER_PORT $LOGS_DIR

# kill the seeder when the leecher is done, only possible way for now :/
sudo lxc-stop -n seeder

echo "---------------------------------------------------------------------------------"

# show storage contents
#ls -alh $SRC_STORE
#ls -alh $DST_STORE

# --------- EXPERIMENT END ----------
#kill -9 $SWIFT_SRC_PID $SWIFT_DST_PID || true
#fusermount -z -u $LFS_SRC_STORE
#fusermount -z -u $LFS_DST_STORE
#kill -9 $LFS_SRC_PID $LFS_DST_PID || true
#pkill -9 swift || true

# separate logs

# remove temps
#sudo rm -rf $SRC_STORE
#sudo rm -rf $DST_STORE
# rm -rf ./src ./dst # TODO

# ------------- LOG PARSING -------------

# copy logs back from containers
cp -R $CONTAINER_DIR/$LOGS_DIR/src $LOGS_DIR/
cp -R $CONTAINER_DIR/$LOGS_DIR/dst $LOGS_DIR/


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
# umount $CONTAINER_DIR
# rmdir $CONTAINER_DIR
