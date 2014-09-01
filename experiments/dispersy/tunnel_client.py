#!/usr/bin/env python

import sys
from os import path, environ
from time import time
from random import sample, randint
from sys import path as pythonpath
from hashlib import sha1

from gumby.experiments.dispersyclient import DispersyExperimentScriptClient, main, buffer_online

from twisted.python.log import msg
from twisted.python.threadable import isInIOThread
from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.internet.threads import deferToThread

# TODO(emilon): Fix this crap
pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))

class TunnelClient(DispersyExperimentScriptClient):

    def __init__(self, *argv, **kwargs):
        from Tribler.community.tunnel.community import TunnelCommunity, TunnelSettings
        DispersyExperimentScriptClient.__init__(self, *argv, **kwargs)
        self.community_class = TunnelCommunity

        tunnel_settings = TunnelSettings()
        tunnel_settings.max_circuits = 0
        self.set_community_kwarg('settings', tunnel_settings)

        self.monitor_circuits_lc = None
        self._prev_scenario_statistics = {}

    def registerCallbacks(self):
        self.scenario_runner.register(self.build_circuits, 'build_circuits')

    def build_circuits(self):
        self._community.settings.max_circuits = 8

    def online(self):
        DispersyExperimentScriptClient.online(self)
        if not self.monitor_circuits_lc:
            self.monitor_circuits_lc = lc = LoopingCall(self.monitor_circuits)
            lc.start(5.0, now=True)

    def monitor_circuits(self):
        nr_circuits = len(self._community.circuits) if self._community else 0
        self._prev_scenario_statistics = self.print_on_change("scenario-statistics", self._prev_scenario_statistics, {'nr_circuits': nr_circuits})

if __name__ == '__main__':
    TunnelClient.scenario_file = environ.get('SCENARIO_FILE', 'tunnel.scenario')
    main(TunnelClient)

