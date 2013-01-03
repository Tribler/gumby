#!/bin/bash
set -e

SCRIPTS_PATH=$PWD/scripts
export PATH=$PATH:$SCRIPTS_PATH
export PYTHONPATH=$PYTHONPATH:$PWD/../mainbranch

#DAS4 Set up:
module load prun/default

cd ..

rm -fR dispersy_experiments/scenario_1000/output/*
rm -fR output/*

cd mainbranch

das4-start $SCRIPTS_PATH/das4-allchannel.conf $PWD/../dispersy_experiments/scenario_1000/ 20 5 $HEAD_IP $TRACKER_PORT $SYNC_PORT
post-process-experiment $SCRIPTS_PATH/das4-allchannel.conf $PWD/../dispersy_experiments/scenario_1000/

cd ../dispersy_experiments/scenario_1000/output

R --no-save --quiet < $WORKSPACE/dispersy_experiments/scripts/r/drop.r &
PID1=$! 
R --no-save --quiet < $WORKSPACE/dispersy_experiments/scripts/r/total_records.r &
PID2=$!
R --no-save --quiet < $WORKSPACE/dispersy_experiments/scripts/r/connections.r &
PID3=$!
R --no-save --quiet < $WORKSPACE/dispersy_experiments/scripts/r/send_received.r &
PID4=$!
R --no-save --quiet < $WORKSPACE/dispersy_experiments/scripts/r/cputimes.r &
PID5=$!

wait $PID1
wait $PID2
wait $PID3
wait $PID4
wait $PID5

find -type f -exec chmod a+r {} \;
find -type d -exec chmod a+rx {} \;