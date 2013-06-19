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

# Load env variables for this experiment
source experiment_vars.sh

# Update PATH
export PATH=$PATH:$PWD/gumby/scripts

# Update LD_LIBRARY_PATH and PATH if we are using a SystemTap enabled Python runtime
if [ "$USE_SYSTEMTAP" -eq True ]; then
    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$PWD/systemtap/inst/lib
    export PATH=$PATH:$PWD/systemtap/inst/bin
fi

# Enter virtualenv in case there's one
if [ "$USE_SYSTEMTAP" -eq True -o "$USE_VENV" -eq True ]; then
    source venv/bin/activate
fi

# Run the actual command
exec $*

#
# run-in-env.sh ends here
