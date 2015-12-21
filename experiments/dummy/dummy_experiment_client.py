#!/usr/bin/env python2
# experiment_client.py ---
#
# Filename: experiment_client.py
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Mon Sep  9 11:20:41 2013 (+0200)

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
from os import environ
from sys import exit, stderr, stdout

from gumby.log import setupLogging
from gumby.sync import ExperimentClient, ExperimentClientFactory
from twisted.internet import reactor
from twisted.python.log import err, msg, startLogging

logger = logging.getLogger()

class DummyExperimentClient(ExperimentClient):

    def startExperiment(self):
        self._logger.info("Starting dummy experiment (exiting in a couple of seconds)")
        self._logger.info("in-experiment DEFAULT_LEVEL")
        err("in-experiment ERROR_LEVEL")
        reactor.callLater(2, reactor.stop)


def main():
    factory = ExperimentClientFactory({"random_key": "random value"}, DummyExperimentClient)
    logger.info("Connecting to: %s:%s", environ['SYNC_HOST'], int(environ['SYNC_PORT']))
    reactor.connectTCP(environ['SYNC_HOST'], int(environ['SYNC_PORT']), factory)

    reactor.exitCode = 0
    reactor.run()
    print >> stderr, "post-main STDERR"
    print >> stdout, "post-main STDOUT"
    exit(reactor.exitCode)

if __name__ == '__main__':
    print >> stderr, "pre-startLogging STDERR"
    print >> stdout, "pre-startLogging STDOUT"
    setupLogging()
    print >> stderr, "post-startLogging STDERR"
    print >> stdout, "post-startLogging STDOUT"
    main()


#
# experiment_client.py ends here
