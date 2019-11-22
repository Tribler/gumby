#!/bin/bash
# das4_node_run_job.sh ---
#
# Filename: das4_node_run_job.sh
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Wed Aug 28 16:37:42 2013 (+0200)

# Commentary:
#
# This script is called from das4_reserve_and_run.sh and spawns N copies of the specified command, sending the output
# data back to the head node when finished.
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

let "PROCESSES_PER_NODE=$DAS4_INSTANCES_TO_RUN/$DAS4_NODE_AMOUNT"
let "PLUS_ONE_NODES=$DAS4_INSTANCES_TO_RUN%$DAS4_NODE_AMOUNT"

# let will return 1 if the last expression evaluates to 0, so set -e after calling it
set -e

PROCESSES_IN_THIS_NODE=$PROCESSES_PER_NODE

if [ $PLUS_ONE_NODES -gt 0 ]; then
    # Truncate the list to the first $PLUS_ONE_NODES, if we are in this segment, increase the number of processes by one
    echo $HOSTS | cut -d" " -f-$PLUS_ONE_NODES | grep -q $(hostname) && let "PROCESSES_IN_THIS_NODE=$PROCESSES_PER_NODE+1"
fi

export PROCESSES_IN_THIS_NODE

echo "$(hostname) here, spawning $PROCESSES_IN_THIS_NODE instances of command: $DAS4_NODE_COMMAND"

OUTPUT_DIR=/local/$USER/Experiment_${EXPERIMENT_NAME}_output
rm -fR "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

CMDFILE=$(mktemp --tmpdir=/local/$USER/ process_guard_XXXXXXXXXXXXX_$USER)

# @CONF_OPTION DAS4_NODE_COMMAND: The command that will be repeatedly launched in the worker nodes of the cluster. (required)
for INSTANCE in $(seq 1 1 $PROCESSES_IN_THIS_NODE); do
    echo "$DAS4_NODE_COMMAND" >> $CMDFILE
done

# @CONF_OPTION DAS4_NODE_TIMEOUT: Time in seconds to wait for the sub-processes to run before killing them. (required)
(process_guard.py -f $CMDFILE -t $DAS4_NODE_TIMEOUT -o $OUTPUT_DIR -m $OUTPUT_DIR  -i 5 2>&1 | tee process_guard.log) ||:

rm $CMDFILE

# Now, lets send the generated data back to the head node
rsync -a --delete-before "$OUTPUT_DIR/" "$OUTPUT_DIR_URI/$(hostname)/" 2>&1 ||:

#
# das4_node_run_job.sh ends here
