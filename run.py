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
import os
from twisted.internet import reactor
from twisted.python.log import msg

from gumby.settings import loadConfig
from gumby.runner import ExperimentRunner
from gumby.log import GumbyPythonLoggingObserver, GumbyLogger

import logging
import logging.config
logging.setLoggerClass(GumbyLogger)
logging.config.fileConfig(
    os.path.join(os.path.dirname(__file__), "logger.conf")
)

if __name__ == '__main__':
    sys.path.append(os.path.dirname(__file__))
    if len(sys.argv) == 2:
        # startLogging(sys.stdout)
        # startLogging(open("/tmp/cosa.log",'w'))
        observer = GumbyPythonLoggingObserver()
        observer.start()

        config = loadConfig(sys.argv[1])
        exp_runner = ExperimentRunner(config)
        exp_runner.run()
        reactor.run()
        msg("Execution finished, have a nice day.")
    else:
        print "Usage:\n%s EXPERIMENT_CONFIG" % sys.argv[0]

#
# run.py ends here
