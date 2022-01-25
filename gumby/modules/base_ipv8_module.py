import json
import os
import time
from abc import abstractmethod
from asyncio import Future
from binascii import hexlify
from typing import Optional

from ipv8.bootstrapping.dispersy.bootstrapper import DispersyBootstrapper
from ipv8.configuration import get_default_configuration

from ipv8_service import IPv8

from gumby.experiment import experiment_callback, ExperimentClient
from gumby.gumby_client_config import GumbyConfig
from gumby.modules.experiment_module import ExperimentModule
from gumby.modules.ipv8_community_launchers import DHTCommunityLauncher, IPv8DiscoveryCommunityLauncher
from gumby.modules.isolated_community_loader import IsolatedIPv8CommunityLoader
from gumby.util import read_keypair_trustchain, run_task


class GumbyMinimalSession:
    """
    Minimal Gumby session, with a configuration.
    """

    def __init__(self, config):
        self.config = config
        self.trustchain_keypair = read_keypair_trustchain(self.config.trustchain.ec_keypair_filename)


class IPv8Provider(ExperimentModule):
    gumby_session: Optional[GumbyMinimalSession] = None
    tribler_config = None
    ipv8_available: Future
    ipv8: Optional[IPv8] = None
    ipv8_port: Optional[int] = None

    def __init__(self, experiment: ExperimentClient):
        for module in experiment.experiment_modules:
            if isinstance(module, IPv8Provider) and module is not self:
                raise Exception("Unable to load multiple IPv8 providers in a single experiment")

        super().__init__(experiment)
        self.ipv8_available = Future()
        self.session_id = os.environ['SYNC_HOST'] + os.environ['SYNC_PORT']
        self.bootstrappers = []

    @experiment_callback
    def write_overlay_statistics(self):
        """
        Write information about the IPv8 overlay networks to a file.
        """
        with open('overlays.txt', 'w') as overlays_file:
            overlays_file.write("name,pub_key,peers\n")
            for overlay in self.ipv8.overlays:
                overlays_file.write("%s,%s,%d\n" % (overlay.__class__.__name__,
                                                    hexlify(overlay.my_peer.public_key.key_to_bin()),
                                                    len(overlay.get_peers())))

        # Write verified peers
        with open('verified_peers.txt', 'w') as peers_file:
            for peer in self.ipv8.network.verified_peers:
                peers_file.write('%d\n' % (peer.address[1] - 12000))

        # Write bandwidth statistics
        with open('bandwidth.txt', 'w') as bandwidth_file:
            bandwidth_file.write("%d,%d" % (self.ipv8.endpoint.bytes_up,
                                            self.ipv8.endpoint.bytes_down))

    @experiment_callback
    def set_bootstrap(self, peer_id, port):
        bootstrap_host, _ = self.experiment.get_peer_ip_port_by_id(int(peer_id))
        bootstrap_ip = (bootstrap_host, int(port))
        self._logger.info("Setting bootstrap to: %s:%d", *bootstrap_ip)
        self.bootstrappers.append(DispersyBootstrapper([bootstrap_ip], []))

    def write_ipv8_statistics(self):
        if not self.ipv8:
            return

        statistics = self.ipv8.endpoint.statistics

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
        super().on_id_received()
        self.tribler_config = self.setup_config()
        setattr(self.experiment, 'tribler_config', self.tribler_config)

    @abstractmethod
    def setup_config(self):
        raise NotImplementedError

    @experiment_callback
    def enable_ipv8_statistics(self):
        self.tribler_config.ipv8.statistics = True

    @experiment_callback
    def start_ipv8_statistics_monitor(self):
        run_task(self.write_ipv8_statistics, interval=1)


class BaseIPv8Module(IPv8Provider):
    def __init__(self, experiment):
        super().__init__(experiment)
        self.custom_ipv8_community_loader = self.create_ipv8_community_loader()
        self.bootstrappers = []

    def create_ipv8_community_loader(self):
        loader = IsolatedIPv8CommunityLoader(self.session_id)
        loader.set_launcher(DHTCommunityLauncher())
        loader.set_launcher(IPv8DiscoveryCommunityLauncher())
        return loader

    @experiment_callback
    def isolate_ipv8_overlay(self, name):
        self.custom_ipv8_community_loader.isolate(name)

    def setup_config(self):
        if self.ipv8_port is None:
            self.ipv8_port = 12000 + self.experiment.my_id
        self._logger.info("IPv8 port set to %d", self.ipv8_port)

        my_state_path = os.path.join(os.environ['OUTPUT_DIR'], str(self.my_id))

        config = GumbyConfig()
        config.trustchain.ec_keypair_filename = os.path.join(my_state_path, "tc_keypair_" + str(self.experiment.my_id))
        self._logger.info("Setting state dir to %s", my_state_path)
        config.state_dir = my_state_path
        config.ipv8.port = self.ipv8_port
        return config

    @experiment_callback
    async def start_session(self):
        """
        Start an IPv8 session.
        """
        ipv8_config = get_default_configuration()
        ipv8_config['port'] = self.tribler_config.ipv8.port
        ipv8_config['overlays'] = []
        ipv8_config['keys'] = []  # We load the keys ourselves
        self.ipv8 = IPv8(ipv8_config, enable_statistics=self.tribler_config.ipv8.statistics)

        self.gumby_session = GumbyMinimalSession(self.tribler_config)

        # Load overlays
        self.custom_ipv8_community_loader.load(self.ipv8, self.gumby_session)

        # Set bootstrap servers if specified
        if self.bootstrappers:
            for overlay in self.ipv8.overlays:
                overlay.bootstrappers = self.bootstrappers

        await self.ipv8.start()
        self.ipv8_available.set_result(self.ipv8)

        if self.tribler_config.ipv8.statistics:
            for overlay in self.ipv8.overlays:
                self.ipv8.endpoint.enable_community_statistics(overlay.get_prefix(), True)

    @experiment_callback
    async def stop_session(self):
        await self.ipv8.stop()
