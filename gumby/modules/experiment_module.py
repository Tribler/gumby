import logging
import os
import time


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
        self.has_ipv8 = False  # Whether this module provides an instance of IPv8

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

    def autoplot_create(self, statistic_name, column_name=None):
        """
        Create a new plot directive for a certain statistic. Call this function before `autoplot_add_point`.

        :param statistic_name: the name of the statistic (this will also be the file name)
        :type statistic_name: str
        :param column_name: the name of the statistic in the plot (or None to use the file name)
        :type column_name: str or None
        :returns: None
        """
        with open('autoplot.txt', 'a') as output_file:
            output_file.write('%s.csv\n' % statistic_name)
        if not os.path.isdir('autoplot'):
            os.mkdir('autoplot')
        with open('autoplot/%s.csv' % statistic_name, 'w') as output_file:
            output_file.write('time,pid,%s\n' % (column_name or statistic_name))

    def autoplot_add_point(self, statistic_name, value):
        """
        Add a new point to our autoplot directive for a certain statistic.
        Make sure that `autoplot_create` was previously called.

        :param statistic_name: the name of the statistic (this will also be the file name)
        :type statistic_name: str
        :param value: the value to add to the plot
        :type value: int or long or float
        :returns: None
        """
        with open('autoplot/%s.csv' % statistic_name, 'a') as output_file:
            output_file.write("%f,%d,%d\n" % (time.time(), self.my_id, value))

    def on_id_received(self):
        """
        The experiment node has been assigned it's ID. After all the handlers for this event are completed the Vars
        dictionary is sent to the experiment server.
        """
        pass

    def on_all_vars_received(self):
        """
        The experiment server has sent us all the vars dictionaries of all the experiment nodes.
        """
        pass

    @staticmethod
    def str2bool(v):
        return v.lower() in ("yes", "true", "t", "1")

    @staticmethod
    def get_dir_size(path='.'):
        """
        Get the recursive directory size.
        """
        total_size = 0
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                # skip if it is symbolic link
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)

        return total_size
