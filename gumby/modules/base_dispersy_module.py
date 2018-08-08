from os import environ, makedirs, symlink, path, getpid

from twisted.internet.defer import Deferred

from gumby.experiment import experiment_callback
from gumby.gumby_tribler_config import GumbyTriblerConfig
from gumby.modules.experiment_module import ExperimentModule
from gumby.modules.gumby_session import GumbySession
from gumby.modules.isolated_community_loader import IsolatedDispersyCommunityLoader, IsolatedIPv8CommunityLoader


class BaseDispersyModule(ExperimentModule):
    def __init__(self, experiment):
        if BaseDispersyModule.get_dispery_provider(experiment) is not None:
            raise Exception("Unable to load multiple dispersy providers in a single experiment")

        super(BaseDispersyModule, self).__init__(experiment)
        self.session = None
        self.tribler_config = None
        self.dispersy_port = None
        self.dispersy = None
        self.session_id = environ['SYNC_HOST'] + environ['SYNC_PORT']
        self.custom_dispersy_community_loader = self.create_dispersy_community_loader()
        self.custom_ipv8_community_loader = self.create_ipv8_community_loader()
        self.dispersy_available = Deferred()

    def on_id_received(self):
        super(BaseDispersyModule, self).on_id_received()
        self.tribler_config = self.setup_config()

    def create_dispersy_community_loader(self):
        return IsolatedDispersyCommunityLoader(self.session_id)

    def create_ipv8_community_loader(self):
        return IsolatedIPv8CommunityLoader(self.session_id)

    @experiment_callback
    def start_session(self):
        self.session = GumbySession(config=self.tribler_config)
        self.tribler_config = None

    @experiment_callback
    def set_dispersy_port(self, port):
        self.dispersy_port = int(port)

    @experiment_callback
    def reset_dispersy_statistics(self):
        self.dispersy._statistics.reset()

    @experiment_callback
    def isolate_dispersy_community(self, name):
        self.custom_dispersy_community_loader.isolate(name)

    @experiment_callback
    def isolate_ipv8_overlay(self, name):
        self.custom_ipv8_community_loader.isolate(name)

    def setup_config(self):
        if self.dispersy_port is None:
            self.dispersy_port = 12000 + self.experiment.my_id
        self._logger.info("Dispersy port set to %d" % self.dispersy_port)

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
            bootstrap_file = path.join(my_state_path, 'bootstraptribler.txt')

        # We manually update the IPv8 bootstrap servers since IPv8 does not use the bootstraptribler.txt file.
        from Tribler.pyipv8.ipv8.deprecated import community
        community._DEFAULT_ADDRESSES = []
        community._DNS_ADDRESSES = []
        with open(bootstrap_file, 'r') as bfile:
            for line in bfile.readlines():
                parts = line.split(" ")
                if not parts:
                    continue
                community._DNS_ADDRESSES.append((parts[0], int(parts[1])))

        config = GumbyTriblerConfig()
        config.set_permid_keypair_filename("keypair_" + str(self.experiment.my_id))
        config.set_state_dir(my_state_path)
        config.set_torrent_checking_enabled(False)
        config.set_megacache_enabled(False)
        config.set_dispersy_enabled(False)
        config.set_market_community_enabled(False)
        config.set_mainline_dht_enabled(False)
        config.set_mainline_dht_port(18000 + self.my_id)
        config.set_torrent_collecting_enabled(False)
        config.set_libtorrent_enabled(False)
        config.set_torrent_search_enabled(False)
        config.set_credit_mining_enabled(False)
        config.set_channel_search_enabled(False)
        config.set_video_server_enabled(False)
        config.set_http_api_enabled(False)
        config.set_libtorrent_port(20000 + self.experiment.my_id)
        config.set_dispersy_port(self.dispersy_port)
        config.set_tunnel_community_enabled(False)
        config.set_dht_enabled(False)
        return config

    @classmethod
    def get_dispery_provider(cls, experiment):
        for module in experiment.experiment_modules:
            if isinstance(module, BaseDispersyModule):
                return module
        return None
