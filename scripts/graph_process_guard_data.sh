#!/bin/bash
# %*% This script will generate all the resource usage graphs from process_guard.py's output files found in OUTPUT_DIR.

# Check that $OUTPUT_DIR exists to avoid going to hour home dir by accident.
if [ -z "$OUTPUT_DIR" ]; then
    echo 'ERROR: $OUTPUT_DIR variable not found, are you running this script from within gumby?'
    exit 1
fi

cd $OUTPUT_DIR

TEMPFILE=$(mktemp)
process_guard_stats_parser.py . .
#Get the XMIN XMAX vars from the extracted data
source axis_stats.txt

collect_profile_logs.py .

modify_autoplot.py . $XSTART

# Graph the stuff
export R_SCRIPTS_TO_RUN="\
autoplot.r
cputimes.r
memtimes.r
writebytes.r
readbytes.r
network.r
threads.r
"
export XMIN
export XMAX
graph_data.sh
