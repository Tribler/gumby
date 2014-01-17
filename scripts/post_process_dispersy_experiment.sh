#!/bin/bash
# post_process_dispersy_experiment.sh ---
#
# Filename: post_process_dispersy_experiment.sh
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Wed Oct  9 13:48:19 2013 (+0200)

# Commentary:
#
# This script will extract the data from the experiment run and create the graphs from then.
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

# Step 1: Look for non-empty stderr files and print its contents

echo "Looking for execution errors..."
for FILE in $(find -type f ! -empty -name "*.err"); do
    echo "Found in: $FILE"
    cat "$FILE"
done
echo "Done"

# @CONF_OPTION DISPERSY_STATISTICS_EXTRACTION_CMD: Override the default statistics extraction script.
if [ -z "$DISPERSY_STATISTICS_EXTRACTION_CMD" ]; then
    DISPERSY_STATISTICS_EXTRACTION_CMD=extract_dispersy_statistics.py
fi

cd $OUTPUT_DIR
#Step 2: Extract the data needed for the graphs from the experiment log file.

TEMPFILE=$(mktemp)
$DISPERSY_STATISTICS_EXTRACTION_CMD . $MESSAGES_TO_PLOT > $TEMPFILE
#Get the XMIN XMAX XSTART vars from the extracted data
source $TEMPFILE
rm $TEMPFILE

#Step 3: Extract the resource usage data from the process_guard logs.
extract_process_guard_stats.py . . $XSTART

#Step 4: Reduce the data
reduce_dispersy_statistics.py . 300

#Step 5: Graph the stuff
export R_SCRIPTS_TO_RUN="\
drop.r
total_records.r
connections.r
send_received.r
send_diff.r
cputimes.r
memtimes.r
statistics.r
writebytes.r
readbytes.r
bl.r
"

graph_data.sh

#
# post_process_dispersy_experiment.sh ends here
