#!/bin/bash
# This script is called from das_reserve_and_run.sh and spawns N copies of the specified command, sending the output
# data back to the head node when finished.
let "PROCESSES_PER_NODE=$INSTANCES_TO_RUN/$NODE_AMOUNT"
let "PLUS_ONE_NODES=$INSTANCES_TO_RUN%$NODE_AMOUNT"

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

# @CONF_OPTION NODE_TIMEOUT: Time in seconds to wait for the sub-processes to run before killing them. (required)
(process_guard.py -f $CMDFILE -t $NODE_TIMEOUT -o $OUTPUT_DIR -m $OUTPUT_DIR  -i 5 2>&1 | tee process_guard.log) ||:

rm $CMDFILE

# Now, lets send the generated data back to the head node
rsync -a --delete-before "$OUTPUT_DIR/" "$OUTPUT_DIR_URI/$(hostname)/" 2>&1
