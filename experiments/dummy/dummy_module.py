from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import static_module, ExperimentModule


@static_module
class DummyModule(ExperimentModule):

    @experiment_callback
    def write_peer_id(self):
        """
        Simply write my peer ID to a file.
        """
        my_peer_id = self.experiment.scenario_runner._peernumber
        with open("id.txt", "w") as id_file:
            id_file.write("%d" % my_peer_id)
