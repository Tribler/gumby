#!/bin/bash
# das4_reserve_and_run.sh ---
#
# Filename: das4_reserve_and_run.sh
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Tue Aug 27 19:27:30 2013 (+0200)

# Commentary:
#
# A simple script to run an experiment on the DAS4 trough prun.
#
#

# Change Log:
#
#
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street, Fifth
# Floor, Boston, MA 02110-1301, USA.
#
#

# Code:

cancel_reservation () {
# Cancel all our rc jobs in the queue
cat <<EOF | at now + 2 minutes

for RID in $(preserve -list | awk '{print $2 " " $1 " " $5 }' | grep rc$ | grep ^$USER | cut -f2 -d" "); do pdel $RID ; done

EOF

exit -15
}

trap cancel_reservation TERM

set -e

# @CONF_OPTION DAS4_NODE_AMOUNT: Set the number of nodes that will get reserved on each cluster to run this experiment. (required)
# @CONF_OPTION DAS4_RESERVE_DURATION: Set the reservation time lengh in seconds. (required)

if [ -z "$DAS4_NODE_AMOUNT" -o -z "$DAS4_RESERVE_DURATION" ]; then
    echo "ERROR: you need to specify both DAS4_NODE_AMOUNT and DAS4_RESERVE_DURATION when using $0" >&2
    exit 1
fi

# @CONF_OPTION HEAD_HOST: Override the head host where the worker nodes will sync their datasets back (default is the host name where the script is executed from)
if [ -z "$HEAD_HOST" ]; then
    echo "HEAD_HOST is not set, using current host"
    export HEAD_HOST=$(hostname)
fi

# @CONF_OPTION SYNC_HOST: Override the experiment synchronization server host to which the sync clients will try to connect to (default is HEAD_HOST)
if [ -z "$SYNC_HOST" ]; then
    echo "SYNC_HOST not set, using HEAD_HOST"
    #SYNC_HOST=$(echo $SSH_CLIENT | awk '{print $1}' )
    export SYNC_HOST=$HEAD_HOST
fi

# This will be used from das4_node_run_job.sh to rsync the output data back to the head node
if [ "$HEAD_NODES" == '[]' ]; then
    # This means we are running the experiment locally
    mkdir $OUTPUT_DIR/localhost
    export OUTPUT_DIR_URI="$HEAD_HOST:$OUTPUT_DIR/localhost"
else
    export OUTPUT_DIR_URI="$HEAD_HOST:$OUTPUT_DIR"
fi

echo "Reserving $DAS4_NODE_AMOUNT nodes for $DAS4_RESERVE_DURATION secs."

prun -t $DAS4_RESERVE_DURATION -v -np $DAS4_NODE_AMOUNT das4_node_run_job.sh &
PID=$!

sleep 1
preserve -llist
wait $PID

cancel_reservation

#
# das4_reserve_and_run.sh ends here
