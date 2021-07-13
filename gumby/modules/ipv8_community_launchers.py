# pylint: disable=import-outside-toplevel
from ipv8.loader import CommunityLauncher, after, kwargs, overlay, precondition, set_in_session, walk_strategy
from ipv8.peer import Peer


INFINITE = -1  # The amount of target_peers for a walk_strategy definition to never stop.


class IPv8CommunityLauncher(CommunityLauncher):
    def get_my_peer(self, _, session):
        return Peer(session.trustchain_keypair)

    def get_bootstrappers(self, session):
        from ipv8.bootstrapping.dispersy.bootstrapper import DispersyBootstrapper
        from ipv8.configuration import DISPERSY_BOOTSTRAPPER
        bootstrap_override = session.config.ipv8.bootstrap_override
        if bootstrap_override:
            address, port = bootstrap_override.split(':')
            return [(DispersyBootstrapper, {"ip_addresses": [(address, int(port))],
                                            "dns_addresses": []})]
        return [(DispersyBootstrapper, DISPERSY_BOOTSTRAPPER['init'])]


# Communities
def discovery_community():
    from ipv8.peerdiscovery.community import DiscoveryCommunity
    return DiscoveryCommunity


def trustchain_community():
    from anydex.trustchain.community import TrustChainCommunity
    return TrustChainCommunity


def market_community():
    from anydex.core.community import MarketCommunity
    return MarketCommunity


def basalt_community():
    from bami.basalt.community import BasaltCommunity
    return BasaltCommunity


def dht_discovery_community():
    from ipv8.dht.discovery import DHTDiscoveryCommunity
    return DHTDiscoveryCommunity


# strategies
def random_churn():
    from ipv8.peerdiscovery.churn import RandomChurn
    return RandomChurn


def ping_churn():
    from ipv8.dht.churn import PingChurn
    return PingChurn


def random_walk():
    from ipv8.peerdiscovery.discovery import RandomWalk
    return RandomWalk


def periodic_similarity():
    from ipv8.peerdiscovery.community import PeriodicSimilarity
    return PeriodicSimilarity


@precondition('session.config.discovery_community.enabled')
@overlay(discovery_community)
@kwargs(max_peers='100')
@walk_strategy(random_churn, target_peers=INFINITE)
@walk_strategy(random_walk)
@walk_strategy(periodic_similarity, target_peers=INFINITE)
class IPv8DiscoveryCommunityLauncher(IPv8CommunityLauncher):
    pass


@precondition('session.config.trustchain.enabled')
@overlay(trustchain_community)
class TrustChainCommunityLauncher(IPv8CommunityLauncher):
    def get_kwargs(self, session):
        return {'working_directory': session.config.state_dir}

    def finalize(self, _, session, community):
        session.trustchain_community = community

        # If we're using a memory DB, replace the existing one
        if session.config.trustchain.memory_db:
            orig_db = community.persistence

            from experiments.trustchain.trustchain_mem_db import TrustchainMemoryDatabase
            community.persistence = TrustchainMemoryDatabase(session.config.state_dir, 'trustchain')
            community.persistence.original_db = orig_db

        return super()


@after('DHTCommunityLauncher', 'TrustChainCommunityLauncher')
@precondition('session.config.market.enabled')
@overlay(market_community)
class MarketCommunityLauncher(IPv8CommunityLauncher):
    def get_kwargs(self, session):
        return {
            'trustchain': session.trustchain_community,
            'dht': session.dht_community,
            'use_database': not session.config.market.memory_db,
            'working_directory': session.config.state_dir
        }


@precondition('session.config.basalt.enabled')
@overlay(basalt_community)
class BasaltCommunityLauncher(IPv8CommunityLauncher):
    pass


@precondition('session.config.dht.enabled')
@set_in_session('dht_community')
@overlay(dht_discovery_community)
@kwargs(max_peers='60')
@walk_strategy(ping_churn, target_peers=INFINITE)
@walk_strategy(random_walk)
class DHTCommunityLauncher(IPv8CommunityLauncher):
    pass
