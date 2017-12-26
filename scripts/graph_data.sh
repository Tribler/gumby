#!/bin/bash
# graph_data.sh ---
#
# Filename: graph_data.sh
# Description:
# Author: Elric Milon & Riccardo Petrocco
# Maintainer:
# Created: Wed Oct  9 13:48:19 2013 (+0200)

# Commentary:
#
# Generic script that runs the graph creation
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

# TODO(emilon): Maybe move this to the general setup script
#make sure the R local install dir exists
mkdir -p $R_LIBS_USER
R --no-save --quiet < $R_SCRIPTS_PATH/install.r

for R_SCRIPT in ""$R_SCRIPTS_TO_RUN $EXTRA_R_SCRIPTS_TO_RUN; do
    if [ -e $EXPERIMENT_DIR/r/$R_SCRIPT ]; then
        R_SCRIPT_PATH=$EXPERIMENT_DIR/r/$R_SCRIPT
    else
        if [ -e $R_SCRIPTS_PATH/$R_SCRIPT ]; then
            R_SCRIPT_PATH=$R_SCRIPTS_PATH/$R_SCRIPT
        else
            echo "ERROR: $R_SCRIPT not found!"
            FAILED=5
        fi
    fi
    R --no-save --quiet --args $XMIN $XMAX $R_SCRIPT < $R_SCRIPT_PATH | tee ${R_SCRIPT}.log &
done

wait

exit $FAILED
#
# post_process_dispersy_experiment.sh ends here
