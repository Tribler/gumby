# pylint: disable=import-outside-toplevel
from ipv8.loader import after, overlay, precondition, set_in_session, walk_strategy

from gumby.modules.ipv8_community_launchers import INFINITE, IPv8CommunityLauncher, random_walk


# Communities
def tribler_tunnel_community():
    from tribler.core.components.tunnel.community.tunnel_community import TriblerTunnelCommunity
    return TriblerTunnelCommunity


def bandwidth_accounting_community():
    from tribler.core.components.bandwidth_accounting.community.bandwidth_accounting_community import \
        BandwidthAccountingCommunity
    return BandwidthAccountingCommunity


def popularity_community():
    from tribler.core.components.popularity.community.popularity_community import PopularityCommunity
    return PopularityCommunity


def giga_channel_community():
    from tribler.core.components.gigachannel.community.gigachannel_community import GigaChannelCommunity
    return GigaChannelCommunity


# Strategies
def golden_ratio_strategy():
    from tribler.core.components.tunnel.community.discovery import GoldenRatioStrategy
    return GoldenRatioStrategy


def remove_peers():
    from tribler.core.components.gigachannel.community.sync_strategy import RemovePeers
    return RemovePeers


@overlay(bandwidth_accounting_community)
@walk_strategy(random_walk)
@set_in_session('bandwidth_community')
class BandwidthCommunityLauncher(IPv8CommunityLauncher):
    def get_kwargs(self, session):
        return {
            'settings': session.config.bandwidth_accounting,
            'database_path': session.config.state_dir / "sqlite" / "bandwidth.db",
        }


@after('DHTCommunityLauncher', 'BandwidthCommunityLauncher')
@precondition('session.config.tunnel_community.enabled')
@set_in_session('tunnel_community')
@overlay(tribler_tunnel_community)
@walk_strategy(random_walk)
@walk_strategy(golden_ratio_strategy, target_peers=INFINITE)
class TriblerTunnelCommunityLauncher(IPv8CommunityLauncher):
    def get_kwargs(self, session):
        from ipv8.dht.provider import DHTCommunityProvider
        from ipv8.messaging.anonymization.community import TunnelSettings

        settings = TunnelSettings()
        settings.min_circuits = session.config.tunnel_community.min_circuits
        settings.max_circuits = session.config.tunnel_community.max_circuits

        return {
            'bandwidth_community': session.bandwidth_community,
            'competing_slots': session.config.tunnel_community.competing_slots,
            'ipv8': session.ipv8,
            'random_slots': session.config.tunnel_community.random_slots,
            'tribler_session': session,
            'dht_provider': DHTCommunityProvider(session.dht_community, session.config.ipv8.port),
            'settings': settings
        }


@precondition('session.config.popularity_community.enabled')
@set_in_session('popularity_community')
@overlay(popularity_community)
@walk_strategy(random_walk, target_peers=30)
@walk_strategy(remove_peers, target_peers=INFINITE)
class PopularityCommunityLauncher(IPv8CommunityLauncher):
    def get_kwargs(self, session):
        return {
            'settings': session.config.popularity_community,
            'rqc_settings': session.config.remote_query_community,

            'metadata_store': session.mds,
            'torrent_checker': session.torrent_checker,
        }


@overlay(giga_channel_community)
@precondition('session.config.chant.enabled')
@set_in_session('gigachannel_community')
@overlay(giga_channel_community)
# GigaChannelCommunity remote search feature works better with higher amount of connected peers
@walk_strategy(random_walk, target_peers=30)
@walk_strategy(remove_peers, target_peers=INFINITE)
class GigaChannelCommunityLauncher(IPv8CommunityLauncher):
    def get_kwargs(self, session):
        return {
            'settings': session.config.chant,
            'rqc_settings': session.config.remote_query_community,

            'metadata_store': session.mds,
            'notifier': session.notifier,
            'max_peers': 50,
        }
