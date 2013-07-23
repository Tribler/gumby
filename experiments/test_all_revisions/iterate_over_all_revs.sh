#!/bin/bash
# parallel_runner.sh ---
#
# Filename: parallel_runner.sh
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Thu Jul 11 14:51:05 2013 (+0200)
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

set -ex

rm -f /tmp/results.log

# if [ ! -d tribler ]; then
#     svn co http://svn.tribler.org/abc/branches/release-5.5.x tribler
#     #rm -R tribler/Tribler/dispersy
#     rm -R tribler/Tribler/Core/dispersy
# fi

# cd tribler/Tribler/Core

# if [ ! -d dispersy ]; then
#     git clone https://github.com/Tribler/dispersy.git
# fi

# cd dispersy

# git checkout devel

if [ ! -d tribler ]; then
    git clone https://github.com/Tribler/tribler.git --recursive
fi

cd tribler
git clean -fd
git checkout devel

export PYTHONPATH=.
export TESTNAME="Whatever"
mkdir -p ../output
export OUTPUTDIR=$(readlink -f "../output/")
CONFFILE=$(readlink -f "test.conf")

COUNT=0
for REV in $(git log --quiet --reverse 4dd183ee07..HEAD | grep ^"commit " | cut -f2 -d" "); do
    let COUNT=1+$COUNT
    ITERATION=1
    git checkout $REV
    git submodule sync
    git submodule update
    cd Tribler
    #set +e
    export REVISION=$REV
    #sed -i 's/assert message.distribution.global_time/#&/' Tribler/Core/dispersy/dispersy.py
    rm -fR sqlite
    ls -l dispersy
    rgrep "update_revision_information(" dispersy ||:

    #python -O Tribler/Main/dispersy.py --script dispersy-batch || exit
    run_stap_probe.sh "python -c 'from dispersy.tool.main import main; main()' --script dispersy.script.DispersySyncScript" $OUTPUTDIR/${TESTNAME}_${COUNT}_${REVISION}_${ITERATION}.csv ||:
    #python -O Tribler/dispersy/tool/main.py --script dispersy-crypto
    echo $? $REV >> /tmp/results.log
    #git checkout -- dispersy.py
    set -e
    cd ..
    #find -iname "*tdebug.py*" -exec sleep 10000 \;
    git clean -fd
done


#
# parallel_runner.sh ends here
