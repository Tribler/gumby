#!/bin/bash
# das4_reserve_and_run.sh ---
#
# Filename: das4_reserve_and_run.sh
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Tue Aug 27 19:27:30 2013 (+0200)

# Commentary:
#
# A simple script to run an experiment on the DAS4 trough prun.
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

let MINUTES=60*$DAS4_RESERVE_DURATION
echo "Reserving $DAS4_NODE_AMOUNT nodes for $MINUTES  minutes."
echo "And spawning $DAS4_NODE_AMOUNT processes on each with command: $DAS4_NODE_COMMAND"
prun  -t $MINUTES -v -np $DAS4_NODE_AMOUNT -"$DAS4_PROCESSES_PER_NODE" $DAS4_NODE_COMMAND

#
# das4_reserve_and_run.sh ends here
