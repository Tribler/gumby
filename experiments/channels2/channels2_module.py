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
        self.session.lm.mds.ChannelMetadata.create_channel('test', 'test')

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

    @experiment_callback
    def write_channels(self):
        """
        Write information about all discovered channels away.
        """
        with db_session:
            with open('channels.txt', 'w') as output_file:
                output_file.write('public_key,title,num_torrents\n')
                chant_channels = list(self.session.lm.mds.ChannelMetadata.select())
                for chant_channel in chant_channels:
                    output_file.write("%s,%s,%d\n" % (
                        str(chant_channel.public_key).encode('hex'),
                        chant_channel.title,
                        len(chant_channel.contents_list)))

        with open('channel_download_times.txt', 'w') as output_file:
            for infohash, download_time in self.overlay.download_times.iteritems():
                output_file.write('%s,%f\n' % (infohash.encode('hex'), download_time))
