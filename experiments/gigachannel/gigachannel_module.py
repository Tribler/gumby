from pony.orm import db_session

from tribler_core.components.gigachannel.gigachannel_component import GigaChannelComponent
from tribler_core.components.gigachannel.community.gigachannel_community import GigaChannelCommunity
from tribler_core.components.libtorrent.libtorrent_component import LibtorrentComponent
from tribler_core.components.metadata_store.metadata_store_component import MetadataStoreComponent
from tribler_core.utilities.simpledefs import DLSTATUS_SEEDING

from gumby.experiment import experiment_callback
from gumby.modules.tribler_module import TriblerBasedModule
from gumby.util import run_task


class GigaChannelModule(TriblerBasedModule):
    """
    This module contains code to manage experiments with the channels2 community.
    """

    def on_id_received(self):
        super(GigaChannelModule, self).on_id_received()
        tribler_config = self.tribler_module.tribler_config
        tribler_config.chant.enabled = True
        tribler_config.libtorrent.enabled = True

        self.autoplot_create('known_channels', 'num_channels')
        self.autoplot_create('downloading_channels', 'num_channels')
        self.autoplot_create('completed_channels', 'num_channels')
        self.autoplot_create('total_torrents', 'num_torrents')

    @property
    def community(self) -> GigaChannelCommunity:
        component = GigaChannelComponent.instance()
        if component is None:
            raise RuntimeError('GigaChannelComponent not found')
        return component.community

    def on_ipv8_available(self, ipv8):
        super().on_ipv8_available(ipv8)
        run_task(self.write_channels, interval=1, delay=0)

    @experiment_callback
    def introduce_peers_gigachannels(self):
        for peer_id in self.all_vars.keys():
            if int(peer_id) != self.my_id:
                self.community.walk_to(self.experiment.get_peer_ip_port_by_id(peer_id))

    def write_channels(self):
        """
        Write information about all discovered channels away.
        """
        mds_component = MetadataStoreComponent.instance()
        if not mds_component:
            return

        mds = mds_component.mds
        download_manager = LibtorrentComponent.instance().download_manager
        with db_session:
            self.autoplot_add_point('known_channels', len(list(mds.ChannelMetadata.select())))
            self.autoplot_add_point('total_torrents', len(list(mds.TorrentMetadata.select())))
        self.autoplot_add_point('downloading_channels', len(download_manager.get_downloads()))
        self.autoplot_add_point('completed_channels',
                                len([c for c in download_manager.get_downloads()
                                     if c.get_state().get_status() == DLSTATUS_SEEDING]))
