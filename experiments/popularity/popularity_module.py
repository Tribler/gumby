import logging
import os
import random
from binascii import hexlify, unhexlify

from Tribler.community.popularity.community import PopularityCommunity
from Tribler.Core.Modules.MetadataStore.OrmBindings.channel_node import NEW
from ipv8.taskmanager import TaskManager
from pony.orm import db_session, count
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.task import LoopingCall

from gumby.experiment import experiment_callback
from gumby.modules.community_experiment_module import IPv8OverlayExperimentModule
from gumby.modules.experiment_module import static_module


class FakeDHTHealthManager(TaskManager):
    """
    This is a fake DHT health manager which gets its file information from a local source.
    """

    def __init__(self):
        TaskManager.__init__(self)
        self._logger = logging.getLogger(self.__class__.__name__)
        self.torrent_healths = {}  # Dictionary from infohash -> (seeders, leechers)

    def get_health(self, infohash, **_):
        self._logger.info("Getting health info for infohash %s", hexlify(infohash))
        deferred = Deferred()

        seeders, peers = 0, 0
        if infohash in self.torrent_healths:
            seeders, peers = self.torrent_healths[infohash]

        health_response = {
            "DHT": [{
                "infohash": hexlify(infohash),
                "seeders": seeders,
                "leechers": peers
            }]
        }

        self.register_task("lookup_%s" % hexlify(infohash),
                           reactor.callLater(random.randint(1, 7), deferred.callback, health_response))
        return deferred


@static_module
class PopularityModule(IPv8OverlayExperimentModule):
    """
    This module contains code to manage experiments with the popularity community.
    """

    def __init__(self, experiment):
        super(PopularityModule, self).__init__(experiment, PopularityCommunity)
        self._logger = logging.getLogger(self.__class__.__name__)
        self.fake_dht_health_manager = None
        self.health_poll_lc = LoopingCall(self.write_periodic_torrent_health_statistics)

    def on_id_received(self):
        super(PopularityModule, self).on_id_received()
        self.tribler_config.set_popularity_community_enabled(True)
        self.tribler_config.set_torrent_checking_enabled(True)

        self.autoplot_create('num_healths', 'Number of torrent healths')

    @experiment_callback
    def start_health_poll(self, interval):
        self.health_poll_lc.start(int(interval))

    @experiment_callback
    def stop_health_poll(self):
        self.health_poll_lc.stop()

    @experiment_callback
    def set_fake_dht_health_manager(self):
        self.fake_dht_health_manager = FakeDHTHealthManager()
        self.session.lm.ltmgr.dht_health_manager = self.fake_dht_health_manager

    @experiment_callback
    def introduce_peers_popularity(self):
        for peer_id in self.all_vars.iterkeys():
            if int(peer_id) != self.my_id:
                self.overlay.walk_to(self.experiment.get_peer_ip_port_by_id(peer_id))

    @experiment_callback
    def set_torrent_check_interval(self, interval):
        interval = int(interval)
        self._logger.info("Changing torrent check interval to %d seconds", interval)
        torrent_checker = self.overlay.torrent_checker
        torrent_checker.cancel_pending_task("torrent_check")
        torrent_checker.torrent_check_lc = torrent_checker.register_task(
            "torrent_check", LoopingCall(torrent_checker.check_random_torrent))
        torrent_checker.torrent_check_lc.start(interval)

    @experiment_callback
    def insert_torrents_from_file(self, filename):
        torrent_healths = {}
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with db_session:
            my_channel = self.overlay.metadata_store.ChannelMetadata.get_my_channel()
            with open(os.path.join(dir_path, filename)) as torrents_file:
                for line in torrents_file.readlines():
                    line = line.rstrip()
                    parts = line.split(",")
                    if len(parts) != 4:
                        continue

                    if int(parts[0]) == self.my_id:
                        # Add the torrent to you channel
                        new_entry_dict = {
                            "infohash": unhexlify(parts[1]),
                            "title": parts[1],
                            "size": 1024,
                            "status": NEW
                        }
                        _ = self.overlay.metadata_store.TorrentMetadata.from_dict(new_entry_dict)

                    # Update torrent health
                    torrent_healths[unhexlify(parts[1])] = (int(parts[2]), int(parts[3]))

            my_channel.commit_channel_torrent()

            if self.fake_dht_health_manager:
                self.fake_dht_health_manager.torrent_healths.update(torrent_healths)

    @experiment_callback
    def write_periodic_torrent_health_statistics(self):
        with db_session:
            torrent_healths = count(state for state in self.overlay.metadata_store.TorrentState.select()
                                    if state.last_check != 0)
            self.autoplot_add_point('num_healths', torrent_healths)

    @experiment_callback
    def write_torrent_health_statistics(self):
        with open("healths.txt", "w") as healths_file:
            with db_session:
                torrent_healths = self.overlay.metadata_store.TorrentState.select()[:]
                for torrent_health in torrent_healths:
                    healths_file.write("%s,%d,%d,%d\n" % (hexlify(torrent_health.infohash),
                                                          torrent_health.seeders,
                                                          torrent_health.leechers,
                                                          torrent_health.last_check))
