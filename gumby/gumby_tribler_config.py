from tribler_core.config.tribler_config import TriblerConfig


class GumbyTriblerConfig(TriblerConfig):
    """
    This class is an extended version of the TriblerConfig.
    A subclass is necessary since we need a few settings that are only used in Gumby experiments.
    """

    def __init__(self, config=None):
        super(GumbyTriblerConfig, self).__init__(config=config)

        self.config['trustchain']['enabled'] = True
        self.config['trustchain']['memory_db'] = False
        self.config['ipv8']['discovery'] = False

    def set_ipv8_discovery(self, value):
        self.config['ipv8']['discovery'] = value

    def get_ipv8_discovery(self):
        return self.config['ipv8']['discovery']

    def set_trustchain_memory_db(self, value):
        self.config['trustchain']['memory_db'] = value

    def use_trustchain_memory_db(self):
        return self.config['trustchain']['memory_db']
