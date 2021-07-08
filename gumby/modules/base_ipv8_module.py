import json
import os
import time
from asyncio import Future
from binascii import hexlify
from pathlib import Path

from gumby.experiment import experiment_callback
from gumby.gumby_tribler_config import GumbyTriblerConfig
from gumby.modules.experiment_module import ExperimentModule
from gumby.modules.gumby_session import GumbyTriblerSession
from gumby.modules.isolated_community_loader import IsolatedIPv8CommunityLoader
from gumby.util import run_task

from tribler_core.modules.ipv8_module_catalog import (BandwidthCommunityLauncher,
                                                      DHTCommunityLauncher,
                                                      GigaChannelCommunityLauncher,
                                                      IPv8DiscoveryCommunityLauncher,
                                                      PopularityCommunityLauncher,
                                                      TriblerTunnelCommunityLauncher)


class BaseIPv8Module(ExperimentModule):
    def __init__(self, experiment):
        if BaseIPv8Module.get_ipv8_provider(experiment) is not None:
            raise Exception("Unable to load multiple IPv8 providers in a single experiment")

        super(BaseIPv8Module, self).__init__(experiment)
        self.has_ipv8 = True
        self.session = None
        self.tribler_config = None
        self.ipv8_port = None
        self.session_id = os.environ['SYNC_HOST'] + os.environ['SYNC_PORT']
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
        loader.set_launcher(TriblerTunnelCommunityLauncher())
        loader.set_launcher(PopularityCommunityLauncher())
        loader.set_launcher(DHTCommunityLauncher())
        loader.set_launcher(GigaChannelCommunityLauncher())
        loader.set_launcher(BandwidthCommunityLauncher())
        return loader

    @experiment_callback
    def start_session(self):
        self.session = GumbyTriblerSession(config=self.tribler_config)
        self.tribler_config = None

    @experiment_callback
    def enable_ipv8_statistics(self):
        self.tribler_config.ipv8.statistics = True

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

        my_state_path = os.path.join(os.environ['OUTPUT_DIR'], str(self.my_id))
        self._logger.info("State path: %s", my_state_path)

        config = GumbyTriblerConfig(state_dir=Path(my_state_path))
        config.ipv8.bootstrap_override = "0.0.0.0:0"
        config.trustchain.ec_keypair_filename = "tc_keypair_" + str(self.experiment.my_id)
        config.torrent_checking.enabled = False
        config.discovery_community.enabled = False
        config.chant.enabled = False
        config.libtorrent.enabled = False
        config.api.http_enabled = False
        config.libtorrent.port = 20000 + self.experiment.my_id * 10
        config.ipv8.port = self.ipv8_port
        config.tunnel_community.enabled = False
        config.dht.enabled = False
        config.general.version_checker_enabled = False
        config.bootstrap.enabled = False
        config.popularity_community.enabled = False
        return config

    @classmethod
    def get_ipv8_provider(cls, experiment):
        for module in experiment.experiment_modules:
            if isinstance(module, BaseIPv8Module):
                return module
        return None
