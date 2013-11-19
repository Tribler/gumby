#!/bin/bash -xe

EXPECTED_ARGS=3
if [ $# -ne $EXPECTED_ARGS ]
then
	echo "Usage: `basename $0` repository_dir src_store filename"
	exit 65
fi

REPOSITORY_DIR="/home/$1"
SRC_STORE="$2"
FILENAME="$3"

# fix path so libswift can find libevent
export LD_LIBRARY_PATH=/usr/local/lib

# start eth0 and set gateway
ifconfig eth0 up 
route add default gw 192.168.1.20

# create file to seed
# TODO: hardcoded now

# seed file
$REPOSITORY_DIR/swift -l 1337 -f $SRC_STORE/$FILENAME -p -H
