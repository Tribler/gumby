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

if [ ! -e $1 ]; then
    echo "Usage: $0 OUTPUT_DIR_NAME"
fi

CONFFILE=$(readlink -f "test.conf")
TESTCASE=Whatever
for CSV in $(ls -1tr); do
    REP_DIR=report_$(echo $CSV | cut -f2 -d_ )
    REVISION=$(echo $CSV | cut -f2 -d_ ) # TODO, change this when we use the new csv files with counter field
    make_io_writes_report.sh $REP_DIR $CSV "LALALAL arr"
    store_run_in_database.py $CONFFILE $REP_DIR/summary_per_stacktrace.csv $REVISION $TESTCASE 
done
# generate_profile.py now refreshes/generates all profiles for a test case, 
# so it is not necessary to give a revision as argument
generate_profile.py $CONFFILE $TESTCASE 

#
# ingest_revision_runs.sh ends here
