#!/usr/bin/env python3
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

import logging
import sys
from os import environ, getpgid, getpid, kill, setpgrp
from os.path import dirname, exists
from signal import SIGKILL, SIGTERM, signal
from time import sleep, time


logging.basicConfig(level=getattr(logging, environ.get('GUMBY_LOG_LEVEL', 'INFO').upper()))

# This conditional import is added to support older versions of psutil
try:
    from psutil import get_pid_list as pids
except ImportError:
    from psutil import pids

from twisted.internet import reactor

from gumby.runner import ExperimentRunner


def _termTrap(self, *argv):
    if not _terminating:
        print("Captured TERM signal")
        _killGroup()
        exit(-15)


def _killGroup(signal=SIGTERM):
    global _terminating
    _terminating = True
    mypid = getpid()
    pids_found = 0
    for pid in pids():
        try:
            if getpgid(pid) == mypid and pid != mypid:
                kill(pid, signal)
                pids_found += 1
        except OSError:
            # The process could already be dead by the time we do the getpgid()
            pass
    return pids_found

_terminating = False

if __name__ == '__main__':
    sys.path.append(dirname(__file__))
    if len(sys.argv) == 2:
        conf_path = sys.argv[1]
        if not exists(conf_path):
            print("Error: The specified configuration file doesn't exist.")
            exit(1)

        if not exists('/proc'):
            print("Error: procfs not available on this system.")
            exit(5)

        # Create a process group so we can clean up after ourselves when
        setpgrp()  # create new process group and become its leader
        # Catch SIGTERM to attempt to clean after ourselves
        signal(SIGTERM, _termTrap)

        exp_runner = ExperimentRunner(conf_path)
        exp_runner.run()

        reactor.exitCode = 0
        reactor.run()

        # Kill all the subprocesses before exiting
        logger = logging.getLogger()
        logger.info("Killing leftover local sub processes...")
        pids_found = _killGroup()
        wait_start_time = time()
        while pids_found and (time() - wait_start_time) < 30:
            pids_found = _killGroup()
            if pids_found:
                logger.info("Waiting for %d subprocess(es) to die...", pids_found)
            sleep(5)

        if (time() - wait_start_time) >= 30:
            logger.info("Time out waiting, sending SIGKILL to remaining processes.")
            _killGroup(SIGKILL)

        logger.info("Done.")

        exit(reactor.exitCode)
    else:
        print("Usage:\n%s EXPERIMENT_CONFIG" % sys.argv[0])

#
# run.py ends here
