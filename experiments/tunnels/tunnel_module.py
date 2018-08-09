#!/usr/bin/env python2
# bartercast_client.py ---
#
# Filename: tunnel_module.py
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
import time

from Tribler.Core.simpledefs import dlstatus_strings, DOWNLOAD, UPLOAD
from Tribler.community.triblertunnel.community import TriblerTunnelCommunity
from Tribler.pyipv8.ipv8.messaging.anonymization.community import TunnelSettings

from gumby.experiment import experiment_callback
from gumby.modules.community_experiment_module import IPv8OverlayExperimentModule
from gumby.modules.experiment_module import static_module


@static_module
class TunnelModule(IPv8OverlayExperimentModule):

    def __init__(self, experiment):
        super(TunnelModule, self).__init__(experiment, TriblerTunnelCommunity)
        self.download_states_history = []

    def on_id_received(self):
        super(TunnelModule, self).on_id_received()
        self.tribler_config.set_tunnel_community_enabled(True)
        self.tribler_config.set_mainline_dht_enabled(True)
        self.tribler_config.set_libtorrent_enabled(True)
        self.tribler_config.set_tunnel_community_socks5_listen_ports([23000 + 100 * self.my_id + i for i in range(5)])
        self.tribler_config.set_tunnel_community_exitnode_enabled(False)
        self.ipv8_community_launcher.community_kwargs["settings"] = TunnelSettings()

    def on_dispersy_available(self, _):
        super(TunnelModule, self).on_dispersy_available(_)

        def monitor_downloads(dslist):
            if isinstance(self.overlay, TriblerTunnelCommunity):
                self.overlay.monitor_downloads(dslist)

            for state in dslist:
                download = state.get_download()

                # Check the peers of this download every five seconds and add them to the payout manager when
                # this peer runs a Tribler instance
                if download.get_hops() == 0:
                    for peer in download.get_peerlist():
                        if 'Tribler' in peer["extended_version"]:
                            self.session.lm.payout_manager.update_peer(peer["id"].decode('hex'),
                                                                       download.get_def().get_infohash(),
                                                                       peer["dtotal"])

                status_dict = {
                    "time": time.time() - self.experiment.scenario_runner._expstartstamp,
                    "infohash": download.get_def().get_infohash().encode('hex'),
                    "progress": state.get_progress(),
                    "status": dlstatus_strings[state.get_status()],
                    "total_up": state.get_total_transferred(UPLOAD),
                    "total_down": state.get_total_transferred(DOWNLOAD),
                    "speed_up": state.get_current_speed(UPLOAD),
                    "speed_down": state.get_current_speed(DOWNLOAD),
                }
                self.download_states_history.append(status_dict)

            return []
        self.session.set_download_states_callback(monitor_downloads)

    # TunnelSettings should be obtained from tribler_config settings. But not all properties of the tunnel settings can
    # be controlled that way. So we store a custom TunnelSettings object in the community launcher. Properties that have
    # a regular config option should also be set in the config object so we're consistent as far as all other code is
    # concerned.
    @property
    def tunnel_settings(self):
        return self.ipv8_community_launcher.community_kwargs["settings"]

    @experiment_callback
    def set_tunnel_exit(self, value):
        value = TunnelModule.str2bool(value)
        self._logger.info("This peer will be exit node: %s" % ('Yes' if value else 'No'))
        self.tribler_config.set_tunnel_community_exitnode_enabled(value)
        self.tunnel_settings.become_exitnode = value

    @experiment_callback
    def set_tunnel_min_circuits(self, value):
        self.tunnel_settings.min_circuits = int(value)

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
    def set_tunnel_max_time_inactive(self, value):
        self.tunnel_settings.max_time_inactive = long(value)

    @experiment_callback
    def build_circuits(self, hops):
        self._logger.info("Start building circuits")
        self.overlay.build_tunnels(int(hops))

    @experiment_callback
    def write_tunnels_info(self):
        """
        Write information about established tunnels/introduction points/rendezvous points to files.
        """
        with open('circuits.txt', 'w', 0) as circuits_file:
            for circuit_id, circuit in self.overlay.circuits.iteritems():
                circuits_file.write('%s,%s,%s,%s,%s,%s,%s,%s:%d\n' % (circuit_id, str(circuit.state), circuit.goal_hops,
                                                                      circuit.bytes_up, circuit.bytes_down,
                                                                      circuit.creation_time, circuit.ctype,
                                                                      circuit.sock_addr[0], circuit.sock_addr[1]))

        with open('relays.txt', 'w', 0) as relays_file:
            for circuit_id_1, relay in self.overlay.relay_from_to.iteritems():
                relays_file.write('%s,%s,%s:%d,%s\n' % (circuit_id_1, relay.circuit_id, relay.sock_addr[0], relay.sock_addr[1], relay.bytes_up))

        with open('downloads_history.txt', 'w', 0) as downloads_file:
            for state_dict in self.download_states_history:
                downloads_file.write('%f,%s,%f,%s,%f,%f,%f,%f\n' % (state_dict['time'], state_dict['infohash'],
                                                                    state_dict['progress'], state_dict['status'],
                                                                    state_dict['total_up'], state_dict['total_down'],
                                                                    state_dict['speed_up'], state_dict['speed_down']))
