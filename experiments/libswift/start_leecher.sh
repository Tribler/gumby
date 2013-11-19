#!/bin/bash -xe

EXPECTED_ARGS=4
if [ $# -ne $EXPECTED_ARGS ]
then
	echo "Usage: `basename $0` repository_dir dst_store hash netem_delay"
	exit 65
fi

REPOSITORY_DIR="/home/$1"
DST_STORE="$2"
HASH="$3"
NETEM_DELAY="$4"

# fix path so libswift can find libevent
export LD_LIBRARY_PATH=/usr/local/lib

# start eth0 and set gateway
ifconfig eth0 up 
route add default gw 192.168.1.20

tc qdisc add dev eth0 root netem delay $NETEM_DELAY

# leech file
$REPOSITORY_DIR/swift -t 192.168.1.110:1337 -o $DST_STORE/ -h $HASH -p 


# remove leeched file
rm -rf $DST_STORE/*

