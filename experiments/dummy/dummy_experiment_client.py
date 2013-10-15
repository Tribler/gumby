#!/usr/bin/env python
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

from os import environ
from sys import stdout, exit

from gumby.sync import ExperimentClient, ExperimentClientFactory

from twisted.internet import reactor
from twisted.python.log import msg, startLogging

class DummyExperimentClient(ExperimentClient):
    def startExperiment(self):
        msg("Starting dummy experiment (IE exiting in a couple seconds)")
        reactor.callLater(2, reactor.stop)


def main():
    factory = ExperimentClientFactory({"random_key": "random value"}, DummyExperimentClient)
    reactor.connectTCP(environ['HEAD_NODE'], int(environ['SYNC_PORT']), factory)

    reactor.exitCode = 0
    reactor.run()
    exit(reactor.exitCode)

if __name__ == '__main__':
    startLogging(stdout)
    main()


#
# experiment_client.py ends here
