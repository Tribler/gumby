"""
The dht module aims to provide DHT isolation for experiments, and provide dht related utility experiment callbacks.
"""
from random import sample

from gumby.experiment import experiment_callback

from gumby.modules.experiment_module import static_module, ExperimentModule
from gumby.modules.base_dispersy_module import BaseDispersyModule
from gumby.modules.tribler_module import TriblerModule

from Tribler.Core.DecentralizedTracking.pymdht.core.routing_table import Bucket
import Tribler.Core.DecentralizedTracking.mainlineDHT as pymdht
import Tribler.Core.Libtorrent.LibtorrentMgr as lt


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
        trib = BaseDispersyModule.get_dispery_provider(self.experiment)
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
        if self.tribler.session_config is None:
            return self.tribler.session
        else:
            return self.tribler.session_config

    def on_id_received(self):
        super(DHTModule, self).on_id_received()
        self.session_config.set_mainline_dht(True)
        self.vars["dht_node_port"] = self.session_config.get_mainline_dht_listen_port()

    def on_all_vars_received(self):
        super(DHTModule, self).on_id_received()
        for node_dict in self.all_vars.itervalues():
            if "dht_node_port" in node_dict:
                self.dht_nodes.append((str(node_dict["host"]), int(node_dict["dht_node_port"])))

    @experiment_callback
    def print_dht_table(self):
        self.lm.mainline_dht.controller._routing_m.table.print_table()
        for ltsession in self.lm.ltmgr.ltsessions.itervalues():
            ltsession.post_dht_stats()

    @experiment_callback
    def disable_libtorrent_dht(self):
        for sess in self.lm.ltmgr.ltsessions.itervalues():
            settings = sess.get_settings()
            settings["enable_dht"] = False
            sess.set_settings(settings)

    @experiment_callback
    def enable_libtorrent_dht(self):
        for sess in self.lm.ltmgr.ltsessions.itervalues():
            settings = sess.get_settings()
            settings["enable_dht"] = True
            sess.set_settings(settings)

    @experiment_callback
    def disable_pymdht_dht(self):
        if self.lm.mainline_dht:
            pymdht.deinit(self.lm.mainline_dht)
            self.lm.mainline_dht = None

    @experiment_callback
    def enable_pymdht_dht(self):
        if not self.lm.mainline_dht:
            self.lm.mainline_dht = pymdht.init(('127.0.0.1', self.session_config.get_mainline_dht_listen_port()),
                                               self.session_config.get_state_dir())

    @experiment_callback
    def isolate_dht(self):
        # This dht method is not split into pymdht and libtorrent dht since having one non isolated DHT causes leakage.
        # Call this function early, specifically before the session is started. This is to ensure the monkey patches are
        # seen by subsequent imports.

        # Pymdht has a hardcoded bootstrap. The only real option is to monkey patch it, and return nodes that we want.
        def is_hardcoded(*_):
            return False

        def get_sample_unstable_addrs(*_):
            return []

        def get_shuffled_stable_addrs(*_):
            return sample(self.dht_nodes, len(self.dht_nodes))

        pymdht.pymdht.controller.bootstrap.OverlayBootstrapper.is_hardcoded = is_hardcoded
        pymdht.pymdht.controller.bootstrap.OverlayBootstrapper.get_sample_unstable_addrs = get_sample_unstable_addrs
        pymdht.pymdht.controller.bootstrap.OverlayBootstrapper.get_shuffled_stable_addrs = get_shuffled_stable_addrs

        # By default pymdht will filter out local addresses in node and peer lists. There is no option to control this
        # behaviour, so again the only solution is a patch...

        def uncompact(c_addr):
            if len(c_addr) != pymdht.pymdht.controller.message.mt.ADDR4_SIZE:
                raise pymdht.pymdht.controller.message.mt.AddrError, 'invalid address size'
            ip = pymdht.pymdht.controller.message.mt.inet_ntoa(c_addr[:-2])
            port = pymdht.pymdht.controller.message.mt.bin_to_int(c_addr[-2:])
            if port == 0:
                pymdht.pymdht.controller.message.mt.logger.warning('c_addr: %r > port is ZERO' % c_addr)
                raise pymdht.pymdht.controller.message.mt.AddrError
            return (ip, port)

        pymdht.pymdht.controller.message.mt.uncompact_addr = uncompact

        # Using only a few hosts on the same IP it is very easy to trigger the flood barrier defence. Disable it...
        def ip_blocked(*_):
            return False

        pymdht.pymdht.minitwisted.FloodBarrier.ip_blocked = ip_blocked

        # By default pymdht's RoutingTable class will filter out multiple nodes on the same IP. It is used rather
        # extensively, so we can't really alter the class. To fix we make sure that the "list of ip's in the table" is
        # immutable. However we have to do this before the instance is created when pymdht is initialized. The way to do
        # this is to monkey patch the __init__ method.
        old_RT__init__ = pymdht.routing_mod.RoutingTable.__init__

        def new_RT__init__(self, my_node, nodes_per_bucket):
            old_RT__init__(self, my_node, nodes_per_bucket)
            self._ips_in_main = EverEmptySet()

        pymdht.routing_mod.RoutingTable.__init__ = new_RT__init__

        # The same story goes for the lookup manager. It will not bootstrap from one IP multiple times.
        old_lookup__init__ = pymdht.lookup_mod._LookupQueue.__init__
        old_lookup_bootstrap = pymdht.lookup_mod._LookupQueue.bootstrap

        def new_lookup__init__(self, info_hash, queue_size):
            old_lookup__init__(self, info_hash, queue_size)
            self.queued_ips = EverEmptySet()
            self.queried_ips = EverEmptySet()

        def new_lookup_bootstrap(inst, rnodes, max_nodes, overlay_bootstrap):
            return old_lookup_bootstrap(inst, rnodes, max(max_nodes, min(20, len(self.dht_nodes))), overlay_bootstrap)

        pymdht.lookup_mod._LookupQueue.__init__ = new_lookup__init__
        pymdht.lookup_mod._LookupQueue.bootstrap = new_lookup_bootstrap

        # With our edits we've broken pymdht such that it will add a node multiple times to a bucket. This causes some
        # messaging overhead. Fix this when adding to a bucket.
        old_Bucket_add = Bucket.add

        def new_Bucket_add(self, rnode):
            if self._find(rnode) == -1:
                return
            old_Bucket_add(self, rnode)

        Bucket.add = new_Bucket_add

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

            settings = sess.get_settings()
            settings["enable_lsd"] = False
            sess.set_settings(settings)

            inst.dht_ready = True
            return sess

        lt.LibtorrentMgr.do_dht_check = do_dht_check
        lt.LibtorrentMgr.create_session = create_session
