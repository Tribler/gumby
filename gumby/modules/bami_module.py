from gumby.modules.base_ipv8_module import BaseIPv8Module
from gumby.modules.experiment_module import static_module
from gumby.modules.ipv8_community_launchers import BasaltCommunityLauncher


@static_module
class BamiModule(BaseIPv8Module):
    """
    This module starts an IPv8 instance and initializes the BAMI community loaders.
    """

    def create_ipv8_community_loader(self):
        loader = super().create_ipv8_community_loader()
        loader.set_launcher(BasaltCommunityLauncher())
        return loader
