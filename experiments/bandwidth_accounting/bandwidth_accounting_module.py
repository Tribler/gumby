import random

from tribler_core.modules.bandwidth_accounting.community import BandwidthAccountingCommunity

from gumby.experiment import experiment_callback
from gumby.modules.community_experiment_module import IPv8OverlayExperimentModule
from gumby.util import run_task


class BandwidthAccountingModule(IPv8OverlayExperimentModule):
    def __init__(self, experiment):
        super().__init__(experiment, BandwidthAccountingCommunity)
        self.payouts_task = None

    @experiment_callback
    def start_payouts(self):
        delay = random.random()

        def start():
            self._logger.info("Starting random payouts!")
            self.payouts_task = run_task(self.do_random_payout, interval=1.0)

        run_task(start, delay=delay)

    def do_random_payout(self):
        verified_peers = list(self.overlay.network.verified_peers)
        random_peer = random.choice(verified_peers)
        random_amount = random.randint(1 * 1024 * 1024, 10 * 1024 * 1024)
        self._logger.info("Performing payout to peer %s with amount %d", random_peer, random_amount)
        self.overlay.do_payout(random_peer, random_amount)

    @experiment_callback
    def stop_payouts(self):
        self._logger.info("Stopping random payouts!")
        if self.payouts_task:
            self.payouts_task.cancel()
