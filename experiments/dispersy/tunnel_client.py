#!/usr/bin/env python

from os import path
from sys import path as pythonpath

from twisted.internet.task import LoopingCall
from twisted.python.log import msg

from gumby.experiments.dispersyclient import DispersyExperimentScriptClient, main
from posix import environ


# TODO(emilon): Fix this crap
pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))


class TunnelClient(DispersyExperimentScriptClient):

    def __init__(self, *argv, **kwargs):
        from Tribler.community.tunnel.hidden_community import HiddenTunnelCommunity
        DispersyExperimentScriptClient.__init__(self, *argv, **kwargs)
        self.community_class = HiddenTunnelCommunity

    def init_community(self, become_exitnode=False):
        from Tribler.community.tunnel.tunnel_community import TunnelSettings
        tunnel_settings = TunnelSettings()
        tunnel_settings.max_circuits = 0
        tunnel_settings.socks_listen_ports = [23000 + (100 * (self.scenario_runner._peernumber)) + i for i in range(5)]
        tunnel_settings.do_test = False
        tunnel_settings.become_exitnode = True if become_exitnode else False

        self.set_community_kwarg('settings', tunnel_settings)

        self.monitor_circuits_lc = None
        self._prev_scenario_statistics = {}

    def registerCallbacks(self):
        self.scenario_runner.register(self.build_circuits, 'build_circuits')
        self.scenario_runner.register(self.init_community, 'init_community')

    def build_circuits(self):
        self._logger.info("build_circuits")
        self._community.settings.max_circuits = 8

    def online(self):
        DispersyExperimentScriptClient.online(self)
        if not self.monitor_circuits_lc:
            self.monitor_circuits_lc = lc = LoopingCall(self.monitor_circuits)
            lc.start(5.0, now=True)

    def offline(self):
        DispersyExperimentScriptClient.offline(self)
        if self.monitor_circuits_lc:
            self.monitor_circuits_lc.stop()
            self.monitor_circuits_lc = None

    def get_my_member(self):
        return self._dispersy.get_new_member(u"curve25519")

    def monitor_circuits(self):
        nr_circuits = len(self._community.active_data_circuits()) if self._community else 0
        self._prev_scenario_statistics = self.print_on_change("scenario-statistics",
                                                              self._prev_scenario_statistics,
                                                              {'nr_circuits': nr_circuits})

if __name__ == '__main__':
    TunnelClient.scenario_file = environ.get('SCENARIO_FILE', 'tunnel.scenario')
    main(TunnelClient)
