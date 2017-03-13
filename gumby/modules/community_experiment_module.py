from gumby.modules.base_dispersy_module import BaseDispersyModule
from gumby.modules.experiment_module import ExperimentModule


class CommunityExperimentModule(ExperimentModule):
    """
    Base class for experiment modules that provide gumby scenario control over a single dispersy community.
    """

    def __init__(self, experiment, community_class):
        super(CommunityExperimentModule, self).__init__(experiment)
        self.community_class = community_class

        # To be sure that the module loading happens in the right order, this next line serves the dual purpose of
        # triggering the check for a loaded dispersy provider
        self.dispersy_provider.dispersy_available.addCallback(self.on_dispersy_available)

    @property
    def dispersy_provider(self):
        """
        Gets an experiment module from the loaded experiment modules that inherits from BaseDispersyModule. It can be
        used as the source for the dispersy instance, session, session config and custom community loader.
        :return: An instance of BaseDispersyModule that was loaded into the experiment.
        """
        ret = BaseDispersyModule.get_dispery_provider(self.experiment)
        if ret:
            return ret

        raise Exception("No dispersy provider module loaded. Load an implementation of BaseDispersyModule ("
                        "DispersyModule or TriblerModule) before loading the %s module", self.__class__.__name__)

    @property
    def dispersy(self):
        return self.dispersy_provider.dispersy

    @property
    def session(self):
        return self.dispersy_provider.session

    @property
    def session_config(self):
        # The session config only exists after on_id_received up to session start. The session start copy constructs all
        # settings so writing to the original session_config after this will not do anything. So on any access to the
        # session_config after the session has launched, return the session. It acts as a session_config as well and
        # alerts the user if some setting cannot be changed at runtime.
        if self.dispersy_provider.session_config is None:
            return self.session
        else:
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

    def on_dispersy_available(self, dispersy):
        pass