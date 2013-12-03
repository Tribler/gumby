#!/usr/bin/env python
# run.py ---
#
# Filename: run.py
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Wed Jun  5 14:47:19 2013 (+0200)

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

import sys
from os.path import dirname, exists

from twisted.internet import reactor

from gumby.runner import ExperimentRunner
from gumby.log import ColoredFileLogObserver, msg

from os import setpgrp, kill, getpgid, getppid, getpid
from signal import signal, SIGTERM
from psutil import get_pid_list


def _termTrap(self, *argv):
    if not _terminating:
        print "Captured TERM signal"
        _killGroup()
        exit(-15)


def _killGroup():
    global _terminating
    _terminating = True
    mypid = getpid()
    for pid in get_pid_list():
        if getpgid(pid) == mypid and pid != mypid:
            kill(pid, SIGTERM)

_terminating = False

if __name__ == '__main__':
    sys.path.append(dirname(__file__))
    if len(sys.argv) == 2:
        # startLogging(sys.stdout)
        # startLogging(open("/tmp/cosa.log",'w'))
        observer = ColoredFileLogObserver()
        observer.start()
        conf_path = sys.argv[1]
        if not exists(conf_path):
            print "Error: The specified configuration file doesn't exist."
            exit(1)

        # Create a process group so we can clean up after ourselves when
        setpgrp()  # create new process group and become its leader
        # Catch SIGTERM to attempt to clean after ourselves
        signal(SIGTERM, _termTrap)

        exp_runner = ExperimentRunner(conf_path)
        exp_runner.run()
        reactor.run()

        # Kill all the subprocesses before exiting
        msg("Killing leftover local sub processes...")
        _killGroup()
        msg("Done.")
    else:
        print "Usage:\n%s EXPERIMENT_CONFIG" % sys.argv[0]

#
# run.py ends here
