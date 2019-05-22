import time as timemod

from Tribler.Core.Session import Session
from Tribler.Core.APIImplementation.LaunchManyCore import TriblerLaunchMany

from gumby.modules.community_loader import IPv8CommunityLoader

from pyipv8.ipv8.util import blocking_call_on_reactor_thread


class GumbyLaunchMany(TriblerLaunchMany):
    """
    Overwritten TriblerLaunchMany allowing for custom community loading.
    """

    def __init__(self, ipv8_community_loader=IPv8CommunityLoader()):
        super(GumbyLaunchMany, self).__init__()
        self.ipv8_community_loader = ipv8_community_loader

    @blocking_call_on_reactor_thread
    def load_ipv8_overlays(self):
        self._logger.info("tribler: Preparing IPv8 overlays...")
        now_time = timemod.time()

        self.ipv8_community_loader.load(self.ipv8, self.session)

        self.session.config.set_anon_proxy_settings(2,
                                                    ("127.0.0.1",
                                                     self.session.config.get_tunnel_community_socks5_listen_ports()))

        self._logger.info("tribler: IPv8 overlays are ready in %.2f seconds", timemod.time() - now_time)


class GumbySession(Session):

    """
    Overwritten Session allowing for custom community loading in Session.lm.
    """

    def __init__(self, config=None, autoload_discovery=True):
        super(GumbySession, self).__init__(config, autoload_discovery)
        self.lm = GumbyLaunchMany()
