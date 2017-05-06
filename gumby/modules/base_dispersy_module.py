from os import environ, makedirs, symlink, path, getpid

from twisted.internet.defer import Deferred

from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import ExperimentModule
from gumby.modules.gumby_session import GumbySession
from gumby.modules.isolated_community_loader import IsolatedCommunityLoader

from Tribler.Core.SessionConfig import SessionStartupConfig


class BaseDispersyModule(ExperimentModule):
    def __init__(self, experiment):
        if BaseDispersyModule.get_dispery_provider(experiment) is not None:
            raise Exception("Unable to load multiple dispersy providers in a single experiment")

        super(BaseDispersyModule, self).__init__(experiment)
        self.session = None
        self.session_config = None
        self.dispersy_port = None
        self.dispersy = None
        self.session_id = environ['SYNC_HOST'] + environ['SYNC_PORT']
        self.custom_community_loader = self.create_community_loader()
        self.dispersy_available = Deferred()

    def on_id_received(self):
        super(BaseDispersyModule, self).on_id_received()
        self.session_config = self.setup_session_config()

    def create_community_loader(self):
        return IsolatedCommunityLoader(self.session_id)

    @experiment_callback
    def start_session(self):
        self.session = GumbySession(scfg=self.session_config)
        self.session_config = None

    @experiment_callback
    def set_dispersy_port(self, port):
        self.dispersy_port = int(port)

    @experiment_callback
    def reset_dispersy_statistics(self):
        self.dispersy._statistics.reset()

    @experiment_callback
    def isolate_community(self, name):
        self.custom_community_loader.isolate(name)

    def setup_session_config(self):
        if self.dispersy_port is None:
            self.dispersy_port = 12000 + self.experiment.my_id
        self._logger.info("Dispersy port set to %d" % self.dispersy_port)

        my_state_path = path.abspath(path.join(environ["OUTPUT_DIR"], ".%s-%d-%d" % (self.__class__.__name__,
                                                                                     getpid(), self.my_id)))
        makedirs(my_state_path)
        bootstrap_file = path.join(environ['OUTPUT_DIR'], 'bootstraptribler.txt')
        if path.exists(bootstrap_file):
            symlink(bootstrap_file, path.join(my_state_path, 'bootstraptribler.txt'))

        config = SessionStartupConfig()
        config.set_state_dir(my_state_path)
        config.set_install_dir(environ["TRIBLER_DIR"])
        config.set_torrent_checking(False)
        config.set_multicast_local_peer_discovery(False)
        config.set_megacache(False)
        config.set_dispersy(True)
        config.set_mainline_dht(False)
        config.set_torrent_collecting(False)
        config.set_libtorrent(False)
        config.set_dht_torrent_collecting(False)
        config.set_enable_torrent_search(False)
        config.set_enable_channel_search(False)
        config.set_videoserver_enabled(False)
        config.set_http_api_enabled(False)
        config.set_upgrader_enabled(False)
        config.set_listen_port(20000 + self.experiment.my_id)
        config.set_dispersy_port(self.dispersy_port)
        config.set_tunnel_community_enabled(False)
        config.set_enable_multichain(False)
        return config

    @classmethod
    def get_dispery_provider(cls, experiment):
        for module in experiment.experiment_modules:
            if isinstance(module, BaseDispersyModule):
                return module
        return None
