from gumby.modules.base_dispersy_module import BaseDispersyModule
from gumby.modules.experiment_module import ExperimentModule


class CommunityExperimentModule(ExperimentModule):
    """
    Base class for experiment modules that provide gumby scenario control over a single dispersy community.
    """

    def __init__(self, experiment, community_class):
        super(CommunityExperimentModule, self).__init__(experiment)
        self.community_class = community_class
        self.community_launcher.finalize_callback = self._community_finalize

    @property
    def dispersy_provider(self):
        """
        Gets an experiment module from the loaded experiment modules that inherits from BaseDispersyModule. It can be
        used as the source for the dispersy instance, session, session config and custom community loader.
        :return: An instance of BaseDispersyModule that was loaded into the experiment.
        """
        for module in self.experiment.experiment_modules:
            if isinstance(module, BaseDispersyModule):
                return module

        raise Exception("No dispersy provider module loaded. Load either DispersyModule or TriblerModule at the "
                        "start of your scenario")

    @property
    def dispersy(self):
        return self.dispersy_provider.dispersy

    @property
    def session(self):
        return self.dispersy_provider.session

    @property
    def session_config(self):
        return self.dispersy_provider.session_config

    @property
    def community_loader(self):
        return self.dispersy_provider.custom_community_loader

    @property
    def community_launcher(self):
        return self.community_loader.get_launcher(self.community_class.__name__)

    @property
    def community(self):
        #TODO: implement MultiCommunityExperimentModule.
        # If there are multiple instances of a community class there are basically 2 approaches to solving this. One
        # is to derive from CommunityExperimentModule and override this community property, then each instance of the
        # community class can get accessed by index or some such. All @experiment_callbacks in this case would require a
        # number/name argument to indicate what community to work on. An alternative approach would be to instance a
        # CommunityExperimentModule for each instance of the community_class. However it would be difficult to separate
        # the scenario usage of its @experiment_callbacks, they would have to be dynamically named/generated.
        for community in self.dispersy.get_communities():
            if isinstance(community, self.community_class):
                return community
        return None

    def _community_finalize(self, *_):
        self.on_community_loaded()

    def on_community_loaded(self):
        pass

    def set_community_launcher(self, community_launcher):
        if self.community_loader is None:
            self._logger.error("Unable to set community launcher, no custom community loader is active")
        self.community_loader.set_launcher(community_launcher)
        self.community_launcher.finalize_callback = self._community_finalize
