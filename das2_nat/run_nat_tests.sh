#!/bin/bash
#svn co https://svn.tribler.org/dispersy/branches/20120612-27046-mainbranch dispersy
#svn co https://svn.tribler.org/abc/branches/boudewijn/das4-walker das4_walker

set -e

if [ -z "$WORKSPACE" ]; then
    echo "This script is meant to be executed from a Jenkins Job."
    exit 1
fi

#Install R dependencies
R --no-save --quiet < $WORKSPACE/experiments/scripts/r/install.r

if [ -z "$1" ]; then
    HOSTLIST=$(dirname $(readlink -f $0))/hostlist.txt
else
    HOSTLIST="$1"
fi

if [ ! -e dispersy -o ! -e das4_walker ]; then
    echo "Please, check out dispersy and das4_walker before running this script."
    exit 1
fi

sed -i 's/^DAS4SCENARIO = True/DAS4SCENARIO = False/' das4_walker/walker/community.py
sed -i 's/^DAS2SCENARIO = False/DAS2SCENARIO = True/' das4_walker/walker/community.py

echo Deleting old data
rm -fR output

echo Deleting old code
parallel-ssh -l jenkins -i -v -p 40 -h $HOSTLIST rm -fR dispersy das4_walker mainbranch

echo Copying dispersy
parallel-rsync -l jenkins -v -o out -e out -p 40 -h $HOSTLIST -avz dispersy/ /home/jenkins/dispersy

echo Copying das4-walker
parallel-rsync -l jenkins -p 40 -h $HOSTLIST -avz das4_walker/ /home/jenkins/das4_walker

echo Running the experiment
parallel-ssh -l jenkins  -t 0 -i -v -p 40 -h $HOSTLIST 'cd das4_walker && pwd && rm -fR dispersy && mv ../dispersy . && python -c "from dispersy.tool.main import main; main()" --script walker.script.ScenarioScript --kargs peernumber=$(hostname |cut -f2 -de),scenario=config'

echo Getting experiment data back from the nodes
mkdir -p output
for HOST in $(grep -v ^# $HOSTLIST); do
    rsync --delete -a jenkins@$HOST:das4_walker/walktest.log output/$HOST.walktest.log
done


