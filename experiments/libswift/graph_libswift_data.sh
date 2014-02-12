#!/bin/bash
# graph_libswift_data
#
# Filename: graph_libswift_data.sh
# Description:
# Author: Riccardo Petrocco
# Maintainer:

# Commentary:
#
# This script will extract the data from the experiment run and create the graphs from then.
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

set -e

# Step 1: Look for non-empty stderr files and print its contents

echo "Looking for execution errors..."
for FILE in $(find -type f -empty -name "*.err"); do
    echo "Found empty log file: $FILE"
done
echo "Done"

# @CONF_OPTION LIBSWIFT_STDERR_PARSER_CMD: Override the default stderr parser script (default: TODO).
if [ -z "$LIBSWIFT_STDERR_PARSER_CMD" ]; then
    LIBSWIFT_STDERR_PARSER_CMD=parser.py
fi

#Step 3: Extract the data needed for the graphs from the experiment log file.
cd $OUTPUT_DIR
$LIBSWIFT_STDERR_PARSER_CMD . . 

#Step 4: Graph the stuff
if [ -z "$R_SCRIPTS_TO_RUN" ]; then
    export R_SCRIPTS_TO_RUN="downloadtime.r ledbat.r requests.r dip.r"
fi

graph_data.sh

