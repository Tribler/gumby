#!/bin/bash -xe
# stats_crawler.sh ---
# Starts the statistics crawler.
# Author: Cor-Paul Bezemer
# Maintainer:
# Created: Feb 09 2015


#isolated_tribler_network.sh &


STATEDIR="$OUTPUT_DIR/statsCrawler"

mkdir -p $STATEDIR/sqlite/

cd tribler/twisted
twistd --logfile=$STATEDIR/crawler.log --nodaemon bartercast_crawler --statedir=$STATEDIR &
sleep $PROCESS_GUARD_TIMEOUT
cd ../..

# if you want to run tests uncomment the following line
# wrap_in_vnc.sh run_nosetests_for_jenkins.sh
