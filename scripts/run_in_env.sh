#!/bin/bash -ex
# run-in-env.sh ---
#
# Filename: run-in-env.sh
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Fri Jun 14 18:07:35 2013 (+0200)

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

cd `dirname $0`/../..
export PROJECTROOT=`pwd`
echo "Project root is: $PROJECTROOT"

# Load env variables for this experiment
source experiment_vars.sh

# Update PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$PROJECTROOT

# Update PATH
export PATH=$PATH:$PROJECTROOT/gumby/scripts

# Update LD_LIBRARY_PATH and PATH if we are using a SystemTap enabled Python runtime
# if [ "$USE_SYSTEMTAP" == True ]; then
# fi

# Enter virtualenv in case there's one
if [ ! -z "$VIRTUALENV_DIR" -a -d "$VIRTUALENV_DIR" ]; then
    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$PWD/systemtap/inst/lib
    export PATH=$PATH:$PWD/systemtap/inst/bin
    source $VIRTUALENV_DIR/bin/activate
    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$EXTRA_LD_LIBRARY_PATH
fi

# Path substitution for the tapsets, needs to be done even in case of USE_LOCAL_SYSTEMTAP
# is disabled as we could be using systemtap from within the experiment.
mkdir -p $VIRTUALENV_DIR/tapsets
for TAP in gumby/scripts/stp/tapsets/* ; do
    sed "s\\__VIRTUALENV_PATH__\\$VIRTUALENV_DIR\\g" < $TAP >  $VIRTUALENV_DIR/tapsets/$(basename -s .i $TAP)
done

# if [ "$USE_LOCAL_SYSTEMTAP" == True -o "$USE_LOCAL_VENV" == True ]; then
# fi

# Create the experiment output dir if its missing
export OUTPUTDIR=$PROJECTROOT/output
mkdir -p $OUTPUTDIR

# Run the actual command
exec $* && echo "Successful execution."

#
# run-in-env.sh ends here
