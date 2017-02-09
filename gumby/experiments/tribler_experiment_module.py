from gumby.experiments.experiment_module import ExperimentModule, static_module


@static_module
class TriblerExperimentModule(ExperimentModule):
    def __init__(self, experiment):
        super(TriblerExperimentModule, self).__init__()
        self._logger.info("I got attached to experiment %s" % repr(experiment))