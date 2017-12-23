from os import path
from twisted.internet.task import LoopingCall

from gumby.experiment import experiment_callback
from gumby.modules.base_dispersy_module import BaseDispersyModule
from gumby.modules.community_launcher import DiscoveryCommunityLauncher
from gumby.modules.experiment_module import static_module

try:
    from ipv8.taskmanager import TaskManager
except ImportError:
    # If ipv8 is not being used, don't try to load it.
    # Allow the IPV8 class to be created for launcher logic though.
    TaskManager = object

from Tribler.Core import permid


class IPV8(TaskManager):

    def __init__(self, port, walker_interval=0.5):
        from ipv8.messaging.interfaces.udp.endpoint import UDPEndpoint
        from ipv8.peerdiscovery.network import Network

        super(IPV8, self).__init__()
        self.endpoint = UDPEndpoint(port)
        self.network = Network()

        self.keys = {}
        self.strategies = []
        self.overlays = []

        self.state_machine_lc = self.register_task("IPv8 Main Loop",
                                                   LoopingCall(self.on_tick)).start(walker_interval, False)

    def start(self):
        self.endpoint.open()

    def stop(self):
        for overlay in self.overlays:
            overlay.unload()
        self.cancel_all_pending_tasks()
        self.endpoint.close()

    def get_member(self, mid="", public_key="", private_key=""):
        """
        Boilerplate code for Dispersy.get_member() using IPv8.
        """
        from ipv8.keyvault.crypto import ECCrypto
        from ipv8.peer import Peer

        if mid:
            for p in self.network.verified_peers[:]:
                if p.mid == mid:
                    return p
            return None
        elif private_key:
            public_key = ECCrypto().key_from_private_bin(private_key).pub().key_to_bin()
        key = ECCrypto().key_from_public_bin(public_key)
        mid = ECCrypto().key_to_hash(key)
        for p in self.network.verified_peers[:]:
            if p.mid == mid:
                return p
        return Peer(key)

    def get_new_member(self):
        """
        Boilerplate code for Dispersy.get_new_member() using IPv8.
        """
        from ipv8.keyvault.crypto import ECCrypto
        from ipv8.peer import Peer

        return Peer(ECCrypto().generate_key(u"medium"), ("127.0.0.1", self.endpoint._port))

    def define_auto_load(self, community_cls, my_member, args=(), kargs=None, load=False):
        """
        Boilerplate code for Dispersy.define_auto_load() using IPv8.
        """
        if kargs is None:
            kargs = {}

        communities = []
        if load:
            from ipv8.overlay import Overlay
            if not issubclass(community_cls, Overlay):

                return []
            community = community_cls(my_member, endpoint=self.endpoint, network=self.network, *args, **kargs)
            communities.append(community)
            self.overlays.append(community)

        return communities

    def on_tick(self):
        if self.endpoint.is_open():
            if not self.network.get_walkable_addresses():
                for strategy, _ in self.strategies:
                    overlay = strategy.overlay
                    if hasattr(overlay, 'bootstrap') and callable(overlay.bootstrap):
                        overlay.bootstrap()
            else:
                for strategy, target_peers in self.strategies:
                    service = strategy.overlay.master_peer.mid
                    peer_count = len(self.network.get_peers_for_service(service))
                    if (target_peers == -1) or (peer_count < target_peers):
                        strategy.take_step(service)



@static_module
class IPv8Module(BaseDispersyModule):

    def __init__(self, experiment):
        from ipv8.keyvault.crypto import ECCrypto

        super(IPv8Module, self).__init__(experiment)
        self.crypto = ECCrypto()
        self.custom_community_loader.set_launcher(DiscoveryCommunityLauncher())
        self.ipv8 = None

    @experiment_callback
    def start_session(self):
        from ipv8.keyvault.private.libnacl import LibNaCLSK
        from ipv8.peer import Peer

        super(IPv8Module, self).start_session()

        self._logger.info("Starting ipv8")
        self.ipv8 = IPV8(self.session.config.get_dispersy_port())
        self.ipv8.start()

        pairfilename = self.session.config.get_permid_keypair_filename()
        if not path.exists(pairfilename):
            keypair = permid.generate_keypair()
            permid.save_keypair(keypair, pairfilename)
            permid.save_pub_key(keypair, "%s.pub" % pairfilename)

        keyfile_content = ""
        with open(pairfilename, 'r') as f:
            keyfile_content = f.read()
        self.session.dispersy_member = Peer(LibNaCLSK(keyfile_content),
                                            ("127.0.0.1", self.session.config.get_dispersy_port()))

        self.custom_community_loader.load(self.ipv8, self.session)
        self.session.config.set_anon_proxy_settings(2, ("127.0.0.1",
                                                        self.session.config.get_tunnel_community_socks5_listen_ports()))

        self._logger.info("Finished starting ipv8")
        self.dispersy_available.callback(self.ipv8)

    @experiment_callback
    def stop_session(self):
        self.ipv8.stop()

    def setup_config(self):
        """
        Disable all default communities, as none of them run on IPv8.
        """
        config = super(IPv8Module, self).setup_config()
        config.set_dispersy_enabled(False)
        config.set_torrent_search_enabled(False)
        config.set_channel_search_enabled(False)
        config.set_channel_community_enabled(False)
        config.set_preview_channel_community_enabled(False)
        config.set_tunnel_community_enabled(False)
        config.set_trustchain_enabled(False)
        config.set_market_community_enabled(False)
        return config
