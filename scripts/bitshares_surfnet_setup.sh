#!/bin/bash

echo "Syncing BitShares data directory with instances"
while read -r SERVER
do
  echo "Sending BitShares data directory to $SERVER..."
  rsync -r --delete /home/jenkins/bitshares martijn@$SERVER:/tmp/ &
  pids[${i}]=$!
done < "$SURFNET_SERVERS_FILE"

./gumby/scripts/surfnet_setup.sh
