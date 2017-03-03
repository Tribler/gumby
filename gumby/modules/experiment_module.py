import logging


class ExperimentModule(object):
    def __init__(self, experiment):
        super(ExperimentModule, self).__init__()
        self._logger = logging.getLogger(self.__class__.__name__)
        self.experiment = experiment
        experiment.experiment_modules.append(self)
        self._logger.info("Load experiment module %s", self.__class__.__name__)

    @classmethod
    def on_module_load(cls, experiment):
        pass

    def print_on_change(self, name, prev_dict, cur_dict):
        return self.experiment.print_on_change(name, prev_dict, cur_dict)

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


def static_module(cls):
    original_on_module_load = cls.on_module_load

    def alt_on_module_load(_, experiment):
        original_on_module_load(experiment)
        cls._the_instance = cls(experiment)
        experiment.register_callbacks(cls._the_instance)

    cls.on_module_load = alt_on_module_load.__get__(cls, cls)
    return cls
