#!/usr/bin/env python2
# bartercast_client.py ---
#
# Filename: hidden_services_module.py
# Description:
# Author: Rob Ruigrok
# Maintainer:
# Created: Wed Apr 22 11:44:23 2015 (+0200)

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
from twisted.internet.task import LoopingCall

from Tribler.community.tunnel.tunnel_community import TunnelSettings
from Tribler.community.tunnel.crypto.tunnelcrypto import NoTunnelCrypto
from Tribler.community.tunnel.hidden_community import HiddenTunnelCommunity

from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import static_module
from gumby.modules.community_experiment_module import CommunityExperimentModule


@static_module
class HiddenServicesModule(CommunityExperimentModule):

    def __init__(self, experiment):
        super(HiddenServicesModule, self).__init__(experiment, HiddenTunnelCommunity)
        self.speed_download = {'download': 0}
        self.speed_upload = {'upload': 0}
        self.progress = {'progress': 0}
        self.test_file_size = 100 * 1024 * 1024
        self.monitor_circuits_lc = LoopingCall(self._monitor_circuits)
        self.prev_scenario_statistics = {}

    def on_id_received(self):
        super(HiddenServicesModule, self).on_id_received()
        self.tribler_config.set_tunnel_community_enabled(True)
        self.tribler_config.set_mainline_dht_enabled(True)
        self.tribler_config.set_libtorrent_enabled(True)
        self.tribler_config.set_tunnel_community_socks5_listen_ports([23000 + 100 * self.my_id + i for i in range(5)])
        self.tribler_config.set_tunnel_community_exitnode_enabled(False)
        self.community_launcher.community_kwargs["settings"] = TunnelSettings(self.tribler_config)

    def on_dispersy_available(self, _):
        super(HiddenServicesModule, self).on_dispersy_available(_)

        def monitor_downloads(dslist):
            self.community.monitor_downloads(dslist)
            return 1.0, []
        self.session.set_download_states_callback(monitor_downloads, False)

    # TunnelSettings should be obtained from tribler_config settings. But not all properties of the tunnel settings can
    # be controlled that way. So we store a custom TunnelSettings object in the community launcher. Properties that have
    # a regular config option should also be set in the config object so we're consistent as far as all other code is
    # concerned.
    @property
    def tunnel_settings(self):
        return self.community_launcher.community_kwargs["settings"]

    @experiment_callback
    def set_tunnel_exit(self, value):
        value = HiddenServicesModule.str2bool(value)
        self._logger.error("This peer will be exit node: %s" % ('Yes' if value else 'No'))
        self.tribler_config.set_tunnel_community_exitnode_enabled(value)
        self.tunnel_settings.become_exitnode = value

    @experiment_callback
    def set_tunnel_max_circuits(self, value):
        self.tunnel_settings.max_circuits = int(value)

    @experiment_callback
    def set_tunnel_max_traffic(self, value):
        self.tunnel_settings.max_traffic = long(value)

    @experiment_callback
    def set_tunnel_max_time(self, value):
        self.tunnel_settings.max_time = long(value)

    @experiment_callback
    def disable_tunnel_crypto(self):
        self._logger.error("Disable tunnel crypto")
        self.tunnel_settings.crypto = NoTunnelCrypto()

    @experiment_callback
    def build_circuits(self):
        self._logger.info("Start building circuits")
        self.community.settings.max_circuits = 8
        self.community.build_tunnels(3)

    @experiment_callback
    def start_circuit_monitor(self):
        self.monitor_circuits_lc.start(5.0, now=True)

    @experiment_callback
    def stop_circuit_monitor(self):
        self.monitor_circuits_lc.stop()

    def _monitor_circuits(self):
        self._logger.info("Monitoring circuits")
        nr_circuits = len(self.community.active_data_circuits()) if self.community else 0
        self.prev_scenario_statistics = self.print_dict_changes("scenario-statistics",
                                                                 self.prev_scenario_statistics,
                                                                 {'nr_circuits': nr_circuits})
