from os import environ, getpid

from twisted.python.log import addObserver

from gumby.sync import experiment_callback
from gumby.modules.experiment_module import ExperimentModule
from gumby.modules.gumby_session import GumbySession
from gumby.modules.isolated_community_loader import IsolatedCommunityLoader

from Tribler.dispersy.util import unhandled_error_observer
from Tribler.Core.SessionConfig import SessionStartupConfig


class BaseDispersyModule(ExperimentModule):
    def __init__(self, experiment):
        super(BaseDispersyModule, self).__init__(experiment)
        self.session = None
        self.session_config = None
        self.dispersy_port = None
        self.dispersy = None
        self.session_id = environ['SYNC_HOST'] + environ['SYNC_PORT']
        self.custom_community_loader = self.create_community_loader()

    def on_id_received(self):
        super(BaseDispersyModule, self).on_id_received()
        self.session_config = self.setup_session_config()
        self.session = GumbySession(scfg=self.session_config)

    def create_community_loader(self):
        return IsolatedCommunityLoader(self.session_id)

    @experiment_callback
    def set_dispersy_port(self, port):
        self.dispersy_port = int(port)

    @experiment_callback
    def reset_dispersy_statistics(self):
        self.dispersy._statistics.reset()

    @experiment_callback
    def isolate_community(self, name):
        self.custom_community_loader.isolate(name)

    @experiment_callback
    def observe_exceptions(self):
        addObserver(unhandled_error_observer)

    def setup_session_config(self):
        if self.dispersy_port is None:
            self.dispersy_port = 12000 + self.experiment.my_id
        self._logger.error("Dispersy port set to %d" % self.dispersy_port)

        config = SessionStartupConfig()
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
        return config
