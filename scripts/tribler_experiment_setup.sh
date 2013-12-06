#!/bin/bash -e
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
# %*% This setup script should be used for any experiment involving Tribler.
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


# @CONF_OPTION BUILD_SWIFT: Set to any value if your experiment needs swift. (default is disabled)
if [ ! -z "$BUILD_SWIFT" ]; then
    echo "build_swift set, building Swift."
    if [ -e tribler/Tribler/SwiftEngine/ ]; then
        buildswift.sh || ( echo "Swift failed to build!" ; exit 1 )
    else
        echo "Couldn't find Swift at tribler/Tribler/SwiftEngine, bailing out."
        exit 2
    fi
else
    echo "Not building Swift."
fi

if [ -z "$LOCAL_RUN" -o $(echo $USE_LOCAL_VENV | tr '[:upper:]' '[:lower:]') == 'true' ]; then
    build_virtualenv.sh
fi


#
# tribler_experiment_setup.sh ends here
