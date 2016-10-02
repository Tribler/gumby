#!/bin/bash
# run_nosetests_for_jenkins.sh ---
#
# Filename: run_nosetests_for_jenkins.sh
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Mon Dec  2 18:24:48 2013 (+0100)

# Commentary:
# %*% This script runs the tests passed as argument using nose with all the
# %*% flags needed to generate all the data to generate the reports used in
# %*% the jenkins experiments.
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


set -e
shopt -s nocasematch

# @CONF_OPTION NOSE_RUN_DIR: Specify from which directory nose should run (default is $PWD)
if [ ! -z "$NOSE_RUN_DIR" ]; then
    cd $NOSE_RUN_DIR
fi

# @CONF_OPTION RUN_PYLINT: Run pylint in parallel with the unit tests (default is TRUE)
if [ "${RUN_PYLINT}" != "false" ]; then
    ionice -c 3 nice pylint --ignore=.git --ignore=dispersy --ignore=pymdht --ignore=libnacl --output-format=parseable --reports=y  Tribler \
         > $OUTPUT_DIR/pylint.out 2> $OUTPUT_DIR/pylint.log &
    PYLINT_PID=$!
fi

# @CONF_OPTION RUN_SLOCCOUNT: Run sloccount in parallel with the unit tests (default is TRUE)
if [ "${RUN_SLOCCOUNT}" != "false" ]; then

    mkdir -p $OUTPUT_DIR/slocdata

    (ionice -c 3 nice sloccount --datadir $OUTPUT_DIR/slocdata --duplicates --wide --details Tribler | \
            fgrep -v .svn | fgrep -v .git | fgrep -v /dispersy/ | fgrep -v /SwiftEngine/ | \
            fgrep -v debian | fgrep -v test_.Tribler | fgrep -v /pymdht/ \
                                                             > $OUTPUT_DIR/sloccount.out 2> $OUTPUT_DIR/sloccount.log) &
    SLOCCOUNT_PID=$!
fi

shopt -u nocasematch

echo Nose will run from $PWD

# TODO(emilon): Make the timeout configurable

NOSEARGS_COMMON="--with-xunit --all-modules --traverse-namespace --cover-package=Tribler --cover-tests --cover-inclusive "
NOSECMD="nosetests -v --with-xcoverage --xcoverage-file=$OUTPUT_DIR/coverage.xml --xunit-file=$OUTPUT_DIR/nosetests.xml.part $NOSEARGS_COMMON"

export NOSE_LOGFORMAT="%(levelname)-7s %(created)d %(module)15s:%(name)s:%(lineno)-4d %(message)s"

# @CONF_OPTION NOSE_TESTS_PARALLELISATION: Run tests in that many concurrent nose instances. WARNING: if this is set,
# NOSE_TESTS_TO_RUN becomes mandatory and has to be a single dir where all files that match test_.*.py will be run by
# nose.

# @CONF_OPTION NOSE_TESTS_TO_RUN: Specify which tests to run in nose syntax. (default is everything nose can find from within NOSE_RUN_DIR)
if [ -z ${NOSE_TESTS_PARALLELISATION} ] || [ ${NOSE_TESTS_PARALLELISATION} -eq 0 ]; then
    if [ $(uname) == "Linux" ]; then
        process_guard.py -t 3600 -m $OUTPUT_DIR -c "$NOSECMD $NOSE_TESTS_TO_RUN"
    else # not using processguard on OS X/Windows
        $NOSECMD $NOSE_TESTS_TO_RUN
    fi
