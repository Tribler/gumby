import time as timemod

from ipv8.loader import IPv8CommunityLoader

from tribler_core.modules.libtorrent.download_manager import DownloadManager
from tribler_core.session import Session


class GumbyTriblerSession(Session):
    """
    Overwritten Session allowing for custom community loading.
    """

    def __init__(self, config=None, ipv8_community_loader=IPv8CommunityLoader()):
        super().__init__(config)
        self.ipv8_community_loader = ipv8_community_loader

    def load_ipv8_overlays(self):
        self._logger.info("tribler: Preparing IPv8 overlays...")
        now_time = timemod.time()

        self.ipv8_community_loader.load(self.ipv8, self)

        DownloadManager.set_anon_proxy_settings(self.config,
                                                2, ("127.0.0.1", self.config.tunnel_community.socks5_listen_ports))

        self._logger.info("tribler: IPv8 overlays are ready in %.2f seconds", timemod.time() - now_time)
