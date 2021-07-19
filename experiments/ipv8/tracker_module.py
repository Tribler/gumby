import os
import subprocess

import ipv8

from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import ExperimentModule, static_module


@static_module
class TrackerModule(ExperimentModule):
    """
    This module contains code to manage the discovery community in IPv8.
    """

    def __init__(self, experiment):
        super().__init__(experiment)
        self.tracker_process = None

    @experiment_callback
    def start_tracker(self, port=50000):
        self._logger.info("Starting IPv8 tracker on port %d", int(port))

        ipv8_dir = os.path.join(os.path.dirname(ipv8.__file__), "..")
        tracker_plugin_path = os.path.join(ipv8_dir, "scripts", "tracker_plugin.py")
        cmd = "python3 %s --listen_port %d" % (tracker_plugin_path, int(port))
        self._logger.info("Tracker command: %s", cmd)
        self.tracker_process = subprocess.Popen(cmd.split(" "), stderr=subprocess.PIPE, stdout=subprocess.PIPE)

    @experiment_callback
    def stop_tracker(self):
        if self.tracker_process:
            self._logger.info("Stopping tracker")
            self.tracker_process.kill()
