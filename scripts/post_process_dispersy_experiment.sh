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

if [ -z "$DISPERSY_STATISTICS_EXTRACTION_CMD" ]; then
    DISPERSY_STATISTICS_EXTRACTION_CMD=extract_dispersy_statistics.py
fi

cd $OUTPUT_DIR
#Step 1: Extract the data needed for the graphs from the experiment log file.

TEMPFILE=$(mktemp)
$DISPERSY_STATISTICS_EXTRACTION_CMD . $MESSAGES_TO_PLOT > $TEMPFILE
#Get the XMIN XMAX XSTART vars from the extracted data
source $TEMPFILE
rm $TEMPFILE

#Step 2: Extract the resource usage data from the process_guard logs.
extract_process_guard_stats.py . . $XSTART

#Step 3: Reduce the data
reduce_dispersy_statistics.py . 300

#Step 4: Graph the stuff
# TODO(emilon): Maybe move this to the general setup script
#make sure the R local install dir exists
mkdir -p $R_LIBS_USER
R --no-save --quiet < $R_SCRIPTS_PATH/install.r

(R --no-save --quiet --args $XMIN $XMAX < $R_SCRIPTS_PATH/drop.r          ; PID1=$!) 2>&1 > /dev/null | tee drop.r.log &
(R --no-save --quiet --args $XMIN $XMAX < $R_SCRIPTS_PATH/total_records.r ; PID2=$!) 2>&1 > /dev/null | tee total_records.r.log &
(R --no-save --quiet --args $XMIN $XMAX < $R_SCRIPTS_PATH/connections.r   ; PID3=$!) 2>&1 > /dev/null | tee connections.r.log &
(R --no-save --quiet --args $XMIN $XMAX < $R_SCRIPTS_PATH/send_received.r ; PID4=$!) 2>&1 > /dev/null | tee send_received.r.log &
(R --no-save --quiet --args $XMIN $XMAX < $R_SCRIPTS_PATH/cputimes.r      ; PID5=$!) 2>&1 > /dev/null | tee cputimes.r.log &
(R --no-save --quiet --args $XMIN $XMAX < $R_SCRIPTS_PATH/statistics.r    ; PID6=$!) 2>&1 > /dev/null | tee statistics.r.log &


wait $PID1
DROP=$?
wait $PID2
RECORDS=$?
wait $PID3
CONNECTIONS=$?
wait $PID4
SEND_RECVD=$?
wait $PID5
CPU=$?
wait $PID6
STATISTICS=$?

echo "exit statuses:" DROP: $DROP RECORDS: $RECORDS CONNECTIONS: $CONNECTIONS SEND_RECVD: $SEND_RECVD CPU: $CPU STATISTICS: $STATISTICS

#
# post_process_dispersy_experiment.sh ends here
