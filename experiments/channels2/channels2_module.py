import os

from pony.orm import db_session
from Tribler.community.channel2.community import Channel2Community

from gumby.experiment import experiment_callback
from gumby.modules.community_experiment_module import IPv8OverlayExperimentModule
from gumby.modules.experiment_module import static_module


@static_module
class Channels2Module(IPv8OverlayExperimentModule):
    """
    This module contains code to manage experiments with the channels2 community.
    """

    def __init__(self, experiment):
        super(Channels2Module, self).__init__(experiment, Channel2Community)

    def on_id_received(self):
        super(Channels2Module, self).on_id_received()
        self.tribler_config.set_chant_enabled(True)
        self.tribler_config.set_libtorrent_enabled(True)

    @experiment_callback
    def create_channel(self):
        my_key = self.session.trustchain_keypair
        my_channel_id = my_key.pub().key_to_bin()

        with db_session:
            my_channel = self.session.lm.mds.ChannelMetadata(
                public_key=buffer(my_channel_id), title='test', tags='test', subscribed=True)
            torrent_path = os.path.join(self.session.lm.mds.channels_dir, my_channel.dir_name + ".torrent")
            old_infohash, new_infohash = my_channel.add_metadata_to_channel(
                my_key, self.session.lm.mds.channels_dir, [])
            self.session.lm.updated_my_channel(old_infohash, new_infohash, torrent_path)

    @experiment_callback
    def add_torrents_to_channel(self, amount):
        amount = int(amount)
        my_key = self.session.trustchain_keypair
        my_channel_id = my_key.pub().key_to_bin()

        with db_session:
            my_channel = self.session.lm.mds.ChannelMetadata.get_channel_with_id(my_channel_id)
            torrent_metadatas = []
            for ind in xrange(amount):
                random_infohash = '\x00' * 20  # TODO make random
                random_torrent_metadata = self.session.lm.mds.TorrentMetadata(public_key=buffer(my_channel_id),
                                                                              title='test ind %d' % ind, tags='test',
                                                                              size=1234,
                                                                              infohash=random_infohash)
                torrent_metadatas.append(random_torrent_metadata)

            torrent_path = os.path.join(self.session.lm.mds.channels_dir, my_channel.dir_name + ".torrent")
            old_infohash, new_infohash = my_channel.add_metadata_to_channel(
                my_key, self.session.lm.mds.channels_dir, torrent_metadatas)
            self.session.lm.updated_my_channel(old_infohash, new_infohash, torrent_path)
