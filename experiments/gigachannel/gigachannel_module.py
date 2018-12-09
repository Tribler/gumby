import os
from time import time

from pony.orm import db_session
from six.moves import xrange
from twisted.internet.task import LoopingCall

from Tribler.community.gigachannel.community import GigaChannelCommunity
from Tribler.community.gigachannel.sync_strategy import SyncChannels
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
        self.strategies['SyncChannels'] = SyncChannels

    def on_id_received(self):
        super(GigaChannelModule, self).on_id_received()
        self.tribler_config.set_chant_enabled(True)
        self.tribler_config.set_libtorrent_enabled(True)

        with open('autoplot.txt', 'a') as output_file:
            output_file.write('known_channels.csv\n')
            output_file.write('downloading_channels.csv\n')
            output_file.write('completed_channels.csv\n')
        os.mkdir('autoplot')
        with open('autoplot/known_channels.csv', 'w') as output_file:
            output_file.write('time,pid,num_channels\n')
        with open('autoplot/downloading_channels.csv', 'w') as output_file:
            output_file.write('time,pid,num_channels\n')
        with open('autoplot/completed_channels.csv', 'w') as output_file:
            output_file.write('time,pid,num_channels\n')

    def on_dispersy_available(self, dispersy):
        super(GigaChannelModule, self).on_dispersy_available(dispersy)
        LoopingCall(self.write_channels).start(1.0, True)

    @experiment_callback
    def add_walking_custom_strategy(self, name, max_peers, **kwargs):
        super(GigaChannelModule, self).add_walking_strategy(name, max_peers, **kwargs)

    @experiment_callback
    def create_channel(self):
        self.session.lm.mds.ChannelMetadata.create_channel('test' + ''.join(str(i) for i in range(100)), 'test')

    @experiment_callback
    def add_torrents_to_channel(self, amount):
        amount = int(amount)
        my_key = self.session.trustchain_keypair
        my_channel_id = my_key.pub().key_to_bin()

        with db_session:
            my_channel = self.session.lm.mds.ChannelMetadata.get_channel_with_id(my_channel_id)
            for ind in xrange(amount):
                random_infohash = '\x00' * 20  # TODO make random
                self.session.lm.mds.TorrentMetadata(title='test ind %d' % ind, tags='test',
                                                    size=1234, infohash=random_infohash)

            my_channel.commit_channel_torrent()
            torrent_path = os.path.join(self.session.lm.mds.channels_dir, my_channel.dir_name + ".torrent")
            self.session.lm.updated_my_channel(torrent_path)

    def write_channels(self):
        """
        Write information about all discovered channels away.
        """
        with db_session:
            with open('autoplot/known_channels.csv', 'a') as output_file:
                chant_channels = list(self.session.lm.mds.ChannelMetadata.select())
                output_file.write("%f,%d,%d\n" % (
                    time(),
                    self.my_id,
                    len(chant_channels)))
        with open('autoplot/downloading_channels.csv', 'a') as output_file:
            channel_downloads = [c for c in self.session.lm.get_downloads() if c.get_channel_download()]
            output_file.write("%f,%d,%d\n" % (
                time(),
                self.my_id,
                len(channel_downloads)))
        with open('autoplot/completed_channels.csv', 'a') as output_file:
            channel_downloads = [c for c in self.session.lm.get_downloads() if c.get_channel_download() and
                                 c.get_state().get_status() == DLSTATUS_SEEDING]
            output_file.write("%f,%d,%d\n" % (
                time(),
                self.my_id,
                len(channel_downloads)))
