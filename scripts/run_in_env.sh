#!/bin/bash -e
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

# Remove variable prefixes used to avoid SSHD filters.
while read VARNAME ; do
    NEWVAR=$(echo $VARNAME | sed 's/^LC_GMB_//')
    export $NEWVAR="${!VARNAME}" # indirect expansion
    unset $VARNAME # Unset "Escaped"" var from the env
done < <(env |grep ^LC_GMB_ | cut -f1 -d= )

cd `dirname $0`/../..
export PROJECTROOT=`pwd`
echo "Project root is: $PROJECTROOT"

# Update PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$PROJECTROOT

# Update PATH
export PATH=$PATH:$PROJECTROOT/gumby/scripts

# R User lib dir
export R_LIBS_USER=$R_LIBS_USER${R_LIBS_USER:+:}$HOME/R

# Enter virtualenv in case there's one
if [ ! -z "$VIRTUALENV_DIR" -a -d "$VIRTUALENV_DIR" ]; then
    echo "Enabling virtualenv at $VIRTUALENV_DIR"
    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$VIRTUALENV_DIR/inst/lib:$VIRTUALENV_DIR/lib
    export PATH=$PATH:$VIRTUALENV_DIR/inst/bin
    source $VIRTUALENV_DIR/bin/activate
    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$EXTRA_LD_LIBRARY_PATH

    # Path substitution for the tapsets, needs to be done even in case of USE_LOCAL_SYSTEMTAP
    # is disabled as we could be using systemtap from within the experiment.
    mkdir -p $VIRTUALENV_DIR/tapsets
    for TAP in gumby/scripts/stp/tapsets/* ; do
        echo "$TAP  ->  $VIRTUALENV_DIR/tapsets/$(basename $TAP .i) "
        sed "s\\__VIRTUALENV_PATH__\\$VIRTUALENV_DIR\\g" < $TAP >  $VIRTUALENV_DIR/tapsets/$(basename $TAP .i)
    done
fi

# Create the experiment output dir if its missing
export OUTPUTDIR=$PROJECTROOT/output
mkdir -p $OUTPUTDIR

# Run the actual command
echo "Running $*"
exec $*

#
# run-in-env.sh ends here
