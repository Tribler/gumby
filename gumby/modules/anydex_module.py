from gumby.modules.base_ipv8_module import BaseIPv8Module
from gumby.modules.experiment_module import static_module
from gumby.modules.ipv8_community_launchers import MarketCommunityLauncher, TrustChainCommunityLauncher


@static_module
class AnyDexModule(BaseIPv8Module):
    """
    This module starts an IPv8 instance and runs AnyDex.
    """

    def create_ipv8_community_loader(self):
        loader = super().create_ipv8_community_loader()
        loader.set_launcher(TrustChainCommunityLauncher())
        loader.set_launcher(MarketCommunityLauncher())
        return loader
