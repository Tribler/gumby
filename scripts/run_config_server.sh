#!/bin/bash -ex
# run_config_server.sh ---
#
# Filename: run_config_server.sh
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Tue Jun 18 15:18:03 2013 (+0200)

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

# TODO: Un-hardcode this
PEER_COUNT=1000
INITIAL_DELAY=120
SYNC_PORT=3500

config_server.py $PEER_COUNT $INITIAL_DELAY $SYNC_PORT

#
# run_config_server.sh ends here
