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

Xvnc $DISPLAY -localhost -SecurityTypes None &

sleep 1

wrap_in_temp_home.sh $* || FAILURE=$?

kill %Xvnc || (sleep 1 ; kill -9 %Xvnc) ||:

exit $FAILURE

#
# wrap_in_vnc.sh ends here
