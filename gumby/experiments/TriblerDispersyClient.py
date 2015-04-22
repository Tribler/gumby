from os import getpid
from sys import path as pythonpath
import os
import time
from twisted.internet import reactor
from twisted.internet.threads import deferToThread

from gumby.experiments.dispersyclient import DispersyExperimentScriptClient
from time import sleep
import logging

# TODO(emilon): Fix this crap
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
pythonpath.append(os.path.abspath(os.path.join(BASE_DIR, "./tribler")))

from Tribler.Core.Session import Session


class TriblerDispersyExperimentScriptClient(DispersyExperimentScriptClient):

    def __init__(self, params):
        DispersyExperimentScriptClient.__init__(self, params)
        self.session = None
        self.session_config = None
        self.session_deferred = None

    def registerCallbacks(self):
        DispersyExperimentScriptClient.registerCallbacks(self)
        self.scenario_runner.register(self.start_session, 'start_session')

    def start_dispersy(self, autoload_discovery=True):
        raise NotImplementedError("Dispersy is started using the tribler session in start_session")

    def stop_dispersy(self):
        raise NotImplementedError("Dispersy is stopped using the tribler session in stop")

    def start_session(self):
        from twisted.internet import threads

        def _do_start():
            logging.error("Starting Tribler Session")
            self.session_config = self.setup_session_config()
            self.session = Session(scfg=self.session_config)

            logging.error("Upgrader")
            upgrader = self.session.prestart()
            while not upgrader.is_done:
                sleep(0.1)

            self.session.start()

            while not self.session.lm.initComplete:
                time.sleep(0.5)

            logging.error("Tribler Session started")
            self.annotate("Tribler Session started")

            self._dispersy = self.session.lm.dispersy

            return self.session

        self.session_deferred = threads.deferToThread(_do_start)
        self.session_deferred.addCallback(self.__start_dispersy)

    def __start_dispersy(self, session):
        self.original_on_incoming_packets = self._dispersy.on_incoming_packets
        if self.master_private_key:
            self._master_member = self._dispersy.get_member(private_key=self.master_private_key)
        else:
            self._master_member = self._dispersy.get_member(public_key=self.master_key)
        self._my_member = self.get_my_member()
        assert self._master_member
        assert self._my_member

        self._do_log()

        self.print_on_change('community-kwargs', {}, self.community_kwargs)
        self.print_on_change('community-env', {}, {'pid': getpid()})

        logging.error("Finished starting dispersy")

    def setup_session_config(self):
        from Tribler.Core.SessionConfig import SessionStartupConfig

        config = SessionStartupConfig()
        config.set_install_dir(os.path.abspath(os.path.join(BASE_DIR, "tribler")))
        config.set_state_dir(os.path.abspath(os.path.join(BASE_DIR, "output", ".Tribler-%d") % getpid()))
        config.set_torrent_checking(False)
        config.set_multicast_local_peer_discovery(False)
        config.set_megacache(False)
        config.set_dispersy(True)
        config.set_mainline_dht(True)
        config.set_torrent_collecting(False)
        config.set_libtorrent(True)
        config.set_dht_torrent_collecting(False)
        config.set_enable_torrent_search(False)
        config.set_enable_channel_search(False)
        config.set_videoplayer(False)
        config.set_listen_port(20000 + 10 * self.scenario_runner._peernumber)
        config.set_dispersy_port(21000 + 10 * self.scenario_runner._peernumber)
        return config

    def stop(self, retry=3):
        logging.error("Defer session stop to thread and stop reactor afterwards")
        return deferToThread(self.session.shutdown, False).addBoth(lambda _: reactor.callLater(10.0, reactor.stop))
