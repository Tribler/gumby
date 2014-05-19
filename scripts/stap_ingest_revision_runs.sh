#!/bin/bash
# stap_ingest_revision_runs.sh ---
#
# Filename: stap_ingest_revision_runs.sh
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


# Find the experiment dir
## TODO: remove, use parameter instead

#EXPERIMENT_DIR=$( dirname $(readlink -f "$1"))
#if [ ! -d "$EXPERIMENT_DIR" ]; then
#    EXPERIMENT_DIR=$( dirname $(readlink -f $(which "$0")))
#fi
#if [ ! -d "$EXPERIMENT_DIR" ]; then
#    echo "Couldn't figure out where the experiment is, bailing out."
#    exit 1
#fi

if [ -z "$CONFFILE" ]; then
	echo "CONFFILE not set, bailing out"
	exit 2
fi
if [ ! -e "$CONFFILE" ]; then
	echo "Can't find config file, bailing out"
	exit 2
fi

# should be unnecessary but gumby seems to re-enter a venv for post process cmd
# so temp fix
export OUTPUTDIR=$(readlink -f $OUTPUT_DIR_NAME)
export CONFFILE=$(readlink -f $CONFFILE) 

if [ -z "$OUTPUTDIR" ]; then
	echo "OUTPUTDIR not set, bailing out"
	exit 2
fi

if [ -z "$SIM_REPORT_NAME" ]; then
	SIM_REPORT_NAME="simreport"
fi

if [ -z "$TESTNAME" ]; then
    TESTNAME="Whatever"
fi
if [ -z "$TEST_DESCRIPTION" ]; then
    TEST_DESCRIPTION="Lalla arr"
fi

cd $OUTPUTDIR
for CSV in $(ls $TESTNAME*.csv -1tr); do
    REVISION=$(basename $CSV .csv | cut -f4 -d_ )
    REP_DIR=report_$(echo $REVISION)_$(echo $CSV | cut -f3 -d_ )
    stap_make_io_writes_report.sh $REP_DIR $CSV "$TEST_DESCRIPTION"
    stap_store_run_in_database.py $CONFFILE $REP_DIR/summary_per_stacktrace.csv $REVISION $TESTNAME
done

for REV in $(ls *.csv | cut -f4 -d_ | uniq); do
	REV=$(basename $REV .csv)
	stap_insert_revision.py $CONFFILE $REV
	# generate_profile.py now refreshes/generates all profiles for a test case,
	# so it is not necessary to give a revision as argument
	stap_generate_profile.py $CONFFILE $REV $TESTNAME
	# calc similarity
	stap_calculate_similarity.py $CONFFILE $OUTPUTDIR $REV $TESTNAME	
done
    
# make report
mkdir -p $SIM_REPORT_NAME
# @CONF_OPTION TOOLNAME: # Name of project in the tribler repository (for linking to github)
stap_make_similarity_report.py $CONFFILE $SIM_REPORT_NAME $TOOLNAME $TESTNAME


#
# stap_ingest_revision_runs.sh ends here
