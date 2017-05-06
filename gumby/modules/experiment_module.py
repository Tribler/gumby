import logging


class ExperimentModule(object):
    """
    Base class for all loadable modules for gumby scenarios. Scenario module statements that do not refer to a
    derivative of this class are not recognized as loadable modules.
    """

    def __init__(self, experiment):
        super(ExperimentModule, self).__init__()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.info("Load experiment module %s", self.__class__.__name__)
        self.experiment = experiment
        self.experiment.register(self)

    @classmethod
    def on_module_load(cls, experiment):
        pass

    def print_dict_changes(self, name, prev_dict, cur_dict):
        return self.experiment.print_dict_changes(name, prev_dict, cur_dict)

    @property
    def my_id(self):
        return self.experiment.my_id

    @property
    def vars(self):
        return self.experiment.vars

    @property
    def all_vars(self):
        return self.experiment.all_vars

    def on_id_received(self):
        pass

    @staticmethod
    def str2bool(v):
        return v.lower() in ("yes", "true", "t", "1")


def static_module(cls):
    """
    Experiment module classes that have this decorator applied will have a singleton instance created when the module
    class is loaded by a scenario file.
    """

    original_on_module_load = cls.on_module_load

    def alt_on_module_load(_, experiment):
        original_on_module_load(experiment)
        cls._the_instance = cls(experiment)

    cls.on_module_load = alt_on_module_load.__get__(cls, cls)
    return cls
