import time
from binascii import unhexlify

from ipv8.dht import DHTError
from ipv8.dht.discovery import DHTDiscoveryCommunity

from tribler.core.components.ipv8.ipv8_component import Ipv8Component

from gumby.experiment import experiment_callback
from gumby.modules.tribler_module import TriblerBasedModule


class DHTModule(TriblerBasedModule):
    """
    This module contains code to manage experiments with the DHT community.
    """

    def __init__(self, experiment):
        super().__init__(experiment)
        self.start_time = 0

    def on_id_received(self):
        super().on_id_received()
        self.tribler_module.tribler_config.dht.enabled = True
        self.start_time = time.time()

    @property
    def community(self) -> DHTDiscoveryCommunity:
        return self.get_component(Ipv8Component).dht_discovery_community

    @experiment_callback
    def introduce_peers_dht(self):
        for peer_id in self.all_vars.keys():
            if int(peer_id) != self.my_id:
                self.community.walk_to(self.experiment.get_peer_ip_port_by_id(peer_id))

    @experiment_callback
    async def store(self, key, value):
        await self.log_timing(self.community.store_value(unhexlify(key), value.encode('utf-8')), 'store')

    @experiment_callback
    async def find(self, key):
        await self.log_timing(self.community.find_values(unhexlify(key)), 'find')

    @experiment_callback
    async def do_dht_announce(self):
        try:
            nodes = await self.community.store_peer()
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
            self.write_to_log('dht.log', '%d %s -1\n', ts, op)

    def write_to_log(self, fn, string, *values):
        with open(fn, 'a') as fp:
            fp.write(string % values)
