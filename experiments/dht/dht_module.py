import time
from binascii import unhexlify

from gumby.experiment import experiment_callback
from gumby.modules.community_experiment_module import IPv8OverlayExperimentModule
from gumby.modules.experiment_module import static_module

from ipv8.dht import DHTError
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
        for peer_id in self.all_vars.keys():
            if int(peer_id) != self.my_id:
                self.overlay.walk_to(self.experiment.get_peer_ip_port_by_id(peer_id))

    @experiment_callback
    async def store(self, key, value):
        await self.log_timing(self.overlay.store_value(unhexlify(key), value.encode('utf-8')), 'store')

    @experiment_callback
    async def find(self, key):
        await self.log_timing(self.overlay.find_values(unhexlify(key)), 'find')

    @experiment_callback
    async def do_dht_announce(self):
        try:
            nodes = await self.overlay.store_peer()
        except Exception as e:
            self._logger.error("Error when storing peer: %s", e)
            return

        if nodes is not None:
            self._logger.info("Stored this peer on %d nodes", len(nodes))

    async def log_timing(self, coro, op):
        ts = time.time() - self.start_time
        try:
            await coro
            self.write_to_log('dht.log', '%d %s %.3f\n', ts, op, time.time() - self.start_time - ts)
        except DHTError:
            self.write_to_log('dht.log', '%d %s -1', ts, op)

    def write_to_log(self, fn, string, *values):
        with open(fn, 'a') as fp:
            fp.write(string % values)
