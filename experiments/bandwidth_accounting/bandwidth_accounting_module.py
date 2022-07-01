import random

from tribler.core.components.bandwidth_accounting.bandwidth_accounting_component import BandwidthAccountingComponent
from tribler.core.components.bandwidth_accounting.community.bandwidth_accounting_community import \
    BandwidthAccountingCommunity

from gumby.experiment import experiment_callback
from gumby.modules.tribler_module import TriblerBasedModule
from gumby.util import run_task


class BandwidthAccountingModule(TriblerBasedModule):
    def __init__(self, experiment):
        super().__init__(experiment)
        self.payouts_task = None

    @property
    def community(self) -> BandwidthAccountingCommunity:
        return self.get_component(BandwidthAccountingComponent).community

    @experiment_callback
    def start_payouts(self):
        delay = random.random()

        def start():
            self._logger.info("Starting random payouts!")
            self.payouts_task = run_task(self.do_random_payout, interval=1.0)

        run_task(start, delay=delay)

    def do_random_payout(self):
        verified_peers = list(self.community.network.verified_peers)
        random_peer = random.choice(verified_peers)
        random_amount = random.randint(1 * 1024 * 1024, 10 * 1024 * 1024)
        self._logger.info("Performing payout to peer %s with amount %d", random_peer, random_amount)
        self.community.do_payout(random_peer, random_amount)

    @experiment_callback
    def stop_payouts(self):
        self._logger.info("Stopping random payouts!")
        if self.payouts_task:
            self.payouts_task.cancel()
