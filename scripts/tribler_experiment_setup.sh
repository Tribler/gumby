#!/bin/bash -ex
# tribler_experiment_setup.sh ---
#
# Filename: tribler_experiment_setup.sh
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Mon Aug 12 17:56:58 2013 (+0200)
# Version:

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

if [ -e tribler/Tribler/SwiftEngine/ ]; then
    cd tribler
    buildswift.sh || echo "Swift failed to build!"
fi

das4_setup.sh

#
# tribler_experiment_setup.sh ends here
