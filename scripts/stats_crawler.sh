#!/bin/bash -xe
# stats_crawler.sh ---
# Starts the statistics crawler.
# Author: Cor-Paul Bezemer
# Maintainer:
# Created: Feb 09 2015


isolated_tribler_network.sh &

STATEDIR="$OUTPUT_DIR/statsCrawler"

mkdir -p $STATEDIR/sqlite/
cd tribler/Tribler
twistd --logfile=$STATEDIR/crawler.log --pidfile=$STATEDIR/crawler.pid --nodaemon bartercast_crawler --statedir=$STATEDIR 
cd ../..
