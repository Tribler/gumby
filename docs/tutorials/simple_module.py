from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import ExperimentModule


class SimpleModule(ExperimentModule):
    """
    A very simple experiment module that has a single callback.
    """

    @experiment_callback
    def write_peer_id(self):
        """
        Simply write my peer ID to a file.
        """
        with open("id.txt", "w") as id_file:
            id_file.write("%d" % self.my_id)
