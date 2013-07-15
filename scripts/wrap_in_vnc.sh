#!/bin/bash -ex
# wrap_in_vnc.sh ---
#
# Filename: wrap_in_vnc.sh
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Thu Jul 11 13:42:37 2013 (+0200)

# Commentary:
# This script starts a new VNC server and executes the specified command.
# When the command finishes, it kills the vnc server before exiting.
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

export DISPLAY=:$RANDOM
export HOME=$(mktemp -d)
mkdir -p $HOME/.vnc

chmod -fR og-rwx $HOME

Xvnc $DISPLAY -localhost -SecurityTypes None &

$* || FAILURE=$?

kill %Xvnc

exit $FAILURE

#
# wrap_in_vnc.sh ends here
