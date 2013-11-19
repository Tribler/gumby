#!/bin/bash -xe

if [ -z "$1" ]; then
    echo "Usage: init.sh repository_dir"
    exit
fi
REPOSITORY_DIR=$1

REPOSITORY_URL="http://svn.tribler.org/libswift/branches/riccardo/testing4devel/"


ifconfig eth0 up 
route add default gw 192.168.1.20

export PATH=$PATH:/usr/bin

# done by lxc (added them to debootstrap)
# apt-get update
# apt-get install -y lxc subversion make g++ wget
if [ ! -d "/home/libevent-2.0.21-stable" ]; then
	cd /home/
	wget https://github.com/downloads/libevent/libevent/libevent-2.0.21-stable.tar.gz --no-check-certificate
	tar -xvf libevent-2.0.21-stable.tar.gz
	cd /home/libevent-2.0.21-stable
	./configure && make install
fi 






svn co $REPOSITORY_URL $REPOSITORY_DIR

cd $REPOSITORY_DIR
make




