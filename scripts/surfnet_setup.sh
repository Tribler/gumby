#!/bin/bash

echo "Syncing Gumby directory with instances"
while read -r SERVER
do
  echo "Sending Gumby directory to $SERVER..."
  rsync -r --delete gumby martijn@$SERVER:/home/martijn &
  pids[${i}]=$!
done < "$SURFNET_SERVERS_FILE"

# wait for all pids
for pid in ${pids[*]}; do
    wait $pid
done

echo "Building venvs on instances"
while read -r SERVER
do
  echo "Building virtualenv on $SERVER..."
  ssh -n martijn@$SERVER gumby/scripts/build_virtualenv_surfnet.sh &
  pids[${i}]=$!
done < "$SURFNET_SERVERS_FILE"

# wait for all pids
for pid in ${pids[*]}; do
    wait $pid
done