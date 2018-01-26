from abc import ABCMeta, abstractmethod


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
        return self.get_community_class().__name__

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

    def prepare(self, dispersy, session):
        """
        Perform setup tasks before the community is loaded.

        :type dispersy: Tribler.dispersy.dispersy.Dispersy
        :type session: Tribler.Core.Session.Session
        """
        pass

    def finalize(self, dispersy, session, community):
        """
        Perform cleanup tasks after the community has been loaded.

        :type dispersy: Tribler.dispersy.dispersy.Dispersy
        :type session: Tribler.Core.Session.Session
        :type community: Tribler.dispersy.community.Community or None
        """
        pass

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

    def should_load_now(self, session):
        """
        Load this class immediately, or perform init_community() later manually.

        :rtype: bool
        """
        return True

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


class DiscoveryCommunityLauncher(CommunityLauncher):

    def get_community_class(self):
        from Tribler.dispersy.discovery.community import DiscoveryCommunity
        return DiscoveryCommunity

    def get_kwargs(self, session):
        return self.community_kwargs

class SearchCommunityLauncher(CommunityLauncher):

    def should_launch(self, session):
        return session.config.get_torrent_search_enabled()

    def get_community_class(self):
        from Tribler.community.search.community import SearchCommunity
        return SearchCommunity


class AllChannelCommunityLauncher(CommunityLauncher):

    def should_launch(self, session):
        return session.config.get_channel_search_enabled()

    def get_community_class(self):
        from Tribler.community.allchannel.community import AllChannelCommunity
        return AllChannelCommunity


class ChannelCommunityLauncher(CommunityLauncher):

    def should_launch(self, session):
        return session.config.get_channel_community_enabled()

    def get_community_class(self):
        from Tribler.community.channel.community import ChannelCommunity
        return ChannelCommunity


class PreviewChannelCommunityLauncher(CommunityLauncher):

    def should_launch(self, session):
        return session.config.get_preview_channel_community_enabled()

    def get_community_class(self):
        from Tribler.community.channel.preview import PreviewChannelCommunity
        return PreviewChannelCommunity

    def should_load_now(self, session):
        return False


class TunnelCommunityLauncher(CommunityLauncher):

    def should_launch(self, session):
        return session.config.get_tunnel_community_enabled() and \
               not session.config.get_tunnel_community_hidden_seeding()

    def get_community_class(self):
        from Tribler.community.tunnel.tunnel_community import TunnelCommunity
        return TunnelCommunity

    def get_my_member(self, dispersy, session):
        keypair = session.trustchain_keypair
        return dispersy.get_member(private_key=keypair.key_to_bin())

    def get_kwargs(self, session):
        from Tribler.community.tunnel.tunnel_community import TunnelSettings
        shared_args = super(TunnelCommunityLauncher, self).get_kwargs(session)
        if 'settings' not in shared_args and session is None:
            shared_args['settings'] = TunnelSettings()
        return shared_args

    def finalize(self, dispersy, session, community):
        super(TunnelCommunityLauncher, self).finalize(dispersy, session, community)
        session.lm.tunnel_community = community


class HiddenTunnelCommunityLauncher(TunnelCommunityLauncher):

    def should_launch(self, session):
        return session.config.get_tunnel_community_enabled and session.config.get_tunnel_community_hidden_seeding()

    def get_community_class(self):
        from Tribler.community.hiddentunnel.hidden_community import HiddenTunnelCommunity
        return HiddenTunnelCommunity


class TrustChainCommunityLauncher(CommunityLauncher):

    def get_community_class(self):
        from Tribler.community.trustchain.community import TrustChainCommunity
        return TrustChainCommunity

    def get_my_member(self, dispersy, session):
        keypair = session.trustchain_keypair
        return dispersy.get_member(private_key=keypair.key_to_bin())


class TriblerChainCommunityLauncher(CommunityLauncher):

    def should_launch(self, session):
        return session.config.get_trustchain_enabled()

    def get_community_class(self):
        from Tribler.community.triblerchain.community import TriblerChainCommunity
        return TriblerChainCommunity

    def get_my_member(self, dispersy, session):
        keypair = session.trustchain_keypair
        return dispersy.get_member(private_key=keypair.key_to_bin())


class MarketCommunityLauncher(CommunityLauncher):

    def should_launch(self, session):
        return session.config.get_market_community_enabled()

    def get_community_class(self):
        from Tribler.community.market.community import MarketCommunity
        return MarketCommunity

    def get_my_member(self, dispersy, session):
        keypair = session.tradechain_keypair
        return dispersy.get_member(private_key=keypair.key_to_bin())
