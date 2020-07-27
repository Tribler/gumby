import json
import time
from asyncio import Future
from binascii import hexlify
from os import environ, makedirs, symlink, path, getpid
from socket import gethostbyname

from gumby.experiment import experiment_callback
from gumby.gumby_tribler_config import GumbyTriblerConfig
from gumby.modules.experiment_module import ExperimentModule
from gumby.modules.community_launcher import *
from gumby.modules.gumby_session import GumbySession
from gumby.modules.isolated_community_loader import IsolatedIPv8CommunityLoader
from gumby.util import run_task


class BaseIPv8Module(ExperimentModule):
    def __init__(self, experiment):
        if BaseIPv8Module.get_ipv8_provider(experiment) is not None:
            raise Exception("Unable to load multiple IPv8 providers in a single experiment")

        super(BaseIPv8Module, self).__init__(experiment)
        self.has_ipv8 = True
        self.session = None
        self.tribler_config = None
        self.ipv8_port = None
        self.session_id = environ['SYNC_HOST'] + environ['SYNC_PORT']
        self.custom_ipv8_community_loader = self.create_ipv8_community_loader()
        self.ipv8_available = Future()

    def write_ipv8_statistics(self):
        if not self.session.ipv8:
            return

        statistics = self.session.ipv8.endpoint.statistics

        # Cleanup this dictionary
        time_elapsed = time.time() - self.experiment.scenario_runner.exp_start_time
        new_dict = {"time": time_elapsed, "stats": {}}
        for overlay_prefix, messages_dict in statistics.items():
            hex_prefix = hexlify(overlay_prefix).decode('utf-8')
            new_dict["stats"][hex_prefix] = {}
            for msg_id, msg_stats in messages_dict.items():
                new_dict["stats"][hex_prefix][msg_id] = msg_stats.to_dict()

        with open('ipv8_statistics.txt', 'a') as statistics_file:
            statistics_file.write(json.dumps(new_dict) + '\n')

    def on_id_received(self):
        super(BaseIPv8Module, self).on_id_received()
        self.tribler_config = self.setup_config()

    def create_ipv8_community_loader(self):
        loader = IsolatedIPv8CommunityLoader(self.session_id)
        loader.set_launcher(IPv8DiscoveryCommunityLauncher())
        loader.set_launcher(TrustChainCommunityLauncher())
        loader.set_launcher(TriblerTunnelCommunityLauncher())
        loader.set_launcher(PopularityCommunityLauncher())
        loader.set_launcher(DHTCommunityLauncher())
        loader.set_launcher(GigaChannelCommunityLauncher())
        return loader

    @experiment_callback
    def start_session(self):
        self.session = GumbySession(config=self.tribler_config)
        self.tribler_config = None

    @experiment_callback
    def enable_ipv8_statistics(self):
        self.tribler_config.set_ipv8_statistics(True)

    @experiment_callback
    def start_ipv8_statistics_monitor(self):
        run_task(self.write_ipv8_statistics, interval=1)

    @experiment_callback
    def set_ipv8_port(self, port):
        self.ipv8_port = int(port)

    @experiment_callback
    def isolate_ipv8_overlay(self, name):
        self.custom_ipv8_community_loader.isolate(name)

    def setup_config(self):
        if self.ipv8_port is None:
            self.ipv8_port = 12000 + self.experiment.my_id
        self._logger.info("IPv8 port set to %d", self.ipv8_port)

        # We manually update the IPv8 bootstrap servers since IPv8 does not use the bootstraptribler.txt file.
        from ipv8 import community
        community._DEFAULT_ADDRESSES = []
        community._DNS_ADDRESSES = []
        head_host = gethostbyname(environ['HEAD_HOST']) if 'HEAD_HOST' in environ else "127.0.0.1"

        my_state_path = path.abspath(path.join(environ["OUTPUT_DIR"], ".%s-%d-%d" % (self.__class__.__name__,
                                                                                     getpid(), self.my_id)))
        makedirs(my_state_path)
        bootstrap_file = path.join(environ['OUTPUT_DIR'], 'bootstraptribler.txt')
        if path.exists(bootstrap_file):
            symlink(bootstrap_file, path.join(my_state_path, 'bootstraptribler.txt'))

            with open(bootstrap_file, 'r') as bfile:
                for line in bfile.readlines():
                    parts = line.split(" ")
                    if not parts:
                        continue
                    community._DNS_ADDRESSES.append((parts[0], int(parts[1])))

        base_tracker_port = int(environ['TRACKER_PORT'])
        port_range = range(base_tracker_port, base_tracker_port + 4)
        with open(path.join(my_state_path, 'bootstraptribler.txt'), "w+") as f:
            f.write("\n".join(["%s %d" % (head_host, port) for port in port_range]))
        community._DEFAULT_ADDRESSES = [(head_host, port) for port in port_range]

        config = GumbyTriblerConfig(my_state_path)
        config.set_trustchain_keypair_filename("tc_keypair_" + str(self.experiment.my_id))
        config.set_torrent_checking_enabled(False)
        config.set_market_community_enabled(False)
        config.set_chant_enabled(False)
        config.set_libtorrent_enabled(False)
        config.set_api_http_enabled(False)
        config.set_libtorrent_port(20000 + self.experiment.my_id * 10)
        config.set_ipv8_port(self.ipv8_port)
        config.set_tunnel_community_enabled(False)
        config.set_dht_enabled(False)
        config.set_version_checker_enabled(False)
        config.set_bootstrap_enabled(False)
        config.set_popularity_community_enabled(False)
        return config

    @classmethod
    def get_ipv8_provider(cls, experiment):
        for module in experiment.experiment_modules:
            if isinstance(module, BaseIPv8Module):
                return module
        return None
