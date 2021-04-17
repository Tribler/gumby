#!/bin/bash

python3 gumby/experiments/libra/create_network.py --validators $NUM_VALIDATORS

echo "Syncing Diem network directory with instances"
while read -r SERVER
do
  echo "Sending Diem network directory to $SERVER..."
  rsync -r --delete /tmp/diem_data_$NUM_VALIDATORS martijn@$SERVER:/tmp/ &
  pids[${i}]=$!
done < "$SURFNET_SERVERS_FILE"

./gumby/scripts/surfnet_setup.sh
