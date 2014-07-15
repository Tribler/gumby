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
from time import sleep, time

from twisted.internet import reactor

from gumby.runner import ExperimentRunner
from gumby.log import ColoredFileLogObserver, msg

from os import setpgrp, kill, getpgid, getppid, getpid
from signal import signal, SIGTERM, SIGKILL
from psutil import get_pid_list, Process, NoSuchProcess


def _termTrap(self, *argv):
    if not _terminating:
        print "Captured TERM signal"
        _killGroup()
        exit(-15)


def _killGroup(signal=SIGTERM):
    global _terminating
    _terminating = True
    mypid = getpid()
    pids_found = 0
    for pid in get_pid_list():
        try:
            # don't forget to close processes that have the current process as ppid
            p = Process(pid)
            ppid = p.ppid
            if (ppid == mypid or getpgid(pid) == mypid) and pid != mypid:
                kill(pid, signal)
                pids_found += 1
        except OSError:
            # The process could already be dead by the time we do the getpgid()
            pass
        except NoSuchProcess:
            # may be thrown by Process.ppid() if the process is already dead
            pass
    return pids_found

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

        reactor.exitCode = 0
        reactor.run()

        # Kill all the subprocesses before exiting
        msg("Killing leftover local sub processes...")
        pids_found = _killGroup()
        wait_start_time = time()
        while pids_found and (time() - wait_start_time) < 30:
            pids_found = _killGroup()
            if pids_found:
                msg("Waiting for %d subprocess(es) to die..." % pids_found)
            sleep(5)

        if (time() - wait_start_time) >= 30:
            msg("Time out waiting, sending SIGKILL to remaining processes.")
            _killGroup(SIGKILL)

        msg("Done.")

        exit(reactor.exitCode)
    else:
        print "Usage:\n%s EXPERIMENT_CONFIG" % sys.argv[0]

#
# run.py ends here
