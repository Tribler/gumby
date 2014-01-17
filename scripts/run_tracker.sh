#!/bin/bash -e
# run_tracker.sh ---
#
# Filename: run_tracker.sh
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Fri Jun 14 12:44:06 2013 (+0200)

# Commentary:
#
# %*% Starts a dispersy tracker.
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

# @CONF_OPTION TRACKER_PORT: Set the port to be used by the tracker. (required)
# @CONF_OPTION TRACKER_CRYPTO: Set the type of crypto to be used by the tracker. (default is ECCrypto)

if [ -z "$TRACKER_PORT" ]; then
    echo "ERROR: you need to specify the TRACKER_PORT when using $0" >&2
    exit 1
fi
if [ -z "$TRACKER_CRYPTO" ]; then
    echo "TRACKER_CRYPTO not set, using ECCrypto"
    export TRACKER_CRYPTO="ECCrypto"
fi


cd $PROJECT_DIR

if [ -e tribler ]; then
    cd tribler
    MODULEPATH=Tribler.dispersy.tool.tracker
else
    MODULEPATH=dispersy.tool.tracker
fi

if [ -z "$HEAD_HOST" ]; then
    HEAD_HOST=$(hostname)
fi

echo $HEAD_HOST $TRACKER_PORT > bootstraptribler.txt
python -O -c "from $MODULEPATH import main; main()" --port $TRACKER_PORT --crypto $TRACKER_CRYPTO 2>&1 > "$OUTPUT_DIR/tracker_out.log"

#
# run_tracker.sh ends here
