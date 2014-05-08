#!/bin/bash
# stap_iterate_over_all_revs.sh ---
#
# Filename: stap_iterate_over_all_revs.sh
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Thu Jul 11 14:51:05 2013 (+0200)
# Version:

# Commentary:
#
#
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

set -ex


if [ -z "$CONFFILE" ]; then
	echo "CONFFILE not set, bailing out"
	exit 2
fi
if [ -z "$OUTPUT_DIR_NAME" ]; then
	echo "OUTPUT_DIR_NAME not set, bailing out"
	exit 2
fi

export CONFFILE=$(readlink -f $CONFFILE)

rm -f /tmp/results.log

# do this in jenkins instead
#if [ -z "$REPOSITORY_DIR" ]; then
#    echo "ERROR: REPOSITORY_DIR variable not set, bailing out."
#    exit 2
#fi

#if [ ! -d "$REPOSITORY_DIR" -a ! -z "$REPOSITORY_URL" ]; then
#    git clone "$REPOSITORY_URL" "$REPOSITORY_DIR"
#fi

# Do only one iteration by default
if [ -z "$STAP_RUN_ITERATIONS" ]; then
    STAP_RUN_ITERATIONS=1
fi
if [ -z "$TESTNAME" ]; then
    TESTNAME="Whatever"
fi

ITERATION_RESULTS_FILE=$OUTPUT_DIR/rev_iter_results.log

pushd $REPOSITORY_DIR
git clean -fd

COUNT=0

GIT_LOG_CMD=""
if [ ! -z "$STAP_RUN_REVS" ]; then
	GIT_LOG_CMD="--topo-order --merges --quiet $STAP_RUN_REVS"
fi

for REV in $(git log $GIT_LOG_CMD | grep ^"commit " | cut -f2 -d" "); do
    let COUNT=1+$COUNT

    git checkout $REV
    # TOOD make submodules configurable?
    git submodule sync
    git submodule update
    export REVISION=$REV
    ITERATION=0
    while [ $ITERATION -lt $STAP_RUN_ITERATIONS ]; do
        let ITERATION=1+$ITERATION

        rm -fR sqlite
        pycompile $([ -z "$PYTHONOPTIMIZE" ] || echo -n "-O" ) .
        cd ..
        [ ! -z "$PRE_PROBE_CMD" ] && $PRE_PROBE_CMD
        process_guard.py -t $PROCESS_GUARD_TIMEOUT -c 'run_stap_probe.sh "$TEST_COMMAND" $OUTPUT_DIR/${TESTNAME}_${COUNT}_${ITERATION}_${REVISION}.csv' ||:
        [ ! -z "$POST_PROBE_CMD" ] && $POST_PROBE_CMD
        cd -
        echo $? $ITERATION $REV >> $ITERATION_RESULTS_FILE
        git checkout -- .
        git clean -fd
    done
done

popd

#
# stap_iterate_over_all_revs.sh ends here
