#!/bin/bash

# Check that $OUTPUT_DIR exists to avoid going to hour home dir by accident.
if [ -z "$OUTPUT_DIR" ]; then
    echo 'ERROR: $OUTPUT_DIR variable not found, are you running this script from within gumby?'
    exit 1
fi

cd $OUTPUT_DIR

# Graph the stuff
export R_SCRIPTS_TO_RUN="\
ipv8_msg_stats.r
"
graph_data.sh
