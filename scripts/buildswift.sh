#!/bin/bash -ex
# buildswift.sh ---
#
# Filename: buildswift.sh
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Thu Nov 21 14:00:45 2013 (+0100)

# Commentary:
# %*% Build the Swift binary.
# %*% The script will look in tribler/Tribler/SwiftEngine/ and swift/
# %*% and build the first one it finds. If found in the first location (as in the usual Tribler checkout)
# %*% the resulting binary will be moved to the location Tribler expects to find it.
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


build () {
    # @CONF_OPTION DEBUG_SWIFT: Set to true if you want to enable Swift's debug output. (default is disabled)
    if [ "${DEBUG_SWIFT,,}" != "true" ]; then
    	#Disable debug output
        sed -i "s/DEBUG = True/DEBUG = False/" SConstruct
    fi

    scons -j$(grep processor /proc/cpuinfo | wc -l)

}

if [ "${BUILD_SWIFT,,}" == "true" ]; then
    if [ -d tribler/Tribler/SwiftEngine ]; then
        cd tribler/Tribler/SwiftEngine
        build
        mv swift ../..
    else
        if [ -d swift ]; then
            cd swift
            build
        fi
    fi
    git clean -fd ||:
fi


#
# buildswift.sh ends here
