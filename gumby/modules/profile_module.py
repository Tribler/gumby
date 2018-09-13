"""
This module provides profiling utilities during experiments. For now, we only support the yappi profiler.
"""
import yappi

from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import static_module, ExperimentModule


@static_module
class ProfileModule(ExperimentModule):

    @experiment_callback
    def start_yappi(self):
        """
        Start the yappi profiler.
        """
        yappi.start(builtins=True)

    @experiment_callback
    def stop_yappi(self):
        """
        Stop yappi and write the stats to the output directory.
        """
        yappi.stop()

        yappi_stats = yappi.get_func_stats()
        yappi_stats.sort("tsub")

        yappi_stats.save('yappi.stats', type='callgrind')
