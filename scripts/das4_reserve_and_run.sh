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

if [ -z "$HEAD_IP" ]; then
    HEAD_IP=$(hostname)
fi

# This will be used from das4_node_run_job.sh to rsync the output data back to the head node
if [ "$HEAD_NODES" == '[]' ]; then
    # This means we are running the experiment locally
    mkdir $OUTPUT_DIR/localhost
    export OUTPUT_DIR_URI="$HEAD_IP:$OUTPUT_DIR/localhost"
else
    export OUTPUT_DIR_URI="$HEAD_IP:$OUTPUT_DIR"
fi

echo "Reserving $DAS4_NODE_AMOUNT nodes for $DAS4_RESERVE_DURATION secs."
module load prun

JOB_STATUS_FILE=/tmp/das4_job_$USER
export RMS_DEBUG=1
(prun -t $DAS4_RESERVE_DURATION -v -np $DAS4_NODE_AMOUNT das4_node_run_job.sh 2> >(tee $JOB_STATUS_FILE >&2) ) &
PID=$!

sleep 2

RESERVATION_ID=$(head -n1 $JOB_STATUS_FILE | sed 's/Reservation number \([0-9]*\):.*/\1/g')
rm $JOB_STATUS_FILE

echo
preserve -llist
echo
echo "*** If the job gets queued, you can cancel waiting using Ctrl+C"
echo "*** (check DAS4 status with 'preserve -llist')"
echo "*** (or cancel the experiment using 'qdel $RESERVATION_ID')"
echo


function stop_everything {
    kill -1 $PID &>/dev/null # according to http://www.cs.vu.nl/das4/prun.shtml, must send SIGINT
    qdel $RESERVATION_ID
    exit
}
trap stop_everything SIGHUP SIGTERM SIGINT

wait $PID
qdel $RESERVATION_ID

#
# das4_reserve_and_run.sh ends here