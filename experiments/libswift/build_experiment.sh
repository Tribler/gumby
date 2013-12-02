#!/bin/bash -xe

# logging
mkdir -p $OUTPUT_DIR/src
mkdir -p $OUTPUT_DIR/dst

# create data file
FILENAME=file_$FILE_SIZE.tmp
truncate -s $FILE_SIZE $OUTPUT_DIR/$FILENAME

# make sure the leecher stopped
sudo /usr/bin/lxc-stop -n seeder

# always remove the container in case it didn't shut down correctly
if [ -d "$CONTAINER_DIR" ]; then
	# umount the union filesystem
	if mount | grep $CONTAINER_DIR; then
		sudo /bin/umount $CONTAINER_DIR -l
	fi
	if mount | grep /tmp/container; then
		sudo /bin/umount /tmp/container	-l
	fi
	rmdir $CONTAINER_DIR
fi

echo "Initializing LXC container in $CONTAINER_DIR..."
# create union filesystem
mkdir -p $CONTAINER_DIR
mkdir -p /tmp/container
sudo /bin/mount -t tmpfs none /tmp/container/
sudo /bin/mount -t aufs -o br=/tmp/container:/ none $CONTAINER_DIR
sudo /bin/mount --bind /home $CONTAINER_DIR/home

svn co $REPOSITORY_URL $REPOSITORY_DIR
cd $REPOSITORY_DIR
make
cd -
