#!/bin/bash -xe

# Define and create storage locations
#SRC_STORE=$WORKSPACE_DIR/$OUTPUT_DIR/src/store
#DST_STORE=$WORKSPACE_DIR/$OUTPUT_DIR/dst/store

#SRC_LXC_STORE=$WORKSPACE_DIR/$CONTAINER_DIR/$WORKSPACE_DIR/$OUTPUT_DIR/src/store
#DST_LXC_STORE=$WORKSPACE_DIR/$CONTAINER_DIR/$WORKSPACE_DIR/$OUTPUT_DIR/dst/store
#mkdir -p $SRC_LXC_STORE $DST_LXC_STORE



# logging
#DATE=$(date +'%F-%H-%M')
#LOGS_DIR=$LOGS_ARCHIVE_DIR/$DATE
#PLOTS_DIR=$OUTPUT_DIR/plots/$DATE
#PLOTS_DIR_LAST=$OUTPUT_DIR/plots/last
#mkdir -p $LOGS_DIR $PLOTS_DIR $PLOTS_DIR_LAST
mkdir -p $OUTPUT_DIR/src
mkdir -p $OUTPUT_DIR/dst

# create data file
FILENAME=file_$FILE_SIZE.tmp
truncate -s $FILE_SIZE $OUTPUT_DIR/$FILENAME

# always remove the container in case it didn't shut down correctly
if [ ! -d "$CONTAINER_DIR" ]; then
	sudo umount $CONTAINER_DIR
	rmdir $CONTAINER_DIR
fi

echo "Initializing LXC container in $CONTAINER_DIR..."
# sudo cp $WORKSPACE_DIR/gumby/experiments/libswift/lxc-debian-libswift /usr/share/lxc/templates/lxc-debian-libswift
# sudo chmod +x $EXPERIMENT_DIR/lxc-debian-libswift
# sudo /usr/bin/lxc-create -n $LXC_CONTAINER_NAME -t $EXPERIMENT_DIR/lxc-debian-libswift -B dir --dir $CONTAINER_DIR
# create union filesystem
mkdir -p $CONTAINER_DIR
mkdir -p /tmp/container
sudo /bin/mount -t tmpfs none /tmp/container/
sudo /bin/mount -t aufs -o br=/tmp/container:/ none $CONTAINER_DIR

svn co $REPOSITORY_URL $REPOSITORY_DIR
cd $REPOSITORY_DIR
make
cd -