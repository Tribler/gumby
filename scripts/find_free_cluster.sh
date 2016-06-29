#!/usr/bin/env bash
# find_free_cluster.sh ---
#
# Filename: find_free_cluster.sh
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Thu Jun  2 16:03:02 2016 (+0200)

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
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Emacs.  If not, see <http://www.gnu.org/licenses/>.
#
#

# Code:

set -e

CLUSTERS="fs0.das5.cs.vu.nl fs1.das5.liacs.nl fs2.das5.science.uva.nl fs3.das5.tudelft.nl fs4.das5.science.uva.nl fs5.das5.astron.nl"
USER=pouwelse

if [ -z "$1" ]; then
    echo "Usage: find_free_cluster.sh NODE_NUMBER"
    exit 1
fi

for CLUSTER in $CLUSTERS; do
    FREE_NODES=`ssh $USER@$CLUSTER sinfo | grep ^defq.*idle| awk '{print $4}'`

    echo "$CLUSTER has $FREE_NODES free nodes"
    if [ $FREE_NODES -ge $1 ]; then
        echo "$CLUSTER" > cluster.txt
        exit 0
    fi
done

echo "Could not find a cluster with enough nodes."
exit 2



#
# find_free_cluster.sh ends here
