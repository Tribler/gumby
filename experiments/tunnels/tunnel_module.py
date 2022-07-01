import time
from binascii import unhexlify

from ipv8.messaging.anonymization.community import TunnelSettings
from ipv8.messaging.anonymization.tunnel import PEER_FLAG_EXIT_BT, PEER_FLAG_RELAY

from tribler.core.components.libtorrent.libtorrent_component import LibtorrentComponent
from tribler.core.components.payout.payout_component import PayoutComponent
from tribler.core.components.tunnel.community.tunnel_community import TriblerTunnelCommunity
from tribler.core.components.tunnel.settings import TunnelCommunitySettings
from tribler.core.components.tunnel.tunnel_component import TunnelsComponent
from tribler.core.utilities.simpledefs import DOWNLOAD, UPLOAD, dlstatus_strings
from tribler.core.utilities.unicode import hexlify

from gumby.experiment import experiment_callback
from gumby.modules.tribler_module import TriblerBasedModule


class TunnelModule(TriblerBasedModule):

    def __init__(self, experiment):
        super().__init__(experiment)
        self.download_states_history = []

        # TunnelSettings should be obtained from tribler_config settings. But not all properties of the tunnel settings
        # can be controlled that way. So we store a custom TunnelSettings object in the community launcher. Properties
        # that have a regular config option should also be set in the config object so we're consistent as far as all
        # other code is concerned.
        self.tunnel_settings = TunnelSettings()

    def on_id_received(self):
        super().on_id_received()
        tribler_config = self.tribler_module.tribler_config
        tribler_config.tunnel_community.enabled = True
        tribler_config.libtorrent.enabled = True
        tribler_config.tunnel_community.exitnode_enabled = False
        self.tunnel_settings.min_circuits = tribler_config.tunnel_community.min_circuits
        self.tunnel_settings.max_circuits = tribler_config.tunnel_community.max_circuits

    @property
    def community(self) -> TriblerTunnelCommunity:
        return self.get_component(TunnelsComponent).community

    def on_ipv8_available(self, ipv8):
        super().on_ipv8_available(ipv8)
        self.community.settings = self.tunnel_settings

        def monitor_downloads(dslist):
            self.community.monitor_downloads(dslist)

            for state in dslist:
                download = state.get_download()

                # Check the peers of this download every five seconds and add them to the payout manager when
                # this peer runs a Tribler instance
                if download.config.get_hops() == 0:
                    peer_aggregate = {}
                    for peer in download.get_peerlist():
                        if 'Tribler' in peer["extended_version"]:
                            pid = unhexlify(peer["id"])
                            infohash = download.get_def().get_infohash()
                            if pid not in peer_aggregate:
                                peer_aggregate[pid] = {}
                            if infohash not in peer_aggregate[pid]:
                                peer_aggregate[pid][infohash] = 0

                            peer_aggregate[pid][infohash] += peer["dtotal"]
                            self._logger.debug("Received peers %s (%s, %s) down total: %s, upload: %s, version %s ",
                                               peer["id"], peer["ip"], peer["port"], peer["dtotal"],
                                               peer["utotal"], peer["extended_version"])

                    payout_component = self.get_component(PayoutComponent, optional=True)
                    if payout_component:
                        payout_manager = payout_component.payout_manager
                        for pid, hashes in peer_aggregate.items():
                            for infohash, balance in hashes.items():
                                payout_manager.update_peer(pid, infohash, balance)

                status_dict = {
                    "time": time.time() - self.experiment.scenario_runner.exp_start_time,
                    "infohash": hexlify(download.get_def().get_infohash()),
                    "progress": state.get_progress(),
                    "status": dlstatus_strings[state.get_status()],
                    "total_up": state.get_total_transferred(UPLOAD),
                    "total_down": state.get_total_transferred(DOWNLOAD),
                    "speed_up": state.get_current_speed(UPLOAD),
                    "speed_down": state.get_current_speed(DOWNLOAD),
                }
                self.download_states_history.append(status_dict)

            return []

        download_manager = self.get_component(LibtorrentComponent).download_manager
        download_manager.set_download_states_callback(monitor_downloads)

    @property
    def tunnel_config(self) -> TunnelCommunitySettings:
        return self.tribler_module.tribler_config.tunnel_community

    @experiment_callback
    def set_tunnel_exit(self, value):
        value = TunnelModule.str2bool(value)
        self._logger.info("This peer will be exit node: %s" % ('Yes' if value else 'No'))

        self.tunnel_config.exitnode_enabled = value
        self.tunnel_settings.become_exitnode = value
        self.tunnel_settings.peer_flags = {PEER_FLAG_EXIT_BT} if value else {PEER_FLAG_RELAY}

    @experiment_callback
    def set_tunnel_min_circuits(self, value):
        self.tunnel_settings.min_circuits = int(value)

    @experiment_callback
    def set_tunnel_max_circuits(self, value):
        self.tunnel_settings.max_circuits = int(value)

    @experiment_callback
    def set_tunnel_max_traffic(self, value):
        self.tunnel_settings.max_traffic = int(value)

    @experiment_callback
    def set_tunnel_max_time(self, value):
        self.tunnel_settings.max_time = int(value)

    @experiment_callback
    def set_tunnel_max_time_inactive(self, value):
        self.tunnel_settings.max_time_inactive = int(value)

    @experiment_callback
    def build_circuits(self, hops):
        self._logger.info("Start building circuits")
        self.community.build_tunnels(int(hops))

    @experiment_callback
    def write_tunnels_info(self):
        """
        Write information about established tunnels/introduction points/rendezvous points to files.
        """
        with open('circuits.txt', 'w') as circuits_file:
            for circuit_id, circuit in self.community.circuits.items():
                circuits_file.write('%s,%s,%s,%s,%s,%s,%s,%s:%d\n' % (circuit_id, str(circuit.state), circuit.goal_hops,
                                                                      circuit.bytes_up, circuit.bytes_down,
                                                                      circuit.creation_time, circuit.ctype,
                                                                      circuit.peer.address[0], circuit.peer.address[1]))

        with open('relays.txt', 'w') as relays_file:
            for circuit_id_1, relay in self.community.relay_from_to.items():
                relays_file.write('%s,%s,%s:%d,%s\n' % (circuit_id_1, relay.circuit_id, relay.peer.address[0],
                                                        relay.peer.address[1], relay.bytes_up))

        with open('downloads_history.txt', 'w') as downloads_file:
            for state_dict in self.download_states_history:
                downloads_file.write('%f,%s,%f,%s,%f,%f,%f,%f\n' % (state_dict['time'], state_dict['infohash'],
                                                                    state_dict['progress'], state_dict['status'],
                                                                    state_dict['total_up'], state_dict['total_down'],
                                                                    state_dict['speed_up'], state_dict['speed_down']))
