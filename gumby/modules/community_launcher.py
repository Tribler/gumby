from abc import ABCMeta, abstractmethod

from Tribler.Core.Modules.wallet.tc_wallet import TrustchainWallet
from Tribler.pyipv8.ipv8.dht.provider import DHTCommunityProvider
from Tribler.pyipv8.ipv8.peer import Peer
from Tribler.pyipv8.ipv8.peerdiscovery.discovery import RandomWalk


class CommunityLauncher(object):

    """
    Object in charge of preparing a Community for loading in IPv8.
    """

    __metaclass__ = ABCMeta

    def __init__(self):
        super(CommunityLauncher, self).__init__()
        self.community_args = []
        self.community_kwargs = {}

    def get_name(self):
        """
        Get the launcher name, for pre-launch organisation.

        :rtype: str
        """
        return None

    def not_before(self):
        """
        Should not launch this before some other launcher has completed.

        :return: The list of launcher names to complete before this is launched
        """
        return []

    def should_launch(self, session):
        """
        Check whether this launcher should launch.

        For example:

            return session.config.get_tunnel_community_enabled()

        :type session: Tribler.Core.Session.Session
        :rtype: bool
        """
        return True

    def prepare(self, overlay_provider, session):
        """
        Perform setup tasks before the community is loaded.

        :type overlay_provider: Tribler.pyipv8.ipv8.IPv8
        :type session: Tribler.Core.Session.Session
        """
        pass

    def finalize(self, overlay_provider, session, community):
        """
        Perform cleanup tasks after the community has been loaded.

        :type overlay_provider: Tribler.pyipv8.ipv8.IPv8
        :type session: Tribler.Core.Session.Session
        :type community: IPv8 community
        """
        pass

    def get_args(self, session):
        """
        Get the args to load the community with.

        :rtype: tuple
        """
        return self.community_args

    def get_kwargs(self, session):
        """
        Get the kwargs to load the community with.

        :rtype: dict or None
        """
        ret = {'tribler_session': session}
        ret.update(self.community_kwargs)
        return ret


class IPv8CommunityLauncher(CommunityLauncher):
    """
    Launcher for IPv8 communities.
    """

    def get_name(self):
        """
        Get the launcher name, for pre-launch organisation.

        :rtype: str
        """
        return self.get_overlay_class().__name__

    @abstractmethod
    def get_overlay_class(self):
        """
        Get the overlay class this launcher wants to load.

        :rtype: Tribler.pyipv8.ipv8.overlay.Overlay
        """
        pass

    @abstractmethod
    def get_my_peer(self, ipv8, session):
        """
        Get the peer to load the community with.
        """
        pass

    def get_walk_strategies(self):
        """
        Get walk strategies for this class.
        It should be provided as a list of tuples with the class, kwargs and maximum number of peers.
        """
        return []


# IPv8 communities

class IPv8DiscoveryCommunityLauncher(IPv8CommunityLauncher):

    def get_overlay_class(self):
        from Tribler.pyipv8.ipv8.peerdiscovery.community import DiscoveryCommunity
        return DiscoveryCommunity

    def should_launch(self, session):
        return session.config.get_ipv8_discovery()

    def get_my_peer(self, ipv8, session):
        return Peer(session.trustchain_keypair)

    def get_kwargs(self, session):
        return {}

    def get_walk_strategies(self):
        return [(RandomWalk, {'timeout': 1.0}, -1)]


class TriblerTunnelCommunityLauncher(IPv8CommunityLauncher):

    def not_before(self):
        return ['DHTDiscoveryCommunity', 'TrustChainCommunity']

    def should_launch(self, session):
        return session.config.get_tunnel_community_enabled()

    def get_overlay_class(self):
        from Tribler.community.triblertunnel.community import TriblerTunnelCommunity
        return TriblerTunnelCommunity

    def get_my_peer(self, ipv8, session):
        return Peer(session.trustchain_keypair)

    def get_kwargs(self, session):
        kwargs = super(TriblerTunnelCommunityLauncher, self).get_kwargs(session)
        if session.config.get_dht_enabled():
            kwargs['dht_provider'] = DHTCommunityProvider(session.lm.dht_community, session.config.get_ipv8_port())
        kwargs['bandwidth_wallet'] = TrustchainWallet(session.lm.trustchain_community)
        return kwargs

    def finalize(self, ipv8, session, community):
        super(TriblerTunnelCommunityLauncher, self).finalize(ipv8, session, community)
        session.lm.tunnel_community = community


class TrustChainCommunityLauncher(IPv8CommunityLauncher):

    def should_launch(self, session):
        return session.config.get_trustchain_enabled()

    def get_overlay_class(self):
        from Tribler.pyipv8.ipv8.attestation.trustchain.community import TrustChainCommunity
        return TrustChainCommunity

    def get_my_peer(self, ipv8, session):
        return Peer(session.trustchain_keypair)

    def get_kwargs(self, session):
        return {'working_directory': session.config.get_state_dir()}

    def finalize(self, ipv8, session, community):
        super(TrustChainCommunityLauncher, self).finalize(ipv8, session, community)
        session.lm.trustchain_community = community

        # If we're using a memory DB, replace the existing one
        if session.config.use_trustchain_memory_db():
            orig_db = community.persistence

            from experiments.trustchain.trustchain_mem_db import TrustchainMemoryDatabase
            community.persistence = TrustchainMemoryDatabase(session.config.get_state_dir(), 'trustchain')
            community.persistence.original_db = orig_db


class MarketCommunityLauncher(IPv8CommunityLauncher):

    def not_before(self):
        return ['DHTDiscoveryCommunity', 'TrustChainCommunity']

    def should_launch(self, session):
        return session.config.get_market_community_enabled()

    def get_overlay_class(self):
        from Tribler.community.market.community import MarketCommunity
        return MarketCommunity

    def get_my_peer(self, ipv8, session):
        return Peer(session.trustchain_keypair)

    def get_kwargs(self, session):
        kwargs = super(MarketCommunityLauncher, self).get_kwargs(session)
        kwargs['trustchain'] = session.lm.trustchain_community
        kwargs['dht'] = session.lm.dht_community
        return kwargs


class GigaChannelCommunityLauncher(IPv8CommunityLauncher):

    def not_before(self):
        return ['TrustChainCommunity']

    def should_launch(self, session):
        return session.config.get_chant_enabled()

    def get_overlay_class(self):
        from Tribler.community.gigachannel.community import GigaChannelCommunity
        return GigaChannelCommunity

    def get_my_peer(self, ipv8, session):
        return Peer(session.trustchain_keypair)

    def finalize(self, ipv8, session, community):
        super(GigaChannelCommunityLauncher, self).finalize(ipv8, session, community)
        session.lm.gigachannel_community = community


class DHTCommunityLauncher(IPv8CommunityLauncher):

    def should_launch(self, session):
        return session.config.get_dht_enabled()

    def get_overlay_class(self):
        from Tribler.pyipv8.ipv8.dht.discovery import DHTDiscoveryCommunity
        return DHTDiscoveryCommunity

    def get_my_peer(self, ipv8, session):
        return Peer(session.trustchain_keypair)

    def get_kwargs(self, session):
        return {}

    def finalize(self, ipv8, session, community):
        super(DHTCommunityLauncher, self).finalize(ipv8, session, community)
        session.lm.dht_community = community
