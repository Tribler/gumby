from abc import ABCMeta, abstractmethod

from Tribler.Core.DecentralizedTracking.dht_provider import MainlineDHTProvider
from Tribler.Core.Modules.wallet.tc_wallet import TrustchainWallet
from Tribler.pyipv8.ipv8.dht.provider import DHTCommunityProvider
from Tribler.pyipv8.ipv8.peer import Peer
from Tribler.pyipv8.ipv8.peerdiscovery.discovery import RandomWalk


class CommunityLauncher(object):

    """
    Object in charge of preparing a Community for loading in Dispersy.
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

        :type overlay_provider: Tribler.dispersy.dispersy.Dispersy or Tribler.pyipv8.ipv8.IPv8
        :type session: Tribler.Core.Session.Session
        """
        pass

    def finalize(self, overlay_provider, session, community):
        """
        Perform cleanup tasks after the community has been loaded.

        :type overlay_provider: Tribler.dispersy.dispersy.Dispersy or Tribler.pyipv8.ipv8.IPv8
        :type session: Tribler.Core.Session.Session
        :type community: Tribler.dispersy.community.Community or None
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


class DispersyCommunityLauncher(CommunityLauncher):
    """
    Launcher for Dispersy communities.
    """

    def get_name(self):
        """
        Get the launcher name, for pre-launch organisation.

        :rtype: str
        """
        return self.get_community_class().__name__

    def should_load_now(self, session):
        """
        Load this class immediately, or perform init_community() later manually.

        :rtype: bool
        """
        return True

    @abstractmethod
    def get_community_class(self):
        """
        Get the Community class this launcher wants to load.

        :rtype: Tribler.dispersy.community.Community.__class__
        """
        pass

    def get_my_member(self, dispersy, session):
        """
        Get the member to load the community with.

        :rtype: Tribler.dispersy.member.Member
        """
        return session.dispersy_member


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


# Dispersy communities


class DiscoveryCommunityLauncher(DispersyCommunityLauncher):

    def get_community_class(self):
        from Tribler.dispersy.discovery.community import DiscoveryCommunity
        return DiscoveryCommunity

    def get_kwargs(self, session):
        return self.community_kwargs


class SearchCommunityLauncher(DispersyCommunityLauncher):

    def should_launch(self, session):
        return session.config.get_torrent_search_enabled()

    def get_community_class(self):
        from Tribler.community.search.community import SearchCommunity
        return SearchCommunity


class AllChannelCommunityLauncher(DispersyCommunityLauncher):

    def should_launch(self, session):
        return session.config.get_channel_search_enabled()

    def get_community_class(self):
        from Tribler.community.allchannel.community import AllChannelCommunity
        return AllChannelCommunity


class ChannelCommunityLauncher(DispersyCommunityLauncher):

    def should_launch(self, session):
        return session.config.get_channel_community_enabled()

    def get_community_class(self):
        from Tribler.community.channel.community import ChannelCommunity
        return ChannelCommunity


class PreviewChannelCommunityLauncher(DispersyCommunityLauncher):

    def should_launch(self, session):
        return session.config.get_preview_channel_community_enabled()

    def get_community_class(self):
        from Tribler.community.channel.preview import PreviewChannelCommunity
        return PreviewChannelCommunity

    def should_load_now(self, session):
        return False


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
            kwargs['dht_provider'] = DHTCommunityProvider(session.lm.dht_community, session.config.get_dispersy_port())
        else:
            kwargs['dht_provider'] = MainlineDHTProvider(session.lm.mainline_dht, session.config.get_dispersy_port())
        kwargs['bandwidth_wallet'] = TrustchainWallet(session.lm.trustchain_community)
        return kwargs

    def finalize(self, dispersy, session, community):
        super(TriblerTunnelCommunityLauncher, self).finalize(dispersy, session, community)
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

    def finalize(self, dispersy, session, community):
        super(TrustChainCommunityLauncher, self).finalize(dispersy, session, community)
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

    def finalize(self, dispersy, session, community):
        super(GigaChannelCommunityLauncher, self).finalize(dispersy, session, community)
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

    def finalize(self, dispersy, session, community):
        super(DHTCommunityLauncher, self).finalize(dispersy, session, community)
        session.lm.dht_community = community
