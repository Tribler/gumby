from gumby.experiment import experiment_callback
from gumby.modules.community_experiment_module import IPv8OverlayExperimentModule
from gumby.modules.experiment_module import static_module


from bami.basalt.community import BasaltCommunity


@static_module
class BasaltModule(IPv8OverlayExperimentModule):
    """
    This module contains code to manage experiments with the Basalt community.
    """

    def __init__(self, experiment):
        super().__init__(experiment, BasaltCommunity)
        self.samples = []

    def on_peer_sampled(self, peer):
        self.samples.append(peer)

    def on_id_received(self):
        super().on_id_received()
        self.tribler_config.basalt.enabled = True

    @experiment_callback
    def register_sample_callback(self):
        self.overlay.sample_callback = self.on_peer_sampled

    @experiment_callback
    def write_basalt_stats(self):
        # Write view
        self._logger.info("Writing view")
        with open("view.csv", "w") as out_file:
            for peer in self.overlay.view:
                out_file.write("%s\n" % peer)

        # Write samples
        self._logger.info("Writing %d samples", len(self.samples))
        with open("peer_samples.csv", "w") as out_file:
            for peer in self.samples:
                peer_id = int(peer.address[1]) - 12000
                out_file.write("%d\n" % peer_id)
