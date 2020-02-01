"""
The dht module aims to provide DHT isolation for experiments, and provide dht related utility experiment callbacks.
"""
from gumby.experiment import experiment_callback

from gumby.modules.experiment_module import static_module, ExperimentModule

from tribler_core.modules.libtorrent.libtorrent_mgr import LibtorrentMgr as lt


class EverEmptySet(frozenset):
    def add(self, _):
        pass

    def remove(self, _):
        pass


@static_module
class DHTModule(ExperimentModule):
    def __init__(self, experiment):
        super(DHTModule, self).__init__(experiment)
        self.dht_nodes = []

    @property
    def tribler(self):
        from gumby.modules.base_ipv8_module import BaseIPv8Module
        from gumby.modules.tribler_module import TriblerModule

        trib = BaseIPv8Module.get_ipv8_provider(self.experiment)
        if not trib or not isinstance(trib, TriblerModule):
            raise Exception("No TriblerModule loaded. Load an implementation of TriblerModule before loading the %s "
                            "module", self.__class__.__name__)
        return trib

    @property
    def lm(self):
        if not self.tribler.session or not self.tribler.session.lm:
            raise Exception("Tribler instance not started or no LaunchManyCore?!")
        return self.tribler.session.lm

    @property
    def session_config(self):
        if self.tribler.tribler_config is None:
            return self.tribler.session

        return self.tribler.tribler_config

    def on_id_received(self):
        super(DHTModule, self).on_id_received()

    def on_all_vars_received(self):
        super(DHTModule, self).on_id_received()
        for node_dict in self.all_vars.values():
            if "dht_node_port" in node_dict:
                self.dht_nodes.append((str(node_dict["host"]), int(node_dict["dht_node_port"])))

    @experiment_callback
    def print_dht_table(self):
        for ltsession in self.ltmgr.ltsessions.values():
            if hasattr(ltsession, 'post_dht_stats'):
                ltsession.post_dht_stats()

    @experiment_callback
    def disable_libtorrent_dht(self):
        for sess in self.lm.ltmgr.ltsessions.values():
            settings = self.session.ltmgr.get_session_settings(sess)
            settings["enable_dht"] = False
            self.session.ltmgr.set_session_settings(sess, settings)

    @experiment_callback
    def enable_libtorrent_dht(self):
        for sess in self.lm.ltmgr.ltsessions.values():
            settings = self.session.ltmgr.get_session_settings(sess)
            settings["enable_dht"] = True
            self.session.ltmgr.set_session_settings(sess, settings)

    @experiment_callback
    def isolate_dht(self):
        # LibTorrentMgr also requires monkey patches, an empty default dht router list and no PEX in the 0 hops case
        original_create_session = lt.LibtorrentMgr.create_session
        lt.DEFAULT_DHT_ROUTERS = []
        if lt.lt.create_ut_pex_plugin in lt.DEFAULT_LT_EXTENSIONS:
            lt.DEFAULT_LT_EXTENSIONS.remove(lt.lt.create_ut_pex_plugin)

        def do_dht_check(*_):
            pass

        def create_session(inst, hops=0, store_listen_port=True):
            sess = original_create_session(inst, hops=hops, store_listen_port=store_listen_port)
            for node in self.dht_nodes:
                sess.add_dht_node(node)

            if hops == 0:
                self.dht_nodes.append(("127.0.0.1", sess.listen_port()))
            # else: we don't know the port of the exit socket

            settings = self.session.ltmgr.get_session_settings(sess)
            settings["enable_lsd"] = False
            self.session.ltmgr.set_session_settings(sess, settings)

            inst.dht_ready = True
            return sess

        lt.LibtorrentMgr.do_dht_check = do_dht_check
        lt.LibtorrentMgr.create_session = create_session
