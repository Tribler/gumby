#!/bin/bash -ex
# wrap_in_vnc.sh ---
#
# Filename: wrap_in_vnc.sh
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Thu Jul 11 13:42:37 2013 (+0200)

# Commentary:
# %*% This script starts a new VNC server and executes the command passed as an argument.
# %*% When the command finishes, it kills the vnc server before exiting.
#
# %*% apt-get install vnc4server  before running this.

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

export DISPLAY=:$RANDOM

# Looks like $TMPDIR doesn't exist in the DAS4
if [ ! -z "$TMPDIR" ]; then
    mkdir -p "$TMPDIR"
fi

export HOME=$(mktemp -d)

if [ ! -e $HOME ]; then
    echo "Something went wrong while creating the temporary execution dir, aborting."
    exit 3
fi

mkdir -p $HOME/.vnc # TODO: I think this is no longer needed

chmod -fR og-rwx $HOME/.vnc

if [ ! -z "$HOME_SEED_FILE" ]; then
    echo "Unpacking HOME seed file..."
    cd $HOME
    tar xaf $HOME_SEED_FILE
    cd -
    echo "Done"
else
    echo "HOME_SEED_FILE not set, using a clean fake home"
fi

Xvnc $DISPLAY -localhost -SecurityTypes None &

sleep 1

$* || FAILURE=$?

kill %Xvnc || (sleep 1 ; kill -9 %Xvnc) ||:

rm -fR $HOME

exit $FAILURE

#
# wrap_in_vnc.sh ends here
