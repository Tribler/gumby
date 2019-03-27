import time

from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import static_module

from gumby.modules.community_experiment_module import ExperimentModule


@static_module
class ForLoopTestModule(ExperimentModule):
    """
    This module introduces some methods which can prove useful in testing the for loop
    """

    def __init__(self, experiment):
        super(ForLoopTestModule, self).__init__(experiment)
        self.start_time = 0

        # A dictionary in case during testing we'd like to store some value for later retrieval
        self.local_storage = {}

    def on_id_received(self):
        self.start_time = time.time()

    @experiment_callback
    def write_to_logger(self, message):
        """
        Write to the local logger a message

        :param message: the message to be written by the logger
        :return:
        """
        self._log_with_timestamp(message)

    @experiment_callback
    def test(self, val, vval=None, cst=None):
        """
        This method can be used to check that the parameters of a method call are successfully passed

        :param val: an unnamed parameter, which can be used to check that unnamed parameters receive their values
                    correctly
        :param vval: the first of the two named parameters, which can be used to check that named parameters receive
                     their values correctly
        :param cst: the second of the two named parameters, which can be used to check that the named parameters receive
                    their values correctly
        """
        self._log_with_timestamp("Unnamed argument: %s; Named arguments: vval=%s, cst=%s", val, vval, cst)

    @experiment_callback
    def store(self, key, val):
        """
        Stores a (key, value) pair in the local storage. The changes made to local storage are not visible to other
        peers

        :param key: the entry's key
        :param val: the entry's value
        """
        self.local_storage[key] = val
        self._log_with_timestamp("Stored the %s --> %s pair", key, val)

    @experiment_callback
    def find(self, key):
        """
        Find value associated to a key, if it exists

        :param key: the key whose value we are searching for
        """
        if key in self.local_storage:
            self._log_with_timestamp("Found the value for %s: %s", key, self.local_storage[key])
        else:
            self._log_with_timestamp("No value found under the key %s", key)

    def _log_with_timestamp(self, message, *args):
        """
        Write to the module logger, and also add the experiment timestamp to the message

        :param message: the message to be written to the log
        :param args: the formatting parameters of the logged message
        """
        timestamp = time.time() - self.start_time
        self._logger.info("@ %s: " + message, timestamp, *args)
