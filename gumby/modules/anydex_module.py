import json
import os
import time
from asyncio import Future
from binascii import hexlify
from os import environ, getpid, makedirs, symlink, path

from gumby.anydex_config import AnyDexConfig
from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import ExperimentModule, static_module
from gumby.modules.isolated_community_loader import IsolatedIPv8CommunityLoader
from gumby.util import read_keypair_trustchain, run_task

from ipv8.bootstrapping.dispersy.bootstrapper import DispersyBootstrapper
from ipv8.loader import CommunityLauncher
from ipv8.peer import Peer

from ipv8_service import IPv8


# The lazy-loading of Community-specific files triggers Pylint, this is expected:
# pylint: disable=C0415,W0613


class BaseAnyDexLauncher(CommunityLauncher):

    def get_bootstrappers(self, session):
        my_state_path = session.config.get_state_dir()

        # We manually update the IPv8 bootstrap servers since IPv8 does not use the bootstraptribler.txt file.
        bootstrap_file = path.join(my_state_path, 'bootstraptribler.txt')
        dns_addresses = []
        with open(bootstrap_file, 'r') as bfile:
            for line in bfile.readlines():
                parts = line.split(" ")
                if not parts:
                    continue
                dns_addresses.append((parts[0], int(parts[1])))

        return [(DispersyBootstrapper, {"ip_addresses": [], "dns_addresses": dns_addresses})]


class TrustChainCommunityLauncher(BaseAnyDexLauncher):

    def should_launch(self, session):
        return session.config.get_trustchain_enabled()

    def get_overlay_class(self):
        from ipv8.attestation.trustchain.community import TrustChainCommunity
        return TrustChainCommunity

    def get_my_peer(self, ipv8, session):
        return Peer(session.trustchain_keypair)

    def get_kwargs(self, session):
        return {'working_directory': session.config.get_state_dir()}

    def finalize(self, ipv8, session, community):
        session.trustchain_community = community

        # If we're using a memory DB, replace the existing one
        if session.config.use_trustchain_memory_db():
            orig_db = community.persistence

            from experiments.trustchain.trustchain_mem_db import TrustchainMemoryDatabase
            community.persistence = TrustchainMemoryDatabase(session.config.get_state_dir(), 'trustchain')
            community.persistence.original_db = orig_db

        return super()


class MarketCommunityLauncher(BaseAnyDexLauncher):

    def not_before(self):
        return ['DHTCommunityLauncher', 'TrustChainCommunityLauncher']

    def should_launch(self, session):
        return session.config.get_market_community_enabled()

    def get_overlay_class(self):
        from anydex.core.community import MarketCommunity
        return MarketCommunity

    def get_my_peer(self, ipv8, session):
        return Peer(session.trustchain_keypair)

    def get_kwargs(self, session):
        return {
            'trustchain': session.trustchain_community,
            'dht': session.dht_community,
            'use_database': not session.config.use_market_memory_db()
        }


class DHTCommunityLauncher(BaseAnyDexLauncher):

    def should_launch(self, session):
        return session.config.get_dht_enabled()

    def get_overlay_class(self):
        from ipv8.dht.discovery import DHTDiscoveryCommunity
        return DHTDiscoveryCommunity

    def get_my_peer(self, ipv8, session):
        return Peer(session.trustchain_keypair)

    def get_kwargs(self, session):
        return {}

    def finalize(self, ipv8, session, community):
        session.dht_community = community
        return super()


class GumbyMinimalLm(object):
    """
    Minimal lm object, used to remain compatibility with Tribler-entangled code.
    """
    pass


class GumbyMinimalSession(object):
    """
    Minimal Gumby session, with a configuration.
    """

    def __init__(self, config):
        self.config = config
        self.lm = GumbyMinimalLm()
        self.trustchain_keypair = None


@static_module
class AnyDexModule(ExperimentModule):
    """
    This module starts an IPv8 instance and runs AnyDex.
    """

    def __init__(self, experiment):
        super(AnyDexModule, self).__init__(experiment)
        self.has_ipv8 = True
        self.session = None
        self.ipv8_port = None
        self.tribler_config = None
        self.session_id = environ['SYNC_HOST'] + environ['SYNC_PORT']
        self.custom_ipv8_community_loader = self.create_ipv8_community_loader()
        self.ipv8_available = Future()
        self.ipv8 = None

    def write_ipv8_statistics(self):
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
        super(AnyDexModule, self).on_id_received()
        self.tribler_config = self.setup_config()

    def create_ipv8_community_loader(self):
        loader = IsolatedIPv8CommunityLoader(self.session_id)
        loader.set_launcher(TrustChainCommunityLauncher())
        loader.set_launcher(MarketCommunityLauncher())
        loader.set_launcher(DHTCommunityLauncher())
        return loader

    @experiment_callback
    async def start_session(self):
        from ipv8.configuration import get_default_configuration

        ipv8_config = get_default_configuration()
        ipv8_config['port'] = self.tribler_config.get_ipv8_port()
        ipv8_config['overlays'] = []
        ipv8_config['keys'] = []  # We load the keys ourselves
        self.ipv8 = IPv8(ipv8_config, enable_statistics=self.tribler_config.get_ipv8_statistics())

        self.session = GumbyMinimalSession(self.tribler_config)
        self.session.trustchain_keypair = read_keypair_trustchain(self.tribler_config.get_trustchain_keypair_filename())

        # Load overlays
        self.custom_ipv8_community_loader.load(self.ipv8, self.session)
        await self.ipv8.start()
        self.ipv8_available.set_result(self.ipv8)

    @experiment_callback
    async def stop_session(self):
        await self.ipv8.stop()

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

        my_state_path = path.abspath(path.join(environ["OUTPUT_DIR"], ".%s-%d-%d" % (self.__class__.__name__,
                                                                                     getpid(), self.my_id)))
        makedirs(my_state_path)
        bootstrap_file = path.join(environ['OUTPUT_DIR'], 'bootstraptribler.txt')
        if path.exists(bootstrap_file):
            symlink(bootstrap_file, path.join(my_state_path, 'bootstraptribler.txt'))
        else:
            base_tracker_port = int(environ['TRACKER_PORT'])
            port_range = range(base_tracker_port, base_tracker_port + 4)
            with open(path.join(my_state_path, 'bootstraptribler.txt'), "w+") as f:
                f.write("\n".join(["%s %d" % (environ['HEAD_HOST'], port) for port in port_range]))

        config = AnyDexConfig()
        config.set_trustchain_keypair_filename(os.path.join(my_state_path, "tc_keypair_" + str(self.experiment.my_id)))
        self._logger.info("Setting state dir to %s", my_state_path)
        config.set_state_dir(my_state_path)
        config.set_ipv8_port(self.ipv8_port)
        return config
