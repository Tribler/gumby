#!/usr/bin/env python
# dummy_scenario_experiment_client.py ---
#
# Filename: dummy_scenario_experiment_client.py
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Wed Sep 18 17:29:33 2013 (+0200)

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


from os import environ, path
from sys import stdout, exit

from gumby.sync import ExperimentClient, ExperimentClientFactory
from gumby.scenario import ScenarioRunner

from twisted.internet import reactor
from twisted.python.log import msg, startLogging


class DummyExperimentScriptClient(ExperimentClient):

    def startExperiment(self):
        msg("Starting dummy scenario experiment")
        scenario_file_path = path.join(path.abspath(path.dirname(__file__)), "dummy.scenario")
        self.scenario_runner = ScenarioRunner(scenario_file_path, int(self.my_id))
        self.scenario_runner.register(self.dummy_action)
        self.scenario_runner.run()
        reactor.callLater(5, reactor.stop)

    def dummy_action(self, arg):
        msg("%s Dummy action got:" % self.my_id, arg)


def main():
    factory = ExperimentClientFactory({"random_key": "random value"}, DummyExperimentScriptClient)
    reactor.connectTCP(environ['HEAD_NODE'], int(environ['SYNC_PORT']), factory)

    reactor.exitCode = 0
    reactor.run()
    exit(reactor.exitCode)

if __name__ == '__main__':
    startLogging(stdout)
    main()



#
# dummy_scenario_experiment_client.py ends here
