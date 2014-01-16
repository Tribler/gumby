#!/bin/bash -x
# das4_setup.sh ---
#
# Filename: das4_setup.sh
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Fri Jun 21 16:10:45 2013 (+0200)

# Commentary:
# %*% This script takes care of setting everything up to run a Dispersy/Tribler experiment on the DAS4.
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

# Check that we are actually running on one of the DAS4 head nodes
if [ ! -z $(hostname |grep ^fs[0-9]$) ]; then
    # Let SGE clean after us
    grep -q "^export SGE_KEEP_TMPFILES" ~/.bashrc || echo "export SGE_KEEP_TMPFILES=no" >> ~/.bashrc
fi

quota -q
if [ $? -ne 0 ]; then
    echo 'Quota exceeded!'
    echo "Aborting experiment."
    exit 1
fi

set -e

build_virtualenv.sh

find -iname *.py[oc] -delete

pycompile.py .


#
# das4_setup.sh ends here
