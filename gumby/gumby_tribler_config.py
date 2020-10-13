from tribler_core.config.tribler_config import TriblerConfig


class GumbyTriblerConfig(TriblerConfig):
    """
    This class is an extended version of the TriblerConfig.
    A subclass is necessary since we need a few settings that are only used in Gumby experiments.
    """

    def __init__(self, state_dir, config_file=None):
        super(GumbyTriblerConfig, self).__init__(state_dir, config_file=config_file)

        self.config['trustchain']['enabled'] = True
        self.config['trustchain']['memory_db'] = False

    def set_trustchain_memory_db(self, value):
        self.config['trustchain']['memory_db'] = value

    def use_trustchain_memory_db(self):
        return self.config['trustchain']['memory_db']
