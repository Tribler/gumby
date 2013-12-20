#!/bin/bash -x

export R_LIBS_USER=$R_LIBS_USER${R_LIBS_USER:+:}$HOME/R

# remove previous output
rm -rf output_*

tail -n +2 ./gumby/legacy_experiments/community_walking_NAT/das2_hostlist.txt | while read IP_ADDRESS HOSTNAME NAT_TYPE; do
    export TITLE_POSTFIX="$HOSTNAME - $IP_ADDRESS - $TYPE"
    echo "RUNNING FOR $TITLE_POSTFIX"

    # copy the dispersy directory (removing all old files)
    rsync --archive --verbose --delete --exclude .git dispersy/ jenkins@$IP_ADDRESS:~/dispersy

    # remove the previous results
    ssh -n jenkins@$IP_ADDRESS 'rm *.txt'

    # start experiment
    time ssh -n jenkins@$IP_ADDRESS 'TEST_OVERLAY_ALL_CHANNEL=yes python -m unittest dispersy.tests.test_overlay' || echo "$IP_ADDRESS $HOSTNAME FAILED, continue anyway"

    mkdir output_$HOSTNAME
    cd output_$HOSTNAME
    rsync --archive --verbose jenkins@$IP_ADDRESS:~/*.txt . || echo "UNABLE TO COPY DATA, continue anyway"
    cat ../gumby/legacy_experiments/community_walking_NAT/test_liveoverlay.r | R --no-save --silent || echo "UNABLE TO CREATE GRAPHS, continue anyway"
    cd $WORKSPACE
done
