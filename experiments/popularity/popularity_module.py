import logging
import os
import random
from asyncio import Future
from binascii import hexlify, unhexlify

from ipv8.taskmanager import TaskManager

from pony.orm import count, db_session, desc

from tribler.core.components.libtorrent.libtorrent_component import LibtorrentComponent
from tribler.core.components.metadata_store.db.orm_bindings.channel_node import NEW
from tribler.core.components.popularity.community.popularity_community import PopularityCommunity
from tribler.core.components.popularity.popularity_component import PopularityComponent

from gumby.experiment import experiment_callback
from gumby.modules.tribler_module import TriblerBasedModule
from gumby.util import run_task


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
        future = Future()

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

        self.register_task("lookup_%s" % hexlify(infohash), future.set_result,
                           health_response, delay=random.randint(1, 7))
        return future


class PopularityModule(TriblerBasedModule):
    """
    This module contains code to manage experiments with the popularity community.
    """

    def __init__(self, experiment):
        super().__init__(experiment)
        self._logger = logging.getLogger(self.__class__.__name__)
        self.fake_dht_health_manager = None
        self.health_poll_lc = None

    def on_id_received(self):
        super(PopularityModule, self).on_id_received()
        tribler_config = self.tribler_module.tribler_config
        tribler_config.popularity_community.enabled = True
        tribler_config.torrent_checking.enabled = True

        self.autoplot_create('num_healths', 'Number of torrent healths')

    @property
    def community(self) -> PopularityCommunity:
        return self.get_component(PopularityComponent).community

    @experiment_callback
    def start_health_poll(self, interval):
        self.health_poll_lc = run_task(self.write_periodic_torrent_health_statistics, interval=int(interval))

    @experiment_callback
    def stop_health_poll(self):
        self.health_poll_lc.cancel()

    @experiment_callback
    def set_fake_dht_health_manager(self):
        download_manager = self.get_component(LibtorrentComponent).download_manager
        self.fake_dht_health_manager = FakeDHTHealthManager()
        download_manager.dht_health_manager = self.fake_dht_health_manager

    @experiment_callback
    def introduce_peers_popularity(self):
        for peer_id in self.all_vars.keys():
            if int(peer_id) != self.my_id:
                self.community.walk_to(self.experiment.get_peer_ip_port_by_id(peer_id))

    @experiment_callback
    def set_torrent_check_interval(self, interval):
        interval = int(interval)
        self._logger.info("Changing torrent check interval to %d seconds", interval)
        torrent_checker = self.community.torrent_checker
        torrent_checker.replace_task("torrent_check", torrent_checker.check_local_torrents, interval=interval)

    @experiment_callback
    def insert_torrents_from_file(self, filename):
        torrent_healths = {}
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with db_session:
            my_channel = self.community.mds.ChannelMetadata.get_my_channels().order_by(lambda c: desc(c.rowid)).first()
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
                        _ = self.community.mds.TorrentMetadata.from_dict(new_entry_dict)

                    # Update torrent health
                    torrent_healths[unhexlify(parts[1])] = (int(parts[2]), int(parts[3]))

            my_channel.commit_channel_torrent()

            if self.fake_dht_health_manager:
                self.fake_dht_health_manager.torrent_healths.update(torrent_healths)

    @experiment_callback
    def write_periodic_torrent_health_statistics(self):
        with db_session:
            torrent_healths = count(state for state in self.community.mds.TorrentState.select()
                                    if state.last_check != 0)
            self.autoplot_add_point('num_healths', torrent_healths)

    @experiment_callback
    def write_torrent_health_statistics(self):
        with open("healths.txt", "w") as healths_file:
            with db_session:
                torrent_healths = self.community.mds.TorrentState.select()[:]
                for torrent_health in torrent_healths:
                    healths_file.write("%s,%d,%d,%d\n" % (hexlify(torrent_health.infohash),
                                                          torrent_health.seeders,
                                                          torrent_health.leechers,
                                                          torrent_health.last_check))
