import random

from gumby.experiment import experiment_callback
from gumby.modules.community_experiment_module import IPv8OverlayExperimentModule
from gumby.modules.experiment_module import static_module

from Tribler.pyipv8.ipv8.peerdiscovery.deprecated.discovery import DiscoveryCommunity


@static_module
class DiscoveryModule(IPv8OverlayExperimentModule):
    """
    This module contains code to manage the discovery community in IPv8.
    """

    def __init__(self, experiment):
        super(DiscoveryModule, self).__init__(experiment, DiscoveryCommunity)

    def on_id_received(self):
        super(DiscoveryModule, self).on_id_received()
        self.tribler_config.set_ipv8_discovery(True)
        self.tribler_config.set_trustchain_enabled(False)

    def on_dispersy_available(self, dispersy):
        # Disable threadpool messages
        self.overlay._use_main_thread = True

    @experiment_callback
    def introduce_some_peers(self, num_peers):
        rand_peer_ids = random.sample(self.all_vars.keys(), int(num_peers))
        for rand_peer_id in rand_peer_ids:
            self._logger.info("Walking initially to peer %s", rand_peer_id)
            self.overlay.walk_to(self.experiment.get_peer_ip_port_by_id(rand_peer_id))
