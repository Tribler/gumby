#!/usr/bin/env python2

from twisted.internet.task import LoopingCall

from Tribler.community.tunnel.hidden_community import HiddenTunnelCommunity
from Tribler.community.tunnel.tunnel_community import TunnelSettings
from gumby.sync import experiment_callback
from gumby.modules.community_experiment_module import CommunityExperimentModule


class TunnelModule(CommunityExperimentModule):

    def __init__(self, experiment):
        super(TunnelModule, self).__init__(experiment, HiddenTunnelCommunity)

        self.session_config.set_tunnel_community_socks5_listen_ports(
            [23000 + 100 * self.my_id + i for i in range(5)])
        self.session_config.set_tunnel_community_exitnode_enabled(False)

        self.community_launcher.community_kwargs["settings"] = TunnelSettings(self.session_config)
        self.community_launcher.community_kwargs["settings"].max_circuits = 0

        self.monitor_circuits_lc = LoopingCall(self._monitor_circuits)
        self._prev_scenario_statistics = {}

    @experiment_callback
    def tunnel_should_become_exit(self, value):
        self.session_config.set_tunnel_community_exitnode_enabled(TunnelModule.str2bool(value))

    @experiment_callback
    def tunnel_build_circuits(self):
        self._logger.info("build_circuits")
        self.community.settings.max_circuits = 8

    @experiment_callback
    def tunnel_start_circuit_monitor(self):
        self.monitor_circuits_lc.start(5.0, now=True)

    @experiment_callback
    def tunnel_stop_circuit_monitor(self):
        self.monitor_circuits_lc.stop()

    def _monitor_circuits(self):
        nr_circuits = len(self.community.active_data_circuits()) if self.community else 0
        self._prev_scenario_statistics = self.print_on_change("scenario-statistics",
                                                              self._prev_scenario_statistics,
                                                              {'nr_circuits': nr_circuits})
