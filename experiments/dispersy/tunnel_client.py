#!/usr/bin/env python

from os import path, getpid
from random import choice
from string import letters
from sys import path as pythonpath
from time import time

from threading import Event

from twisted.internet.task import LoopingCall
from twisted.python.log import msg

from gumby.experiments.dispersyclient import DispersyExperimentScriptClient, main


# TODO(emilon): Fix this crap
pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))


class TunnelClient(DispersyExperimentScriptClient):

    def __init__(self, *argv, **kwargs):
        from Tribler.community.tunnel.community import TunnelCommunity, TunnelSettings
        DispersyExperimentScriptClient.__init__(self, *argv, **kwargs)
        self.community_class = TunnelCommunity

        tunnel_settings = TunnelSettings()
        tunnel_settings.max_circuits = 8
        tunnel_settings.socks_listen_port = -1
        self.set_community_kwarg('settings', tunnel_settings)

        self.monitor_circuits_lc = None
        self._prev_scenario_statistics = {}

    def registerCallbacks(self):
        self.scenario_runner.register(self.build_circuits, 'build_circuits')

    def start_dispersy(self, autoload_discovery=True):
        msg("Starting dispersy")
        # We need to import the stuff _AFTER_ configuring the logging stuff.
        from Tribler.dispersy.dispersy import Dispersy
        from Tribler.community.tunnel.endpoint import TunnelStandaloneEndpoint
        from Tribler.dispersy.util import unhandled_error_observer

        self._dispersy = Dispersy(TunnelStandaloneEndpoint(int(self.my_id) + 12000, '0.0.0.0'), u'.', self._database_file, self._crypto)
        self._dispersy.statistics.enable_debug_statistics(True)

        self.original_on_incoming_packets = self._dispersy.on_incoming_packets

        if self._strict:
            from twisted.python.log import addObserver
            addObserver(unhandled_error_observer)

        self._dispersy.start(autoload_discovery=autoload_discovery)

        if self.master_private_key:
            self._master_member = self._dispersy.get_member(private_key=self.master_private_key)
        else:
            self._master_member = self._dispersy.get_member(public_key=self.master_key)
        self._my_member = self._dispersy.get_member(private_key=self.my_member_private_key)
        assert self._master_member
        assert self._my_member

        self._do_log()

        self.print_on_change('community-kwargs', {}, self.community_kwargs)
        self.print_on_change('community-env', {}, {'pid':getpid()})

        msg("Finished starting dispersy")

    def build_circuits(self):
        msg("build_circuits")
        self._community.settings.max_circuits = 8

    def online(self):
        DispersyExperimentScriptClient.online(self)
        if not self.monitor_circuits_lc:
            self.monitor_circuits_lc = lc = LoopingCall(self.monitor_circuits)
            lc.start(5.0, now=True)

    def offline(self):
        DispersyExperimentScriptClient.offline(self)

    def monitor_circuits(self):
        nr_circuits = len(self._community.circuits) if self._community else 0
        self._prev_scenario_statistics = self.print_on_change("scenario-statistics", self._prev_scenario_statistics, {'nr_circuits': nr_circuits})


if __name__ == '__main__':
    TunnelClient.scenario_file = 'tunnel.scenario'
    main(TunnelClient)
