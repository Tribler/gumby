#!/bin/bash

python3 gumby/experiments/algorand/create_network.py --validators $NUM_VALIDATORS

echo "Syncing Algorand network directory with instances"
while read -r SERVER
do
  echo "Sending Algorand network directory to $SERVER..."
  rsync -r --delete /tmp/algo_data_$NUM_VALIDATORS martijn@$SERVER:/tmp/ &
  pids[${i}]=$!
done < "$SURFNET_SERVERS_FILE"

./gumby/scripts/surfnet_setup.sh
