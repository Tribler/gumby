# ingest_revision_runs.sh ---
#
# Filename: ingest_revision_runs.sh
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Wed Jul 17 15:37:59 2013 (+0200)

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

set -xe

if [ ! -d "$1" ]; then
    echo "Usage: $0 OUTPUT_DIR_NAME"
    exit 1
fi

# Find the experiment dir
EXPERIMENT_DIR=$( dirname $(readlink -f "$0"))
if [ ! -d "$EXPERIMENT_DIR" ]; then
    EXPERIMENT_DIR=$( dirname $(readlink -f $(which "$0")))
fi
if [ ! -d "$EXPERIMENT_DIR" ]; then
    echo "Couldn't figure out where the experiment is, bailing out."
    exit 1
fi

CONFFILE=$EXPERIMENT_DIR"/test.conf"

# TODO: Put this in the config file
if [ -z "$TESTNAME" ]; then
    TESTNAME="Whatever"
fi
if [ -z "$TEST_DESCRIPTION" ]; then
    TEST_DESCRIPTION="Lalla arr"
fi

cd $1
for CSV in $(ls -1tr); do
    REP_DIR=report_$(echo $CSV | cut -f2 -d_ )
    REVISION=$(echo $CSV | cut -f3 -d_ ) # TODO, change this when we use the new csv files with counter field
    make_io_writes_report.sh $REP_DIR $CSV $TEST_DESCRIPTION
    store_run_in_database.py $CONFFILE $REP_DIR/summary_per_stacktrace.csv $REVISION $TESTNAME
done
# generate_profile.py now refreshes/generates all profiles for a test case,
# so it is not necessary to give a revision as argument
generate_profile.py $CONFFILE $TESTNAME

#
# ingest_revision_runs.sh ends here
