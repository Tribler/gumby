#!/bin/bash
# run_tracker.sh ---
#
# Filename: run_tracker.sh
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Fri Jun 14 12:44:06 2013 (+0200)

# Commentary:
#
# %*% Starts a dispersy tracker.
#
#

# Change Log:
#
#
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street, Fifth
# Floor, Boston, MA 02110-1301, USA.
#
#

# Code:

# @CONF_OPTION TRACKER_PORT: Set the port to be used by the tracker. (required)
# @CONF_OPTION TRACKER_IP: Listen only on the specified IP. (default: dispersy's default 0.0.0.0)
# @CONF_OPTION TRACKER_CRYPTO: Set the type of crypto to be used by the tracker. (default is ECCrypto)
# @CONF_OPTION TRACKER_PROFILE: Enable profiling for the tracker? (default: FALSE)

if [ -z "$TRACKER_PORT" ]; then
    echo "ERROR: you need to specify the TRACKER_PORT when using $0" >&2
    exit 1
fi

if [ -z "$TRACKER_CRYPTO" ]; then
    echo "TRACKER_CRYPTO not set, using ECCrypto"
    export TRACKER_CRYPTO="ECCrypto"
fi

cd $PROJECT_DIR

if [ -e tribler ]; then
    cd tribler/Tribler
fi

if [ ! -e dispersy ]; then
    echo "Dispersy dir not found at $PWD/dispersy, bailing out."
    exit 1
fi

export PYTHONPATH=$PYTHONPATH:$PWD/dispersy

if [ -z "$HEAD_HOST" ]; then
    HEAD_HOST=$(hostname)
fi

if [ ! -z "$SYNC_SUBSCRIBERS_AMOUNT" ]; then
    EXPECTED_SUBSCRIBERS=$SYNC_SUBSCRIBERS_AMOUNT
else
    if [ ! -z "$DAS4_INSTANCES_TO_RUN" ]; then
        EXPECTED_SUBSCRIBERS=$DAS4_INSTANCES_TO_RUN
    else
        echo 'Neither SYNC_SUBSCRIBERS_AMOUNT nor DAS4_INSTANCES_TO_RUN is set, not balancing.'
        EXPECTED_SUBSCRIBERS=1
    fi
fi

mkdir -p "$OUTPUT_DIR/tracker"
rm -f ../bootstraptribler.txt

if [ "${TRACKER_PROFILE,,}" == "true" ]; then
    echo "Tracker profiling enabled"
    EXTRA_ARGS="--profile=$OUTPUT_DIR/tracker_$TRACKER_PORT.cprofile --profiler=cprofile --savestats"
fi

if [ ! -z "$TRACKER_IP" ]; then
    EXTRA_TRACKER_ARGS="$EXTRA_TRACKER_ARGS --ip $TRACKER_IP "
fi

while [ $EXPECTED_SUBSCRIBERS -gt 0 ]; do
    echo $HEAD_HOST $TRACKER_PORT >> ../bootstraptribler.txt
    # Do not daemonize the process as we want to wait for all of them to die at the end of this script
    twistd -n $EXTRA_ARGS --logfile="$OUTPUT_DIR/tracker_out_$TRACKER_PORT.log" tracker --port $TRACKER_PORT --crypto $TRACKER_CRYPTO $EXTRA_TRACKER_ARGS --statedir="$OUTPUT_DIR/tracker" &
    let TRACKER_PORT=$TRACKER_PORT+1
    let EXPECTED_SUBSCRIBERS=$EXPECTED_SUBSCRIBERS-1000
done

wait

#
# run_tracker.sh ends here
