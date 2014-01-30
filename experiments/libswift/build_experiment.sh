#!/bin/bash -xe
# %*% Prepare all the necessary stuff for the libswift experiment.
# %*% Does the following:
# %*% - Create the output directories for seeder (src) and leechers (dst)
# %*% - Creates a data file to seed
# %*% - Checks if the previous experiment was cleaned up correctly
# %*% - Creates and mounts a temporary filesystem for the containers
# %*% - Checks out and builds libswift



# logging
mkdir -p $OUTPUT_DIR/src
mkdir -p $OUTPUT_DIR/dst

# kill previous bridge
interface="/sys/class/net/"$BRIDGE_NAME
if [ -d "interface" ]; then
    sudo /sbin/ifconfig $BRIDGE_NAME down 2>/dev/null 
    sudo /sbin/brctl delbr $BRIDGE_NAME 2>/dev/null
fi

# setup networking bridge
sudo /sbin/brctl addbr $BRIDGE_NAME
sudo /sbin/brctl setfd $BRIDGE_NAME 0

sudo /sbin/ifconfig $BRIDGE_NAME $BRIDGE_IP netmask 255.255.255.0 up

sudo /sbin/iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
sudo /sbin/iptables -A FORWARD -i $BRIDGE_NAME -o eth0 -j ACCEPT

# create data file
# @CONF_OPTION FILE_SIZE: Size of the file to seed. (e,g., 10M - for syntax see man truncate)
[ -z "$FILE_SIZE" ] && FILE_SIZE="10M"
FILENAME=file_seed.tmp
truncate -s $FILE_SIZE $OUTPUT_DIR/$FILENAME

# make sure the leecher stopped
sudo /usr/bin/lxc-stop -n seeder

# always remove the container in case it didn't shut down correctly
# @CONF_OPTION CONTAINER_DIR: Directory to use for the lxc container (e.g., /tmp/debian-libswift) note the remark in README.MD concerning the sudoers file
if [ -d "$CONTAINER_DIR" ]; then
	# umount the union filesystem
	if mount | grep "$CONTAINER_DIR "; then
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
sudo /bin/mount -t tmpfs none /tmp/container
sudo /bin/mount -t aufs -o br=/tmp/container:/ none $CONTAINER_DIR
sudo /bin/mount --bind /home $CONTAINER_DIR/home

cd swift
make
cd -
#buildswift.sh