else
    if [ -d ${NOSE_TESTS_TO_RUN} ]; then
        NOSECMD_FILE="$OUTPUT_DIR/nosecommands"
        TEST_NUMBER=$(find ${NOSE_TESTS_TO_RUN} -type f -iname "test_*.py" | wc -l)

        let "BUCKET_SIZE=$TEST_NUMBER / ${NOSE_TESTS_PARALLELISATION}"
        if [ "$(expr $BUCKET_SIZE \* $NOSE_TESTS_PARALLELISATION)" -lt $TEST_NUMBER ]; then
            let "BUCKET_SIZE=1+$BUCKET_SIZE"
        fi

        COUNT=0
        OLD_IFS=$IFS
        IFS=$'\n'

        SORT_CMD="sort"
        if [ $(uname) == "Darwin" ]; then
            SORT_CMD="gsort"
        fi

        # This weird sort call sorts randomly with a fixed salt so the test sorting is always the same, but not alphabetical
        if [[ $(uname) == MSYS* ]]; then
            NOSE_TESTS_UNIX_PATH=$(cygpath -u $NOSE_TESTS_TO_RUN)
            LINES=$(find ${NOSE_TESTS_UNIX_PATH} -type f -iname "test_*.py" | ${SORT_CMD} -R --random-source=/dev/zero | xargs -n${BUCKET_SIZE})
        else
            LINES=$(find ${NOSE_TESTS_TO_RUN} -type f -iname "test_*.py" | ${SORT_CMD} -R --random-source=/dev/zero | xargs -n${BUCKET_SIZE})
        fi

        TEST_RUNNER_OUT_DIR=$OUTPUT_DIR/test_runners_output
        if [ $(uname) == "Linux" ]; then
            for LINE in $LINES; do
                echo -n "TEST_BUCKET=$COUNT COVERAGE_FILE=.coverage.$COUNT wrap_in_vnc.sh 'nosetests -v --with-xcoverage  " >> $NOSECMD_FILE
                echo -n "--xunit-file=$OUTPUT_DIR/${COUNT}_nosetests.xml.part " >> $NOSECMD_FILE
                echo -n "$NOSEARGS_COMMON '" >> $NOSECMD_FILE
                echo $LINE >> $NOSECMD_FILE
                let COUNT=1+$COUNT
            done
            IFS=$OLD_IFS
            process_guard.py -T -t 1200 -m $OUTPUT_DIR -o $TEST_RUNNER_OUT_DIR -f $NOSECMD_FILE || PG_EXIT_STATUS=$?
            rm -f $OUTPUT_DIR/*_nosetests.xml
            if [ ! -z "$PG_EXIT_STATUS" ]; then
                if [  "$PG_EXIT_STATUS" -eq 5 ]; then
                    echo "WARNING: At least one test run failed, proceeding"
                else
                    echo "ERROR: Process guard failed with exit code $PG_EXIT_STATUS, aborting and printing logs"
                    [ ! -z $PYLINT_PID ] && kill -3 $PYLINT_PID ||:
                    [ ! -z $SLOCCOUNT_PID ] && kill -3 $SLOCCOUNT_PID ||:
                    for LOG in $(ls -1 $TEST_RUNNER_OUT_DIR/* | sort); do
                        echo "##vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv##"
                        echo "## Last 20 lines of $LOG"
                        tail -20 $LOG
                        echo "## End of $LOG"
                        echo "##^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^##"
                    done
                    exit 1
                fi
            fi
        else
            mkdir $TEST_RUNNER_OUT_DIR
            for LINE in $LINES; do
                echo "Starting $LINE"
                TIMEOUT_CMD="timeout"
                if [ $(uname) == "Darwin" ]; then
                    TIMEOUT_CMD="gtimeout"
                fi
                TEST_BUCKET=$COUNT COVERAGE_FILE=.coverage.$COUNT ${TIMEOUT_CMD} 600 $WORKSPACE/gumby/scripts/wrap_in_temp_home.sh nosetests -v --with-xcoverage --xunit-file=$OUTPUT_DIR/${COUNT}_nosetests.xml.part $NOSEARGS_COMMON $LINE \
                > $TEST_RUNNER_OUT_DIR/${COUNT}.out 2> $TEST_RUNNER_OUT_DIR/${COUNT}.err &
                let COUNT=1+$COUNT
            done
            wait
        fi
    else
        echo "ERROR: NOSE_TESTS_PARALLELISATION is set but NOSE_TESTS_TO_RUN is not a directory, bailing out."
        echo "NOSE_TESTS_TO_RUN set to: $NOSE_TESTS_TO_RUN which resolves to $(readlink -f $NOSE_TESTS_TO_RUN)"
        exit 1
    fi
fi

python-coverage combine
python-coverage xml -o $OUTPUT_DIR/coverage.xml

chmod 644 $OUTPUT_DIR/coverage.xml

echo Nose finished.

# This is a hack to convince Jenkins' Xcover plugin to parse the coverage file generated by nosexcover.
ESCAPED_PATH=$(echo $PWD| sed 's~/~\\/~g')

if [ $(uname) == "Darwin" ]; then
    # On OS X, the -i option to sed expects the extension of the backup file first.
    sed -i '' 's/<!-- Generated by coverage.py: http:\/\/nedbatchelder.com\/code\/coverage -->/<sources><source>'$ESCAPED_PATH'<\/source><\/sources>/g' $OUTPUT_DIR/*coverage.xml
elif [[ $(uname) == MSYS* ]]; then
    UNIX_OUTPUT_DIR=$(cygpath -u $OUTPUT_DIR)
    sed -i 's/<!-- Generated by coverage.py: http:\/\/nedbatchelder.com\/code\/coverage -->/<sources><source>'$ESCAPED_PATH'<\/source><\/sources>/g' $UNIX_OUTPUT_DIR/*coverage.xml
else
    sed -i 's/<!-- Generated by coverage.py: http:\/\/nedbatchelder.com\/code\/coverage -->/<sources><source>'$ESCAPED_PATH'<\/source><\/sources>/g' $OUTPUT_DIR/*coverage.xml
fi

# Fix nose's xml output so the logs of failed tests don't get printed twice on the report.
pushd $OUTPUT_DIR
for XML in *nosetests.xml.part; do
    echo "processing $XML"
    xmlstarlet fo -C $XML | xmlstarlet ed -u '/testsuite/testcase/error/text()' -v '' > nosetests.tmp.xml
    #xmlstarlet fo -C $XML | xmlstarlet ed -u '/testsuite/testcase/error/text()' -v '' -u '/testsuite/testcase/failure/text()' -v '' > nosetests.tmp.xml
    mv nosetests.tmp.xml $(basename $XML .part )
done
popd

echo Waiting for pylint at $(date)
wait $PYLINT_PID ||:
echo Waiting for sloccount at $(date)
wait $SLOCCOUNT_PID
echo Done waiting at $(date)

exit $PG_EXIT_STATUS
#
# run_nosetests_for_jenkins.sh ends here
