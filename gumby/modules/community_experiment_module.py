from gumby.modules.experiment_module import ExperimentModule


class CommunityExperimentModule(ExperimentModule):
    def __init__(self, experiment, community_class):
        super(CommunityExperimentModule, self).__init__(experiment)
        self.community_class = community_class
        self.community_launcher.finalize_callback = self._community_finalize

    @property
    def dispersy_provider(self):
        from gumby.modules.base_dispersy_module import BaseDispersyModule

        for module in self.experiment.experiment_modules:
            if isinstance(module, BaseDispersyModule):
                return module

        self._logger.error("No dispersy provider module loaded. Load either DispersyModule or TriblerModule at the start of your scenario")
        return None

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
        return  self.community_loader.get_launcher(self.community_class.__name__)

    @property
    def community(self):
        for c in self.dispersy.get_communities():
            if isinstance(c, self.community_class):
                return c
        return None

    def _community_finalize(self, *_):
        self.on_community_loaded()

    def on_community_loaded(self):
        pass

    def set_community_launcher(self, community_launcher):
        loader = self.community_loader
        if loader is None:
            self._logger.error("Unable to set community launcher, no custom community loader is active")
        self.community_loader.set_launcher(community_launcher)