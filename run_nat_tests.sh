#!/bin/bash

set -e

#svn co https://svn.tribler.org/dispersy/branches/20120612-27046-mainbranch dispersy
#svn co https://svn.tribler.org/abc/branches/boudewijn/das4-walker das4_walker

if [ ! -e dispersy -o ! -e das4_walker ]; then
    echo "Please, check out dispersy and das4_walker before running this script."
    exit 1
fi

sed -i 's/^DAS4SCENARIO = True/DAS4SCENARIO = False/' das4_walker/walker/community.py
sed -i 's/^DAS2SCENARIO = False/DAS2SCENARIO = True/' das4_walker/walker/community.py

echo Deleting old data
rm -fR output

echo Deleting old code
parallel-ssh -p 40 -h hostlist.txt rm -fR /home/whirm/dispersy /home/emilon/das4_walker /home/emilon/mainbranch

echo Copying dispersy
parallel-rsync -v -o out -e out -p 40 -h hostlist.txt -avz dispersy /home/emilon/dispersy

echo Copying das4-walker
parallel-rsync -p 40 -h hostlist.txt -avz das4_walker/ /home/emilon/das4_walker

echo Running the experiment
parallel-ssh -t 0 -i -p 40 -h hostlist.txt 'cd das4_walker && pwd && python -c "from dispersy.tool.main import main; main()" --script walker.script.ScenarioScript --kargs peernumber=$(hostname |cut -f2 -de),scenario=config'

echo Getting experiment data back from the nodes
mkdir -p output
for HOST in $(grep -v ^# hostlist.txt); do
    rsync --delete -a $HOST:das4_walker/walktest.log output/$HOST.walktest.log
done


