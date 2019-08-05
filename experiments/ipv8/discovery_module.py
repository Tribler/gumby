from gumby.modules.community_experiment_module import IPv8OverlayExperimentModule
from gumby.modules.experiment_module import static_module

from ipv8.peerdiscovery.community import DiscoveryCommunity
from ipv8.attestation.trustchain.community import TrustChainCommunity

@static_module
class DiscoveryModule(IPv8OverlayExperimentModule):
    """
    This module contains code to manage the discovery community in IPv8.
    """

    def __init__(self, experiment):
        super(DiscoveryModule, self).__init__(experiment, TrustChainCommunity)

    def on_id_received(self):
        super(DiscoveryModule, self).on_id_received()
        self.tribler_config.set_ipv8_discovery(True)

    def on_ipv8_available(self, _):
        # Disable threadpool messages
        self.overlay._use_main_thread = True
