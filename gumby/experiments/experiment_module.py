import logging


class ExperimentModule(object):
    def __init__(self, experiment):
        super(ExperimentModule, self).__init__()
        self._logger = logging.getLogger(self.__class__.__name__)
        experiment.experiment_modules.append(self)

    @classmethod
    def on_module_load(cls, experiment):
        pass


def static_module(cls):
    original_on_module_load = cls.on_module_load

    def alt_on_module_load(clss, experiment):
        original_on_module_load(clss, experiment)
        clss._the_instance = clss(experiment)
        experiment.register_callbacks(clss._the_instance)

    cls.on_module_load = alt_on_module_load
    return cls
