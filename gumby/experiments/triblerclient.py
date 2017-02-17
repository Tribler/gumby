from os import getpid
from sys import path as pythonpath
import os
from twisted.internet import reactor
from twisted.internet.threads import deferToThread

from gumby.experiments.dispersyclient import DispersyExperimentScriptClient
import logging

# TODO(emilon): Fix this crap
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
pythonpath.append(os.path.abspath(os.path.join(BASE_DIR, "./tribler")))

from Tribler.Core.Session import Session


class TriblerExperimentScriptClient(DispersyExperimentScriptClient):

    def __init__(self, params):
        super(TriblerExperimentScriptClient, self).__init__(params)
        self.session = None
        self.session_config = None
        self.session_deferred = None
        self.dispersy_port = None

    def registerCallbacks(self):
        super(TriblerExperimentScriptClient, self).registerCallbacks()
        self.scenario_runner.register(self.set_dispersy_port)
        self.scenario_runner.register(self.start_session)
        self.scenario_runner.register(self.stop_session)

    def set_dispersy_port(self, port):
        self.dispersy_port = int(port)

    def start_dispersy(self, autoload_discovery=True):
        raise NotImplementedError("Dispersy is started using the tribler session in start_session")

    def stop_dispersy(self):
        raise NotImplementedError("Dispersy is stopped using the tribler session in stop")

    def start_session(self):
        logging.error("Starting Tribler Session")

        # symlink the bootstrap file so we are only connecting to our own trackers
        os.makedirs(os.path.abspath(os.path.join(BASE_DIR, "output", ".Tribler-%d" % getpid())))
        bootstrap_file_path = os.path.join(os.environ['PROJECT_DIR'], 'tribler', 'bootstraptribler.txt')
        dest_file_path = os.path.abspath(
            os.path.join(BASE_DIR, "output", ".Tribler-%d" % getpid(), 'bootstraptribler.txt'))
        os.symlink(bootstrap_file_path, dest_file_path)

        self.session_config = self.setup_session_config()
        self.session = Session(scfg=self.session_config)

        def on_tribler_started(_):
            logging.error("Tribler Session started")
            self.annotate("Tribler Session started")
            self._dispersy = self.session.lm.dispersy

        return self.session.start().addCallback(on_tribler_started)

    def stop_session(self):
        self.annotate('end of experiment')
        deferToThread(self.session.shutdown)

    def setup_session_config(self):
        from Tribler.Core.SessionConfig import SessionStartupConfig

        config = SessionStartupConfig()
        config.set_install_dir(os.path.abspath(os.path.join(BASE_DIR, "tribler")))
        config.set_state_dir(os.path.abspath(os.path.join(BASE_DIR, "output", ".Tribler-%d") % getpid()))
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
        config.set_listen_port(20000 + self.scenario_runner._peernumber)

        if self.dispersy_port is None:
            self.dispersy_port = 21000 + self.scenario_runner._peernumber
        config.set_dispersy_port(self.dispersy_port)
        logging.error("Dispersy port set to %d" % self.dispersy_port)
        return config

    def stop(self, retry=3):
        logging.error("Stopping reactor")
        reactor.stop()
