import os
import time
from sys import getsizeof

from twisted.internet.task import LoopingCall

from gumby.experiment import experiment_callback
from gumby.modules.community_experiment_module import IPv8OverlayExperimentModule
from gumby.modules.experiment_module import static_module

from Tribler.pyipv8.ipv8.dht.discovery import DHTDiscoveryCommunity


@static_module
class DHTModule(IPv8OverlayExperimentModule):
    """
    This module contains code to manage experiments with the DHT community.
    """

    def __init__(self, experiment):
        super(DHTModule, self).__init__(experiment, DHTDiscoveryCommunity)
        self.start_time = 0

        self.callbacks = {}

    def on_id_received(self):
        super(DHTModule, self).on_id_received()
        self.tribler_config.set_dht_enabled(True)

        with open('autoplot.txt', 'a') as output_file:
            output_file.write('storage_size.csv\n')
        os.mkdir('autoplot')
        with open('autoplot/storage_size.csv', 'w') as output_file:
            output_file.write('time,pid,storage_size_bytes\n')

        self.start_time = time.time()

    def on_ipv8_available(self, _):
        # Disable threadpool messages
        self.overlay._use_main_thread = True

    @experiment_callback
    def trigger_dht_size_measure(self, sample_period=1.0):
        """
        Trigger the measurement of the local DHT storage size

        :param sample_period: the interval between samples
        :return: None
        """
        assert sample_period > 0.0, "The sample period must be greater than 0."

        sample_period = float(sample_period)
        self.callbacks['dht_storage_measurement'] = LoopingCall(self.record_storage_size)
        self.callbacks['dht_storage_measurement'].start(sample_period, False)

    @experiment_callback
    def terminate_dht_size_measure(self):
        """
        Terminate the measurement of the local DHT storage size
        """
        self.callbacks['dht_storage_measurement'].stop()

    @experiment_callback
    def introduce_peers_dht(self):
        for peer_id in self.all_vars.iterkeys():
            if int(peer_id) != self.my_id:
                self.overlay.walk_to(self.experiment.get_peer_ip_port_by_id(peer_id))

    @experiment_callback
    def store(self, key, value):
        self.log_timing(self.overlay.store_value(key.decode('hex'), value), 'store')

    @experiment_callback
    def find(self, key):
        self.log_timing(self.overlay.find_values(key.decode('hex')), 'find')

    @experiment_callback
    def do_dht_announce(self):
        def on_peer_stored(nodes):
            self._logger.info("Stored this peer on %d nodes", len(nodes))

        def on_peer_store_error(failure):
            self._logger.error("Error when storing peer: %s", failure)

        self.overlay.store_peer().addCallbacks(on_peer_stored, on_peer_store_error)

    def record_storage_size(self):
        """
        Compute the size of the storage in the DHTOverlay

        :return: None
        """
        time_stamp = time.time()
        total_storage_size = 0

        for key in self.overlay.storage.items:
            for item in self.overlay.storage.get(key):
                total_storage_size += getsizeof(item)

        with open('autoplot/storage_size.csv', 'a') as output_file:
            output_file.write("%f,%d,%d\n" % (time_stamp, self.my_id, total_storage_size))

    def log_timing(self, deferred, op):
        ts = time.time() - self.start_time
        cb = lambda _, t=ts: self.write_to_log('dht.log', '%d %s %.3f\n', ts, op, time.time() - self.start_time - t)
        eb = lambda _: self.write_to_log('dht.log', '%d %s -1', ts, op)
        deferred.addCallbacks(cb, eb)

    def write_to_log(self, fn, string, *values):
        with open(fn, 'a') as fp:
            fp.write(string % values)

