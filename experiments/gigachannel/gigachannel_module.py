from pony.orm import db_session

from tribler_common.simpledefs import DLSTATUS_SEEDING
from tribler_core.modules.metadata_store.community.gigachannel_community import GigaChannelCommunity

from gumby.experiment import experiment_callback
from gumby.modules.community_experiment_module import IPv8OverlayExperimentModule
from gumby.modules.experiment_module import static_module
from gumby.util import run_task


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
        run_task(self.write_channels, interval=1, delay=0)

    @experiment_callback
    def introduce_peers_gigachannels(self):
        for peer_id in self.all_vars.keys():
            if int(peer_id) != self.my_id:
                self.overlay.walk_to(self.experiment.get_peer_ip_port_by_id(peer_id))

    def write_channels(self):
        """
        Write information about all discovered channels away.
        """
        if not self.session.mds:
            return

        with db_session:
            self.autoplot_add_point('known_channels', len(list(self.session.mds.ChannelMetadata.select())))
            self.autoplot_add_point('total_torrents', len(list(self.session.mds.TorrentMetadata.select())))
        self.autoplot_add_point('downloading_channels', len(self.session.ltmgr.get_downloads()))
        self.autoplot_add_point('completed_channels',
                                len([c for c in self.session.ltmgr.get_downloads()
                                     if c.get_state().get_status() == DLSTATUS_SEEDING]))
