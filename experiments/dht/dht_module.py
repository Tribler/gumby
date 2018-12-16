import time

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

    @experiment_callback
    def start_queries(self, key):
        # Write the default value: element was not found
        with open('DHT_dissemination_time.log', 'w') as fp:
            fp.write('%d %s -1\n' % (self.my_id, 'miss'))

        self.callbacks['query_storage'] = LoopingCall(self.query_dht_storage, key.decode('hex')).start(0.0001, True)
        self.start_time = time.time()

    def on_ipv8_available(self, _):
        # Disable threadpool messages
        self.overlay._use_main_thread = True

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

    def query_dht_storage(self, key):
        """
        Query the local storage of the DHT Community for the element located at the specified key

        :param key: the key for which a query should be made
        :return: None
        """
        query_time = time.time() - self.start_time
        if self.overlay.storage.get(key, limit=1):
            with open('DHT_dissemination_time.log', 'w') as fp:
                # Record the time in milliseconds
                fp.write('%d %s %.6f\n' % (self.my_id, 'hit', query_time * 1000))

            # If the element has finally been found, then we should stop the LoopingCall for this method
            self.callbacks['query_storage'].stop()

    def log_timing(self, deferred, op):
        ts = time.time() - self.start_time
        cb = lambda _, t=ts: self.write_to_log('dht.log', '%d %s %.3f\n', ts, op, time.time() - self.start_time - t)
        eb = lambda _: self.write_to_log('dht.log', '%d %s -1', ts, op)
        deferred.addCallbacks(cb, eb)

    def write_to_log(self, fn, string, *values):
        with open(fn, 'a') as fp:
            fp.write(string % values)
