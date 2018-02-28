from gumby.modules.experiment_module import static_module
from gumby.modules.community_experiment_module import CommunityExperimentModule

from ipv8.peerdiscovery.deprecated.discovery import DiscoveryCommunity


@static_module
class TestModule(CommunityExperimentModule):

    def __init__(self, experiment):
        super(TestModule, self).__init__(experiment, DiscoveryCommunity)
