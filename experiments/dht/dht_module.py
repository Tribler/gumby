import time

from gumby.experiment import experiment_callback
from gumby.modules.community_experiment_module import IPv8OverlayExperimentModule
from gumby.modules.experiment_module import static_module

from ipv8.dht.discovery import DHTDiscoveryCommunity


@static_module
class DHTModule(IPv8OverlayExperimentModule):
    """
    This module contains code to manage experiments with the DHT community.
    """

    def __init__(self, experiment):
        super(DHTModule, self).__init__(experiment, DHTDiscoveryCommunity)
        self.start_time = 0

    def on_id_received(self):
        super(DHTModule, self).on_id_received()
        self.tribler_config.set_dht_enabled(True)

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

    def log_timing(self, deferred, op):
        ts = time.time() - self.start_time
        cb = lambda _, t=ts: self.write_to_log('dht.log', '%d %s %.3f\n', ts, op, time.time() - self.start_time - t)
        eb = lambda _: self.write_to_log('dht.log', '%d %s -1', ts, op)
        deferred.addCallbacks(cb, eb)

    def write_to_log(self, fn, string, *values):
        with open(fn, 'a') as fp:
            fp.write(string % values)

