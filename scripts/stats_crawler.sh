#!/bin/bash -xe
# stats_crawler.sh ---
# Starts the statistics crawler.
# Author: Cor-Paul Bezemer
# Maintainer:
# Created: Feb 09 2015


#isolated_tribler_network.sh &


STATEDIR="$OUTPUT_DIR/statsCrawler"

mkdir -p $STATEDIR/sqlite/
#while [ ! -f $DISPERSY_BOOTSTRAP_FILE ] ;
#	do
#	      sleep 2
#	done

#cp $DISPERSY_BOOTSTRAP_FILE $STATEDIR 
cd tribler/twisted
#twistd --logfile=$STATEDIR/crawler.log --pidfile=$STATEDIR/crawler.pid --nodaemon bartercast_crawler --statedir=$STATEDIR &
twistd --logfile=$STATEDIR/crawler.log --nodaemon bartercast_crawler --statedir=$STATEDIR &
sleep $PROCESS_GUARD_TIMEOUT
cd ../..

#wrap_in_vnc.sh run_nosetests_for_jenkins.sh
