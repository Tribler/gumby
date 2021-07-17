#!/bin/bash
# %*% A simple script to run experiments on the DAS4 trough prun.
# %*% Have in mind that this script uses das4_node_run_job.sh, so you will need to set its config options too.
EXIT_CODE=-15
cancel_reservation () {
# Cancel all our dr jobs in the queue
cat <<EOF | at now + 2 minutes

for RID in $(preserve -list | awk '{print $2 " " $1 " " $5 }' | grep dr$ | grep ^$USER | cut -f2 -d" "); do qdel -f $RID ; done

EOF

exit $EXIT_CODE
}

trap cancel_reservation TERM

set -e

# @CONF_OPTION NODE_AMOUNT: Set the number of nodes that will get reserved on each cluster to run this experiment. (required)
# @CONF_OPTION DAS4_RESERVE_DURATION: Set the reservation time length in seconds. (default is NODE_TIMEOUT+120)


if [ -z "$NODE_AMOUNT" ]; then
    echo "ERROR: you need to specify at least NODE_AMOUNT when using $0" >&2
    exit 1
fi
if [ -z "$DAS4_RESERVE_DURATION" ]; then
    echo "DAS4_RESERVE_DURATION not set, using NODE_TIMEOUT+120"
    let DAS4_RESERVE_DURATION=$NODE_TIMEOUT+120
fi

# Set the head host to the current host
export HEAD_HOST=$(hostname)

# @CONF_OPTION SYNC_HOST: Override the experiment synchronization server host to which the sync clients will try to connect to (default is HEAD_HOST)
if [ -z "$SYNC_HOST" ]; then
    echo "SYNC_HOST not set, using HEAD_HOST"
    #SYNC_HOST=$(echo $SSH_CLIENT | awk '{print $1}' )
    export SYNC_HOST=$HEAD_HOST
fi

mkdir $OUTPUT_DIR/localhost
export OUTPUT_DIR_URI="$HEAD_HOST:$OUTPUT_DIR/localhost"

# We need to go back to home in order to prevent prun complaining about not being able to cwd into the directory
WORKING_DIR=$PWD
cd ~

echo "Reserving $NODE_AMOUNT nodes for $DAS4_RESERVE_DURATION secs."
prun -t $DAS4_RESERVE_DURATION -v -np $NODE_AMOUNT das4_node_run_job.sh &
PID=$!

sleep 1
preserve -llist
wait $PID

EXIT_CODE=$?
cancel_reservation
