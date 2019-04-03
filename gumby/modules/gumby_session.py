import logging
import time as timemod

from gumby.modules.community_launcher import *

from Tribler.Core.Session import Session
from Tribler.Core.APIImplementation.LaunchManyCore import TriblerLaunchMany
from Tribler.pyipv8.ipv8.util import blocking_call_on_reactor_thread


class CommunityLoader(object):

    """
    Object in charge of loading communities into IPv8.
    """

    def __init__(self):
        self.community_launchers = {}
        self._logger = logging.getLogger(self.__class__.__name__)

    def get_launcher(self, name):
        return self.community_launchers[name][0]

    def has_launched(self, name):
        return self.community_launchers[name][1]

    def set_launcher(self, launcher):
        """
        Register a launcher to be launched by name.

        If a launcher for the same name already existed, it is overwritten.

        :type launcher: CommunityLauncher
        """
        assert isinstance(launcher, CommunityLauncher)

        if launcher.get_name() in self.community_launchers:
            self._logger.info("Overriding CommunityLauncher %s", launcher.get_name())
            if self.has_launched(launcher.get_name()):
                self._logger.error("Unable to replace launcher for %s, it was already launched", launcher.get_name())
                return

        self.community_launchers[launcher.get_name()] = (launcher, False)

    def del_launcher(self, launcher):
        """
        Unregister a launcher

        :type launcher: CommunityLauncher
        """
        assert isinstance(launcher, CommunityLauncher)

        if launcher.get_name() in self.community_launchers:
            del self.community_launchers[launcher.get_name()]

    def load(self, overlay_provider, session):
        """
        Load all of the communities specified by the registered launchers into IPv8.
        """
        remaining = [launcher for launcher, _ in self.community_launchers.values()]
        cycle = len(remaining)*len(remaining)
        while remaining and cycle >= 0:
            launcher = remaining.pop(0)
            cycle -= 1
            if launcher.should_launch(session):
                validated = True
                for dependency in launcher.not_before():
                    # If the dependency does not exist, don't wait for it
                    # If the dependency is never loaded, don't wait for it
                    if dependency in self.community_launchers and \
                            self.community_launchers[dependency][0].should_launch(session):
                        validated = validated and self.has_launched(dependency)
                if validated:
                    self._launch(launcher, overlay_provider, session)
                else:
                    remaining.append(launcher)
        if cycle < 0:
            launcher_names = [launcher.get_name() for launcher in remaining]
            raise RuntimeError("Cycle detected in CommunityLauncher not_before(): %s" % (str(launcher_names)))

    def _launch(self, launcher, ipv8, session):
        """
        This method should be overridden.
        """
        pass


class IPv8CommunityLoader(CommunityLoader):
    """
    Loader for IPv8 communities.
    """

    def __init__(self):
        super(IPv8CommunityLoader, self).__init__()
        self.set_launcher(IPv8DiscoveryCommunityLauncher())
        self.set_launcher(TrustChainCommunityLauncher())
        self.set_launcher(TriblerTunnelCommunityLauncher())
        self.set_launcher(MarketCommunityLauncher())
        self.set_launcher(PopularityCommunityLauncher())
        self.set_launcher(DHTCommunityLauncher())
        self.set_launcher(GigaChannelCommunityLauncher())

    def _launch(self, launcher, ipv8, session):
        """
        Launch a launcher: register the overlay with IPv8.
        """
        # Prepare launcher
        launcher.prepare(ipv8, session)
        # Register community
        overlay_class = launcher.get_overlay_class()
        self._logger.info("Loading overlay %s", overlay_class)
        walk_strategies = launcher.get_walk_strategies()
        peer = launcher.get_my_peer(ipv8, session)
        args = launcher.get_args(session)
        kwargs = launcher.get_kwargs(session)
        overlay = overlay_class(peer, ipv8.endpoint, ipv8.network, *args, **kwargs)

        ipv8.overlays.append(overlay)
        for strategy_class, strategy_kwargs, max_peers in walk_strategies:
            ipv8.strategies.append((strategy_class(overlay, **strategy_kwargs), max_peers))

        # Cleanup
        launcher.finalize(ipv8, session, overlay)
        self.community_launchers[launcher.get_name()] = (launcher, True)

        # Enable community statistics if applicable
        if session.config.get_ipv8_statistics():
            ipv8.endpoint.enable_community_statistics(overlay.get_prefix(), True)


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
