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
# This script runs N copies of the specified command and sends the output
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

set -ex

echo "$(hostname) here, spawning $DAS4_PROCESSES_PER_NODE instances of command: $DAS4_NODE_COMMAND"

OUTPUT_DIR=/local/$USER/Experiment_${EXPERIMENT_NAME}_output
rm -fR "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

CMDFILE=$(mktemp --tmpdir=/local/$USER/ process_guard_XXXXXXXXXXXXX_$USER)

for INSTANCE in $(seq 1 1 $DAS4_PROCESSES_PER_NODE); do
    echo "$DAS4_NODE_COMMAND" >> $CMDFILE
done

process_guard.py -f $CMDFILE -t $DAS4_NODE_TIMEOUT -o $OUTPUT_DIR -m $OUTPUT_DIR  -i 5 2>&1 | tee process_guard.log ||:

rm $CMDFILE

# Now, lets send the generated data back to the head node

rsync -av --delete-during "$OUTPUT_DIR/" "$OUTPUT_DIR_URI/$(hostname)/" && rm -fR "$OUTPUT_DIR"

#
# das4_node_run_job.sh ends here
