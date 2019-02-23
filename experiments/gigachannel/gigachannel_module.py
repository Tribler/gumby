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

        with open('autoplot.txt', 'a') as output_file:
            output_file.write('known_channels.csv\n')
            output_file.write('downloading_channels.csv\n')
            output_file.write('completed_channels.csv\n')
            output_file.write('total_torrents.csv\n')
        os.mkdir('autoplot')
        with open('autoplot/known_channels.csv', 'w') as output_file:
            output_file.write('time,pid,num_channels\n')
        with open('autoplot/downloading_channels.csv', 'w') as output_file:
            output_file.write('time,pid,num_channels\n')
        with open('autoplot/completed_channels.csv', 'w') as output_file:
            output_file.write('time,pid,num_channels\n')
        with open('autoplot/total_torrents.csv', 'w') as output_file:
            output_file.write('time,pid,num_torrents\n')

    def on_ipv8_available(self, _):
        LoopingCall(self.write_channels).start(1.0, True)

    @experiment_callback
    def introduce_peers_gigachannels(self):
        for peer_id in self.all_vars.iterkeys():
            if int(peer_id) != self.my_id:
                self.overlay.walk_to(self.experiment.get_peer_ip_port_by_id(peer_id))

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
            with open('autoplot/total_torrents.csv', 'a') as output_file:
                chant_torrents = list(self.session.lm.mds.TorrentMetadata.select())
                output_file.write("%f,%d,%d\n" % (
                    time(),
                    self.my_id,
                    len(chant_torrents)))
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
