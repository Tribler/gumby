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

from twisted.python.log import msg, FileLogObserver, textFromEventDict, _safeFormat
from twisted.python import util
from twisted.internet import reactor

from gumby.runner import ExperimentRunner
from os import setpgrp, kill, getpgid, getppid, getpid
from signal import signal, SIGTERM
from psutil import get_pid_list


class ColoredFileLogObserver(FileLogObserver):
    CANCEL_COLOR = "\x1b[0m"
    RED_NORMAL = "\x1b[31m"
    RED_BOLD = "\x1b[31;1m"
    GREEN_NORMAL = "\x1b[32m"
    GREEN_BOLD = "\x1b[32;1m"
    GREY_NORMAL = "\x1b[37m"

    def __init__(self, f=None):
        if f is None:
            FileLogObserver.__init__(self, sys.stdout)
        else:
            FileLogObserver.__init__(self, f)

    def _colorize(self, text, color=GREY_NORMAL):
        return color + text + ColoredFileLogObserver.CANCEL_COLOR

    def emit(self, eventDict):
        text = textFromEventDict(eventDict)
        if text is None:
            return

        timeStr = self._colorize(
            self.formatTime(eventDict['time']),
            ColoredFileLogObserver.GREY_NORMAL)
        fmtDict = {
            'system': eventDict['system'],
            'text': text.replace("\n", "\n\t")}
        systemStr = ""
        systemStr = self._colorize(
            _safeFormat("[%(system)s]", fmtDict),
            ColoredFileLogObserver.GREY_NORMAL)
        textStr = _safeFormat("%(text)s", fmtDict)

        if textStr.startswith("SSH"):
            t = textStr.find("STDERR:")
            if t != -1:
                textStr = self._colorize(
                    textStr[t + 8:],
                    ColoredFileLogObserver.RED_BOLD)
            else:
                textStr = self._colorize(
                    textStr[textStr.find("STDOUT:") + 8:],
                    ColoredFileLogObserver.GREEN_BOLD)
            # only text for incoming data
            msgStr = textStr + "\n"
        else:
            # add system to the local logs
            # TODO: Make system more useful, not just "SSHChannel...".
            msgStr = systemStr + " " + textStr + "\n"

        util.untilConcludes(self.write, timeStr + " " + msgStr)
        util.untilConcludes(self.flush)  # Hoorj!


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
