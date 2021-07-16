from ipv8.peerdiscovery.community import DiscoveryCommunity

from gumby.modules.community_experiment_module import IPv8OverlayExperimentModule
from gumby.modules.experiment_module import static_module


@static_module
class DiscoveryModule(IPv8OverlayExperimentModule):
    """
    This module contains code to manage the discovery community in IPv8.
    """

    def __init__(self, experiment):
        super(DiscoveryModule, self).__init__(experiment, DiscoveryCommunity)

    def on_id_received(self):
        super(DiscoveryModule, self).on_id_received()
        self.tribler_config.ipv8.discovery.enabled = True
