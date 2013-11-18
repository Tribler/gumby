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

set -e

if [ -z "$HEAD_HOST" ]; then
    echo "HEAD_HOST is not set, using current host"
    export HEAD_HOST=$(hostname)
fi

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
#
# das4_reserve_and_run.sh ends here
