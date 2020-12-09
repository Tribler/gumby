#!/bin/bash

while read -r SERVER
do
  cmd="INSTANCES_TO_RUN=$INSTANCES_TO_RUN NODE_AMOUNT=$NODE_AMOUNT EXPERIMENT_NAME=$EXPERIMENT_NAME INSTANCE_COMMAND=$DAS4_NODE_COMMAND NODE_TIMEOUT=$NODE_TIMEOUT SYNC_PORT=$SYNC_PORT SCENARIO_FILE=$SCENARIO_FILE TRACKER_PORT=$TRACKER_PORT NUM_VALIDATORS=$NUM_VALIDATORS NUM_CLIENTS=$NUM_CLIENTS TX_RATE=$TX_RATE EXPERIMENT_DIR=$SCENARIO_DIR VENV=/home/martijn/venv3 gumby/scripts/surfnet_run.sh"
  ssh -n martijn@$SERVER $cmd &
  pids[${i}]=$!
done < "$SURFNET_SERVERS_FILE"

# wait for all pids
for pid in ${pids[*]}; do
    wait $pid
done

# Rsync everything back
OUTPUT_DIR=/tmp/Experiment_${EXPERIMENT_NAME}_output
while read -r SERVER
do
  echo "RSynching back from $SERVER"
  mkdir -p output/localhost
  rsync -r martijn@$SERVER:$OUTPUT_DIR/ output/localhost/$SERVER
done < "$SURFNET_SERVERS_FILE"