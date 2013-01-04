#!/bin/bash
set -e

SCRIPTS_PATH=$PWD/scripts
EXPERIMENT_CONFIG=$SCRIPTS_PATH/das4-baseconfig.conf
export PATH=$PATH:$SCRIPTS_PATH
export PYTHONPATH=$PYTHONPATH:$PWD/../mainbranch

#DAS4 Set up:
module load prun/default
# check if we allready have SGE_KEEP_TMPFILES=no in .bashrc, if not add it
cat ~/.bashrc | grep SGE_KEEP_TMPFILES || echo SGE_KEEP_TMPFILES=no >> ~/.bashrc

#Modify baseconfig such that it contains all global variables
cd ../mainbranch

echo "" >> "$EXPERIMENT_CONFIG"
echo HEAD_IP=$HEAD_IP >> "$EXPERIMENT_CONFIG"
echo SYNC_PORT=$SYNC_PORT >> "$EXPERIMENT_CONFIG"
echo MESSAGESTOPLOT=$MESSAGESTOPLOT >> "$EXPERIMENT_CONFIG"

sed -i "s/^COMMUNITY\_SCRIPT=.*/COMMUNITY\_SCRIPT=$COMMUNITY_SCRIPT/" "$EXPERIMENT_CONFIG"
sed -i "s/^COMMUNITY\_ARGS=.*/COMMUNITY\_ARGS=$COMMUNITY_ARGS/" "$EXPERIMENT_CONFIG"

#Start experiment
das4-start $EXPERIMENT_CONFIG $PWD/../dispersy_experiments/$SCENARIO_PATH/ $NRNODES $DURATION $TRACKER_PORT
post-process-experiment $EXPERIMENT_CONFIG $PWD/../dispersy_experiments/$SCENARIO_PATH/

#XMIN,XMAX is now in experiment config
source $EXPERIMENT_CONFIG

cd ../dispersy_experiments/$SCENARIO_PATH/output

R --no-save --quiet --args $XMIN $XMAX < $WORKSPACE/dispersy_experiments/scripts/r/drop.r &
PID1=$! 
R --no-save --quiet --args $XMIN $XMAX < $WORKSPACE/dispersy_experiments/scripts/r/total_records.r &
PID2=$!
R --no-save --quiet --args $XMIN $XMAX < $WORKSPACE/dispersy_experiments/scripts/r/connections.r &
PID3=$!
R --no-save --quiet --args $XMIN $XMAX < $WORKSPACE/dispersy_experiments/scripts/r/send_received.r &
PID4=$!
R --no-save --quiet --args $XMIN $XMAX < $WORKSPACE/dispersy_experiments/scripts/r/cputimes.r &
PID5=$!

wait $PID1
wait $PID2
wait $PID3
wait $PID4
wait $PID5

find -type f -exec chmod a+r {} \;
find -type d -exec chmod a+rx {} \;