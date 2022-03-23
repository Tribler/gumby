from tribler_core.config.tribler_config import TriblerConfig
from tribler_core.modules.settings import TrustchainSettings


class GumbyTrustchainSettings(TrustchainSettings):
    enabled: bool = True
    memory_db: bool = False


class GumbyTriblerConfig(TriblerConfig):
    """
    This class is an extended version of the TriblerConfig.
    A subclass is necessary since we need a few settings that are only used in Gumby experiments.
    """
    trustchain: GumbyTrustchainSettings = GumbyTrustchainSettings()
