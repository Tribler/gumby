import json
import os
import time
from asyncio import Future
from binascii import hexlify

from ipv8.bootstrapping.dispersy.bootstrapper import DispersyBootstrapper
from ipv8.configuration import get_default_configuration

from ipv8_service import IPv8

from gumby.experiment import experiment_callback
from gumby.gumby_client_config import GumbyConfig
from gumby.modules.experiment_module import ExperimentModule, static_module
from gumby.modules.ipv8_community_launchers import DHTCommunityLauncher, IPv8DiscoveryCommunityLauncher
from gumby.modules.isolated_community_loader import IsolatedIPv8CommunityLoader
from gumby.util import read_keypair_trustchain, run_task


class GumbyMinimalSession:
    """
    Minimal Gumby session, with a configuration.
    """

    def __init__(self, config):
        self.config = config
        self.trustchain_keypair = None


@static_module
class BaseIPv8Module(ExperimentModule):

    @classmethod
    def get_ipv8_provider(cls, experiment):
        for module in experiment.experiment_modules:
            if isinstance(module, BaseIPv8Module):
                return module
        return None

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
        self.ipv8 = None
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
        super(BaseIPv8Module, self).on_id_received()
        self.tribler_config = self.setup_config()

    def create_ipv8_community_loader(self):
        loader = IsolatedIPv8CommunityLoader(self.session_id)
        loader.set_launcher(DHTCommunityLauncher())
        loader.set_launcher(IPv8DiscoveryCommunityLauncher())
        return loader

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

        self.session = GumbyMinimalSession(self.tribler_config)
        self.session.trustchain_keypair = read_keypair_trustchain(self.tribler_config.trustchain.ec_keypair_filename)

        # Load overlays
        self.custom_ipv8_community_loader.load(self.ipv8, self.session)

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

    @experiment_callback
    def enable_ipv8_statistics(self):
        self.tribler_config.ipv8.statistics = True

    @experiment_callback
    def start_ipv8_statistics_monitor(self):
        run_task(self.write_ipv8_statistics, interval=1)

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
