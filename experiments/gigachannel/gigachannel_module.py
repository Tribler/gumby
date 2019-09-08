import os
from time import time

from pony.orm import db_session
from twisted.internet.task import LoopingCall

from Tribler.community.gigachannel.community import GigaChannelCommunity
from Tribler.Core.simpledefs import DLSTATUS_SEEDING

from gumby.experiment import experiment_callback
from gumby.modules.community_experiment_module import IPv8OverlayExperimentModule
from gumby.modules.experiment_module import static_module


@static_module
class GigaChannelModule(IPv8OverlayExperimentModule):
    """
    This module contains code to manage experiments with the channels2 community.
    """

    def __init__(self, experiment):
        super(GigaChannelModule, self).__init__(experiment, GigaChannelCommunity)

    def on_id_received(self):
        super(GigaChannelModule, self).on_id_received()
        self.tribler_config.set_chant_enabled(True)
        self.tribler_config.set_libtorrent_enabled(True)

        self.autoplot_create('known_channels', 'num_channels')
        self.autoplot_create('downloading_channels', 'num_channels')
        self.autoplot_create('completed_channels', 'num_channels')
        self.autoplot_create('total_torrents', 'num_torrents')

    def on_ipv8_available(self, _):
        LoopingCall(self.write_channels).start(1.0, True)

    @experiment_callback
    def introduce_peers_gigachannels(self):
        for peer_id in self.all_vars.keys():
            if int(peer_id) != self.my_id:
                self.overlay.walk_to(self.experiment.get_peer_ip_port_by_id(peer_id))

    def write_channels(self):
        """
        Write information about all discovered channels away.
        """
        with db_session:
            self.autoplot_add_point('known_channels', len(list(self.session.lm.mds.ChannelMetadata.select())))
            self.autoplot_add_point('total_torrents', len(list(self.session.lm.mds.TorrentMetadata.select())))
        self.autoplot_add_point('downloading_channels', len(self.session.lm.get_downloads()))
        self.autoplot_add_point('completed_channels',
                                len([c for c in self.session.lm.get_downloads()
                                     if c.get_state().get_status() == DLSTATUS_SEEDING]))
