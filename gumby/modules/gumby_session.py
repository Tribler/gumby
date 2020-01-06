import time as timemod

from tribler_core.session import Session

from gumby.modules.community_loader import IPv8CommunityLoader


class GumbySession(Session):
    """
    Overwritten Session allowing for custom community loading.
    """

    def __init__(self, config=None, ipv8_community_loader=IPv8CommunityLoader()):
        super(GumbySession, self).__init__(config)
        self.ipv8_community_loader = ipv8_community_loader

    def load_ipv8_overlays(self):
        self._logger.info("tribler: Preparing IPv8 overlays...")
        now_time = timemod.time()

        self.ipv8_community_loader.load(self.ipv8, self)

        self.config.set_anon_proxy_settings(2,
                                            ("127.0.0.1",
                                             self.config.get_tunnel_community_socks5_listen_ports()))

        self._logger.info("tribler: IPv8 overlays are ready in %.2f seconds", timemod.time() - now_time)
