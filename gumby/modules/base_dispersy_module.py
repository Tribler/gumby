from os import environ, makedirs, symlink, path, getpid

from twisted.internet.defer import Deferred

from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import ExperimentModule
from gumby.modules.gumby_session import GumbySession
from gumby.modules.isolated_community_loader import IsolatedCommunityLoader

from Tribler.Core.Config.tribler_config import TriblerConfig


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
        self.session_config = self.setup_config()

    def create_community_loader(self):
        return IsolatedCommunityLoader(self.session_id)

    @experiment_callback
    def start_session(self):
        conf = self.session_config
        self.session_config = None
        self.session = GumbySession(config=conf)

    @experiment_callback
    def set_dispersy_port(self, port):
        self.dispersy_port = int(port)

    @experiment_callback
    def reset_dispersy_statistics(self):
        self.dispersy._statistics.reset()

    @experiment_callback
    def isolate_community(self, name):
        self.custom_community_loader.isolate(name)

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

        config = TriblerConfig()
        config.set_permid_keypair_filename("keypair_" + str(self.experiment.my_id))
        config.set_state_dir(my_state_path)
        config.set_torrent_checking_enabled(False)
        config.set_megacache_enabled(False)
        config.set_dispersy_enabled(True)
        config.set_mainline_dht_enabled(False)
        config.set_mainline_dht_port(18000 + self.my_id)
        config.set_torrent_collecting_enabled(False)
        config.set_libtorrent_enabled(False)
        config.set_torrent_search_enabled(False)
        config.set_channel_search_enabled(False)
        config.set_video_server_enabled(False)
        config.set_http_api_enabled(False)
        config.set_upgrader_enabled(False)
        config.set_libtorrent_port(20000 + self.experiment.my_id)
        config.set_dispersy_port(self.dispersy_port)
        config.set_tunnel_community_enabled(False)
        config.set_trustchain_enabled(False)
        config.set_market_community_enabled(False)
        return config

    @classmethod
    def get_dispery_provider(cls, experiment):
        for module in experiment.experiment_modules:
            if isinstance(module, BaseDispersyModule):
                return module
        return None

    @classmethod
    def get_dispersy(cls, experiment):
        provider = cls.get_dispery_provider(experiment)
        if not provider:
            return None
        return provider.dispersy

    @classmethod
    def get_session(cls, experiment):
        provider = cls.get_dispery_provider(experiment)
        if not provider:
            return None
        return cls.get_dispery_provider(experiment).session

    @classmethod
    def get_session_config(cls, experiment):
        provider = cls.get_dispery_provider(experiment)
        if not provider:
            return None

        # The session_config only exists after on_id_received, up to session start. The session start copies
        # all settings so writing to the original session_config after this will not do anything. So on any access to
        # the session_config after the session has launched, return the sessions config.
        if provider.session_config is None:
            return provider.session.config
        else:
            return provider.session_config
